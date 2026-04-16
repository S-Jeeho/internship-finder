"""
Pipeline orchestrator — ties every module together.

Execution order:
  1. Load config and initialise database
  2. Fetch companies from Companies House (filtered by SIC codes)
  3. Optionally geocode and filter by distance from Manchester
  4. Save new companies to SQLite
  5. Retrieve uncontacted companies from tracker
  6. For each company:
       a. Tailor CV with Claude
       b. Build PDF
       c. Send email via Gmail
       d. Mark result in tracker
       e. Delete temp PDF
  7. Log summary

The dry_run flag stops before any email is sent but exercises every step up
to and including PDF generation, so you can verify the output before committing.
"""

import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import Settings
from config.sic_codes import DEFAULT_SEARCH_SIC_CODES
from src.companies.companies_house import CompaniesHouseClient
from src.companies.geocoder import Geocoder
from src.companies.models import Company
from src.cv.pdf_builder import build_pdf
from src.cv.tailorer import CVTailor, CVTailoringError
from src.email.gmail_auth import get_gmail_service
from src.email.gmail_sender import EmailSendError, send_application
from src.storage.database import init_db
from src.storage.tracker import Tracker

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    sent: int = 0
    failed: int = 0
    skipped: int = 0
    dry_run_count: int = 0
    errors: list[str] = field(default_factory=list)


def run(
    settings: Settings,
    sic_codes: Optional[list[str]] = None,
    applicant_name: str = "The Applicant",
    max_companies: Optional[int] = None,
    dry_run: bool = False,
    location_term: str = "Manchester",
) -> PipelineResult:
    """
    Run the full internship-finder pipeline.

    Args:
        settings: Validated Settings object from config.settings.
        sic_codes: SIC codes to search (defaults to DEFAULT_SEARCH_SIC_CODES).
        applicant_name: Full name for the email body signature.
        max_companies: Cap on companies to process in this run (overrides config).
        dry_run: If True, skips sending emails and deletes temp PDFs.
        location_term: Location keyword for Companies House search.

    Returns:
        PipelineResult with counts of sent, failed, skipped, and dry-run emails.
    """
    sic_codes = sic_codes or DEFAULT_SEARCH_SIC_CODES
    cap = max_companies if max_companies is not None else settings.MAX_COMPANIES_PER_RUN or None
    result = PipelineResult()

    # ── 1. Initialise storage ─────────────────────────────────────────────────
    init_db(settings.DB_PATH)
    tracker = Tracker(settings.DB_PATH)
    logger.info("Database ready at %s", settings.DB_PATH)

    # ── 2. Fetch companies ────────────────────────────────────────────────────
    ch_client = CompaniesHouseClient(settings.COMPANIES_HOUSE_API_KEY)
    companies = ch_client.search_companies_by_sic(
        sic_codes=sic_codes,
        location_term=location_term,
        max_results=cap,
    )
    logger.info("Fetched %d companies from Companies House", len(companies))

    # ── 3. Geocode + filter by distance (optional) ────────────────────────────
    geocoder = Geocoder(settings.GOOGLE_MAPS_API_KEY)
    if geocoder.enabled:
        companies = geocoder.enrich_with_distance(companies)
        companies = Geocoder.filter_by_distance(companies, settings.MAX_DISTANCE_KM)
        logger.info("%d companies within %.0f km", len(companies), settings.MAX_DISTANCE_KM)

    # ── 4. Save new companies to tracker ─────────────────────────────────────
    tracker.save_companies(companies)

    # ── 5. Get uncontacted companies ──────────────────────────────────────────
    uncontacted = tracker.get_uncontacted_companies()
    if cap:
        uncontacted = uncontacted[:cap]
    logger.info("Processing %d uncontacted companies", len(uncontacted))

    if not uncontacted:
        logger.info("Nothing to do — all known companies have been contacted")
        return result

    # ── 6. Initialise shared resources ───────────────────────────────────────
    tailor = CVTailor(
        api_key=settings.ANTHROPIC_API_KEY,
        base_cv_path=settings.BASE_CV_PATH,
    )

    gmail_service = None
    if not dry_run:
        gmail_service = get_gmail_service(
            credentials_path=settings.GMAIL_CREDENTIALS_PATH,
            token_path=settings.GMAIL_TOKEN_PATH,
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="internship_cv_"))

    # ── 7. Per-company loop ───────────────────────────────────────────────────
    for company in uncontacted:
        _process_company(
            company=company,
            tailor=tailor,
            gmail_service=gmail_service,
            tracker=tracker,
            temp_dir=temp_dir,
            sender_address=settings.GMAIL_SENDER_ADDRESS,
            applicant_name=applicant_name,
            dry_run=dry_run,
            result=result,
        )

    # ── 8. Summary ────────────────────────────────────────────────────────────
    logger.info(
        "Pipeline complete — sent: %d, dry_run: %d, failed: %d, skipped: %d",
        result.sent,
        result.dry_run_count,
        result.failed,
        result.skipped,
    )
    return result


# ── Per-company helper ────────────────────────────────────────────────────────

def _process_company(
    company: Company,
    tailor: CVTailor,
    gmail_service,
    tracker: Tracker,
    temp_dir: Path,
    sender_address: str,
    applicant_name: str,
    dry_run: bool,
    result: PipelineResult,
) -> None:
    company_label = f"{company.company_name} ({company.company_number})"

    if not company.contact_email:
        logger.warning("Skipping %s — no contact email", company_label)
        tracker.mark_emailed(company.company_number, "skipped", error_message="no contact email")
        result.skipped += 1
        return

    pdf_path: Optional[Path] = None
    try:
        # a. Tailor CV
        tailored_cv = tailor.tailor_for_company(company)

        # b. Build PDF
        pdf_path = build_pdf(
            tailored_cv,
            output_dir=temp_dir,
            filename=f"cv_{company.company_number}",
        )

        # c. Send email
        msg_id = send_application(
            gmail_service=gmail_service,
            company=company,
            pdf_path=pdf_path,
            sender_address=sender_address,
            applicant_name=applicant_name,
            dry_run=dry_run,
        )

        # d. Mark result
        if dry_run:
            tracker.mark_emailed(company.company_number, "dry_run", gmail_message_id=msg_id)
            result.dry_run_count += 1
            logger.info("[DRY RUN] %s — PDF at %s", company_label, pdf_path)
        else:
            tracker.mark_emailed(company.company_number, "sent", gmail_message_id=msg_id)
            result.sent += 1
            logger.info("Sent to %s (msg=%s)", company_label, msg_id)

    except CVTailoringError as exc:
        logger.error("CV tailoring failed for %s: %s", company_label, exc)
        tracker.mark_emailed(company.company_number, "failed", error_message=str(exc))
        result.failed += 1
        result.errors.append(str(exc))

    except (EmailSendError, ValueError) as exc:
        logger.error("Email send failed for %s: %s", company_label, exc)
        tracker.mark_emailed(company.company_number, "failed", error_message=str(exc))
        result.failed += 1
        result.errors.append(str(exc))

    except Exception as exc:
        logger.error("Unexpected error for %s: %s", company_label, exc, exc_info=True)
        tracker.mark_emailed(company.company_number, "failed", error_message=str(exc))
        result.failed += 1
        result.errors.append(str(exc))

    finally:
        # e. Clean up temp PDF (even on dry run — PDF was just for preview)
        if pdf_path and pdf_path.exists() and not dry_run:
            pdf_path.unlink()
