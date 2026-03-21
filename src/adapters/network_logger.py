"""Network request logger for reverse API engineering.

Intercepts Playwright network traffic to discover internal API endpoints used by
AIS and Indy during exploration phase. Not for production use.

Usage:
    net_logger = NetworkLogger(output_dir=Path("io/research/ais"))
    net_logger.attach(page)
    # ... navigate pages ...
    net_logger.export()
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

# Patterns to mask sensitive data in logs (credentials, tokens, passwords)
SENSITIVE_PATTERNS = [
    re.compile(r"Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"(password[\"']?\s*[:=]\s*[\"']?)\S+", re.IGNORECASE),
    re.compile(r"(token[\"']?\s*[:=]\s*[\"']?)\S+", re.IGNORECASE),
]


class NetworkLogger:
    """Capture and log network requests from Playwright pages.

    Intercepts HTTP requests/responses to discover API endpoints and data models.
    Masks sensitive headers (Authorization, tokens, cookies) per RGPD rules.

    Attributes:
        _output_dir: Directory where logs are written.
        _requests: List of captured request entries.
        _responses: List of captured response entries.
        _api_endpoints: Dict tracking unique API endpoints by method + URL.
    """

    def __init__(self, output_dir: Path) -> None:
        """Initialize NetworkLogger.

        Args:
            output_dir: Directory path where JSONL and markdown files are written.
                       Created if missing.
        """
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._requests: list[dict[str, Any]] = []
        self._responses: list[dict[str, Any]] = []
        self._api_endpoints: dict[str, dict[str, Any]] = {}

    def attach(self, page: Any) -> None:
        """Attach network listeners to a Playwright page.

        Args:
            page: Playwright Page object to monitor.
        """
        page.on("request", self._on_request)
        page.on("response", self._on_response)
        logger.info("Network logger attached to page")

    def _on_request(self, request: Any) -> None:
        """Log outgoing HTTP request.

        Args:
            request: Playwright Request object.
        """
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "url": request.url,
            "method": request.method,
            "resource_type": request.resource_type,
            "headers": self._mask_sensitive(dict(request.headers)),
        }

        # Capture POST/PUT/PATCH body if available
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = request.post_data
                if body:
                    entry["body"] = body[:2000]  # Limit size for performance
            except Exception:
                pass

        self._requests.append(entry)

        # Track unique API endpoints (filter out static assets)
        if self._is_api_call(request.url, request.resource_type):
            self._track_endpoint(request.url, request.method, entry)

    def _on_response(self, response: Any) -> None:
        """Log incoming HTTP response.

        Args:
            response: Playwright Response object.
        """
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "url": response.url,
            "status": response.status,
            "headers": self._mask_sensitive(dict(response.headers)),
        }

        # Capture JSON response body if available
        content_type = response.headers.get("content-type", "")
        if "json" in content_type or "graphql" in response.url:
            try:
                body = response.text()
                entry["body"] = body[:5000]  # Limit size for performance
            except Exception:
                pass

        self._responses.append(entry)

    def _is_api_call(self, url: str, resource_type: str) -> bool:
        """Filter: is this an API call (not static asset)?

        Args:
            url: Full request URL.
            resource_type: Playwright resource type (xhr, fetch, stylesheet, etc).

        Returns:
            True if URL is likely an API call, False if static asset.
        """
        # Exclude known static asset types
        if resource_type in ("stylesheet", "image", "font", "media"):
            return False

        # Exclude common static file extensions
        if any(ext in url for ext in [".css", ".js", ".png", ".jpg", ".svg", ".woff"]):
            return False

        # Include /api/ and graphql paths
        if "/api/" in url or "graphql" in url:
            return True

        # Include xhr and fetch resource types (dynamic requests)
        return resource_type in ("xhr", "fetch")

    def _track_endpoint(self, url: str, method: str, entry: dict[str, Any]) -> None:
        """Track unique API endpoint (deduplicate by method + base URL).

        Args:
            url: Full request URL (may include query parameters).
            method: HTTP method (GET, POST, etc).
            entry: Request entry dict with timestamp.
        """
        # Separate base URL from query params
        base_url = url.split("?")[0]
        params = url.split("?")[1] if "?" in url else ""

        key = f"{method} {base_url}"

        if key not in self._api_endpoints:
            self._api_endpoints[key] = {
                "method": method,
                "url": base_url,
                "params": params,
                "count": 0,
                "first_seen": entry["timestamp"],
            }

        self._api_endpoints[key]["count"] += 1

    def _mask_sensitive(self, headers: dict[str, str]) -> dict[str, str]:
        """Mask sensitive values in headers (RGPD compliance).

        Args:
            headers: Dict of HTTP headers.

        Returns:
            Dict with sensitive values masked.
        """
        masked: dict[str, str] = {}

        for key, value in headers.items():
            # Entirely mask sensitive header types for RGPD
            if key.lower() in ("authorization", "cookie", "set-cookie"):
                masked_value = "***MASKED***"
            else:
                masked_value = value
                # Apply regex patterns to mask credentials in other headers
                masked_value = SENSITIVE_PATTERNS[0].sub("Bearer ***MASKED***", masked_value)
                for pattern in SENSITIVE_PATTERNS[1:]:
                    masked_value = pattern.sub(r"\1***MASKED***", masked_value)

            masked[key] = masked_value

        return masked

    def export(self) -> Path:
        """Export captured network data to files.

        Creates two files:
        - network-TIMESTAMP.jsonl: Raw request/response entries, one per line
        - api-endpoints.md: Summary table of discovered endpoints

        Returns:
            Path to created JSONL log file.
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")

        # Write raw network log as JSONL (one JSON object per line)
        log_file = self._output_dir / f"network-{timestamp}.jsonl"
        with log_file.open("w") as f:
            for req in self._requests:
                f.write(json.dumps(req, default=str) + "\n")
            for resp in self._responses:
                f.write(json.dumps(resp, default=str) + "\n")

        # Write API endpoints summary as Markdown table
        endpoints_file = self._output_dir / "api-endpoints.md"
        with endpoints_file.open("w") as f:
            f.write("# API Endpoints Discovered\n\n")
            f.write(f"Generated: {timestamp}\n\n")
            f.write("| Method | URL | Calls | First Seen | Params |\n")
            f.write("|--------|-----|-------|------------|--------|\n")

            for key in sorted(self._api_endpoints.keys()):
                info = self._api_endpoints[key]
                first_seen = info["first_seen"][:19]  # Truncate timestamp
                params_col = f"`{info['params']}`" if info["params"] else "(none)"
                f.write(
                    f"| {info['method']} | `{info['url']}` | {info['count']} | "
                    f"{first_seen} | {params_col} |\n"
                )

        logger.info(
            "Network log exported",
            extra={
                "requests": len(self._requests),
                "responses": len(self._responses),
                "endpoints": len(self._api_endpoints),
                "log_file": str(log_file),
            },
        )

        return log_file

    def get_api_endpoints(self) -> dict[str, dict[str, Any]]:
        """Return copy of discovered API endpoints dict.

        Returns:
            Dict mapping "METHOD URL" -> {method, url, params, count, first_seen}.
        """
        return dict(self._api_endpoints)
