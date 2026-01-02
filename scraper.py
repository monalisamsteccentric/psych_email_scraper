import os
import json
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import time

# --------------------------
# Load config
# --------------------------
with open("config.json") as f:
    config = json.load(f)

KEYWORDS = config["keywords"]
MAX_RESULTS_PER_KEYWORD = config.get("max_results", 20)
SHEET_NAME = config.get("sheet_name", "PsychThoughtLeads")

# --------------------------
# Google Sheets setup
# --------------------------
creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Try to open existing sheet, else create
try:
    sheet = client.open(SHEET_NAME).sheet1
except gspread.SpreadsheetNotFound:
    spreadsheet = client.create(SHEET_NAME)
    sheet = spreadsheet.sheet1
    print(f"Created new Google Sheet: {SHEET_NAME}")

# --------------------------
# SerpAPI setup
# --------------------------
SERPAPI_KEY = os.environ["SERPAPI_KEY"]
SEARCH_ENGINE = "google"  # SerpAPI engine

def serpapi_search_urls(query, num_results=20):
    """
    Use SerpAPI to get URLs for a search query
    """
    urls = []
    start = 0
    while len(urls) < num_results:
        params = {
            "engine": SEARCH_ENGINE,
            "q": query,
            "api_key": SERPAPI_KEY,
            "start": start
        }
        try:
            response = requests.get("https://serpapi.com/search", params=params, timeout=10)
            data = response.json()
            for result in data.get("organic_results", []):
                link = result.get("link")
                if link:
                    urls.append(link)
            start += 10
            time.sleep(1)
        except Exception as e:
            print(f"Error in SerpAPI request: {e}")
            break
    return urls[:num_results]

# --------------------------
# Email extraction
# --------------------------
def extract_emails(url):
    emails = set()
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        text = r.text
        found = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        for email in found:
            emails.add(email)
    except Exception as e:
        print(f"Error extracting emails from {url}: {e}")
    return list(emails)

# --------------------------
# Main function
# --------------------------
def main():
    results = []
    for keyword in KEYWORDS:
        print(f"Searching for keyword: {keyword}")
        urls = serpapi_search_urls(keyword, MAX_RESULTS_PER_KEYWORD)
        print(f"Found {len(urls)} URLs")
        for url in urls:
            emails = extract_emails(url)
            if emails:
                for e in emails:
                    results.append({"url": url, "email": e, "keyword": keyword})

    if results:
        df = pd.DataFrame(results)
        try:
            sheet.append_rows(df.values.tolist())
            print(f"Added {len(results)} emails to Google Sheet '{SHEET_NAME}'.")
        except Exception as e:
            print(f"Error writing to Google Sheet: {e}")
    else:
        print("No emails found.")

if __name__ == "__main__":
    main()
