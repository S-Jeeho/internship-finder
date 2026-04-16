"""Tests for src/email/gmail_sender.py and src/email/templates.py"""

import base64
import email as email_lib
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.companies.models import Company
from src.email.gmail_sender import EmailSendError, send_application, _build_mime_message
from src.email.templates import render_email


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def company() -> Company:
    return Company(
        company_number="12345678",
        company_name="BioTech Innovations Ltd",
        company_type="ltd",
        sic_codes=["72110"],
        contact_email="hr@biotechinnovations.co.uk",
        description="Cutting-edge biotech R&D.",
    )


@pytest.fixture
def pdf_file(tmp_path: Path) -> Path:
    p = tmp_path / "cv.pdf"
    p.write_bytes(b"%PDF-test-content")  # fake PDF bytes
    return p


@pytest.fixture
def mock_gmail_service() -> MagicMock:
    service = MagicMock()
    service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
        "id": "msg_abc123"
    }
    return service


# ── templates.render_email ────────────────────────────────────────────────────

def test_render_email_contains_company_name(company: Company) -> None:
    subject, body = render_email(company, applicant_name="Jane Doe")
    assert "Biotech Innovations Ltd" in body or "BioTech Innovations Ltd" in body


def test_render_email_contains_applicant_name(company: Company) -> None:
    _, body = render_email(company, applicant_name="Jane Doe")
    assert "Jane Doe" in body


def test_render_email_subject_contains_applicant_name(company: Company) -> None:
    subject, _ = render_email(company, applicant_name="Jane Doe")
    assert "Jane Doe" in subject


def test_render_email_subject_contains_internship(company: Company) -> None:
    subject, _ = render_email(company, applicant_name="Jane Doe")
    assert "Internship" in subject or "internship" in subject


# ── _build_mime_message ───────────────────────────────────────────────────────

def test_build_mime_has_correct_headers(pdf_file: Path) -> None:
    msg = _build_mime_message(
        sender="me@gmail.com",
        to="hr@company.co.uk",
        subject="Test Subject",
        body="Test body",
        pdf_path=pdf_file,
    )
    assert msg["From"] == "me@gmail.com"
    assert msg["To"] == "hr@company.co.uk"
    assert msg["Subject"] == "Test Subject"


def test_build_mime_has_pdf_attachment(pdf_file: Path) -> None:
    msg = _build_mime_message(
        sender="me@gmail.com",
        to="hr@company.co.uk",
        subject="Subject",
        body="Body",
        pdf_path=pdf_file,
    )
    payloads = msg.get_payload()
    assert len(payloads) == 2  # text + attachment
    attachment = payloads[1]
    assert attachment.get_filename() == "cv.pdf"


# ── send_application ──────────────────────────────────────────────────────────

def test_send_application_returns_message_id(
    mock_gmail_service: MagicMock, company: Company, pdf_file: Path
) -> None:
    msg_id = send_application(
        gmail_service=mock_gmail_service,
        company=company,
        pdf_path=pdf_file,
        sender_address="me@gmail.com",
        applicant_name="Jane Doe",
    )
    assert msg_id == "msg_abc123"


def test_send_application_calls_gmail_api_once(
    mock_gmail_service: MagicMock, company: Company, pdf_file: Path
) -> None:
    send_application(
        gmail_service=mock_gmail_service,
        company=company,
        pdf_path=pdf_file,
        sender_address="me@gmail.com",
        applicant_name="Jane Doe",
    )
    mock_gmail_service.users().messages().send.assert_called_once()


def test_send_application_dry_run_skips_api(
    mock_gmail_service: MagicMock, company: Company, pdf_file: Path
) -> None:
    msg_id = send_application(
        gmail_service=mock_gmail_service,
        company=company,
        pdf_path=pdf_file,
        sender_address="me@gmail.com",
        applicant_name="Jane Doe",
        dry_run=True,
    )
    assert msg_id == "dry_run"
    mock_gmail_service.users().messages().send.assert_not_called()


def test_send_application_raises_without_recipient(
    mock_gmail_service: MagicMock, pdf_file: Path
) -> None:
    no_email_company = Company("99999999", "No Email Co", "ltd", sic_codes=["72110"])
    with pytest.raises(ValueError, match="No recipient email"):
        send_application(
            gmail_service=mock_gmail_service,
            company=no_email_company,
            pdf_path=pdf_file,
            sender_address="me@gmail.com",
            applicant_name="Jane Doe",
        )


def test_send_application_uses_override_recipient(
    mock_gmail_service: MagicMock, pdf_file: Path
) -> None:
    no_email_company = Company("99999999", "No Email Co", "ltd", sic_codes=["72110"])
    msg_id = send_application(
        gmail_service=mock_gmail_service,
        company=no_email_company,
        pdf_path=pdf_file,
        sender_address="me@gmail.com",
        applicant_name="Jane Doe",
        recipient_email="override@company.co.uk",
    )
    assert msg_id == "msg_abc123"


def test_send_application_raises_email_send_error_on_http_error(
    company: Company, pdf_file: Path
) -> None:
    from googleapiclient.errors import HttpError

    mock_service = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status = 500
    mock_resp.reason = "Internal Server Error"
    mock_service.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
        HttpError(resp=mock_resp, content=b"error")
    )

    with pytest.raises(EmailSendError, match="Gmail API error"):
        send_application(
            gmail_service=mock_service,
            company=company,
            pdf_path=pdf_file,
            sender_address="me@gmail.com",
            applicant_name="Jane Doe",
        )
