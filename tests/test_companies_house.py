"""Tests for src/companies/companies_house.py — all HTTP calls are mocked."""

from unittest.mock import MagicMock, patch

import pytest

from src.companies.companies_house import CompaniesHouseClient, CompaniesHouseError


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_search_response(company_numbers: list[str], total: int | None = None) -> dict:
    """Build a fake Companies House search response."""
    return {
        "total_results": total if total is not None else len(company_numbers),
        "items": [{"company_number": cn} for cn in company_numbers],
    }


def _make_profile(
    company_number: str,
    company_name: str,
    sic_codes: list[str],
    status: str = "active",
) -> dict:
    return {
        "company_number": company_number,
        "company_name": company_name,
        "type": "ltd",
        "company_status": status,
        "sic_codes": [{"sic_code": c} for c in sic_codes],
        "registered_office_address": {
            "address_line_1": "1 Science Park",
            "locality": "Manchester",
            "postal_code": "M1 1AA",
        },
    }


@pytest.fixture
def client() -> CompaniesHouseClient:
    return CompaniesHouseClient(api_key="test_key", rate_limit_sleep=0)


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_search_returns_matching_companies(client: CompaniesHouseClient) -> None:
    search_resp = _make_search_response(["11111111", "22222222"])
    profile_biotech = _make_profile("11111111", "BioTech Ltd", ["72110"])
    profile_pharma = _make_profile("22222222", "Pharma Co", ["21200"])

    mock_session = MagicMock()
    mock_session.get.side_effect = [
        _mock_response(search_resp),
        _mock_response(profile_biotech),
        _mock_response(profile_pharma),
        _mock_response({"total_results": 2, "items": []}),  # empty next page
    ]
    client._session = mock_session

    companies = client.search_companies_by_sic(["72110", "21200"], location_term="Manchester")
    assert len(companies) == 2
    assert companies[0].company_number == "11111111"
    assert companies[1].company_number == "22222222"


def test_search_filters_out_non_matching_sic(client: CompaniesHouseClient) -> None:
    search_resp = _make_search_response(["33333333"])
    profile_unrelated = _make_profile("33333333", "IT Consulting Ltd", ["62010"])

    mock_session = MagicMock()
    mock_session.get.side_effect = [
        _mock_response(search_resp),
        _mock_response(profile_unrelated),
        _mock_response({"total_results": 1, "items": []}),
    ]
    client._session = mock_session

    companies = client.search_companies_by_sic(["72110"], location_term="Manchester")
    assert len(companies) == 0


def test_search_respects_max_results(client: CompaniesHouseClient) -> None:
    search_resp = _make_search_response(["11111111", "22222222", "33333333"], total=3)
    p1 = _make_profile("11111111", "Bio A", ["72110"])
    p2 = _make_profile("22222222", "Bio B", ["72110"])
    p3 = _make_profile("33333333", "Bio C", ["72110"])

    mock_session = MagicMock()
    mock_session.get.side_effect = [
        _mock_response(search_resp),
        _mock_response(p1),
        _mock_response(p2),
        # p3 should never be fetched because max_results=2
    ]
    client._session = mock_session

    companies = client.search_companies_by_sic(["72110"], max_results=2)
    assert len(companies) == 2


def test_search_skips_404_profiles(client: CompaniesHouseClient) -> None:
    search_resp = _make_search_response(["11111111"])
    mock_404 = MagicMock()
    mock_404.status_code = 404
    mock_404.ok = False

    mock_session = MagicMock()
    mock_session.get.side_effect = [
        _mock_response(search_resp),
        mock_404,
        _mock_response({"total_results": 1, "items": []}),
    ]
    client._session = mock_session

    companies = client.search_companies_by_sic(["72110"])
    assert len(companies) == 0


def test_search_raises_on_rate_limit(client: CompaniesHouseClient) -> None:
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.ok = False

    mock_session = MagicMock()
    mock_session.get.return_value = mock_429
    client._session = mock_session

    # Patch sleep so the 61s retry waits don't run in tests
    with patch("src.companies.companies_house.time.sleep"):
        with pytest.raises(CompaniesHouseError, match="Rate limited"):
            client.search_companies_by_sic(["72110"])


def test_profile_address_is_formatted(client: CompaniesHouseClient) -> None:
    profile = _make_profile("44444444", "Address Test Ltd", ["72110"])
    company = CompaniesHouseClient._profile_to_company(profile, ["72110"])
    assert "Manchester" in company.registered_address
    assert "M1 1AA" in company.registered_address


def test_empty_search_results(client: CompaniesHouseClient) -> None:
    mock_session = MagicMock()
    mock_session.get.return_value = _mock_response({"total_results": 0, "items": []})
    client._session = mock_session

    companies = client.search_companies_by_sic(["72110"])
    assert companies == []


# ── Helper ────────────────────────────────────────────────────────────────────

def _mock_response(data: dict) -> MagicMock:
    mock = MagicMock()
    mock.status_code = 200
    mock.ok = True
    mock.json.return_value = data
    return mock
