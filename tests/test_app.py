"""Tests pour le FastAPI app — CDC §8."""

from fastapi.testclient import TestClient

from src.app import app

client = TestClient(app)


class TestAppIndex:
    """Tests pour le endpoint index."""

    def test_index_returns_200(self) -> None:
        response = client.get("/")
        assert response.status_code == 200

    def test_index_returns_status_ok(self) -> None:
        response = client.get("/")
        data = response.json()
        assert data["status"] == "ok"

    def test_index_returns_project_name(self) -> None:
        response = client.get("/")
        data = response.json()
        assert "SAP-Facture" in data["message"]
