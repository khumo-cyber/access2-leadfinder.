import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urlparse
import tldextract
import sqlite3
import pandas as pd

DB_PATH = 'leads.db'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36'
}
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
KEYWORDS = [
    'appointment','book','contact','services','call','clinic','practice','schedule',
    'client','clients','portfolio','projects','store','shop','products','gallery'
]

# === DATABASE INIT ===
def init_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
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
            message TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# === SCRAPER ===
def duckduckgo_search(query, max_results=10, pause=1.0):
    url = 'https://html.duckduckgo.com/html/'
    data = {'q': query}
    try:
        r = requests.post(url, data=data, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, 'lxml')
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('http') and 'duckduckgo.com' not in href:
                if href not in links:
                    links.append(href)
            if len(links) >= max_results:
                break
        time.sleep(pause)
        return links
    except Exception as e:
        print('Search failed:', e)
        return []

def fetch_page(url, pause=0.5):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        time.sleep(pause)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print('fetch_page error', url, e)
    return ''

def extract_from_page(html, url):
    soup = BeautifulSoup(html, 'lxml')
    title = (soup.title.string.strip() if soup.title and soup.title.string else '')
    meta_desc = ''
    md = soup.find('meta', attrs={'name': 'description'})
    if md and md.get('content'):
        meta_desc = md['content'].strip()
    if not meta_desc:
        og = soup.find('meta', attrs={'property': 'og:description'})
        if og and og.get('content'):
            meta_desc = og['content'].strip()

    text = soup.get_text(separator=' ', strip=True)
    emails = set(re.findall(EMAIL_REGEX, text))
    has_contact = any('contact' in a['href'].lower() for a in soup.find_all('a', href=True))
    return {
        'title': title,
        'meta_description': meta_desc,
        'text': text[:4000],
        'emails': list(emails),
        'has_contact_page': has_contact,
    }

def to_domain(url):
    try:
        parsed = urlparse(url)
        ext = tldextract.extract(parsed.netloc)
        return ext.domain + ('.' + ext.suffix if ext.suffix else '')
    except:
        return url

def scrape_leads(niche, city, max_results=20):
    query = f"{niche} in {city}"
    urls = duckduckgo_search(query, max_results=max_results)
    leads = []
    for u in urls:
        info = {
            'url': u,
            'domain': to_domain(u),
            'niche': niche,
            'city': city,
        }
        page_html = fetch_page(u)
        if page_html:
            extracted = extract_from_page(page_html, u)
            info.update(extracted)
            info['email'] = extracted['emails'][0] if extracted['emails'] else ''
        else:
            info.update({'title': '', 'meta_description': '', 'text': '', 'emails': [], 'has_contact_page': False, 'email': ''})
        leads.append(info)
    return leads

# === SCORING + MESSAGE GENERATION ===
def score_lead(lead: dict) -> int:
    score = 0
    if lead.get('email'):
        score += 40
    if lead.get('has_contact_page'):
        score += 20
    wc = len((lead.get('text') or '').split())
    if wc > 150:
        score += 20
    matches = sum(1 for k in KEYWORDS if k in (lead.get('text') or '').lower())
    score += min(matches * 5, 20)
    return min(score, 100)

def generate_message(lead: dict, your_name: str = 'Khumo') -> str:
    biz = lead.get('title') or lead.get('domain') or 'there'
    city = lead.get('city') or ''
    niche = lead.get('niche') or 'business'
    obs = ''

