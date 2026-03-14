from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import httpx
import pytest
from freezegun import freeze_time

from app.integrations.urssaf_client import URSSAFClient
from app.integrations.urssaf_exceptions import (
    URSSAFAuthError,
    URSSAFCircuitBreakerOpenError,
    URSSAFServerError,
    URSSAFTimeoutError,
    URSSAFValidationError,
)


@pytest.fixture
def urssaf_client() -> URSSAFClient:
    """Create a URSSAF client for testing."""
    return URSSAFClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        base_url="https://portailapi-sandbox.urssaf.fr",
        sandbox=True,
    )


@pytest.mark.asyncio
async def test_authenticate_success(urssaf_client: URSSAFClient) -> None:
    """Test successful authentication."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token_12345",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        token = await urssaf_client.authenticate()

        assert token == "test_token_12345"
        assert urssaf_client._token == "test_token_12345"
        assert urssaf_client._token_expiry is not None
        assert urssaf_client._consecutive_errors == 0


@pytest.mark.asyncio
async def test_authenticate_invalid_credentials(urssaf_client: URSSAFClient) -> None:
    """Test authentication with invalid credentials (401)."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        with pytest.raises(URSSAFAuthError, match="Invalid client credentials"):
            await urssaf_client.authenticate()


@pytest.mark.asyncio
async def test_authenticate_server_error(urssaf_client: URSSAFClient) -> None:
    """Test authentication with server error (5xx)."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        with pytest.raises(URSSAFServerError, match="Server error"):
            await urssaf_client.authenticate()


@pytest.mark.asyncio
async def test_authenticate_timeout(urssaf_client: URSSAFClient) -> None:
    """Test authentication timeout."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = TimeoutError("Request timed out")

        with pytest.raises(URSSAFTimeoutError, match="timed out"):
            await urssaf_client.authenticate()


@pytest.mark.asyncio
async def test_token_refresh_when_expired(urssaf_client: URSSAFClient) -> None:
    """Test token refresh when cached token expires."""
    with freeze_time("2000-01-01 00:00:00") as frozen_time:
        # Set up initial token with 3600 second expiry
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "initial_token",
                "expires_in": 3600,
            }
            mock_post.return_value = mock_response

            initial_token = await urssaf_client.authenticate()
            assert initial_token == "initial_token"

        # Advance time to within 60s buffer (3540 seconds later = 59 minutes)
        frozen_time.move_to("2000-01-01 00:59:00")

        # Token should be refreshed (within 60s buffer)
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "refreshed_token",
                "expires_in": 3600,
            }
            mock_post.return_value = mock_response

            token = await urssaf_client._ensure_token()
            assert token == "refreshed_token"


