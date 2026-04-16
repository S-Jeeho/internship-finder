"""
Company and email-send state tracker.

Single source of truth for pipeline state. Wraps database.py with
domain-level CRUD so the pipeline never writes raw SQL outside this module.

Key invariant: a company in `email_log` with status='sent' will never be
returned by get_uncontacted_companies(), preventing duplicate emails.
"""

import logging
from pathlib import Path
from typing import Optional

from src.companies.models import Company
from src.storage.database import get_connection

logger = logging.getLogger(__name__)


class Tracker:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    # ── Write ─────────────────────────────────────────────────────────────────

    def save_companies(self, companies: list[Company]) -> int:
        """
        Insert new companies, ignore duplicates (INSERT OR IGNORE).
        Returns the number of newly inserted rows.
        """
        inserted = 0
        with get_connection(self.db_path) as conn:
            for company in companies:
                row = company.to_dict()
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO companies (
                        company_number, company_name, company_type, sic_codes,
                        registered_address, contact_email, website,
                        latitude, longitude, distance_km, description, status
                    ) VALUES (
                        :company_number, :company_name, :company_type, :sic_codes,
                        :registered_address, :contact_email, :website,
                        :latitude, :longitude, :distance_km, :description, :status
                    )
                    """,
                    row,
                )
                inserted += cursor.rowcount
        logger.info("Saved %d new companies to database", inserted)
        return inserted

    def mark_emailed(
        self,
        company_number: str,
        status: str,
        gmail_message_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Record the outcome of an email send attempt."""
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO email_log (company_number, status, gmail_message_id, error_message)
                VALUES (?, ?, ?, ?)
                """,
                (company_number, status, gmail_message_id, error_message),
            )
            conn.execute(
                "UPDATE companies SET status = ? WHERE company_number = ?",
                (status, company_number),
            )
        logger.debug(
            "Marked company %s as '%s' (msg_id=%s)", company_number, status, gmail_message_id
        )

    # ── Read ──────────────────────────────────────────────────────────────────

    def get_uncontacted_companies(self) -> list[Company]:
        """
        Return companies that have NOT been successfully emailed yet.

        A company is considered contacted if it has at least one email_log
        row with status='sent'. Failed attempts are retryable.
        """
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT c.*
                FROM companies c
                WHERE c.company_number NOT IN (
                    SELECT company_number FROM email_log WHERE status = 'sent'
                )
                ORDER BY c.created_at ASC
                """
            ).fetchall()
        companies = [Company.from_dict(dict(row)) for row in rows]
        logger.debug("Found %d uncontacted companies", len(companies))
        return companies

    def has_been_emailed(self, company_number: str) -> bool:
        """Return True if a successful email has been recorded for this company."""
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM email_log WHERE company_number = ? AND status = 'sent' LIMIT 1",
                (company_number,),
            ).fetchone()
        return row is not None

    def get_email_log(self) -> list[dict]:
        """Return the full email log as a list of plain dicts."""
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM email_log ORDER BY sent_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def count_companies(self) -> int:
        """Total number of companies stored."""
        with get_connection(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM companies").fetchone()
        return row[0] if row else 0

    def count_sent(self) -> int:
        """Total number of successfully sent emails."""
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM email_log WHERE status = 'sent'"
            ).fetchone()
        return row[0] if row else 0
