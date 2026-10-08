# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies (required if running Playwright/browser automation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition file first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser binaries (if your project uses Playwright)
RUN python -m playwright install --with-deps chromium

# Copy the rest of the application code (including save_auth_state.py and main scripts)
COPY . .

# Run your auth script or main entry point
CMD ["python", "main.py"]
