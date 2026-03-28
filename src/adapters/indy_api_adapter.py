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

from src.adapters.exceptions import (
    IndyAPIError,
    IndyAuthError,
    IndyConnectionError,
    IndyLoginError,
)
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

    def connect(self, *, custom_token: str | None = None) -> None:
        """Login Indy et obtient un Bearer JWT Firebase.

        Args:
            custom_token: Si fourni, skip nodriver et échange directement
                le custom token contre un JWT. Utile pour les tests et
                quand un token pré-obtenu est disponible.

        Flow sans custom_token:
            nodriver (Turnstile+2FA) → customToken → Firebase JWT.
        Flow avec custom_token:
            customToken → Firebase JWT (0 browser).
        """
        if custom_token is None:
            custom_token = self._login_with_nodriver()

        id_token, refresh_token, expires_in = self._exchange_custom_token(custom_token)
        self._id_token = id_token
        self._refresh_token = refresh_token
        self._token_expires_at = time.time() + expires_in
        logger.info("Indy connected (JWT TTL %ds)", expires_in)

    def _login_with_nodriver(self) -> str:
        """Login Indy via nodriver headless browser.

        Sync wrapper autour de _async_nodriver_login().
        Lance nodriver pour Turnstile bypass + 2FA Gmail → retourne customToken.

        Returns:
            Firebase custom token string.

        Raises:
            IndyLoginError: Si le login échoue (timeout, 2FA, Turnstile).
        """
        import asyncio

        return asyncio.run(self._async_nodriver_login())

    async def _async_nodriver_login(self) -> str:
        """Login Indy via nodriver — implémentation async.

        1. Navigate /connexion, fill email+password
        2. Submit (nodriver bypass Turnstile)
        3. Intercepte POST /api/auth/login via CDP
        4. Si 401: 2FA → poll Gmail → re-submit avec code
        5. Si 200: retourne customToken
        """
        import json as json_mod

        import nodriver as uc  # type: ignore[import-untyped]

        captured: dict[str, Any] = {}

        def _on_response(event: Any) -> None:
            url = getattr(getattr(event, "response", None), "url", "") or ""
            if "/api/auth/login" in url:
                captured["status"] = event.response.status
                captured["request_id"] = event.request_id

        browser = await uc.start(  # type: ignore[reportUnknownMemberType]
            headless=True,
            browser_args=["--no-first-run", "--no-default-browser-check"],
        )
        try:
            page = await browser.get(f"{self._settings.indy_api_base_url}/connexion")
            await page.sleep(3)

            await page.send(uc.cdp.network.enable())
            page.add_handler(  # type: ignore[reportUnknownMemberType]
                uc.cdp.network.ResponseReceived, _on_response
            )

            await self._fill_login_form(page)
            custom_token = await self._capture_login_response(page, captured, json_mod)

            if custom_token:
                logger.info("Indy nodriver login successful")
                return custom_token

            if captured.get("status") == 401:
                custom_token = await self._handle_2fa_flow(page, captured, json_mod)
                if custom_token:
                    return custom_token

            raise IndyLoginError(
                f"Login failed (HTTP {captured.get('status', 'unknown')})",
                http_status=captured.get("status"),
            )
        finally:
            browser.stop()

    async def _fill_login_form(self, page: Any) -> None:
        """Remplit et soumet le formulaire de login Indy."""
        email_input = await page.find("input[type='email']", timeout=10)
        if email_input:
            await email_input.send_keys(self._settings.indy_email)

        password_input = await page.find("input[type='password']", timeout=10)
        if password_input:
            await password_input.send_keys(self._settings.indy_password)

        await page.sleep(1)
        submit_btn = await page.find("button[type='submit']", timeout=10)
        if submit_btn:
            await submit_btn.click()

    async def _capture_login_response(
        self,
        page: Any,
        captured: dict[str, Any],
        json_mod: Any,
    ) -> str | None:
        """Attend et capture la réponse POST /api/auth/login."""
        for _ in range(30):
            await page.sleep(1)
            if "request_id" in captured:
                break

        if "request_id" not in captured:
            raise IndyLoginError("Login request not intercepted within 30s")

        body_data = await page.send(
            __import__("nodriver").cdp.network.get_response_body(captured["request_id"])
        )
        response_json = json_mod.loads(body_data[0])

        if captured.get("status") == 200:
            token = response_json.get("customToken")
            if token:
                return token
            raise IndyLoginError("customToken missing from 200 response")

        return None

    async def _handle_2fa_flow(
        self,
        page: Any,
        captured: dict[str, Any],
        json_mod: Any,
    ) -> str:
        """Gère le flow 2FA: poll Gmail → inject code → re-submit."""
        logger.info("2FA required — polling Gmail for verification code")
        code = await self._poll_gmail_2fa_code()

        captured.clear()
        code_input = await page.find(
            "input[placeholder*='code' i], input[name='code'], input[type='text']",
            timeout=15,
        )
        if code_input:
            await code_input.send_keys(code)

        verify_btn = await page.find("button[type='submit']", timeout=10)
        if verify_btn:
            await verify_btn.click()

        for _ in range(30):
            await page.sleep(1)
            if "request_id" in captured:
                break

        if "request_id" not in captured:
            raise IndyLoginError("2FA login response not captured")

        body_data = await page.send(
            __import__("nodriver").cdp.network.get_response_body(captured["request_id"])
        )
        response_json = json_mod.loads(body_data[0])

        if captured.get("status") != 200:
            raise IndyLoginError(
                f"2FA login failed (HTTP {captured.get('status')})",
                http_status=captured.get("status"),
            )

        token = response_json.get("customToken")
        if not token:
            raise IndyLoginError("customToken missing after 2FA")

        logger.info("Indy 2FA login successful")
        return token

    async def _poll_gmail_2fa_code(self) -> str:
        """Poll Gmail IMAP pour le code 2FA Indy."""
        from src.adapters.gmail_reader import GmailReader

        reader = GmailReader(self._settings)
        try:
            reader.connect()
            reader.flush_old_emails()
            code = reader.get_latest_2fa_code(timeout_sec=60)
            if not code:
                raise IndyLoginError("2FA code not received from Gmail within 60s")
            return code
        finally:
            reader.close()

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
