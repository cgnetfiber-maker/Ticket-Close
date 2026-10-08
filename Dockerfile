FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH="/ms-playwright" \
    TICKET_STATE_PATH="/data/.ticket-close-state.json" \
    SSRMS_HEADLESS="true" \
    SSRMS_STORAGE_STATE="/run/secrets/ssrms-storage-state.json"

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

COPY watcher.py save_auth_state.py ./

RUN useradd --create-home --uid 10001 app \
    && mkdir -p /data \
    && chown app:app /data

USER app

CMD ["python", "watcher.py"]
