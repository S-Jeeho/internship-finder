"""
Shared pytest fixtures used across all test modules.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from src.companies.models import Company
from src.storage.database import init_db


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Create a fresh in-memory-style SQLite database in a temp directory."""
    db_path = tmp_path / "test_tracker.db"
    init_db(db_path)
    return db_path


@pytest.fixture
def sample_company() -> Company:
    return Company(
        company_number="12345678",
        company_name="BioTech Innovations Ltd",
        company_type="ltd",
        sic_codes=["72110"],
        registered_address="1 Science Park, Manchester, M1 1AA",
        contact_email="hello@biotechinnovations.co.uk",
        website="https://biotechinnovations.co.uk",
        latitude=53.48,
        longitude=-2.24,
        distance_km=5.2,
        description="Cutting-edge biotech R&D company.",
        status="new",
    )


@pytest.fixture
def sample_company_list(sample_company: Company) -> list[Company]:
    second = Company(
        company_number="87654321",
        company_name="Pharma Solutions UK Ltd",
        company_type="ltd",
        sic_codes=["21200"],
        registered_address="2 Health Way, Salford, M5 2BB",
        description="Pharmaceutical preparations manufacturer.",
    )
    return [sample_company, second]
