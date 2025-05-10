import os
import sqlite3

def init_db():
    conn = sqlite3.connect(os.path.abspath("db/job_matches.sqlite"))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT UNIQUE,
        job_title TEXT,
        company TEXT,
        location TEXT,
        url TEXT,
        pay TEXT,
        job_type TEXT,
        shift_and_schedule TEXT,
        benefits TEXT,
        description TEXT,
        description_html TEXT,
        match_score INTEGER,
        match_reason TEXT,
        date_scraped TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        likelihood_score INTEGER,
        last_synced TIMESTAMP,
        date_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()
