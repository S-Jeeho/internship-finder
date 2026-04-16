"""
Email subject and body templates for internship applications.

Provides render_email(company) -> (subject, body) using simple string
substitution. Edit the templates here to change the tone or content of
every application email without touching the sender logic.
"""

from src.companies.models import Company
from config.sic_codes import SIC_LABELS

SUBJECT_TEMPLATE = "Internship Application — Biology / {sector} — {applicant_name}"

BODY_TEMPLATE = """\
Dear {company_name} Team,

I am writing to express my keen interest in undertaking an internship with {company_name}. \
I am currently studying biology and am particularly excited about the work being done in \
the {sector} field.

I have attached my CV, which has been tailored to highlight the skills and experience most \
relevant to your organisation. I would welcome the opportunity to contribute to your team \
and to learn from the experts at {company_name}.

Please do not hesitate to contact me if you would like any further information or to \
arrange an interview at a mutually convenient time.

Thank you for considering my application.

Kind regards,
{applicant_name}
"""


def render_email(company: Company, applicant_name: str) -> tuple[str, str]:
    """
    Render the subject and body for an internship application email.

    Args:
        company: Target company.
        applicant_name: The applicant's full name (from the CV / config).

    Returns:
        (subject, body) as plain strings.
    """
    sector = company.primary_sic_label(SIC_LABELS)
    context = {
        "company_name": company.display_name(),
        "sector": sector,
        "applicant_name": applicant_name,
    }
    subject = SUBJECT_TEMPLATE.format(**context)
    body = BODY_TEMPLATE.format(**context)
    return subject, body
