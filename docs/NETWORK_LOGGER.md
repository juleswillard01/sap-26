# NetworkLogger — Reverse API Engineering Utility

**Purpose**: Intercept and analyze HTTP network traffic during Playwright automation to discover internal API endpoints, data models, and authentication mechanisms.

**Status**: Development tool (exploration phase only). Not for production.

**Location**: `/src/adapters/network_logger.py`

---

## Quick Start

```python
from pathlib import Path
from src.adapters import NetworkLogger
from playwright.async_api import async_playwright

# Initialize logger
net_logger = NetworkLogger(output_dir=Path("io/research/ais"))

# Attach to Playwright page
async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    net_logger.attach(page)

    # Navigate and interact with portal
    await page.goto("https://app.avance-immediate.fr")
    await page.fill("input[name='email']", "user@example.com")
    await page.click("button[type='submit']")
    # ... more interactions ...

    # Export results
    log_file = net_logger.export()
    endpoints = net_logger.get_api_endpoints()
    print(f"Discovered {len(endpoints)} API endpoints")
    print(f"Log written to {log_file}")

await browser.close()
```

---

## Features

### 1. Request Interception
- Captures all HTTP requests (method, URL, headers, body)
- Logs timestamps for correlation
- Filters out static assets (CSS, JS, images)

### 2. Response Capture
- Captures HTTP status codes and response headers
- Extracts JSON response bodies for analysis
- Limited to 5KB per response for performance

### 3. API Endpoint Discovery
- Deduplicates by `{METHOD} {BASE_URL}`
- Tracks request count per endpoint
- Captures query parameters separately
- Records first-seen timestamp

### 4. RGPD-Compliant Masking
- **Entirely masks**: Authorization, Cookie, Set-Cookie headers
- **Regex masking**: Bearer tokens, passwords, API keys in other headers
- No sensitive data logged to disk

### 5. Export Formats

#### JSONL Log File (`network-YYYYMMDD-HHMMSS.jsonl`)
Raw request/response entries, one JSON object per line.

```json
{"timestamp": "2026-03-21T10:15:30.123456+00:00", "url": "https://api.example.com/api/v1/users", "method": "GET", "resource_type": "xhr", "headers": {"content-type": "application/json"}, "status": 200}
```

#### Markdown Summary (`api-endpoints.md`)
Table of discovered endpoints for quick review.

```markdown
| Method | URL | Calls | First Seen | Params |
|--------|-----|-------|------------|--------|
| GET | `https://api.example.com/api/v1/users` | 5 | 2026-03-21T10:15 | `page=1&limit=10` |
| POST | `https://api.example.com/api/v1/invoices` | 2 | 2026-03-21T10:16 | (none) |
```

---

## API Reference

### `NetworkLogger(output_dir: Path)`
Initialize logger with output directory.

```python
logger = NetworkLogger(output_dir=Path("io/research/ais"))
```

**Args**:
- `output_dir`: Directory where JSONL and Markdown files are written. Created if missing.

---

### `attach(page: Any) -> None`
Attach event listeners to a Playwright page.

```python
net_logger.attach(page)
```

**Args**:
- `page`: Playwright Page object.

**Note**: Must be called before navigation; removes listeners on page close.

---

### `export() -> Path`
Export captured data to files.

```python
log_file = net_logger.export()
```

**Returns**: Path to created JSONL log file.

**Creates**:
1. `network-YYYYMMDD-HHMMSS.jsonl` — Raw request/response log
2. `api-endpoints.md` — Discovered endpoints summary

**Example**:
```
io/research/ais/network-20260321-101530.jsonl
io/research/ais/api-endpoints.md
```

---

### `get_api_endpoints() -> dict[str, dict[str, Any]]`
Get discovered API endpoints.

```python
endpoints = net_logger.get_api_endpoints()
for key, info in endpoints.items():
    print(f"{key}: {info['count']} calls, first seen {info['first_seen']}")
```

**Returns**: Dict mapping `"{METHOD} {URL}"` to endpoint info dict.

**Example**:
```python
{
    "GET https://api.example.com/api/v1/users": {
        "method": "GET",
        "url": "https://api.example.com/api/v1/users",
        "params": "page=1&limit=10",
        "count": 5,
        "first_seen": "2026-03-21T10:15:30.123456+00:00"
    }
}
```

---

## Use Cases

### 1. Discover AIS API Endpoints
Understand how the AIS portal communicates internally for facturation workflows.

```python
# Navigate AIS and observe all API calls
net_logger = NetworkLogger(output_dir=Path("io/research/ais"))
net_logger.attach(page)

