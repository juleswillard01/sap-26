"""Adapter REST API pour AIS (app.avance-immediate.fr) — CDC §3.

Remplace le scraping Playwright par des appels REST directs
à l'API interne AIS (AWS API Gateway + Lambda + MongoDB).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

try:
    from datetime import UTC
except ImportError:
    UTC = timezone.utc

import httpx

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)


class AISAPIAdapter:
    """Client REST API pour AIS.

    AIS (Avance Immédiate Services) expose une API REST interne
    avec authentification par token. Cette classe gère:
    - Login et récupération du token
    - Lecture des clients (collection 'customer')
    - Lecture des factures (collection 'bill')
    - Gestion des relances (EN_ATTENTE > N heures)
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._token: str | None = None
        self._client = httpx.Client(timeout=float(settings.ais_timeout_sec))

    def connect(self) -> None:
        """Se connecte à AIS et récupère le token.

        Raise:
            ValueError: Si login échoue après 3 tentatives.
        """
        self._token = self._get_token_with_retry()
        logger.info("AIS login successful")

    def _get_token_with_retry(self) -> str:
        """Obtient le token avec retry 3x backoff exponentiel (réseau seul)."""
        import time

        auth_header = json.dumps(
            {
                "request": "token",
                "mail": self._settings.ais_email,
                "password": self._settings.ais_password,
            }
        )

        last_error: Exception | None = None

        for attempt in range(self._settings.ais_max_retries):
            try:
                response = self._client.post(
                    f"{self._settings.ais_api_base_url}/professional",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": auth_header,
                    },
                    json={},
                )
                response.raise_for_status()

                data = response.json()
                if not data.get("boolean"):
                    logger.error(
                        "AIS login rejected",
                        extra={"code": data.get("code"), "server_message": data.get("message")},
                    )
                    # Don't retry on client error (credentials, etc.)
                    raise ValueError(f"AIS login failed: {data.get('code')}")

                token = data.get("data")
                if not token:
                    raise ValueError("AIS login: no token in response")

                return token

            except httpx.HTTPError as e:
                logger.warning(
                    "AIS login HTTP error",
                    extra={"attempt": attempt + 1, "error": str(e)},
                )
                last_error = e
                if attempt < self._settings.ais_max_retries - 1:
                    # Exponential backoff
                    wait_time = 2**attempt
                    if wait_time > 30:
                        wait_time = 30
                    time.sleep(wait_time)
                else:
                    raise

        # Should not reach here, but ensure we have an error
        if last_error:
            raise last_error
        raise RuntimeError("AIS login failed")

    def get_profile(self) -> dict[str, Any]:
        """Récupère le profil de l'utilisateur AIS.

        Returns:
            Dict contenant: _id, professional, information (SIRET, NOVA, etc.), abonnement.

        Raises:
            ValueError: Si lecture échoue.
        """
        if not self._token:
            raise RuntimeError("Token non disponible — appeler connect() d'abord")

        return self._read_collection_single(
            collection="professional",
            request_type="read",
        )

    def get_clients(self) -> list[dict[str, Any]]:
        """Récupère la liste des clients inscrits auprès d'URSSAF.

        Returns:
            Liste de dicts contenant: _id, name, email, status (URSSAF), etc.
            Déduplique par _id.
        """
        items = self._read_collection("customer")

        # Mapper les champs AIS vers format SAP-Facture
        clients: list[dict[str, Any]] = []
        seen_ids: set[Any] = set()

        for item in items:
            client_id = item.get("_id") or item.get("id")
            if not client_id or client_id in seen_ids:
                continue

            seen_ids.add(client_id)

            # Extraire nom/prénom (peuvent être dans fields différents selon AIS)
            nom = item.get("lastName") or item.get("nom") or ""
            prenom = item.get("firstName") or item.get("prenom") or ""
            email = item.get("email") or ""
            status = item.get("status") or item.get("statut_urssaf") or ""

            clients.append(
                {
                    "client_id": client_id,
                    "nom": nom,
                    "prenom": prenom,
                    "email": email,
                    "statut_urssaf": status,
                }
            )

        logger.info("Clients AIS récupérés", extra={"count": len(clients)})
        return clients

    def get_invoices(self, status: str | None = None) -> list[dict[str, Any]]:
        """Récupère la liste des factures AIS.

        Args:
            status: Statut optionnel à filtrer (ex: 'EN_ATTENTE', 'VALIDE', 'PAYEE').

        Returns:
            Liste de dicts contenant: _id, status, amount, date, customer_id.
        """
        invoices = self.get_invoice_statuses()
        if status:
            invoices = [inv for inv in invoices if inv.get("statut") == status]
        return invoices

    def get_invoice_statuses(self) -> list[dict[str, Any]]:
        """Récupère tous les statuts de factures depuis la collection 'bill'.

        Returns:
            Liste de dicts contenant: demande_id, statut, montant, date, client_id.
            Déduplique par demande_id.
        """
        items = self._read_collection("bill")

        invoices: list[dict[str, Any]] = []
        seen_ids: set[Any] = set()

        for item in items:
            # _id ou id sont les clés primaires AIS
            demande_id = item.get("_id") or item.get("id")
            if not demande_id or demande_id in seen_ids:
                continue

            seen_ids.add(demande_id)

            # Mapper statut AIS vers format SAP-Facture
            statut = item.get("status") or item.get("statut") or "INCONNU"
            montant = item.get("amount") or item.get("montant") or 0
            date = item.get("createdAt") or item.get("date") or ""
            client_id = item.get("customerId") or item.get("customer_id") or ""

            invoices.append(
                {
                    "demande_id": demande_id,
                    "statut": statut,
                    "client_id": client_id,
                    "montant": montant,
                    "date": date,
                }
            )

        logger.info("Statuts AIS récupérés", extra={"count": len(invoices)})
        return invoices

    def get_invoice_status(self, demande_id: str) -> str:
        """Retourne le statut d'une facture spécifique.

        Args:
            demande_id: ID de la facture.

        Returns:
            Statut (ex: 'EN_ATTENTE', 'PAYEE').

        Raises:
            ValueError: Si demande_id non trouvée.
        """
        invoices = self.get_invoice_statuses()
        for inv in invoices:
            if inv.get("demande_id") == demande_id:
                return inv.get("statut", "INCONNU")
        raise ValueError(f"Demande {demande_id} non trouvée")

    def get_invoice_statuses_by_status(self, status: str) -> list[dict[str, Any]]:
        """Alias pour get_invoices(status)."""
        return self.get_invoices(status=status)

    def get_pending_reminders(self, hours_threshold: int = 36) -> list[dict[str, Any]]:
        """Identifie les factures EN_ATTENTE depuis plus de N heures.

        Args:
            hours_threshold: Seuil en heures (défaut 36).

        Returns:
            Liste de dicts (factures en attente) avec champ supplémentaire 'hours_waiting'.
        """

        invoices = self.get_invoice_statuses()
        reminders: list[dict[str, Any]] = []
        now = datetime.now(UTC)

        for inv in invoices:
            if inv.get("statut") != "EN_ATTENTE":
                continue

            date_str = inv.get("date", "")
            if not date_str:
                continue

            try:
                # Parser la date ISO
                created = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if created.tzinfo is None:
                    created = created.replace(tzinfo=UTC)

                age = now - created
                age_hours = age.total_seconds() / 3600

                if age_hours > hours_threshold:
                    inv_copy = inv.copy()
                    inv_copy["hours_waiting"] = age_hours
                    reminders.append(inv_copy)

            except (ValueError, TypeError):
                logger.warning(
                    "Impossible parser date demande",
                    extra={"demande_id": inv.get("demande_id"), "date": date_str},
                )
                continue

        logger.info(
            "Relances AIS",
            extra={"count": len(reminders), "threshold": hours_threshold},
        )
        return reminders

    def register_client(self, client_data: dict[str, Any]) -> str:
        """INTERDIT — AIS gère l'inscription clients, pas SAP-Facture."""
        raise NotImplementedError("INTERDIT — AIS gère l'inscription clients, pas SAP-Facture")

    def submit_invoice(self, client_id: str, invoice_data: dict[str, Any]) -> str:
        """INTERDIT — AIS gère la soumission factures, pas SAP-Facture."""
        raise NotImplementedError("INTERDIT — AIS gère la soumission factures, pas SAP-Facture")

    def close(self) -> None:
        """Ferme la connexion httpx."""
        if self._client:
            self._client.close()
        self._token = None

    def __enter__(self) -> AISAPIAdapter:
        """Entre le context manager."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Sort le context manager."""
        self.close()

    def _read_collection(self, collection: str) -> list[dict[str, Any]]:
        """Lit une collection MongoDB via API /mongo.

        Args:
            collection: Nom de la collection (ex: 'customer', 'bill').

        Returns:
            Liste d'items (dicts).

        Raises:
            ValueError: Si lecture échoue.
        """
        if not self._token:
            raise RuntimeError("Token non disponible")

        auth_header = json.dumps(
            {
                "request": "read",
                "token": self._token,
                "collection": collection,
            }
        )

        response = self._client.post(
            f"{self._settings.ais_api_base_url}/mongo",
            headers={
                "Content-Type": "application/json",
                "Authorization": auth_header,
            },
            json={
                "limit": 10000,
                "skip": 0,
                "compress": True,
            },
        )
        response.raise_for_status()

        data = response.json()
        if not data.get("boolean"):
            logger.error(
                "AIS read collection failed",
                extra={"collection": collection, "code": data.get("code")},
            )
            raise ValueError(f"AIS read failed: {data.get('code')}")

        items = data.get("data", {}).get("items", [])
        return items

    def _read_collection_single(
        self, collection: str, request_type: str = "read"
    ) -> dict[str, Any]:
        """Lit un objet unique (ex: profil utilisateur).

        Args:
            collection: 'professional' pour profil.
            request_type: Type de requête ('read', 'token').

        Returns:
            Dict avec données.

        Raises:
            ValueError: Si lecture échoue.
        """
        if not self._token:
            raise RuntimeError("Token non disponible")

        auth_header = json.dumps(
            {
                "request": request_type,
                "token": self._token,
            }
        )

        response = self._client.post(
            f"{self._settings.ais_api_base_url}/{collection}",
            headers={
                "Content-Type": "application/json",
                "Authorization": auth_header,
            },
            json={},
        )
        response.raise_for_status()

        data = response.json()
        if not data.get("boolean"):
            logger.error(
                "AIS read single failed",
                extra={"collection": collection, "code": data.get("code")},
            )
            raise ValueError(f"AIS read failed: {data.get('code')}")

        return data.get("data", {})

    def _make_auth_header(self, **extra: Any) -> str:
        """Construit l'en-tête Authorization en JSON.

        Args:
            **extra: Clés supplémentaires à ajouter au header.

        Returns:
            Chaîne JSON pour l'en-tête Authorization.
        """
        auth_data: dict[str, Any] = {
            "token": self._token,
            **extra,
        }
        return json.dumps(auth_data)


# Backward compatibility alias
AISAdapter = AISAPIAdapter
