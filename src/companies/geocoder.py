"""
Geocoder — enriches Company objects with lat/lon and filters by distance.

Uses the Google Maps Geocoding API. If no API key is configured the module
silently skips enrichment, so the pipeline degrades gracefully.

Manchester city centre reference point:
  Latitude:  53.4808  (Piccadilly Gardens)
  Longitude: -2.2426
"""

import logging
import math
from typing import Optional

from src.companies.models import Company

logger = logging.getLogger(__name__)

# Manchester city centre (Piccadilly Gardens)
MANCHESTER_LAT = 53.4808
MANCHESTER_LON = -2.2426

_EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Return the great-circle distance in kilometres between two (lat, lon) points.
    """
    r = _EARTH_RADIUS_KM
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class Geocoder:
    """
    Wraps the Google Maps Geocoding API.

    Constructed with an API key. If the key is empty the class is a no-op
    — enrich_with_distance returns companies unchanged.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = None

        if api_key:
            try:
                import googlemaps  # type: ignore
                self._client = googlemaps.Client(key=api_key)
                logger.debug("Google Maps client initialised")
            except ImportError:
                logger.warning(
                    "googlemaps package not installed — distance filtering disabled. "
                    "Run: pip install googlemaps"
                )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def geocode_address(self, address: str) -> Optional[tuple[float, float]]:
        """
        Return (latitude, longitude) for a UK address string, or None on failure.
        """
        if not self._client:
            return None
        try:
            results = self._client.geocode(address + ", UK")
            if results:
                loc = results[0]["geometry"]["location"]
                return loc["lat"], loc["lng"]
        except Exception as exc:
            logger.warning("Geocoding failed for '%s': %s", address, exc)
        return None

    def enrich_with_distance(
        self,
        companies: list[Company],
        ref_lat: float = MANCHESTER_LAT,
        ref_lon: float = MANCHESTER_LON,
    ) -> list[Company]:
        """
        Geocode each company's registered address and compute its distance
        from the reference point (defaults to Manchester city centre).

        Modifies each Company in-place (sets latitude, longitude, distance_km).
        Companies that fail to geocode keep None for those fields.
        """
        if not self.enabled:
            logger.info("Geocoder disabled — skipping distance enrichment")
            return companies

        for company in companies:
            if not company.registered_address:
                continue
            coords = self.geocode_address(company.registered_address)
            if coords:
                company.latitude, company.longitude = coords
                company.distance_km = haversine_km(
                    ref_lat, ref_lon, company.latitude, company.longitude
                )
                logger.debug(
                    "%s — %.1f km from reference point",
                    company.company_name,
                    company.distance_km,
                )
            else:
                logger.debug("Could not geocode address for %s", company.company_name)

        return companies

    @staticmethod
    def filter_by_distance(
        companies: list[Company],
        max_km: float,
    ) -> list[Company]:
        """
        Return only companies within max_km of Manchester (or those without
        distance data, so un-geocoded companies are not silently dropped).
        """
        filtered = []
        for c in companies:
            if c.distance_km is None or c.distance_km <= max_km:
                filtered.append(c)
            else:
                logger.debug(
                    "Excluding %s (%.1f km > %.1f km limit)",
                    c.company_name,
                    c.distance_km,
                    max_km,
                )
        return filtered
