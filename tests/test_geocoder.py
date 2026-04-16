"""Tests for src/companies/geocoder.py — no real Google Maps calls."""

from unittest.mock import MagicMock, patch

import pytest

from src.companies.geocoder import Geocoder, haversine_km
from src.companies.models import Company


# ── Haversine unit tests ──────────────────────────────────────────────────────

def test_haversine_same_point_is_zero() -> None:
    assert haversine_km(53.48, -2.24, 53.48, -2.24) == pytest.approx(0.0, abs=1e-6)


def test_haversine_manchester_to_london() -> None:
    # Manchester Piccadilly → London Euston: ~265 km
    dist = haversine_km(53.4808, -2.2426, 51.5285, -0.1340)
    assert 255 <= dist <= 275


def test_haversine_manchester_to_liverpool() -> None:
    # Manchester → Liverpool: ~50 km
    dist = haversine_km(53.4808, -2.2426, 53.4084, -2.9916)
    assert 40 <= dist <= 60


def test_haversine_symmetry() -> None:
    d1 = haversine_km(53.48, -2.24, 51.52, -0.13)
    d2 = haversine_km(51.52, -0.13, 53.48, -2.24)
    assert d1 == pytest.approx(d2, rel=1e-9)


# ── Geocoder — disabled when no key ──────────────────────────────────────────

def test_geocoder_disabled_without_key() -> None:
    geo = Geocoder(api_key="")
    assert not geo.enabled


def test_geocoder_enrich_no_op_when_disabled() -> None:
    company = Company("00000001", "Test Co", "ltd", registered_address="1 Test St, Manchester")
    geo = Geocoder(api_key="")
    result = geo.enrich_with_distance([company])
    assert result[0].latitude is None
    assert result[0].distance_km is None


# ── Geocoder — enabled path (Google Maps client mocked) ──────────────────────

def _make_geocoder_with_mock_client(geocode_return: list) -> Geocoder:
    geo = Geocoder.__new__(Geocoder)
    geo._api_key = "fake_key"
    mock_client = MagicMock()
    mock_client.geocode.return_value = geocode_return
    geo._client = mock_client
    return geo


def test_geocode_address_returns_coords() -> None:
    fake_result = [{"geometry": {"location": {"lat": 53.48, "lng": -2.24}}}]
    geo = _make_geocoder_with_mock_client(fake_result)
    coords = geo.geocode_address("1 Science Park, Manchester, M1 1AA")
    assert coords == pytest.approx((53.48, -2.24))


def test_geocode_address_returns_none_on_empty_result() -> None:
    geo = _make_geocoder_with_mock_client([])
    assert geo.geocode_address("Nowhere Land") is None


def test_enrich_sets_distance_km() -> None:
    fake_result = [{"geometry": {"location": {"lat": 53.48, "lng": -2.24}}}]
    geo = _make_geocoder_with_mock_client(fake_result)
    company = Company("00000001", "Test Co", "ltd", registered_address="1 Science Park, Manchester")
    geo.enrich_with_distance([company])
    assert company.latitude == pytest.approx(53.48)
    assert company.distance_km is not None
    assert company.distance_km < 5  # basically at Manchester centre


def test_enrich_skips_company_without_address() -> None:
    fake_result = [{"geometry": {"location": {"lat": 53.48, "lng": -2.24}}}]
    geo = _make_geocoder_with_mock_client(fake_result)
    company = Company("00000001", "No Address Co", "ltd", registered_address="")
    geo.enrich_with_distance([company])
    assert company.latitude is None  # untouched


# ── filter_by_distance ────────────────────────────────────────────────────────

def test_filter_keeps_nearby_companies() -> None:
    nearby = Company("1", "Nearby", "ltd", distance_km=10.0)
    far = Company("2", "Far Away", "ltd", distance_km=200.0)
    result = Geocoder.filter_by_distance([nearby, far], max_km=80)
    assert len(result) == 1
    assert result[0].company_number == "1"


def test_filter_keeps_companies_without_distance() -> None:
    no_dist = Company("3", "No Geo", "ltd")
    assert no_dist.distance_km is None
    result = Geocoder.filter_by_distance([no_dist], max_km=80)
    assert len(result) == 1  # not silently dropped


def test_filter_includes_exactly_at_boundary() -> None:
    boundary = Company("4", "Boundary Co", "ltd", distance_km=80.0)
    result = Geocoder.filter_by_distance([boundary], max_km=80)
    assert len(result) == 1
