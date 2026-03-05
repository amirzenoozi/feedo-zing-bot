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
            join_date DATETIME
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