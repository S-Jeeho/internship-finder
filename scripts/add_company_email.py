#!/usr/bin/env python3
"""
Utility — view companies in the database and add/update contact emails.

Usage:
    python scripts/add_company_email.py                 # list companies without emails
    python scripts/add_company_email.py --all           # list all companies
    python scripts/add_company_email.py --set 12345678 hr@company.co.uk
    python scripts/add_company_email.py --clear-emails  # wipe all contact emails (re-enrich)
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import load_settings
from src.storage.database import get_connection, init_db
from src.storage.tracker import Tracker


def list_companies(db_path: Path, show_all: bool = False) -> None:
    with get_connection(db_path) as conn:
        if show_all:
            rows = conn.execute(
                "SELECT company_number, company_name, registered_address, contact_email "
                "FROM companies ORDER BY company_name"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT company_number, company_name, registered_address, contact_email "
                "FROM companies WHERE contact_email IS NULL OR contact_email = '' "
                "ORDER BY company_name"
            ).fetchall()

    if not rows:
        print("No companies found." if show_all else "All companies already have contact emails.")
        return

    label = "All companies" if show_all else "Companies missing a contact email"
    print(f"\n{label} ({len(rows)}):\n")
    print(f"{'Number':<12}  {'Email':<30}  Name / Address")
    print("-" * 90)
    for row in rows:
        email = row["contact_email"] or "(none)"
        address = (row["registered_address"] or "")[:40]
        print(f"{row['company_number']:<12}  {email:<30}  {row['company_name']}  |  {address}")


def reset_sent(db_path: Path) -> None:
    """Remove all 'sent' log entries so previously-emailed companies can be re-sent."""
    tracker = Tracker(db_path)
    count = tracker.reset_sent_status()
    print(f"Reset {count} companies to 'pending'. They will be picked up on the next pipeline run.")


def clear_all_emails(db_path: Path) -> None:
    with get_connection(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM companies WHERE contact_email IS NOT NULL"
        ).fetchone()[0]
        conn.execute("UPDATE companies SET contact_email = NULL")
    print(f"Cleared contact emails for {count} companies. Run enrich_companies.py to re-populate.")


def set_email(db_path: Path, company_number: str, email: str) -> None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT company_name FROM companies WHERE company_number = ?",
            (company_number,),
        ).fetchone()

        if row is None:
            print(f"Company {company_number} not found in database.")
            sys.exit(1)

        conn.execute(
            "UPDATE companies SET contact_email = ? WHERE company_number = ?",
            (email, company_number),
        )

    print(f"Updated {row['company_name']} ({company_number}) → {email}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="View companies and add contact emails to the database."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="List all companies, not just those missing emails.",
    )
    parser.add_argument(
        "--clear-emails",
        action="store_true",
        help="Wipe all contact emails so they can be re-enriched from scratch.",
    )
    parser.add_argument(
        "--reset-sent",
        action="store_true",
        help="Clear 'sent' status so companies with new emails can be re-emailed.",
    )
    parser.add_argument(
        "--set",
        nargs=2,
        metavar=("COMPANY_NUMBER", "EMAIL"),
        help="Set the contact email for a company. Example: --set 12345678 hr@company.co.uk",
    )
    args = parser.parse_args()

    try:
        settings = load_settings()
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    init_db(settings.DB_PATH)

    if args.reset_sent:
        reset_sent(settings.DB_PATH)
    elif args.clear_emails:
        clear_all_emails(settings.DB_PATH)
    elif args.set:
        set_email(settings.DB_PATH, args.set[0], args.set[1])
    else:
        list_companies(settings.DB_PATH, show_all=args.all)
        if not args.all:
            print(
                "\nTo add an email, run:\n"
                "  python scripts/add_company_email.py --set <company_number> <email>\n"
                "Example:\n"
                "  python scripts/add_company_email.py --set 12366811 hr@manchestertech.co.uk"
            )


if __name__ == "__main__":
    main()
