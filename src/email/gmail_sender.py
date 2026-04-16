"""
Gmail sender — composes a MIME email with a PDF attachment and sends it.

Never catches its own exceptions — that is the pipeline's responsibility,
so failures are logged at the call site and the company is marked 'failed'.
"""

import base64
import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from googleapiclient.errors import HttpError

from src.companies.models import Company
from src.email.templates import render_email

logger = logging.getLogger(__name__)


class EmailSendError(Exception):
    """Raised when the Gmail API rejects the send request."""


def send_application(
    gmail_service,
    company: Company,
    pdf_path: Path,
    sender_address: str,
    applicant_name: str,
    recipient_email: str | None = None,
    dry_run: bool = False,
) -> str:
    """
    Compose and send an internship application email with a PDF CV attachment.

    Args:
        gmail_service: Authenticated Gmail API resource from gmail_auth.py.
        company: Target company.
        pdf_path: Path to the tailored PDF CV.
        sender_address: Gmail address to send from.
        applicant_name: Applicant's full name for the email body.
        recipient_email: Override the to-address. If None, uses company.contact_email.
        dry_run: If True, logs what would be sent but does NOT call the API.

    Returns:
        Gmail message ID string (or "dry_run" if dry_run=True).

    Raises:
        ValueError: If no recipient email can be determined.
        EmailSendError: If the Gmail API call fails.
    """
    to_address = recipient_email or company.contact_email
    if not to_address:
        raise ValueError(
            f"No recipient email for {company.company_name} "
            "(company.contact_email is empty and no override given)"
        )

    subject, body = render_email(company, applicant_name)
    message = _build_mime_message(
        sender=sender_address,
        to=to_address,
        subject=subject,
        body=body,
        pdf_path=pdf_path,
    )

    if dry_run:
        logger.info(
            "[DRY RUN] Would send to %s <%s> — subject: '%s'",
            company.company_name,
            to_address,
            subject,
        )
        return "dry_run"

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    try:
        sent = (
            gmail_service.users()
            .messages()
            .send(userId="me", body={"raw": raw})
            .execute()
        )
    except HttpError as exc:
        raise EmailSendError(
            f"Gmail API error sending to {company.company_name}: {exc}"
        ) from exc

    msg_id = sent.get("id", "")
    logger.info(
        "Email sent to %s <%s> — Gmail message ID: %s",
        company.company_name,
        to_address,
        msg_id,
    )
    return msg_id


# ── Private helpers ───────────────────────────────────────────────────────────

def _build_mime_message(
    sender: str,
    to: str,
    subject: str,
    body: str,
    pdf_path: Path,
) -> MIMEMultipart:
    message = MIMEMultipart()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    with open(pdf_path, "rb") as f:
        attachment = MIMEApplication(f.read(), _subtype="pdf")
    attachment.add_header(
        "Content-Disposition",
        "attachment",
        filename=pdf_path.name,
    )
    message.attach(attachment)

    return message
