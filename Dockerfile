FROM python:3.11-slim

# Set environment variables to prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Poetry
RUN pip install --no-cache-dir poetry

# Set the working directory in the container
WORKDIR /app

# Copy only the dependency files first to leverage Docker cache
COPY pyproject.toml poetry.lock* ./

# Install dependencies using Poetry
# We disable virtualenv creation because the container itself is an isolated environment
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Copy the rest of the application code
COPY . .

# Create the database directory if it doesn't exist (to avoid permission issues)
RUN mkdir -p database constants

# Run the bot script from the scripts folder
CMD ["python", "scripts/bot.py"]