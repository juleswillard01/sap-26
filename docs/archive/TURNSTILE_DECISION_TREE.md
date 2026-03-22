# Cloudflare Turnstile Bypass Decision Tree

**Quick Reference**: Which approach to use for automating Indy login?

---

## Decision Flow

```
┌─ Is headless automation REQUIRED?
│  │
│  ├─ NO (can run headed mode)
│  │  └─ Use Approach 2: Session Persistence
│  │     - Interactive login every 30-90 days
│  │     - Simple, proven, already implemented
│  │     - Cost: ~5 min human intervention quarterly
│  │
│  └─ YES (fully autonomous needed)
│     │
│     ├─ Is OAuth discovery cost acceptable?
│     │  │
│     │  ├─ YES (2-3 hours one-time)
│     │  │  └─ Use Approach 1: Google OAuth Bypass (RECOMMENDED)
│     │  │     - Fully autonomous
│     │  │     - No Turnstile interaction
│     │  │     - Discovery: 2-3 hours (one-time)
│     │  │     - Long-term: Zero manual intervention
│     │  │     - Most robust solution
│     │  │
│     │  └─ NO (can't invest discovery time)
│     │     └─ Fallback to Session Persistence
│     │        with periodic headed refreshes
│
└─ Summary: Your choice depends on cost/benefit
   - Quarterly 5-min manual login (Approach 2) vs
   - One-time 2-3hr discovery + full automation (Approach 1)
```

---

## Quick Lookup Table

| Scenario | Approach | Effort | Maintenance | Recommendation |
|----------|----------|--------|-------------|-----------------|
| **Scheduled job, OK with quarterly refresh** | Session Persistence (2) | Low | 5 min/90 days | ✓ Use This |
| **Scheduled job, needs 100% autonomy** | Google OAuth (1) | Medium | Zero | ✓ Use This |
| **Need multiple retry strategies** | OAuth (1) + Fallback (2) | High | Very low | ✓ Best |
| **Quick one-off exports** | Headed mode manual | Very Low | Per-run | For testing only |
| **Long-term production pipeline** | OAuth (1) + monitoring | Medium | Minimal | ✓ Use This |

---

## Your Situation (Jules)

