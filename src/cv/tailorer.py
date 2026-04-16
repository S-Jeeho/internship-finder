"""
CV Tailorer — uses the Claude API to make small, targeted CV adjustments.

Given a base CV (Markdown text) and a Company object, Claude is asked to
make 3-5 specific adjustments that make the CV more relevant to that company.
The overall structure, length, and content must not change significantly.
"""

import logging
from pathlib import Path

import anthropic

from src.companies.models import Company
from config.sic_codes import SIC_LABELS

logger = logging.getLogger(__name__)

_LENGTH_TOLERANCE = 0.60  # allow ±60% change in character count
_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 8192
_MIN_CV_CHARS = 200  # anything shorter is clearly a bad response


class CVTailoringError(Exception):
    """Raised when tailoring fails or produces an unacceptable response."""


class CVTailor:
    def __init__(self, api_key: str, base_cv_path: Path) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._base_cv = self._load_cv(base_cv_path)
        logger.debug("CVTailor initialised, base CV: %d chars", len(self._base_cv))

    # ── Public interface ──────────────────────────────────────────────────────

    def tailor_for_company(self, company: Company) -> str:
        """
        Return a lightly tailored version of the base CV for this company.

        Raises:
            CVTailoringError: If the API call fails or the response is unusable.
        """
        sector_label = company.primary_sic_label(SIC_LABELS)
        prompt = self._build_prompt(company, sector_label)

        logger.info("Tailoring CV for %s (%s)", company.company_name, sector_label)

        try:
            message = self._client.messages.create(
                model=_MODEL,
                max_tokens=_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:
            raise CVTailoringError(f"Claude API error for {company.company_name}: {exc}") from exc

        if not message.content:
            raise CVTailoringError(f"Claude returned empty response for {company.company_name}")

        tailored = self._clean_response(message.content[0].text)

        if len(tailored) < _MIN_CV_CHARS:
            raise CVTailoringError(
                f"Claude returned a near-empty response for {company.company_name} "
                f"({len(tailored)} chars). The CV was not tailored."
            )

        self._validate_length(tailored, company.company_name)

        logger.debug(
            "CV tailored for %s: %d → %d chars",
            company.company_name,
            len(self._base_cv),
            len(tailored),
        )
        return tailored

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_prompt(self, company: Company, sector_label: str) -> str:
        description_snippet = (
            company.description[:300] if company.description else "Not available"
        )
        return f"""You are helping a biology student tailor their CV for an internship application.

## Company Information
- **Name**: {company.company_name}
- **Sector**: {sector_label}
- **Location**: {company.registered_address or "Manchester area, UK"}
- **Description**: {description_snippet}

## Your Task
Make 3 to 5 small, targeted word-level changes to the CV so it reads as a better fit for this company.

CRITICAL RULES — read carefully:
1. Output the COMPLETE, FULL CV from the very first line to the very last line. Do NOT omit any section.
2. Do NOT change section headings, overall structure, or the number of bullet points.
3. Do NOT invent qualifications or experience the candidate does not have.
4. Only swap specific words/phrases for more sector-relevant ones (e.g. "data analysis" → "genomic data analysis").
5. You may add one short objective sentence at the top if there is none already.
6. Output RAW Markdown only — no code fences, no preamble, no "Here is the CV:" line.

## Base CV (copy this in full, with your small changes applied)
{self._base_cv}
"""

    @staticmethod
    def _clean_response(text: str) -> str:
        """Strip any code fences or preamble Claude may add despite instructions."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            inner = lines[1:]
            if inner and inner[-1].strip().startswith("```"):
                inner = inner[:-1]
            text = "\n".join(inner).strip()
        # Strip a leading explanation line (e.g. "Here is the tailored CV:")
        lines = text.splitlines()
        if lines and not lines[0].startswith("#") and lines[0].endswith(":"):
            text = "\n".join(lines[1:]).strip()
        return text

    def _validate_length(self, tailored: str, company_name: str) -> None:
        base_len = len(self._base_cv)
        tailored_len = len(tailored)
        delta = abs(tailored_len - base_len) / base_len if base_len > 0 else 1.0
        if delta > _LENGTH_TOLERANCE:
            raise CVTailoringError(
                f"Tailored CV for {company_name} is {delta:.0%} different in length "
                f"from base CV ({base_len} → {tailored_len} chars). "
                "Rejecting to avoid sending a malformed CV."
            )

    @staticmethod
    def _load_cv(path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(
                f"Base CV not found at '{path}'. "
                "Create data/cv_base.md with your CV in Markdown format."
            )
        return path.read_text(encoding="utf-8").strip()
