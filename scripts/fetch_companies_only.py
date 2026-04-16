#!/usr/bin/env python3
"""
Standalone script — searches Companies House and saves results to the database
WITHOUT triggering any CV tailoring or email sending.

Useful for previewing what companies would be found before committing to a run.

Usage:
    python scripts/fetch_companies_only.py
    python scripts/fetch_companies_only.py --max 50 --location Salford
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import load_settings
from config.sic_codes import DEFAULT_SEARCH_SIC_CODES
from src.companies.companies_house import CompaniesHouseClient
from src.companies.geocoder import Geocoder
from src.storage.database import init_db
from src.storage.tracker import Tracker


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and store biology companies only.")
    parser.add_argument("--max", type=int, default=50, help="Max companies to fetch.")
    parser.add_argument("--location", default="Manchester", help="Location search keyword.")
    parser.add_argument(
        "--sic-codes", nargs="+", default=None, metavar="CODE", help="SIC codes to search."
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger = logging.getLogger(__name__)

    try:
        settings = load_settings()
    except Exception as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    sic_codes = args.sic_codes or DEFAULT_SEARCH_SIC_CODES

    init_db(settings.DB_PATH)
    tracker = Tracker(settings.DB_PATH)

    client = CompaniesHouseClient(settings.COMPANIES_HOUSE_API_KEY)
    companies = client.search_companies_by_sic(sic_codes, args.location, max_results=args.max)

    geocoder = Geocoder(settings.GOOGLE_MAPS_API_KEY)
    if geocoder.enabled:
        companies = geocoder.enrich_with_distance(companies)
        companies = Geocoder.filter_by_distance(companies, settings.MAX_DISTANCE_KM)

    inserted = tracker.save_companies(companies)
    total = tracker.count_companies()

    print(f"\nFetched {len(companies)} companies — {inserted} newly saved.")
    print(f"Total in database: {total}")
    print("\nFirst 10 results:")
    for c in companies[:10]:
        dist = f" ({c.distance_km:.0f} km)" if c.distance_km is not None else ""
        print(f"  {c.company_number}  {c.company_name}{dist}  —  {c.registered_address[:60]}")


if __name__ == "__main__":
    main()
