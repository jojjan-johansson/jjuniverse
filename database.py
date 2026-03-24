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
    conn.execute('''
        CREATE TABLE IF NOT EXISTS visits (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ip         TEXT,
            path       TEXT,
            user_agent TEXT,
            created    DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS security_events (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            type    TEXT NOT NULL,
            ip      TEXT,
            detail  TEXT,
            created DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS readings_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            spread_type TEXT,
            created     DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS consent_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            ip             TEXT,
            email          TEXT,
            terms_version  TEXT DEFAULT '1.0',
            accepted_terms INTEGER DEFAULT 0,
            accepted_age   INTEGER DEFAULT 0,
            accepted_entertainment INTEGER DEFAULT 0,
            accepted_connectivity  INTEGER DEFAULT 0,
            accepted_withdrawal    INTEGER DEFAULT 0,
            created        DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()


def log_visit(ip: str, path: str, user_agent: str):
    conn = get_db()
    conn.execute(
        "INSERT INTO visits (ip, path, user_agent) VALUES (?, ?, ?)",
        (ip, path, user_agent)
    )
    conn.commit()
    conn.close()


def log_security_event(event_type: str, ip: str, detail: str = ""):
    conn = get_db()
    conn.execute(
        "INSERT INTO security_events (type, ip, detail) VALUES (?, ?, ?)",
        (event_type, ip, detail)
    )
    conn.commit()
    conn.close()


def log_consent(ip: str, email: str = "", accepted_withdrawal: bool = False):
    conn = get_db()
    conn.execute(
        """INSERT INTO consent_log
           (ip, email, accepted_terms, accepted_age, accepted_entertainment,
            accepted_connectivity, accepted_withdrawal)
           VALUES (?, ?, 1, 1, 1, 1, ?)""",
        (ip, email, 1 if accepted_withdrawal else 0)
    )
    conn.commit()
    conn.close()


def log_reading(user_id: int, spread_type: str):
    conn = get_db()
    conn.execute(
        "INSERT INTO readings_log (user_id, spread_type) VALUES (?, ?)",
        (user_id, spread_type)
    )
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
