import os
import sys
import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "1SyhE9nQf3LV8QEBTCLavgfr8w45y-mI69XPbtuN2hPA"

def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    
    # Check if JSON string exists in Render Environment Variables
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    elif os.path.exists("service_account.json"):
        return gspread.service_account(filename="service_account.json", scopes=scopes)
    else:
        raise FileNotFoundError("No GOOGLE_CREDENTIALS_JSON env var or service_account.json file found.")

def load_tickets_from_sheet():
    print("Fetching ticket list from Google Sheet via API...")
    try:
        client = get_gspread_client()
        sheet = client.open_by_key(SHEET_ID).sheet1
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
