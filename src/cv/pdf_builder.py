"""
PDF Builder — converts a Markdown CV string to a styled PDF file.

Uses fpdf2 (pure Python, no system dependencies, works on Windows/Mac/Linux).
Pipeline: Markdown lines → parsed tokens → fpdf2 PDF.

Usage:
    from src.cv.pdf_builder import build_pdf
    pdf_path = build_pdf(cv_text, output_dir=Path("/tmp"))
"""

import logging
import re
import tempfile
import uuid
from pathlib import Path

from fpdf import FPDF

logger = logging.getLogger(__name__)

# Page margins in mm
_MARGIN_LEFT = 20
_MARGIN_RIGHT = 20
_MARGIN_TOP = 20


class _CVPDF(FPDF):
    """Custom FPDF subclass with CV-specific styling."""

    def header(self):
        pass  # no header

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


_UNICODE_REPLACEMENTS = str.maketrans({
    "\u2013": "-",   # en-dash
    "\u2014": "--",  # em-dash
    "\u2018": "'",   # left single quote
    "\u2019": "'",   # right single quote / apostrophe
    "\u201c": '"',   # left double quote
    "\u201d": '"',   # right double quote
    "\u2022": "-",   # bullet
    "\u00b7": ".",   # middle dot
    "\u2026": "...", # ellipsis
    "\u00a0": " ",   # non-breaking space
})


def _sanitise(text: str) -> str:
    """Replace Unicode characters unsupported by Helvetica with ASCII equivalents."""
    return text.translate(_UNICODE_REPLACEMENTS).encode("latin-1", errors="replace").decode("latin-1")


def _strip_markdown_bold(text: str) -> str:
    """Remove **bold** and *italic* markers, return plain text."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    return text


def _render_inline(pdf: FPDF, text: str, base_size: float = 10.5) -> None:
    """
    Write a line of text that may contain **bold** spans, handling mixed
    bold/normal segments on one line.
    """
    # Split on **...** markers
    parts = re.split(r"(\*\*[^*]+\*\*)", text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            pdf.set_font("Helvetica", "B", base_size)
            pdf.write(5, _sanitise(part[2:-2]))
        else:
            plain = re.sub(r"\*(.+?)\*", r"\1", part)
            pdf.set_font("Helvetica", "", base_size)
            pdf.write(5, _sanitise(plain))


def build_pdf(
    cv_text: str,
    output_dir: Path | None = None,
    filename: str | None = None,
) -> Path:
    """
    Convert a Markdown CV string to a PDF and write it to disk.

    Args:
        cv_text: CV content in Markdown format.
        output_dir: Directory to write the PDF into. Defaults to a system
                    temp directory.
        filename: Filename for the PDF (without extension). Auto-generated
                  if omitted.

    Returns:
        Path to the created PDF file.

    Raises:
        RuntimeError: If PDF generation fails.
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="internship_cv_"))
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = f"cv_{uuid.uuid4().hex[:8]}"

    pdf_path = output_dir / f"{filename}.pdf"

    try:
        pdf = _CVPDF()
        pdf.set_margins(_MARGIN_LEFT, _MARGIN_TOP, _MARGIN_RIGHT)
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        for line in cv_text.splitlines():
            stripped = line.strip()

            # ── H1: # Name ────────────────────────────────────────────────────
            if stripped.startswith("# ") and not stripped.startswith("## "):
                text = _sanitise(stripped[2:].strip())
                pdf.set_font("Helvetica", "B", 18)
                pdf.set_text_color(30, 30, 30)
                pdf.cell(0, 10, text, ln=True)
                # Underline rule
                pdf.set_draw_color(44, 111, 173)
                pdf.set_line_width(0.5)
                x = pdf.get_x()
                y = pdf.get_y()
                pdf.line(_MARGIN_LEFT, y, pdf.w - _MARGIN_RIGHT, y)
                pdf.ln(3)

            # ── H2: ## Section ────────────────────────────────────────────────
            elif stripped.startswith("## "):
                text = _sanitise(stripped[3:].strip())
                pdf.ln(3)
                pdf.set_font("Helvetica", "B", 12)
                pdf.set_text_color(44, 111, 173)
                pdf.cell(0, 7, text, ln=True)
                # Thin underline
                pdf.set_draw_color(180, 210, 240)
                pdf.set_line_width(0.3)
                y = pdf.get_y()
                pdf.line(_MARGIN_LEFT, y, pdf.w - _MARGIN_RIGHT, y)
                pdf.ln(2)

            # ── H3: ### Subheading ────────────────────────────────────────────
            elif stripped.startswith("### "):
                text = _sanitise(stripped[4:].strip())
                pdf.set_font("Helvetica", "B", 10.5)
                pdf.set_text_color(30, 30, 30)
                pdf.cell(0, 6, _strip_markdown_bold(text), ln=True)

            # ── Horizontal rule: --- ──────────────────────────────────────────
            elif stripped in ("---", "***", "___"):
                pdf.ln(1)

            # ── Bullet point: - text ──────────────────────────────────────────
            elif stripped.startswith("- "):
                content = stripped[2:].strip()
                pdf.set_text_color(30, 30, 30)
                # Bullet character
                pdf.set_font("Helvetica", "", 10.5)
                pdf.set_x(_MARGIN_LEFT + 4)
                pdf.cell(5, 5, "-", ln=False)
                _render_inline(pdf, content, base_size=10.5)
                pdf.ln(5)

            # ── Empty line ────────────────────────────────────────────────────
            elif stripped == "":
                pdf.ln(2)

            # ── Regular paragraph line ────────────────────────────────────────
            else:
                pdf.set_text_color(30, 30, 30)
                pdf.set_x(_MARGIN_LEFT)
                _render_inline(pdf, stripped, base_size=10.5)
                pdf.ln(5)

        pdf.output(str(pdf_path))

    except Exception as exc:
        raise RuntimeError(f"PDF generation failed: {exc}") from exc

    logger.debug("PDF written to %s (%d bytes)", pdf_path, pdf_path.stat().st_size)
    return pdf_path
