FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install the few packages we need directly
# Using --no-cache-dir keeps the image size minimal
RUN pip install --no-cache-dir \
    python-telegram-bot \
    python-telegram-bot[job-queue] \
    asyncio \
    feedparser \
    python-dotenv

# Copy the project files
COPY . .

# Create necessary directories to avoid permission issues with volumes
RUN mkdir -p database constants

# Run the bot
CMD ["python", "bot.py"]