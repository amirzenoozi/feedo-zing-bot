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

# Step 2: Create a dummy README (Poetry often requires this to install)
RUN touch README.md

# Install dependencies using Poetry
# We use --no-root to install ONLY libraries without looking for the current project code yet
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --no-directory

# Copy the rest of the application code
COPY . .

# Create the database directory if it doesn't exist (to avoid permission issues)
RUN mkdir -p database constants

# Run the bot script from the scripts folder
CMD ["python", "bot.py"]