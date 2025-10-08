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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for L in leads:
        cur.execute(
            "INSERT INTO leads (business_name, domain, url, email, score, message) VALUES (?, ?, ?, ?, ?, ?)",
            (L.get("title",""), L.get("domain",""), L.get("url",""), L.get("email",""), L.get("score",0), L.get("message",""))
        )
    conn.commit()
    conn.close()

# ---------- SEARCH USING SERPAPI ----------
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

# ---------- SCRAPE SITE ----------
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
    except Exception as e:
        return {"text": "", "emails": [], "meta_description": ""}

# ---------- SCORING + MESSAGE ----------
KEYWORDS = ["contact", "services", "clients", "shop", "book", "portfolio", "products"]

def score_lead(lead):
    score = 0
    if lead.get("email"): score += 40
    if any(k in lead.get("text","").lower() for k in KEYWORDS): score += 30
    if lead.get("meta_description"): score += 20
    if len(lead.get("text","").split()) > 100: score += 10
    return min(score, 100)

def generate_message(lead, your_name="Khumo"):
    biz = lead.get("title") or lead.get("domain") or "there"
    msg = f"Hi {biz},\nI'm {your_name}. I help businesses like yours get more customers without paid ads.\nWould you like a free 3-tip audit that shows how to get more leads? Reply and I’ll send it over."
    return msg

# ---------- STREAMLIT UI ----------
st.set_page_config(page_title="Access 2 — Lead Finder", layout="wide")
st.title("Access 2 — AI Lead Finder (Free MVP)")
st.write("Enter a niche and city, and this tool finds real businesses with contact info and outreach messages.")

niche = st.text_input("Niche (e.g. dentist, marketing agency)")
city = st.text_input("City (e.g. Cape Town)")
limit = st.slider("Number of results", 5, 30, 10)
your_name = st.text_input("Your name", "Khumo")

if st.button("Find Leads"):
    if not niche or not city:
        st.error("Please fill in both fields.")
    else:
        init_db()
        st.info("Searching...")
        query = f"{niche} in {city}"
        results = search_google(query, limit=limit)

        if not results:
            st.warning("No results found. Try different keywords.")
        else:
            leads = []
            progress = st.progress(0)
            for i, res in enumerate(results):
                domain = tldextract.extract(urlparse(res["url"]).netloc)
                domain_str = domain.domain + "." + domain.suffix if domain.suffix else domain.domain
                site_data = fetch_site_data(res["url"])
                email = site_data["emails"][0] if site_data["emails"] else ""
                lead = {
                    "title": res["title"],
                    "domain": domain_str,
                    "url": res["url"],
                    "email": email,
                    "meta_description": site_data["meta_description"],
                    "text": site_data["text"]
                }
                lead["score"] = score_lead(lead)
                lead["message"] = generate_message(lead, your_name)
                leads.append(lead)
                progress.progress((i + 1) / len(results))
                time.sleep(0.3)

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

