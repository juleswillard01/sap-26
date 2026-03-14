# URSSAF OAuth 2.0 Client Implementation

## Overview

The URSSAF client provides a complete OAuth 2.0 implementation for integrating with the URSSAF API. It handles authentication, token management, request retry logic, and circuit breaker patterns to ensure robust and reliable communication with the URSSAF platform.

## Architecture

### Core Components

#### `app/integrations/urssaf_client.py`
Main client class implementing OAuth 2.0 client_credentials flow.

**Key Features:**
- Async client using httpx.AsyncClient
- Token caching with automatic refresh 60 seconds before expiry
- Thread-safe token management with asyncio.Lock
- Exponential backoff retry logic (3 attempts: 1s, 2s, 4s)
- Circuit breaker pattern (opens after 5 consecutive errors, resets after 60s)
- Structured logging for all operations

#### `app/integrations/urssaf_exceptions.py`
Exception hierarchy for proper error handling.

**Exception Types:**
- `URSSAFError` - Base exception
- `URSSAFAuthError` - Authentication failures (401)
- `URSSAFValidationError` - Input validation errors (400)
- `URSSAFServerError` - Server errors (5xx)
- `URSSAFTimeoutError` - Network timeouts
- `URSSAFCircuitBreakerOpenError` - Circuit breaker open

## Configuration

Settings are loaded from environment variables via `app/config.py`:

```python
from app.config import settings

# Required environment variables
# urssaf_api_base: str - API base URL (default: https://portailapi-sandbox.urssaf.fr)
# urssaf_client_id: str - OAuth client ID
# urssaf_client_secret: str - OAuth client secret
```

## Usage

### Basic Setup

```python
from app.integrations.urssaf_client import URSSAFClient
from app.config import settings

# Create client
client = URSSAFClient(
    client_id=settings.urssaf_client_id,
    client_secret=settings.urssaf_client_secret,
    base_url=settings.urssaf_api_base,
    sandbox=True
)

# Token is automatically managed - no need to manually authenticate
```

### Core Operations

#### 1. Register a Particulier (Client)

```python
result = await client.register_particulier(
    email="contact@example.com",
    first_name="Jean",
    last_name="Dupont"
)
# Returns: {"id": "particulier_123", "email": "contact@example.com", ...}
```

#### 2. Submit Payment Request

```python
result = await client.submit_payment_request(
    intervenant_code="INT001",
    particulier_email="contact@example.com",
    date_debut="2024-01-01",
    date_fin="2024-01-31",
    montant=1500.00,
    unite_travail="H",  # Hours
    code_nature="NAT001",
    reference="INV-2024-001"
)
# Returns: {"id": "payment_123", "status": "pending", ...}
```

#### 3. Check Payment Status

```python
result = await client.get_payment_status("payment_123")
# Returns: {"id": "payment_123", "status": "completed", ...}
```

## Advanced Features

### Token Management

Tokens are automatically managed:
- Cached in memory after authentication
- Automatically refreshed when approaching expiry (60s buffer)
- Thread-safe refresh using asyncio.Lock (prevents duplicate auth requests during concurrent calls)

```python
# Get current valid token (auto-refreshes if needed)
token = await client._ensure_token()
```

### Retry Logic

All API calls automatically retry with exponential backoff:
- **Attempts:** 3 total
- **Backoff:** 1s, 2s, 4s between attempts
- **Triggers:** 5xx errors, network timeouts, connection errors

The retry logic is transparent - no special handling needed.

### Circuit Breaker

Protects against cascading failures:
- **Opens after:** 5 consecutive errors
- **Resets after:** 60 seconds of circuit open
- **Behavior:** Raises `URSSAFCircuitBreakerOpenError` when open (fail-fast)
- **Error tracking:** Resets on successful request

```python
# This will raise URSSAFCircuitBreakerOpenError if CB is open
try:
    result = await client.get_payment_status("id")
except URSSAFCircuitBreakerOpenError:
    # Circuit breaker is open - service unavailable
    logger.warning("URSSAF service temporarily unavailable")
```

### Error Handling

