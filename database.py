import sqlite3

DB_PATH = "anon_chat.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            partner_id INTEGER,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT partner_id, status FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        return {"partner_id": row[0], "status": row[1]}
    return None

def set_user(user_id, partner_id=None, status=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, partner_id, status) VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            partner_id = excluded.partner_id,
            status = excluded.status
    """, (user_id, partner_id, status))
    conn.commit()
    conn.close()

def clear_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_waiting():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE status = 'waiting' LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None
