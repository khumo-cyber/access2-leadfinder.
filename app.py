import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import sqlite3
import time

# === Database Setup ===
DB_PATH = "leads.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT,
            domain TEXT,
            url TEXT,
            email TEXT,
            meta_description TEXT,
            score INTEGER,
            message TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# === Utility Functions ===

def extract_emails_from_text(text):
    pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    return re.findall(pattern, text)

def score_lead(meta_description, email):
    score = 0
    if not email:
        score -= 2
    if meta_description:
        desc = meta_description.lower()
        if "lead" in desc or "client" in desc or "growth" in desc:
            score += 3
        elif "contact" in desc or "services" in desc:
            score += 1
    return score

def search_google(query, limit=10):
    """Scrape search results from DuckDuckGo (Google blocks scraping)."""
    url = f"https://duckduckgo.com/html/?q={query}"
    resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for a in soup.select(".result__a", limit=limit):
        link = a.get("href")
        title = a.text
        results.append({"title": title, "url": link})
    return results

def analyze_website(url):
    try:
        resp = requests.get(url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        emails = extract_emails_from_text(text)
        meta_tag = soup.find("meta", attrs={"name": "description"})
        meta_desc = meta_tag["content"] if meta_tag and "content" in meta_tag.attrs else ""
        score = score_lead(meta_desc, emails[0] if emails else "")
        return {
            "domain": url.split("//")[-1].split("/")[0],
            "url": url,
            "email": emails[0] if emails else "",
            "meta_description": meta_desc,
            "score": score
        }
    except Exception:
        return {
            "domain": url,
            "url": url,
            "email": "",
            "meta_description": "",
            "score": 0
        }

def save_leads_to_db(leads):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for L in leads:
        cur.execute(
            "INSERT INTO leads (business_name, domain, url, email, meta_description, score, message) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                L.get('title',''),
                L.get('domain',''),
                L.get('url',''),
                L.get('email',''),
                L.get('meta_description',''),
                L.get('score',0),
                L.get('message','')
            )
        )
    conn.commit()
    conn.close()

# === Streamlit UI ===

st.set_page_config(page_title="Access 2 — AI Lead Finder", layout="wide")
st.title("🚀 Access 2 — AI Lead Finder")
st.write("Type a niche + city below to automatically find and score potential leads.")

query = st.text_input("Search Query (e.g. dentists in Cape Town):")
limit = st.slider("Number of leads to collect:", 5, 30, 10)

if st.button("Find Leads"):
    if not query:
        st.warning("Please enter a search query first.")
    else:
        st.info("🔍 Collecting leads... Please wait a few seconds.")
        start_time = time.time()

        results = search_google(query, limit=limit)
        leads = []

        # === Progress bar setup ===
        progress_text = st.empty()
        progress_bar = st.progress(0)

        for i, res in enumerate(results):
            lead_info = analyze_website(res["url"])
            lead = {**res, **lead_info}
            lead["message"] = f"Hey {lead['title']}, noticed your site ({lead['domain']}) could use better lead gen tools."
            leads.append(lead)

            progress_bar.progress(int((i + 1) / len(results) * 100))
            progress_text.text(f"Processing lead {i+1} of {len(results)}")

        progress_bar.empty()
        progress_text.empty()

        save_leads_to_db(leads)
        st.success(f"✅ Done! Collected {len(leads)} leads in {round(time.time()-start_time, 1)}s")

        for L in leads:
            with st.expander(f"{L['title']} — {L['domain']}"):
                st.write(f"**URL:** {L['url']}")
                st.write(f"**Email:** {L['email'] or 'None found'}")
                st.write(f"**Meta Description:** {L['meta_description'] or 'N/A'}")
                st.write(f"**Lead Score:** {L['score']}")
                st.write(f"**Suggested Outreach Message:** {L['message']}")

st.markdown("---")
st.caption("Access 2 — Free AI Lead Finder (Early Tester Build)")

