# Indy API Interceptor — Network Reverse Engineering

## Purpose

`intercept_indy_api.py` captures all XHR/fetch API calls made by the Indy web application. This allows us to reverse-engineer the Indy REST API without needing official documentation.

This is analogous to how we discovered the AIS API by inspecting network traffic—Indy has no public API, so we extract endpoints by observing the web app's behavior.

## Background

- **Indy** (app.indy.fr) is a banking/accounting app with no public API
- **SAP-Facture** needs to export transaction data from Indy
- **Solution**: Playwright/nodriver headless automation + network interception = extract API calls → reverse-engineer endpoints

## How It Works

1. **Login** to Indy (via credentials in `.env.mcp`)
2. **Navigate** through key pages (Dashboard, Transactions, Documents, Comptabilité, Bank)
3. **Capture** all network requests:
   - Method (GET, POST, PUT, DELETE)
   - URL and query parameters
   - Request/response headers (with auth tokens masked)
   - Request body (for POST/PUT)
   - Response status and content-type
4. **Filter** out static assets (JS, CSS, images) and tracking domains
5. **Export** results:
   - `api-endpoints.md` — human-readable summary
   - `api-raw.json` — full request/response data for analysis
   - Screenshots — visual evidence of each page visited

## Prerequisites

```bash
# Ensure dependencies installed
uv sync

# Create or verify .env.mcp with credentials
cat .env.mcp
# Should contain:
# INDY_EMAIL=your.email@example.com
# INDY_PASSWORD=your.password
```

## Usage

```bash
# Run the interceptor
python tools/intercept_indy_api.py

# Or with logging
PYTHONUNBUFFERED=1 python tools/intercept_indy_api.py

# Monitor output
tail -f io/research/indy/api-raw.json
```

### What Happens

1. Browser opens Indy login page (headed mode — you'll see it)
2. Auto-fills email/password
3. Submits login form
4. If 2FA enabled: **you must enter the code manually** (code sent to your email)
5. Once logged in, navigates through:
   - `/app/` — Dashboard
   - `/app/transactions` — Transaction list
   - `/app/documents` — Documents
   - `/app/comptabilite` — Accounting
   - `/app/bank` — Bank accounts
6. Captures all API calls during navigation
7. Browser stays open 30 seconds for manual exploration
8. Exports results automatically

**Total time**: ~3-5 minutes (depending on 2FA entry speed)

## Output Files

### `io/research/indy/api-endpoints.md`

Human-readable markdown summary:

```
# Indy API Endpoints — Reverse Engineering

Generated: 2026-03-21T14:30:45.123456

Total requests: 157
Static/tracking filtered: 89
API calls captured: 68

## API Endpoints Summary

| Method | URL | Status | Content-Type |
|---|---|---|---|
| GET | https://api.indy.fr/api/v1/dashboard | 200 | application/json |
| POST | https://api.indy.fr/api/v1/auth/refresh | 200 | application/json |
...

## Detailed Calls (68 total)

### Call 1: GET https://api.indy.fr/api/v1/dashboard
- **Status**: 200 OK
- **Content-Type**: application/json
- **Timestamp**: 2026-03-21T14:30:50.123
...
```

### `io/research/indy/api-raw.json`

Full request/response data (100+ lines per call):

```json
[
  {
    "url": "https://api.indy.fr/api/v1/dashboard",
    "method": "GET",
    "headers": {
      "Authorization": "Bearer eyJ...***",
      "Content-Type": "application/json",
      "X-Request-ID": "abc123"
    },
    "post_data": "",
    "type": "FETCH",
    "timestamp": "2026-03-21T14:30:50.123",
    "status": 200,
    "status_text": "OK",
    "content_type": "application/json"
  },
  ...
]
```

### Screenshots

- `01-login-page.png` — Indy login form
- `02-filled.png` — After filling credentials
- `03-after-login.png` — Post-login state
- `04-dashboard.png` — Dashboard page
- `05-transactions.png` — Transactions page
- `06-documents.png` — Documents page
- `07-comptabilite.png` — Accounting page
- `08-bank.png` — Bank accounts page

## Data Security

### What's Captured ✓

- API endpoint URLs (paths, not query params with IDs)
- HTTP methods and status codes
- Content-types and headers (non-auth)
- General structure of responses

### What's Masked ✗

- Authorization tokens (replaced with `***` or truncated)
- Cookie values
- API keys and secrets
- Personal/financial data (not captured, only headers logged)
- Session IDs

## Analysis — Next Steps

Once you have `api-raw.json`, analyze it to:

1. **Identify endpoints**:
   ```bash
   jq '.[].url | split("?")[0]' io/research/indy/api-raw.json | sort -u
   ```

2. **Group by method**:
   ```bash
   jq 'group_by(.method) | .[] | {method: .[0].method, count: length}' io/research/indy/api-raw.json
   ```

3. **Find transaction endpoints**:
   ```bash
   jq '.[] | select(.url | contains("transaction")) | .url' io/research/indy/api-raw.json
   ```

4. **Extract response structure** (sample):
   ```bash
   jq '.[0]' io/research/indy/api-raw.json | less
   ```

## Integration with SAP-Facture

Once API endpoints are identified, we'll implement:

1. **InodyAdapter** — async HTTP client for discovered endpoints
2. **Transaction fetcher** — GET `/api/v1/transactions` with pagination
3. **CSV export workaround** — if Indy doesn't expose transaction export, we'll use Playwright to click the export button and parse CSV

## Troubleshooting

### "INDY_EMAIL and INDY_PASSWORD required"
→ Create `.env.mcp` with credentials (see `.env.example`)

### "Browser opens but login fails"
→ Check if Indy changed their login UI. Update CSS selectors in code.

### "2FA code not entered in time"
→ Script waits 120 seconds. Enter code in the browser window when prompted.

### "No API calls captured"
→ Check if Indy blocks headless browsers. Try:
   - `headless=False` (current) — headed mode, should work
   - Disable Cloudflare Turnstile detection (nodriver handles this)
   - Clear cookies: `rm io/research/indy/cookies.json`

### "Screenshots are blank"
→ Timing issue. Increase `await page.sleep()` delays in code.

## Limitations

- **No actual HTTP client yet** — we're capturing URLs/methods, not implementing them
- **No authentication handling** — tokens are masked, must extract from Indy session
- **No pagination detection** — may need manual analysis of "next page" APIs
- **No webhook support** — Indy webhooks (if any) not captured

## References

- [Nodriver Documentation](https://github.com/ultrafunkamsterdam/nodriver)
- [CDP Network Domain](https://chromedevtools.github.io/devtools-protocol/tot/Network/)
- SAP-Facture CDC: `docs/CDC.md` §3.1 (Import Transactions)
- Existing AIS exploration: `tools/explore_ais.py` (pattern reference)

## Code Quality

- ✓ Type hints on all function signatures
- ✓ Ruff lint: all checks pass
- ✓ Docstrings for public methods
- ✓ Structured logging (no print)
- ✓ Error handling with graceful fallbacks
- ✓ GDPR-compliant (tokens masked, no PII captured)

## Author Notes

This script is **exploratory**, not part of production SAP-Facture. Its sole purpose is API discovery. Once we have the endpoints, we'll implement a proper `InodyAdapter` with tests and integration into the main codebase.

Expected time to extract and analyze: 5-10 minutes per run.
Expected time to implement adapter: 2-4 hours (with tests).

---

**Last updated**: 2026-03-21
**Status**: Ready for use
