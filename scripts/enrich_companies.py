#!/usr/bin/env python3
"""
Enrichment script — automatically finds contact emails for companies in the
database that have none, using:

  1. Companies House officers API → director names
  2. HTTP domain guessing → company website
  3. Email format guessing → candidate addresses
  4. SMTP verification → confirm address exists (best-effort)

Run this BEFORE run_pipeline.py to maximise the number of companies that
get emailed rather than skipped.

Usage:
    python scripts/enrich_companies.py                   # enrich all missing
    python scripts/enrich_companies.py --max 20          # limit to 20 companies
    python scripts/enrich_companies.py --no-smtp         # skip SMTP verification
    python scripts/enrich_companies.py --dry-run         # print guesses, don't save
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import load_settings
from src.companies.director_fetcher import DirectorFetcher
from src.companies.email_enricher import EmailEnricher
from src.storage.database import get_connection, init_db


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto-find contact emails for companies in the database."
    )
    parser.add_argument("--max", type=int, default=None, help="Max companies to enrich.")
    parser.add_argument(
        "--no-smtp",
        action="store_true",
        help="Skip SMTP verification (faster but less accurate).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print guessed emails but do not save to database.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger(__name__)

    try:
        settings = load_settings()
    except Exception as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    init_db(settings.DB_PATH)

    # Fetch companies with no contact email
    with get_connection(settings.DB_PATH) as conn:
        rows = conn.execute(
            "SELECT company_number, company_name, registered_address "
            "FROM companies "
            "WHERE contact_email IS NULL OR contact_email = '' "
            "ORDER BY company_name"
        ).fetchall()

    companies = [dict(r) for r in rows]
    if args.max:
        companies = companies[: args.max]

    if not companies:
        print("All companies already have contact emails.")
        return

    print(f"\nEnriching {len(companies)} companies...\n")

    director_fetcher = DirectorFetcher(settings.COMPANIES_HOUSE_API_KEY)
    enricher = EmailEnricher(smtp_verify=not args.no_smtp)

    found = 0
    not_found = 0

    for company in companies:
        number = company["company_number"]
        name = company["company_name"]
        address = company.get("registered_address", "")

        directors = director_fetcher.get_directors(number)
        email = enricher.find_email(name, directors, address)

        if email:
            found += 1
            if args.dry_run:
                print(f"  [DRY RUN] {name} → {email}")
            else:
                with get_connection(settings.DB_PATH) as conn:
                    conn.execute(
                        "UPDATE companies SET contact_email = ? WHERE company_number = ?",
                        (email, number),
                    )
                print(f"  FOUND  {name} → {email}")
        else:
            not_found += 1
            print(f"  NONE   {name}")

    print(f"\nDone — found: {found}, not found: {not_found}")
    if not args.dry_run and found:
        print(f"\n{found} emails saved. Run the pipeline to send applications:")
        print("  python scripts/run_pipeline.py --dry-run --name \"Your Name\"")


if __name__ == "__main__":
    main()
