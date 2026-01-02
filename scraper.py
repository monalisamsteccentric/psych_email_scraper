import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import re
import time

# Load config
with open("config.json") as f:
    config = json.load(f)

KEYWORDS = config["keywords"]
MAX_PAGES = config.get("max_pages", 3)

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("PsychThoughtLeads").sheet1

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
        except:
            continue
    return list(set(urls))

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
    except:
        pass
    return list(emails)

def main():
    results = []
    for keyword in KEYWORDS:
        urls = google_search_urls(keyword, MAX_PAGES)
        for url in urls:
            emails = extract_emails(url)
            if emails:
                for e in emails:
                    results.append({"url": url, "email": e, "keyword": keyword})

    if results:
        df = pd.DataFrame(results)
        sheet.append_rows(df.values.tolist())
        print(f"Added {len(results)} emails to Google Sheet.")
    else:
        print("No emails found.")

if __name__ == "__main__":
    main()
