"""
Pytest configuration and shared fixtures.

Usage: pytest auto-discovers and uses these fixtures
Reference: docs/phase3/test-strategy.md section 2
"""

from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    """Test configuration."""
    # Create a minimal valid Google Service Account JSON for testing
    service_account = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test-key-id",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA2a2rwplBCWHZo2a5c8K8eFDzaJjYCpx1L3dxeMyLQWYpYAVy\nX8pgVzlKhNkLvgODL7VUg0nQ6w3L7nh8S9Z3B3hDxL6dF9XzPZ0zBLaL5qZ5qL8m\nV8TfTlqUZn3pN2LxI8EqF8vV0K0f7S6X8z0L6c0F5d9Z0L7g8M2H4n3J9P4K8r1\nA3b5C2d7E1f9G3h4J4k6L8M9O5N6P7Q9R8S0T2U3V4W5X6Y7Z8a9B0c1D2e3F4g\nQIDAQABAoIBABr+qyaXKmZzVS2qVJTqCx8P8z3L3c2K4b1J1a0I9Y9X8w7V6u5T\n4s3R2r1P0o9N9m7L8k5J3i3H2g1F0e9D0c8Vz1U7T2S8y+wvUtRq0pzsJRnMoLpn\nA3KBpOECgYEA/Vn1nA7l8w9Q8p1M0l7K3i2J1h0I9G8F0e7D2c6VxlU5T0S3r2Q\n3p1O9n0N2m1L7k4J4j3I2h1G1f0E0d7Vw1U6T1S4r3P3o0N8m0L6k3I3i2H1g0\nF0eAgEz7B5d8C2wvUtSq1Z0l5M9C/6F/8G+hKJZ2/xkxLxkW4+9NlZMCgYEA2+V7\n/mq5f8v7s9r2q8n1p7m0o7l9k8j3i7g1f6e0d5c9b4a8Z8b7a6c5d3e3f2g1h9\nKJI1z3qz0zBbMoLpmA2KBpOECgYEApKzd/s5FzVvQttj0p7n1q8m0p7l9k8j3i7g\n1f6e0d5c9b4a8Z8b7a6c5d3e3f2g1h2jKJJ2z4rz1zCcNoLpnA3LBqPFDhIUKnZM\nOJbj2CPsQ4L1n2d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t1u2v3w4x5y6z7a8b\nCgYEA6h8G+9c4e2i3m8k9l2j0h8f7d5c3b1a9Z7y5x3w1v9u7t5s3r1q9p7o5n3\nm1l9k7j5i3h1g9f7e5d3c1b9a7z5y3x1w9v7u5t3s1r9q7p5o3n1m9l7k5j3i1h\nKBgQCjdw8sKzTn0xYU8QZdkW/5P0h0Z5W3V1U2T0R9Q7P2O1N8M7L6K5J4I3H2G1\nF0E9D8C7Vx1U4T3S0R5Q6P1O0N7M6L5K4J3I2H1G0F9E8D7C6Vw==\n-----END RSA PRIVATE KEY-----",
        "client_email": "test@test-project.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    service_account_b64 = base64.b64encode(json.dumps(service_account).encode()).decode()

    return Settings(
        SPREADSHEET_ID="test-sheet-id",
        URSSAF_CLIENT_ID="test-urssaf-id",
        URSSAF_CLIENT_SECRET="test-urssaf-secret",
        SWAN_API_KEY="test-swan-key",
        SWAN_ACCOUNT_ID="test-swan-account",
        SMTP_HOST="localhost",
        SMTP_USERNAME="test",
        SMTP_PASSWORD="test",
        GOOGLE_SERVICE_ACCOUNT_B64=service_account_b64,
        API_KEY_INTERNAL="test-api-key-that-is-at-least-32-characters-long",
    )


@pytest.fixture
def app(test_settings: Settings):
    """FastAPI test app."""
    return create_app(test_settings)


@pytest.fixture
def client(app):
    """FastAPI test client."""
    return TestClient(app)
