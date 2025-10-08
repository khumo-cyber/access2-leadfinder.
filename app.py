import streamlit as st
import pandas as pd
import sqlite3
from scraper import scrape_leads
from ai_module import score_lead, generate_message
from db_init import init_db

DB_PATH = 'leads.db'

# === ADMIN MODE ===
if st.sidebar.checkbox("Admin login"):
    password = st.sidebar.text_input("Enter admin password", type="password")
    if password == "YourPasswordHere":  # <-- change this to your secure password
        st.title("🔒 Admin Dashboard")

        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql('SELECT * FROM leads', conn)
            conn.close()
        except Exception as e:
            st.error(f"Error loading database: {e}")
            st.stop()

        if df.empty:
            st.warning("No leads found in the database yet.")
        else:
            st.dataframe(df)

        st.stop()  # stop the rest of the app from loading for admin view

# === MAIN APP ===
def save_leads_to_db(leads, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for L in leads:
        cur.execute(
            "INSERT INTO leads (business_name, domain, url, email, meta_description, score, message) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                L.get('title') or '',
                L.get('domain') or '',
                L.get('url') or '',
                L.get('email') or '',
                L.get('meta_description') or '',
                L.get('score') or 0,
                L.get('message') or '',
            )
        )
    conn.commit()
    conn.close()

st.set_page_config(page_title='Access 2 — Free Lead Finder', layout='wide')
st.title('Access 2 — Free Lead Finder (MVP)')
st.write('Type a niche and city, find local leads, get a score and short outreach message. Fully free.')

with st.sidebar:
    st.header('Search')
    niche = st.text_input('Niche (e.g. dentist, marketing agency)')
    city = st.text_input('City (e.g. Cape Town)')
    num = st.slider('How many search results to fetch', 5, 30, 10)
    your_name = st.text_input('Your name (for messages)', 'Khumo')
    run = st.button('Find leads')

if run:
    if not niche or not city:
        st.error('Please enter both niche and city.')
    else:
        init_db()  # ensure DB exists
        with st.spinner('Searching and scraping — this may take a minute...'):
            leads = scrape_leads(niche, city, max_results=num)
            processed = []
            for L in leads:
                sc = score_lead(L)
                msg = generate_message(L, your_name=your_name)
                L['score'] = sc
                L['message'] = msg
                processed.append(L)
            save_leads_to_db(processed)

        df = pd.DataFrame(processed)
        if df.empty:
            st.warning('No leads found. Try increasing results or changing query.')
        else:
            st.subheader('Leads found')
            st.dataframe(df[['domain','url','email','score']].sort_values('score', ascending=False))
            csv = df.to_csv(index=False)
            st.download_button('Download CSV', csv, file_name='leads.csv', mime='text/csv')
            st.markdown('### Messages (copy & paste to send manually)')
            for i, row in df.sort_values('score', ascending=False).iterrows():
                st.markdown(f"**{row.get('domain','')}** — score: {row.get('score',0)}")
                st.code(row.get('message',''), language='text')

try:
    conn = sqlite3.connect(DB_PATH)
    total = pd.read_sql('SELECT COUNT(*) as c FROM leads', conn)['c'][0]
    conn.close()
    st.sidebar.markdown(f"**Leads saved in DB:** {total}")
except Exception:
    pass

