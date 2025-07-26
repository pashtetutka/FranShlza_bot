import sqlite3
from pathlib import Path
from bot.config import settings

_SQL_CREATE = """
CREATE TABLE IF NOT EXISTS users(
    tg_id       INTEGER PRIMARY KEY,
    ref_code    TEXT,
    referrer_id INTEGER,
    wallet      TEXT,
    role        TEXT DEFAULT 'unregistered',
    inst_nick   TEXT,
    price_offer INTEGER,
    paid        INTEGER DEFAULT 0,
    subs_ok     INTEGER DEFAULT 0,
    joined_at   TEXT
);
CREATE TABLE IF NOT EXISTS payments(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id       INTEGER,
    amount      INTEGER,
    paid_at     TEXT
);
"""

_DB_PATH = Path(settings.DB_PATH)

def get_conn():
    con = sqlite3.connect(_DB_PATH)
    con.executescript(_SQL_CREATE)
    return con
