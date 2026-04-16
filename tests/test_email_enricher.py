"""Tests for src/companies/email_enricher.py — no real HTTP or SMTP calls."""

from unittest.mock import MagicMock, patch

import pytest

from src.companies.director_fetcher import Director
from src.companies.email_enricher import (
    EmailEnricher,
    _build_candidates,
    _name_to_slug,
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
    import requests as req
    enricher = EmailEnricher(smtp_verify=False)
    mock_500 = MagicMock()
    mock_500.status_code = 500

    with patch("src.companies.email_enricher.requests.head", return_value=mock_500):
        domain = enricher._guess_domain("Bad Server Ltd")

    assert domain is None


# ── EmailEnricher.find_email ──────────────────────────────────────────────────

def test_find_email_returns_fallback_without_smtp() -> None:
    enricher = EmailEnricher(smtp_verify=False)
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("src.companies.email_enricher.requests.head", return_value=mock_resp):
        email = enricher.find_email("BioTech Ltd", directors=[])

    assert email is not None
    assert "@" in email


def test_find_email_prefers_info_as_fallback() -> None:
    enricher = EmailEnricher(smtp_verify=False)
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("src.companies.email_enricher.requests.head", return_value=mock_resp):
        email = enricher.find_email("BioTech Ltd", directors=[])

    assert email is not None
    assert email.startswith("info@")


def test_find_email_uses_smtp_verified_result() -> None:
    enricher = EmailEnricher(smtp_verify=True)
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    director = Director("Jane Doe", "Jane", "Doe", "director")

    with (
        patch("src.companies.email_enricher.requests.head", return_value=mock_resp),
        patch("src.companies.email_enricher._get_mx_host", return_value="mail.biotech.co.uk"),
        patch("src.companies.email_enricher._smtp_check", return_value=True),
    ):
        email = enricher.find_email("BioTech Ltd", directors=[director])

    assert email is not None
    assert "@" in email


def test_find_email_falls_back_when_smtp_returns_none() -> None:
    enricher = EmailEnricher(smtp_verify=True)
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with (
        patch("src.companies.email_enricher.requests.head", return_value=mock_resp),
        patch("src.companies.email_enricher._get_mx_host", return_value=None),
    ):
        email = enricher.find_email("BioTech Ltd", directors=[])

    assert email is not None  # still returns a fallback
