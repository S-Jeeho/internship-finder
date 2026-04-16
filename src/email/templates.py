"""
Email subject and body templates for internship applications.

Provides render_email(company, applicant_name) -> (subject, body).
Edit the templates here to change the tone or content of every application
email without touching the sender logic.
"""

from src.companies.models import Company
from config.sic_codes import SIC_LABELS

SUBJECT_TEMPLATE = "Summer Internship Application 2025 — {applicant_name}"

BODY_TEMPLATE = """\
Dear {company_name} Team,

I hope this email finds you well. My name is {applicant_name} and I am a biology \
student currently looking for a summer internship placement for 2025. I came across \
{company_name} and was genuinely impressed by your work in {sector}, which aligns \
closely with my academic background and career interests.

I would love the opportunity to contribute to your team over the summer, even in a \
supporting capacity — whether that involves laboratory work, data analysis, research \
assistance, or anything else where an enthusiastic biotechnology student could be useful. \
I am also fully open to a remote or hybrid arrangement if that works better for your \
organisation.

I have attached a tailored CV for your review. I am a fast learner, reliable, and \
genuinely motivated by the kind of science {company_name} is doing. I would be very \
grateful for even a brief conversation if there is any possibility of a placement.

Thank you so much for taking the time to read this — I really appreciate it.

Kind regards,
{applicant_name}
"""


def render_email(company: Company, applicant_name: str) -> tuple[str, str]:
    """
    Render the subject and body for an internship application email.

    Args:
        company: Target company.
        applicant_name: The applicant's full name.

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
