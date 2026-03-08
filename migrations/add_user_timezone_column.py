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

    # Define the new columns and their SQL definitions
    # timezone: TEXT (e.g., 'Europe/Rome')
    # utc_offset: REAL (e.g., 1.0 or 3.5)
    # silent_start/end: INTEGER (Hour in 24h format)
    new_columns = {
        'timezone': "TEXT DEFAULT 'UTC'",
        'utc_offset': "REAL DEFAULT 0.0",
        'latitude': "REAL",
        'longitude': "REAL",
        'silent_start': "INTEGER DEFAULT 23",
        'silent_end': "INTEGER DEFAULT 8"
    }

    try:
        # Check current columns in the users table
        cursor.execute("PRAGMA table_info(users)")
        existing_columns = [column[1] for column in cursor.fetchall()]

        migration_happened = False

        for col_name, col_def in new_columns.items():
            if col_name not in existing_columns:
                print(f"🚀 Migrating: Adding '{col_name}' column...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
                migration_happened = True

        if migration_happened:
            conn.commit()
            print("✅ Migration successful: All new columns added and existing records updated.")
        else:
            print("ℹ️ Database is already up to date. No migration needed.")

    except Exception as e:
        print(f"💥 An error occurred during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()