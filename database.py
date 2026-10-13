import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL не установлен!")


def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            partner_id BIGINT,
            status TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS all_users (
            user_id BIGINT PRIMARY KEY
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


def get_user(user_id):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT partner_id, status FROM users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {"partner_id": row["partner_id"], "status": row["status"]}
    return None


def set_user(user_id, partner_id=None, status=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, partner_id, status) VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET
            partner_id = EXCLUDED.partner_id,
            status = EXCLUDED.status
    """, (user_id, partner_id, status))
    conn.commit()
    cur.close()
    conn.close()


def clear_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
    conn.commit()
    cur.close()
    conn.close()


def get_waiting():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE status = 'waiting' LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def add_all_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO all_users (user_id) VALUES (%s)
        ON CONFLICT (user_id) DO NOTHING
    """, (user_id,))
    conn.commit()
    cur.close()
    conn.close()


def count_all_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM all_users")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else 0


def count_waiting():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE status = 'waiting'")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else 0


def count_chatting():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE status = 'chatting'")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else 0
