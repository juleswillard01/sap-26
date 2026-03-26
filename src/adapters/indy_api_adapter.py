"""Adapter REST API pour Indy Banking via httpx — MPP-65.

Remplace le scraping Playwright par des appels REST directs
à l'API interne Indy (Firebase Auth + Bearer JWT).
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import TYPE_CHECKING, Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.adapters.exceptions import IndyAPIError, IndyAuthError, IndyConnectionError
from src.models.transaction import Transaction

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)

_FIREBASE_IDENTITY_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken"
_FIREBASE_REFRESH_URL = "https://securetoken.googleapis.com/v1/token"
_TOKEN_REFRESH_BUFFER_SEC = 300


def _is_retryable(exc: BaseException) -> bool:
    """Retry sur 5xx et erreurs réseau (timeout, connexion)."""
    if isinstance(exc, IndyAPIError):
        if exc.http_status is None:
            return True  # network errors (timeout, connect)
        return exc.http_status >= 500
    return False


class IndyAPIAdapter:
    """Client REST API pour Indy Banking.

    Auth: nodriver login (1x Turnstile) → Firebase JWT → refresh httpx.
    Toutes les opérations bancaires passent par httpx (pas de browser).
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.indy_email:
            msg = "indy_email requis dans les settings"
            raise ValueError(msg)
        if not settings.indy_password:
            msg = "indy_password requis dans les settings"
            raise ValueError(msg)

        self._settings = settings
        self._client = httpx.Client(
            base_url=settings.indy_api_base_url,
            timeout=float(settings.indy_api_timeout_sec),
        )
        self._id_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires_at: float = 0.0
        self._closed = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Login via nodriver + Firebase token exchange.

        Flow: nodriver (Turnstile+2FA) → customToken → Firebase JWT.
        """
        msg = "connect() requires nodriver integration — see plan.md"
        raise NotImplementedError(msg)

    def close(self) -> None:
        """Ferme le client httpx et nettoie les tokens. Idempotent."""
        if not self._closed:
            self._client.close()
            self._closed = True
        self._id_token = None
        self._refresh_token = None
        self._token_expires_at = 0.0

    def __enter__(self) -> IndyAPIAdapter:
        """Context manager — appelle connect()."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager — appelle close()."""
        self.close()

    # ------------------------------------------------------------------
    # Auth internals
    # ------------------------------------------------------------------

    def _exchange_custom_token(self, custom_token: str) -> tuple[str, str, int]:
        """Échange un custom token Firebase contre un Bearer JWT.

        Returns:
            Tuple (id_token, refresh_token, expires_in_seconds).
        """
        url = f"{_FIREBASE_IDENTITY_URL}?key={self._settings.indy_firebase_api_key}"
        try:
            response = self._client.post(
                url,
                json={"token": custom_token, "returnSecureToken": True},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise IndyAuthError(
                "Firebase token exchange failed",
                http_status=e.response.status_code,
            ) from e

        data = response.json()
        try:
            return data["idToken"], data["refreshToken"], int(data["expiresIn"])
        except (KeyError, TypeError, ValueError) as e:
            raise IndyAuthError(f"Firebase response missing key: {e}") from e

    def _refresh_bearer_token(self) -> None:
        """Refresh le Bearer JWT via Firebase refresh token."""
        if self._refresh_token is None:
            raise IndyAuthError("No refresh token available — connect() required")

        url = f"{_FIREBASE_REFRESH_URL}?key={self._settings.indy_firebase_api_key}"
        try:
            response = self._client.post(
                url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise IndyAuthError(
                "Token refresh failed",
                http_status=e.response.status_code,
            ) from e

        data = response.json()
        try:
            self._id_token = data["id_token"]
            self._refresh_token = data["refresh_token"]
            self._token_expires_at = time.time() + int(data["expires_in"])
        except (KeyError, TypeError, ValueError) as e:
            raise IndyAuthError(f"Firebase refresh response missing key: {e}") from e
        logger.info("Indy token refreshed")

    def _ensure_token(self) -> None:
        """Refresh le token si expiration < 5 minutes."""
        remaining = self._token_expires_at - time.time()
        if remaining < _TOKEN_REFRESH_BUFFER_SEC:
            self._refresh_bearer_token()

    def _ensure_connected(self) -> None:
        """Lève IndyConnectionError si connect() non appelé."""
        if self._id_token is None:
            raise IndyConnectionError("connect() must be called first")

    # ------------------------------------------------------------------
    # API internals (avec retry)
    # ------------------------------------------------------------------

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, max=2),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    def _api_get(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> Any:
        """GET avec Bearer auth + retry 3x sur 5xx."""
        self._ensure_connected()
        self._ensure_token()
        try:
            response = self._client.get(
                path,
                params=params,
                headers={"Authorization": f"Bearer {self._id_token}"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise IndyAPIError(
                f"GET {path} failed: {e.response.status_code}",
                http_status=e.response.status_code,
            ) from e
        except httpx.TimeoutException as e:
            raise IndyAPIError(f"GET {path} timed out") from e
        except httpx.ConnectError as e:
            raise IndyAPIError(f"Connection to {path} failed") from e
        return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.1, max=2),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    def _api_post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """POST avec Bearer auth + retry 3x sur 5xx."""
        self._ensure_connected()
        self._ensure_token()
        try:
            response = self._client.post(
                path,
                json=json or {},
                headers={"Authorization": f"Bearer {self._id_token}"},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise IndyAPIError(
                f"POST {path} failed: {e.response.status_code}",
                http_status=e.response.status_code,
            ) from e
        except httpx.TimeoutException as e:
            raise IndyAPIError(f"POST {path} timed out") from e
        except httpx.ConnectError as e:
            raise IndyAPIError(f"Connection to {path} failed") from e
        return response.json()

    # ------------------------------------------------------------------
    # Data conversion
    # ------------------------------------------------------------------

    def _to_transaction(self, raw: dict[str, Any]) -> Transaction:
        """Convertit une transaction API (cents) → Transaction (EUR)."""
        return Transaction(
            transaction_id=raw["_id"],
            indy_id=raw["_id"],
            date_valeur=date.fromisoformat(raw["date"]),
            montant=round(raw["amountInCents"] / 100.0, 2),
            libelle=raw.get("description") or raw.get("rawDescription", ""),
            type=raw.get("transactionType", ""),
            source="indy",
            date_import=date.today(),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_transactions(
        self,
        start_date: str,
        end_date: str,
    ) -> list[Transaction]:
        """Récupère les transactions Indy (filtre dates, dedup, EUR).

        Args:
            start_date: Date début ISO (YYYY-MM-DD).
            end_date: Date fin ISO (YYYY-MM-DD).

        Returns:
            Liste de Transaction (montants en EUR, dédupliquées par _id).
        """
        data = self._api_get(
            "/api/transactions/transactions-list",
            params={"startDate": start_date, "endDate": end_date},
        )
        seen: set[str] = set()
        transactions: list[Transaction] = []
        for raw in data.get("transactions", []):
            try:
                txn_id: str = raw["_id"]
            except (KeyError, TypeError):
                logger.warning("Skipping malformed transaction: missing _id")
                continue
            if txn_id in seen:
                continue
            seen.add(txn_id)
            try:
                transactions.append(self._to_transaction(raw))
            except (KeyError, TypeError, ValueError) as e:
                logger.warning(
                    "Skipping malformed transaction",
                    extra={"txn_id": txn_id, "error": str(e)},
                )

        logger.info(
            "Fetched transactions",
            extra={"count": len(transactions), "start": start_date, "end": end_date},
        )
        return transactions

    def get_pending_transactions(self) -> dict[str, Any]:
        """Récupère les transactions en attente."""
        return self._api_get("/api/transactions/transactions-pending-list")

    def get_balance(self) -> float:
        """Récupère le solde du compte en EUR."""
        data = self._api_get("/api/compte-pro/bank-account")
        balance = round(data["balanceInCents"] / 100.0, 2)
        logger.info("Balance fetched", extra={"balance_eur": balance})
        return balance

    def get_account_statements(self) -> list[dict[str, str]]:
        """Récupère les relevés mensuels (URLs PDF pré-signées Swan)."""
        return self._api_get("/api/compte-pro/account-statements")

    def get_accounting_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Récupère le résumé comptable (totaux revenus/dépenses)."""
        body: dict[str, str] = {}
        if start_date:
            body["startDate"] = start_date
        if end_date:
            body["endDate"] = end_date
        return self._api_post("/api/accounting/transactions/summary", json=body)
