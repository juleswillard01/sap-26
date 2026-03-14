from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx

from app.integrations.urssaf_exceptions import (
    URSSAFAuthError,
    URSSAFCircuitBreakerOpenError,
    URSSAFServerError,
    URSSAFTimeoutError,
    URSSAFValidationError,
)

logger = logging.getLogger(__name__)


class URSSAFClient:
    """URSSAF OAuth 2.0 API client with retry logic and circuit breaker."""

    # Circuit breaker configuration
    CIRCUIT_BREAKER_THRESHOLD = 5  # errors before opening
    CIRCUIT_BREAKER_RESET_SECONDS = 60  # reset after 60s
    REQUEST_TIMEOUT = 30  # seconds
    TOKEN_REFRESH_BUFFER = 60  # refresh 60s before expiry
    MAX_RETRIES = 3
    RETRY_BACKOFF = [1, 2, 4]  # exponential backoff in seconds

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str,
        sandbox: bool = True,
    ) -> None:
        """
        Initialize URSSAF client.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            base_url: URSSAF API base URL
            sandbox: Whether using sandbox environment
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url
        self.sandbox = sandbox

        # Token management
        self._token: str | None = None
        self._token_expiry: datetime | None = None
        self._token_lock = asyncio.Lock()

        # Circuit breaker state
        self._consecutive_errors = 0
        self._circuit_open_time: datetime | None = None

        logger.info(
            "URSSAF client initialized",
            extra={
                "client_id": client_id,
                "base_url": base_url,
                "sandbox": sandbox,
            },
        )

    async def authenticate(self) -> str:
        """
        Authenticate using OAuth 2.0 client_credentials flow.

        Returns:
            Access token string

        Raises:
            URSSAFAuthError: Authentication failed
            URSSAFServerError: Server error during authentication
            URSSAFTimeoutError: Request timeout
        """
        url = f"{self.base_url}/oauth/authorize"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        logger.info("Authenticating with URSSAF", extra={"url": url})

        try:
            async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                response = await client.post(url, data=payload)

                if response.status_code == 401:
                    logger.error(
                        "Authentication failed: invalid credentials",
                        extra={"status": response.status_code},
                    )
                    raise URSSAFAuthError("Invalid client credentials")

                if response.status_code >= 500:
                    logger.error(
                        "Authentication server error",
                        extra={"status": response.status_code, "body": response.text},
                    )
                    raise URSSAFServerError(f"Server error: {response.status_code}")

                response.raise_for_status()
                data = response.json()

                token: str = data.get("access_token")
                expires_in: int = data.get("expires_in", 3600)

                self._token = token
                self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
                self._consecutive_errors = 0

                logger.info(
                    "Authentication successful",
                    extra={
                        "expires_in": expires_in,
                        "expiry": self._token_expiry.isoformat(),
                    },
                )

                return token

        except TimeoutError as e:
            logger.error("Authentication timeout", exc_info=True)
            raise URSSAFTimeoutError("Authentication request timed out") from e
        except httpx.RequestError as e:
            logger.error(
                "Authentication request error",
                exc_info=True,
                extra={"error": str(e)},
            )
            raise URSSAFTimeoutError(f"Network error: {str(e)}") from e

    async def _ensure_token(self) -> str:
        """
        Get cached token or refresh if needed.

        Returns:
            Valid access token

        Raises:
            URSSAFAuthError: Token refresh failed
            URSSAFCircuitBreakerOpenError: Circuit breaker is open
        """
        # Check circuit breaker
        if self._circuit_open_time is not None:
            if datetime.utcnow() < (
                self._circuit_open_time + timedelta(seconds=self.CIRCUIT_BREAKER_RESET_SECONDS)
            ):
                logger.error(
                    "Circuit breaker open",
                    extra={
                        "error_count": self._consecutive_errors,
                        "reset_in": (
                            self._circuit_open_time
                            + timedelta(seconds=self.CIRCUIT_BREAKER_RESET_SECONDS)
                            - datetime.utcnow()
                        ).total_seconds(),
                    },
                )
                raise URSSAFCircuitBreakerOpenError(
                    "Too many consecutive errors, circuit breaker open"
                )
            else:
                # Reset circuit breaker
                self._circuit_open_time = None
                self._consecutive_errors = 0
                logger.info("Circuit breaker reset")

        # Check if token is valid
        if (
            self._token is not None
            and self._token_expiry is not None
            and datetime.utcnow()
            < self._token_expiry - timedelta(seconds=self.TOKEN_REFRESH_BUFFER)
        ):
            logger.debug("Using cached token")
            return self._token

        # Refresh token
        async with self._token_lock:
            # Double-check after acquiring lock
            if (
                self._token is not None
                and self._token_expiry is not None
                and datetime.utcnow()
                < self._token_expiry - timedelta(seconds=self.TOKEN_REFRESH_BUFFER)
            ):
                logger.debug("Using cached token (double-check)")
                return self._token

            logger.info("Token expired or missing, refreshing")
            token = await self.authenticate()
            return token

    async def _retry_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """
        Execute HTTP request with retry logic and circuit breaker.

        Args:
            method: HTTP method
            url: Request URL
            **kwargs: Additional httpx client arguments

        Returns:
            HTTP response

        Raises:
            URSSAFServerError: Server error (5xx) after retries
            URSSAFTimeoutError: Timeout after retries
            URSSAFCircuitBreakerOpenError: Circuit breaker is open
        """

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT) as client:
                    response = await client.request(method, url, **kwargs)

                    # Success
                    if response.status_code < 500:
                        self._consecutive_errors = 0
                        return response

                    # 5xx error - retry
                    logger.warning(
                        "Server error, will retry",
                        extra={
                            "status": response.status_code,
                            "attempt": attempt + 1,
                            "max_attempts": self.MAX_RETRIES,
                        },
                    )

                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(self.RETRY_BACKOFF[attempt])
                        continue

                    # Final attempt failed
                    self._consecutive_errors += 1
                    if self._consecutive_errors >= self.CIRCUIT_BREAKER_THRESHOLD:
                        self._circuit_open_time = datetime.utcnow()
                        logger.error(
                            "Circuit breaker opened after consecutive errors",
                            extra={"error_count": self._consecutive_errors},
                        )

                    raise URSSAFServerError(
                        f"Server error after {self.MAX_RETRIES} attempts: {response.status_code}"
                    )

            except TimeoutError as e:
                logger.warning(
                    "Request timeout, will retry",
                    extra={
                        "attempt": attempt + 1,
                        "max_attempts": self.MAX_RETRIES,
                    },
                )

                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_BACKOFF[attempt])
                    continue

                # Final attempt timed out
                self._consecutive_errors += 1
                if self._consecutive_errors >= self.CIRCUIT_BREAKER_THRESHOLD:
                    self._circuit_open_time = datetime.utcnow()
                    logger.error(
                        "Circuit breaker opened after timeout errors",
                        extra={"error_count": self._consecutive_errors},
                    )

                raise URSSAFTimeoutError(
                    f"Request timeout after {self.MAX_RETRIES} attempts"
                ) from e

            except httpx.RequestError as e:
                logger.warning(
                    "Request error, will retry",
                    extra={
                        "attempt": attempt + 1,
                        "max_attempts": self.MAX_RETRIES,
                        "error": str(e),
                    },
                )

                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_BACKOFF[attempt])
                    continue

                # Final attempt failed
                self._consecutive_errors += 1
                if self._consecutive_errors >= self.CIRCUIT_BREAKER_THRESHOLD:
                    self._circuit_open_time = datetime.utcnow()
                    logger.error(
                        "Circuit breaker opened after network errors",
                        extra={"error_count": self._consecutive_errors},
                    )

                raise URSSAFTimeoutError(f"Network error: {str(e)}") from e

        # Should not reach here
        raise URSSAFServerError("Unexpected error in retry loop")

    async def register_particulier(
        self,
        email: str,
        first_name: str,
        last_name: str,
    ) -> dict[str, Any]:
        """
        Register a particulier (client).

        Args:
            email: Client email
            first_name: Client first name
            last_name: Client last name

        Returns:
            Registration response with client ID

        Raises:
            URSSAFValidationError: Invalid input
            URSSAFServerError: Server error
            URSSAFAuthError: Authentication failed
            URSSAFTimeoutError: Request timeout
            URSSAFCircuitBreakerOpenError: Circuit breaker is open
        """
        token = await self._ensure_token()
        url = f"{self.base_url}/particulier"

        payload = {
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
        }

        headers = {"Authorization": f"Bearer {token}"}

        logger.info(
            "Registering particulier",
            extra={"email": email, "url": url},
        )

        response = await self._retry_request(
            "POST",
            url,
            json=payload,
            headers=headers,
        )

        if response.status_code == 400:
            logger.error(
                "Particulier registration validation error",
                extra={"status": 400, "body": response.text},
            )
            raise URSSAFValidationError(f"Invalid input: {response.text}")

        if response.status_code == 401:
            logger.error("Authentication failed during registration", extra={"status": 401})
            raise URSSAFAuthError("Authentication failed")

        response.raise_for_status()
        data: dict[str, Any] = response.json()

        logger.info(
            "Particulier registered successfully",
            extra={"particulier_id": data.get("id")},
        )

        return data

    async def submit_payment_request(
        self,
        intervenant_code: str,
        particulier_email: str,
        date_debut: str,
        date_fin: str,
        montant: float,
        unite_travail: str,
        code_nature: str,
        reference: str,
    ) -> dict[str, Any]:
        """
        Submit a payment request (invoice).

        Args:
            intervenant_code: Intervenant code
            particulier_email: Client email
            date_debut: Start date (YYYY-MM-DD)
            date_fin: End date (YYYY-MM-DD)
            montant: Amount in EUR
            unite_travail: Work unit (e.g., "H" for hours)
            code_nature: Nature code
            reference: Invoice reference

        Returns:
            Payment request response with request ID

        Raises:
            URSSAFValidationError: Invalid input
            URSSAFServerError: Server error
            URSSAFAuthError: Authentication failed
            URSSAFTimeoutError: Request timeout
            URSSAFCircuitBreakerOpenError: Circuit breaker is open
        """
        token = await self._ensure_token()
        url = f"{self.base_url}/payment-request"

        payload = {
            "intervenantCode": intervenant_code,
            "particulierEmail": particulier_email,
            "dateDebut": date_debut,
            "dateFin": date_fin,
            "montant": montant,
            "uniteTravail": unite_travail,
            "codeNature": code_nature,
            "reference": reference,
        }

        headers = {"Authorization": f"Bearer {token}"}

        logger.info(
            "Submitting payment request",
            extra={
                "url": url,
                "reference": reference,
                "montant": montant,
            },
        )

        response = await self._retry_request(
            "POST",
            url,
            json=payload,
            headers=headers,
        )

        if response.status_code == 400:
            logger.error(
                "Payment request validation error",
                extra={"status": 400, "body": response.text},
            )
            raise URSSAFValidationError(f"Invalid input: {response.text}")

        if response.status_code == 401:
            logger.error("Authentication failed during payment request", extra={"status": 401})
            raise URSSAFAuthError("Authentication failed")

        response.raise_for_status()
        data: dict[str, Any] = response.json()

        logger.info(
            "Payment request submitted successfully",
            extra={"request_id": data.get("id")},
        )

        return data

    async def get_payment_status(self, request_id: str) -> dict[str, Any]:
        """
        Get payment request status.

        Args:
            request_id: Payment request ID

        Returns:
            Payment status response

        Raises:
            URSSAFServerError: Server error
            URSSAFAuthError: Authentication failed
            URSSAFTimeoutError: Request timeout
            URSSAFCircuitBreakerOpenError: Circuit breaker is open
        """
        token = await self._ensure_token()
        url = f"{self.base_url}/payment-request/{request_id}"

        headers = {"Authorization": f"Bearer {token}"}

        logger.info(
            "Getting payment status",
            extra={"url": url, "request_id": request_id},
        )

        response = await self._retry_request(
            "GET",
            url,
            headers=headers,
        )

        if response.status_code == 401:
            logger.error("Authentication failed during status check", extra={"status": 401})
            raise URSSAFAuthError("Authentication failed")

        response.raise_for_status()
        data: dict[str, Any] = response.json()

        logger.info(
            "Payment status retrieved",
            extra={
                "request_id": request_id,
                "status": data.get("status"),
            },
        )

        return data
