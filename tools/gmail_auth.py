"""Gmail OAuth2 first-time authentication.

Run this ONCE to authorize SAP-Facture to read Gmail.
Opens browser for Google consent, saves token for future use.

Usage:
    uv run python tools/gmail_auth.py

Expected output:
    Token saved to credentials/gmail_token.json
    SUCCESS! Connected to Gmail. Found X recent emails.
      - From: ... | Subject: ...

Troubleshooting:
    - If "gmail_oauth.json not found": Download OAuth client from Google Cloud
      Console → APIs & Services → Credentials → OAuth 2.0 Client IDs
    - If "credentials/ not found": mkdir credentials/
    - If browser doesn't open: check firewall/localhost access
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CREDENTIALS_DIR = PROJECT_ROOT / "credentials"
CLIENT_FILE = CREDENTIALS_DIR / "gmail_oauth.json"
TOKEN_FILE = CREDENTIALS_DIR / "gmail_token.json"

# Gmail API scope (read-only)
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def ensure_credentials_dir() -> None:
    """Ensure credentials directory exists."""
    CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)


def load_or_refresh_token() -> Credentials | None:
    """Load existing token or refresh if expired."""
    if not TOKEN_FILE.exists():
        return None

    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            logger.info("Token expired, refreshing...")
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
            logger.info(f"Token refreshed and saved to {TOKEN_FILE}")

        return creds
    except Exception as e:
        logger.warning(f"Failed to load token: {e}")
        return None


def obtain_new_token() -> Credentials:
    """Obtain new token via browser OAuth flow."""
    if not CLIENT_FILE.exists():
        logger.error(f"ERROR: {CLIENT_FILE} not found!")
        logger.error(
            "Download it from Google Cloud Console → Credentials → OAuth client ID → Download JSON"
        )
        sys.exit(1)

    logger.info("Starting OAuth flow...")
    logger.info("A browser window will open for you to grant permission.")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
        creds = flow.run_local_server(port=8888, open_browser=True)
    except Exception as e:
        logger.error(f"OAuth flow failed: {e}")
        sys.exit(1)

    return creds


def save_token(creds: Credentials) -> None:
    """Save token to file."""
    TOKEN_FILE.write_text(creds.to_json())
    logger.info(f"✓ Token saved to {TOKEN_FILE}")


def test_gmail_connection(creds: Credentials) -> None:
    """Test Gmail connection and list recent emails."""
    try:
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(userId="me", maxResults=3).execute()
        messages = results.get("messages", [])

        logger.info(f"\n✓ SUCCESS! Connected to Gmail. Found {len(messages)} recent emails.")

        if messages:
            for msg in messages:
                try:
                    detail = (
                        service.users()
                        .messages()
                        .get(userId="me", id=msg["id"], format="metadata")
                        .execute()
                    )
                    headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
                    from_addr = headers.get("From", "?")[:50]
                    subject = headers.get("Subject", "?")[:60]
                    logger.info(f"  - From: {from_addr} | Subject: {subject}...")
                except Exception as e:
                    logger.debug(f"Failed to fetch message detail: {e}")
        else:
            logger.info("  (No recent emails found)")

    except Exception as e:
        logger.error(f"Failed to test Gmail connection: {e}")
        sys.exit(1)


def main() -> None:
    """Main authentication flow."""
    logger.info("=" * 70)
    logger.info("Gmail OAuth2 Authentication for SAP-Facture")
    logger.info("=" * 70)

    ensure_credentials_dir()

    # Try to load or refresh existing token
    creds = load_or_refresh_token()

    if creds and creds.valid:
        logger.info(f"✓ Using existing valid token from {TOKEN_FILE}")
    else:
        # Obtain new token via browser
        creds = obtain_new_token()
        save_token(creds)

    # Test the connection
    test_gmail_connection(creds)

    logger.info("\n" + "=" * 70)
    logger.info("Next steps:")
    logger.info("1. Add to .env:")
    logger.info("   GMAIL_OAUTH_CLIENT_FILE=credentials/gmail_oauth.json")
    logger.info("   GMAIL_OAUTH_TOKEN_FILE=credentials/gmail_token.json")
    logger.info("2. Update SAP-Facture to use Gmail reader for 2FA injection")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