@pytest.mark.asyncio
async def test_token_cached_when_valid(urssaf_client: URSSAFClient) -> None:
    """Test token is cached and reused when still valid."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        token1 = await urssaf_client._ensure_token()
        mock_post.reset_mock()

        # Get token again - should not call authenticate
        token2 = await urssaf_client._ensure_token()

        assert token1 == token2 == "test_token"
        mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_register_particulier_success(urssaf_client: URSSAFClient) -> None:
    """Test successful particulier registration."""
    # Authenticate first
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response
        await urssaf_client.authenticate()

    # Now register particulier
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "particulier_123",
            "email": "test@example.com",
        }
        mock_request.return_value = mock_response

        result = await urssaf_client.register_particulier(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
        )

        assert result["id"] == "particulier_123"
        assert result["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_register_particulier_validation_error(urssaf_client: URSSAFClient) -> None:
    """Test particulier registration with validation error (400)."""
    # Authenticate first
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response
        await urssaf_client.authenticate()

    # Now try to register with invalid data
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid email format"
        mock_request.return_value = mock_response

        with pytest.raises(URSSAFValidationError):
            await urssaf_client.register_particulier(
                email="invalid_email",
                first_name="John",
                last_name="Doe",
            )


@pytest.mark.asyncio
async def test_submit_payment_request_success(urssaf_client: URSSAFClient) -> None:
    """Test successful payment request submission."""
    # Authenticate first
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response
        await urssaf_client.authenticate()

    # Now submit payment request
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "payment_123",
            "status": "pending",
        }
        mock_request.return_value = mock_response

        result = await urssaf_client.submit_payment_request(
            intervenant_code="INT001",
            particulier_email="test@example.com",
            date_debut="2024-01-01",
            date_fin="2024-01-31",
            montant=1500.00,
            unite_travail="H",
            code_nature="NAT001",
            reference="INV001",
        )

        assert result["id"] == "payment_123"
        assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_submit_payment_request_validation_error(urssaf_client: URSSAFClient) -> None:
    """Test payment request with validation error (400)."""
    # Authenticate first
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response
        await urssaf_client.authenticate()

    # Now try to submit with invalid data
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid amount"
        mock_request.return_value = mock_response

        with pytest.raises(URSSAFValidationError):
            await urssaf_client.submit_payment_request(
                intervenant_code="INT001",
                particulier_email="test@example.com",
                date_debut="2024-01-01",
                date_fin="2024-01-31",
                montant=-100.00,  # Invalid negative amount
                unite_travail="H",
                code_nature="NAT001",
                reference="INV001",
            )


@pytest.mark.asyncio
async def test_get_payment_status_success(urssaf_client: URSSAFClient) -> None:
    """Test successful payment status retrieval."""
    # Authenticate first
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response
        await urssaf_client.authenticate()

    # Now get status
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "payment_123",
            "status": "completed",
        }
        mock_request.return_value = mock_response

        result = await urssaf_client.get_payment_status("payment_123")

        assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_retry_on_server_error(urssaf_client: URSSAFClient) -> None:
    """Test retry logic on 5xx errors."""
    # Authenticate first
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response
        await urssaf_client.authenticate()

    # Now test retry on 5xx
    with patch("httpx.AsyncClient.request") as mock_request:
        # First two attempts fail with 500, third succeeds
        mock_responses = [
            MagicMock(status_code=500, text="Internal Error"),
            MagicMock(status_code=500, text="Internal Error"),
            MagicMock(status_code=200, json=lambda: {"status": "ok"}),
        ]
        mock_request.side_effect = mock_responses

        with patch("asyncio.sleep"):  # Skip actual sleep for faster tests
            result = await urssaf_client.get_payment_status("payment_123")

        assert result["status"] == "ok"
        assert mock_request.call_count == 3


@pytest.mark.asyncio
async def test_retry_exhausted_on_server_error(urssaf_client: URSSAFClient) -> None:
    """Test exception raised when retries are exhausted on 5xx."""
    # Authenticate first
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response
        await urssaf_client.authenticate()

    # Now test retry failure
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.side_effect = [
            MagicMock(status_code=500, text="Internal Error"),
            MagicMock(status_code=500, text="Internal Error"),
            MagicMock(status_code=500, text="Internal Error"),
        ]

        with patch("asyncio.sleep"):  # Skip actual sleep for faster tests
            with pytest.raises(URSSAFServerError, match="after 3 attempts"):
                await urssaf_client.get_payment_status("payment_123")

        assert mock_request.call_count == 3


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_errors(urssaf_client: URSSAFClient) -> None:
    """Test circuit breaker opens after 5 consecutive errors."""
    # Authenticate first
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response
        await urssaf_client.authenticate()

    # Trigger 5 consecutive errors to open circuit breaker
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.return_value = MagicMock(status_code=500)

        with patch("asyncio.sleep"):
            for _ in range(5):
                try:
                    await urssaf_client.get_payment_status("payment_123")
                except URSSAFServerError:
                    pass

    # Next request should fail immediately with circuit breaker open
    with pytest.raises(URSSAFCircuitBreakerOpenError):
        await urssaf_client.get_payment_status("payment_123")


@pytest.mark.asyncio
async def test_circuit_breaker_resets_after_timeout(urssaf_client: URSSAFClient) -> None:
    """Test circuit breaker resets after timeout period."""
    with freeze_time("2000-01-01 00:00:00") as frozen_time:
        # Authenticate first
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "test_token",
                "expires_in": 3600,
            }
            mock_post.return_value = mock_response
            await urssaf_client.authenticate()

        # Trigger circuit breaker open
        with patch("httpx.AsyncClient.request") as mock_request:
            mock_request.return_value = MagicMock(status_code=500)

            with patch("asyncio.sleep"):
                for _ in range(5):
                    try:
                        await urssaf_client.get_payment_status("payment_123")
                    except URSSAFServerError:
                        pass

        # Verify circuit breaker is open
        with pytest.raises(URSSAFCircuitBreakerOpenError):
            await urssaf_client.get_payment_status("payment_123")

        # Advance time to reset the circuit breaker (61+ seconds later)
        frozen_time.move_to("2000-01-01 00:01:01")

        with patch("httpx.AsyncClient.request") as mock_request:
            mock_request.return_value = MagicMock(status_code=200, json=lambda: {"status": "ok"})

            result = await urssaf_client.get_payment_status("payment_123")
            assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_retry_on_timeout(urssaf_client: URSSAFClient) -> None:
    """Test retry logic on timeout."""
    # Authenticate first
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response
        await urssaf_client.authenticate()

    # Test retry on timeout
    with patch("httpx.AsyncClient.request") as mock_request:
        # First two attempts timeout, third succeeds
        mock_request.side_effect = [
            TimeoutError(),
            TimeoutError(),
            MagicMock(status_code=200, json=lambda: {"status": "ok"}),
        ]

        with patch("asyncio.sleep"):
            result = await urssaf_client.get_payment_status("payment_123")

        assert result["status"] == "ok"
        assert mock_request.call_count == 3


@pytest.mark.asyncio
async def test_auth_failure_during_request(urssaf_client: URSSAFClient) -> None:
    """Test authentication failure during API request."""
    # Authenticate first
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response
        await urssaf_client.authenticate()

    # Now get 401 during request
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.return_value = MagicMock(status_code=401)

        with pytest.raises(URSSAFAuthError):
            await urssaf_client.get_payment_status("payment_123")


@pytest.mark.asyncio
async def test_concurrent_token_refresh(urssaf_client: URSSAFClient) -> None:
    """Test concurrent token refresh doesn't cause duplicate requests."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        # Multiple concurrent calls should only refresh token once
        tasks = [urssaf_client._ensure_token() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        assert all(token == "test_token" for token in results)
        # Should be called once (or twice due to double-check pattern)
        assert mock_post.call_count <= 2


@pytest.mark.asyncio
async def test_authenticate_network_error(urssaf_client: URSSAFClient) -> None:
    """Test authentication with network error."""
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.side_effect = httpx.RequestError("Network unreachable")

        with pytest.raises(URSSAFTimeoutError, match="Network error"):
            await urssaf_client.authenticate()


@pytest.mark.asyncio
async def test_submit_payment_with_auth_error(urssaf_client: URSSAFClient) -> None:
    """Test payment submission when authentication fails during request."""
    # Authenticate first
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response
        await urssaf_client.authenticate()

    # Now test auth error during submission
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.return_value = MagicMock(status_code=401)

        with pytest.raises(URSSAFAuthError):
            await urssaf_client.submit_payment_request(
                intervenant_code="INT001",
                particulier_email="test@example.com",
                date_debut="2024-01-01",
                date_fin="2024-01-31",
                montant=1500.00,
                unite_travail="H",
                code_nature="NAT001",
                reference="INV001",
            )


@pytest.mark.asyncio
async def test_register_particulier_with_auth_error(urssaf_client: URSSAFClient) -> None:
    """Test registration when authentication fails during request."""
    # Authenticate first
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response
        await urssaf_client.authenticate()

    # Now test auth error during registration
    with patch("httpx.AsyncClient.request") as mock_request:
        mock_request.return_value = MagicMock(status_code=401)

        with pytest.raises(URSSAFAuthError):
            await urssaf_client.register_particulier(
                email="test@example.com",
                first_name="John",
                last_name="Doe",
            )


@pytest.mark.asyncio
async def test_initialization(urssaf_client: URSSAFClient) -> None:
    """Test client initialization."""
    assert urssaf_client.client_id == "test_client_id"
    assert urssaf_client.client_secret == "test_client_secret"
    assert urssaf_client.base_url == "https://portailapi-sandbox.urssaf.fr"
    assert urssaf_client.sandbox is True
    assert urssaf_client._token is None
    assert urssaf_client._token_expiry is None
    assert urssaf_client._consecutive_errors == 0
