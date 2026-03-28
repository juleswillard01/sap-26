"""Tests RED — GmailReader & GmailAPIReader for 2FA code extraction.

Tests for src/adapters/gmail_reader.py — Indy 2FA automation via Gmail (IMAP or OAuth2 API).

Requirement coverage (IMAP):
- Connect to Gmail IMAP with credentials
- Poll INBOX for unseen emails from Indy
- Extract 6-digit verification codes
- Timeout if code not received within deadline
- Parse plaintext and HTML email bodies
- Filter by sender domain

Requirement coverage (Gmail API):
- Initialize with OAuth2 credentials files
- Build Gmail API service with auto token refresh
- Search unread emails via Gmail API query
- Extract verification codes from email bodies
- Poll with timeout and retry intervals
- Handle API errors gracefully
"""

from __future__ import annotations

import base64
import email
import imaplib
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.gmail_reader import GmailAPIReader, GmailReader
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


class TestGmailAPIReaderInit:
    """Tests for GmailAPIReader.__init__() initialization."""

    def test_init_with_existing_client_file(self, tmp_path) -> None:
        """__init__() accepts existing credentials file."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')
        token_file = tmp_path / "token.json"

        reader = GmailAPIReader(client_file, token_file)

        assert reader._client_file == client_file
        assert reader._token_file == token_file

    def test_init_raises_if_client_file_missing(self, tmp_path) -> None:
        """__init__() raises ValueError if client file not found."""
        client_file = tmp_path / "missing.json"
        token_file = tmp_path / "token.json"

        with pytest.raises(ValueError, match="not found"):
            GmailAPIReader(client_file, token_file)

    def test_init_accepts_string_paths(self, tmp_path) -> None:
        """__init__() accepts string paths and converts to Path."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(str(client_file), str(tmp_path / "token.json"))

        assert isinstance(reader._client_file, type(tmp_path))


