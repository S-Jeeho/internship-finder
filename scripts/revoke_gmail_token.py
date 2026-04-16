#!/usr/bin/env python3
"""
Utility — deletes the stored Gmail OAuth2 token so the next pipeline run
will trigger a fresh authentication flow (browser window).

Use this if:
  - You changed Gmail accounts
  - Your token was accidentally committed or compromised
  - You want to revoke access and re-grant it

Usage:
    python scripts/revoke_gmail_token.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import load_settings


def main() -> None:
    try:
        settings = load_settings()
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    token_path = settings.GMAIL_TOKEN_PATH
    if token_path.exists():
        token_path.unlink()
        print(f"Deleted Gmail token: {token_path}")
        print("Next pipeline run will prompt for re-authentication.")
    else:
        print(f"No token file found at {token_path} — nothing to delete.")


if __name__ == "__main__":
    main()
