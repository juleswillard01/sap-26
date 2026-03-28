"""Mock IMAP server for testing GmailReader 2FA code extraction.

Provides a minimal IMAP4rev1-compatible TCP server that satisfies
imaplib.IMAP4 for integration testing without real Gmail.

Supports: LOGIN, SELECT, SEARCH, FETCH, STORE, CLOSE, LOGOUT, NOOP, CAPABILITY.
"""

from __future__ import annotations

import logging
import socketserver
import threading
from datetime import UTC, datetime
from email.mime.text import MIMEText
from email.utils import format_datetime
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SENDER = "support@indy.fr"
DEFAULT_CODE = "123456"
DEFAULT_SUBJECT = "Code de vérification Indy"


class _Email:
    """Internal representation of a stored email."""

    __slots__ = ("body", "date", "seen", "sender", "subject")

    def __init__(
        self,
        sender: str,
        subject: str,
        body: str,
        date: datetime | None = None,
    ) -> None:
        self.sender = sender
        self.subject = subject
        self.body = body
        self.date = date or datetime.now(tz=UTC)
        self.seen = False

    def to_rfc822(self) -> bytes:
        """Serialize to RFC822 bytes suitable for IMAP FETCH."""
        msg = MIMEText(self.body, "plain", "utf-8")
        msg["From"] = self.sender
        msg["Subject"] = self.subject
        msg["Date"] = format_datetime(self.date)
        msg["To"] = "test@gmail.com"
        return msg.as_bytes()


class _IMAPRequestHandler(socketserver.StreamRequestHandler):
    """Handles one IMAP client connection with minimal protocol support.

    Speaks enough IMAP4rev1 to satisfy Python's imaplib.IMAP4.
    """

    server: MockGmail2FAServer  # type: ignore[assignment]

    def handle(self) -> None:
        """Main connection loop: greet, then parse tagged commands."""
        self._send_untagged("OK [CAPABILITY IMAP4rev1] Mock Gmail IMAP ready")
        try:
            self._command_loop()
        except (ConnectionResetError, BrokenPipeError):
            logger.debug("Client disconnected")
        except Exception:
            logger.exception("Unexpected error in IMAP handler")

    def _command_loop(self) -> None:
        """Read and dispatch tagged IMAP commands until LOGOUT or disconnect."""
        while True:
            raw = self.rfile.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            parts = line.split(None, 2)
            if len(parts) < 2:
                continue

            tag = parts[0]
            command = parts[1].upper()
            args = parts[2] if len(parts) > 2 else ""

            if command == "LOGOUT":
                self._cmd_logout(tag, args)
                break

            handler = self._dispatch(command)
            if handler:
                handler(tag, args)
            else:
                self._send_tagged(tag, "BAD", f"Unknown command {command}")

    def _dispatch(self, command: str) -> Any:
        """Map IMAP command name to handler method."""
        handlers: dict[str, Any] = {
            "LOGIN": self._cmd_login,
            "CAPABILITY": self._cmd_capability,
            "SELECT": self._cmd_select,
            "SEARCH": self._cmd_search,
            "FETCH": self._cmd_fetch,
            "STORE": self._cmd_store,
            "CLOSE": self._cmd_close,
            "LOGOUT": self._cmd_logout,
            "NOOP": self._cmd_noop,
        }
        return handlers.get(command)

    # ── IMAP command handlers ──

    def _cmd_login(self, tag: str, args: str) -> None:
        self._send_tagged(tag, "OK", "LOGIN completed")

    def _cmd_capability(self, tag: str, args: str) -> None:
        self._send_untagged("CAPABILITY IMAP4rev1")
        self._send_tagged(tag, "OK", "CAPABILITY completed")

    def _cmd_select(self, tag: str, args: str) -> None:
        count = len(self.server.emails)
        self._send_untagged(f"{count} EXISTS")
        self._send_untagged("0 RECENT")
        self._send_untagged("FLAGS (\\Seen \\Answered \\Flagged \\Deleted \\Draft)")
        self._send_tagged(tag, "OK", "[READ-WRITE] SELECT completed")

    def _cmd_search(self, tag: str, args: str) -> None:
        ids = self._matching_ids(args)
        id_str = " ".join(str(i) for i in ids)
        self._send_untagged(f"SEARCH {id_str}")
        self._send_tagged(tag, "OK", "SEARCH completed")

    def _cmd_fetch(self, tag: str, args: str) -> None:
        msg_num_str = args.split(None, 1)[0] if args else ""
        msg_num = int(msg_num_str)
        idx = msg_num - 1

        if 0 <= idx < len(self.server.emails):
            rfc822 = self.server.emails[idx].to_rfc822()
            size = len(rfc822)
            # Literal format: {size}\r\n<data>\r\n)
            self._send_raw(f"* {msg_num} FETCH (RFC822 {{{size}}}\r\n".encode())
            self._send_raw(rfc822)
            self._send_raw(b")\r\n")
            self.server.emails[idx].seen = True
        else:
            self._send_untagged(f"{msg_num} FETCH (RFC822 NIL)")

        self._send_tagged(tag, "OK", "FETCH completed")

    def _cmd_store(self, tag: str, args: str) -> None:
        parts = args.split(None, 1)
        msg_num = int(parts[0]) if parts else 0
        idx = msg_num - 1
        if 0 <= idx < len(self.server.emails):
            self.server.emails[idx].seen = True
        self._send_tagged(tag, "OK", "STORE completed")

    def _cmd_close(self, tag: str, args: str) -> None:
        self._send_tagged(tag, "OK", "CLOSE completed")

    def _cmd_logout(self, tag: str, args: str) -> None:
        self._send_untagged("BYE Mock Gmail IMAP server logging out")
        self._send_tagged(tag, "OK", "LOGOUT completed")

    def _cmd_noop(self, tag: str, args: str) -> None:
        self._send_tagged(tag, "OK", "NOOP completed")

    # ── Search logic ──

    def _matching_ids(self, args: str) -> list[int]:
        """Return 1-based message IDs matching the SEARCH criteria."""
        args_upper = args.upper()

        # UNSEEN filter
        if "UNSEEN" in args_upper:
            return [i + 1 for i, em in enumerate(self.server.emails) if not em.seen]

        # FROM filter: extract quoted value
        if "FROM" in args_upper:
            sender_filter = self._extract_quoted(args, "FROM")
            return [
                i + 1
                for i, em in enumerate(self.server.emails)
                if sender_filter.lower() in em.sender.lower()
            ]

        # Default: all messages
        return list(range(1, len(self.server.emails) + 1))

    @staticmethod
    def _extract_quoted(args: str, keyword: str) -> str:
        """Extract quoted value after a keyword in IMAP search args."""
        upper = args.upper()
        pos = upper.find(keyword.upper())
        if pos == -1:
            return ""
        rest = args[pos + len(keyword) :].strip()
        if rest.startswith('"'):
            end = rest.find('"', 1)
            return rest[1:end] if end > 0 else rest[1:]
        return rest.split()[0] if rest else ""

    # ── Wire helpers ──

    def _send_untagged(self, text: str) -> None:
        self._send_raw(f"* {text}\r\n".encode())

    def _send_tagged(self, tag: str, status: str, text: str) -> None:
        self._send_raw(f"{tag} {status} {text}\r\n".encode())

    def _send_raw(self, data: bytes) -> None:
        self.wfile.write(data)
        self.wfile.flush()


