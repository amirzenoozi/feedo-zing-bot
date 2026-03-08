import os
import json
import feedparser
import datetime
import asyncio
import random

from dotenv import load_dotenv
from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters
)

# Import our custom database functions
from scripts import database_manager
from scripts.utils import load_all_locales

# Load environment variables
load_dotenv()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
PREMIUM_FEEDS_LIMIT = int(os.getenv('PREMIUM_FEEDS_LIMIT'))
FREEMIUM_FEEDS_LIMIT = int(os.getenv('FREEMIUM_FEEDS_LIMIT'))

LINKS_PATH = os.path.join("constants", "links.json")

# --- Conversation Constant Variables ---
WAITING_FOR_RSS_NAME, WAITING_FOR_RSS_URL = range(2)
ADMIN_ADD_NAME, ADMIN_ADD_URL = range(3, 5)
WAITING_FOR_BROADCAST = 10

# --- Localization Data ---
LOCALES_PATH = os.path.join(BASE_DIR, "locales")
SUPPORTED_LANGUAGES = ['en', 'it', 'de', 'ru']
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
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows bot statistics."""
    user_id = update.effective_user.id
    lang = await get_lang(update, context)

    if ADMIN_ID and str(user_id) == str(ADMIN_ID):
        users_count, premium_counts, custom_feeds_count = database_manager.get_stats_for_admin()
        text = MESSAGES[lang]['stats_template'].format(users=users_count, subscribers=premium_counts, custom_feeds=custom_feeds_count)
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text(MESSAGES[lang]['stats_error_text'])
        return


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command or menu to change language."""
    lang = await get_lang(update, context)
    keyboard = [[
        InlineKeyboardButton("English 🇺🇸", callback_data="set_lang_en"),
        InlineKeyboardButton("Italiano 🇮🇹", callback_data="set_lang_it")
    ],[
        InlineKeyboardButton("Русский 🇷🇺", callback_data="set_lang_ru"),
        InlineKeyboardButton("Deutsch 🇩🇪", callback_data="set_lang_de")
    ]]
    await update.message.reply_text(
        MESSAGES[lang]['choose_lang'],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def user_feeds_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Opens the feed selection menu."""
    user_id = update.effective_user.id
    lang = await get_lang(update, context)

    text = MESSAGES[lang]['feeds_selection'].format(free=FREEMIUM_FEEDS_LIMIT, premium=PREMIUM_FEEDS_LIMIT)

    await update.message.reply_text(
        text,
        reply_markup=get_settings_main_keyboard()
    )


async def contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /home command to show project links."""
    lang = await get_lang(update, context)
    text = MESSAGES[lang]['contact_message']
    keyboard = [
        [
            InlineKeyboardButton(MESSAGES[lang]['contact_home_page'], url="https://amirdouzandeh.me/en"),
            InlineKeyboardButton(MESSAGES[lang]['contact_github'], url="https://github.com/amirzenoozi/feedo-zing-bot")
        ],
        [
            InlineKeyboardButton(MESSAGES[lang]['contact_issue'], url="https://github.com/amirzenoozi/feedo-zing-bot/issues/new")
        ]
    ]

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def admin_add_feed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the official feed addition process (Admin only)."""
    user_id = update.effective_user.id
    lang = await get_lang(update, context)

    # Check if the user is the admin
    if str(user_id) != str(ADMIN_ID):
        await update.message.reply_text(MESSAGES[lang]['stats_error_text'])
        return ConversationHandler.END

    await update.message.reply_text(MESSAGES[lang]['submit_rss_admin'])
    return ADMIN_ADD_NAME


async def admin_manage_feeds_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for the admin feed management panel."""
    user_id = update.effective_user.id
    lang = await get_lang(update, context)

    # Security Check
    if str(user_id) != str(ADMIN_ID):
        await update.message.reply_text(MESSAGES[lang]['stats_error_text'])
        return

    await update.message.reply_text(
        MESSAGES[lang]['admin_manage_feeds'],
        reply_markup=get_admin_manage_feeds_keyboard(),
        parse_mode="Markdown"
    )


async def send_invoice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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


async def get_news_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Fetches and sends news immediately ONLY for premium users.
    Free users are prompted to subscribe.
    """
    user_id = update.effective_user.id
    lang = await get_lang(update, context)

    # 1. Check if user is premium
    is_premium = database_manager.is_user_premium(user_id)

    if is_premium:
        # Inform them it's coming (parsing can take a few seconds)
        wait_text = MESSAGES[lang]['fetching']
        wait_msg = await update.message.reply_text(wait_text)

        # Call the existing modular function
        await send_news_to_chat(user_id, context, feed_cache={}, is_premium=True)

        # Clean up the "Fetching..." message
        await wait_msg.delete()
    else:
        # 2. Handle Free Users
        sub_text = MESSAGES[lang]['upgrade_your_plan']
        sub_btn_text = MESSAGES[lang]['sub_btn']

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(sub_btn_text, callback_data="buy_sub")]
        ])

        await update.message.reply_text(
            sub_text,
            reply_markup=keyboard
        )


def get_settings_main_keyboard():
    """First screen: Choose between Presets or Custom feeds."""
    keyboard = [
        [InlineKeyboardButton("📋 Official Presets", callback_data="view_presets_0")],
        [InlineKeyboardButton("➕ Add Custom RSS", callback_data="add_custom_rss")],
        [InlineKeyboardButton("🚪 Done", callback_data="cancel_settings")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_feeds_keyboard(user_id, page=0, items_per_page=6):
    """
    Generates paginated keyboard.
    Mode 'presets' shows official feeds.
    Mode 'custom' shows only feeds created by this user.
    """
    # Use the new unified query
    all_feeds = database_manager.get_available_feeds(user_id)
    selected_feeds = [f[0] for f in database_manager.get_user_selected_feeds(user_id)]

    start = page * items_per_page
    end = start + items_per_page
    current_page_feeds = all_feeds[start:end]

    keyboard = []
    for f_id, f_name in current_page_feeds:
        status = "✅" if f_id in selected_feeds else "❌"
        # We pass the mode in the callback so the bot knows which list to redraw
        keyboard.append([InlineKeyboardButton(f"{status} {f_name}", callback_data=f"toggle_{f_id}_{page}")])

    # Nav Row
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page_{page - 1}"))
    if end < len(all_feeds):
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page + 1}"))

    if nav_row: keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_settings_main")])

    return InlineKeyboardMarkup(keyboard)


def get_admin_manage_feeds_keyboard(page=0, items_per_page=6):
    """Generates a keyboard for admin to toggle official feeds status."""
    all_feeds = database_manager.get_all_official_feeds_for_admin()

    start = page * items_per_page
    end = start + items_per_page
    current_page_feeds = all_feeds[start:end]

    keyboard = []
    for f_id, f_name, is_active in current_page_feeds:
        # ✅ = Active (Visible to users), 🚫 = Inactive (Hidden)
        status_icon = "✅" if is_active else "🚫"
        keyboard.append([InlineKeyboardButton(f"{status_icon} {f_name}", callback_data=f"adm_toggle_{f_id}_{page}")])

    # Navigation
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"adm_page_{page - 1}"))
    if end < len(all_feeds):
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"adm_page_{page + 1}"))

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("🚪 Close Admin Panel", callback_data="cancel_settings")])
    return InlineKeyboardMarkup(keyboard)


# Handle Custom RSS Conversation
async def start_custom_rss_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered when user clicks 'Add Custom RSS'."""
    query = update.callback_query
    lang = await get_lang(update, context)
    await query.answer()
    await query.message.edit_text(MESSAGES[lang]['insert_rss_name'])
    return WAITING_FOR_RSS_NAME


async def handle_custom_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['temp_rss_name'] = update.message.text
    lang = await get_lang(update, context)
    await update.message.reply_text(MESSAGES[lang]['insert_rss_link'])
    return WAITING_FOR_RSS_URL


async def handle_custom_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    url = update.message.text
    name = context.user_data.get('temp_rss_name')
    lang = await get_lang(update, context)

    # Basic check if it's a valid RSS
    feed = feedparser.parse(url)
    if not feed.entries:
        await update.message.reply_text(MESSAGES[lang]['invalid_rss'])
        return ConversationHandler.END

    # Save to DB with user_id
    database_manager.add_custom_feed(user_id, name, url)

    await update.message.reply_text(MESSAGES[lang]['rss_add_successfully'].format(name=name), reply_markup=get_settings_main_keyboard())
    return ConversationHandler.END


# Handle Custom RSS Conversation For Admin User
async def handle_admin_feed_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['admin_temp_name'] = update.message.text
    lang = await get_lang(update, context)
    await update.message.reply_text(MESSAGES[lang]['insert_rss_link'])
    return ADMIN_ADD_URL


async def handle_admin_feed_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get('admin_temp_name')
    url = update.message.text
    lang = await get_lang(update, context)

    # Basic validation
    feed = feedparser.parse(url)
    if not feed.entries:
        await update.message.reply_text(MESSAGES[lang]['invalid_rss'])
        return ConversationHandler.END

    # Save as NULL user_id in DB
    database_manager.add_official_feed(name, url)

    await update.message.reply_text(MESSAGES[lang]['rss_add_successfully_admin'].format(name=name))
    return ConversationHandler.END


# Handle Broadcast Conversation
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin starts the broadcast process."""
    user_id = update.effective_user.id
    lang = await get_lang(update, context)

    if str(user_id) != str(ADMIN_ID):
        await update.message.reply_text(MESSAGES[lang]['stats_error_text'])
        return

    await update.message.reply_text(MESSAGES[lang]['broadcast_conv_guid'], parse_mode="Markdown")
    return WAITING_FOR_BROADCAST


async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes and sends the message to all users."""
    admin_msg = update.message
    user_id = update.effective_user.id
    all_users = database_manager.get_all_users(user_id)
    lang = await get_lang(update, context)

    count = 0
    blocked = 0

    await update.message.reply_text(MESSAGES[lang]['start_broadcasting'].format(all_users=len(all_users)))

    for user_id in all_users:
        try:
            # If the admin sent a photo
            if admin_msg.photo:
                # Get the highest resolution photo
                photo_file_id = admin_msg.photo[-1].file_id
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=photo_file_id,
                    caption=admin_msg.caption,
                    caption_entities=admin_msg.caption_entities
                )
            # If the admin sent text only
            elif admin_msg.text:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=admin_msg.text,
                    entities=admin_msg.entities
                )
            count += 1
        except Exception as e:
            # Usually happens if a user blocked the bot
            blocked += 1
            continue

    await update.message.reply_text(MESSAGES[lang]['broadcasting_stats'].format(count=count, blocked=blocked), parse_mode="Markdown")
    return ConversationHandler.END