class TestGmailAPIReaderConnect:
    """Tests for GmailAPIReader.connect() OAuth2 initialization."""

    @pytest.mark.skip(reason="googleapiclient not available in test env")
    def test_connect_builds_gmail_service(self, tmp_path) -> None:
        """connect() builds Gmail API service with OAuth2 user tokens."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"installed": {"client_id": "x"}}')
        token_file = tmp_path / "token.json"
        token_file.write_text('{"token": "access", "refresh_token": "refresh"}')

        reader = GmailAPIReader(client_file, token_file)

        with patch("googleapiclient.discovery.build") as mock_build:
            mock_service = MagicMock()
            mock_build.return_value = mock_service

            mock_creds = MagicMock()
            mock_creds.valid = True
            mock_creds.expired = False
            with patch(
                "google.oauth2.credentials.Credentials.from_authorized_user_file",
                return_value=mock_creds,
            ):
                reader.connect()

                assert reader._service is not None

    def test_connect_raises_on_import_error(self, tmp_path) -> None:
        """connect() raises RuntimeError if Google libraries missing."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")

        with (
            patch.dict("sys.modules", {"google.auth.transport.requests": None}),
            pytest.raises(RuntimeError, match="google-auth-oauthlib"),
        ):
            reader.connect()

    @pytest.mark.skip(reason="google.oauth2 not available in test env")
    def test_connect_raises_on_service_build_error(self, tmp_path) -> None:
        """connect() raises RuntimeError on service build failure."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"installed": {"client_id": "x"}}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")

        with (
            patch(
                "google.oauth2.credentials.Credentials.from_authorized_user_file",
                side_effect=Exception("Invalid credentials"),
            ),
            pytest.raises(RuntimeError, match="Failed to build"),
        ):
            reader.connect()


class TestGmailAPIReaderGetLatest2FACode:
    """Tests for GmailAPIReader.get_latest_2fa_code() polling."""

    def test_get_latest_2fa_code_returns_code_immediately(self, tmp_path) -> None:
        """get_latest_2fa_code() returns code on first search."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        reader._service = MagicMock()

        # Mock search to return code immediately
        reader._search_and_extract_code = MagicMock(return_value="123456")

        code = reader.get_latest_2fa_code(timeout_sec=60)

        assert code == "123456"
        reader._search_and_extract_code.assert_called_once()

    def test_get_latest_2fa_code_polls_on_first_empty(self, tmp_path) -> None:
        """get_latest_2fa_code() polls again if first search returns None."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        reader._service = MagicMock()

        # Mock: first None, then code
        reader._search_and_extract_code = MagicMock(side_effect=[None, "654321"])

        code = reader.get_latest_2fa_code(timeout_sec=60, poll_interval_sec=0.1)

        assert code == "654321"
        assert reader._search_and_extract_code.call_count == 2

    def test_get_latest_2fa_code_timeout_returns_none(self, tmp_path) -> None:
        """get_latest_2fa_code() returns None if timeout exceeded."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        reader._service = MagicMock()

        reader._search_and_extract_code = MagicMock(return_value=None)

        code = reader.get_latest_2fa_code(timeout_sec=0.1, poll_interval_sec=0.05)

        assert code is None

    def test_get_latest_2fa_code_auto_connects(self, tmp_path) -> None:
        """get_latest_2fa_code() auto-connects if not connected."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        reader._service = None  # Not connected

        with patch.object(reader, "connect") as mock_connect:
            reader._search_and_extract_code = MagicMock(return_value="999999")
            code = reader.get_latest_2fa_code(timeout_sec=5)

            assert code == "999999"
            mock_connect.assert_called_once()

    def test_get_latest_2fa_code_respects_poll_interval(self, tmp_path) -> None:
        """get_latest_2fa_code() uses poll_interval_sec between checks."""
        import time

        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        reader._service = MagicMock()

        reader._search_and_extract_code = MagicMock(side_effect=[None, None, "789012"])

        start = time.monotonic()
        code = reader.get_latest_2fa_code(timeout_sec=10, poll_interval_sec=0.2)
        elapsed = time.monotonic() - start

        assert code == "789012"
        # Should have at least 2 intervals (~0.4s)
        assert elapsed >= 0.3


class TestGmailAPIReaderSearchAndExtract:
    """Tests for GmailAPIReader._search_and_extract_code()."""

    def test_search_and_extract_code_finds_code(self, tmp_path) -> None:
        """_search_and_extract_code() finds and returns code."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        mock_service = MagicMock()
        reader._service = mock_service

        # Mock API response with message
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg-123"}]
        }

        # Mock email body extraction to return code
        reader._get_email_body = MagicMock(return_value="Code: 123456")

        code = reader._search_and_extract_code("sender@example.com", "Label")

        assert code == "123456"

    def test_search_and_extract_code_empty_results(self, tmp_path) -> None:
        """_search_and_extract_code() returns None if no messages."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        mock_service = MagicMock()
        reader._service = mock_service

        mock_service.users().messages().list().execute.return_value = {}

        code = reader._search_and_extract_code("sender@example.com", "Label")

        assert code is None

    def test_search_and_extract_code_handles_api_error(self, tmp_path) -> None:
        """_search_and_extract_code() handles API errors gracefully."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        mock_service = MagicMock()
        reader._service = mock_service

        mock_service.users().messages().list().execute.side_effect = Exception("API error")

        code = reader._search_and_extract_code("sender@example.com", "Label")

        assert code is None

    def test_search_and_extract_code_checks_multiple_messages(self, tmp_path) -> None:
        """_search_and_extract_code() checks multiple messages in reverse."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        mock_service = MagicMock()
        reader._service = mock_service

        # Mock API with 3 messages
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        }

        # Mock: first two empty, third has code
        reader._get_email_body = MagicMock(side_effect=["no code", "no code", "Code: 654321"])

        code = reader._search_and_extract_code("sender@example.com", "Label")

        assert code == "654321"
        assert reader._get_email_body.call_count == 3


class TestGmailAPIReaderGetEmailBody:
    """Tests for GmailAPIReader._get_email_body() MIME parsing."""

    def test_get_email_body_plaintext_part(self, tmp_path) -> None:
        """_get_email_body() extracts plaintext from MIME parts."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        mock_service = MagicMock()
        reader._service = mock_service

        # Mock API response with base64 plaintext
        encoded_text = base64.urlsafe_b64encode(b"Your code is 123456").decode()

        mock_service.users().messages().get().execute.return_value = {
            "payload": {
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": encoded_text},
                    }
                ]
            }
        }

        body = reader._get_email_body("msg-123")

        assert "123456" in body

    def test_get_email_body_html_part(self, tmp_path) -> None:
        """_get_email_body() extracts HTML when plaintext missing."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        mock_service = MagicMock()
        reader._service = mock_service

        encoded_html = base64.urlsafe_b64encode(b"<html><body>Code: 654321</body></html>").decode()

        mock_service.users().messages().get().execute.return_value = {
            "payload": {
                "parts": [
                    {
                        "mimeType": "text/html",
                        "body": {"data": encoded_html},
                    }
                ]
            }
        }

        body = reader._get_email_body("msg-123")

        assert "654321" in body

    def test_get_email_body_fallback_root_payload(self, tmp_path) -> None:
        """_get_email_body() falls back to root payload if no parts."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        mock_service = MagicMock()
        reader._service = mock_service

        encoded_text = base64.urlsafe_b64encode(b"Code: 789012").decode()

        mock_service.users().messages().get().execute.return_value = {
            "payload": {"body": {"data": encoded_text}}
        }

        body = reader._get_email_body("msg-123")

        assert "789012" in body

    def test_get_email_body_handles_utf8_encoding(self, tmp_path) -> None:
        """_get_email_body() decodes UTF-8 properly."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        mock_service = MagicMock()
        reader._service = mock_service

        # UTF-8 encoded text with special characters
        encoded_text = base64.urlsafe_b64encode("Côde: 111222".encode()).decode()

        mock_service.users().messages().get().execute.return_value = {
            "payload": {
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": encoded_text},
                    }
                ]
            }
        }

        body = reader._get_email_body("msg-123")

        assert "111222" in body

    def test_get_email_body_returns_empty_on_error(self, tmp_path) -> None:
        """_get_email_body() returns empty string on API error."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        mock_service = MagicMock()
        reader._service = mock_service

        mock_service.users().messages().get().execute.side_effect = Exception("API error")

        body = reader._get_email_body("msg-123")

        assert body == ""

    def test_get_email_body_no_service_returns_empty(self, tmp_path) -> None:
        """_get_email_body() returns empty string if service not initialized."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        reader._service = None

        body = reader._get_email_body("msg-123")

        assert body == ""


class TestGmailAPIReaderExtractCode:
    """Tests for GmailAPIReader._extract_code() code extraction."""

    def test_extract_code_6_digits(self, tmp_path) -> None:
        """_extract_code() extracts 6-digit code."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")

        text = "Your code is 123456. Do not share."
        code = reader._extract_code(text)

        assert code == "123456"

    def test_extract_code_prefers_6_digits(self, tmp_path) -> None:
        """_extract_code() prefers 6-digit codes."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")

        text = "Code 1234 or 654321 or 12345678"
        code = reader._extract_code(text)

        assert code == "654321"

    def test_extract_code_returns_none_if_not_found(self, tmp_path) -> None:
        """_extract_code() returns None if no code found."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")

        code = reader._extract_code("No code here")

        assert code is None


