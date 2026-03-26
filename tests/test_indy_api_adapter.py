"""Tests for IndyAPIAdapter REST httpx — MPP-65.

TDD RED phase: all tests must FAIL before implementation.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.adapters.exceptions import (
    IndyAPIError,
    IndyAuthError,
    IndyConnectionError,
    IndyError,
    IndyLoginError,
)
from src.config import Settings

# ============================================================================
# T1: Exceptions hierarchy
# ============================================================================


class TestIndyExceptions:
    """Test Indy exception hierarchy."""

    def test_indy_error_is_base_exception(self) -> None:
        err = IndyError("something broke")
        assert isinstance(err, Exception)
        assert str(err) == "something broke"
        assert err.message == "something broke"

    def test_indy_error_default_message(self) -> None:
        err = IndyError()
        assert err.message == "An error occurred with Indy"

    def test_indy_error_http_status(self) -> None:
        err = IndyError("fail", http_status=500)
        assert err.http_status == 500

    def test_indy_error_http_status_default_none(self) -> None:
        err = IndyError("fail")
        assert err.http_status is None

    def test_indy_login_error_inherits(self) -> None:
        err = IndyLoginError("login failed")
        assert isinstance(err, IndyError)
        assert isinstance(err, Exception)

    def test_indy_auth_error_inherits(self) -> None:
        err = IndyAuthError("token exchange failed")
        assert isinstance(err, IndyError)

    def test_indy_api_error_inherits(self) -> None:
        err = IndyAPIError("API 500", http_status=500)
        assert isinstance(err, IndyError)
        assert err.http_status == 500

    def test_indy_connection_error_inherits(self) -> None:
        err = IndyConnectionError("not connected")
        assert isinstance(err, IndyError)


# ============================================================================
# T2: Settings
# ============================================================================


class TestIndyAPISettings:
    """Test Indy API settings in config."""

    def test_settings_indy_api_base_url_default(self) -> None:
        settings = Settings()
        assert settings.indy_api_base_url == "https://app.indy.fr"

    def test_settings_indy_api_timeout_default(self) -> None:
        settings = Settings()
        assert settings.indy_api_timeout_sec == 30

    def test_settings_indy_firebase_api_key_default(self) -> None:
        settings = Settings()
        assert settings.indy_firebase_api_key == "AIzaSyAVJ8xwjy0uG-zgPKQKUADa2-c-4KKHryI"


# ============================================================================
# T3: IndyAPIAdapter
# ============================================================================


@pytest.fixture()
def settings() -> Settings:
    """Settings with Indy credentials."""
    return Settings(
        indy_email="test@example.com",
        indy_password="secret123",
        gmail_imap_user="gmail@example.com",
        gmail_imap_password="gmail_pass",
    )


@pytest.fixture()
def settings_no_creds() -> Settings:
    """Settings without Indy credentials."""
    return Settings(indy_email="", indy_password="")


class TestIndyAPIAdapterInit:
    """Test adapter initialization."""

    def test_init_valid_settings(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        assert adapter is not None
        adapter.close()

    def test_init_missing_email_raises(self, settings_no_creds: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        with pytest.raises(ValueError, match="indy_email"):
            IndyAPIAdapter(settings_no_creds)

    def test_init_missing_password_raises(self) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        s = Settings(indy_email="test@example.com", indy_password="")
        with pytest.raises(ValueError, match="indy_password"):
            IndyAPIAdapter(s)


class TestIndyAPIAdapterConnectionError:
    """Test that methods raise IndyConnectionError when not connected."""

    def test_get_transactions_not_connected(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        with pytest.raises(IndyConnectionError):
            adapter.get_transactions("2025-01-01", "2025-12-31")

    def test_get_balance_not_connected(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        with pytest.raises(IndyConnectionError):
            adapter.get_balance()

    def test_get_account_statements_not_connected(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        with pytest.raises(IndyConnectionError):
            adapter.get_account_statements()

    def test_get_accounting_summary_not_connected(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        with pytest.raises(IndyConnectionError):
            adapter.get_accounting_summary()


class TestIndyAPIAdapterTokenExchange:
    """Test Firebase token exchange."""

    def test_exchange_custom_token_success(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "idToken": "fake-jwt",
            "refreshToken": "fake-refresh",
            "expiresIn": "3600",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(adapter, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            id_token, refresh_token, expires_in = adapter._exchange_custom_token(
                "fake-custom-token"
            )

        assert id_token == "fake-jwt"
        assert refresh_token == "fake-refresh"
        assert expires_in == 3600

    def test_exchange_custom_token_failure_raises(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )

        with patch.object(adapter, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            with pytest.raises(IndyAuthError):
                adapter._exchange_custom_token("bad-token")


class TestIndyAPIAdapterRefreshToken:
    """Test Firebase token refresh."""

    def test_refresh_bearer_token_success(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        adapter._id_token = "old-jwt"
        adapter._refresh_token = "valid-refresh"
        adapter._token_expires_at = time.time() - 100  # expired

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id_token": "new-jwt",
            "refresh_token": "new-refresh",
            "expires_in": "3600",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(adapter, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            adapter._refresh_bearer_token()

        assert adapter._id_token == "new-jwt"
        assert adapter._refresh_token == "new-refresh"

    def test_refresh_bearer_token_failure_raises(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        adapter._refresh_token = "expired-refresh"

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )

        with patch.object(adapter, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            with pytest.raises(IndyAuthError):
                adapter._refresh_bearer_token()


class TestIndyAPIAdapterEnsureToken:
    """Test token validity check and auto-refresh."""

    def test_ensure_token_valid_does_nothing(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        adapter._id_token = "valid-jwt"
        adapter._refresh_token = "refresh"
        adapter._token_expires_at = time.time() + 600  # 10min left

        # Should not raise, should not refresh
        adapter._ensure_token()
        assert adapter._id_token == "valid-jwt"

    def test_ensure_token_expired_triggers_refresh(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        adapter._id_token = "old-jwt"
        adapter._refresh_token = "refresh"
        adapter._token_expires_at = time.time() + 60  # <5min

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id_token": "new-jwt",
            "refresh_token": "new-refresh",
            "expires_in": "3600",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(adapter, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            adapter._ensure_token()

        assert adapter._id_token == "new-jwt"


# ============================================================================
# Fixtures for connected adapter
# ============================================================================


@pytest.fixture()
def connected_adapter(settings: Settings) -> Any:
    """An adapter with token state set (simulating post-connect)."""
    from src.adapters.indy_api_adapter import IndyAPIAdapter

    adapter = IndyAPIAdapter(settings)
    adapter._id_token = "valid-jwt"
    adapter._refresh_token = "valid-refresh"
    adapter._token_expires_at = time.time() + 3600
    return adapter


# ============================================================================
# T3: get_transactions
# ============================================================================


SAMPLE_TRANSACTIONS_RESPONSE: dict[str, Any] = {
    "transactions": [
        {
            "_id": "txn001",
            "date": "2025-06-15",
            "description": "VIREMENT URSSAF",
            "rawDescription": "VIR URSSAF CESU",
            "amountInCents": 15000,
            "totalAmountInCents": 15000,
            "transactionType": "od",
            "bankAccountId": "Xv7tiXcgbqoiKJ97k",
            "isVerified": False,
            "isDeleted": False,
            "subdivisions": [],
        },
        {
            "_id": "txn002",
            "date": "2025-06-16",
            "description": "Paiement CB",
            "rawDescription": "CB ACHAT",
            "amountInCents": -4590,
            "totalAmountInCents": -4590,
            "transactionType": "prelevement",
            "bankAccountId": "Xv7tiXcgbqoiKJ97k",
            "isVerified": True,
            "isDeleted": False,
            "subdivisions": [],
        },
    ],
    "nbTransactions": 2,
    "toCategorizeCount": 0,
}


class TestGetTransactions:
    """Test get_transactions method."""

    def test_happy_path(self, connected_adapter: Any) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_TRANSACTIONS_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            txns = connected_adapter.get_transactions("2025-06-01", "2025-06-30")

        assert len(txns) == 2
        assert txns[0].indy_id == "txn001"
        assert txns[0].montant == 150.00  # cents → EUR
        assert txns[0].libelle == "VIREMENT URSSAF"
        assert txns[0].date_valeur == date(2025, 6, 15)
        assert txns[0].source == "indy"

    def test_negative_amount_conversion(self, connected_adapter: Any) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_TRANSACTIONS_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            txns = connected_adapter.get_transactions("2025-06-01", "2025-06-30")

        assert txns[1].montant == -45.90  # negative cents → EUR

    def test_empty_transactions(self, connected_adapter: Any) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transactions": [],
            "nbTransactions": 0,
            "toCategorizeCount": 0,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            txns = connected_adapter.get_transactions("2025-01-01", "2025-01-31")

        assert txns == []

    def test_dedup_by_id(self, connected_adapter: Any) -> None:
        """Duplicate _id should be deduplicated."""
        dup_response = {
            "transactions": [
                {
                    "_id": "txn001",
                    "date": "2025-06-15",
                    "description": "First",
                    "rawDescription": "",
                    "amountInCents": 10000,
                    "totalAmountInCents": 10000,
                    "transactionType": "od",
                    "bankAccountId": "acc1",
                    "isVerified": False,
                    "isDeleted": False,
                    "subdivisions": [],
                },
                {
                    "_id": "txn001",
                    "date": "2025-06-15",
                    "description": "Duplicate",
                    "rawDescription": "",
                    "amountInCents": 10000,
                    "totalAmountInCents": 10000,
                    "transactionType": "od",
                    "bankAccountId": "acc1",
                    "isVerified": False,
                    "isDeleted": False,
                    "subdivisions": [],
                },
            ],
            "nbTransactions": 2,
            "toCategorizeCount": 0,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = dup_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            txns = connected_adapter.get_transactions("2025-06-01", "2025-06-30")

        assert len(txns) == 1
        assert txns[0].libelle == "First"

    def test_api_error_raises(self, connected_adapter: Any) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            with pytest.raises(IndyAPIError):
                connected_adapter.get_transactions("2025-01-01", "2025-12-31")

    def test_date_params_passed_to_api(self, connected_adapter: Any) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transactions": [],
            "nbTransactions": 0,
            "toCategorizeCount": 0,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            connected_adapter.get_transactions("2025-06-01", "2025-06-30")

            call_kwargs = mock_client.get.call_args
            params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params", {})
            assert params.get("startDate") == "2025-06-01"
            assert params.get("endDate") == "2025-06-30"


# ============================================================================
# T3: get_balance
# ============================================================================


SAMPLE_BANK_ACCOUNT_RESPONSE: dict[str, Any] = {
    "_id": "Xv7tiXcgbqoiKJ97k",
    "name": "Compte courant",
    "balanceInCents": 123456,
    "availableBalanceInCents": 120000,
    "lastSyncAt": "2026-03-26T05:39:18.276Z",
    "bankConnector": {
        "id": "76e14af1-a2db-452d-b818-5b3b37b305a8",
        "type": "swan",
        "accountStatus": "Opened",
    },
}


class TestGetBalance:
    """Test get_balance method."""

    def test_happy_path_cents_to_eur(self, connected_adapter: Any) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_BANK_ACCOUNT_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            balance = connected_adapter.get_balance()

        assert balance == 1234.56

    def test_zero_balance(self, connected_adapter: Any) -> None:
        response = {**SAMPLE_BANK_ACCOUNT_RESPONSE, "balanceInCents": 0}
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response
        mock_response.raise_for_status = MagicMock()

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            balance = connected_adapter.get_balance()

        assert balance == 0.0

    def test_api_error_raises(self, connected_adapter: Any) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            with pytest.raises(IndyAPIError):
                connected_adapter.get_balance()


# ============================================================================
# T3: get_account_statements
# ============================================================================


SAMPLE_STATEMENTS_RESPONSE: list[dict[str, str]] = [
    {
        "closingDate": "2026-02-28",
        "url": "https://documents-v2.swan.io/accounts/xxx/ReleveCompte.pdf?Expires=123",
    },
    {
        "closingDate": "2026-01-31",
        "url": "https://documents-v2.swan.io/accounts/xxx/ReleveCompte2.pdf?Expires=456",
    },
]


class TestGetAccountStatements:
    """Test get_account_statements method."""

    def test_happy_path(self, connected_adapter: Any) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_STATEMENTS_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            statements = connected_adapter.get_account_statements()

        assert len(statements) == 2
        assert statements[0]["closingDate"] == "2026-02-28"
        assert "swan.io" in statements[0]["url"]

    def test_empty_statements(self, connected_adapter: Any) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            statements = connected_adapter.get_account_statements()

        assert statements == []


# ============================================================================
# T3: get_accounting_summary
# ============================================================================


SAMPLE_SUMMARY_RESPONSE: dict[str, Any] = {
    "totalTransactionsCount": 42,
    "totalAmountInCents": 500000,
    "totalIncomeAmountInCents": 800000,
    "totalExpenseAmountInCents": -300000,
}


class TestGetAccountingSummary:
    """Test get_accounting_summary method."""

    def test_happy_path(self, connected_adapter: Any) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_SUMMARY_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            summary = connected_adapter.get_accounting_summary()

        assert summary["totalTransactionsCount"] == 42
        assert summary["totalAmountInCents"] == 500000

    def test_with_date_filter(self, connected_adapter: Any) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = SAMPLE_SUMMARY_RESPONSE
        mock_response.raise_for_status = MagicMock()

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            connected_adapter.get_accounting_summary("2025-01-01", "2025-12-31")

            call_kwargs = mock_client.post.call_args
            json_body = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json", {})
            assert json_body.get("startDate") == "2025-01-01"
            assert json_body.get("endDate") == "2025-12-31"


# ============================================================================
# T3: Context manager
# ============================================================================


class TestContextManager:
    """Test sync context manager."""

    def test_enter_exit(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)

        # Patch connect to avoid actual login
        with patch.object(adapter, "connect"), adapter as a:
            assert a is adapter
        # After exit, token should be cleared
        assert adapter._id_token is None

    def test_close_is_idempotent(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        adapter.close()
        adapter.close()  # Should not raise


# ============================================================================
# T3: Retry behavior
# ============================================================================


class TestRetryBehavior:
    """Test retry on transient errors."""

    def test_retry_on_5xx(self, connected_adapter: Any) -> None:
        """Should retry 3x on 5xx then raise IndyAPIError."""
        fail_response = MagicMock()
        fail_response.status_code = 503
        fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable", request=MagicMock(), response=fail_response
        )

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = fail_response
            with pytest.raises(IndyAPIError):
                connected_adapter.get_balance()

            # Should have retried (tenacity 3 attempts)
            assert mock_client.get.call_count == 3

    def test_no_retry_on_4xx(self, connected_adapter: Any) -> None:
        """Should NOT retry on 4xx (client error)."""
        fail_response = MagicMock()
        fail_response.status_code = 403
        fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=MagicMock(), response=fail_response
        )

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = fail_response
            with pytest.raises(IndyAPIError):
                connected_adapter.get_balance()

            # Should NOT have retried
            assert mock_client.get.call_count == 1


# ============================================================================
# C1: Network errors (timeout, connect) wrapped + retried
# ============================================================================


class TestNetworkErrors:
    """Test httpx.TimeoutException and ConnectError handling."""

    def test_timeout_raises_indy_api_error(self, connected_adapter: Any) -> None:
        """Timeout should be wrapped as IndyAPIError."""
        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.side_effect = httpx.TimeoutException("read timeout")
            with pytest.raises(IndyAPIError, match="timed out"):
                connected_adapter.get_balance()

    def test_connect_error_raises_indy_api_error(self, connected_adapter: Any) -> None:
        """ConnectError should be wrapped as IndyAPIError."""
        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.side_effect = httpx.ConnectError("DNS resolution failed")
            with pytest.raises(IndyAPIError, match="Connection"):
                connected_adapter.get_balance()

    def test_timeout_is_retried(self, connected_adapter: Any) -> None:
        """Timeouts should be retried 3x."""
        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            with pytest.raises(IndyAPIError):
                connected_adapter.get_balance()
            assert mock_client.get.call_count == 3

    def test_connect_error_is_retried(self, connected_adapter: Any) -> None:
        """Connect errors should be retried 3x."""
        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.side_effect = httpx.ConnectError("refused")
            with pytest.raises(IndyAPIError):
                connected_adapter.get_balance()
            assert mock_client.get.call_count == 3


# ============================================================================
# C2: Firebase KeyError handling
# ============================================================================


class TestFirebaseKeyError:
    """Test that malformed Firebase responses raise IndyAuthError."""

    def test_exchange_missing_id_token(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"refreshToken": "r", "expiresIn": "3600"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(adapter, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            with pytest.raises(IndyAuthError, match="missing"):
                adapter._exchange_custom_token("token")

    def test_refresh_missing_id_token(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        adapter._refresh_token = "valid"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"refresh_token": "r", "expires_in": "3600"}
        mock_response.raise_for_status = MagicMock()

        with patch.object(adapter, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            with pytest.raises(IndyAuthError, match="missing"):
                adapter._refresh_bearer_token()


# ============================================================================
# H1: _refresh_bearer_token guard on None refresh_token
# ============================================================================


class TestRefreshTokenGuard:
    """Test that refresh with None token raises early."""

    def test_refresh_with_none_token_raises(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        adapter._refresh_token = None
        with pytest.raises(IndyAuthError, match="refresh token"):
            adapter._refresh_bearer_token()


# ============================================================================
# M1: _to_transaction defensive handling
# ============================================================================


class TestToTransactionDefensive:
    """Test _to_transaction handles malformed entries."""

    def test_malformed_transaction_skipped(self, connected_adapter: Any) -> None:
        """Malformed entries should be skipped, not crash the batch."""
        response = {
            "transactions": [
                {
                    "_id": "good1",
                    "date": "2025-06-15",
                    "description": "OK",
                    "amountInCents": 10000,
                    "transactionType": "od",
                },
                {
                    "date": "2025-06-16",
                    "description": "Missing _id",
                    "amountInCents": 5000,
                },
                {
                    "_id": "good2",
                    "date": "2025-06-17",
                    "description": "Also OK",
                    "amountInCents": 20000,
                    "transactionType": "virement",
                },
            ],
            "nbTransactions": 3,
            "toCategorizeCount": 0,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = response
        mock_response.raise_for_status = MagicMock()

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            txns = connected_adapter.get_transactions("2025-06-01", "2025-06-30")

        assert len(txns) == 2
        assert txns[0].indy_id == "good1"
        assert txns[1].indy_id == "good2"


# ============================================================================
# M2: get_pending_transactions test
# ============================================================================


class TestGetPendingTransactions:
    """Test get_pending_transactions method."""

    def test_happy_path(self, connected_adapter: Any) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "pendingTransactions": [],
            "upcomingTransactions": [],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.get.return_value = mock_response
            result = connected_adapter.get_pending_transactions()

        assert result["pendingTransactions"] == []


# ============================================================================
# M3: _api_post error path test
# ============================================================================


class TestApiPostError:
    """Test _api_post error handling."""

    def test_accounting_summary_api_error(self, connected_adapter: Any) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )

        with patch.object(connected_adapter, "_client") as mock_client:
            mock_client.post.return_value = mock_response
            with pytest.raises(IndyAPIError):
                connected_adapter.get_accounting_summary()


# ============================================================================
# M4: close() explicit idempotency
# ============================================================================


class TestCloseIdempotency:
    """Test close() with explicit state tracking."""

    def test_close_clears_state(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        adapter._id_token = "token"
        adapter._refresh_token = "refresh"
        adapter.close()

        assert adapter._id_token is None
        assert adapter._refresh_token is None

    def test_close_twice_no_error(self, settings: Settings) -> None:
        from src.adapters.indy_api_adapter import IndyAPIAdapter

        adapter = IndyAPIAdapter(settings)
        adapter.close()
        adapter.close()  # must not raise
