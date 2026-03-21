import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'users.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    UNIQUE NOT NULL,
            password TEXT    NOT NULL,
            created  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS free_card_draws (
            ip      TEXT NOT NULL,
            drawn   DATE NOT NULL DEFAULT (date('now')),
            PRIMARY KEY (ip, drawn)
        )
    ''')
    conn.commit()
    conn.close()


def can_draw_free_card(ip: str) -> bool:
    """Returnerar True om denna IP inte redan dragit gratis-kort idag."""
    conn = get_db()
    row = conn.execute(
        "SELECT 1 FROM free_card_draws WHERE ip = ? AND drawn = date('now')",
        (ip,)
    ).fetchone()
    conn.close()
    return row is None


def record_free_card_draw(ip: str):
    """Registrerar att denna IP dragit gratis-kort idag."""
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO free_card_draws (ip) VALUES (?)",
        (ip,)
    )
    conn.commit()
    conn.close()
