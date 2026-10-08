import os
import sys
import time
import pandas as pd
from playwright.sync_api import sync_playwright

# Google Sheet CSV Export URL (Sheet ID extracted from your link)
SHEET_ID = "1SyhE9nQf3LV8QEBTCLavgfr8w45y-mI69XPbtuN2hPA"
GID = "1597249711"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

def load_tickets_from_sheet():
    """Fetches tickets directly from the public Google Sheet."""
    print("Fetching ticket list from Google Sheet...")
    try:
        df = pd.read_csv(SHEET_URL)
        # Extract non-null ticket IDs from column 'Details' or fallback to first column
        col_name = 'Details' if 'Details' in df.columns else df.columns[0]
        tickets = df[col_name].dropna().astype(str).str.strip().tolist()
        # Filter out header labels if present
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
        return

    portal_url = os.environ.get("PORTAL_URL", "https://your-ticketing-portal.com")
    username = os.environ.get("PORTAL_USER", "")
    password = os.environ.get("PORTAL_PASS", "")

    with sync_playwright() as p:
        print("Launching headless Chromium browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Execute login sequence if credentials are set
        if username and password:
            print(f"Logging in to {portal_url}...")
            page.goto(portal_url)
            # Adjust selectors below according to your portal's login form
            page.fill("input[name='username']", username)
            page.fill("input[name='password']", password)
            page.click("button[type='submit']")
            page.wait_for_load_state("networkidle")

        for ticket_id in tickets:
            print(f"Processing ticket: {ticket_id}")
            try:
                # Add your ticket search & close automation logic here
                # Example:
                # page.goto(f"{portal_url}/tickets/{ticket_id}")
                # page.click("button#close-ticket")
                # page.fill("textarea#remarks", "Closed via automation script")
                # page.click("button#save")
                time.sleep(1)
            except Exception as e:
                print(f"Failed to close {ticket_id}: {e}")

        browser.close()
        print("Completed processing all tickets.")

if __name__ == "__main__":
    close_tickets()
