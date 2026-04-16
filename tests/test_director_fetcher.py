"""Tests for src/companies/director_fetcher.py"""

from unittest.mock import MagicMock

import pytest

from src.companies.director_fetcher import DirectorFetcher, _parse_name


# ── _parse_name ───────────────────────────────────────────────────────────────

def test_parse_name_companies_house_format() -> None:
    first, last = _parse_name("SMITH, John")
    assert first == "John"
    assert last == "Smith"


def test_parse_name_title_case() -> None:
    first, last = _parse_name("JOHNSON, EMILY")
    assert first == "Emily"
    assert last == "Johnson"


def test_parse_name_no_comma() -> None:
    first, last = _parse_name("John Smith")
    assert first == "John"
    assert last == "Smith"


def test_parse_name_empty() -> None:
    first, last = _parse_name("")
    assert first == ""
    assert last == ""


def test_parse_name_ignores_middle_name() -> None:
    first, last = _parse_name("DOE, John Michael")
    assert first == "John"
    assert last == "Doe"


# ── DirectorFetcher ───────────────────────────────────────────────────────────

def _make_fetcher() -> DirectorFetcher:
    f = DirectorFetcher.__new__(DirectorFetcher)
    f._session = MagicMock()
    return f


def _mock_response(data: dict, status: int = 200) -> MagicMock:
    r = MagicMock()
    r.status_code = status
    r.ok = status == 200
    r.json.return_value = data
    return r


def test_get_directors_returns_active_only() -> None:
    fetcher = _make_fetcher()
    fetcher._session.get.return_value = _mock_response({
        "items": [
            {"name": "SMITH, John", "officer_role": "director", "resigned_on": None},
            {"name": "DOE, Jane", "officer_role": "director", "resigned_on": "2023-01-01"},
        ]
    })
    directors = fetcher.get_directors("12345678")
    assert len(directors) == 1
    assert directors[0].last_name == "Smith"


def test_get_directors_filters_by_role() -> None:
    fetcher = _make_fetcher()
    fetcher._session.get.return_value = _mock_response({
        "items": [
            {"name": "SMITH, John", "officer_role": "director"},
            {"name": "JONES, Bob", "officer_role": "nominee-director"},
        ]
    })
    directors = fetcher.get_directors("12345678")
    assert len(directors) == 1
    assert directors[0].last_name == "Smith"


def test_get_directors_returns_empty_on_404() -> None:
    fetcher = _make_fetcher()
    fetcher._session.get.return_value = _mock_response({}, status=404)
    directors = fetcher.get_directors("00000000")
    assert directors == []


def test_get_directors_returns_empty_on_network_error() -> None:
    import requests as req
    fetcher = _make_fetcher()
    fetcher._session.get.side_effect = req.RequestException("timeout")
    directors = fetcher.get_directors("12345678")
    assert directors == []


def test_get_directors_role_stored() -> None:
    fetcher = _make_fetcher()
    fetcher._session.get.return_value = _mock_response({
        "items": [{"name": "LEE, Sarah", "officer_role": "director"}]
    })
    directors = fetcher.get_directors("12345678")
    assert directors[0].role == "director"
