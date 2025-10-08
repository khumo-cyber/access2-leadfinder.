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

