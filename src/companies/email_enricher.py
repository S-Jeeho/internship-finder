"""
Email enricher — finds a contact email for a company using:

  1. Website discovery: guesses the company's domain from its name and
     checks if it responds to HTTP requests.
  2. Website scraping: visits the homepage and common pages (/contact,
     /about) to extract real email addresses listed on the site.
  3. SMTP verification: fallback for when no emails are scraped — checks
     guessed addresses against the domain's mail server.

Only saves an email address if there is reasonable confidence it exists.
If nothing is found the company is left without an email rather than
sending to a bouncing address.
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

_STRIP_WORDS = {
    "limited", "ltd", "plc", "llp", "llc", "inc",
    "holdings", "holding", "the", "and", "&", "co", "company",
}

_GENERIC_PREFIXES = ["info", "contact", "hello", "hr", "careers", "admin", "enquiries"]
_TLDS = [".co.uk", ".com", ".org.uk", ".org"]

_REQUEST_TIMEOUT = 6
_SMTP_TIMEOUT = 8

# Pages to scrape for contact emails (tried in order)
_CONTACT_PATHS = ["/contact", "/contact-us", "/about", "/about-us", "/team", "/"]

# Emails to discard even if scraped from the site
_IGNORE_PREFIXES = {"noreply", "no-reply", "donotreply", "do-not-reply", "bounce", "mailer"}


class EmailEnricher:
    def __init__(self, smtp_verify: bool = True) -> None:
        self._smtp_verify = smtp_verify

    def find_email(
        self,
        company_name: str,
        directors: list[Director],
        registered_address: str = "",
    ) -> Optional[str]:
        """
        Try to find a verified contact email for a company.

        Strategy:
          1. Discover domain via HTTP HEAD on guessed names.
          2. Scrape real emails from the company website.
          3. If scraping finds nothing, try SMTP-verified guesses.
          4. Return None rather than an unverified guess that will bounce.
        """
        domain = self._guess_domain(company_name)
        if not domain:
            logger.debug("No domain found for '%s' — skipping", company_name)
            return None

        # Try to find real emails on the website first
        scraped = self._scrape_emails_from_website(domain)
        if scraped:
            best = _pick_best_email(scraped)
            logger.info("Scraped email for %s: %s", company_name, best)
            return best

        # Fall back to SMTP-verified guesses
        if self._smtp_verify:
            candidates = _build_candidates(domain, directors)
            verified = self._smtp_verify_candidates(candidates, domain)
            if verified:
                logger.info("SMTP-verified email for %s: %s", company_name, verified)
                return verified

        logger.debug("No verified email found for %s", company_name)
        return None

    # ── Website / domain discovery ─────────────────────────────────────────

    def _guess_domain(self, company_name: str) -> Optional[str]:
        """Return the first domain that responds to HTTP HEAD, or None."""
        slug = _name_to_slug(company_name)
        if not slug:
            return None

        for domain in [f"{slug}{tld}" for tld in _TLDS]:
            for scheme in ("https", "http"):
                try:
                    resp = requests.head(
                        f"{scheme}://{domain}",
                        timeout=_REQUEST_TIMEOUT,
                        allow_redirects=True,
                    )
                    if resp.status_code < 500:
                        logger.debug("Domain found: %s (%s)", domain, resp.status_code)
                        return domain
                except requests.RequestException:
                    continue

        return None

    # ── Website scraping ───────────────────────────────────────────────────

    def _scrape_emails_from_website(self, domain: str) -> list[str]:
        """
        Visit the website's common pages and extract any email addresses found
        in the HTML. Returns deduplicated list, excluding no-reply addresses.
        """
        found: set[str] = set()

        for path in _CONTACT_PATHS:
            for scheme in ("https", "http"):
                url = f"{scheme}://{domain}{path}"
                try:
                    resp = requests.get(
                        url,
                        timeout=_REQUEST_TIMEOUT,
                        allow_redirects=True,
                        headers={"User-Agent": "Mozilla/5.0 (compatible; internship-finder/1.0)"},
                    )
                    if resp.status_code == 200:
                        emails = _extract_emails_from_html(resp.text, domain)
                        found.update(emails)
                        if found:
                            break  # got something from this path, no need to try http
                except requests.RequestException:
                    continue

            if found:
                break  # found emails on this page — stop searching

        return list(found)

    # ── SMTP verification ──────────────────────────────────────────────────

    def _smtp_verify_candidates(
        self, candidates: list[str], domain: str
    ) -> Optional[str]:
        mx = _get_mx_host(domain)
        if not mx:
            return None

        for email in candidates:
            try:
                if _smtp_check(email, mx):
                    return email
                time.sleep(0.3)
            except Exception as exc:
                logger.debug("SMTP check failed for %s: %s", email, exc)
                break

        return None


# ── Module-level helpers ───────────────────────────────────────────────────────

def _extract_emails_from_html(html: str, domain: str) -> list[str]:
    """
    Extract email addresses from HTML source, keeping only those that belong
    to the company's own domain or are clearly contact addresses.
    """
    raw = re.findall(r"[\w.+%-]+@[\w.-]+\.[a-zA-Z]{2,}", html)
    results: list[str] = []
    seen: set[str] = set()

    # Extract domain base without subdomain for matching
    domain_base = domain.lstrip("www.")

    for email in raw:
        email = email.lower().strip(".")
        if email in seen:
            continue
        seen.add(email)

        prefix = email.split("@")[0]
        email_domain = email.split("@")[1]

        # Skip noreply / automated addresses
        if any(prefix.startswith(ig) for ig in _IGNORE_PREFIXES):
            continue
        # Skip example / placeholder emails
        if "example" in email or "yourcompany" in email:
            continue
        # Prefer emails on the company's own domain
        if domain_base in email_domain or email_domain in domain_base:
            results.insert(0, email)  # prioritise own-domain emails
        else:
            results.append(email)

    return results


def _pick_best_email(emails: list[str]) -> str:
    """
    From a list of scraped emails, pick the most useful one for a job
    application: prefer hr/careers/jobs, then contact/hello/info, then others.
    """
    priority = ["careers", "jobs", "hr", "recruitment", "intern",
                "contact", "hello", "info", "enquiries", "admin"]
    for pref in priority:
        for email in emails:
            if email.startswith(pref + "@"):
                return email
    return emails[0]


def _name_to_slug(company_name: str) -> str:
    """Convert 'BioTech Innovations Ltd' → 'biotechinnovations'."""
    name = company_name.lower()
    name = re.sub(r"[^a-z0-9 ]", "", name)
    words = [w for w in name.split() if w not in _STRIP_WORDS]
    return "".join(words)[:30]


def _build_candidates(domain: str, directors: list[Director]) -> list[str]:
    seen: set[str] = set()
    candidates: list[str] = []

    def add(email: str) -> None:
        email = email.lower().strip()
        if email and email not in seen:
            seen.add(email)
            candidates.append(email)

    for prefix in _GENERIC_PREFIXES:
        add(f"{prefix}@{domain}")

    for d in directors:
        f, l = d.first_name.lower(), d.last_name.lower()
        if not l:
            continue
        add(f"{f}.{l}@{domain}")
        add(f"{f}@{domain}")
        add(f"{f[0]}.{l}@{domain}" if f else "")
        add(f"{l}@{domain}")

    return candidates


def _get_mx_host(domain: str) -> Optional[str]:
    try:
        import dns.resolver  # type: ignore
        answers = dns.resolver.resolve(domain, "MX")
        best = sorted(answers, key=lambda r: r.preference)[0]
        return str(best.exchange).rstrip(".")
    except Exception as exc:
        logger.debug("MX lookup failed for %s: %s", domain, exc)
        return None


def _smtp_check(email: str, mx_host: str) -> bool:
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
