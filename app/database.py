import os
import sqlite3
import tempfile
from pathlib import Path

from logger import get_logger

log = get_logger(__name__)
DB_PATH = Path(os.getenv("APP_DB_PATH", str(Path(tempfile.gettempdir()) / "sha_app.db")))


def get_connection() -> sqlite3.Connection:
    log.info("DATABASE_CONNECTION_OPENED", extra={"request_id": "none", "db_path": str(DB_PATH)})
    return sqlite3.connect(DB_PATH)


def initialize() -> None:
    with get_connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS records "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL)"
        )
    log.info("DATABASE_INITIALIZED", extra={"request_id": "none"})
