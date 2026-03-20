"""Tests pour le modèle Client — CDC §2."""

from src.models.client import Client, ClientStatus


class TestClientModel:
    """Tests pour le modèle Client."""

    def test_default_status_is_en_attente(self) -> None:
        client = Client(client_id="C001", nom="Dupont", prenom="Marie", email="m@test.fr")
        assert client.statut_urssaf == ClientStatus.EN_ATTENTE

    def test_default_actif_is_true(self) -> None:
        client = Client(client_id="C001", nom="Dupont", prenom="Marie", email="m@test.fr")
        assert client.actif is True

    def test_all_fields_set(self) -> None:
        client = Client(
            client_id="C001",
            nom="Dupont",
            prenom="Marie",
            email="marie@test.fr",
            telephone="0612345678",
            adresse="12 rue Test",
            code_postal="75001",
            ville="Paris",
            urssaf_id="URF-123",
            statut_urssaf=ClientStatus.INSCRIT,
            date_inscription="2026-01-15",
            actif=True,
        )
        assert client.urssaf_id == "URF-123"
        assert client.statut_urssaf == ClientStatus.INSCRIT
        assert client.ville == "Paris"
