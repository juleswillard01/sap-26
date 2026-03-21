"""Tests RED — GmailReader IMAP adapter for 2FA code extraction.

Tests for src/adapters/gmail_reader.py — Indy 2FA automation via IMAP Gmail.

Requirement coverage:
- Connect to Gmail IMAP with credentials
- Poll INBOX for unseen emails from Indy
- Extract 6-digit verification codes
- Timeout if code not received within deadline
- Parse plaintext and HTML email bodies
- Filter by sender domain
"""

from __future__ import annotations

import email
import imaplib
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.gmail_reader import GmailReader
from src.config import Settings


class TestGmailReaderConnect:
    """Tests for GmailReader.connect() initialization."""

    def test_connect_creates_imap_ssl_connection(self) -> None:
        """connect() establishes IMAP4_SSL connection."""
        settings = Settings(
            gmail_imap_user="jules.willard.pro@gmail.com",
            gmail_imap_password="test_app_password",
        )
        reader = GmailReader(settings)

        with patch("imaplib.IMAP4_SSL") as mock_imap:
            mock_instance = MagicMock()
            mock_imap.return_value = mock_instance

            reader.connect()

            mock_imap.assert_called_once_with("imap.gmail.com", 993)
            mock_instance.login.assert_called_once_with(
                "jules.willard.pro@gmail.com",
                "test_app_password",
            )

    def test_connect_stores_connection(self) -> None:
        """connect() stores IMAP connection reference."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        with patch("imaplib.IMAP4_SSL") as mock_imap:
            mock_instance = MagicMock()
            mock_imap.return_value = mock_instance
            reader.connect()

            assert reader._connection is not None

    def test_connect_raises_on_invalid_credentials(self) -> None:
        """connect() raises RuntimeError on login failure."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="wrong_password",
        )
        reader = GmailReader(settings)

        with patch("imaplib.IMAP4_SSL") as mock_imap:
            mock_instance = MagicMock()
            mock_instance.login.side_effect = imaplib.IMAP4.error("Invalid credentials")
            mock_imap.return_value = mock_instance

            with pytest.raises(RuntimeError):
                reader.connect()


