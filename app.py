import streamlit as st
import pandas as pd
import time
from scraper import scrape_leads
from datetime import datetime

st.set_page_config(page_title="AI Lead Finder", page_icon="🤖", layout="centered")

# --- Admin password from Streamlit secrets ---
ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]

# Sidebar login
st.sidebar.title("Admin Login")
password = st.sidebar.text_input("Enter admin password", type="password")
is_admin = password == ADMIN_PASSWORD

st.title("🔍 AI Lead Finder")
st.write("Find high-quality leads fast using AI-powered business searches.")

query = st.text_input("Search query (e.g., 'dentists in Cape Town')")
num_results = st.slider("Number of leads", 5, 50, 10)
api_key = st.text_input("Enter your SerpAPI key", type="password")

if st.button("Start Search"):
    if not query.strip():
        st.warning("Please enter a search query.")
    elif not api_key.strip():
        st.warning("Please enter your SerpAPI key.")
    else:
        with st.spinner("Collecting leads..."):
            start_time = time.time()
            leads = scrape_leads(query, num_results, api_key)
            duration = time.time() - start_time

        if leads and len(leads) > 0:
            st.success(f"✅ Done! Collected {len(leads)} leads in {duration:.1f}s")
            df = pd.DataFrame(leads)
            st.dataframe(df)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download leads CSV",
                csv,
                f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv"
            )
        else:
            st.error("No leads found. Check your query and API key.")

# --- Admin Dashboard ---
if is_admin:
    st.markdown("---")
    st.header("🧠 Admin Dashboard")
    st.write("You are logged in as admin.")

