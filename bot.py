import os
import json
import feedparser
import datetime

from dotenv import load_dotenv
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, PreCheckoutQueryHandler, SuccessPaymentHandler

# Import our custom database functions
from scripts import database_manager

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
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
    chat_id = update.effective_chat.id
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


# --- Daily Broadcast Task ---
async def daily_broadcast(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled task to send news to all active subscribers."""
    links = get_rss_links()
    subscribers = database_manager.get_active_subscribers()

    if not links or not subscribers:
        return

    for source in links:
        feed = feedparser.parse(source['url'])
        if not feed.entries:
            continue

        # Prepare the summary message
        msg = f"📌 *Latest from {source['name']}*:\n\n"
        for entry in feed.entries[:3]:  # Send top 3 articles
            msg += f"• {entry.title}\n🔗 {entry.link}\n\n"

        for user_id in subscribers:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=msg,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                await asyncio.sleep(0.05)  # Small delay to avoid rate limiting
            except Exception as e:
                print(f"Error sending to {user_id}: {e}")


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
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    # Job Queue for Daily Updates (e.g., 09:00 AM)
    job_queue = application.job_queue
    job_queue.run_daily(
        daily_broadcast,
        time=datetime.time(hour=9, minute=0, second=0)
    )

    print("Bot is starting...")
    application.run_polling()