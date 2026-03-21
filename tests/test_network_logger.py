"""Tests for NetworkLogger utility (reverse API engineering)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from src.adapters.network_logger import NetworkLogger


class TestNetworkLoggerInit:
    """Tests for NetworkLogger initialization."""

    def test_init_creates_output_dir(self, tmp_path: Path) -> None:
        """Test that output directory is created if missing."""
        output_dir = tmp_path / "network_logs"
        assert not output_dir.exists()

        logger = NetworkLogger(output_dir=output_dir)

        assert output_dir.exists()
        assert logger._output_dir == output_dir

    def test_init_uses_existing_dir(self, tmp_path: Path) -> None:
        """Test that existing output directory is reused."""
        output_dir = tmp_path / "network_logs"
        output_dir.mkdir(parents=True)

        logger = NetworkLogger(output_dir=output_dir)

        assert logger._output_dir == output_dir


class TestNetworkLoggerAttach:
    """Tests for attaching listeners to Playwright page."""

    def test_attach_registers_request_listener(self, tmp_path: Path) -> None:
        """Test that attach registers request listener."""
        logger = NetworkLogger(output_dir=tmp_path)
        mock_page = MagicMock()

        logger.attach(mock_page)

        # Verify on("request", ...) was called
        calls = [call for call in mock_page.on.call_args_list if call[0][0] == "request"]
        assert len(calls) == 1

    def test_attach_registers_response_listener(self, tmp_path: Path) -> None:
        """Test that attach registers response listener."""
        logger = NetworkLogger(output_dir=tmp_path)
        mock_page = MagicMock()

        logger.attach(mock_page)

        # Verify on("response", ...) was called
        calls = [call for call in mock_page.on.call_args_list if call[0][0] == "response"]
        assert len(calls) == 1


class TestMaskSensitive:
    """Tests for masking sensitive data in headers."""

    def test_mask_authorization_bearer(self, tmp_path: Path) -> None:
        """Test that Bearer tokens are masked."""
        logger = NetworkLogger(output_dir=tmp_path)
        headers = {"Authorization": "Bearer secret123token"}

        masked = logger._mask_sensitive(headers)

        assert "secret123token" not in masked["Authorization"]
        assert "***MASKED***" in masked["Authorization"]

    def test_mask_authorization_header_case_insensitive(self, tmp_path: Path) -> None:
        """Test that authorization header masking is case-insensitive."""
        logger = NetworkLogger(output_dir=tmp_path)
        headers = {"authorization": "Bearer token123"}

        masked = logger._mask_sensitive(headers)

        assert "token123" not in masked["authorization"]

    def test_mask_cookie(self, tmp_path: Path) -> None:
        """Test that cookie headers are truncated and masked."""
        logger = NetworkLogger(output_dir=tmp_path)
        headers = {"Cookie": "session=abc123def456ghi789jkl"}

        masked = logger._mask_sensitive(headers)

        assert "abc123def456ghi789jkl" not in masked["Cookie"]
        assert "***MASKED***" in masked["Cookie"]

    def test_preserve_non_sensitive_headers(self, tmp_path: Path) -> None:
        """Test that non-sensitive headers are preserved."""
        logger = NetworkLogger(output_dir=tmp_path)
        headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

        masked = logger._mask_sensitive(headers)

        assert masked["Content-Type"] == "application/json"
        assert masked["User-Agent"] == "Mozilla/5.0"

    def test_mask_password_in_json(self, tmp_path: Path) -> None:
        """Test that password patterns in headers are masked."""
        logger = NetworkLogger(output_dir=tmp_path)
        headers = {"X-Custom": 'password: "secret123"'}

        masked = logger._mask_sensitive(headers)

        assert "secret123" not in masked["X-Custom"]

    def test_mask_token_key_value(self, tmp_path: Path) -> None:
        """Test that token=value patterns are masked."""
        logger = NetworkLogger(output_dir=tmp_path)
        headers = {"X-Custom": 'token="mytoken123"'}

        masked = logger._mask_sensitive(headers)

        assert "mytoken123" not in masked["X-Custom"]


class TestIsApiCall:
    """Tests for filtering API calls from static assets."""

    def test_filter_stylesheet(self, tmp_path: Path) -> None:
        """Test that stylesheets are not counted as API calls."""
        logger = NetworkLogger(output_dir=tmp_path)

        is_api = logger._is_api_call("https://cdn.example.com/style.css", "stylesheet")

        assert is_api is False

    def test_filter_image(self, tmp_path: Path) -> None:
        """Test that images are not counted as API calls."""
        logger = NetworkLogger(output_dir=tmp_path)

        is_api = logger._is_api_call("https://cdn.example.com/logo.png", "image")

        assert is_api is False

    def test_filter_font(self, tmp_path: Path) -> None:
        """Test that fonts are not counted as API calls."""
        logger = NetworkLogger(output_dir=tmp_path)

        is_api = logger._is_api_call("https://fonts.example.com/font.woff", "font")

        assert is_api is False

    def test_filter_by_extension(self, tmp_path: Path) -> None:
        """Test that files with asset extensions are filtered."""
        logger = NetworkLogger(output_dir=tmp_path)

        assert logger._is_api_call("https://app.example.com/bundle.js", "fetch") is False
        assert logger._is_api_call("https://app.example.com/style.css", "fetch") is False

    def test_recognize_api_endpoint(self, tmp_path: Path) -> None:
        """Test that API endpoints are recognized."""
        logger = NetworkLogger(output_dir=tmp_path)

        is_api = logger._is_api_call("https://api.example.com/api/v1/users", "xhr")

        assert is_api is True

    def test_recognize_graphql(self, tmp_path: Path) -> None:
        """Test that GraphQL endpoints are recognized."""
        logger = NetworkLogger(output_dir=tmp_path)

        is_api = logger._is_api_call("https://api.example.com/graphql", "fetch")

        assert is_api is True

    def test_recognize_fetch_resource_type(self, tmp_path: Path) -> None:
        """Test that fetch resource type is recognized as API."""
        logger = NetworkLogger(output_dir=tmp_path)

        is_api = logger._is_api_call("https://app.example.com/data", "fetch")

        assert is_api is True

    def test_recognize_xhr_resource_type(self, tmp_path: Path) -> None:
        """Test that xhr resource type is recognized as API."""
        logger = NetworkLogger(output_dir=tmp_path)

        is_api = logger._is_api_call("https://app.example.com/data", "xhr")

        assert is_api is True


class TestTrackEndpoint:
    """Tests for tracking discovered API endpoints."""

    def test_track_new_endpoint(self, tmp_path: Path) -> None:
        """Test tracking a new API endpoint."""
        logger = NetworkLogger(output_dir=tmp_path)
        entry = {"timestamp": datetime.now().isoformat()}

        logger._track_endpoint("https://api.example.com/api/v1/users", "GET", entry)

        endpoints = logger.get_api_endpoints()
        assert "GET https://api.example.com/api/v1/users" in endpoints
        assert endpoints["GET https://api.example.com/api/v1/users"]["count"] == 1

    def test_track_endpoint_increments_count(self, tmp_path: Path) -> None:
        """Test that repeated endpoint calls increment counter."""
        logger = NetworkLogger(output_dir=tmp_path)
        entry = {"timestamp": datetime.now().isoformat()}

        logger._track_endpoint("https://api.example.com/api/v1/users", "GET", entry)
        logger._track_endpoint("https://api.example.com/api/v1/users", "GET", entry)

        endpoints = logger.get_api_endpoints()
        assert endpoints["GET https://api.example.com/api/v1/users"]["count"] == 2

    def test_track_endpoint_preserves_base_url(self, tmp_path: Path) -> None:
        """Test that query parameters are stripped from tracked URL."""
        logger = NetworkLogger(output_dir=tmp_path)
        entry = {"timestamp": datetime.now().isoformat()}

        logger._track_endpoint("https://api.example.com/api/v1/users?page=1&limit=10", "GET", entry)

        endpoints = logger.get_api_endpoints()
        key = next(iter(endpoints.keys()))
        assert "page=1" not in endpoints[key]["url"]

    def test_track_endpoint_captures_query_params(self, tmp_path: Path) -> None:
        """Test that query parameters are captured separately."""
        logger = NetworkLogger(output_dir=tmp_path)
        entry = {"timestamp": datetime.now().isoformat()}

        logger._track_endpoint("https://api.example.com/api/v1/users?page=1&limit=10", "GET", entry)

        endpoints = logger.get_api_endpoints()
        key = next(iter(endpoints.keys()))
        assert endpoints[key]["params"] == "page=1&limit=10"


class TestOnRequest:
    """Tests for request interception."""

    def test_on_request_captures_url(self, tmp_path: Path) -> None:
        """Test that request handler captures URL."""
        logger = NetworkLogger(output_dir=tmp_path)
        mock_request = MagicMock()
        mock_request.url = "https://api.example.com/api/v1/data"
        mock_request.method = "GET"
        mock_request.resource_type = "xhr"
        mock_request.headers = {"Content-Type": "application/json"}
        mock_request.post_data = None

        logger._on_request(mock_request)

        assert len(logger._requests) == 1
        assert logger._requests[0]["url"] == "https://api.example.com/api/v1/data"

    def test_on_request_captures_method(self, tmp_path: Path) -> None:
        """Test that request handler captures HTTP method."""
        logger = NetworkLogger(output_dir=tmp_path)
        mock_request = MagicMock()
        mock_request.url = "https://api.example.com/api/v1/data"
        mock_request.method = "POST"
        mock_request.resource_type = "xhr"
        mock_request.headers = {}
        mock_request.post_data = None

        logger._on_request(mock_request)

        assert logger._requests[0]["method"] == "POST"

    def test_on_request_captures_post_body(self, tmp_path: Path) -> None:
        """Test that POST body is captured."""
        logger = NetworkLogger(output_dir=tmp_path)
        mock_request = MagicMock()
        mock_request.url = "https://api.example.com/api/v1/data"
        mock_request.method = "POST"
        mock_request.resource_type = "xhr"
        mock_request.headers = {"Content-Type": "application/json"}
        mock_request.post_data = '{"key": "value"}'

        logger._on_request(mock_request)

        assert "body" in logger._requests[0]
        assert logger._requests[0]["body"] == '{"key": "value"}'


class TestOnResponse:
    """Tests for response interception."""

    def test_on_response_captures_status(self, tmp_path: Path) -> None:
        """Test that response handler captures status code."""
        logger = NetworkLogger(output_dir=tmp_path)
        mock_response = MagicMock()
        mock_response.url = "https://api.example.com/api/v1/data"
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "application/json"}

        logger._on_response(mock_response)

        assert len(logger._responses) == 1
        assert logger._responses[0]["status"] == 200

    def test_on_response_captures_json_body(self, tmp_path: Path) -> None:
        """Test that JSON response body is captured."""
        logger = NetworkLogger(output_dir=tmp_path)
        mock_response = MagicMock()
        mock_response.url = "https://api.example.com/api/v1/data"
        mock_response.status = 200
        # Use a dict-like object that supports case-insensitive get
        headers = {"content-type": "application/json"}
        mock_response.headers = headers
        mock_response.text = MagicMock(return_value='{"id": 123, "name": "Test"}')

        logger._on_response(mock_response)

        assert "body" in logger._responses[0]
        assert '{"id": 123' in logger._responses[0]["body"]


class TestExport:
    """Tests for exporting captured data."""

    def test_export_creates_jsonl_file(self, tmp_path: Path) -> None:
        """Test that export creates JSONL log file."""
        logger = NetworkLogger(output_dir=tmp_path)
        mock_request = MagicMock()
        mock_request.url = "https://api.example.com/api/v1/data"
        mock_request.method = "GET"
        mock_request.resource_type = "xhr"
        mock_request.headers = {}
        mock_request.post_data = None

        logger._on_request(mock_request)
        result = logger.export()

        assert result.exists()
        assert result.suffix == ".jsonl"

    def test_export_creates_endpoints_markdown(self, tmp_path: Path) -> None:
        """Test that export creates API endpoints markdown file."""
        logger = NetworkLogger(output_dir=tmp_path)
        entry = {"timestamp": datetime.now().isoformat()}
        logger._track_endpoint("https://api.example.com/api/v1/users", "GET", entry)

        logger.export()

        endpoints_file = tmp_path / "api-endpoints.md"
        assert endpoints_file.exists()

    def test_export_markdown_contains_endpoints(self, tmp_path: Path) -> None:
        """Test that endpoints markdown contains discovered endpoints."""
        logger = NetworkLogger(output_dir=tmp_path)
        entry = {"timestamp": datetime.now().isoformat()}
        logger._track_endpoint("https://api.example.com/api/v1/users", "GET", entry)

        logger.export()

        endpoints_file = tmp_path / "api-endpoints.md"
        content = endpoints_file.read_text()
        assert "GET" in content
        assert "api/v1/users" in content

    def test_export_jsonl_is_valid_json(self, tmp_path: Path) -> None:
        """Test that exported JSONL file contains valid JSON lines."""
        logger = NetworkLogger(output_dir=tmp_path)
        mock_request = MagicMock()
        mock_request.url = "https://api.example.com/api/v1/data"
        mock_request.method = "GET"
        mock_request.resource_type = "xhr"
        mock_request.headers = {"Content-Type": "application/json"}
        mock_request.post_data = None

        logger._on_request(mock_request)
        result = logger.export()

        lines = result.read_text().strip().split("\n")
        assert len(lines) >= 1
        # Parse as JSON to verify validity
        parsed = json.loads(lines[0])
        assert "url" in parsed or "status" in parsed

    def test_export_returns_log_file_path(self, tmp_path: Path) -> None:
        """Test that export returns path to created log file."""
        logger = NetworkLogger(output_dir=tmp_path)
        result = logger.export()

        assert isinstance(result, Path)
        assert result.name.startswith("network-")


class TestGetApiEndpoints:
    """Tests for retrieving discovered endpoints."""

    def test_get_api_endpoints_empty(self, tmp_path: Path) -> None:
        """Test get_api_endpoints returns empty dict if nothing tracked."""
        logger = NetworkLogger(output_dir=tmp_path)

        endpoints = logger.get_api_endpoints()

        assert isinstance(endpoints, dict)
        assert len(endpoints) == 0

    def test_get_api_endpoints_contains_tracked(self, tmp_path: Path) -> None:
        """Test get_api_endpoints returns tracked endpoints."""
        logger = NetworkLogger(output_dir=tmp_path)
        entry = {"timestamp": datetime.now().isoformat()}
        logger._track_endpoint("https://api.example.com/api/v1/users", "GET", entry)

        endpoints = logger.get_api_endpoints()

        assert "GET https://api.example.com/api/v1/users" in endpoints

    def test_get_api_endpoints_is_copy(self, tmp_path: Path) -> None:
        """Test that get_api_endpoints returns a copy, not reference."""
        logger = NetworkLogger(output_dir=tmp_path)
        entry = {"timestamp": datetime.now().isoformat()}
        logger._track_endpoint("https://api.example.com/api/v1/users", "GET", entry)

        endpoints1 = logger.get_api_endpoints()
        endpoints2 = logger.get_api_endpoints()

        assert endpoints1 is not endpoints2


class TestIntegration:
    """Integration tests for NetworkLogger workflow."""

    def test_full_workflow(self, tmp_path: Path) -> None:
        """Test complete workflow: attach, capture, export."""
        logger = NetworkLogger(output_dir=tmp_path)
        mock_page = MagicMock()

        # Attach listeners
        logger.attach(mock_page)

        # Simulate captured request
        mock_request = MagicMock()
        mock_request.url = "https://api.example.com/api/v1/users"
        mock_request.method = "GET"
        mock_request.resource_type = "xhr"
        mock_request.headers = {"Authorization": "Bearer token123"}
        mock_request.post_data = None

        logger._on_request(mock_request)

        # Simulate captured response
        mock_response = MagicMock()
        mock_response.url = "https://api.example.com/api/v1/users"
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text.return_value = '{"id": 1}'

        logger._on_response(mock_response)

        # Export
        result = logger.export()

        assert result.exists()
        assert (tmp_path / "api-endpoints.md").exists()

    def test_multiple_requests_same_endpoint(self, tmp_path: Path) -> None:
        """Test tracking multiple requests to same endpoint."""
        logger = NetworkLogger(output_dir=tmp_path)
        entry = {"timestamp": datetime.now().isoformat()}

        # First request
        logger._track_endpoint("https://api.example.com/api/v1/users", "GET", entry)
        # Second request
        logger._track_endpoint("https://api.example.com/api/v1/users", "GET", entry)

        endpoints = logger.get_api_endpoints()
        assert len(endpoints) == 1
        assert endpoints["GET https://api.example.com/api/v1/users"]["count"] == 2

    def test_multiple_different_endpoints(self, tmp_path: Path) -> None:
        """Test tracking multiple different endpoints."""
        logger = NetworkLogger(output_dir=tmp_path)
        entry = {"timestamp": datetime.now().isoformat()}

        logger._track_endpoint("https://api.example.com/api/v1/users", "GET", entry)
        logger._track_endpoint("https://api.example.com/api/v1/clients", "POST", entry)
        logger._track_endpoint("https://api.example.com/api/v1/invoices", "GET", entry)

        endpoints = logger.get_api_endpoints()
        assert len(endpoints) == 3
