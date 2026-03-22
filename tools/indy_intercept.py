"""Intercept Indy API calls via nodriver CDP Network domain.

Captures all XHR/fetch API calls from Indy by enabling Chrome DevTools Protocol
(CDP) Network domain events. Filters out static assets and logs API endpoints
for reverse engineering.

Usage:
    python tools/intercept_indy_api.py

Output:
    - io/research/indy/api-endpoints.md  (markdown summary)
    - io/research/indy/api-raw.json      (full request/response data)
    - io/research/indy/*.png              (page screenshots)
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import nodriver as uc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("io/research/indy")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Static asset extensions and tracking domains to filter
STATIC_EXTENSIONS = {".js", ".css", ".png", ".jpg", ".svg", ".woff", ".ttf", ".ico"}
TRACKING_DOMAINS = {
    "google-analytics",
    "googletagmanager",
    "cloudflare",
    "intercom",
    "sentry",
    "amplitude",
    "segment",
}


class NetworkInterceptor:
    """Capture API calls via CDP Network events."""

    def __init__(self) -> None:
        self.requests: dict[str, dict[str, Any]] = {}
        self.api_calls: list[dict[str, Any]] = []
        self.request_count = 0
        self.filtered_count = 0

    def _is_static_asset(self, url: str) -> bool:
        """Check if URL is a static asset to ignore."""
        url_lower = url.lower()
        return any(ext in url_lower for ext in STATIC_EXTENSIONS) or any(
            domain in url_lower for domain in TRACKING_DOMAINS
        )

    def on_request_will_be_sent(self, event: uc.cdp.network.RequestWillBeSent) -> None:
        """Handle CDP Network.requestWillBeSent event.

        Args:
            event: CDP RequestWillBeSent event containing request details.
        """
        request = event.request
        url = request.url
        request_id = event.request_id

        self.request_count += 1

        # Filter out static assets and trackers
        if self._is_static_asset(url):
            self.filtered_count += 1
            return

        # Only track XHR/fetch requests (based on resource type)
        request_type = (event.type or "OTHER").upper()
        if request_type not in {"XHR", "FETCH"}:
            return

        # Extract headers safely (may be None)
        headers = request.headers or {}

        self.requests[request_id] = {
            "url": url,
            "method": request.method or "GET",
            "headers": self._mask_headers(headers),
            "post_data": request.post_data or "",
            "type": request_type,
            "timestamp": datetime.now().isoformat(),
        }

        logger.debug("Request captured: %s %s", request.method, url)

    def on_response_received(self, event: uc.cdp.network.ResponseReceived) -> None:
        """Handle CDP Network.responseReceived event.

        Args:
            event: CDP ResponseReceived event containing response details.
        """
        request_id = event.request_id
        if request_id not in self.requests:
            return

        response = event.response
        entry = self.requests[request_id]
        entry["status"] = response.status
        entry["status_text"] = response.status_text or ""
        entry["content_type"] = (response.headers or {}).get("content-type", "")
        entry["url"] = response.url or entry["url"]

        # Keep entry (will be filtered by content-type later if needed)
        self.api_calls.append(entry)
        logger.debug("Response: %s %d", entry["url"], entry["status"])

    @staticmethod
    def _mask_headers(headers: dict[str, str | int | float | bool] | None) -> dict[str, str]:
        """Mask sensitive headers for security.

        Args:
            headers: Dictionary of HTTP headers to filter.

        Returns:
            Dictionary of headers with sensitive values masked.
        """
        if not headers:
            return {}

        masked = {}
        sensitive_keys = {"authorization", "cookie", "token", "secret", "x-api-key"}

        for key, value in headers.items():
            key_lower = key.lower()
            if any(s in key_lower for s in sensitive_keys):
                val_str = str(value)
                if len(val_str) > 30:
                    masked[key] = val_str[:30] + "..."
                else:
                    masked[key] = "***"
            else:
                masked[key] = str(value)

        return masked

    def export_markdown(self) -> str:
        """Export API calls as markdown summary."""
        lines = [
            "# Indy API Endpoints — Reverse Engineering\n",
            f"Generated: {datetime.now().isoformat()}",
            f"Total requests: {self.request_count}",
            f"Static/tracking filtered: {self.filtered_count}",
            f"API calls captured: {len(self.api_calls)}\n",
            "## API Endpoints Summary\n",
            "| Method | URL | Status | Content-Type |",
            "|---|---|---|---|",
        ]

        seen_endpoints = set()
        for call in self.api_calls:
            # Normalize URL (remove query params for dedup)
            url_normalized = call["url"].split("?")[0]
            endpoint_key = f"{call['method']} {url_normalized}"

            if endpoint_key in seen_endpoints:
                continue
            seen_endpoints.add(endpoint_key)

            method = call.get("method", "?")
            url = url_normalized[:80]
            status = call.get("status", "?")
            content_type = call.get("content_type", "?").split(";")[0]

            lines.append(f"| {method} | {url} | {status} | {content_type} |")

        lines.append(f"\n## Detailed Calls ({len(self.api_calls)} total)\n")

        for i, call in enumerate(self.api_calls, 1):
            lines.append(f"### Call {i}: {call['method']} {call['url'][:100]}")
            lines.append(f"- **Status**: {call.get('status', '?')} {call.get('status_text', '')}")
            lines.append(f"- **Content-Type**: {call.get('content_type', '?')}")
            lines.append(f"- **Timestamp**: {call.get('timestamp', '?')}")

            if call.get("post_data"):
                body = call["post_data"]
                if isinstance(body, str) and len(body) > 500:
                    lines.append(f"- **Body**: ```{body[:500]}...```")
                else:
                    lines.append(f"- **Body**: ```{body}```")

            lines.append("")

        return "\n".join(lines)

    def export_json(self) -> str:
        """Export API calls as JSON."""
        return json.dumps(self.api_calls, indent=2, default=str)


async def main() -> None:
    """Main execution: login to Indy and capture network traffic."""
    # Read credentials from .env.mcp
    env: dict[str, str] = {}
    env_file = Path(".env.mcp")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    else:
        logger.warning(".env.mcp not found, will attempt to proceed")

    email = env.get("INDY_EMAIL", "")
    password = env.get("INDY_PASSWORD", "")

    if not email or not password:
        logger.error("INDY_EMAIL and INDY_PASSWORD required in .env.mcp")
        logger.error("Exiting without intercepting.")
        return

    logger.info("Starting nodriver browser (headed mode)...")
    browser = await uc.start(
        headless=False,
        browser_args=[
            "--no-first-run",
            "--no-default-browser-check",
        ],
    )

    interceptor = NetworkInterceptor()

    try:
        logger.info("Navigating to app.indy.fr/connexion...")
        page = await browser.get("https://app.indy.fr/connexion")
        await page.sleep(3)

        # Save initial login page
        await page.save_screenshot(str(OUTPUT_DIR / "01-login-page.png"))
        logger.info("Screenshot saved: 01-login-page.png")

        # Enable CDP Network domain to intercept requests
        logger.info("Enabling CDP Network interception...")
        try:
            # Enable CDP Network domain to capture all XHR/fetch requests
            await page.send(
                uc.cdp.network.enable(
                    max_total_buffer_size=100 * 1024 * 1024,  # 100MB buffer
                    max_resource_buffer_size=10 * 1024 * 1024,  # 10MB per resource
                    max_post_data_size=1024 * 1024,  # 1MB post data
                    report_direct_socket_traffic=False,
                    enable_durable_messages=True,
                )
            )
            logger.info("CDP Network domain enabled for traffic capture")

            # Register handlers for request/response events
            page.add_handler(
                uc.cdp.network.RequestWillBeSent,
                interceptor.on_request_will_be_sent,
            )
            page.add_handler(
                uc.cdp.network.ResponseReceived,
                interceptor.on_response_received,
            )
            logger.info("Network event handlers registered (RequestWillBeSent, ResponseReceived)")

        except Exception as e:
            logger.warning("CDP Network enable failed (non-critical): %s", e)

        # Fill login form
        logger.info("Filling login form...")
        email_input = await page.find("input[type='email']", timeout=10)
        if email_input:
            await email_input.send_keys(email)
            logger.info("Email filled")

        password_input = await page.find("input[type='password']", timeout=10)
        if password_input:
            await password_input.send_keys(password)
            logger.info("Password filled")

        await page.sleep(2)
        await page.save_screenshot(str(OUTPUT_DIR / "02-filled.png"))

        # Submit login
        logger.info("Submitting login...")
        try:
            submit_btn = await page.find("Se connecter", timeout=10)
            if submit_btn:
                await submit_btn.click()
                logger.info("Login submitted")
        except Exception as e:
            logger.warning("Could not find submit by text, trying selector: %s", e)
            try:
                submit_btn = await page.query_selector("button[type='submit']")
                if submit_btn:
                    await submit_btn.click()
                    logger.info("Login submitted (via selector)")
            except Exception as ex:
                logger.error("Could not submit: %s", ex)

        # Wait for login to complete
        logger.info("Waiting for login response (max 120s)...")
        logged_in = False
        for _attempt in range(24):
            await page.sleep(5)
            current_url = page.url
            logger.info("URL: %s", current_url)

            if any(x in current_url.lower() for x in ["dashboard", "accueil", "app.indy.fr/app"]):
                logged_in = True
                logger.info("Login successful!")
                break

            if "verification" in current_url.lower() or "2fa" in current_url.lower():
                logger.info("2FA detected. Enter code in browser window...")
                logger.info("Waiting for 2FA completion (max 120s)...")
                # Wait for 2FA
                for _i in range(24):
                    await page.sleep(5)
                    url = page.url
                    if any(x in url.lower() for x in ["dashboard", "accueil", "app.indy.fr/app"]):
                        logged_in = True
                        logger.info("2FA completed!")
                        break
                break

        await page.save_screenshot(str(OUTPUT_DIR / "03-after-login.png"))

        if not logged_in:
            logger.error("Login failed or timed out")
            logger.error("Final URL: %s", page.url)
            return

        # Now navigate through key pages to trigger API calls
        logger.info("Exploring Indy pages to capture API calls...")

        pages_to_explore = [
            ("/app/", "Dashboard"),
            ("/app/transactions", "Transactions"),
            ("/app/documents", "Documents"),
            ("/app/comptabilite", "Comptabilité"),
            ("/app/bank", "Bank/Accounts"),
        ]

        for i, (path, name) in enumerate(pages_to_explore, start=1):
            try:
                full_url = f"https://app.indy.fr{path}"
                logger.info("Navigating to %s (%s)...", name, full_url)
                await page.get(full_url)
                await page.sleep(4)  # Wait for API calls to complete
                await page.save_screenshot(str(OUTPUT_DIR / f"0{i + 3}-{name.lower()}.png"))
                logger.info("Screenshot saved: 0%d-%s.png", i + 3, name.lower())
            except Exception as e:
                logger.warning("Could not navigate to %s: %s", name, e)

        # Export results
        logger.info("Exporting captured data...")
        md_content = interceptor.export_markdown()
        md_file = OUTPUT_DIR / "api-endpoints.md"
        md_file.write_text(md_content)
        logger.info("Markdown export saved: %s", md_file)

        json_content = interceptor.export_json()
        json_file = OUTPUT_DIR / "api-raw.json"
        json_file.write_text(json_content)
        logger.info("JSON export saved: %s", json_file)

        logger.info("Keeping browser open for 30 more seconds...")
        await page.sleep(30)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Error during exploration: %s", e, exc_info=True)
    finally:
        # Final export
        md_content = interceptor.export_markdown()
        (OUTPUT_DIR / "api-endpoints.md").write_text(md_content)
        logger.info("Final export: %d API calls captured", len(interceptor.api_calls))
        logger.info("Closing browser...")
        browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
