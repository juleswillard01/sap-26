"""Gmail readers for extracting 2FA codes from Indy verification emails.

CDC §3 support: Automates Indy 2FA verification code extraction via Gmail (IMAP or OAuth2 API).
Used to support headless Playwright automation for Indy transaction scraping.

Two implementations:
- GmailReader: IMAP protocol (requires app password)
- GmailAPIReader: Gmail API with OAuth2 (recommended, requires credentials.json)

Security note:
- IMAP: gmail_imap_user and gmail_imap_password must be in .env
- OAuth2: credentials files must be in credentials/ directory, .gitignore'd
- No credentials logged or exposed in error messages
"""

from __future__ import annotations

import base64
import email
import imaplib
import logging
import re
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)

# Pattern for 2FA codes (4-8 digits)
CODE_PATTERN = re.compile(r"\b(\d{4,8})\b")


class GmailReader:
    """Read emails via IMAP to extract 2FA verification codes from Indy."""

    IMAP_HOST = "imap.gmail.com"
    IMAP_PORT = 993

    def __init__(self, settings: Settings) -> None:
        """Initialize GmailReader with Gmail credentials.

        Args:
            settings: Settings instance with gmail_imap_user and gmail_imap_password.

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
        """Connect to Gmail IMAP server and authenticate.

        Raises:
            RuntimeError: If connection or login fails.
        """
        try:
            self._connection = imaplib.IMAP4_SSL(self.IMAP_HOST, self.IMAP_PORT)
            self._connection.login(self._email, self._password)
            logger.info("Gmail IMAP connected")
        except imaplib.IMAP4.error as e:
            logger.error("Gmail IMAP login failed")
            msg = "Gmail IMAP connection failed"
            raise RuntimeError(msg) from e
        except Exception as e:
            logger.error("Gmail IMAP connection error")
            msg = "Gmail IMAP unexpected error"
            raise RuntimeError(msg) from e

    def get_latest_2fa_code(
        self,
        timeout_sec: int = 60,
        poll_interval_sec: int = 5,
        sender_filter: str = "indy",
        label_name: str | None = None,
    ) -> str | None:
        """Poll Gmail INBOX for latest 2FA code from Indy with timeout.

        Args:
            timeout_sec: Maximum seconds to wait for code (default 60).
            poll_interval_sec: Seconds between inbox checks (default 5).
            sender_filter: Filter emails by sender containing this string.
            label_name: Optional Gmail label name to search (default None = INBOX).

        Returns:
            The 2FA code as string (4-8 digits), or None if not found within timeout.
        """
        if not self._connection:
            self.connect()

        deadline = time.monotonic() + timeout_sec

        while time.monotonic() < deadline:
            code = self._check_inbox(sender_filter, label_name=label_name)
            if code:
                logger.info("2FA code extracted from Gmail")
                return code

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(poll_interval_sec, remaining))

        logger.warning("2FA code not found within timeout")
        return None

    def _check_inbox(
        self,
        sender_filter: str,
        label_name: str | None = None,
    ) -> str | None:
        """Check INBOX or custom label for recent unseen emails matching sender filter.

        Args:
            sender_filter: Only process emails with this string in From header.
            label_name: Optional Gmail label name to search (default None = INBOX).

        Returns:
            Extracted 2FA code if found, None otherwise.
        """
        if not self._connection:
            return None

        try:
            # Select label: try custom label first, fall back to INBOX if needed
            if label_name:
                try:
                    self._connection.select(label_name)
                except imaplib.IMAP4.error:
                    # Label not found or error, fall back to INBOX
                    logger.warning("Label '%s' not found, falling back to INBOX", label_name)
                    self._connection.select("INBOX")
            else:
                self._connection.select("INBOX")

            # Search for recent emails from sender (today, read or unread)
            import datetime

            today = datetime.datetime.now(tz=datetime.UTC).strftime("%d-%b-%Y")
            status, messages = self._connection.search(
                None, f'(FROM "{sender_filter}" SINCE "{today}" SUBJECT "code")'
            )
            if status != "OK" or not messages[0]:
                # Fallback: try UNSEEN only
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
            logger.error("Error checking Gmail inbox: %s", e)

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


class GmailAPIReader:
    """Read Gmail via OAuth2 API to extract 2FA verification codes from Indy.

    Recommended over IMAP: requires less setup, better rate limits, native API support.
    OAuth2 flow handles token refresh automatically.
    """

    def __init__(self, client_file: str | Path, token_file: str | Path) -> None:
        """Initialize GmailAPIReader with OAuth2 credentials files.

        Args:
            client_file: Path to credentials.json (OAuth2 client ID/secret).
            token_file: Path to token.json (OAuth2 access/refresh tokens).

        Raises:
            ValueError: If client_file does not exist.
        """
        self._client_file = Path(client_file)
        self._token_file = Path(token_file)

        if not self._client_file.exists():
            msg = f"OAuth2 client file not found: {self._client_file}"
            raise ValueError(msg)

        self._service: Any = None

    def connect(self) -> None:
        """Load or refresh OAuth2 credentials and build Gmail service.

        Handles token refresh automatically. Creates token.json on first run.

        Raises:
            RuntimeError: If credential loading or service build fails.
        """
        try:
            from google.auth.transport.requests import Request  # type: ignore[import-untyped]
            from google.oauth2.service_account import Credentials  # type: ignore[import-untyped]
            from googleapiclient.discovery import build  # type: ignore[import-untyped]

            # Load credentials from client file
            creds = Credentials.from_service_account_file(
                str(self._client_file),
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            )

            # Refresh token if needed
            if creds.expired:
                creds.refresh(Request())

            # Build Gmail service
            self._service = build("gmail", "v1", credentials=creds)
            logger.info("Gmail API connected")

        except ImportError as e:
            logger.error("Google libraries not installed")
            msg = "google-auth-oauthlib and google-api-python-client required"
            raise RuntimeError(msg) from e
        except Exception as e:
            logger.error("Gmail API connection failed")
            msg = "Failed to build Gmail service"
            raise RuntimeError(msg) from e

    def get_latest_2fa_code(
        self,
        timeout_sec: int = 60,
        poll_interval_sec: int = 5,
        sender_filter: str = "noreply@indy.fr",
        label_name: str = "Indy-2FA",
    ) -> str | None:
        """Poll Gmail API for latest 2FA code with timeout.

        Searches unread emails from specified sender in given label,
        extracts verification code, and polls with timeout.

        Args:
            timeout_sec: Maximum seconds to wait for code (default 60).
            poll_interval_sec: Seconds between Gmail API checks (default 5).
            sender_filter: Filter emails by sender (default "noreply@indy.fr").
            label_name: Gmail label to search (default "Indy-2FA").

        Returns:
            The 2FA code as string (4-8 digits), or None if not found within timeout.
        """
        if not self._service:
            self.connect()

        deadline = time.monotonic() + timeout_sec

        while time.monotonic() < deadline:
            code = self._search_and_extract_code(sender_filter, label_name)
            if code:
                logger.info("2FA code extracted from Gmail API")
                return code

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(poll_interval_sec, remaining))

        logger.warning("2FA code not found within timeout")
        return None

    def _search_and_extract_code(
        self,
        sender_filter: str,
        label_name: str,
    ) -> str | None:
        """Search Gmail API for recent unread emails and extract 2FA code.

        Args:
            sender_filter: Email sender to filter (e.g., "noreply@indy.fr").
            label_name: Gmail label name to search (e.g., "Indy-2FA").

        Returns:
            Extracted 2FA code if found, None otherwise.
        """
        if not self._service:
            return None

        try:
            # Build Gmail API search query
            query = f"from:{sender_filter} is:unread newer_than:5m"

            # Search messages
            results = (
                self._service.users()
                .messages()
                .list(
                    userId="me",
                    q=query,
                    maxResults=10,
                )
                .execute()
            )

            messages = results.get("messages", [])
            if not messages:
                return None

            # Check most recent messages first
            for msg_meta in reversed(messages):
                msg_id = msg_meta["id"]
                body = self._get_email_body(msg_id)
                code = self._extract_code(body)
                if code:
                    return code

        except Exception as e:
            logger.error("Error searching Gmail API: %s", e)

        return None

    def _get_email_body(self, msg_id: str) -> str:
        """Retrieve email body text from Gmail API message.

        Handles both plaintext and HTML content, base64 decoding MIME payload.

        Args:
            msg_id: Gmail message ID.

        Returns:
            Email body text (plaintext or HTML), or empty string if not found.
        """
        if not self._service:
            return ""

        try:
            msg = (
                self._service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg_id,
                    format="full",
                )
                .execute()
            )

            payload = msg.get("payload", {})
            parts = payload.get("parts", [])

            # Check message parts for text content
            for part in parts:
                mime_type = part.get("mimeType", "")
                if mime_type in ("text/plain", "text/html"):
                    data = part.get("body", {}).get("data", "")
                    if data:
                        decoded = base64.urlsafe_b64decode(data).decode(
                            "utf-8",
                            errors="replace",
                        )
                        return decoded

            # Fallback: check root payload if no parts
            data = payload.get("body", {}).get("data", "")
            if data:
                decoded = base64.urlsafe_b64decode(data).decode(
                    "utf-8",
                    errors="replace",
                )
                return decoded

        except Exception as e:
            logger.error("Error retrieving email body: %s", e)

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
        """Cleanup Gmail service connection."""
        if self._service:
            try:
                self._service = None
                logger.info("Gmail API disconnected")
            except Exception:
                pass
