#!/usr/bin/env python3
"""
Main CLI entry point — runs the full internship-finder pipeline.

Usage:
    python scripts/run_pipeline.py --help
    python scripts/run_pipeline.py --dry-run
    python scripts/run_pipeline.py --max-companies 5 --name "Jane Doe"
    python scripts/run_pipeline.py --sic-codes 72110 21200

Before running:
    1. Copy .env.example to .env and fill in all required values.
    2. Place your CV in data/cv_base.md (Markdown format).
    3. Download your Gmail OAuth2 credentials.json from Google Cloud Console.
"""

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Ensure the project root is on sys.path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import load_settings
from config.sic_codes import DEFAULT_SEARCH_SIC_CODES
from src.pipeline.runner import run


def setup_logging(level: str, log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3),
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find biology internships near Manchester and send tailored applications."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tailor CVs and generate PDFs but do NOT send any emails.",
    )
    parser.add_argument(
        "--max-companies",
        type=int,
        default=None,
        metavar="N",
        help="Maximum number of companies to process in this run.",
    )
    parser.add_argument(
        "--name",
        default="The Applicant",
        metavar="FULL_NAME",
        help='Your full name as it should appear in email signatures (e.g. "Jane Doe").',
    )
    parser.add_argument(
        "--sic-codes",
        nargs="+",
        default=None,
        metavar="CODE",
        help=f"SIC codes to search (default: {' '.join(DEFAULT_SEARCH_SIC_CODES)}).",
    )
    parser.add_argument(
        "--location",
        default="Manchester",
        help="Location keyword for the Companies House search (default: Manchester).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO).",
    )
    args = parser.parse_args()

    log_file = Path(__file__).parent.parent / "logs" / "app.log"
    setup_logging(args.log_level, log_file)
    logger = logging.getLogger(__name__)

    try:
        settings = load_settings()
    except Exception as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    if args.dry_run:
        logger.info("=== DRY RUN MODE — no emails will be sent ===")

    result = run(
        settings=settings,
        sic_codes=args.sic_codes,
        applicant_name=args.name,
        max_companies=args.max_companies,
        dry_run=args.dry_run,
        location_term=args.location,
    )

    print(
        f"\nDone — sent: {result.sent}, dry_run: {result.dry_run_count}, "
        f"failed: {result.failed}, skipped: {result.skipped}"
    )
    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for err in result.errors:
            print(f"  • {err}")


if __name__ == "__main__":
    main()
