"""Smoke tests for the mock IMAP server.

Verifies that MockGmail2FAServer speaks enough IMAP4 protocol
to satisfy imaplib.IMAP4 for GmailReader testing.
"""

from __future__ import annotations

import email
import email.header
import imaplib

import pytest

from tests.mocks.gmail_2fa_server import MockGmail2FAServer


@pytest.fixture()
def imap_server() -> MockGmail2FAServer:
    """Start a mock IMAP server with default 2FA email, stop after test."""
    server = MockGmail2FAServer(code="123456", sender="support@indy.fr")
    server.start()
    yield server  # type: ignore[misc]
    server.stop()


class TestMockIMAPServerConnection:
    """Basic IMAP connection and authentication."""

    def test_connect_and_login(self, imap_server: MockGmail2FAServer) -> None:
        """imaplib.IMAP4 can connect and login to mock server."""
        conn = imaplib.IMAP4("127.0.0.1", imap_server.port)
        status, _ = conn.login("user", "pass")
        assert status == "OK"
        conn.logout()

    def test_select_inbox(self, imap_server: MockGmail2FAServer) -> None:
        """SELECT INBOX returns EXISTS count matching loaded emails."""
        conn = imaplib.IMAP4("127.0.0.1", imap_server.port)
        conn.login("user", "pass")
        status, data = conn.select("INBOX")
        assert status == "OK"
        # data[0] contains the mailbox count
        assert int(data[0]) == 1
        conn.close()
        conn.logout()


class TestMockIMAPServerSearch:
    """SEARCH command for finding emails."""

    def test_search_unseen_finds_preloaded_email(self, imap_server: MockGmail2FAServer) -> None:
        """SEARCH UNSEEN returns the pre-loaded email."""
        conn = imaplib.IMAP4("127.0.0.1", imap_server.port)
        conn.login("user", "pass")
        conn.select("INBOX")

        status, data = conn.search(None, "UNSEEN")
        assert status == "OK"
        assert data[0] is not None
        msg_ids = data[0].split()
        assert len(msg_ids) == 1
        assert msg_ids[0] == b"1"

        conn.close()
        conn.logout()

    def test_search_from_filter(self, imap_server: MockGmail2FAServer) -> None:
        """SEARCH FROM filters by sender address."""
        conn = imaplib.IMAP4("127.0.0.1", imap_server.port)
        conn.login("user", "pass")
        conn.select("INBOX")

        status, data = conn.search(None, "FROM", '"support@indy.fr"')
        assert status == "OK"
        msg_ids = data[0].split()
        assert len(msg_ids) == 1

        # Non-matching sender returns empty
        status, data = conn.search(None, "FROM", '"nobody@example.com"')
        assert status == "OK"
        assert data[0] == b""

        conn.close()
        conn.logout()


class TestMockIMAPServerFetch:
    """FETCH command for retrieving email content."""

    def test_fetch_rfc822_returns_valid_email(self, imap_server: MockGmail2FAServer) -> None:
        """FETCH (RFC822) returns parseable email with 2FA code in body."""
        conn = imaplib.IMAP4("127.0.0.1", imap_server.port)
        conn.login("user", "pass")
        conn.select("INBOX")

        status, msg_data = conn.fetch(b"1", "(RFC822)")
        assert status == "OK"

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        assert "support@indy.fr" in msg["From"]
        # Subject may be MIME Q-encoded due to accents
        decoded_subject = str(email.header.make_header(email.header.decode_header(msg["Subject"])))
        assert "Code de" in decoded_subject

        body = msg.get_payload(decode=True).decode("utf-8")
        assert "123456" in body

        conn.close()
        conn.logout()

    def test_fetch_marks_email_as_seen(self, imap_server: MockGmail2FAServer) -> None:
        """After FETCH, the email is marked as seen (UNSEEN search skips it)."""
        conn = imaplib.IMAP4("127.0.0.1", imap_server.port)
        conn.login("user", "pass")
        conn.select("INBOX")

        # Fetch marks as seen
        conn.fetch(b"1", "(RFC822)")

        # Re-select to refresh
        conn.select("INBOX")
        status, data = conn.search(None, "UNSEEN")
        assert status == "OK"
        # No unseen emails left
        assert data[0] == b""

        conn.close()
        conn.logout()


class TestMockIMAPServerInject:
    """Dynamic email injection after server start."""

    def test_inject_email_adds_new_message(self, imap_server: MockGmail2FAServer) -> None:
        """inject_email() adds a new email discoverable via SEARCH."""
        imap_server.inject_email(code="654321", sender="noreply@indy.fr")

        conn = imaplib.IMAP4("127.0.0.1", imap_server.port)
        conn.login("user", "pass")
        conn.select("INBOX")

        status, data = conn.search(None, "UNSEEN")
        assert status == "OK"
        msg_ids = data[0].split()
        # Original + injected = 2 unseen
        assert len(msg_ids) == 2

        # Fetch the new one (id=2) and verify code
        status, msg_data = conn.fetch(b"2", "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        body = msg.get_payload(decode=True).decode("utf-8")
        assert "654321" in body

        conn.close()
        conn.logout()

    def test_reset_clears_and_reloads(self, imap_server: MockGmail2FAServer) -> None:
        """reset() clears all emails and injects a fresh one."""
        imap_server.reset(code="999999")

        conn = imaplib.IMAP4("127.0.0.1", imap_server.port)
        conn.login("user", "pass")
        conn.select("INBOX")

        _status, data = conn.search(None, "UNSEEN")
        msg_ids = data[0].split()
        assert len(msg_ids) == 1

        _status, msg_data = conn.fetch(b"1", "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        body = msg.get_payload(decode=True).decode("utf-8")
        assert "999999" in body

        conn.close()
        conn.logout()


class TestMockIMAPServerCustomCode:
    """Parameterized server with custom 2FA codes."""

    def test_custom_code_in_email_body(self) -> None:
        """Server with custom code includes it in email body."""
        server = MockGmail2FAServer(code="987654")
        server.start()
        try:
            conn = imaplib.IMAP4("127.0.0.1", server.port)
            conn.login("u", "p")
            conn.select("INBOX")

            _status, msg_data = conn.fetch(b"1", "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            body = msg.get_payload(decode=True).decode("utf-8")
            assert "987654" in body

            conn.close()
            conn.logout()
        finally:
            server.stop()
