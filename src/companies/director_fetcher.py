"""
Director fetcher — retrieves company officers (directors) from Companies House.

Uses the /company/{number}/officers endpoint which is free and public.
Director names are used by the email enricher to guess contact emails.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.company-information.service.gov.uk"


@dataclass
class Director:
    name: str
    first_name: str
    last_name: str
    role: str  # e.g. "director", "secretary"


class DirectorFetcher:
    def __init__(self, api_key: str) -> None:
        self._auth = HTTPBasicAuth(api_key, "")
        self._session = requests.Session()
        self._session.auth = self._auth
        self._session.headers.update({"Accept": "application/json"})

    def get_directors(self, company_number: str) -> list[Director]:
        """
        Return active directors for a company.

        Args:
            company_number: Companies House company number.

        Returns:
            List of Director objects (active appointments only).
        """
        url = f"{_BASE_URL}/company/{company_number}/officers"
        try:
            response = self._session.get(url, timeout=10)
            if response.status_code == 404:
                logger.debug("No officers found for %s", company_number)
                return []
            if not response.ok:
                logger.warning(
                    "Officers API error %s for %s", response.status_code, company_number
                )
                return []
        except requests.RequestException as exc:
            logger.warning("Failed to fetch officers for %s: %s", company_number, exc)
            return []

        items = response.json().get("items", [])
        directors = []
        for item in items:
            # Skip resigned officers
            if item.get("resigned_on"):
                continue

            role = item.get("officer_role", "").lower()
            if role not in ("director", "secretary", "managing-officer", "llp-designated-member"):
                continue

            name_raw = item.get("name", "")
            first, last = _parse_name(name_raw)
            if not last:
                continue

            directors.append(Director(
                name=f"{first} {last}".strip(),
                first_name=first,
                last_name=last,
                role=role,
            ))

        logger.debug("Found %d active directors for %s", len(directors), company_number)
        return directors


def _parse_name(raw: str) -> tuple[str, str]:
    """
    Companies House stores names as "LASTNAME, Firstname Middlename".
    Returns (first_name, last_name) in title case.
    """
    raw = raw.strip()
    if "," in raw:
        parts = raw.split(",", 1)
        last = parts[0].strip().title()
        first = parts[1].strip().split()[0].title() if parts[1].strip() else ""
    else:
        parts = raw.split()
        last = parts[-1].title() if parts else ""
        first = parts[0].title() if len(parts) > 1 else ""
    return first, last
