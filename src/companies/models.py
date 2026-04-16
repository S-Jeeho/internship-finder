"""
Canonical data model for a company.

All modules pass Company objects — never raw dicts. This keeps the data
contract explicit and prevents string-key typos from propagating.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Company:
    """Represents a biology-sector company discovered via Companies House."""

    # ── Identity (from Companies House) ──────────────────────────────────────
    company_number: str          # e.g. "12345678"
    company_name: str            # e.g. "BioTech Innovations Ltd"
    company_type: str            # e.g. "ltd", "plc"
    sic_codes: list[str] = field(default_factory=list)  # e.g. ["72110"]

    # ── Address ───────────────────────────────────────────────────────────────
    registered_address: str = ""  # Full address as a single string

    # ── Contact (may not be on Companies House, enriched later) ───────────────
    contact_email: Optional[str] = None
    website: Optional[str] = None

    # ── Geocoding (enriched by geocoder.py if Maps key is set) ───────────────
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_km: Optional[float] = None  # Distance from Manchester city centre

    # ── Description (free text from Companies House or manual enrichment) ─────
    description: str = ""

    # ── Pipeline status ───────────────────────────────────────────────────────
    status: str = "new"  # "new" | "emailed" | "failed" | "skipped"

    def display_name(self) -> str:
        """Company name formatted for logs and email subjects."""
        return self.company_name.title()

    def primary_sic_label(self, sic_labels: dict[str, str]) -> str:
        """Human-readable label for the first SIC code, or a generic fallback."""
        if self.sic_codes:
            return sic_labels.get(self.sic_codes[0], f"SIC {self.sic_codes[0]}")
        return "Biology / Life Sciences"

    def to_dict(self) -> dict:
        """Serialise to a plain dict (for SQLite storage)."""
        return {
            "company_number": self.company_number,
            "company_name": self.company_name,
            "company_type": self.company_type,
            "sic_codes": ",".join(self.sic_codes),
            "registered_address": self.registered_address,
            "contact_email": self.contact_email,
            "website": self.website,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "distance_km": self.distance_km,
            "description": self.description,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, row: dict) -> "Company":
        """Hydrate from a SQLite row dict."""
        sic_raw = row.get("sic_codes", "") or ""
        return cls(
            company_number=row["company_number"],
            company_name=row["company_name"],
            company_type=row.get("company_type", ""),
            sic_codes=[s for s in sic_raw.split(",") if s],
            registered_address=row.get("registered_address", ""),
            contact_email=row.get("contact_email"),
            website=row.get("website"),
            latitude=row.get("latitude"),
            longitude=row.get("longitude"),
            distance_km=row.get("distance_km"),
            description=row.get("description", ""),
            status=row.get("status", "new"),
        )
