# Gmail OAuth2 — Dependency & Implementation Notes

## Dependencies to Add

The auth script (`tools/gmail_auth.py`) requires the following packages. Add to `pyproject.toml` if not already present:

```toml
[project]
dependencies = [
    # ... existing ...
    "google-auth-oauthlib>=1.2.0",      # OAuth2 flow for CLI apps
    "google-auth-httplib2>=0.2.0",      # HTTP transport for google-auth
    "google-api-python-client>=2.110.0", # Gmail API client
]
```

**Current status** (`pyproject.toml` as of 2026-03-21):
- ✅ `google-auth>=2.30` — already present
- ❌ `google-auth-oauthlib` — **NEEDS ADDING**
- ❌ `google-auth-httplib2` — **NEEDS ADDING** (for HTTP/2 support)
- ❌ `google-api-python-client` — **NEEDS ADDING**

### Update command

```bash
cd /home/jules/Documents/3-git/SAP/PAYABLES

# Add dependencies
uv add google-auth-oauthlib google-auth-httplib2 google-api-python-client

# Or manually edit pyproject.toml and run:
uv sync
```

---

## Script Location

```
/home/jules/Documents/3-git/SAP/PAYABLES/tools/gmail_auth.py
```

**First-time use**:
```bash
uv run python tools/gmail_auth.py
```

**What it does**:
1. Checks if `credentials/gmail_oauth.json` exists
2. Checks if `credentials/gmail_token.json` exists and is valid
3. If valid token found → uses it (with auto-refresh if expired)
4. If no valid token → opens browser for OAuth consent flow
5. Tests connection by listing 3 recent emails
6. Saves token to `credentials/gmail_token.json` (never checked in)

**Output on success**:
```
SUCCESS! Connected to Gmail. Found 3 recent emails.
  - From: sender@example.com | Subject: Your email subject...
  - From: noreply@indy.fr | Subject: Code de validation...
```

---

## Next: GmailReader Implementation

Once the auth script works, create `src/adapters/gmail_reader.py`:

```python
"""Gmail reader adapter for SAP-Facture 2FA automation."""

from __future__ import annotations

import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class GmailReader:
    """Read 2FA emails from Gmail for Indy Banking automation."""

    def __init__(
        self,
        oauth_file: str = "credentials/gmail_oauth.json",
        token_file: str = "credentials/gmail_token.json",
    ) -> None:
        """Initialize Gmail reader with OAuth credentials."""
        self.oauth_file = Path(oauth_file)
        self.token_file = Path(token_file)
        self.service = None
        self.creds = None

    def connect(self) -> None:
        """Connect to Gmail API using stored token."""
        if self.token_file.exists():
            self.creds = Credentials.from_authorized_user_file(
                str(self.token_file), SCOPES
            )

            if self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
                self.token_file.write_text(self.creds.to_json())

        if not self.creds or not self.creds.valid:
            raise RuntimeError("No valid Gmail token found. Run tools/gmail_auth.py")

        self.service = build("gmail", "v1", credentials=self.creds)
        logger.info("Gmail reader connected")

    def count_unread(self) -> int:
        """Count unread emails."""
        if not self.service:
            raise RuntimeError("Not connected. Call connect() first")

        result = self.service.users().messages().list(
            userId="me", q="is:unread"
        ).execute()
        return len(result.get("messages", []))

    def find_2fa_emails(self, max_results: int = 10) -> list[dict]:
        """Find 2FA emails from Indy (label: Indy-2FA)."""
        if not self.service:
            raise RuntimeError("Not connected. Call connect() first")

        result = self.service.users().messages().list(
            userId="me",
            q="label:Indy-2FA",
            maxResults=max_results,
        ).execute()

        messages = result.get("messages", [])
        emails = []

        for msg in messages:
            detail = self.service.users().messages().get(
                userId="me", id=msg["id"], format="metadata"
            ).execute()

            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            emails.append({
                "id": msg["id"],
                "from": headers.get("From", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
            })

        return emails

    def get_email_body(self, msg_id: str) -> str:
        """Get full email body by message ID."""
        if not self.service:
            raise RuntimeError("Not connected. Call connect() first")

        message = self.service.users().messages().get(
            userId="me", id=msg_id, format="full"
        ).execute()

        # Parse multipart/alternative to get text
        payload = message["payload"]
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    return part["body"].get("data", "")
        else:
            return payload["body"].get("data", "")

        return ""

    def extract_2fa_code(self, email_body: str) -> str | None:
        """Extract 6-digit code from email body."""
        import re

        # Look for 6-digit code (adjust regex if needed)
        match = re.search(r"\b(\d{6})\b", email_body)
        return match.group(1) if match else None

    def close(self) -> None:
        """Close the Gmail reader."""
        self.service = None
        self.creds = None
        logger.info("Gmail reader closed")
```

