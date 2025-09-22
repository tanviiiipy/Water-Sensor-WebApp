# backend/db.py
import sqlite3
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "water_guard.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    # Sensors table
    c.execute("""
    CREATE TABLE IF NOT EXISTS sensors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        room TEXT,
        active INTEGER DEFAULT 1,
        data TEXT  -- JSON list of {"date": "...", "usage": number}
    )
    """)
    # Notifications
    c.execute("""
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        msg TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # Settings (single-row)
    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        theme TEXT DEFAULT 'Light',
        refresh INTEGER DEFAULT 15,
        enable_notif INTEGER DEFAULT 1
    )
    """)
    # Challenge checklist (key,value)
    c.execute("""
    CREATE TABLE IF NOT EXISTS checklist (
        name TEXT PRIMARY KEY,
        done INTEGER DEFAULT 0
    )
    """)
    # Game state (single-row)
    c.execute("""
    CREATE TABLE IF NOT EXISTS game_state (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        score INTEGER DEFAULT 0,
        missed INTEGER DEFAULT 0,
        bucket TEXT DEFAULT 'middle',
        drop_col TEXT DEFAULT 'middle'
    )
    """)
    # Game history
    c.execute("""
    CREATE TABLE IF NOT EXISTS game_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        score INTEGER,
        played_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    # Ensure single rows exist
    c.execute("INSERT OR IGNORE INTO settings (id, theme, refresh, enable_notif) VALUES (1, 'Light', 15, 1)")
    # Sample checklist initial rows
    default_tasks = [
        "Fix a leak",
        "Turn off tap while brushing",
        "Take a short shower",
        "Install water-saving aerator",
        "Water plants early morning",
        "Share a water fact"
    ]
    for t in default_tasks:
        c.execute("INSERT OR IGNORE INTO checklist (name, done) VALUES (?, 0)", (t,))
    c.execute("INSERT OR IGNORE INTO game_state (id, score, missed, bucket, drop_col) VALUES (1,0,0,'middle','middle')")
    conn.commit()
    conn.close()

# helper wrappers
def fetchall(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def fetchone(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def execute(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    lastrowid = cur.lastrowid
    conn.close()
    return lastrowid

def update(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    conn.close()
