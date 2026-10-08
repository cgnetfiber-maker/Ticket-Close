# 1. Base Image
FROM python:3.10-slim

# 2. Set working directory inside the container
WORKDIR /app

# 3. Install system dependencies (required for web automation / headless browser tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy dependency file and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Install Playwright browser dependencies (if using Playwright)
RUN python -m playwright install --with-deps chromium || true

# 6. Copy all project files (including save_auth_state.py and your execution script)
COPY . .

# 7. Entrypoint: Replace 'save_auth_state.py' with your actual main Python filename
CMD ["python", "save_auth_state.py"]
