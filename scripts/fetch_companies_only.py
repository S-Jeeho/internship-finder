#!/usr/bin/env python3
"""
Standalone script — searches Companies House and saves results to the database
WITHOUT triggering any CV tailoring or email sending.

Searches using biology-specific keywords (biotech, pharma, genomics etc.)
to return genuinely relevant companies rather than just location matches.

Usage:
    python scripts/fetch_companies_only.py
    python scripts/fetch_companies_only.py --max 10
    python scripts/fetch_companies_only.py --keywords "genomics" "therapeutics"
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import load_settings
from config.sic_codes import BIOLOGY_SEARCH_TERMS, DEFAULT_SEARCH_SIC_CODES
from src.companies.companies_house import CompaniesHouseClient
from src.companies.geocoder import Geocoder
from src.storage.database import init_db
from src.storage.tracker import Tracker


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and store biology companies only.")
    parser.add_argument("--max", type=int, default=5,
                        help="Max companies to fetch per search keyword (default: 5).")
    parser.add_argument(
        "--keywords", nargs="+", default=None,
        help="Biology search keywords (default: biotech, pharmaceutical, genomics etc.)."
    )
    parser.add_argument(
        "--sic-codes", nargs="+", default=None, metavar="CODE", help="SIC codes to filter by."
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
    keywords = args.keywords or BIOLOGY_SEARCH_TERMS

    init_db(settings.DB_PATH)
    tracker = Tracker(settings.DB_PATH)
    client = CompaniesHouseClient(settings.COMPANIES_HOUSE_API_KEY)
    geocoder = Geocoder(settings.GOOGLE_MAPS_API_KEY)

    all_companies = []
    seen_numbers = set()

    for keyword in keywords:
        logger.info("Searching for: '%s'", keyword)
        companies = client.search_companies_by_sic(
            sic_codes, location_term=keyword, max_results=args.max
        )
        for c in companies:
            if c.company_number not in seen_numbers:
                seen_numbers.add(c.company_number)
                all_companies.append(c)

    if geocoder.enabled:
        all_companies = geocoder.enrich_with_distance(all_companies)
        all_companies = Geocoder.filter_by_distance(all_companies, settings.MAX_DISTANCE_KM)

    inserted = tracker.save_companies(all_companies)
    total = tracker.count_companies()

    print(f"\nFetched {len(all_companies)} unique companies — {inserted} newly saved.")
    print(f"Total in database: {total}")
    print("\nResults:")
    for c in all_companies:
        dist = f" ({c.distance_km:.0f} km)" if c.distance_km is not None else ""
        print(f"  {c.company_number}  {c.company_name}{dist}  —  {c.registered_address[:60]}")


if __name__ == "__main__":
    main()
