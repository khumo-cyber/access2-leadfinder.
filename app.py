import streamlit as st
import requests
import pandas as pd
import re
import time
import sqlite3
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import tldextract

# ---------------- CONFIG ----------------
SERPAPI_KEY = "c6322d1665b5c1b06517f196b8062a872b1b4bfa93f3e92e2bdcc35a4feb17ca"
DB_PATH = "leads.db"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36'}
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# ---------------- DATABASE ----------------
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
    cur.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rating INTEGER,
            comments TEXT
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

# ---------------- SCRAPING ----------------
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
        return {"text": text[:4000], "emails": list(set(emails)), "meta_description": meta_desc}
    except Exception:
        return {"text": "", "emails": [], "meta_description": ""}

# ---------------- AI LOGIC ----------------
KEYWORDS = ["contact", "services", "clients", "book", "shop", "portfolio", "products"]

def score_lead(lead):
    score = 0
    if lead.get("email"): score += 40
    if any(k in lead.get("text","").lower() for k in KEYWORDS): score += 30
    if lead.get("meta_description"): score += 20
    if len(lead.get("text","").split()) > 100: score += 10
    return min(score, 100)

def generate_message(lead, template, your_name):
    biz = lead.get("title") or lead.get("domain") or "there"
    msg = template.replace("{business_name}", biz).replace("{your_name}", your_name)
    return msg

# ---------------- UI ----------------
st.set_page_config(page_title="Access 2 — AI Lead Finder", layout="wide")
st.title("🚀 Access 2 — AI Lead Finder (Beta Demo)")
st.caption("Find qualified local leads automatically • Built for small businesses")

init_db()

# ---- Sidebar Menu with Admin Login ----
menu = ["Find Leads"]
if st.sidebar.checkbox("Admin login"):
    password = st.sidebar.text_input("Enter admin password", type="password")
    if password == "Access2Admin123":  # change to your secret password
        menu.append("View Feedback")
    elif password:
        st.sidebar.error("Incorrect password")

choice = st.sidebar.selectbox("Menu", menu)

# ---------------- Find Leads ----------------
if choice == "Find Leads":
    if "search_count" not in st.session_state:
        st.session_state.search_count = 0

    MAX_SEARCHES = 2
    remaining_searches = MAX_SEARCHES - st.session_state.search_count
    st.info(f"🔎 You have **{remaining_searches}** search{'es' if remaining_searches != 1 else ''} left in this session.")

    if st.session_state.search_count >= MAX_SEARCHES:
        st.warning(f"Demo limit reached: You can only run {MAX_SEARCHES} searches per session.")
        st.stop()

    st.markdown("---")
    st.subheader("Step 1 — Enter your search")
    niche = st.text_input("Niche (e.g. dentist, restaurant, marketing agency)")
    city = st.text_input("City (e.g. Cape Town, Johannesburg)")
    limit = st.slider("Number of leads", 5, 30, 10)
    your_name = st.text_input("Your name", "Khumo")

    st.subheader("Step 2 — Customize your outreach message")
    default_template = (
        "Hi {business_name},\n"
        "I'm {your_name}. I help businesses like yours attract more customers using simple AI-driven strategies.\n"
        "Would you be open to a short free audit showing how to boost your leads?\n\n"
        "Best,\n{your_name}"
    )
    template = st.text_area("Message template (use {business_name} and {your_name})", value=default_template, height=160)

    if st.button("🔍 Find Leads"):
        if not niche or not city:
            st.error("Please fill in both fields.")
        else:
            st.session_state.search_count += 1
            st.info("Searching businesses...")
            query = f"{niche} in {city}"
            results = search_google(query, limit=limit)

            if not results:
                st.warning("No results found. Try different keywords.")
            else:
                leads = []
                progress = st.progress(0)
                placeholder = st.empty()
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
                    lead["message"] = generate_message(lead, template, your_name)
                    leads.append(lead)
                    progress.progress((i + 1) / len(results))
                    placeholder.write(f"Processing lead {i+1} of {len(results)}...")
                    time.sleep(0.3)

                save_leads(leads)
                progress.empty()
                placeholder.empty()
                st.success(f"✅ Done! Collected {len(leads)} leads.")
                df = pd.DataFrame(leads)
                st.dataframe(df[["domain", "email", "score"]])
                csv = df.to_csv(index=False)
                st.download_button("📥 Download CSV", csv, "leads.csv", "text/csv")

                st.markdown("### ✉️ Outreach Messages")
                for _, row in df.iterrows():
                    st.markdown(f"**{row['domain']}** — Score {row['score']}")
                    st.code(row["message"], language="text")

    st.markdown("---")
    st.subheader("💬 Feedback (Beta Testers)")
    with st.form("feedback_form"):
        rating = st.slider("How useful was this tool?", 1, 5, 4)
        comments = st.text_area("Any feedback or ideas?", "")
        submitted = st.form_submit_button("Submit Feedback")
        if submitted:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("INSERT INTO feedback (rating, comments) VALUES (?, ?)", (rating, comments))
            conn.commit()
            conn.close()
            st.success("Thanks for your feedback! 🙏")

# ---------------- View Feedback (Admin Only Dashboard) ----------------
elif choice == "View Feedback":
    st.subheader("📋 Tester Feedback Dashboard (Admin Only)")

    try:
        conn = sqlite3.connect(DB_PATH)
        df_feedback = pd.read_sql("SELECT * FROM feedback ORDER BY id DESC", conn)
        conn.close()

        if df_feedback.empty:
            st.info("No feedback yet.")
        else:
            avg_rating = df_feedback["rating"].mean()
            st.metric("Average Rating ⭐", f"{avg_rating:.2f} / 5")

            st.markdown("### 📊 Ratings Distribution")
            rating_counts = df_feedback["rating"].value_counts().sort_index()
            st.bar_chart(rating_counts)

            st.markdown("### 📝 Recent Comments")
            for idx, row in df_feedback.iterrows():
                st.markdown(f"**Rating:** {row['rating']} ⭐ — {row['comments']}")

            csv = df_feedback.to_csv(index=False)
            st.download_button("📥 Download Feedback CSV", csv, "feedback.csv", "text/csv")

    except Exception as e:
        st.error(f"Error loading feedback: {e}")
