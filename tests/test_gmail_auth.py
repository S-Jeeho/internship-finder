"""Tests for src/email/gmail_auth.py — no real OAuth calls."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.email.gmail_auth import GmailAuthError, _save_token, get_gmail_service


# ── _save_token ───────────────────────────────────────────────────────────────

def test_save_token_writes_file(tmp_path: Path) -> None:
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = '{"token": "abc"}'
    token_path = tmp_path / "token.json"
    _save_token(mock_creds, token_path)
    assert token_path.exists()
    assert json.loads(token_path.read_text())["token"] == "abc"


def test_save_token_creates_parent_dirs(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "token.json"
    mock_creds = MagicMock()
    mock_creds.to_json.return_value = "{}"
    _save_token(mock_creds, nested)
    assert nested.exists()


# ── get_gmail_service — missing credentials file ──────────────────────────────

def test_get_gmail_service_raises_if_credentials_missing(tmp_path: Path) -> None:
    with pytest.raises(GmailAuthError, match="credentials file not found"):
        get_gmail_service(
            credentials_path=tmp_path / "missing.json",
            token_path=tmp_path / "token.json",
        )


# ── get_gmail_service — valid token already exists ───────────────────────────

def test_get_gmail_service_uses_existing_valid_token(tmp_path: Path) -> None:
    token_path = tmp_path / "token.json"
    creds_path = tmp_path / "creds.json"
    creds_path.write_text("{}")  # content doesn't matter — mocked

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.expired = False

    with (
        patch("src.email.gmail_auth.Credentials.from_authorized_user_file", return_value=mock_creds),
        patch("src.email.gmail_auth.build") as mock_build,
    ):
        token_path.write_text("{}")  # make it exist
        get_gmail_service(creds_path, token_path)
        mock_build.assert_called_once_with(
            "gmail", "v1", credentials=mock_creds, cache_discovery=False
        )


# ── get_gmail_service — expired token gets refreshed ─────────────────────────

def test_get_gmail_service_refreshes_expired_token(tmp_path: Path) -> None:
    token_path = tmp_path / "token.json"
    token_path.write_text("{}")
    creds_path = tmp_path / "creds.json"
    creds_path.write_text("{}")

    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "refresh_abc"
    mock_creds.to_json.return_value = "{}"

    with (
        patch("src.email.gmail_auth.Credentials.from_authorized_user_file", return_value=mock_creds),
        patch("src.email.gmail_auth.Request"),
        patch("src.email.gmail_auth.build"),
    ):
        get_gmail_service(creds_path, token_path)
        mock_creds.refresh.assert_called_once()
