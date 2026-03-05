import sqlite3
import os

DB_PATH = os.path.join("database", "bot.db")

def migrate():
    """
    Safely adds the 'language' column to the users table
    without losing existing user data.
    """
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found at {DB_PATH}. Run the bot first to initialize or check your paths.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check current columns in the users table
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'language' not in columns:
            print("🚀 Migrating database: Adding 'language' column...")
            # Add the column with 'en' as default for all existing records
            cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
            conn.commit()
            print("✅ Migration successful: 'language' column added.")
        else:
            print("ℹ️ Database is already up to date. No migration needed.")

    except Exception as e:
        print(f"💥 An error occurred during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()