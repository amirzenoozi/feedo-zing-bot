import sqlite3
import os
import json

DB_PATH = os.path.join("database", "bot.db")
LINKS_PATH = os.path.join("constants", "links.json")

def migrate():
    """
    Migration V2:
    - Creates 'feeds' and 'user_feeds' tables.
    - Imports existing JSON links into the database.
    """
    if not os.path.exists(DB_PATH):
        print("❌ Database not found. Run the bot first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Create Feeds table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                is_active BOOLEAN DEFAULT 1,
                generated_user_id INTEGER DEFAULT NULL
            )
        ''')

        # 2. Create User-Feed junction table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_feeds (
                user_id INTEGER,
                feed_id INTEGER,
                PRIMARY KEY (user_id, feed_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (feed_id) REFERENCES feeds (id)
            )
        ''')

        # 3. Import JSON links if the feeds table is empty
        cursor.execute("SELECT COUNT(*) FROM feeds")
        if cursor.fetchone()[0] == 0 and os.path.exists(LINKS_PATH):
            with open(LINKS_PATH, 'r') as f:
                links = json.load(f).get("supported_links", [])
                for link in links:
                    cursor.execute("INSERT OR IGNORE INTO feeds (name, url) VALUES (?, ?)",(link['name'], link['url']))
            print(f"✅ Migrated {len(links)} links from JSON to DB.")

        conn.commit()
        print("🚀 Migration complete: Tables created and data migrated.")

    except Exception as e:
        print(f"💥 Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()