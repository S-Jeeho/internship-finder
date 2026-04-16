"""
SQLite connection manager and schema initialisation.

Creates two tables on first run (idempotent via IF NOT EXISTS):
  - companies  : one row per discovered company
  - email_log  : one row per send attempt (success or failure)

Usage:
    from src.storage.database import get_connection
    with get_connection(db_path) as conn:
        conn.execute("SELECT * FROM companies")
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    company_number      TEXT PRIMARY KEY,
    company_name        TEXT NOT NULL,
    company_type        TEXT,
    sic_codes           TEXT,
    registered_address  TEXT,
    contact_email       TEXT,
    website             TEXT,
    latitude            REAL,
    longitude           REAL,
    distance_km         REAL,
    description         TEXT,
    status              TEXT DEFAULT 'new',
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS email_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company_number  TEXT NOT NULL REFERENCES companies(company_number),
    sent_at         TEXT DEFAULT (datetime('now')),
    status          TEXT NOT NULL,   -- 'sent' | 'failed' | 'dry_run'
    gmail_message_id TEXT,
    error_message   TEXT
);
"""


def init_db(db_path: Path) -> None:
    """Create the database file and tables if they do not exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()
    logger.debug("Database initialised at %s", db_path)


@contextmanager
def get_connection(db_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager that yields a SQLite connection with row_factory set.

    Commits on clean exit, rolls back on exception.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
