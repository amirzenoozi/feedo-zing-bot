# 🤖 RSS News Telegram Bot

A high-performance Telegram Bot built with Python that fetches RSS feeds and delivers them to subscribers. It features **Telegram Stars** payment integration, multi-language support (English & Italian), and an automated daily broadcast system.

---

## ✨ Features

* 📡 **RSS Curation:** Automatically fetches top stories from configured RSS feeds.
* ⭐ **Monetization:** Integrated subscription system using Telegram Stars.
* 🌍 **Multi-language:** Support for English 🇺🇸 and Italian 🇮🇹 with in-memory caching.
* 👑 **Admin Mode:** Bypass payments and manage the bot directly via User ID.
* 🐳 **Dockerized:** Ready for production with Docker and Docker Compose.
* 🗄️ **Persistent Storage:** SQLite database for user management and subscription tracking.

---

## 🛠️ Setup & Installation

### 1. Clone the Repository
```bash
git clone git@github.com:amirzenoozi/feedo-zing-bot.git
```

### 2. Configuration
Create a `.env` file in the root directory:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_ID=your_telegram_user_id
PREMIUM_FEEDS_LIMIT=5
FREEMIUM_FEEDS_LIMIT=2
```

You can insert all RSS feeds you want using admin commands (i.e. `/add_official`) inside the BOT.
For each Item you must Enter a Title and a URL.

### 3. Run with Docker Compose
```bash
docker compose up -d --build
```

## 🗃️ Database Management & Migrations
The bot automatically handles basic migrations on startup.
However, if you add complex schema changes in the future, follow these steps:

### Running Manual Migrations
If you create a new migration script (e.g., migrations/migrate_v2.py), run it inside the existing container environment:
```bash
# Run a specific migration script
docker compose run --rm rss-bot python migrations/migrate_v2.py
```

## 🚀 Commands
| Command         | Description                                  |
|-----------------|----------------------------------------------|
| `/start`        | Register and show the main menu              |
| `/subscribe`    | Open the payment invoice for Telegram Stars  |
| `/profile`      | Handle User Settings (Lang, Timezone)        |
| `/add_official` | ADMIN command to add a new RSS feed          |
| `/stats`        | ADMIN command to see the statistics          |
| `/get_now`      | Premium command to get the latest news Now   |
| `/feeds`        | Manage your own subscribed feeds             |
| `/admin_feeds`  | ADMIN command to manage all feeds            |
| `/about`        | Show the developer information               |
| `/broadcast`    | ADMIN command to send a message to all users |


## 🌐 Supported Languages
At the moment, the bot supports languages list below:

- [x] English (EN) 🇺🇸
- [x] Italian (IT) 🇮🇹
- [x] Русский (RU) 🇷🇺
- [x] Deutsch (DE) 🇩🇪
- [ ] Persian (Fa) 🦁
- [ ] Arabic (AR) 🇸🇦
- [ ] French (FR) 🇫🇷
- [ ] Turkey (TR) 🇹🇷

## 📝 Critique & Challenges

#### Pros:
- Decoupled Architecture: Using database_manager.py keeps the main logic clean. 
- Efficiency: RAM caching for user language prevents excessive Disk I/O. 
- Portability: Docker ensures the bot runs the same way on your laptop and your server.

#### Cons & Challenges:
- SQLite Locking: In a high-traffic environment, SQLite might face "database is locked" errors. Consider migrating to PostgreSQL if you exceed 10,000 active users. 
- Memory Reset: Since the language cache is in RAM, a container restart forces a re-fetch from the DB on the first interaction.


