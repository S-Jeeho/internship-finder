"""Tests for src/storage/database.py"""

import sqlite3
from pathlib import Path

import pytest

from src.storage.database import get_connection, init_db


def test_init_db_creates_file(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    assert not db_path.exists()
    init_db(db_path)
    assert db_path.exists()


def test_init_db_creates_companies_table(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='companies'"
        ).fetchone()
    assert row is not None


def test_init_db_creates_email_log_table(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='email_log'"
        ).fetchone()
    assert row is not None


def test_init_db_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)
    init_db(db_path)  # Should not raise
    with get_connection(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    assert count == 0


def test_get_connection_commits_on_success(tmp_db: Path) -> None:
    with get_connection(tmp_db) as conn:
        conn.execute(
            "INSERT INTO companies (company_number, company_name) VALUES ('00000001', 'Test Co')"
        )
    with get_connection(tmp_db) as conn:
        row = conn.execute(
            "SELECT company_name FROM companies WHERE company_number = '00000001'"
        ).fetchone()
    assert row["company_name"] == "Test Co"


def test_get_connection_rolls_back_on_exception(tmp_db: Path) -> None:
    with pytest.raises(ValueError):
        with get_connection(tmp_db) as conn:
            conn.execute(
                "INSERT INTO companies (company_number, company_name) VALUES ('00000002', 'Rollback Co')"
            )
            raise ValueError("Simulated error")

    with get_connection(tmp_db) as conn:
        row = conn.execute(
            "SELECT * FROM companies WHERE company_number = '00000002'"
        ).fetchone()
    assert row is None


def test_get_connection_row_factory(tmp_db: Path) -> None:
    with get_connection(tmp_db) as conn:
        conn.execute(
            "INSERT INTO companies (company_number, company_name) VALUES ('00000003', 'Named Row Co')"
        )
    with get_connection(tmp_db) as conn:
        row = conn.execute(
            "SELECT company_number, company_name FROM companies WHERE company_number = '00000003'"
        ).fetchone()
    # sqlite3.Row allows column access by name
    assert row["company_name"] == "Named Row Co"
    assert row["company_number"] == "00000003"
