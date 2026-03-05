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
from scripts.utils import load_all_locales

# Load environment variables
load_dotenv()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
LINKS_PATH = os.path.join("constants", "links.json")


# --- Localization Data ---
# Define paths and preferences
LOCALES_PATH = os.path.join(BASE_DIR, "locales")
SUPPORTED_LANGUAGES = ['en', 'it']
MESSAGES = load_all_locales(LOCALES_PATH, SUPPORTED_LANGUAGES)

# --- Helper Functions ---
async def get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """Gets language from RAM cache, or DB if not present."""
    user_id = update.effective_user.id
    if 'lang' not in context.user_data:
        # Fallback to DB and store in RAM
        lang = database_manager.get_user_language(user_id)
        context.user_data['lang'] = lang
    return context.user_data['lang']


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
    user_id = update.effective_user.id
    database_manager.add_user(user_id)

    lang = await get_lang(update, context)

    keyboard = [
        [InlineKeyboardButton(MESSAGES[lang]['sub_btn'], callback_data="buy_sub")],
        [InlineKeyboardButton(MESSAGES[lang]['news_btn'], callback_data="get_now")],
        [InlineKeyboardButton(MESSAGES[lang]['lang_btn'], callback_data="show_lang_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(MESSAGES[lang]['start'], reply_markup=reply_markup)


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command or menu to change language."""
    lang = await get_lang(update, context)
    keyboard = [[
        InlineKeyboardButton("English 🇺🇸", callback_data="set_lang_en"),
        InlineKeyboardButton("Italiano 🇮🇹", callback_data="set_lang_it")
    ]]
    await update.message.reply_text(
        MESSAGES[lang]['choose_lang'],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def send_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if ADMIN_ID and str(user_id) == str(ADMIN_ID):
        expiry_dt = database_manager.update_subscription(user_id, days=365)
        await (update.callback_query.message if update.callback_query else update.message).reply_text(
            f"👑 Admin Mode: Active until {expiry_dt.strftime('%Y-%m-%d')}."
        )
        return

    prices = [LabeledPrice("Monthly Plan", 10)]
    await context.bot.send_invoice(
        chat_id=chat_id,
        title="Premium Subscription",
        description="30 days of RSS updates.",
        payload="monthly_news_subscription",
        provider_token="",
        currency="XTR",
        prices=prices
    )


# --- Callback Handling ---
async def button_tap_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()

    lang = await get_lang(update, context)

    if query.data == "buy_sub":
        await send_invoice(update, context)

    elif query.data == "show_lang_menu":
        keyboard = [[
            InlineKeyboardButton("English 🇺🇸", callback_data="set_lang_en"),
            InlineKeyboardButton("Italiano 🇮🇹", callback_data="set_lang_it")
        ]]
        await query.message.edit_text(MESSAGES[lang]['choose_lang'], reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("set_lang_"):
        new_lang = query.data.split("_")[-1]
        database_manager.set_user_language(user_id, new_lang)
        context.user_data['lang'] = new_lang
        await query.message.edit_text(MESSAGES[new_lang]['lang_set'])

    elif query.data == "get_now":
        subscribers = database_manager.get_active_subscribers()
        if user_id in subscribers or (ADMIN_ID and str(user_id) == str(ADMIN_ID)):
            await query.message.reply_text(MESSAGES[lang]['fetching'])
            await send_news_to_chat(query.message.chat_id, context)
        else:
            await query.message.reply_text(MESSAGES[lang]['sub_req'])


# --- Payment Handling ---
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    expiry_dt = database_manager.update_subscription(user_id, days=30)
    await update.message.reply_text(f"✅ Active until: {expiry_dt.strftime('%Y-%m-%d')}")


async def send_news_to_chat(chat_id, context):
    links = get_rss_links()
    for source in links:
        feed = feedparser.parse(source['url'])
        if feed.entries:
            msg = f"📌 *{source['name']}*\n\n"
            for entry in feed.entries[:3]:
                msg += f"• {entry.title}\n🔗 {entry.link}\n\n"
            await context.bot.send_message(chat_id, msg, parse_mode='Markdown', disable_web_page_preview=True)
            await asyncio.sleep(0.1)

async def daily_broadcast(context: ContextTypes.DEFAULT_TYPE):
    subscribers = database_manager.get_active_subscribers()
    for user_id in subscribers:
        try: await send_news_to_chat(user_id, context)
        except: pass


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
    application.add_handler(CommandHandler("language", language_command))

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