import os
import requests
import re
import json
import time
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# ---------------- CONFIG ---------------- #
SERP_API_KEY = os.environ["SERPAPI_KEY"]

KEYWORDS = [
    "personal psychology blog",
    "independent psychology writer",
    "psychology essays personal site",
    "human behavior personal blog",
    "radical psychology thinker"
]

MAX_RESULTS_PER_KEYWORD = 10

BLOCKED_DOMAINS = [
    "medium.com", "substack.com", "wordpress.com", "wixsite.com",
    "blogspot.com", "tumblr.com", "github.io"
]

FAKE_DOMAINS = [
    "example.com", "domain.com", "sentry.io", "feedly.com", "amazon.com"
]

ASSET_EXTENSIONS = (
    ".png", ".jpg", ".jpeg", ".svg", ".webp",
    ".css", ".js", ".woff", ".ico"
)

EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"

# ---------------- GSHEET SETUP ---------------- #
creds_json = json.loads(os.environ["GOOGLE_CREDS_JSON"])
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
client = gspread.authorize(creds)

sheet = client.open("PsychThoughtLeads")
leads_ws = sheet.worksheet("Leads")
visited_ws = sheet.worksheet("Visited")

existing_emails = set(filter(None, leads_ws.col_values(1)))
visited_urls = set(filter(None, visited_ws.col_values(1)))

# ---------------- HELPERS ---------------- #
def is_personal_blog(url):
    domain = urlparse(url).netloc.lower()
    return not any(bad in domain for bad in BLOCKED_DOMAINS)

def valid_email(email):
    if email.endswith(ASSET_EXTENSIONS):
        return False
    domain = email.split("@")[-1].lower()
    if domain in FAKE_DOMAINS:
        return False
    return True

def extract_emails(url):
    emails = set()
    try:
        r = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")

        for tag in soup.find_all(text=True):
            if tag.parent.name in ["p", "span", "a", "div"]:
                found = re.findall(EMAIL_REGEX, tag)
                for e in found:
                    if valid_email(e):
                        emails.add(e.lower())
    except:
        pass
    return emails

def serp_search(query):
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERP_API_KEY,
        "num": MAX_RESULTS_PER_KEYWORD
    }
    r = requests.get("https://serpapi.com/search", params=params)
    data = r.json()
    return [res["link"] for res in data.get("organic_results", [])]

# ---------------- MAIN ---------------- #
def main():
    new_rows = []
    visited_new = []

    for keyword in KEYWORDS:
        urls = serp_search(keyword)

        for url in urls:
            if url in visited_urls:
                continue
            if not is_personal_blog(url):
                continue

            emails = extract_emails(url)

            for email in emails:
                if email not in existing_emails:
                    new_rows.append([
                        email,
                        url,
                        keyword,
                        datetime.utcnow().isoformat()
                    ])
                    existing_emails.add(email)

            visited_new.append([url])
            visited_urls.add(url)
            time.sleep(1)

    if new_rows:
        leads_ws.append_rows(new_rows)
    if visited_new:
        visited_ws.append_rows(visited_new)

    print(f"Added {len(new_rows)} new human emails.")

if __name__ == "__main__":
    main()