### Usage in Indy adapter

```python
from src.adapters.gmail_reader import GmailReader

# In InidyAdapter.login() or wherever 2FA is needed:
gmail = GmailReader()
gmail.connect()

# Get recent 2FA email
emails = gmail.find_2fa_emails(max_results=1)
if emails:
    body = gmail.get_email_body(emails[0]["id"])
    code = gmail.extract_2fa_code(body)
    if code:
        # Auto-fill 2FA code in Playwright
        await page.fill("input[name='2fa']", code)
        logger.info(f"2FA code injected: {code[:3]}***")

gmail.close()
```

---

## Security Notes

### OAuth Scopes

- ✅ `gmail.readonly` — READ-ONLY (no send/delete)
- ❌ `gmail.modify` — NOT requested (too permissive)
- ❌ `gmail` — NOT requested (full access)

### Token Storage

- `credentials/gmail_oauth.json` — OAuth client secret
  - Listed in `.gitignore`
  - Never committed
  - Read-only permission: `600` recommended

- `credentials/gmail_token.json` — Refresh token
  - Listed in `.gitignore`
  - Auto-generated on first auth
  - Auto-refreshed on expiration
  - Never logged or printed

### Environment Variables

In `.env`:
```env
GMAIL_OAUTH_CLIENT_FILE=credentials/gmail_oauth.json
GMAIL_OAUTH_TOKEN_FILE=credentials/gmail_token.json
```

Load via `pydantic_settings.BaseSettings`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    gmail_oauth_client_file: str = "credentials/gmail_oauth.json"
    gmail_oauth_token_file: str = "credentials/gmail_token.json"

    class Config:
        env_file = ".env"
```

---

## Testing

### Unit Tests

```python
import pytest
from unittest.mock import MagicMock, patch
from src.adapters.gmail_reader import GmailReader


@pytest.mark.asyncio
async def test_gmail_reader_connect():
    """Test connection with mocked service."""
    with patch("src.adapters.gmail_reader.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        reader = GmailReader()
        reader.creds = MagicMock()
        reader.creds.valid = True
        reader.creds.expired = False
        reader.connect()

        assert reader.service is not None


def test_extract_2fa_code():
    """Test 2FA code extraction."""
    reader = GmailReader()
    body = "Your verification code is: 123456. Do not share."
    code = reader.extract_2fa_code(body)
    assert code == "123456"


def test_extract_2fa_code_multiple_numbers():
    """Test extraction with multiple numbers (takes first 6-digit)."""
    reader = GmailReader()
    body = "Code: 654321 (expires in 300 seconds)"
    code = reader.extract_2fa_code(body)
    assert code == "654321"
```

---

## Checklist Before Production

- [ ] `google-auth-oauthlib` added to `pyproject.toml`
- [ ] `google-auth-httplib2` added to `pyproject.toml`
- [ ] `google-api-python-client` added to `pyproject.toml`
- [ ] Run `uv sync` to update lock file
- [ ] `tools/gmail_auth.py` runs successfully
- [ ] `credentials/gmail_token.json` created
- [ ] `src/adapters/gmail_reader.py` implemented
- [ ] Unit tests written and passing
- [ ] Integration test with `InidyAdapter` working
- [ ] No secrets logged (verify with grep)
- [ ] `.gitignore` covers all credential files

---

## References

- **Gmail API**: https://developers.google.com/gmail/api
- **OAuth 2.0 Scopes**: https://developers.google.com/identity/protocols/oauth2/scopes#gmail
- **google-auth-oauthlib**: https://github.com/googleapis/google-auth-library-python-oauthlib
- **Setup Guide**: `/home/jules/Documents/3-git/SAP/PAYABLES/docs/GMAIL_SETUP_GUIDE.md`

---

**Created**: 2026-03-21
**Project**: SAP-Facture Orchestrateur
