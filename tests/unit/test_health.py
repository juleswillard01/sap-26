"""Health check endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test GET /health endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "message" in data
