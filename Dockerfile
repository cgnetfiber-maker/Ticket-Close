# 1. Base Python image
FROM python:3.10-slim

# 2. Set working directory
WORKDIR /app

# 3. Install required system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy dependency list and install Python libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Install Playwright browser binaries and dependencies
RUN python -m playwright install --with-deps chromium || true

# 6. Copy all files into the container
COPY . .

# 7. Start command executing the main entry point
CMD ["python", "main.py"]
