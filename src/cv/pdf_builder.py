"""
PDF Builder — converts a Markdown CV string to a styled PDF file.

Pipeline: Markdown → HTML (via `markdown`) → PDF (via WeasyPrint).
Each PDF is written to a temp directory so concurrent runs never collide.
The original cv_base.md/pdf is never touched.

Usage:
    from src.cv.pdf_builder import build_pdf
    pdf_path = build_pdf(cv_text, output_dir=Path("/tmp"))
"""

import logging
import tempfile
from pathlib import Path

import markdown as md_lib
import weasyprint

logger = logging.getLogger(__name__)

# Minimal CSS that makes the PDF readable and professional-looking
_CV_CSS = """
@page {
    size: A4;
    margin: 2cm 2.5cm;
}
body {
    font-family: "Helvetica Neue", Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #222;
}
h1 {
    font-size: 20pt;
    margin-bottom: 4pt;
    border-bottom: 2px solid #2c6fad;
    padding-bottom: 4pt;
    color: #1a1a1a;
}
h2 {
    font-size: 13pt;
    color: #2c6fad;
    margin-top: 14pt;
    margin-bottom: 4pt;
    border-bottom: 1px solid #cde;
    padding-bottom: 2pt;
}
h3 {
    font-size: 11pt;
    font-weight: bold;
    margin-bottom: 2pt;
}
ul {
    margin: 4pt 0;
    padding-left: 18pt;
}
li {
    margin-bottom: 2pt;
}
p {
    margin: 4pt 0;
}
strong {
    font-weight: bold;
}
a {
    color: #2c6fad;
    text-decoration: none;
}
"""


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
        filename: Filename for the PDF (without extension). If omitted, a
                  unique name is generated.

    Returns:
        Path to the created PDF file.

    Raises:
        RuntimeError: If WeasyPrint fails to render the PDF.
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="internship_cv_"))
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        import uuid
        filename = f"cv_{uuid.uuid4().hex[:8]}"

    pdf_path = output_dir / f"{filename}.pdf"

    html_body = md_lib.markdown(cv_text, extensions=["extra"])
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <style>{_CV_CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    try:
        weasyprint.HTML(string=full_html).write_pdf(str(pdf_path))
    except Exception as exc:
        raise RuntimeError(f"WeasyPrint failed to render PDF: {exc}") from exc

    logger.debug("PDF written to %s (%d bytes)", pdf_path, pdf_path.stat().st_size)
    return pdf_path