# General Conversation Cancel Function
async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Clears the conversation state and returns to the main settings menu.
    All comments in English.
    """
    lang = await get_lang(update, context)
    msg = MESSAGES[lang]['action_canceled']

    # Check if this was a button click or a typed command
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(msg)
    else:
        await update.message.reply_text(msg)

    # This is the magic return that tells the ConversationHandler to stop
    return ConversationHandler.END


# --- Callback Handling ---
async def button_tap_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data
    await query.answer()

    lang = await get_lang(update, context)

    # 1. Main Navigation
    if data == "view_presets_0":
        await query.message.edit_reply_markup(reply_markup=get_feeds_keyboard(user_id, page=0))

    elif data == "back_to_settings_main":
        await query.message.edit_reply_markup(reply_markup=get_settings_main_keyboard())

    # --- FEED TOGGLING ---
    elif data.startswith("toggle_"):
        parts = data.split("_")
        feed_id, page = int(parts[1]), int(parts[2])
        success, message = database_manager.toggle_feed_selection(user_id, int(feed_id), FREEMIUM_FEEDS_LIMIT, PREMIUM_FEEDS_LIMIT)

        if not success:
            # Show an alert if they hit their limit (e.g., 2/2 feeds)
            await query.answer(f"⚠️ {message}", show_alert=True)
        else:
            # Refresh the keyboard to show the new checkmark/cross
            await query.message.edit_reply_markup(reply_markup=get_feeds_keyboard(user_id, page=int(page)))

    # --- PAGINATION ---
    elif data.startswith("page_"):
        new_page = int(data.split("_")[1])
        await query.message.edit_reply_markup(reply_markup=get_feeds_keyboard(user_id, page=new_page))

    # --- ADMIN TOGGLING OFFICIAL FEEDS ---
    elif data.startswith("adm_toggle_"):
        # Format: adm_toggle_{id}_{page}
        parts = data.split("_")
        f_id, page = int(parts[2]), int(parts[3])

        # Toggle the status in DB
        database_manager.toggle_feed_active_status(f_id)

        # Refresh the keyboard
        await query.message.edit_reply_markup(reply_markup=get_admin_manage_feeds_keyboard(page=page))

    # --- ADMIN FEEDS PAGINATION ---
    elif data.startswith("adm_page_"):
        page = int(data.split("_")[2])
        await query.message.edit_reply_markup(reply_markup=get_admin_manage_feeds_keyboard(page=page))

    # --- CANCEL/EXIT ---
    elif data == "cancel_settings":
        lang = await get_lang(update, context)
        msg = MESSAGES[lang]['saved_feeds_settings']
        await query.message.edit_text(msg)

    elif query.data == "buy_sub":
        await send_invoice_command(update, context)

    elif query.data == "show_lang_menu":
        keyboard = [[
            InlineKeyboardButton("English 🇺🇸", callback_data="set_lang_en"),
            InlineKeyboardButton("Italiano 🇮🇹", callback_data="set_lang_it")
        ],[
            InlineKeyboardButton("Русский 🇷🇺", callback_data="set_lang_ru"),
            InlineKeyboardButton("Deutsch 🇩🇪", callback_data="set_lang_de")
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
            await send_news_to_chat(query.message.chat_id, context, {}, is_premium=True)
        else:
            await query.message.reply_text(MESSAGES[lang]['sub_req'])


# --- Payment Handling ---
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    expiry_dt = database_manager.update_subscription(user_id, days=30)
    await update.message.reply_text(f"✅ Active until: {expiry_dt.strftime('%Y-%m-%d')}")


async def fetch_and_format_feed(feed_name, feed_url):
    """Fetches a single RSS feed and returns a formatted Markdown string."""
    try:
        # Using a timeout or limit is good practice
        feed = feedparser.parse(feed_url)
        if not feed.entries:
            return ""

        msg = f"📌 *{feed_name}*\n\n"
        # Take top 3 entries
        for entry in feed.entries[:3]:
            msg += f"• {entry.title}\n🔗 {entry.link}\n\n"
        return msg
    except Exception as e:
        print(f"Error parsing {feed_url}: {e}")
        return ""


async def send_news_to_chat(chat_id, context, feed_cache, is_premium):
    """Sends personalized news to a specific chat based on user selection."""
    user_feeds = database_manager.get_user_selected_feeds(chat_id)
    lang = context.user_data.get('lang') or database_manager.get_user_language(chat_id)
    is_random = False

    # Check if user has selected anything
    if not user_feeds:
        # Fallback: Pick 2 random feeds so they don't get an empty message
        user_feeds = database_manager.get_random_feeds(limit=1)
        is_random = True

    if not user_feeds:
        return  # Should only happen if 'feeds' table is completely empty

    if not is_premium and not is_random:
        user_feeds = [random.choice(user_feeds)]

    full_message = ""
    if is_random:
        note = f"${MESSAGES[lang]['random_news']} \n\n"
        full_message += note
    elif not is_premium:
        full_message += MESSAGES[lang]['preview_msg']

    for feed_id, feed_name, feed_url in user_feeds:
        # Check if we already fetched this URL in this broadcast cycle
        if feed_url not in feed_cache:
            feed_cache[feed_url] = await fetch_and_format_feed(feed_name, feed_url)

        full_message += feed_cache[feed_url]

    if full_message:
        try:
            await context.bot.send_message(
                chat_id,
                full_message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"Could not send message to {chat_id}: {e}")


async def daily_broadcast(context: ContextTypes.DEFAULT_TYPE):
    """Main job that orchestrates the daily news delivery."""
    # This cache lives only for the duration of this broadcast
    # It prevents downloading the same RSS multiple times
    feed_cache = {}

    subscribers = database_manager.get_active_subscribers()
    for user_id in subscribers:
        try:
            await send_news_to_chat(user_id, context, feed_cache, is_premium=True)
            # Mandatory sleep to respect Telegram's flood limits (30 msgs/sec)
            await asyncio.sleep(0.05)
        except Exception as e:
            print(f"General error in broadcast for {user_id}: {e}")

    # PHASE 2: Freemium Users (One Random Feed)
    freemium_users = database_manager.get_freemium_users()
    for user_id in freemium_users:
        try:
            # We pass is_premium=False to the sender function
            await send_news_to_chat(user_id, context, feed_cache, is_premium=False)
            await asyncio.sleep(0.05)
        except Exception as e:
            print(f"Error in Freemium broadcast for {user_id}: {e}")



# --- Main Application ---
if __name__ == '__main__':
    if not TOKEN:
        print("CRITICAL ERROR: TELEGRAM_BOT_TOKEN not found.")
        exit(1)

    # Initialize the database table
    database_manager.init_db()

    # Build the application
    application = Application.builder().token(TOKEN).build()

    # Define the ConversationHandler for adding custom RSS
    custom_rss_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_custom_rss_flow, pattern="^add_custom_rss$")],
        states={
            WAITING_FOR_RSS_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_name)],
            WAITING_FOR_RSS_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_url)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CallbackQueryHandler(cancel_conversation, pattern="^cancel_settings$")
        ],
        allow_reentry=True
    )

    # Let Admin register Feeds for all Users
    admin_feed_conv = ConversationHandler(
        entry_points=[CommandHandler("add_official", admin_add_feed_command)],
        states={
            ADMIN_ADD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_feed_name)],
            ADMIN_ADD_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_feed_url)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        allow_reentry=True
    )

    # Let Admin Broadcast a Message to all Users
    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", start_broadcast)],
        states={
            WAITING_FOR_BROADCAST: [
                # Catch photos and text
                MessageHandler(filters.PHOTO | filters.TEXT & ~filters.COMMAND, handle_broadcast_message)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        allow_reentry=True
    )

    # Handlers
    application.add_handler(custom_rss_conv)
    application.add_handler(admin_feed_conv)
    application.add_handler(broadcast_conv)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("subscribe", send_invoice_command))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("feeds", user_feeds_command))
    application.add_handler(CommandHandler("get_now", get_news_now_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("admin_feeds", admin_manage_feeds_command))
    application.add_handler(CommandHandler("about", contacts_command))

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