class MockGmail2FAServer(socketserver.ThreadingTCPServer):
    """Mock IMAP server pre-loaded with a 2FA verification email.

    Usage::

        server = MockGmail2FAServer(code="654321", sender="noreply@indy.fr")
        server.start()
        # ... use imaplib.IMAP4("127.0.0.1", server.port) ...
        server.stop()
    """

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        code: str = DEFAULT_CODE,
        sender: str = DEFAULT_SENDER,
        subject: str = DEFAULT_SUBJECT,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> None:
        self.emails: list[_Email] = []
        super().__init__((host, port), _IMAPRequestHandler)
        self._thread: threading.Thread | None = None

        # Pre-load initial 2FA email
        self.inject_email(code=code, sender=sender, subject=subject)
        logger.info(
            "Mock IMAP server initialized",
            extra={"port": self.port, "code": code},
        )

    @property
    def port(self) -> int:
        """Return the actual bound port (useful when port=0 for random)."""
        addr = self.server_address
        return int(addr[1])

    def inject_email(
        self,
        code: str = DEFAULT_CODE,
        sender: str = DEFAULT_SENDER,
        subject: str = DEFAULT_SUBJECT,
        body_template: str = "Votre code de verification Indy : {code}",
    ) -> None:
        """Add a new email to the server mailbox.

        Args:
            code: 2FA verification code to embed in body.
            sender: Email sender address.
            subject: Email subject line.
            body_template: Body text with {code} placeholder.
        """
        body = body_template.format(code=code)
        self.emails.append(_Email(sender=sender, subject=subject, body=body))
        logger.info(
            "Injected email",
            extra={"sender": sender, "code": code, "total": len(self.emails)},
        )

    def start(self) -> None:
        """Start serving in a background daemon thread."""
        self._thread = threading.Thread(
            target=self.serve_forever,
            daemon=True,
            name="mock-imap-server",
        )
        self._thread.start()
        logger.info("Mock IMAP server started", extra={"port": self.port})

    def stop(self) -> None:
        """Shutdown the server and wait for thread to join."""
        self.shutdown()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        self.server_close()
        logger.info("Mock IMAP server stopped")

    def clear_emails(self) -> None:
        """Remove all emails from the mailbox."""
        self.emails.clear()

    def reset(
        self,
        code: str = DEFAULT_CODE,
        sender: str = DEFAULT_SENDER,
    ) -> None:
        """Clear all emails and inject a fresh 2FA email."""
        self.clear_emails()
        self.inject_email(code=code, sender=sender)
