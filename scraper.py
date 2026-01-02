import os
import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import re
import time

# --------------------------
# Load config
# --------------------------
with open("config.json") as f:
    config = json.load(f)

KEYWORDS = config["keywords"]
MAX_PAGES = config.get("max_pages", 3)
SHEET_NAME = config.get("sheet_name", "PsychThoughtLeads")  # Default sheet name

# --------------------------
# Google Sheets setup via GitHub Secret
# --------------------------
# The secret GOOGLE_CREDS_JSON should contain the full JSON of your service account
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
# Google search function
# --------------------------
def google_search_urls(query, max_pages=3):
    urls = []
    for i in range(max_pages):
        start = i * 10
        search_url = f"https://www.google.com/search?q={query}&start={start}"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            r = requests.get(search_url, headers=headers, timeout=5)
            soup = BeautifulSoup(r.text, "html.parser")
            for link in soup.find_all("a"):
                href = link.get("href")
                if href and href.startswith("/url?q="):
                    url = href.split("/url?q=")[1].split("&")[0]
                    urls.append(url)
            time.sleep(1)
        except Exception as e:
            print(f"Error fetching search results for {query}: {e}")
            continue
    return list(set(urls))

# --------------------------
# Email extraction
# --------------------------
def extract_emails(url):
    emails = set()
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text()
        found = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
        for email in found:
            emails.add(email)
    except Exception as e:
        print(f"Error extracting emails from {url}: {e}")
    return list(emails)

# --------------------------
# Main scraping logic
# --------------------------
def main():
    results = []
    for keyword in KEYWORDS:
        print(f"Searching for keyword: {keyword}")
        urls = google_search_urls(keyword, MAX_PAGES)
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
