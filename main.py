import os
import sys
import time
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright

# Google Sheet ID from your link
SHEET_ID = "1SyhE9nQf3LV8QEBTCLavgfr8w45y-mI69XPbtuN2hPA"
WORKSHEET_NAME = "Details"  # tab name in your spreadsheet

def load_tickets_from_sheet():
    print("Fetching ticket list from Google Sheet via API...")
    try:
        # Define OAuth scopes
        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        
        # Load service account JSON key from Render Environment Variable
        service_account_info = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        
        if service_account_info:
            import json
            creds_dict = json.loads(service_account_info)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)
        else:
            # Fallback to local service_account.json if present
            client = gspread.service_account(filename="service_account.json", scopes=scopes)

        sheet = client.open_by_key(SHEET_ID).worksheet(WORKSHEET_NAME)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        col_name = 'Details' if 'Details' in df.columns else df.columns[0]
        tickets = df[col_name].dropna().astype(str).str.strip().tolist()
        tickets = [t for t in tickets if t.startswith("TKT")]
        
        print(f"Found {len(tickets)} tickets to process.")
        return tickets
    except Exception as e:
        print(f"Error fetching Google Sheet: {e}")
        return []

def close_tickets():
    tickets = load_tickets_from_sheet()
    if not tickets:
        print("No valid tickets found to process. Exiting.")
        sys.exit(1)

    portal_url = os.environ.get("PORTAL_URL", "https://your-ticketing-portal.com")
    username = os.environ.get("PORTAL_USER", "")
    password = os.environ.get("PORTAL_PASS", "")

    with sync_playwright() as p:
        print("Launching headless Chromium browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        if username and password:
            print(f"Logging in to {portal_url}...")
            page.goto(portal_url)
            page.fill("input[name='username']", username)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")

        for ticket_id in tickets:
            print(f"Processing ticket: {ticket_id}")
            time.sleep(1)

        browser.close()
        print("Completed processing all tickets.")

if __name__ == "__main__":
    close_tickets()