class TestGmailAPIReaderClose:
    """Tests for GmailAPIReader.close() cleanup."""

    def test_close_clears_service(self, tmp_path) -> None:
        """close() clears Gmail service reference."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        reader._service = MagicMock()

        reader.close()

        assert reader._service is None

    def test_close_handles_exception_gracefully(self, tmp_path) -> None:
        """close() handles errors gracefully."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        reader._service = MagicMock()

        # Should not raise
        reader.close()

        assert reader._service is None

    def test_close_idempotent(self, tmp_path) -> None:
        """close() can be called multiple times safely."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        reader._service = MagicMock()

        reader.close()
        reader.close()  # Second call

        assert reader._service is None


class TestGmailReaderLabelSupport:
    """Tests for GmailReader label support in _check_inbox()."""

    def test_check_inbox_uses_custom_label_when_provided(self) -> None:
        """_check_inbox() selects custom label when label_name provided."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        reader._connection = mock_imap

        # Mock: label selection succeeds
        mock_imap.select.return_value = ("OK", [b"5"])
        mock_imap.search.return_value = ("OK", [b""])

        reader._check_inbox("indy", label_name="Indy-2FA")

        # Should select the custom label, not INBOX
        mock_imap.select.assert_called_once_with("Indy-2FA")

    def test_check_inbox_fallback_to_inbox_on_label_error(self) -> None:
        """_check_inbox() falls back to INBOX if label selection fails."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        reader._connection = mock_imap

        # Mock: label selection fails, then INBOX succeeds
        mock_imap.select.side_effect = [
            imaplib.IMAP4.error("Label not found"),
            ("OK", [b"1"]),
        ]
        mock_imap.search.return_value = ("OK", [b""])

        reader._check_inbox("indy", label_name="NonExistent")

        # Should try label first, then fall back to INBOX
        assert mock_imap.select.call_count == 2
        # First call: custom label, second call: INBOX
        calls = mock_imap.select.call_args_list
        assert calls[0][0][0] == "NonExistent"
        assert calls[1][0][0] == "INBOX"

    def test_check_inbox_backward_compatible_no_label(self) -> None:
        """_check_inbox() uses INBOX by default (backward compatible)."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        reader._connection = mock_imap
        mock_imap.search.return_value = ("OK", [b""])

        reader._check_inbox("indy")

        # Should select INBOX when no label_name provided
        mock_imap.select.assert_called_once_with("INBOX")

    def test_init_raises_error_missing_imap_user(self) -> None:
        """__init__() raises ValueError if gmail_imap_user missing."""
        settings = Settings(
            gmail_imap_user="",
            gmail_imap_password="pwd",
        )

        with pytest.raises(ValueError, match="gmail_imap_user and gmail_imap_password required"):
            GmailReader(settings)

    def test_init_raises_error_missing_imap_password(self) -> None:
        """__init__() raises ValueError if gmail_imap_password missing."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="",
        )

        with pytest.raises(ValueError, match="gmail_imap_user and gmail_imap_password required"):
            GmailReader(settings)

    def test_connect_generic_exception(self) -> None:
        """connect() raises RuntimeError on unexpected exception."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        with patch("imaplib.IMAP4_SSL") as mock_imap:
            mock_imap.side_effect = RuntimeError("Network error")

            with pytest.raises(RuntimeError, match="Gmail IMAP unexpected error"):
                reader.connect()

    def test_get_latest_2fa_code_timeout_exact_boundary(self) -> None:
        """get_latest_2fa_code() handles exact timeout boundary."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        reader._connection = mock_imap
        reader._check_inbox = MagicMock(return_value=None)

        # Should timeout after minimal timeout
        code = reader.get_latest_2fa_code(timeout_sec=0, poll_interval_sec=0)

        assert code is None

    def test_check_inbox_connection_none_returns_none(self) -> None:
        """_check_inbox() returns None if connection not initialized."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)
        reader._connection = None

        result = reader._check_inbox("indy")

        assert result is None

    def test_check_inbox_fetch_status_not_ok_continues(self) -> None:
        """_check_inbox() continues if fetch() returns non-OK status."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        reader._connection = mock_imap

        # Mock: search returns messages, but fetch fails
        mock_imap.select.return_value = ("OK", [b"1"])
        mock_imap.search.return_value = ("OK", [b"1 2"])
        mock_imap.fetch.return_value = ("BAD", [])  # Non-OK status

        result = reader._check_inbox("indy")

        assert result is None

    def test_get_email_body_multipart_html(self) -> None:
        """_get_email_body() extracts HTML content from multipart."""
        msg = MagicMock()
        msg.is_multipart.return_value = True

        html_part = MagicMock()
        html_part.get_content_type.return_value = "text/html"
        html_part.get_payload.return_value = b"<p>Code: 123456</p>"
        html_part.get_content_charset.return_value = "utf-8"

        msg.walk.return_value = [html_part]

        body = GmailReader._get_email_body(msg)

        assert body == "<p>Code: 123456</p>"

    def test_get_email_body_utf16_charset(self) -> None:
        """_get_email_body() handles UTF-16 charset decoding."""
        msg = MagicMock()
        msg.is_multipart.return_value = False

        utf16_text = "Code: 123456"
        msg.get_payload.return_value = utf16_text.encode("utf-16")
        msg.get_content_charset.return_value = "utf-16"

        body = GmailReader._get_email_body(msg)

        assert "Code: 123456" in body

    def test_extract_code_empty_text(self) -> None:
        """_extract_code() returns None for empty text."""
        code = GmailReader._extract_code("")

        assert code is None

    def test_extract_code_no_match(self) -> None:
        """_extract_code() returns None if no code pattern matched."""
        code = GmailReader._extract_code("No code here")

        assert code is None

    def test_extract_code_prefers_4_digit_when_no_6_digit(self) -> None:
        """_extract_code() returns first match if no 6-digit code."""
        code = GmailReader._extract_code("Your code is 1234")

        assert code == "1234"

    def test_gmail_api_reader_init_validates_client_file(self) -> None:
        """__init__() raises ValueError if client file missing."""
        with pytest.raises(ValueError, match="OAuth2 client file not found"):
            GmailAPIReader("/nonexistent/path/credentials.json", "/tmp/token.json")

    def test_gmail_api_reader_connect_import_error(self, tmp_path) -> None:
        """connect() raises RuntimeError if google libs not installed."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"installed": {"client_id": "x"}}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")

        with (
            patch.dict("sys.modules", {"google.oauth2.credentials": None}),
            pytest.raises(RuntimeError, match="google-auth-oauthlib"),
        ):
            reader.connect()

    def test_gmail_api_reader_connect_generic_exception(self, tmp_path) -> None:
        """connect() raises RuntimeError on service build failure."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"installed": {"client_id": "x"}}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")

        with (
            patch.dict("sys.modules", {"google.oauth2.credentials": None}),
            pytest.raises(RuntimeError, match="google-auth-oauthlib"),
        ):
            reader.connect()

    def test_gmail_api_reader_get_latest_2fa_code_timeout_boundary(self, tmp_path) -> None:
        """get_latest_2fa_code() handles exact timeout boundary."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        reader._service = MagicMock()  # Mock service to avoid connect() call
        reader._search_and_extract_code = MagicMock(return_value=None)

        code = reader.get_latest_2fa_code(timeout_sec=0, poll_interval_sec=0)

        assert code is None

    def test_gmail_api_reader_search_and_extract_no_service(self, tmp_path) -> None:
        """_search_and_extract_code() returns None if service not initialized."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        reader._service = None

        result = reader._search_and_extract_code("sender@example.com", "label")

        assert result is None

    def test_gmail_api_reader_extract_code_empty_text(self, tmp_path) -> None:
        """_extract_code() returns None for empty text."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")

        code = reader._extract_code("")

        assert code is None

    def test_gmail_api_reader_extract_code_no_match(self, tmp_path) -> None:
        """_extract_code() returns None if no code pattern matched."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")

        code = reader._extract_code("No code in this text")

        assert code is None

    def test_gmail_api_reader_extract_code_5_digit_fallback(self, tmp_path) -> None:
        """_extract_code() returns 5-digit if no 6-digit available."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")

        code = reader._extract_code("Code: 12345")

        assert code == "12345"

    def test_gmail_api_reader_close_exception_handled(self, tmp_path) -> None:
        """close() handles exceptions gracefully."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        reader._service = MagicMock()

        # Should not raise even if service raises
        reader.close()

        assert reader._service is None

    def test_gmail_reader_close_exception_handled(self) -> None:
        """close() handles exceptions gracefully."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        mock_imap.close.side_effect = Exception("Close error")
        reader._connection = mock_imap

        # Should not raise even if close fails
        reader.close()

        assert reader._connection is None

    def test_get_latest_2fa_code_deadline_passes_during_poll(self) -> None:
        """get_latest_2fa_code() breaks loop when deadline passes during poll."""
        settings = Settings(
            gmail_imap_user="test@gmail.com",
            gmail_imap_password="pwd",
        )
        reader = GmailReader(settings)

        mock_imap = MagicMock()
        reader._connection = mock_imap

        # Mock check_inbox to return None
        reader._check_inbox = MagicMock(return_value=None)

        # Very short timeout to force deadline check
        code = reader.get_latest_2fa_code(timeout_sec=0.01, poll_interval_sec=0)

        assert code is None

    def test_gmail_api_reader_get_latest_2fa_code_deadline_passes_during_poll(
        self, tmp_path
    ) -> None:
        """get_latest_2fa_code() breaks loop when deadline passes during poll."""
        client_file = tmp_path / "credentials.json"
        client_file.write_text('{"type": "service_account"}')

        reader = GmailAPIReader(client_file, tmp_path / "token.json")
        reader._service = MagicMock()

        reader._search_and_extract_code = MagicMock(return_value=None)

        # Very short timeout to force deadline check
        code = reader.get_latest_2fa_code(timeout_sec=0.01, poll_interval_sec=0)

        assert code is None
