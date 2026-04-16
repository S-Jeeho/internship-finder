"""
Integration-style tests for src/pipeline/runner.py.

All external dependencies (Companies House API, Claude, Gmail, geocoder)
are mocked. We verify the orchestration logic — correct ordering, error
handling, tracker state, and dry-run behaviour.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.companies.models import Company
from src.pipeline.runner import PipelineResult, run
from src.storage.database import init_db
from src.storage.tracker import Tracker


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_settings(tmp_path: Path, db_path: Path) -> MagicMock:
    s = MagicMock()
    s.DB_PATH = db_path
    s.ANTHROPIC_API_KEY = "fake_anthropic"
    s.COMPANIES_HOUSE_API_KEY = "fake_ch"
    s.GMAIL_CREDENTIALS_PATH = tmp_path / "creds.json"
    s.GMAIL_TOKEN_PATH = tmp_path / "token.json"
    s.GMAIL_SENDER_ADDRESS = "me@gmail.com"
    s.GOOGLE_MAPS_API_KEY = ""  # disable geocoder
    s.MAX_DISTANCE_KM = 80.0
    s.MAX_COMPANIES_PER_RUN = 10
    s.BASE_CV_PATH = tmp_path / "cv_base.md"
    (tmp_path / "cv_base.md").write_text("# Jane Doe\n\n## Skills\n- Python")
    return s


def _make_company(number: str = "12345678", with_email: bool = True) -> Company:
    return Company(
        company_number=number,
        company_name=f"Bio Co {number}",
        company_type="ltd",
        sic_codes=["72110"],
        contact_email=f"hr@company{number}.co.uk" if with_email else None,
    )


BASE_CV = "# Jane Doe\n\n## Skills\n- Python"


# ── Test: dry run ─────────────────────────────────────────────────────────────

def test_dry_run_does_not_call_gmail(tmp_path: Path, tmp_db: Path) -> None:
    settings = _make_settings(tmp_path, tmp_db)
    company = _make_company()

    with (
        patch("src.pipeline.runner.CompaniesHouseClient") as MockCH,
        patch("src.pipeline.runner.Geocoder") as MockGeo,
        patch("src.pipeline.runner.CVTailor") as MockTailor,
        patch("src.pipeline.runner.get_gmail_service") as mock_auth,
        patch("src.pipeline.runner.send_application") as mock_send,
        patch("src.pipeline.runner.build_pdf") as mock_pdf,
    ):
        MockCH.return_value.search_companies_by_sic.return_value = [company]
        MockGeo.return_value.enabled = False
        MockTailor.return_value.tailor_for_company.return_value = BASE_CV
        mock_pdf.return_value = tmp_path / "cv_12345678.pdf"
        (tmp_path / "cv_12345678.pdf").write_bytes(b"%PDF-fake")
        mock_send.return_value = "dry_run"

        result = run(settings, dry_run=True, applicant_name="Jane Doe")

        mock_auth.assert_not_called()  # no OAuth on dry run
        assert result.dry_run_count == 1
        assert result.sent == 0


def test_live_run_calls_gmail_and_marks_sent(tmp_path: Path, tmp_db: Path) -> None:
    settings = _make_settings(tmp_path, tmp_db)
    company = _make_company()

    with (
        patch("src.pipeline.runner.CompaniesHouseClient") as MockCH,
        patch("src.pipeline.runner.Geocoder") as MockGeo,
        patch("src.pipeline.runner.CVTailor") as MockTailor,
        patch("src.pipeline.runner.get_gmail_service") as mock_auth,
        patch("src.pipeline.runner.send_application") as mock_send,
        patch("src.pipeline.runner.build_pdf") as mock_pdf,
    ):
        pdf_path = tmp_path / "cv_12345678.pdf"
        pdf_path.write_bytes(b"%PDF-fake")

        MockCH.return_value.search_companies_by_sic.return_value = [company]
        MockGeo.return_value.enabled = False
        MockTailor.return_value.tailor_for_company.return_value = BASE_CV
        mock_pdf.return_value = pdf_path
        mock_send.return_value = "msg_real123"
        mock_auth.return_value = MagicMock()

        result = run(settings, dry_run=False, applicant_name="Jane Doe")

        assert result.sent == 1
        assert result.failed == 0
        tracker = Tracker(tmp_db)
        assert tracker.has_been_emailed("12345678")


def test_company_without_email_is_skipped(tmp_path: Path, tmp_db: Path) -> None:
    settings = _make_settings(tmp_path, tmp_db)
    company = _make_company(with_email=False)

    with (
        patch("src.pipeline.runner.CompaniesHouseClient") as MockCH,
        patch("src.pipeline.runner.Geocoder") as MockGeo,
        patch("src.pipeline.runner.CVTailor"),
        patch("src.pipeline.runner.get_gmail_service"),
        patch("src.pipeline.runner.send_application") as mock_send,
        patch("src.pipeline.runner.build_pdf"),
    ):
        MockCH.return_value.search_companies_by_sic.return_value = [company]
        MockGeo.return_value.enabled = False

        result = run(settings, dry_run=True, applicant_name="Jane Doe")

        assert result.skipped == 1
        mock_send.assert_not_called()


def test_tailoring_error_marks_company_failed(tmp_path: Path, tmp_db: Path) -> None:
    from src.cv.tailorer import CVTailoringError

    settings = _make_settings(tmp_path, tmp_db)
    company = _make_company()

    dummy_pdf = tmp_path / "cv.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4")

    with (
        patch("src.pipeline.runner.CompaniesHouseClient") as MockCH,
        patch("src.pipeline.runner.Geocoder") as MockGeo,
        patch("src.pipeline.runner.CVTailor") as MockTailor,
        patch("src.pipeline.runner.build_pdf", return_value=dummy_pdf),
        patch("src.pipeline.runner.get_gmail_service"),
        patch("src.pipeline.runner.send_application", return_value="msg_fallback") as mock_send,
    ):
        MockCH.return_value.search_companies_by_sic.return_value = [company]
        MockGeo.return_value.enabled = False
        MockTailor.return_value.tailor_for_company.side_effect = CVTailoringError("API down")
        MockTailor.return_value.base_cv = "# Fallback CV\n\nBase content."

        result = run(settings, dry_run=True, applicant_name="Jane Doe")

        # Tailoring error falls back to base CV — email is still sent
        assert result.dry_run_count == 1
        assert result.failed == 0
        mock_send.assert_called_once()


def test_already_emailed_company_is_not_processed_again(tmp_path: Path, tmp_db: Path) -> None:
    settings = _make_settings(tmp_path, tmp_db)
    company = _make_company()

    # Pre-populate DB as already sent
    init_db(tmp_db)
    tracker = Tracker(tmp_db)
    tracker.save_companies([company])
    tracker.mark_emailed(company.company_number, "sent")

    with (
        patch("src.pipeline.runner.CompaniesHouseClient") as MockCH,
        patch("src.pipeline.runner.Geocoder") as MockGeo,
        patch("src.pipeline.runner.CVTailor"),
        patch("src.pipeline.runner.get_gmail_service"),
        patch("src.pipeline.runner.send_application") as mock_send,
    ):
        MockCH.return_value.search_companies_by_sic.return_value = [company]
        MockGeo.return_value.enabled = False

        result = run(settings, dry_run=True, applicant_name="Jane Doe")

        mock_send.assert_not_called()
        assert result.sent == 0
        assert result.dry_run_count == 0


def test_empty_company_list_returns_zeroes(tmp_path: Path, tmp_db: Path) -> None:
    settings = _make_settings(tmp_path, tmp_db)

    with (
        patch("src.pipeline.runner.CompaniesHouseClient") as MockCH,
        patch("src.pipeline.runner.Geocoder") as MockGeo,
        patch("src.pipeline.runner.CVTailor"),
        patch("src.pipeline.runner.get_gmail_service"),
    ):
        MockCH.return_value.search_companies_by_sic.return_value = []
        MockGeo.return_value.enabled = False

        result = run(settings, dry_run=True)
        assert result.sent == 0
        assert result.failed == 0
        assert result.skipped == 0
