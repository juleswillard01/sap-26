"""Intercept Indy API calls — auto-login + CDP Network capture.

Reuses existing Indy2FAAdapter + GmailReader for automated login,
captures all XHR/fetch API calls via CDP Network domain events.

Usage:
    uv run python tools/indy_intercept.py

Output:
    - io/research/indy/api-endpoints.md  (markdown summary)
    - io/research/indy/api-raw.json      (full request/response data)
    - io/research/indy/*.png              (page screenshots)
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import nodriver as uc
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Project imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.adapters.gmail_reader import GmailReader
from src.adapters.indy_2fa_adapter import Indy2FAAdapter
from src.config import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

console = Console()

OUTPUT_DIR = Path("io/research/indy")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STATIC_EXTENSIONS = {
    ".js",
    ".css",
    ".png",
    ".jpg",
    ".svg",
    ".woff",
    ".woff2",
    ".ttf",
    ".ico",
    ".gif",
}
TRACKING_DOMAINS = {
    "google-analytics",
    "googletagmanager",
    "cloudflare",
    "intercom",
    "sentry",
    "amplitude",
    "segment",
    "hotjar",
}

PAGES_TO_EXPLORE = [
    ("/pilotage", "Pilotage"),
    ("/transactions", "Transactions"),
    ("/comptabilite", "Comptabilite"),
    ("/documents", "Documents"),
    ("/comptes-pro", "Comptes-Pro"),
]


class NetworkInterceptor:
    """Capture API calls via CDP Network events with Rich live display."""

    def __init__(self) -> None:
        self.requests: dict[str, dict[str, Any]] = {}
        self.api_calls: list[dict[str, Any]] = []
        self.auth_tokens: dict[str, Any] = {}
        self.request_count: int = 0
        self.filtered_count: int = 0

    def _capture_auth(self, headers: dict[str, str], url: str) -> None:
        """Extract auth-related headers and persist to disk immediately."""
        auth_keys = {"authorization", "cookie", "x-api-key", "x-csrf-token", "x-access-token"}
        found: dict[str, str] = {}
        for key, value in headers.items():
            if key.lower() in auth_keys:
                found[key] = value

        if not found:
            return

        # Update with latest tokens (overwrite per key)
        for key, value in found.items():
            self.auth_tokens[key] = {
                "value": value,
                "url": url,
                "timestamp": datetime.now().isoformat(),
            }

        # Write immediately — gitignored, sensitive
        auth_file = OUTPUT_DIR / "api-auth.json"
        auth_file.write_text(json.dumps(self.auth_tokens, indent=2, default=str))
        console.print(f"  [bold yellow]AUTH captured: {', '.join(found.keys())}[/bold yellow]")

    def _is_noise(self, url: str) -> bool:
        """Check if URL is a static asset or tracking pixel."""
        url_lower = url.lower()
        return any(ext in url_lower for ext in STATIC_EXTENSIONS) or any(
            domain in url_lower for domain in TRACKING_DOMAINS
        )

    def on_request(self, event: uc.cdp.network.RequestWillBeSent) -> None:
        """CDP Network.requestWillBeSent handler."""
        request = event.request
        url = request.url
        self.request_count += 1

        if self._is_noise(url):
            self.filtered_count += 1
            return

        # Extract resource type — CDP enum .value gives the raw string
        raw_type = getattr(event, "type_", None) or getattr(event, "type", None)
        resource_type = getattr(raw_type, "value", str(raw_type or "OTHER")).upper()

        headers = request.headers or {}

        # Extract auth tokens/cookies (raw, for api-auth.json)
        raw_headers = {str(k): str(v) for k, v in headers.items()} if headers else {}
        self._capture_auth(raw_headers, url)

        self.requests[str(event.request_id)] = {
            "url": url,
            "method": request.method or "GET",
            "headers": _mask_headers(headers),
            "headers_raw": raw_headers,
            "post_data": request.post_data or "",
            "type": resource_type,
            "timestamp": datetime.now().isoformat(),
        }

        console.print(f"  [dim cyan]-> {request.method} {url[:120]}[/dim cyan]")

    def on_response(self, event: uc.cdp.network.ResponseReceived) -> None:
        """CDP Network.responseReceived handler."""
        request_id = str(event.request_id)
        if request_id not in self.requests:
            return

        response = event.response
        entry = self.requests[request_id]
        entry["status"] = response.status
        entry["status_text"] = response.status_text or ""
        entry["content_type"] = str((response.headers or {}).get("content-type", ""))
        entry["url"] = response.url or entry["url"]

        self.api_calls.append(entry)

        status_style = "green" if 200 <= response.status < 300 else "red"
        console.print(
            f"  [dim]<- [{status_style}]{response.status}[/{status_style}] "
            f"{entry['method']} {entry['url'][:100]}[/dim]"
        )

        # Write to disk after every response — no data loss on kill
        (OUTPUT_DIR / "api-raw.json").write_text(self.export_json())
        (OUTPUT_DIR / "api-endpoints.md").write_text(self.export_markdown())

    def export_markdown(self) -> str:
        """Export API calls as markdown summary."""
        lines = [
            "# Indy API Endpoints -- Reverse Engineering\n",
            f"Generated: {datetime.now().isoformat()}",
            f"Total requests: {self.request_count}",
            f"Static/tracking filtered: {self.filtered_count}",
            f"API calls captured: {len(self.api_calls)}\n",
            "## Endpoints Summary\n",
            "| Method | URL | Status | Content-Type |",
            "|---|---|---|---|",
        ]

        seen: set[str] = set()
        for call in self.api_calls:
            base_url = call["url"].split("?")[0]
            key = f"{call['method']} {base_url}"
            if key in seen:
                continue
            seen.add(key)
            ct = call.get("content_type", "?").split(";")[0]
            lines.append(
                f"| {call['method']} | {base_url[:80]} | {call.get('status', '?')} | {ct} |"
            )

        lines.append(f"\n## Detailed Calls ({len(self.api_calls)} total)\n")
        for i, call in enumerate(self.api_calls, 1):
            lines.append(f"### {i}. {call['method']} {call['url'][:100]}")
            lines.append(f"- **Status**: {call.get('status', '?')} {call.get('status_text', '')}")
            lines.append(f"- **Content-Type**: {call.get('content_type', '?')}")
            lines.append(f"- **Timestamp**: {call.get('timestamp', '?')}")
            if call.get("post_data"):
                body = str(call["post_data"])[:500]
                lines.append(f"- **Body**: ```{body}```")
            lines.append("")

        return "\n".join(lines)

    def export_json(self) -> str:
        """Export API calls as JSON."""
        return json.dumps(self.api_calls, indent=2, default=str)

    def print_summary(self) -> None:
        """Print Rich table of discovered endpoints."""
        table = Table(title="Indy API Endpoints Discovered", show_lines=True)
        table.add_column("Method", style="bold cyan")
        table.add_column("URL", style="white", max_width=80)
        table.add_column("Status", justify="center")
        table.add_column("Type", style="dim")

        seen: set[str] = set()
        for call in self.api_calls:
            base_url = call["url"].split("?")[0]
            key = f"{call['method']} {base_url}"
            if key in seen:
                continue
            seen.add(key)

            status = str(call.get("status", "?"))
            status_style = "green" if status.startswith("2") else "red"
            table.add_row(
                call["method"],
                base_url[:80],
                f"[{status_style}]{status}[/{status_style}]",
                call.get("type", "?"),
            )

        console.print(table)


def _mask_headers(headers: dict[str, Any] | None) -> dict[str, str]:
    """Mask sensitive header values (RGPD)."""
    if not headers:
        return {}

    masked: dict[str, str] = {}
    sensitive = {"authorization", "cookie", "token", "secret", "x-api-key"}

    for key, value in headers.items():
        if any(s in key.lower() for s in sensitive):
            val_str = str(value)
            masked[key] = val_str[:30] + "..." if len(val_str) > 30 else "***"
        else:
            masked[key] = str(value)

    return masked


async def main() -> None:
    """Auto-login Indy + CDP network interception + page exploration."""
    console.print(
        Panel(
            "[bold]Indy Network Interceptor[/bold]\nAuto-login (2FA Gmail) + CDP capture",
            style="blue",
        )
    )

    # --- Step 1: Settings ---
    console.print("\n[bold cyan]1/5[/bold cyan] Loading settings from .env...")
    try:
        settings = Settings()
    except Exception as e:
        console.print(f"[red]Settings load failed: {e}[/red]")
        return

    missing: list[str] = []
    if not settings.indy_email or not settings.indy_password:
        missing.extend(["INDY_EMAIL", "INDY_PASSWORD"])
    if not settings.gmail_imap_user or not settings.gmail_imap_password:
        missing.extend(["GMAIL_IMAP_USER", "GMAIL_IMAP_PASSWORD"])
    if missing:
        console.print(f"[red]Missing in .env: {', '.join(missing)}[/red]")
        return

    console.print("[green]  Settings OK[/green]")

    # --- Step 2: Gmail IMAP for 2FA ---
    console.print("\n[bold cyan]2/5[/bold cyan] Connecting Gmail IMAP (2FA codes)...")
    gmail_reader = GmailReader(settings)
    try:
        gmail_reader.connect()
    except Exception as e:
        console.print(f"[red]Gmail connection failed: {e}[/red]")
        return
    console.print("[green]  Gmail IMAP connected[/green]")

    # --- Step 3: Browser + CDP ---
    console.print("\n[bold cyan]3/5[/bold cyan] Launching browser (headed)...")
    browser = await uc.start(
        headless=False,
        browser_args=["--no-first-run", "--no-default-browser-check"],
    )

    interceptor = NetworkInterceptor()

    try:
        page = await browser.get("https://app.indy.fr/connexion")
        await page.sleep(3)

        # Enable CDP BEFORE login to capture auth endpoints too
        console.print("  Enabling CDP Network capture...")
        try:
            await page.send(
                uc.cdp.network.enable(
                    max_total_buffer_size=100 * 1024 * 1024,
                    max_resource_buffer_size=10 * 1024 * 1024,
                    max_post_data_size=1024 * 1024,
                )
            )
            page.add_handler(uc.cdp.network.RequestWillBeSent, interceptor.on_request)
            page.add_handler(uc.cdp.network.ResponseReceived, interceptor.on_response)
            console.print("[green]  CDP Network enabled[/green]")
        except Exception as e:
            console.print(f"[yellow]  CDP enable warning: {e}[/yellow]")

        await page.save_screenshot(str(OUTPUT_DIR / "01-login-page.png"))

        # --- Step 3b: Flush stale 2FA emails BEFORE triggering login ---
        console.print("  Flushing old Indy 2FA emails...")
        flushed = gmail_reader.flush_old_emails(sender_filter="support@indy.fr")
        console.print(f"  [green]{flushed} stale emails marked as read[/green]")

        # --- Step 4: Auto-login ---
        console.print("\n[bold cyan]4/5[/bold cyan] Auto-login Indy (2FA via Gmail IMAP)...")
        adapter_2fa = Indy2FAAdapter()
        login_ok = await adapter_2fa.auto_2fa_login(
            page=page,
            gmail_reader=gmail_reader,
            email=settings.indy_email,
            password=settings.indy_password,
            timeout_sec=120,
        )

        if not login_ok:
            console.print("[red]  Login FAILED[/red]")
            await page.save_screenshot(str(OUTPUT_DIR / "02-login-failed.png"))
            return

        console.print("[green]  Login OK[/green]")
        await page.sleep(5)

        # Extract Firebase refresh token from browser storage
        console.print("  Extracting Firebase tokens...")
        try:
            firebase_tokens = await page.evaluate("""
                (async () => {
                    // Firebase stores tokens in IndexedDB: firebaseLocalStorageDb
                    const dbs = await indexedDB.databases();
                    const fbDb = dbs.find(db => db.name && db.name.includes('firebase'));
                    if (!fbDb) return {error: 'no firebase db found', dbs: dbs.map(d => d.name)};

                    return new Promise((resolve, reject) => {
                        const req = indexedDB.open(fbDb.name);
                        req.onsuccess = (event) => {
                            const db = event.target.result;
                            const stores = Array.from(db.objectStoreNames);
                            const store = stores.find(s => s.includes('firebaseLocalStorage')) || stores[0];
                            if (!store) { resolve({error: 'no store found', stores}); return; }

                            const tx = db.transaction(store, 'readonly');
                            const os = tx.objectStore(store);
                            const getAll = os.getAll();
                            getAll.onsuccess = () => {
                                const items = getAll.result;
                                const tokens = {};
                                for (const item of items) {
                                    const val = item.value || item;
                                    if (val.spiTokenKey || val.refreshToken || val.accessToken) {
                                        tokens.refreshToken = val.spiTokenKey?.refreshToken || val.refreshToken;
                                        tokens.accessToken = val.spiTokenKey?.accessToken || val.accessToken;
                                        tokens.expirationTime = val.spiTokenKey?.expirationTime || val.expirationTime;
                                    }
                                }
                                resolve({items: items.length, tokens, raw: items});
                            };
                            getAll.onerror = () => resolve({error: 'getAll failed'});
                        };
                        req.onerror = () => resolve({error: 'open failed'});
                    });
                })()
            """)
            auth_file = OUTPUT_DIR / "api-auth.json"
            existing = json.loads(auth_file.read_text()) if auth_file.exists() else {}
            existing["firebase_storage"] = firebase_tokens
            auth_file.write_text(json.dumps(existing, indent=2, default=str))
            console.print("  [bold yellow]Firebase tokens saved to api-auth.json[/bold yellow]")
        except Exception as e:
            console.print(f"  [dim red]Firebase token extraction failed: {e}[/dim red]")

        # Dismiss popup "Alerte au faux conseiller" if present
        try:
            dismiss_btn = await page.find("J'ai compris", timeout=5)
            if dismiss_btn:
                await dismiss_btn.click()
                console.print("  [dim]Popup dismissed[/dim]")
                await page.sleep(1)
        except Exception:
            pass

        await page.save_screenshot(str(OUTPUT_DIR / "02-logged-in.png"))

        # --- Step 5: Free navigation — user controls the browser ---
        console.print(
            Panel(
                "[bold]Navigate librement dans Indy.[/bold]\n"
                "Le trafic API est capturé en temps réel.\n"
                "[yellow]Ctrl+C[/yellow] pour arrêter et exporter.",
                style="green",
            )
        )

        # Keep running until user interrupts
        while True:
            await page.sleep(5)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logger.error("Interception failed", exc_info=True)
    finally:
        # Always export what we captured
        (OUTPUT_DIR / "api-endpoints.md").write_text(interceptor.export_markdown())
        (OUTPUT_DIR / "api-raw.json").write_text(interceptor.export_json())
        console.print(f"\n[dim]Final export: {len(interceptor.api_calls)} API calls[/dim]")
        gmail_reader.close()
        browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
