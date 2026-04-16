#!/usr/bin/env python3
"""
List all companies in the database, with emailed companies pinned at the top.

Usage:
    python scripts/list_companies.py             # print to terminal
    python scripts/list_companies.py --save      # also save to companies_report.txt
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import load_settings
from src.storage.database import get_connection, init_db


def fetch_all(db_path: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (sent, have_email, no_email) groups."""
    with get_connection(db_path) as conn:
        # Companies that were successfully emailed — most recent send first
        sent_rows = conn.execute("""
            SELECT c.company_number, c.company_name, c.registered_address,
                   c.contact_email, c.sic_codes,
                   MAX(l.sent_at) AS sent_at
            FROM companies c
            JOIN email_log l ON c.company_number = l.company_number
            WHERE l.status = 'sent'
            GROUP BY c.company_number
            ORDER BY sent_at DESC
        """).fetchall()

        # Companies with an email but not yet sent
        queued_rows = conn.execute("""
            SELECT c.company_number, c.company_name, c.registered_address,
                   c.contact_email, c.sic_codes
            FROM companies c
            WHERE c.contact_email IS NOT NULL AND c.contact_email != ''
              AND c.company_number NOT IN (
                  SELECT company_number FROM email_log WHERE status = 'sent'
              )
            ORDER BY c.company_name
        """).fetchall()

        # Companies with no email found yet
        no_email_rows = conn.execute("""
            SELECT c.company_number, c.company_name, c.registered_address,
                   c.contact_email, c.sic_codes
            FROM companies c
            WHERE c.contact_email IS NULL OR c.contact_email = ''
            ORDER BY c.company_name
        """).fetchall()

    return (
        [dict(r) for r in sent_rows],
        [dict(r) for r in queued_rows],
        [dict(r) for r in no_email_rows],
    )


def format_report(sent: list[dict], queued: list[dict], no_email: list[dict]) -> str:
    lines: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines.append("=" * 72)
    lines.append(f"  INTERNSHIP APPLICATIONS REPORT  —  {now}")
    lines.append(f"  Sent: {len(sent)}   Queued: {len(queued)}   No email: {len(no_email)}")
    lines.append("=" * 72)

    # ── Sent ──────────────────────────────────────────────────────────────────
    lines.append("")
    lines.append(f"✔  EMAILED ({len(sent)})")
    lines.append("-" * 72)
    if sent:
        for c in sent:
            sent_at = (c.get("sent_at") or "")[:16].replace("T", " ")
            lines.append(f"  {c['company_name']}")
            lines.append(f"    Email  : {c['contact_email']}")
            lines.append(f"    Sent   : {sent_at}")
            lines.append(f"    Number : {c['company_number']}")
            lines.append("")
    else:
        lines.append("  (none yet)")
        lines.append("")

    # ── Queued ────────────────────────────────────────────────────────────────
    lines.append(f"→  READY TO SEND ({len(queued)})")
    lines.append("-" * 72)
    if queued:
        for c in queued:
            lines.append(f"  {c['company_name']}")
            lines.append(f"    Email  : {c['contact_email']}")
            lines.append(f"    Number : {c['company_number']}")
            lines.append("")
    else:
        lines.append("  (none — run enrich_companies.py to find more)")
        lines.append("")

    # ── No email ──────────────────────────────────────────────────────────────
    lines.append(f"✗  NO EMAIL FOUND ({len(no_email)})")
    lines.append("-" * 72)
    if no_email:
        for c in no_email:
            addr = (c.get("registered_address") or "")[:55]
            lines.append(f"  {c['company_number']}  {c['company_name']}")
            if addr:
                lines.append(f"    {addr}")
        lines.append("")
    else:
        lines.append("  (all companies have emails)")
        lines.append("")

    lines.append("=" * 72)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="List all companies and application status.")
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save the report to data/companies_report.txt as well as printing it.",
    )
    args = parser.parse_args()

    try:
        settings = load_settings()
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    init_db(settings.DB_PATH)
    sent, queued, no_email = fetch_all(settings.DB_PATH)
    report = format_report(sent, queued, no_email)

    print(report)

    if args.save:
        out = Path(__file__).parent.parent / "data" / "companies_report.txt"
        out.write_text(report, encoding="utf-8")
        print(f"Report saved to {out}")


if __name__ == "__main__":
    main()
