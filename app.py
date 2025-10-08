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
HEADERS = {'User-Agent': 'Mozilla/5.0'}
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
KEYWORDS = ['appointment','book','contact','services','call','clinic','practice','schedule','client','clients','portfolio','projects','store','shop','products','gallery']

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY AUTOINCREMENT,business_name TEXT,domain TEXT,url TEXT,email TEXT,meta_description TEXT,score INTEGER,message TEXT,scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.close()

def duckduckgo_search(query, max_results=10):
    url = 'https://html.duckduckgo.com/html/'
    data = {'q': query}
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
    return links

def fetch_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.text
    except:
        return ''
    return ''

def extract_from_page(html):
    soup = BeautifulSoup(html, 'lxml')
    title = soup.title.string.strip() if soup.title else ''
    meta_desc = ''
    md = soup.find('meta', attrs={'name': 'description'})
    if md and md.get('content'):
        meta_desc = md['content'].strip()
    text = soup.get_text(separator=' ', strip=True)
    emails = set(re.findall(EMAIL_REGEX, text))
    has_contact = any('contact' in a['href'].lower() for a in soup.find_all('a', href=True))
    return {'title': title, 'meta_description': meta_desc, 'text': text, 'emails': list(emails), 'has_contact_page': has_contact}

def to_domain(url):
    parsed = urlparse(url)
    ext = tldextract.extract(parsed.netloc)
    return ext.domain + ('.' + ext.suffix if ext.suffix else '')

def score_lead(lead):
    score = 0
    if lead.get('email'):
        score += 40
    if lead.get('has_contact_page'):
        score += 20
    if len(lead.get('text','').split()) > 150:
        score += 20
    matches = sum(1 for k in KEYWORDS if k in lead.get('text','').lower())
    score += min(matches*5,20)
    return min(score, 100)

def generate_message(lead, your_name='Khumo'):
    biz = lead.get('title') or lead.get('domain') or 'there'
    city = lead.get('city') or ''
    niche = lead.get('niche') or 'business'
    obs = lead.get('meta_description','')[:100]
    lines = [f"Hi {biz},",f"I'm {your_name}. I help {niche} in {city} get more customers without paid ads."]
    if obs:
        lines.append(obs+'.')
    lines.append("Would you like a 3-tip free audit that shows quick wins for getting more leads? Reply and I'll send it — no cost.")
    return " \n".join(lines)

def scrape_leads(niche, city, max_results=10):
    query = f"{niche} in {city}"
    urls = duckduckgo_search(query, max_results=max_results)
    leads = []
    for u in urls:
        info = {'url': u, 'domain': to_domain(u), 'niche': niche, 'city': city}
        html = fetch_page(u)
        if html:
            extracted = extract_from_page(html)
            info.update(extracted)
            info['email'] = extracted['emails'][0] if extracted['emails'] else ''
        else:
            info.update({'title': '', 'meta_description': '', 'text': '', 'emails': [], 'has_contact_page': False, 'email': ''})
        leads.append(info)
    return leads

def save_leads_to_db(leads):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for L in leads:
        cur.execute("INSERT INTO leads (business_name, domain, url, email, meta_description, score, message) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (L.ge
