# Ticket Close SSRMS Automation

Watches the configured Google Sheet for ticket/remark rows and updates each ticket in SSRMS. New rows and changed remarks are processed automatically and assigned to **Ramjee Katwal**. The watcher verifies the update in SSRMS before recording it as complete.

## Run

1. Install Python 3.10 or newer.
2. Share the Google Sheet as **Anyone with the link – Viewer** so the watcher can read its CSV export. The default URL points at the provided sheet tab. Open PowerShell in this folder and install the requirements:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m playwright install chromium
   ```

3. Start the watcher:

   ```powershell
   .\.venv\Scripts\python.exe .\watcher.py
   ```

4. Sign in to SSRMS in the browser window opened by the watcher, then press Enter in PowerShell. The automation does not save or request your password.
5. Keep the watcher running. It checks the sheet every 15 seconds by default; press `Ctrl+C` to stop it.

The selected sheet tab must contain `Ticket` and `Remarks` headers within the first 10 rows. Rows with an empty ticket or remark are skipped. Each distinct ticket/remark pair is processed once, so multiple remark rows for a ticket are retained; if a remark is later edited, the changed remark is added to that ticket's internal remarks and the ticket is assigned to Ramjee Katwal again.

## Run with Docker

Docker runs the watcher headlessly, so create an authenticated Playwright browser-state file on the host first. The file contains session credentials; keep it private and do not commit or share it.

1. Install the project requirements and Chromium locally using the steps above.
2. Run the helper and sign in to SSRMS in the browser window:

   ```powershell
   .\.venv\Scripts\python.exe .\save_auth_state.py
   ```

   This creates `ssrms-storage-state.json`. If the SSRMS session expires, rerun the helper to refresh it.
3. Build the image and create a persistent state directory:

   ```powershell
   docker build -t ticket-close-automation .
   New-Item -ItemType Directory -Force .\docker-data | Out-Null
   ```

4. Start the watcher, mounting the browser state read-only and the processing state directory read-write:

   ```powershell
   docker run --rm --name ticket-close `
     --mount "type=bind,source=$((Resolve-Path '.\ssrms-storage-state.json').Path),target=/run/secrets/ssrms-storage-state.json,readonly" `
     --mount "type=bind,source=$((Resolve-Path '.\docker-data').Path),target=/data" `
     ticket-close-automation
   ```

The container polls every 15 seconds by default. Set `WATCH_INTERVAL_SECONDS` with `docker run -e` to change the interval. The watcher writes completion fingerprints under `docker-data` so they survive container restarts.

## Options

Set these environment variables in PowerShell before starting the watcher:

```powershell
$env:SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/export?format=csv&gid=SHEET_TAB_ID"
$env:WATCH_INTERVAL_SECONDS = "15"
$env:SSRMS_BASE_URL = "https://billing.cgnet.com.np/h8ssrms"
.\.venv\Scripts\python.exe .\watcher.py
```

`SHEET_CSV_URL` defaults to the CSV export for the provided Google Sheets tab. Set it to another sheet's CSV export URL to change the source. The watcher fetches fresh data each polling cycle, so the sheet must remain link-viewable. Completed row fingerprints are stored in `.ticket-close-state.json` in this folder (or `/data` in Docker) so unchanged rows are not submitted again. Delete that file only if you intentionally want the watcher to recheck every row. SSRMS remains the source of truth: before editing, the watcher checks whether the requested assignee and remark are already present, which helps prevent duplicate remarks if it is restarted after a successful save.
