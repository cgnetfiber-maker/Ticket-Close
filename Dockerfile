FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser dependencies if your script automates browser interactions
RUN python -m playwright install --with-deps chromium || true

COPY . .

# Replace with the exact script name you want Render to run
CMD ["python", "save_auth_state.py"]