**Current Setup**:
- SAP-Facture is a **scheduled job** (cron-based)
- Jules' Google account has **NO 2FA** (makes OAuth simpler)
- Indy requires **headless automation** (can't wait for human interaction)
- Current solution: **Session Persistence** (works, but needs 30-90 day refresh)

**Recommendation**: **Use Approach 1 (Google OAuth) as PRIMARY**
- Discovery phase: ~2-3 hours (run NetworkLogger, extract client_id)
- Implementation: ~2 hours (use provided code in `examples/indy_oauth_automation.py`)
- Long-term: Zero maintenance once set up

**Fallback**: Keep Approach 2 (Session Persistence) as backup
- If OAuth fails → fall back to session refresh
- Adds resilience without extra effort

---

## Implementation Roadmap

### Phase 1: Investigation (2-3 hours)

```bash
# Step 1: Run NetworkLogger to discover OAuth URL
python examples/network_logger_example.py --mode indy_oauth

# Step 2: Extract INDY_OAUTH_CLIENT_ID from network log
cat io/research/indy_oauth/api-endpoints.md
# Find the Google OAuth URL with client_id parameter

# Step 3: Document findings
# Update .env with:
#   INDY_OAUTH_CLIENT_ID=your_client_id
#   GOOGLE_EMAIL=jules@example.com
#   GOOGLE_PASSWORD=(already set)
```

### Phase 2: Implementation (2 hours)

```bash
# Step 1: Copy example to adapter
cp examples/indy_oauth_automation.py src/adapters/indy_oauth_adapter.py

# Step 2: Integrate into IndyBrowserAdapter
# Add method: login_via_google_oauth()
# Add fallback logic in connect()

# Step 3: Test with real credentials
uv run pytest tests/integration/test_indy_oauth_real.py -v
```

### Phase 3: Integration (1-2 hours)

```bash
# Step 1: Update IndyBrowserAdapter.connect()
# - Try OAuth first
# - Fall back to session persistence if needed

# Step 2: Update CLI commands
# - sap reconcile --auth oauth
# - sap reconcile --auth session (fallback)

# Step 3: Add monitoring
# - Log OAuth success/failure
# - Alert on repeated failures
```

### Phase 4: Monitoring (Ongoing)

```bash
# Watch for:
# - OAuth client_id changes (Indy updates auth config)
# - Google OAuth URL changes (rare, but possible)
# - Session state expiration (keep fallback ready)

# Set alerts for:
# - export_journal_csv() failures (try OAuth refresh)
# - Repeated 401/403 errors (session expired)
```

---

## Cost-Benefit Analysis

### Approach 2: Session Persistence (Current)

**Pros**:
- ✅ Already implemented
- ✅ Proven working
- ✅ No discovery needed

**Cons**:
- ❌ Cookies expire every 30-90 days
- ❌ Requires periodic manual login (headed mode)
- ❌ Not fully autonomous

**Total Effort**:
- Setup: 0 hours (already done)
- Maintenance: 5 min × 4/year = 20 min/year
- Annual cost: ~20 minutes human time

---

### Approach 1: Google OAuth (Recommended)

**Pros**:
- ✅ Fully autonomous (no manual intervention)
- ✅ No Turnstile (Google page is bot-friendly)
- ✅ No session expiration (OAuth tokens managed by Indy)
- ✅ More reliable long-term

**Cons**:
- ❌ Requires discovery phase (2-3 hours)
- ❌ Depends on Indy's OAuth config stability
- ❌ Google could change OAuth flow (rare)

**Total Effort**:
- Setup: 3 hours (discovery + implementation)
- Maintenance: 0 hours (fully autonomous)
- Annual cost: ~3 hours (one-time)

---

### Hybrid: OAuth + Session Fallback (Best Practice)

**Pros**:
- ✅ 100% autonomous (OAuth primary)
- ✅ Graceful degradation (session fallback)
- ✅ Handles edge cases (OAuth failures, client_id changes)
- ✅ Most robust for production

**Cons**:
- ❌ More code to maintain
- ❌ More testing needed

**Total Effort**:
- Setup: 4-5 hours (discovery + OAuth + fallback logic)
- Maintenance: Minimal (monitoring only)
- Annual cost: ~4-5 hours (one-time)

---

## Decision: Go With Approach 1 (OAuth)

**Justification**:
1. **Jules' time is valuable** — 20 min/year (session) vs 4-5 hours (OAuth) is only justified if you want zero future intervention
2. **Pipeline reliability** — Scheduled jobs need autonomy; manual refresh is a failure point
3. **Low risk** — Google OAuth is industry-standard; if it breaks, you have session fallback
4. **One-time cost** — Discovery is ~3 hours; you do it once and forget it

**Action Items**:
- [ ] Run NetworkLogger for OAuth discovery (Phase 1)
- [ ] Implement `login_via_google_oauth()` (Phase 2)
- [ ] Add OAuth to IndyBrowserAdapter.connect() with session fallback (Phase 3)
- [ ] Test with real Indy account (Phase 4)
- [ ] Deploy and monitor (Phase 5)

---

## Code Template (Phase 2 Implementation)

Update `src/adapters/indy_adapter.py`:

```python
class IndyBrowserAdapter:
    # Add to __init__
    OAUTH_MODE = "oauth"
    SESSION_MODE = "session"

    def connect(self, auth_mode: str = "auto") -> None:
        """Connect to Indy with auto-failover strategy.

        Args:
            auth_mode: "auto" (try OAuth, fall back to session),
                      "oauth" (OAuth only),
                      "session" (session only)
        """
        if auth_mode == "auto":
            try:
                self._login_via_google_oauth()
                logger.info("Connected via Google OAuth")
            except Exception as e:
                logger.warning(f"OAuth failed: {e}, falling back to session persistence")
                try:
                    self._login_via_session_persistence()
                except Exception as e2:
                    logger.error(f"Session persistence also failed: {e2}")
                    raise
        elif auth_mode == "oauth":
            self._login_via_google_oauth()
        elif auth_mode == "session":
            self._login_via_session_persistence()
        else:
            raise ValueError(f"Invalid auth_mode: {auth_mode}")

    def _login_via_google_oauth(self) -> None:
        """Login via Google OAuth (no Turnstile)."""
        # Implement using examples/indy_oauth_automation.py
        pass

    def _login_via_session_persistence(self) -> None:
        """Login via saved session state (existing code)."""
        # Already implemented
        pass
```

---

## Testing Checklist

### Unit Tests (Mock)

- [ ] OAuth URL construction is correct
- [ ] Auth code extraction from callback works
- [ ] Session token extraction from cookies works
- [ ] Error handling for missing auth code
- [ ] Fallback logic triggers on OAuth failure

### Integration Tests (Real, need .env)

- [ ] Google OAuth login succeeds
- [ ] Session state saved to file
- [ ] Headless login with saved state works
- [ ] Dashboard access confirmed
- [ ] Session expiration handling

### Manual Testing

- [ ] Run with `--headed` to watch flow
- [ ] Verify no Turnstile appears
- [ ] Check session state file is created
- [ ] Verify headless mode reuses session

---

## Security Checklist

Before deploying to production:

- [ ] Google credentials in `.env`, never hardcoded
- [ ] Auth codes never logged (redact in debug)
- [ ] Session state file ignored in `.gitignore`
- [ ] HTTPS validation enabled
- [ ] Callback URL origin check (must be `app.indy.fr`)
- [ ] State token validation (CSRF protection)
- [ ] Token expiration handled gracefully
- [ ] Error messages don't expose sensitive data

---

## FAQ

**Q: Will Google OAuth always work?**
A: Google's OAuth is industry-standard and very stable. Worst case, you fall back to session persistence.

**Q: Can Indy block OAuth logins?**
A: Possible but unlikely. If they do, you'd see redirect loops. Fall back to session would still work.

**Q: Does Jules' lack of 2FA on Google make it less secure?**
A: For this automation, it's actually better — no OTP extraction needed. Security depends on `.env` file being private (it should be).

**Q: How long is the OAuth client_id discovery phase?**
A: 2-3 hours: 30 min to run NetworkLogger, 30 min to analyze output, 1-2 hours to implement and test.

**Q: Can I use this for other portals?**
A: Yes! Any portal with Google OAuth (no Turnstile on Google's page) can use this pattern.

**Q: What if Indy changes their OAuth client_id?**
A: It's unlikely (they'd break existing integrations). If it happens, you'd need to re-discover and update `.env`. Fallback to session would still work.

---

## References

- `docs/OAUTH_TURNSTILE_RESEARCH.md` — Deep technical analysis
- `examples/indy_oauth_automation.py` — Production-ready implementation
- `docs/NETWORK_LOGGER.md` — How to discover OAuth URL

---

## Next Step

**Choose your approach and commit to a timeline:**

- **Go with Approach 1 (OAuth)**: Schedule 4-5 hours this week to implement
- **Stick with Approach 2 (Session)**: Set calendar reminder for quarterly refresh
- **Try Approach 3 (Hybrid)**: Implement OAuth now, add session fallback later

Once decided, file an issue or create a task to track progress.

