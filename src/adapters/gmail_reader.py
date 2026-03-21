"""IMAP Gmail reader for extracting 2FA codes from Indy verification emails.

CDC §3 support: Automates Indy 2FA verification code extraction via Gmail IMAP.
Used to support headless Playwright automation for Indy transaction scraping.

Security note:
- Credentials (gmail_imap_user, gmail_imap_password) must be in .env, never hardcoded
- App password recommended for Gmail (not account password)
- No credentials logged or exposed in error messages
"""

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
    ) -> str | None:
        """Poll Gmail INBOX for latest 2FA code from Indy with timeout.

        Args:
            timeout_sec: Maximum seconds to wait for code (default 60).
            poll_interval_sec: Seconds between inbox checks (default 5).
            sender_filter: Filter emails by sender containing this string.

        Returns:
            The 2FA code as string (4-8 digits), or None if not found within timeout.
        """
        if not self._connection:
            self.connect()

        deadline = time.monotonic() + timeout_sec

        while time.monotonic() < deadline:
            code = self._check_inbox(sender_filter)
            if code:
                logger.info("2FA code extracted from Gmail")
                return code

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(poll_interval_sec, remaining))

        logger.warning("2FA code not found within timeout")
        return None

    def _check_inbox(self, sender_filter: str) -> str | None:
        """Check INBOX for recent unseen emails matching sender filter.

        Args:
            sender_filter: Only process emails with this string in From header.

        Returns:
            Extracted 2FA code if found, None otherwise.
        """
        if not self._connection:
            return None

        try:
            self._connection.select("INBOX")

            # Search for unseen emails
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
