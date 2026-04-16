"""
Companies House REST API client.

Searches for UK companies by SIC code and location keyword, returning
a list of Company objects. Handles pagination (max 20 results/page),
rate limiting, and maps raw JSON to the Company dataclass.

API docs: https://developer.company-information.service.gov.uk/api/docs/
Authentication: HTTP Basic Auth — API key as username, empty password.
"""

import logging
import time
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

from src.companies.models import Company

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.company-information.service.gov.uk"
_PAGE_SIZE = 20
_DEFAULT_RATE_LIMIT_SLEEP = 1.0  # seconds between requests (free tier: 600 req/5min)
_RETRY_WAIT_429 = 61  # seconds to wait when rate limited before retrying


class CompaniesHouseError(Exception):
    """Raised when the Companies House API returns an unexpected response."""


class CompaniesHouseClient:
    def __init__(self, api_key: str, rate_limit_sleep: float = _DEFAULT_RATE_LIMIT_SLEEP) -> None:
        self._auth = HTTPBasicAuth(api_key, "")
        self._rate_limit_sleep = rate_limit_sleep
        self._session = requests.Session()
        self._session.auth = self._auth
        self._session.headers.update({"Accept": "application/json"})

    # ── Public interface ──────────────────────────────────────────────────────

    def search_companies_by_sic(
        self,
        sic_codes: list[str],
        location_term: str = "Manchester",
        max_results: Optional[int] = None,
    ) -> list[Company]:
        """
        Search for active UK companies matching any of the given SIC codes
        near the specified location.

        Companies House does not natively filter by SIC code in its search
        endpoint, so we search by location and filter client-side.

        Strategy:
          1. Search for companies with the location keyword.
          2. For each company, fetch its profile to get SIC codes.
          3. Keep only companies whose SIC codes overlap with our target list.

        Args:
            sic_codes: UK SIC 2007 codes to match against.
            location_term: Location keyword for the search query (e.g. "Manchester").
            max_results: Cap on total returned companies (None = no limit).

        Returns:
            List of Company objects with SIC codes matching the filter.
        """
        sic_set = set(sic_codes)
        matched: list[Company] = []
        start_index = 0

        logger.info(
            "Searching Companies House for '%s' biology companies (SICs: %s)",
            location_term,
            ", ".join(sic_codes),
        )

        while True:
            page = self._search_page(location_term, start_index)
            items = page.get("items", [])
            total_results = page.get("total_results", 0)

            if not items:
                break

            for item in items:
                if max_results and len(matched) >= max_results:
                    return matched

                company_number = item.get("company_number", "")
                if not company_number:
                    continue

                profile = self._get_company_profile(company_number)
                if profile is None:
                    continue

                # Live API returns sic_codes as plain strings e.g. ["72110"]
                raw_sics = profile.get("sic_codes", [])
                company_sic_codes = [
                    s if isinstance(s, str) else s.get("sic_code", "")
                    for s in raw_sics
                ]
                if not sic_set.intersection(company_sic_codes):
                    continue

                company = self._profile_to_company(profile, company_sic_codes)
                matched.append(company)
                logger.debug(
                    "Matched: %s (%s) — SICs: %s",
                    company.company_name,
                    company.company_number,
                    company_sic_codes,
                )

                time.sleep(self._rate_limit_sleep)

            start_index += _PAGE_SIZE
            if start_index >= total_results:
                break

            time.sleep(self._rate_limit_sleep)

        logger.info("Found %d matching companies", len(matched))
        return matched

    def get_company_profile(self, company_number: str) -> Optional[Company]:
        """Fetch a single company profile by its Companies House number."""
        profile = self._get_company_profile(company_number)
        if profile is None:
            return None
        raw_sics = profile.get("sic_codes", [])
        sic_codes = [s if isinstance(s, str) else s.get("sic_code", "") for s in raw_sics]
        return self._profile_to_company(profile, sic_codes)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _get_company_profile(self, company_number: str) -> Optional[dict]:
        url = f"{_BASE_URL}/company/{company_number}"
        for attempt in range(3):
            response = self._session.get(url, timeout=10)
            if response.status_code == 404:
                logger.debug("Company %s not found", company_number)
                return None
            if response.status_code == 429:
                logger.warning(
                    "Rate limited — waiting %ds before retry (attempt %d/3)",
                    _RETRY_WAIT_429, attempt + 1,
                )
                time.sleep(_RETRY_WAIT_429)
                continue
            self._raise_for_status(response)
            return response.json()
        raise CompaniesHouseError("Rate limited by Companies House API after 3 retries")

    def _search_page(self, query: str, start_index: int) -> dict:
        url = f"{_BASE_URL}/search/companies"
        params = {
            "q": query,
            "items_per_page": _PAGE_SIZE,
            "start_index": start_index,
        }
        for attempt in range(3):
            response = self._session.get(url, params=params, timeout=10)
            if response.status_code == 429:
                logger.warning(
                    "Rate limited on search — waiting %ds (attempt %d/3)",
                    _RETRY_WAIT_429, attempt + 1,
                )
                time.sleep(_RETRY_WAIT_429)
                continue
            self._raise_for_status(response)
            return response.json()
        raise CompaniesHouseError("Rate limited by Companies House API after 3 retries")

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        if response.status_code == 429:
            raise CompaniesHouseError("Rate limited by Companies House API (429)")
        if not response.ok:
            raise CompaniesHouseError(
                f"Companies House API error {response.status_code}: {response.text[:200]}"
            )

    @staticmethod
    def _profile_to_company(profile: dict, sic_codes: list[str]) -> Company:
        """Map a raw Companies House profile dict to a Company object."""
        address_obj = profile.get("registered_office_address", {})
        address_parts = [
            address_obj.get("address_line_1", ""),
            address_obj.get("address_line_2", ""),
            address_obj.get("locality", ""),
            address_obj.get("region", ""),
            address_obj.get("postal_code", ""),
            address_obj.get("country", ""),
        ]
        address = ", ".join(p for p in address_parts if p)

        return Company(
            company_number=profile.get("company_number", ""),
            company_name=profile.get("company_name", ""),
            company_type=profile.get("type", ""),
            sic_codes=[c for c in sic_codes if c],
            registered_address=address,
            description=profile.get("company_status", ""),
            status="new",
        )