```python
from app.integrations.urssaf_exceptions import (
    URSSAFAuthError,
    URSSAFValidationError,
    URSSAFServerError,
    URSSAFTimeoutError,
    URSSAFCircuitBreakerOpenError
)

try:
    result = await client.register_particulier(...)
except URSSAFAuthError:
    # Fix credentials
    logger.error("Invalid URSSAF credentials")
except URSSAFValidationError as e:
    # Fix input data
    logger.error(f"Invalid particulier data: {e}")
except URSSAFServerError:
    # Server error after retries
    logger.error("URSSAF server error after retries")
except URSSAFTimeoutError:
    # Timeout after retries
    logger.error("URSSAF request timeout after retries")
except URSSAFCircuitBreakerOpenError:
    # Too many recent errors
    logger.error("URSSAF circuit breaker is open")
```

## Logging

All operations are logged with structured logging:

```python
# Authentication
logger.info("Authenticating with URSSAF", extra={"url": url})
logger.info("Authentication successful", extra={"expires_in": 3600})

# API calls
logger.info("Registering particulier", extra={"email": email})
logger.info("Payment request submitted", extra={"reference": reference})

# Errors and retries
logger.warning("Server error, will retry", extra={"status": 500, "attempt": 1})
logger.error("Circuit breaker opened after consecutive errors")

# Token management
logger.info("Token expired or missing, refreshing")
logger.debug("Using cached token")
```

Log extra context includes:
- Request URLs and methods
- Response status codes
- Error details
- Retry attempts and backoff timing
- Circuit breaker state

## Testing

### Test Coverage
- **22 test cases** covering:
  - Authentication success and failures
  - Token caching and refresh
  - All API operations
  - Validation errors
  - Retry logic
  - Circuit breaker behavior
  - Concurrent operations
  - Timeout handling
  - Authorization failures

### Running Tests

```bash
# Run all tests
pytest tests/unit/test_urssaf_client.py -v

# Run with coverage
pytest tests/unit/test_urssaf_client.py --cov=app.integrations.urssaf_client --cov-report=html

# Run specific test
pytest tests/unit/test_urssaf_client.py::test_authenticate_success -v
```

### Test Structure

Tests use:
- **pytest-asyncio** for async test support
- **freezegun** for time-based token expiry testing
- **unittest.mock** for HTTP mocking (no real network calls)
- **pytest fixtures** for test isolation

Example test:

```python
@pytest.mark.asyncio
async def test_retry_on_server_error(urssaf_client: URSSAFClient) -> None:
    """Test retry logic on 5xx errors."""
    # Setup mock responses for retry scenarios
    with patch("httpx.AsyncClient.request") as mock_request:
        # First two attempts fail with 500, third succeeds
        mock_responses = [
            MagicMock(status_code=500),
            MagicMock(status_code=500),
            MagicMock(status_code=200, json=lambda: {"status": "ok"}),
        ]
        mock_request.side_effect = mock_responses

        result = await urssaf_client.get_payment_status("id")
        assert result["status"] == "ok"
        assert mock_request.call_count == 3
```

## Type Safety

Full type hints with strict mypy compliance:

```python
# All functions fully type-annotated
async def authenticate(self) -> str: ...
async def register_particulier(
    self,
    email: str,
    first_name: str,
    last_name: str,
) -> dict[str, Any]: ...

# Run type checking
mypy app/integrations/urssaf_client.py --strict
```

## Performance Considerations

1. **Token Caching:** Reduces authentication calls significantly
2. **Concurrent Token Refresh:** Double-check locking prevents duplicate auth during concurrent access
3. **Timeout:** 30-second default prevents hung requests
4. **Circuit Breaker:** Prevents cascading failures during outages
5. **Logging:** Structured logging with minimal overhead

## Deployment

### Environment Variables

```bash
# Production
URSSAF_API_BASE=https://api.urssaf.fr
URSSAF_CLIENT_ID=<your-client-id>
URSSAF_CLIENT_SECRET=<your-client-secret>

# Sandbox (for testing)
URSSAF_API_BASE=https://portailapi-sandbox.urssaf.fr
URSSAF_CLIENT_ID=<sandbox-client-id>
URSSAF_CLIENT_SECRET=<sandbox-client-secret>
```