class TestGmailReaderGetLatest2FACode:
    """Tests for GmailReader.get_latest_2fa_code() polling."""

    def test_get_latest_2fa_code_returns_code_on_success(self) -> None:
        """get_latest_2fa_code() returns extracted 2FA code."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        # Mock IMAP connection
        mock_imap = MagicMock()
        reader._connection = mock_imap

        # Mock inbox check to return code immediately
        reader._check_inbox = MagicMock(return_value="123456")

        code = reader.get_latest_2fa_code(timeout_sec=60)

        assert code == "123456"
        reader._check_inbox.assert_called_once()

    def test_get_latest_2fa_code_polls_on_first_check_empty(self) -> None:
        """get_latest_2fa_code() polls again if first check returns None."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)
        reader._connection = MagicMock()

        # Mock: first call None, second call returns code
        reader._check_inbox = MagicMock(side_effect=[None, "654321"])

        code = reader.get_latest_2fa_code(timeout_sec=60, poll_interval_sec=0.1)

        assert code == "654321"
        assert reader._check_inbox.call_count == 2

    def test_get_latest_2fa_code_timeout_returns_none(self) -> None:
        """get_latest_2fa_code() returns None if timeout exceeded."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)
        reader._connection = MagicMock()

        # Mock: never return code
        reader._check_inbox = MagicMock(return_value=None)

        code = reader.get_latest_2fa_code(timeout_sec=0.1, poll_interval_sec=0.05)

        assert code is None

    def test_get_latest_2fa_code_respects_poll_interval(self) -> None:
        """get_latest_2fa_code() uses poll_interval_sec between checks."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)
        reader._connection = MagicMock()

        # Mock: return None twice, then code
        reader._check_inbox = MagicMock(side_effect=[None, None, "789012"])

        import time

        start = time.monotonic()
        code = reader.get_latest_2fa_code(timeout_sec=10, poll_interval_sec=0.2)
        elapsed = time.monotonic() - start

        assert code == "789012"
        # Should have at least 2 poll intervals (~0.4s) before success
        assert elapsed >= 0.3

    def test_get_latest_2fa_code_connects_if_not_connected(self) -> None:
        """get_latest_2fa_code() auto-connects if not already connected."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)
        reader._connection = None  # Not connected

        with patch.object(reader, "connect") as mock_connect:
            reader._check_inbox = MagicMock(return_value="999999")
            code = reader.get_latest_2fa_code(timeout_sec=5)

            assert code == "999999"
            mock_connect.assert_called_once()


class TestGmailReaderCheckInbox:
    """Tests for GmailReader._check_inbox() filtering and parsing."""

    def test_check_inbox_filters_by_sender(self) -> None:
        """_check_inbox() filters emails by sender_filter."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        reader._connection = mock_imap

        # Mock: search returns 2 unseen emails
        mock_imap.search.return_value = ("OK", [b"1 2"])

        # Create test email
        msg = email.message.EmailMessage()
        msg["From"] = "noreply@indy.fr"
        msg["Subject"] = "Verification Code"
        msg.set_content("Your code is 123456")

        raw_email = msg.as_bytes()
        mock_imap.fetch.return_value = ("OK", [[b"", raw_email]])

        code = reader._check_inbox("indy")

        assert code == "123456"
        mock_imap.select.assert_called_once_with("INBOX")
        mock_imap.search.assert_called_once()

    def test_check_inbox_skips_wrong_sender(self) -> None:
        """_check_inbox() skips emails from wrong sender."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        reader._connection = mock_imap
        mock_imap.search.return_value = ("OK", [b"1"])

        # Email from wrong sender
        msg = email.message.EmailMessage()
        msg["From"] = "someone@example.com"
        msg.set_content("Your code is 654321")

        mock_imap.fetch.return_value = ("OK", [[b"", msg.as_bytes()]])

        code = reader._check_inbox("indy")

        # Should skip because sender doesn't contain "indy"
        assert code is None

    def test_check_inbox_returns_none_on_empty_inbox(self) -> None:
        """_check_inbox() returns None if no unseen emails."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        reader._connection = mock_imap
        mock_imap.search.return_value = ("OK", [b""])

        code = reader._check_inbox("indy")

        assert code is None

    def test_check_inbox_handles_fetch_error(self) -> None:
        """_check_inbox() returns None on fetch error."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        reader._connection = mock_imap
        mock_imap.search.return_value = ("OK", [b"1"])
        mock_imap.fetch.side_effect = imaplib.IMAP4.error("Fetch error")

        code = reader._check_inbox("indy")

        assert code is None


class TestGmailReaderExtractCode:
    """Tests for GmailReader._extract_code() regex matching."""

    def test_extract_code_6_digits(self) -> None:
        """_extract_code() extracts 6-digit verification code."""
        text = "Your verification code is 123456. Do not share."
        code = GmailReader._extract_code(text)
        assert code == "123456"

    def test_extract_code_4_digits(self) -> None:
        """_extract_code() extracts 4-digit code."""
        text = "Code: 1234"
        code = GmailReader._extract_code(text)
        assert code == "1234"

    def test_extract_code_8_digits(self) -> None:
        """_extract_code() extracts 8-digit code."""
        text = "Your authentication code is 12345678."
        code = GmailReader._extract_code(text)
        assert code == "12345678"

    def test_extract_code_prefers_6_digits(self) -> None:
        """_extract_code() prefers 6-digit codes over others."""
        text = "Code 1234 or 654321 or 12345678"
        code = GmailReader._extract_code(text)
        # Should prefer 6-digit match
        assert code == "654321"

    def test_extract_code_no_match_returns_none(self) -> None:
        """_extract_code() returns None if no code found."""
        text = "No code here, just text."
        code = GmailReader._extract_code(text)
        assert code is None

    def test_extract_code_empty_string_returns_none(self) -> None:
        """_extract_code() returns None for empty text."""
        code = GmailReader._extract_code("")
        assert code is None

    def test_extract_code_ignores_short_numbers(self) -> None:
        """_extract_code() ignores numbers < 4 digits."""
        text = "My number is 123 or 456"
        code = GmailReader._extract_code(text)
        assert code is None


class TestGmailReaderGetEmailBody:
    """Tests for GmailReader._get_email_body() MIME parsing."""

    def test_get_email_body_plaintext(self) -> None:
        """_get_email_body() extracts plaintext body."""
        msg = email.message.EmailMessage()
        msg.set_content("Hello, verification code is 123456")

        body = GmailReader._get_email_body(msg)

        assert "123456" in body
        assert "Hello" in body

    def test_get_email_body_multipart_plaintext(self) -> None:
        """_get_email_body() extracts plaintext from multipart."""
        msg = email.message.EmailMessage()
        msg["From"] = "test@example.com"
        msg["Subject"] = "Test"

        # Add plaintext part
        msg.set_content("Verification code: 654321")

        body = GmailReader._get_email_body(msg)

        assert "654321" in body

    def test_get_email_body_multipart_html(self) -> None:
        """_get_email_body() extracts HTML when plaintext missing."""
        msg = email.message_from_string(
            "From: test@example.com\n"
            "Subject: Test\n"
            "MIME-Version: 1.0\n"
            "Content-Type: text/html\n"
            "\n"
            "<html><body>Code: 789012</body></html>"
        )

        body = GmailReader._get_email_body(msg)

        assert "789012" in body

    def test_get_email_body_handles_encoding(self) -> None:
        """_get_email_body() handles UTF-8 encoding."""
        msg = email.message.EmailMessage()
        msg["From"] = "test@example.com"
        msg["Subject"] = "Test Encoding"
        msg.set_content("Cöde: 111222")

        body = GmailReader._get_email_body(msg)

        # Should decode properly
        assert "111222" in body

    def test_get_email_body_returns_empty_on_no_content(self) -> None:
        """_get_email_body() returns empty string if no content."""
        msg = email.message_from_string("From: test@example.com\nSubject: Empty")

        body = GmailReader._get_email_body(msg)

        assert body == ""


class TestGmailReaderClose:
    """Tests for GmailReader.close() cleanup."""

    def test_close_closes_imap_connection(self) -> None:
        """close() closes IMAP connection."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        reader._connection = mock_imap

        reader.close()

        mock_imap.close.assert_called_once()
        mock_imap.logout.assert_called_once()

    def test_close_handles_exception_gracefully(self) -> None:
        """close() handles disconnect errors gracefully."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        mock_imap.close.side_effect = Exception("Already closed")
        reader._connection = mock_imap

        # Should not raise
        reader.close()
        assert reader._connection is None

    def test_close_idempotent(self) -> None:
        """close() can be called multiple times safely."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        reader._connection = mock_imap

        reader.close()
        reader.close()  # Second call

        # Should handle gracefully
        assert reader._connection is None
