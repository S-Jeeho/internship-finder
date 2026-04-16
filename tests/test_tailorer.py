"""Tests for src/cv/tailorer.py — all Claude API calls are mocked."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.companies.models import Company
from src.cv.tailorer import CVTailor, CVTailoringError


# ── Fixtures ──────────────────────────────────────────────────────────────────

BASE_CV_TEXT = """\
# Jane Doe

**Email**: jane@example.com | **Location**: Manchester, UK

## Education
- BSc Biology, University of Manchester (2022–2025)

## Skills
- Molecular biology, PCR, cell culture
- Python (data analysis), R (statistics)

## Experience
- Lab assistant, University of Manchester (Summer 2024)
  - Assisted with protein purification experiments
  - Maintained laboratory equipment logs

## Projects
- Bioinformatics pipeline for 16S rRNA analysis (Python)
"""


@pytest.fixture
def cv_file(tmp_path: Path) -> Path:
    p = tmp_path / "cv_base.md"
    p.write_text(BASE_CV_TEXT)
    return p


@pytest.fixture
def mock_client() -> MagicMock:
    """A mock anthropic.Anthropic client."""
    client = MagicMock()
    return client


@pytest.fixture
def tailor(cv_file: Path, mock_client: MagicMock) -> CVTailor:
    t = CVTailor.__new__(CVTailor)
    t._client = mock_client
    t._base_cv = BASE_CV_TEXT
    return t


@pytest.fixture
def company() -> Company:
    return Company(
        company_number="12345678",
        company_name="BioTech Innovations Ltd",
        company_type="ltd",
        sic_codes=["72110"],
        registered_address="1 Science Park, Manchester, M1 1AA",
        description="Cutting-edge biotech R&D laboratory.",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def _make_api_response(text: str) -> MagicMock:
    content_block = MagicMock()
    content_block.text = text
    response = MagicMock()
    response.content = [content_block]
    return response


def test_tailor_returns_string(tailor: CVTailor, company: Company, mock_client: MagicMock) -> None:
    mock_client.messages.create.return_value = _make_api_response(BASE_CV_TEXT)
    result = tailor.tailor_for_company(company)
    assert isinstance(result, str)
    assert len(result) > 0


def test_tailor_calls_claude_once(tailor: CVTailor, company: Company, mock_client: MagicMock) -> None:
    mock_client.messages.create.return_value = _make_api_response(BASE_CV_TEXT)
    tailor.tailor_for_company(company)
    mock_client.messages.create.assert_called_once()


def test_tailor_prompt_contains_company_name(
    tailor: CVTailor, company: Company, mock_client: MagicMock
) -> None:
    captured_prompt = []

    def capture(*args, **kwargs):
        captured_prompt.append(kwargs["messages"][0]["content"])
        return _make_api_response(BASE_CV_TEXT)

    mock_client.messages.create.side_effect = capture
    tailor.tailor_for_company(company)
    assert "BioTech Innovations Ltd" in captured_prompt[0]


def test_tailor_prompt_contains_base_cv(
    tailor: CVTailor, company: Company, mock_client: MagicMock
) -> None:
    captured_prompt = []

    def capture(*args, **kwargs):
        captured_prompt.append(kwargs["messages"][0]["content"])
        return _make_api_response(BASE_CV_TEXT)

    mock_client.messages.create.side_effect = capture
    tailor.tailor_for_company(company)
    assert "Jane Doe" in captured_prompt[0]


def test_tailor_raises_on_too_long_response(
    tailor: CVTailor, company: Company, mock_client: MagicMock
) -> None:
    bloated = BASE_CV_TEXT * 4  # 4x the length — way over ±20%
    mock_client.messages.create.return_value = _make_api_response(bloated)
    with pytest.raises(CVTailoringError, match="different in length"):
        tailor.tailor_for_company(company)


def test_tailor_raises_on_too_short_response(
    tailor: CVTailor, company: Company, mock_client: MagicMock
) -> None:
    tiny = "Hi."
    mock_client.messages.create.return_value = _make_api_response(tiny)
    with pytest.raises(CVTailoringError, match="different in length"):
        tailor.tailor_for_company(company)


def test_tailor_accepts_response_within_tolerance(
    tailor: CVTailor, company: Company, mock_client: MagicMock
) -> None:
    # Append a small sentence — within 20% length change
    slightly_modified = BASE_CV_TEXT + "\n- Interested in biotech applications."
    mock_client.messages.create.return_value = _make_api_response(slightly_modified)
    result = tailor.tailor_for_company(company)
    assert "biotech applications" in result


def test_tailor_raises_on_api_error(
    tailor: CVTailor, company: Company, mock_client: MagicMock
) -> None:
    import anthropic
    mock_client.messages.create.side_effect = anthropic.APIStatusError(
        "Internal server error", response=MagicMock(status_code=500), body={}
    )
    with pytest.raises(CVTailoringError, match="Claude API error"):
        tailor.tailor_for_company(company)


def test_load_cv_raises_if_file_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="cv_base.md"):
        CVTailor(api_key="key", base_cv_path=tmp_path / "nonexistent.md")


def test_load_cv_reads_content(cv_file: Path) -> None:
    with patch("anthropic.Anthropic"):
        t = CVTailor(api_key="fake", base_cv_path=cv_file)
    assert "Jane Doe" in t._base_cv
