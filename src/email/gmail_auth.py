"""
Gmail OAuth2 authentication manager.

Handles the full credential lifecycle:
  - First run: opens a browser for the user to grant access.
  - Subsequent runs: loads saved token and silently refreshes if expired.
  - Exposes get_gmail_service() which always returns a live, authenticated
    Gmail API resource — callers never touch credentials directly.

Required Google Cloud setup (one-time):
  1. Enable Gmail API in your Google Cloud project.
  2. Create an OAuth 2.0 Desktop App client.
  3. Download credentials.json and set GMAIL_CREDENTIALS_PATH in .env.

Scopes requested: send-only (least privilege).
"""

import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

# Send-only scope — we never read the inbox
_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class GmailAuthError(Exception):
    """Raised when authentication cannot be completed."""


def get_gmail_service(
    credentials_path: Path,
    token_path: Path,
):
    """
    Return an authenticated Gmail API service resource.

    Args:
        credentials_path: Path to the OAuth2 client credentials JSON file
                          downloaded from Google Cloud Console.
        token_path: Path where the access/refresh token will be stored
                    after the first successful login.

    Returns:
        A `googleapiclient.discovery.Resource` for the Gmail API v1.

    Raises:
        GmailAuthError: If credentials file is missing or the OAuth flow fails.
    """
    creds = _load_or_refresh_token(credentials_path, token_path)
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    logger.debug("Gmail service ready")
    return service


# ── Private helpers ───────────────────────────────────────────────────────────

def _load_or_refresh_token(credentials_path: Path, token_path: Path) -> Credentials:
    creds: Credentials | None = None

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), _SCOPES)
            logger.debug("Loaded Gmail token from %s", token_path)
        except Exception as exc:
            logger.warning("Could not load token file: %s — will re-authenticate", exc)
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        logger.info("Gmail token expired — refreshing")
        try:
            creds.refresh(Request())
            _save_token(creds, token_path)
            return creds
        except Exception as exc:
            logger.warning("Token refresh failed: %s — will re-authenticate", exc)

    # Full OAuth2 flow required
    creds = _run_oauth_flow(credentials_path)
    _save_token(creds, token_path)
    return creds


def _run_oauth_flow(credentials_path: Path) -> Credentials:
    if not credentials_path.exists():
        raise GmailAuthError(
            f"Gmail credentials file not found at '{credentials_path}'. "
            "Download it from Google Cloud Console and set GMAIL_CREDENTIALS_PATH in .env."
        )
    logger.info("Starting Gmail OAuth2 flow — a browser window will open")
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), _SCOPES)
    return flow.run_local_server(port=0)


def _save_token(creds: Credentials, token_path: Path) -> None:
    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    logger.debug("Gmail token saved to %s", token_path)
