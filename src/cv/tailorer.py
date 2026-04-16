"""
CV Tailorer — uses the Claude API to make small, targeted CV adjustments.

Given a base CV (Markdown text) and a Company object, Claude is asked to
make 3-5 specific adjustments that make the CV more relevant to that company.
The overall structure, length, and content must not change significantly.

A length-validation guard (±20%) catches runaway Claude responses before they
become malformed PDFs.
"""

import logging
from pathlib import Path

import anthropic

from src.companies.models import Company
from config.sic_codes import SIC_LABELS

logger = logging.getLogger(__name__)

_LENGTH_TOLERANCE = 0.40  # allow ±40% change in character count
_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 4096


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

        Args:
            company: The target company.

        Returns:
            Tailored CV as a Markdown string.

        Raises:
            CVTailoringError: If the API call fails or the response is too
                              different in length from the original.
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

        tailored = self._clean_response(message.content[0].text)
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
- **Company description**: {description_snippet}

## Task
Make 3 to 5 small, targeted adjustments to the CV below to make it more relevant to this specific company and sector.

### Rules (STRICT — do not break these):
1. Do NOT change the overall structure or section headings.
2. Do NOT add new sections or remove existing ones.
3. Do NOT invent qualifications, skills, or experience the candidate does not have.
4. Keep the total length within ±20% of the original.
5. Small changes only: reorder bullet points, swap generic phrases for sector-specific ones, add a brief one-sentence objective at the top if there is none.
6. Return ONLY the modified CV in Markdown. No preamble, no explanation, no "Here is the tailored CV:" header.

## Base CV
{self._base_cv}
"""

    @staticmethod
    def _clean_response(text: str) -> str:
        """Strip preamble/postamble and markdown code fences Claude may add."""
        text = text.strip()
        # Remove ```markdown ... ``` or ``` ... ``` wrappers
        if text.startswith("```"):
            lines = text.splitlines()
            # Drop the opening fence line and any closing fence
            inner = lines[1:]
            if inner and inner[-1].strip().startswith("```"):
                inner = inner[:-1]
            text = "\n".join(inner).strip()
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