await page.goto("https://app.avance-immediate.fr")
# ... interact with invoice creation flow ...

net_logger.export()
# Review io/research/ais/api-endpoints.md for discovered endpoints
```

### 2. Reverse-Engineer Indy Banking API
Map out the Indy Banking transaction export workflow.

```python
net_logger = NetworkLogger(output_dir=Path("io/research/indy"))
net_logger.attach(page)

await page.goto("https://app.indy.fr")
# ... export transactions ...

endpoints = net_logger.get_api_endpoints()
for key, info in endpoints.items():
    if "transaction" in key.lower():
        print(f"Found transaction endpoint: {key}")
```

### 3. Debug Authentication Issues
Trace the login flow to understand OAuth2 or token management.

```python
net_logger = NetworkLogger(output_dir=Path("io/research/auth"))
net_logger.attach(page)

await page.goto("https://app.example.com/login")
await page.fill("input[name='email']", "user@example.com")
await page.click("button[type='submit']")

# Examine network log to find auth endpoints and token flows
```

---

## Implementation Details

### Request Filtering
Static assets (CSS, JS, images, fonts) are **not** logged to reduce noise:
- Matched by resource type: stylesheet, image, font, media
- Matched by extension: .css, .js, .png, .jpg, .svg, .woff

API calls are identified as:
- URLs containing `/api/` or `graphql`
- Resource types `xhr` or `fetch`

### Header Masking Strategy
1. **Sensitive headers** (Authorization, Cookie, Set-Cookie) → Entirely masked
2. **Other headers** → Regex patterns mask Bearer tokens, passwords, API keys

Example masking:
```
Before: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
After: Authorization: ***MASKED***
```

### Performance Optimizations
- Request body limited to 2KB
- Response body limited to 5KB
- Deduplication by base URL (query params tracked separately)
- No persistence of full payloads, only summaries

---

## RGPD Compliance

### Data Protection
- **No user credentials** logged (headers masked)
- **No tokens/API keys** in cleartext (regex masking)
- **No cookies** persisted (header masking)
- **No PII** in URLs (unless in data model — review before sharing logs)

### Recommendations
1. Run discovery on **internal/test accounts only**
2. **Sanitize logs** before sharing (remove sensitive URLs if needed)
3. **Delete logs** after analysis (not for long-term storage)
4. **Audit timestamps** to correlate with actual user actions

---

## Troubleshooting

### No API endpoints discovered
- Verify `attach()` was called before navigation
- Check if portal uses static HTML (no dynamic API calls)
- Increase wait times if portal loads slowly
- Inspect browser console for JavaScript errors

### Headers not properly masked
- All header values are logged (even if masked)
- Review exported JSONL to confirm no plaintext tokens
- Adjust `_mask_sensitive()` if new header types added

### Export files not created
- Verify output directory exists or is writable
- Check filesystem permissions
- Ensure `export()` called before script ends

### Performance degradation
- Playwright event handlers are synchronous
- For high-traffic scenarios, increase body size limits
- Use `get_api_endpoints()` for in-memory queries (faster)

---

## Testing

Unit tests for NetworkLogger cover:
- Initialization and directory creation
- Request/response interception
- Sensitive header masking
- API endpoint deduplication
- File export (JSONL + Markdown)
- Integration workflows

**Run tests**:
```bash
uv run pytest tests/test_network_logger.py -v
```

**Coverage**:
```bash
uv run pytest tests/test_network_logger.py --cov=src/adapters/network_logger
```

---

## Limitations

1. **Playwright-only**: Designed for browser automation, not raw HTTP tools
2. **No request body modification**: Logger is read-only
3. **No response interception**: Cannot modify responses
4. **Synchronous handlers**: May impact performance on high-traffic sites
5. **Memory-resident**: Keeps all data in memory until export

---

## Related Documentation

- `docs/SCHEMAS.html` — Overall SAP-Facture architecture
- `docs/CDC.md` — Business requirements
- `.claude/rules/urssaf-api.md` — AIS/URSSAF integration details
- `src/adapters/ais_adapter.py` — AIS Playwright scraping implementation

---

## Examples

See `/examples/network_logger_example.py` for:
- AIS discovery setup
- Indy discovery setup
- Basic attachment workflow

---

## Future Enhancements

- [ ] Support request/response filtering by URL regex
- [ ] Automatic GraphQL schema extraction
- [ ] HAR (HTTP Archive) export format
- [ ] Real-time dashboard for monitoring
- [ ] Performance profiling by endpoint
- [ ] Automated test generation from captured flows
