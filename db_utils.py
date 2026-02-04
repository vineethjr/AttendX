import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "db", "attendance.db")
DB_PATH = os.getenv("ATTENDX_DB_PATH", DEFAULT_DB_PATH)


def get_db_connection(timeout=10, row_factory=sqlite3.Row):
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    if row_factory is not None:
        conn.row_factory = row_factory
    return conn
