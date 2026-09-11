import sqlite3

DB = "mod.db"


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS members (
            chat_id INTEGER,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            warns INTEGER DEFAULT 0,
            reps INTEGER DEFAULT 0,
            rank TEXT DEFAULT 'Участник',
            PRIMARY KEY (chat_id, user_id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            admin_id INTEGER,
            target_id INTEGER,
            action TEXT,
            reason TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def get_member(chat_id, user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE chat_id = ? AND user_id = ?", (chat_id, user_id))
    row = c.fetchone()
    conn.close()
    return row


def add_member(chat_id, user_id, username, first_name):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        INSERT OR IGNORE INTO members (chat_id, user_id, username, first_name)
        VALUES (?, ?, ?, ?)
    """, (chat_id, user_id, username, first_name))
    conn.commit()
    conn.close()


def add_warn(chat_id, user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "UPDATE members SET warns = warns + 1 WHERE chat_id = ? AND user_id = ?",
        (chat_id, user_id)
    )
    conn.commit()
    conn.close()


def reset_warns(chat_id, user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "UPDATE members SET warns = 0 WHERE chat_id = ? AND user_id = ?",
        (chat_id, user_id)
    )
    conn.commit()
    conn.close()


def add_rep(chat_id, user_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "UPDATE members SET reps = reps + 1 WHERE chat_id = ? AND user_id = ?",
        (chat_id, user_id)
    )
    conn.commit()
    conn.close()


def set_rank(chat_id, user_id, rank):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "UPDATE members SET rank = ? WHERE chat_id = ? AND user_id = ?",
        (rank, chat_id, user_id)
    )
    conn.commit()
    conn.close()


def add_log(chat_id, admin_id, target_id, action, reason=""):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO logs (chat_id, admin_id, target_id, action, reason)
        VALUES (?, ?, ?, ?, ?)
    """, (chat_id, admin_id, target_id, action, reason))
    conn.commit()
    conn.close()


def get_logs(chat_id, limit=20):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT admin_id, target_id, action, reason, created_at
        FROM logs WHERE chat_id = ?
        ORDER BY created_at DESC LIMIT ?
    """, (chat_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows


def get_top_reps(chat_id, limit=10):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT first_name, reps FROM members
        WHERE chat_id = ? ORDER BY reps DESC LIMIT ?
    """, (chat_id, limit))
    rows = c.fetchall()
    conn.close()
    return rows


def get_all_admins(chat_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT user_id, first_name, rank FROM members
        WHERE chat_id = ? AND rank != 'Участник'
        ORDER BY rank
    """, (chat_id,))
    rows = c.fetchall()
    conn.close()
    return rows
