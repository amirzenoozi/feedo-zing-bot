import os
import json
import feedparser
import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Import our custom database functions
import database_manager

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
LINKS_PATH = os.path.join("constants", "links.json")


def get_rss_links():
    # Read links from the volume-mapped JSON file
    try:
        with open(LINKS_PATH, 'r') as f:
            return json.load(f).get("supported_links", [])
    except Exception as e:
        print(f"Error reading links.json: {e}")
        return []


async def daily_broadcast(context: ContextTypes.DEFAULT_TYPE):
    links = get_rss_links()
    subscribers = database_manager.get_active_subscribers()

    if not links or not subscribers:
        return

    for link_info in links:
        feed = feedparser.parse(link_info['url'])
        if not feed.entries: continue

        message = f"📢 *{link_info['name']} Update:*\n\n"
        for entry in feed.entries[:2]:
            message += f"🔹 {entry.title}\n🔗 {entry.link}\n\n"

        for user_id in subscribers:
            try:
                await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            except Exception as e:
                print(f"Failed to send to {user_id}: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    database_manager.add_user(user_id)
    await update.message.reply_text("Welcome! Registered successfully.")


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    expiry = database_manager.update_subscription(user_id)
    await update.message.reply_text(f"Subscribed! Valid until: {expiry.date()}")


if __name__ == '__main__':
    database_manager.init_db()
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", subscribe))

    # Run daily at 09:00
    application.job_queue.run_daily(daily_broadcast, time=datetime.time(hour=9, minute=0))

    print("RSS Bot is live and connected to database...")
    application.run_polling()