### Configuration in app/config.py

```python
class Settings(BaseSettings):
    urssaf_api_base: str = Field(default="https://portailapi-sandbox.urssaf.fr")
    urssaf_client_id: str = Field(default="")
    urssaf_client_secret: str = Field(default="")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def is_sandbox(self) -> bool:
        return "sandbox" in self.urssaf_api_base
```

## Troubleshooting

### Circuit Breaker Open
**Symptom:** `URSSAFCircuitBreakerOpenError` after making requests

**Causes:**
- URSSAF service is down
- Network connectivity issues
- Invalid credentials (causing 401 errors)

**Resolution:**
- Wait 60 seconds for automatic reset
- Check URSSAF service status
- Verify credentials
- Check network connectivity

### Token Refresh Issues
**Symptom:** `URSSAFAuthError` during normal operations

**Causes:**
- Invalid client credentials
- Client credentials have been revoked
- Token refresh endpoint changed

**Resolution:**
- Verify `URSSAF_CLIENT_ID` and `URSSAF_CLIENT_SECRET` in environment
- Check with URSSAF that credentials are valid
- Review URSSAF API changelog for endpoint changes

### Timeout Errors
**Symptom:** `URSSAFTimeoutError` after retries

**Causes:**
- URSSAF service is slow
- Network latency is high
- Large request payloads

**Resolution:**
- Wait and retry (automatic retry already handles this)
- Check URSSAF service status
- Review request payload sizes
- Monitor network latency

## Integration Examples

### In a Service Class

```python
from app.integrations.urssaf_client import URSSAFClient
from app.config import settings

class PaymentService:
    def __init__(self):
        self.urssaf = URSSAFClient(
            client_id=settings.urssaf_client_id,
            client_secret=settings.urssaf_client_secret,
            base_url=settings.urssaf_api_base,
            sandbox=not settings.is_production
        )

    async def submit_invoice(self, invoice: Invoice) -> str:
        """Submit invoice to URSSAF."""
        result = await self.urssaf.submit_payment_request(
            intervenant_code=invoice.client.intervenant_code,
            particulier_email=invoice.client.email,
            date_debut=invoice.date_debut.isoformat(),
            date_fin=invoice.date_fin.isoformat(),
            montant=invoice.total_amount,
            unite_travail="H",
            code_nature="NAT001",
            reference=invoice.reference
        )
        return result["id"]
```

### In a FastAPI Route

```python
from fastapi import APIRouter, Depends
from app.integrations.urssaf_client import URSSAFClient
from app.config import settings

router = APIRouter(prefix="/api/v1/invoices", tags=["invoices"])

async def get_urssaf_client() -> URSSAFClient:
    return URSSAFClient(
        client_id=settings.urssaf_client_id,
        client_secret=settings.urssaf_client_secret,
        base_url=settings.urssaf_api_base
    )

@router.post("/submit")
async def submit_invoice(
    invoice_id: str,
    urssaf: URSSAFClient = Depends(get_urssaf_client)
):
    try:
        result = await urssaf.submit_payment_request(...)
        return {"status": "success", "request_id": result["id"]}
    except URSSAFValidationError as e:
        return {"status": "error", "message": str(e)}, 400
    except URSSAFCircuitBreakerOpenError:
        return {"status": "unavailable"}, 503
```

## Future Enhancements

1. **Metrics Collection:** Add Prometheus metrics for request counts, latencies, errors
2. **Request Caching:** Cache frequently-accessed GET requests
3. **Batch Operations:** Support batch submission of multiple payment requests
4. **Webhook Support:** Handle URSSAF webhooks for payment status updates
5. **Rate Limiting:** Client-side rate limiting to respect URSSAF API quotas
6. **Request Signing:** Support request signing if URSSAF adds that requirement

## References

- URSSAF API Documentation: https://portailapi-sandbox.urssaf.fr/docs
- OAuth 2.0 Client Credentials: https://tools.ietf.org/html/rfc6749#section-4.4
- httpx Documentation: https://www.python-httpx.org/
- Circuit Breaker Pattern: https://martinfowler.com/bliki/CircuitBreaker.html
