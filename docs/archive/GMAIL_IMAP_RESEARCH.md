# Gmail IMAP Research — Label Access, Authentication & 2FA Code Extraction

**Date**: 2026-03-21
**Context**: Enhancing `GmailReader` class to read from custom Gmail labels (e.g., "Indy-2FA") instead of INBOX.

---

## Executive Summary

| Question | Answer | Source |
|----------|--------|--------|
| **Custom label access syntax** | `imap.select("Indy-2FA")` works directly; no prefix needed | [Gmail IMAP Extensions](https://developers.google.com/workspace/gmail/imap/imap-extensions) |
| **Gmail authentication 2026** | **App Password ONLY** (less secure apps deleted in May 2022, full enforcement March 2025) | [Google Workspace Updates](https://workspaceupdates.googleblog.com/2023/09/winding-down-google-sync-and-less-secure-apps-support.html) |
| **2FA required?** | Yes, to create App Password. If Jules has 2FA disabled → **must enable first** | [Google Account Help](https://support.google.com/accounts/answer/6010255) |
| **Alternative to App Password** | OAuth 2.0 with XOAUTH2 (more complex, future-proof) | [GitHub: howto-gmail-imap-oauth2](https://github.com/aler9/howto-gmail-imap-oauth2) |

---

## 1. Gmail IMAP Label Access Syntax

### Custom Labels (User-Created)

Custom labels in Gmail appear as regular IMAP folders. Use the label name directly:

```python
imap.select("Indy-2FA")      # ✓ Correct
imap.select("[Gmail]/Indy-2FA")  # ✗ Wrong (reserved prefix)
imap.select('"Indy-2FA"')    # ✗ Double-quoted (not needed)
```

**Rules**:
- Custom labels: **no prefix**, use exact name
- System labels: **`[Gmail]/`** or **`[GoogleMail]/`** prefix
  - Examples: `[Gmail]/All Mail`, `[Gmail]/Drafts`, `[Gmail]/Spam`, `[Gmail]/Sent Mail`
- UTF-7 encoding applied automatically by imaplib (transparent)

### Gmail System Labels Reference

| System Label | IMAP Folder Name |
|--------------|------------------|
| All Mail | `[Gmail]/All Mail` |
| Drafts | `[Gmail]/Drafts` |
| Sent Mail | `[Gmail]/Sent Mail` |
| Spam | `[Gmail]/Spam` |
| Trash | `[Gmail]/Trash` |
| Starred | `[Gmail]/Starred` |
| Important | `[Gmail]/Important` |

### Special Characters in Custom Label Names

Gmail allows custom labels with special characters. IMAP handles them:
- Spaces: `"Email Verifications"` → `imap.select("Email Verifications")`
- Hyphens: `"Indy-2FA"` → `imap.select("Indy-2FA")`
- Slashes (nested): `"Support/Urgent"` → `imap.select("Support/Urgent")`

**Key**: No additional quoting needed in Python imaplib — pass the label name as-is.

---

## 2. Gmail Authentication — App Password (Mandatory 2026)

### Timeline of Changes

| Date | Event |
|------|-------|
| **May 30, 2022** | "Less secure apps" toggle removed from Gmail |
| **March 14, 2025** | Full enforcement: IMAP/SMTP/POP/CalDAV/CardDAV require App Password or OAuth |
| **2026 onwards** | Regular Gmail password **DOES NOT WORK** for IMAP |

**Status as of March 2026**: Regular password login is **BLOCKED**. App Password is **MANDATORY**.

### Option 1: App Password (Simple, Recommended for Jules)

**Requirements**:
1. Gmail account with **2FA enabled** (2-step verification)
2. Google Account dashboard access

**Setup Steps** (exact sequence):

1. Go to **Google Account** → https://myaccount.google.com/
2. Left sidebar → **Security**
3. Under "How you sign in to Google" → **2-Step Verification**
   - If NOT enabled → click "Get started" and follow prompts (SMS or authenticator app)
4. After 2FA enabled, return to **Security** page
5. Under "How you sign in to Google" → **App passwords** (appears only if 2FA enabled)
6. **Select app** → Mail
7. **Select device** → Linux / Windows / Mac (your machine)
8. Click **Generate**
9. Google displays a **16-character password** (looks like `abcd efgh ijkl mnop`)
   - Copy this **app password** (spaces ignored)
10. Store in `.env`:
    ```
    GMAIL_IMAP_USER=jules@example.com
    GMAIL_IMAP_PASSWORD=abcdefghijklmnop  # 16-char app password
    ```

**Why App Password?**
- Uses same 2FA protection as regular login
- Works for IMAP/SMTP/POP only (not Gmail web)
- Can be revoked anytime without affecting account password
- No hardcoded full account password in code

### Option 2: OAuth 2.0 XOAUTH2 (Complex, Future-Proof)

If Jules prefers **not to enable 2FA** on his account, he can use OAuth 2.0:

**Pros**:
- No app password needed
- Short-lived tokens (refresh automatically)
- Tighter scopes (read-only if needed)

**Cons**:
- More complex implementation (needs refresh token flow)
- Requires Google Cloud Console setup
- Not needed for current MVP

**Implementation** (future roadmap):
- Use `google-auth-oauthlib` to obtain access token
- Exchange for IMAP XOAUTH2 string
- Pass to `imap.authenticate("XOAUTH2", oauth2_string)`

Reference: [howto-gmail-imap-oauth2](https://github.com/aler9/howto-gmail-imap-oauth2)

---

## 3. Current Status — Does Jules Have 2FA?

**User claim**: "My Gmail does NOT have 2FA"

**Implication**:
- Jules **cannot generate an App Password** (Google requires 2FA first)
- Regular password will **FAIL** with `[Gmail] LOGIN failed` error
- **Two options**:
  1. **Enable 2FA** on Gmail → generate App Password → use with IMAP
  2. **Use OAuth 2.0** (skip 2FA requirement, but more complex)

**Recommended path**: Enable 2FA (SMS or authenticator app). Takes 5 minutes.

---

## 4. Python Implementation — GmailReader with Custom Label

### Current Code Issues

The existing `GmailReader` (lines 120) uses:
```python
self._connection.select("INBOX")  # Always hardcoded
```

**Changes needed**:
1. Add parameter to select custom label
2. Add App Password authentication handling
3. Add error message hinting for authentication failures

### Enhanced Implementation

```python
from __future__ import annotations

import email
import imaplib
import logging
import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)

# Pattern for 2FA codes (4-8 digits, prefer 6-digit)
CODE_PATTERN = re.compile(r"\b(\d{4,8})\b")


class GmailReader:
    """Read emails via IMAP to extract 2FA verification codes from custom Gmail labels.

    Supports custom labels (e.g., "Indy-2FA") and system labels.
    Requires Gmail App Password (not regular password) due to Google's 2022+ policy.
    """

    IMAP_HOST = "imap.gmail.com"
    IMAP_PORT = 993

    def __init__(self, settings: Settings) -> None:
        """Initialize GmailReader with Gmail credentials.

        Args:
            settings: Settings instance with gmail_imap_user and gmail_imap_password.
                     Password should be 16-char App Password (not account password).

        Raises:
            ValueError: If gmail_imap_user or gmail_imap_password missing.
        """
        if not settings.gmail_imap_user or not settings.gmail_imap_password:
            msg = "gmail_imap_user and gmail_imap_password required in settings"
            raise ValueError(msg)

        self._email = settings.gmail_imap_user
        self._password = settings.gmail_imap_password
        self._connection: imaplib.IMAP4_SSL | None = None

    def connect(self) -> None:
        """Connect to Gmail IMAP server and authenticate with App Password.

        Raises:
            RuntimeError: If connection or login fails.
            Note: Regular Gmail password will fail. Use 16-char App Password.
        """
        try:
            self._connection = imaplib.IMAP4_SSL(self.IMAP_HOST, self.IMAP_PORT)
            self._connection.login(self._email, self._password)
            logger.info("Gmail IMAP connected")
        except imaplib.IMAP4.error as e:
            error_msg = str(e).lower()
            if "login" in error_msg or "auth" in error_msg:
                logger.error(
                    "Gmail IMAP login failed. "
                    "Ensure password is 16-char App Password, not account password. "
                    "See docs/GMAIL_IMAP_RESEARCH.md for setup."
                )
            else:
                logger.error("Gmail IMAP error: %s", error_msg)
            msg = "Gmail IMAP authentication failed"
            raise RuntimeError(msg) from e
        except Exception as e:
            logger.error("Gmail IMAP connection error")
            msg = "Gmail IMAP unexpected error"
            raise RuntimeError(msg) from e

    def get_latest_2fa_code(
        self,
        label: str = "INBOX",
        timeout_sec: int = 60,
        poll_interval_sec: int = 5,
        sender_filter: str = "indy",
    ) -> str | None:
        """Poll Gmail label for latest 2FA code with timeout.

        Args:
            label: Gmail label/folder name. Examples:
                - "INBOX" (system, default)
                - "Indy-2FA" (custom label)
                - "[Gmail]/All Mail" (system label)
            timeout_sec: Maximum seconds to wait for code (default 60).
            poll_interval_sec: Seconds between label checks (default 5).
            sender_filter: Filter emails by sender containing this string.

        Returns:
            The 2FA code as string (4-8 digits), or None if not found within timeout.

        Raises:
            RuntimeError: If not connected or label selection fails.
        """
        if not self._connection:
            self.connect()

        # Validate label exists and select it
        self._select_label(label)

        deadline = time.monotonic() + timeout_sec

        while time.monotonic() < deadline:
            code = self._check_label(sender_filter)
            if code:
                logger.info(
                    "2FA code extracted from Gmail",
                    extra={"label": label, "sender": sender_filter}
                )
                return code

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(poll_interval_sec, remaining))

        logger.warning(
            "2FA code not found within timeout",
            extra={"label": label, "timeout_sec": timeout_sec}
        )
        return None

    def _select_label(self, label: str) -> None:
        """Select a Gmail label/folder. Handle custom and system labels.

        Args:
            label: Label name (e.g., "Indy-2FA" for custom, "[Gmail]/Drafts" for system).

        Raises:
            RuntimeError: If label selection fails.
        """
        if not self._connection:
            msg = "Not connected to Gmail IMAP"
            raise RuntimeError(msg)

        try:
            status, _ = self._connection.select(label)
            if status != "OK":
                msg = f"Failed to select label: {label}"
                raise RuntimeError(msg)
            logger.info("Selected Gmail label", extra={"label": label})
        except imaplib.IMAP4.error as e:
            logger.error(
                "Label selection error",
                extra={"label": label, "error": str(e)}
            )
            msg = f"Cannot select label '{label}'. Ensure it exists in Gmail. "
            msg += "Custom labels must be created in Gmail web UI first."
            raise RuntimeError(msg) from e

    def _check_label(self, sender_filter: str) -> str | None:
        """Check currently selected label for recent unseen emails.

        Args:
            sender_filter: Only process emails with this string in From header.

        Returns:
            Extracted 2FA code if found, None otherwise.
        """
        if not self._connection:
            return None

        try:
            # Search for unseen emails in current label
            status, messages = self._connection.search(None, "UNSEEN")
            if status != "OK" or not messages[0]:
                return None

            msg_ids = messages[0].split()
            # Check most recent emails first (last 10)
            for msg_id in reversed(msg_ids[-10:]):
                status, msg_data = self._connection.fetch(msg_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email: Any = msg_data[0][1]  # type: ignore[index]
                msg = email.message_from_bytes(raw_email)  # type: ignore[arg-type]

                # Check sender
                sender = str(msg.get("From", "")).lower()
                if sender_filter.lower() not in sender:
                    continue

                # Extract body and find code
                body = self._get_email_body(msg)
                code = self._extract_code(body)
                if code:
                    return code

        except Exception as e:
            logger.error("Error checking Gmail label: %s", e)

        return None

    @staticmethod
    def _get_email_body(msg: Any) -> str:  # email.message.Message has poor typing
        """Extract text body from email message (plaintext or HTML).

        Args:
            msg: Email message object.

        Returns:
            Email body text, or empty string if no content found.
        """
        if msg.is_multipart():  # type: ignore[union-attr]
            for part in msg.walk():  # type: ignore[union-attr]
                content_type = part.get_content_type()  # type: ignore[union-attr]
                if content_type == "text/plain" or content_type == "text/html":
                    payload = part.get_payload(decode=True)  # type: ignore[union-attr]
                    if payload:
                        charset: str = part.get_content_charset() or "utf-8"  # type: ignore[union-attr]
                        return payload.decode(charset, errors="replace")
        else:
            payload = msg.get_payload(decode=True)  # type: ignore[union-attr]
            if payload:
                charset = msg.get_content_charset() or "utf-8"  # type: ignore[union-attr]
                return payload.decode(charset, errors="replace")
        return ""

    @staticmethod
    def _extract_code(text: str) -> str | None:
        """Extract verification code (4-8 digits) from email text.

        Prefers 6-digit codes (most common for 2FA), falls back to any match.

        Args:
            text: Email body text.

        Returns:
            Extracted code string, or None if no match found.
        """
        if not text:
            return None

        matches = CODE_PATTERN.findall(text)
        if not matches:
            return None

        # Prefer 6-digit codes (most common for 2FA)
        six_digit = [m for m in matches if len(m) == 6]
        if six_digit:
            return six_digit[0]

        return matches[0]

    def close(self) -> None:
        """Close IMAP connection and logout gracefully."""
        if self._connection:
            try:
                self._connection.close()
                self._connection.logout()
                logger.info("Gmail IMAP disconnected")
            except Exception:
                pass
            finally:
                self._connection = None
```

### Usage Examples

```python
from src.config import Settings
from src.adapters.gmail_reader import GmailReader

settings = Settings()  # Reads GMAIL_IMAP_USER, GMAIL_IMAP_PASSWORD from .env
reader = GmailReader(settings)

# Example 1: Read from custom label "Indy-2FA"
code = reader.get_latest_2fa_code(
    label="Indy-2FA",
    timeout_sec=60,
    sender_filter="indy"
)

# Example 2: Read from INBOX (default)
code = reader.get_latest_2fa_code(
    label="INBOX",
    timeout_sec=30,
    sender_filter="support@indy.fr"
)

# Example 3: Read from system label
code = reader.get_latest_2fa_code(
    label="[Gmail]/All Mail",
    timeout_sec=120
)

reader.close()
```

---

## 5. Gmail Filter Setup — Auto-Label Indy Emails

To automatically label incoming Indy verification emails, use Gmail's built-in filters:

**Steps**:

1. Go to **Gmail web** → https://mail.google.com
2. Click **Settings** (gear icon) → **See all settings**
3. Click **Filters and Blocked Addresses** tab
4. Click **Create a new filter**
5. In **From** field, enter: `noreply@indy.fr` (or your Indy notification address)
6. Click **Create filter**
7. Check **Apply label** → Create new label → Name: `Indy-2FA`
8. (Optional) Check **Skip the Inbox** if you don't want them in INBOX
9. Click **Create filter**

**Result**: All emails from Indy will be labeled "Indy-2FA" automatically, and `GmailReader` can pull from that label.

---

## 6. Error Handling & Troubleshooting

### Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `[Gmail] LOGIN failed` | Wrong password | Ensure you're using **16-char App Password**, not account password |
| `[Gmail] NO [CANNOT] Invalid mailbox name` | Label doesn't exist | Create label in Gmail web UI, or check spelling |
| `[Gmail] NO [CANNOT] ... EXAMINE` | Permission denied (rare) | Check label is not archived/deleted |
| `Timeout waiting for code` | Email didn't arrive | Check Gmail filter + sender address is correct |
| `login failed ... [ALERT] Credentials invalid` | 2FA not enabled | Must enable 2FA on Gmail before creating App Password |

### Debug Checklist

- [ ] Gmail account has **2FA enabled** (Security → 2-Step Verification)
- [ ] App Password generated and copied correctly
- [ ] `.env` has `GMAIL_IMAP_PASSWORD=<16-char-app-password>` (no spaces)
- [ ] Custom label exists in Gmail (`Settings → Labels → Manage labels`)
- [ ] Gmail filter active (`Settings → Filters and Blocked Addresses`)
- [ ] Test IMAP connection manually:
  ```python
  import imaplib
  imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
  imap.login("your@gmail.com", "your-16-char-app-password")
  status, mailboxes = imap.list()
  print(mailboxes)  # Should include "Indy-2FA"
  imap.close()
  ```

---

## 7. Security Considerations

### App Password vs. Account Password

| Aspect | App Password | Account Password |
|--------|--------------|------------------|
| **Scope** | IMAP/SMTP/POP only | Full Google account access |
| **2FA required** | Yes (must enable 2FA) | No |
| **Revocation** | Easy (delete in Google Account) | Full account compromise if exposed |
| **Exposure risk** | Limited to email protocols | Complete account takeover |
| **Recommended** | ✓ Yes for IMAP | ✗ Never use for IMAP |

### Best Practices

1. **Never commit `.env`** to git (already in `.gitignore`)
2. **Rotate App Password annually** or if suspected leak
3. **Log authentication errors** without exposing password
4. **Use IMAP4_SSL** (TLS 1.2+) — never unencrypted IMAP
5. **Mask credentials in logs**:
   ```python
   # Good
   logger.error("Login failed for user", extra={"user": "ju***@gmail.com"})

   # Bad
   logger.error(f"Login failed: {password}")
   ```

---

## 8. Testing

### Unit Test Template

```python
import pytest
from unittest.mock import MagicMock, patch
from src.adapters.gmail_reader import GmailReader
from src.config import Settings


@pytest.fixture
def mock_settings():
    settings = MagicMock(spec=Settings)
    settings.gmail_imap_user = "jules@example.com"
    settings.gmail_imap_password = "abcd efgh ijkl mnop"  # App password
    return settings


@patch("imaplib.IMAP4_SSL")
def test_connect_success(mock_imap_class, mock_settings):
    """Test successful Gmail IMAP connection with App Password."""
    mock_imap = MagicMock()
    mock_imap_class.return_value = mock_imap
    mock_imap.login.return_value = ("OK", [])

    reader = GmailReader(mock_settings)
    reader.connect()

    mock_imap_class.assert_called_once_with("imap.gmail.com", 993)
    mock_imap.login.assert_called_once_with("jules@example.com", "abcd efgh ijkl mnop")


@patch("imaplib.IMAP4_SSL")
def test_select_custom_label(mock_imap_class, mock_settings):
    """Test selecting custom label 'Indy-2FA'."""
    mock_imap = MagicMock()
    mock_imap_class.return_value = mock_imap
    mock_imap.login.return_value = ("OK", [])
    mock_imap.select.return_value = ("OK", [b"42"])  # 42 emails in label

    reader = GmailReader(mock_settings)
    reader.connect()
    reader._select_label("Indy-2FA")

    mock_imap.select.assert_called_once_with("Indy-2FA")


@patch("imaplib.IMAP4_SSL")
def test_get_latest_2fa_code_from_custom_label(mock_imap_class, mock_settings):
    """Test extracting 2FA code from 'Indy-2FA' label."""
    mock_imap = MagicMock()
    mock_imap_class.return_value = mock_imap
    mock_imap.login.return_value = ("OK", [])
    mock_imap.select.return_value = ("OK", [b"1"])
    mock_imap.search.return_value = ("OK", [b"1"])

    # Mock email with 2FA code
    email_body = b"""From: noreply@indy.fr
To: jules@example.com
Subject: Verification Code

Your verification code is: 123456

Do not share this code."""

    mock_imap.fetch.return_value = ("OK", [(b"", email_body)])

    reader = GmailReader(mock_settings)
    code = reader.get_latest_2fa_code(
        label="Indy-2FA",
        timeout_sec=5,
        sender_filter="indy"
    )

    assert code == "123456"
```

---

## 9. Checklist for Jules

- [ ] **Enable 2FA on Gmail**
  - [ ] Go to https://myaccount.google.com/security
  - [ ] Enable 2-Step Verification (SMS or authenticator app)

- [ ] **Generate App Password**
  - [ ] Go to https://myaccount.google.com/security
  - [ ] Click "App passwords" (appears only if 2FA enabled)
  - [ ] Select "Mail" + "Linux"
  - [ ] Generate and copy 16-char password

- [ ] **Store in `.env`**
  ```
  GMAIL_IMAP_USER=jules@example.com
  GMAIL_IMAP_PASSWORD=abcdefghijklmnop
  ```

- [ ] **Create Gmail label**
  - [ ] Go to https://mail.google.com
  - [ ] Settings → Labels → Create new label → "Indy-2FA"

- [ ] **Create Gmail filter**
  - [ ] Settings → Filters and Blocked Addresses → Create new filter
  - [ ] From: `noreply@indy.fr`
  - [ ] Apply label: "Indy-2FA"

- [ ] **Test connection**
  ```bash
  python -c "
  from src.adapters.gmail_reader import GmailReader
  from src.config import Settings
  reader = GmailReader(Settings())
  reader.connect()
  print('✓ Connected to Gmail IMAP')
  reader.close()
  "
  ```

---

## References

- [Gmail IMAP Extensions — Google Developers](https://developers.google.com/workspace/gmail/imap/imap-extensions)
- [App Passwords — Google Account Help](https://support.google.com/accounts/answer/185833)
- [Less Secure Apps Deprecation — Google Workspace Updates](https://workspaceupdates.googleblog.com/2023/09/winding-down-google-sync-and-less-secure-apps-support.html)
- [Python imaplib Documentation](https://docs.python.org/3/library/imaplib.html)
- [OAuth 2.0 IMAP Reference — GitHub](https://github.com/aler9/howto-gmail-imap-oauth2)
