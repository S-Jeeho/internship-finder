"""Tests for src/cv/pdf_builder.py"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.cv.pdf_builder import build_pdf

SAMPLE_CV = """\
# Jane Doe

**Email**: jane@example.com

## Education
- BSc Biology, University of Manchester

## Skills
- Python, PCR, cell culture
"""


def test_build_pdf_creates_file(tmp_path: Path) -> None:
    pdf_path = build_pdf(SAMPLE_CV, output_dir=tmp_path, filename="test_cv")
    assert pdf_path.exists()
    assert pdf_path.suffix == ".pdf"
    assert pdf_path.stat().st_size > 0


def test_build_pdf_uses_provided_filename(tmp_path: Path) -> None:
    pdf_path = build_pdf(SAMPLE_CV, output_dir=tmp_path, filename="my_cv")
    assert pdf_path.name == "my_cv.pdf"


def test_build_pdf_generates_filename_if_none(tmp_path: Path) -> None:
    pdf_path = build_pdf(SAMPLE_CV, output_dir=tmp_path)
    assert pdf_path.suffix == ".pdf"
    assert pdf_path.name.startswith("cv_")


def test_build_pdf_creates_output_dir(tmp_path: Path) -> None:
    nested = tmp_path / "nested" / "dir"
    assert not nested.exists()
    pdf_path = build_pdf(SAMPLE_CV, output_dir=nested, filename="cv")
    assert nested.exists()
    assert pdf_path.exists()


def test_build_pdf_uses_temp_dir_by_default() -> None:
    pdf_path = build_pdf(SAMPLE_CV, filename="tmp_cv")
    try:
        assert pdf_path.exists()
        assert "internship_cv_" in str(pdf_path.parent)
    finally:
        pdf_path.unlink(missing_ok=True)


def test_build_pdf_two_calls_produce_different_files(tmp_path: Path) -> None:
    p1 = build_pdf(SAMPLE_CV, output_dir=tmp_path)
    p2 = build_pdf(SAMPLE_CV, output_dir=tmp_path)
    assert p1 != p2  # filenames differ (uuid-based)


def test_build_pdf_raises_on_weasyprint_error(tmp_path: Path) -> None:
    with patch("src.cv.pdf_builder.weasyprint.HTML") as mock_html:
        mock_html.return_value.write_pdf.side_effect = Exception("render crash")
        with pytest.raises(RuntimeError, match="WeasyPrint failed"):
            build_pdf(SAMPLE_CV, output_dir=tmp_path, filename="crash_test")


def test_build_pdf_content_is_valid_pdf(tmp_path: Path) -> None:
    pdf_path = build_pdf(SAMPLE_CV, output_dir=tmp_path, filename="valid")
    with open(pdf_path, "rb") as f:
        header = f.read(4)
    assert header == b"%PDF"  # PDF magic bytes
