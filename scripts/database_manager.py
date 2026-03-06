import sqlite3
import os
from datetime import datetime

# Path relative to the project root
DB_PATH = os.path.join("database", "bot.db")

def init_db():
    # Ensure database directory exists
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            is_subscribed BOOLEAN DEFAULT 0,
            expiry_date DATETIME,
            join_date DATETIME,
            language TEXT DEFAULT 'en'
        )
    ''')
    conn.commit()
    conn.close()


def add_user(user_id):
    # Register a new user or ignore if already exists
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)', (user_id, now))
    conn.commit()
    conn.close()


def get_active_subscribers():
    # Fetch all users with a valid subscription
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('SELECT user_id FROM users WHERE is_subscribed = 1 AND expiry_date > ?', (now,))
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users


def update_subscription(user_id, days=30):
    # Logic to extend or activate subscription
    from datetime import timedelta
    new_expiry = datetime.now() + timedelta(days=days)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_subscribed = 1, expiry_date = ? WHERE user_id = ?', (new_expiry.strftime('%Y-%m-%d %H:%M:%S'), user_id))
    conn.commit()
    conn.close()
    return new_expiry


def set_user_language(user_id, lang_code):
    """Updates the preferred language for a specific user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET language = ? WHERE user_id = ?', (lang_code, user_id))
    conn.commit()
    conn.close()


def get_user_language(user_id):
    """Returns the user's language, defaults to 'en'."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row and row[0] else 'en'


def is_user_premium(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Check for an active subscription/stars record
    cursor.execute('SELECT is_subscribed FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row[0]) if row else False


def get_official_feeds():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM feeds WHERE generated_user_id IS NULL AND is_active = 1')
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_user_created_feeds(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM feeds WHERE generated_user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def add_custom_feed(user_id, name, url):
    """Saves a user-specific RSS feed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO feeds (name, url, is_active, generated_user_id) VALUES (?, ?, 1, ?)', (name, url, user_id))
    conn.commit()
    conn.close()


def get_user_selected_feeds(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT f.id, f.name, f.url FROM feeds f JOIN user_feeds uf ON f.id = uf.feed_id WHERE uf.user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_random_feeds(limit=1):
    """Returns a list of random active feeds (id, name, url)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # ORDER BY RANDOM() is efficient for small-to-medium tables
    cursor.execute('SELECT id, name, url FROM feeds WHERE is_active = 1 AND generated_user_id IS NULL ORDER BY RANDOM() LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def toggle_feed_selection(user_id, feed_id, freemium_limit=2, premium_limit=5):
    """Adds or removes a feed. Returns (status_code, message)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Check current subscription and count
    cursor.execute('SELECT is_subscribed FROM users WHERE user_id = ?', (user_id,))
    is_premium = cursor.fetchone()[0]
    limit = premium_limit if is_premium else freemium_limit

    cursor.execute('SELECT COUNT(*) FROM user_feeds WHERE user_id = ?', (user_id,))
    current_count = cursor.fetchone()[0]

    # 2. Check if already following
    cursor.execute('SELECT 1 FROM user_feeds WHERE user_id = ? AND feed_id = ?', (user_id, feed_id))
    exists = cursor.fetchone()

    if exists:
        cursor.execute('DELETE FROM user_feeds WHERE user_id = ? AND feed_id = ?', (user_id, feed_id))
        conn.commit()
        conn.close()
        return True, "Removed"

    if current_count >= limit:
        conn.close()
        return False, f"Limit reached ({limit})"

    cursor.execute('INSERT INTO user_feeds (user_id, feed_id) VALUES (?, ?)', (user_id, feed_id))
    conn.commit()
    conn.close()
    return True, "Added"