"""Tests for src/companies/email_enricher.py — no real HTTP or SMTP calls."""

from unittest.mock import MagicMock, patch

import pytest

from src.companies.director_fetcher import Director
from src.companies.email_enricher import (
    EmailEnricher,
    _build_candidates,
    _extract_emails_from_html,
    _name_to_slug,
    _pick_best_email,
    _smtp_check,
)


# ── _name_to_slug ─────────────────────────────────────────────────────────────

def test_slug_strips_ltd() -> None:
    assert _name_to_slug("BioTech Innovations Ltd") == "biotechinnovations"


def test_slug_strips_limited() -> None:
    assert _name_to_slug("Pharma Solutions Limited") == "pharmasolutions"


def test_slug_strips_group() -> None:
    assert _name_to_slug("Manchester Bio Group Ltd") == "manchesterbiogroup"


def test_slug_lowercase() -> None:
    assert _name_to_slug("BIOTECH LTD") == "biotech"


def test_slug_removes_special_chars() -> None:
    assert _name_to_slug("Bio & Tech Ltd") == "biotech"


# ── _build_candidates ─────────────────────────────────────────────────────────

def test_candidates_includes_generic_prefixes() -> None:
    candidates = _build_candidates("biotech.co.uk", directors=[])
    assert "info@biotech.co.uk" in candidates
    assert "hr@biotech.co.uk" in candidates
    assert "contact@biotech.co.uk" in candidates


def test_candidates_includes_director_formats() -> None:
    director = Director("John Smith", "John", "Smith", "director")
    candidates = _build_candidates("biotech.co.uk", [director])
    assert "john.smith@biotech.co.uk" in candidates
    assert "john@biotech.co.uk" in candidates
    assert "j.smith@biotech.co.uk" in candidates


def test_candidates_no_duplicates() -> None:
    director = Director("John Smith", "John", "Smith", "director")
    candidates = _build_candidates("biotech.co.uk", [director])
    assert len(candidates) == len(set(candidates))


def test_candidates_generic_before_director() -> None:
    director = Director("John Smith", "John", "Smith", "director")
    candidates = _build_candidates("biotech.co.uk", [director])
    info_idx = candidates.index("info@biotech.co.uk")
    director_idx = candidates.index("john.smith@biotech.co.uk")
    assert info_idx < director_idx


# ── _extract_emails_from_html ─────────────────────────────────────────────────

def test_extract_finds_emails_in_html() -> None:
    html = '<a href="mailto:hello@biotech.co.uk">Contact us</a>'
    emails = _extract_emails_from_html(html, "biotech.co.uk")
    assert "hello@biotech.co.uk" in emails


def test_extract_skips_noreply() -> None:
    html = "Email us at noreply@biotech.co.uk or contact@biotech.co.uk"
    emails = _extract_emails_from_html(html, "biotech.co.uk")
    assert "noreply@biotech.co.uk" not in emails
    assert "contact@biotech.co.uk" in emails


def test_extract_deduplicates() -> None:
    html = "info@biotech.co.uk and info@biotech.co.uk again"
    emails = _extract_emails_from_html(html, "biotech.co.uk")
    assert emails.count("info@biotech.co.uk") == 1


# ── _pick_best_email ──────────────────────────────────────────────────────────

def test_pick_best_prefers_careers() -> None:
    emails = ["info@co.uk", "careers@co.uk", "sales@co.uk"]
    assert _pick_best_email(emails) == "careers@co.uk"


def test_pick_best_prefers_hr_over_info() -> None:
    emails = ["info@co.uk", "hr@co.uk"]
    assert _pick_best_email(emails) == "hr@co.uk"


def test_pick_best_falls_back_to_first() -> None:
    emails = ["sales@co.uk", "billing@co.uk"]
    assert _pick_best_email(emails) == "sales@co.uk"


# ── EmailEnricher._guess_domain ───────────────────────────────────────────────

def test_guess_domain_returns_working_domain() -> None:
    enricher = EmailEnricher(smtp_verify=False)
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("src.companies.email_enricher.requests.head", return_value=mock_resp):
        domain = enricher._guess_domain("BioTech Innovations Ltd")

    assert domain is not None
    assert "biotech" in domain


def test_guess_domain_returns_none_when_all_fail() -> None:
    import requests as req
    enricher = EmailEnricher(smtp_verify=False)

    with patch("src.companies.email_enricher.requests.head", side_effect=req.RequestException):
        domain = enricher._guess_domain("Totally Unknown Company Ltd")

    assert domain is None


def test_guess_domain_skips_500_responses() -> None:
    enricher = EmailEnricher(smtp_verify=False)
    mock_500 = MagicMock()
    mock_500.status_code = 500

    with patch("src.companies.email_enricher.requests.head", return_value=mock_500):
        domain = enricher._guess_domain("Bad Server Ltd")

    assert domain is None


# ── EmailEnricher.find_email ──────────────────────────────────────────────────

def _mock_head_ok() -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    return r


def _mock_get_with_email(email: str) -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.text = f'<a href="mailto:{email}">Contact</a>'
    return r


def test_find_email_returns_scraped_email() -> None:
    enricher = EmailEnricher(smtp_verify=False)

    with (
        patch("src.companies.email_enricher.requests.head", return_value=_mock_head_ok()),
        patch("src.companies.email_enricher.requests.get",
              return_value=_mock_get_with_email("hello@biotech.co.uk")),
    ):
        email = enricher.find_email("BioTech Ltd", directors=[])

    assert email == "hello@biotech.co.uk"


def test_find_email_returns_none_when_no_domain() -> None:
    import requests as req
    enricher = EmailEnricher(smtp_verify=False)

    with patch("src.companies.email_enricher.requests.head", side_effect=req.RequestException):
        email = enricher.find_email("Unknown Corp Ltd", directors=[])

    assert email is None


def test_find_email_returns_none_when_scraping_empty_and_no_smtp() -> None:
    enricher = EmailEnricher(smtp_verify=False)
    empty_page = MagicMock()
    empty_page.status_code = 200
    empty_page.text = "<html><body>No emails here</body></html>"

    with (
        patch("src.companies.email_enricher.requests.head", return_value=_mock_head_ok()),
        patch("src.companies.email_enricher.requests.get", return_value=empty_page),
    ):
        email = enricher.find_email("BioTech Ltd", directors=[])

    assert email is None


def test_find_email_uses_smtp_when_scraping_empty() -> None:
    enricher = EmailEnricher(smtp_verify=True)
    empty_page = MagicMock()
    empty_page.status_code = 200
    empty_page.text = "<html><body>No emails here</body></html>"

    with (
        patch("src.companies.email_enricher.requests.head", return_value=_mock_head_ok()),
        patch("src.companies.email_enricher.requests.get", return_value=empty_page),
        patch("src.companies.email_enricher._get_mx_host", return_value="mail.biotech.co.uk"),
        patch("src.companies.email_enricher._smtp_check", return_value=True),
    ):
        email = enricher.find_email("BioTech Ltd", directors=[])

    assert email is not None
    assert "@" in email


def test_find_email_returns_none_when_smtp_also_fails() -> None:
    enricher = EmailEnricher(smtp_verify=True)
    empty_page = MagicMock()
    empty_page.status_code = 200
    empty_page.text = "<html><body>No emails here</body></html>"

    with (
        patch("src.companies.email_enricher.requests.head", return_value=_mock_head_ok()),
        patch("src.companies.email_enricher.requests.get", return_value=empty_page),
        patch("src.companies.email_enricher._get_mx_host", return_value=None),
    ):
        email = enricher.find_email("BioTech Ltd", directors=[])

    assert email is None
