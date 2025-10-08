import streamlit as st
import requests
import pandas as pd
import re
import time
import sqlite3
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import tldextract

# ---------- CONFIG ----------
SERPAPI_KEY = "c6322d1665b5c1b06517f196b8062a872b1b4bfa93f3e92e2bdcc35a4feb17ca"
DB_PATH = "leads.db"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36'}
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# ---------- DATABASE ----------
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
            score INTEGER,
            message TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_leads(leads):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for L in leads:
            cur.execute(
                "INSERT INTO leads (business_name, domain, url, email, score, message) VALUES (?, ?, ?, ?, ?, ?)",
                (L.get("title",""), L.get("domain",""), L.get("url",""), L.get("email",""), L.get("score",0), L.get("message",""))
            )
        conn.commit()
    except Exception as e:
        st.warning(f"DB error: {e}")
    finally:
        conn.close()

# ---------- SEARCH ----------
def search_google(query, limit=10):
    url = f"https://serpapi.com/search.json?q={query}&engine=google&api_key={SERPAPI_KEY}"
    try:
        r = requests.get(url)
        data = r.json()
        results = []
        for item in data.get("organic_results", [])[:limit]:
            results.append({"title": item.get("title", ""), "url": item.get("link", "")})
        return results
    except Exception as e:
        st.error(f"Search failed: {e}")
        return []

# ---------- SCRAPE ----------
def fetch_site_data(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        emails = re.findall(EMAIL_REGEX, text)
        meta_desc = ""
        md = soup.find("meta", attrs={"name": "description"})
        if md and md.get("content"):
            meta_desc = md["content"]
        return {
            "text": text[:4000],
            "emails": list(set(emails)),
            "meta_description": meta_desc
        }
    except Exception:
        return {"text": "", "emails": [], "meta_description": ""}

# ---------- SCORING ----------
KEYWORDS = ["contact", "services", "clients", "shop", "book", "portfolio", "products"]

def score_lead(lead):
    score = 0
    if lead.get("email"): score += 40
    if any(k in lead.get("text","").lower() for k in KEYWORDS): score += 30
    if lead.get("meta_description"): score += 20
    if len(lead.get("text","").split()) > 100: score += 10
    return min(score, 100)

# ---------- STREAMLIT UI ----------
st.set_page_config(page_title="Access 2 — Lead Finder", layout="wide")
st.title("Access 2 — AI Lead Finder (SerpAPI Version)")
st.caption("Find local leads, analyze sites, and auto-generate outreach messages.")

with st.sidebar:
    st.header("Settings")
    niche = st.text_input("Niche (e.g. dentist, marketing agency)")
    city = st.text_input("City (e.g. Cape Town)")
    limit = st.slider("Number of results", 5, 30, 10)
    your_name = st.text_input("Your name", "Khumo")

    st.markdown("### Outreach Template")
    message_template = st.text_area(
        "Customize your message (use {business}, {your_name}, {niche}, {city})",
        "Hi {business}, I'm {your_name}. I help {niche} in {city} get more customers online. "
        "Would you like a free 3-tip audit to improve your leads?"
    )

run = st.button("Find Leads")

if run:
    if not niche or not city:
        st.error("Please fill in both fields.")
    else:
        init_db()
        st.info("Searching Google...")
        query = f"{niche} in {city}"
        results = search_google(query, limit=limit)

        if not results:
            st.warning("No results found. Try another query.")
        else:
            leads = []
            progress = st.progress(0)
            for i, res in enumerate(results):
                domain = tldextract.extract(urlparse(res["url"]).netloc)
                domain_str = domain.domain + "." + domain.suffix if domain.suffix else domain.domain
                site_data = fetch_site_data(res["url"])
                email = site_data["emails"][0] if site_data["emails"] else ""

                # Customizable message
                message = message_template.format(
                    business=res["title"] or domain_str,
                    your_name=your_name,
                    niche=niche,
                    city=city
                )

                lead = {
                    "title": res["title"],
                    "domain": domain_str,
                    "url": res["url"],
                    "email": email,
                    "meta_description": site_data["meta_description"],
                    "text": site_data["text"],
                    "score": score_lead(site_data),
                    "message": message
                }

                leads.append(lead)
                progress.progress((i + 1) / len(results))
                time.sleep(0.2)

            save_leads(leads)
            st.success(f"✅ Done! Collected {len(leads)} leads.")
            df = pd.DataFrame(leads)
            st.dataframe(df[["domain", "email", "score"]])
            csv = df.to_csv(index=False)
            st.download_button("Download CSV", csv, "leads.csv", "text/csv")

            st.markdown("### Outreach Messages")
            for _, row in df.iterrows():
                st.markdown(f"**{row['domain']}** — score {row['score']}")
                st.code(row["message"], language="text")

