import streamlit as st
import requests
import sqlite3
import time

# --- DATABASE SETUP ---
conn = sqlite3.connect("access2_feedback.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        feedback TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# --- SCRAPER FUNCTION (SERPAPI) ---
def scrape_leads(niche, city, api_key):
    query = f"{niche} in {city}"
    url = f"https://serpapi.com/search.json?engine=google_maps&q={query}&type=search&api_key={api_key}"
    results = []
    try:
        res = requests.get(url)
        data = res.json()
        for business in data.get("local_results", []):
            results.append({
                "name": business.get("title"),
                "address": business.get("address"),
                "website": business.get("website"),
                "phone": business.get("phone"),
                "rating": business.get("rating"),
            })
    except Exception as e:
        st.error(f"Error fetching leads: {e}")
    return results

# --- APP UI ---
st.set_page_config(page_title="Access 2 Lead Finder", layout="wide")
st.title("🚀 Access 2 — AI Lead Finder (Beta)")

# --- Sidebar Inputs ---
st.sidebar.header("Search Settings")
niche = st.sidebar.text_input("Business type or niche", "dentists")
city = st.sidebar.text_input("City", "Cape Town")
api_key = st.sidebar.text_input("Your SerpAPI Key", type="password")
outreach_msg = st.sidebar.text_area("Custom Outreach Message Template", 
                                    "Hey {name}, I came across your business and wanted to share how we can help you get more leads through AI.")
search_btn = st.sidebar.button("Find Leads")

# --- Search Functionality ---
if search_btn:
    if not api_key:
        st.warning("Please enter your SerpAPI key first.")
    else:
        with st.spinner("Finding leads..."):
            progress = st.progress(0)
            leads = scrape_leads(niche, city, api_key)
            time.sleep(0.3)
            progress.progress(100)
        st.success(f"✅ Done! Collected {len(leads)} leads.")
        if leads:
            for i, lead in enumerate(leads, 1):
                st.write(f"**{i}. {lead['name']}**")
                st.write(f"📍 {lead.get('address', 'N/A')}")
                if lead.get("phone"):
                    st.write(f"📞 {lead['phone']}")
                if lead.get("website"):
                    st.write(f"🌐 {lead['website']}")
                msg = outreach_msg.replace("{name}", lead["name"])
                st.code(msg, language="markdown")
                st.divider()

# --- Feedback Section ---
st.header("💬 Leave Feedback")
name = st.text_input("Your Name (optional)")
feedback = st.text_area("What do you think of Access 2 so far?")
if st.button("Submit Feedback"):
    if feedback.strip():
        c.execute("INSERT INTO feedback (name, feedback) VALUES (?, ?)", (name, feedback))
        conn.commit()
        st.success("Thanks for your feedback!")
    else:
        st.warning("Please type some feedback first.")

# --- Admin Login ---
st.sidebar.divider()
st.sidebar.subheader("🔒 Admin Login")
admin_pwd = st.sidebar.text_input("Enter Admin Password", type="password")
if admin_pwd == "Access2Admin123":
    st.sidebar.success("Admin logged in ✅")
    show_feedback = st.sidebar.checkbox("View Feedback")
    if show_feedback:
        st.header("📊 User Feedback")
        rows = c.execute("SELECT name, feedback, timestamp FROM feedback ORDER BY timestamp DESC").fetchall()
        if not rows:
            st.info("No feedback yet.")
        else:
            for r in rows:
                st.write(f"**{r[0] or 'Anonymous'}** ({r[2]}): {r[1]}")
else:
    if admin_pwd:
        st.sidebar.error("Incorrect password.")
