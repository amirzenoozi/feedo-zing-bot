import os
import json
import feedparser
import datetime
import asyncio

from dotenv import load_dotenv
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    MessageHandler,
    filters
)

# Import our custom database functions
from scripts import database_manager

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
LINKS_PATH = os.path.join("constants", "links.json")


def get_rss_links():
    """Reads the list of RSS feeds from the volume-mapped JSON file."""
    try:
        if not os.path.exists(LINKS_PATH):
            return []
        with open(LINKS_PATH, 'r') as f:
            return json.load(f).get("supported_links", [])
    except Exception as e:
        print(f"Error reading links.json: {e}")
        return []


# --- Bot Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Registers the user and shows the welcome message with a subscription button."""
    user_id = update.effective_user.id
    database_manager.add_user(user_id)

    keyboard = [
        [InlineKeyboardButton("⭐ Subscribe (10 Stars / Month)", callback_data="buy_sub")],
        [InlineKeyboardButton("📰 Get News Now", callback_data="get_now")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Welcome to the RSS News Bot!\n\n"
        "To receive daily updates, you need an active subscription.\n"
        "Click the button below to subscribe using Telegram Stars.",
        reply_markup=reply_markup
    )


async def send_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the Telegram Stars invoice to the user."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # Check if the user is the Admin
    if str(user_id) == str(ADMIN_ID):
        # Admin bypass: Activate subscription directly in DB
        expiry_dt = database_manager.update_subscription(user_id, days=365)  # Give admin 1 year
        await update.message.reply_text(
            f"👑 **Admin Mode Activated**\n"
            f"Your subscription has been manually activated until {expiry_dt.strftime('%Y-%m-%d')}."
        )
        return

    # Regular user: Proceed to Telegram Stars Invoice
    title = "Premium News Subscription"
    description = "30 days of automated RSS updates directly to your chat."
    payload = "monthly_news_subscription"
    currency = "XTR"  # Currency code for Telegram Stars
    price = 10
    prices = [LabeledPrice("Monthly Plan", price)]

    await context.bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",  # Leave empty for Telegram Stars
        currency=currency,
        prices=prices
    )


# --- Callback Handling (The missing link) ---
async def button_tap_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles clicks on inline keyboard buttons."""
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()

    if query.data == "buy_sub":
        await send_invoice(update, context)

    elif query.data == "get_now":
        subscribers = database_manager.get_active_subscribers()
        # Allow if user is subscribed OR is the Admin
        if user_id in subscribers or (ADMIN_ID and str(user_id) == str(ADMIN_ID)):
            await query.message.reply_text("⏳ Fetching latest news for you...")
            # Trigger the broadcast logic specifically for this chat
            await send_news_to_chat(query.message.chat_id, context)
        else:
            await query.message.reply_text("❌ Subscription required. Please click 'Subscribe' first.")


# --- Payment Handling ---
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Answers the pre-checkout query to confirm the transaction."""
    query = update.pre_checkout_query
    if query.invoice_payload != "monthly_news_subscription":
        await query.answer(ok=False, error_message="Invalid payload.")
    else:
        await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered after a successful Telegram Stars payment."""
    user_id = update.effective_user.id
    # Update DB with 30 days subscription
    expiry_dt = database_manager.update_subscription(user_id, days=30)

    await update.message.reply_text(
        f"✅ Payment successful! Your subscription is now active.\n"
        f"📅 Expiry date: {expiry_dt.strftime('%Y-%m-%d')}"
    )


# --- News Logic ---
async def send_news_to_chat(chat_id, context):
    """Fetch and send news to a specific chat ID."""
    links = get_rss_links()
    if not links:
        await context.bot.send_message(chat_id, "No RSS links configured.")
        return

    for source in links:
        feed = feedparser.parse(source['url'])
        if feed.entries:
            msg = f"📌 *{source['name']}*\n\n"
            for entry in feed.entries[:3]:
                msg += f"• {entry.title}\n🔗 {entry.link}\n\n"
            await context.bot.send_message(chat_id, msg, parse_mode='Markdown', disable_web_page_preview=True)
            await asyncio.sleep(0.1)

async def daily_broadcast(context: ContextTypes.DEFAULT_TYPE):
    """Job to send news to all active subscribers."""
    subscribers = database_manager.get_active_subscribers()
    for user_id in subscribers:
        try:
            await send_news_to_chat(user_id, context)
        except Exception as e:
            print(f"Failed sending to {user_id}: {e}")


# --- Main Application ---
if __name__ == '__main__':
    if not TOKEN:
        print("CRITICAL ERROR: TELEGRAM_BOT_TOKEN not found.")
        exit(1)

    # Initialize the database table
    database_manager.init_db()

    # Build the application
    application = Application.builder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", send_invoice))

    # Payment Handlers
    application.add_handler(CallbackQueryHandler(button_tap_handler))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    # Job Queue for Daily Updates (e.g., 09:00 AM)
    job_queue = application.job_queue
    job_queue.run_daily(
        daily_broadcast,
        time=datetime.time(hour=9, minute=0, second=0)
    )

    print("Bot is live with Admin Mode and Stars Payment.")
    application.run_polling()