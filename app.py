import streamlit as st
import pandas as pd
import time
from scraper import scrape_leads
from datetime import datetime

st.set_page_config(page_title="AI Lead Finder", page_icon="🤖", layout="centered")

# --- Admin login ---
try:
    ADMIN_PASSWORD = st.secrets["auth"]["admin_password"]
except Exception:
    ADMIN_PASSWORD = None

st.sidebar.title("Admin Login")
password = st.sidebar.text_input("Enter admin password", type="password")
is_admin = password == ADMIN_PASSWORD

# --- App UI ---
st.title("🔍 AI Lead Finder")
st.write("Find high-quality leads fast using AI-powered business searches.")

query = st.text_input("Search query (e.g., 'dentists in Cape Town')")
num_results = st.slider("Number of leads", 5, 50, 10)
api_key = st.text_input("Enter your SerpAPI key", type="password")
custom_message = st.text_area(
    "Custom Outreach Message (use {Business} placeholder)",
    value="Hi {Business}, I’m reaching out to help you get more leads."
)

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

        if leads:
            st.success(f"✅ Done! Collected {len(leads)} leads in {duration:.1f}s")
            df = pd.DataFrame(leads)
            st.dataframe(df)

            # Outreach messages
            st.markdown("### 📨 Outreach Messages")
            for i, row in df.iterrows():
                message = custom_message.replace("{Business}", row["Business"])
                st.markdown(f"**{row['Business']}** — {row['Website']}")
                st.code(message, language="text")

            # CSV download
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download leads CSV",
                csv,
                f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv"
            )

            # Feedback box
            feedback = st.text_area("Leave feedback about this search")
            if st.button("Submit Feedback"):
                with open("feedback.csv", "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now()},{query},{feedback}\n")
                st.success("Thanks for your feedback!")

        else:
            st.error("No leads found. Check your query and API key.")

# --- Admin dashboard ---
if is_admin:
    st.markdown("---")
    st.header("🧠 Admin Dashboard")
    st.write("You are logged in as admin.")
    try:
        feedback_df = pd.read_csv("feedback.csv", names=["Time", "Query", "Feedback"])
        st.dataframe(feedback_df)
    except FileNotFoundError:
        st.write("No feedback yet.")
