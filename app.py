import streamlit as st
import pandas as pd
import time
from scraper import scrape_leads  # Your scraper logic
from datetime import datetime

# App configuration
st.set_page_config(page_title="AI Lead Finder", page_icon="🤖", layout="centered")

# --- Authentication ---
ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]  # Securely loaded from secrets.toml

# Sidebar for admin login
st.sidebar.title("Admin Login")
password = st.sidebar.text_input("Enter admin password", type="password")

is_admin = password == ADMIN_PASSWORD

# --- Title ---
st.title("🔍 AI Lead Finder")
st.write("Find high-quality leads fast using AI-powered business searches.")

# --- Lead search section ---
query = st.text_input("What kind of leads are you looking for?", placeholder="Example: digital marketing agencies in Cape Town")
num_results = st.slider("Number of leads to collect", 5, 50, 10)

if st.button("Start Search"):
    if not query.strip():
        st.warning("Please enter a search query.")
    else:
        with st.spinner("Collecting leads..."):
            start_time = time.time()
            leads = scrape_leads(query, num_results)
            duration = time.time() - start_time

        if leads and len(leads) > 0:
            st.success(f"✅ Done! Collected {len(leads)} leads in {duration:.1f}s")

            df = pd.DataFrame(leads)
            st.dataframe(df)

            # Export CSV
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download leads as CSV", csv, f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "text/csv")

            # Feedback section
            st.subheader("💬 Feedback")
            feedback = st.text_area("How was your experience?", placeholder="Share any issues or ideas...")
            if st.button("Submit Feedback"):
                with open("feedback.txt", "a") as f:
                    f.write(f"{datetime.now()} | {feedback}\n")
                st.success("Thanks for your feedback!")
        else:
            st.error("No leads found. Try a different search query.")

# --- Admin Dashboard ---
if is_admin:
    st.markdown("---")
    st.header("🧠 Admin Dashboard")
    st.write("You are logged in as admin.")

    try:
        with open("feedback.txt", "r") as f:
            feedback_data = f.readlines()

        if feedback_data:
            st.subheader("🗣 User Feedback")
            for entry in feedback_data[::-1]:  # Show newest first
                st.write(entry.strip())
        else:
            st.info("No feedback yet.")
    except FileNotFoundError:
        st.info("No feedback file found yet.")
elif password:
    st.error("Incorrect password.")

