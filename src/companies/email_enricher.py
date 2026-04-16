"""
Email enricher — finds a contact email for a company using:

  1. Website discovery: guesses the company's domain from its name and
     checks if it responds to HTTP requests.
  2. Email generation: produces candidate addresses from director names
     and common generic prefixes (info@, hr@, contact@).
  3. SMTP verification: connects to the domain's mail server and checks
     whether each address is accepted — without sending any email.

The best verified address is returned and saved to the database.
SMTP verification is best-effort: many servers block it, so unverified
guesses are still returned as a fallback ranked by likelihood.
"""

import logging
import re
import smtplib
import socket
import time
from typing import Optional

import requests

from src.companies.director_fetcher import Director

logger = logging.getLogger(__name__)

# Words to strip when turning a company name into a domain guess
_STRIP_WORDS = {
    "limited", "ltd", "plc", "llp", "llc", "inc",
    "holdings", "holding", "the", "and", "&", "co", "company",
}

# Generic email prefixes tried for every company (ordered by likelihood)
_GENERIC_PREFIXES = ["info", "contact", "hello", "hr", "careers", "admin", "enquiries"]

# TLDs to try when guessing domain
_TLDS = [".co.uk", ".com", ".org.uk", ".org"]

_REQUEST_TIMEOUT = 5   # seconds for HTTP website check
_SMTP_TIMEOUT = 8      # seconds for SMTP verification


class EmailEnricher:
    def __init__(self, smtp_verify: bool = True) -> None:
        """
        Args:
            smtp_verify: If True, attempt SMTP verification of guessed emails.
                         Set False in tests or when mail servers block probes.
        """
        self._smtp_verify = smtp_verify

    def find_email(
        self,
        company_name: str,
        directors: list[Director],
        registered_address: str = "",
    ) -> Optional[str]:
        """
        Try to find a working contact email for a company.

        Returns the best candidate found, or None if nothing plausible is found.
        Priority: SMTP-verified > generic info@ > director guess.
        """
        domain = self._guess_domain(company_name)
        if not domain:
            logger.debug("Could not guess domain for '%s'", company_name)
            # Still try generic addresses with the cleaned name as a last resort
            domain = _name_to_slug(company_name) + ".co.uk"

        candidates = _build_candidates(domain, directors)
        logger.debug(
            "%s — domain guess: %s, %d email candidates",
            company_name, domain, len(candidates),
        )

        if self._smtp_verify:
            verified = self._smtp_verify_candidates(candidates, domain)
            if verified:
                logger.info("SMTP-verified email for %s: %s", company_name, verified)
                return verified

        # Fallback: return the first generic address without verification
        fallback = next((c for c in candidates if c.startswith("info@")), candidates[0] if candidates else None)
        if fallback:
            logger.info("Using unverified fallback email for %s: %s", company_name, fallback)
        return fallback

    # ── Website / domain discovery ─────────────────────────────────────────

    def _guess_domain(self, company_name: str) -> Optional[str]:
        """
        Try common domain patterns derived from the company name.
        Returns the first domain that responds to an HTTP HEAD request.
        """
        slug = _name_to_slug(company_name)
        if not slug:
            return None

        candidates = [f"{slug}{tld}" for tld in _TLDS]

        for domain in candidates:
            for scheme in ("https", "http"):
                url = f"{scheme}://{domain}"
                try:
                    resp = requests.head(url, timeout=_REQUEST_TIMEOUT, allow_redirects=True)
                    if resp.status_code < 500:
                        logger.debug("Domain found: %s (%s)", domain, resp.status_code)
                        return domain
                except requests.RequestException:
                    continue

        return None

    # ── SMTP verification ──────────────────────────────────────────────────

    def _smtp_verify_candidates(
        self, candidates: list[str], domain: str
    ) -> Optional[str]:
        """
        Try SMTP RCPT TO verification for each candidate.
        Returns the first address that the mail server accepts (250 response).
        """
        mx = _get_mx_host(domain)
        if not mx:
            logger.debug("No MX record for %s — skipping SMTP verify", domain)
            return None

        for email in candidates:
            try:
                result = _smtp_check(email, mx)
                if result:
                    return email
                time.sleep(0.3)
            except Exception as exc:
                logger.debug("SMTP check failed for %s: %s", email, exc)
                break  # server likely blocking — stop trying

        return None


# ── Module-level helpers ───────────────────────────────────────────────────────

def _name_to_slug(company_name: str) -> str:
    """Convert 'BioTech Innovations Ltd' → 'biotechinnovations'."""
    name = company_name.lower()
    name = re.sub(r"[^a-z0-9 ]", "", name)
    words = [w for w in name.split() if w not in _STRIP_WORDS]
    return "".join(words)[:30]  # keep it reasonable


def _build_candidates(domain: str, directors: list[Director]) -> list[str]:
    """
    Build an ordered list of email candidates to try.

    Order: generic prefixes first (most likely to be monitored),
    then director-derived addresses.
    """
    seen: set[str] = set()
    candidates: list[str] = []

    def add(email: str) -> None:
        email = email.lower().strip()
        if email and email not in seen:
            seen.add(email)
            candidates.append(email)

    # Generic prefixes
    for prefix in _GENERIC_PREFIXES:
        add(f"{prefix}@{domain}")

    # Director-derived formats
    for d in directors:
        f, l = d.first_name.lower(), d.last_name.lower()
        if not l:
            continue
        add(f"{f}.{l}@{domain}")       # john.smith@company.co.uk
        add(f"{f}@{domain}")           # john@company.co.uk
        add(f"{f[0]}.{l}@{domain}" if f else "")   # j.smith@company.co.uk
        add(f"{l}@{domain}")           # smith@company.co.uk

    return candidates


def _get_mx_host(domain: str) -> Optional[str]:
    """Return the highest-priority MX hostname for a domain, or None."""
    try:
        import dns.resolver  # type: ignore
        answers = dns.resolver.resolve(domain, "MX")
        best = sorted(answers, key=lambda r: r.preference)[0]
        return str(best.exchange).rstrip(".")
    except Exception as exc:
        logger.debug("MX lookup failed for %s: %s", domain, exc)
        return None


def _smtp_check(email: str, mx_host: str) -> bool:
    """
    Return True if the SMTP server accepts RCPT TO for this address.
    Uses a dummy sender — no email is actually sent.
    """
    try:
        with smtplib.SMTP(mx_host, 25, timeout=_SMTP_TIMEOUT) as smtp:
            smtp.ehlo("internship-finder.local")
            code, _ = smtp.mail("probe@internship-finder.local")
            if code != 250:
                return False
            code, _ = smtp.rcpt(email)
            return code == 250
    except (smtplib.SMTPException, socket.error, OSError):
        return False
