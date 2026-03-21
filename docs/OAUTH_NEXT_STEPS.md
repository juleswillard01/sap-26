# Next Steps: From Research to Implementation

**Status**: Research complete, ready for Phase 2
**Timeline**: 4-5 hours total setup
**Effort**: 2-3 hours discovery + 2 hours implementation + 1-2 hours testing

---

## Your Action Items (In Order)

### ✅ COMPLETED: Research & Documentation
- [x] Deep technical analysis (OAUTH_TURNSTILE_RESEARCH.md)
- [x] Production-ready code (examples/indy_oauth_automation.py)
- [x] Decision framework (TURNSTILE_DECISION_TREE.md)
- [x] Navigation guide (OAUTH_RESEARCH_INDEX.md)

### ⏳ NEXT: Phase 1 — Investigation (Estimate: 2-3 hours)

**Step 1: Understand the OAuth URL (30 min)**
1. Read section "Discovery: Finding Indy's OAuth Client ID" in OAUTH_TURNSTILE_RESEARCH.md
2. Understand what NetworkLogger does (docs/NETWORK_LOGGER.md)
3. Confirm you have Playwright installed and working

**Step 2: Run NetworkLogger Discovery (30-60 min)**
1. Execute:
   ```bash
   cd /home/jules/Documents/3-git/SAP/PAYABLES
   python examples/network_logger_example.py --mode indy_oauth
   ```

2. Or manually using the provided template in OAUTH_TURNSTILE_RESEARCH.md:
   ```bash
   # Navigate to https://app.indy.fr/login in headed mode
   # Click "Connexion avec Google" button
   # Capture network request to accounts.google.com
   ```

3. Expected output:
   - Network log: `io/research/indy_oauth/network-*.jsonl`
   - Summary: `io/research/indy_oauth/api-endpoints.md`

**Step 3: Extract OAuth Parameters (15-30 min)**
1. Open the generated `api-endpoints.md`
2. Find the entry for `accounts.google.com/o/oauth2/v2/auth`
3. Extract parameters:
   - `client_id` → Store as `INDY_OAUTH_CLIENT_ID`
   - `redirect_uri` → Should be `https://app.indy.fr/oauth/callback`
   - `scope` → Should be `email profile` or similar

**Step 4: Update Configuration (10 min)**
1. Edit `.env` and add:
   ```
   INDY_OAUTH_CLIENT_ID=<extracted_client_id>
   GOOGLE_EMAIL=<your_email>
   GOOGLE_PASSWORD=<your_password>
   ```

2. Verify credentials are correct:
   ```bash
   grep -E "INDY_OAUTH_CLIENT_ID|GOOGLE_" .env
   ```

---

### 📋 THEN: Phase 2 — Implementation (Estimate: 2-3 hours)

**Step 5: Integrate OAuth Adapter (60-90 min)**

1. Create new file `src/adapters/indy_oauth_adapter.py`:
   ```bash
   cp examples/indy_oauth_automation.py src/adapters/indy_oauth_adapter.py
   ```

2. Review the code and understand:
   - `IndyGoogleOAuthAutomation` class
   - `login_via_oauth()` method
   - Session state persistence

3. Update `src/adapters/indy_adapter.py` to add OAuth login:
   ```python
   # Add to IndyBrowserAdapter class

   def login_via_google_oauth(self) -> None:
       """Login via Google OAuth (no Turnstile)."""
       from src.adapters.indy_oauth_adapter import IndyGoogleOAuthAutomation

       oauth = IndyGoogleOAuthAutomation(
           client_id=self._settings.indy_oauth_client_id,
           google_email=self._settings.google_email,
           google_password=self._settings.google_password,
           headless=True
       )
       result = oauth.login_via_oauth(save_session=True)

       if not result["success"]:
           raise RuntimeError(f"OAuth login failed: {result}")

       logger.info(f"OAuth login successful for {result['email']}")

   def connect(self, session_mode: str = "auto") -> None:
       """Connect with auto-failover: try OAuth, fall back to session."""
       if session_mode == "auto":
           try:
               self.login_via_google_oauth()
           except Exception as e:
               logger.warning(f"OAuth login failed, falling back: {e}")
               # Fall back to existing session persistence logic
               self._verify_session()
       # ... rest of existing code
   ```

4. Update `src/config.py` to add OAuth settings:
   ```python
   class Settings(BaseSettings):
       # ... existing settings ...

       # Indy OAuth
       indy_oauth_client_id: str = ""
       google_email: str = ""
       google_password: str = ""
   ```

5. Run ruff/pyright to verify no linting errors:
   ```bash
   uv run ruff check src/adapters/indy_*.py --fix
   uv run pyright --strict src/adapters/indy_*.py
   ```

**Step 6: Update Tests (30-60 min)**

1. Create `tests/integration/test_indy_oauth_real.py`:
   ```python
   import pytest
   from src.adapters.indy_adapter import IndyBrowserAdapter
   from src.config import Settings

   @pytest.mark.integration
   def test_indy_oauth_login_real(settings: Settings) -> None:
       """Real OAuth login to Indy (requires credentials)."""
       adapter = IndyBrowserAdapter(settings)
       adapter.connect(session_mode="auto")  # Try OAuth, fall back if needed

       # Verify we're on dashboard
       assert adapter._page
       assert "dashboard" in adapter._page.url
       assert (Path("io/cache/indy_oauth_session.json").exists() or
               Path("io/cache/indy_browser_state.json").exists())

   @pytest.mark.integration
   def test_indy_export_journal_after_oauth(settings: Settings) -> None:
       """Export journal transactions after OAuth login."""
       adapter = IndyBrowserAdapter(settings)
       adapter.connect(session_mode="auto")

       transactions = adapter.export_journal_book()
       assert isinstance(transactions, list)
       # Further assertions on transaction structure
   ```

2. Run integration tests:
   ```bash
   uv run pytest tests/integration/test_indy_oauth_real.py -v
   ```

---

### 🧪 THEN: Phase 3 — Testing (Estimate: 1-2 hours)

**Step 7: Test OAuth Discovery (30 min)**

1. Run the OAuth discovery phase:
   ```bash
   python examples/indy_oauth_automation.py --discover
   ```

2. Follow the prompts:
   - Browser opens with Indy login page
   - Click "Connexion avec Google" button manually
   - Script detects redirect and captures OAuth URL
   - Verify client_id matches your .env value

**Step 8: Test OAuth Login in Headed Mode (30 min)**

1. Run OAuth login with visible browser:
   ```bash
   python examples/indy_oauth_automation.py --login --headed
   ```

2. Expected flow:
   - Browser opens (headed mode, visible)
   - Redirects to Google OAuth (no Turnstile!)
   - Fills email and password automatically
   - Gets redirected back to Indy dashboard
   - Session state saved to `io/cache/indy_oauth_session.json`

3. Verify success:
   ```bash
   ls -lh io/cache/indy_oauth_session.json
   # Should exist and have recent timestamp
   ```

**Step 9: Test Headless Mode (30 min)**

1. Run export with headless mode (reusing saved session):
   ```bash
   python examples/indy_oauth_automation.py --export-transactions
   ```

2. Expected behavior:
   - Launches browser in headless mode (invisible)
   - Loads saved OAuth session from file
   - Does NOT visit login page (NO Turnstile!)
   - Successfully navigates to dashboard
   - Exports transactions

3. Verify success:
   ```bash
   # Check logs for success message
   # Should see: "Successfully connected with saved session (headless)"
   ```

---

### 🚀 FINALLY: Phase 4 — Deployment (Estimate: 1 hour)

**Step 10: Update CLI Commands (30 min)**

1. Update `src/cli.py` to use OAuth by default:
   ```python
   @click.command()
   @click.option(
       "--auth-mode",
       type=click.Choice(["auto", "oauth", "session"]),
       default="auto",
       help="Authentication method: auto (try OAuth, fall back), oauth (OAuth only), session (session only)"
   )
   def reconcile(auth_mode: str) -> None:
       """Reconcile bank transactions (export from Indy, match with invoices)."""
       adapter = IndyBrowserAdapter(settings)
       adapter.connect(session_mode=auth_mode)
       # ... rest of reconciliation logic
   ```

2. Update help text in CLI:
   ```bash
   sap reconcile --help
   # Should show: "--auth-mode [auto|oauth|session]"
   ```

**Step 11: Add Monitoring & Alerting (20 min)**

1. Add error notifications for failed OAuth:
   ```python
   def connect(self, session_mode: str = "auto") -> None:
       try:
           self.login_via_google_oauth()
       except Exception as e:
           logger.error("OAuth login failed", exc_info=True)
           # Send email alert to Jules
           send_error_notification(f"Indy OAuth login failed: {e}")
           # Fall back to session
   ```

2. Log OAuth success for monitoring:
   ```python
   logger.info(
       "OAuth login successful",
       extra={
           "method": "google_oauth",
           "email": self._settings.google_email,
           "session_saved": True,
       }
   )
   ```

**Step 12: First Cron Run & Monitoring (10 min)**

1. Monitor the first automated run:
   ```bash
   # Check logs for the cron job
   grep "OAuth login successful" logs/*.log
   # Should see success message with timestamp
   ```

2. Verify no manual intervention needed:
   - Should run completely headless
   - Should NOT prompt for login
   - Should complete successfully

---

## Decision Checkpoint

**Before starting Phase 2, confirm:**

- [ ] Read OAUTH_RESEARCH_INDEX.md (overview, 15 min)
- [ ] Read TURNSTILE_DECISION_TREE.md (decision, 15 min)
- [ ] Understand why Google OAuth bypass works
- [ ] Confirmed Jules' Google account has NO 2FA
- [ ] Have network access to run headless browser
- [ ] Have .env file configured with Google credentials

**If all checked**: Proceed to Phase 1 (Investigation)
**If uncertain**: Re-read OAUTH_RESEARCH_INDEX.md or TURNSTILE_DECISION_TREE.md

---

## Estimated Timeline

| Phase | Task | Hours | Dependencies |
|-------|------|-------|--------------|
| 1 | Investigation | 2-3 | None |
| 2 | Implementation | 2-3 | Phase 1 ✓ |
| 3 | Testing | 1-2 | Phase 2 ✓ |
| 4 | Deployment | 1 | Phase 3 ✓ |
| **TOTAL** | **Complete OAuth Setup** | **4-5 hrs** | One-time effort |

After this, annual maintenance is:
- Monitoring: ~5 minutes/month (watch for errors)
- No manual logins needed (fully autonomous)

---

## Success Criteria

After completing all phases, you should have:

- ✅ `login_via_google_oauth()` method in IndyBrowserAdapter
- ✅ OAuth session saved to `io/cache/indy_oauth_session.json`
- ✅ Headless `export_journal_csv()` works without Turnstile
- ✅ Session fallback configured for resilience
- ✅ Cron job `sap reconcile` succeeds autonomously
- ✅ Zero manual login interventions
- ✅ Monitoring alerts configured for failures
- ✅ Full test coverage (unit + integration)

---

## Troubleshooting Common Issues

### OAuth client_id not found in network log
**Cause**: NetworkLogger didn't capture Google redirect
**Solution**: Run in headed mode, click button manually, wait for redirect to appear

### Google "Account recovery" screen appears
**Cause**: Google detects unusual login (headless patterns)
**Solution**: Use Jules' real Indy account with saved Google cookie

### "Session expired" on headless run
**Cause**: OAuth session token expired (rare, usually >7 days)
**Solution**: Implement refresh logic to auto-login again

### Turnstile still appears
**Cause**: Not using Google OAuth (still on Indy login page)
**Solution**: Verify you're navigating to `accounts.google.com`, not `app.indy.fr/login`

---

## Questions?

Refer to the research documents:

| Question | Document |
|----------|----------|
| "How does this work?" | OAUTH_TURNSTILE_RESEARCH.md |
| "Which approach should I use?" | TURNSTILE_DECISION_TREE.md |
| "What's the code?" | examples/indy_oauth_automation.py |
| "Where do I start?" | OAUTH_RESEARCH_INDEX.md |
| "How do I navigate?" | This file (OAUTH_NEXT_STEPS.md) |

---

## Ready to Begin?

**YES → Start with Phase 1 (Investigation)**
```bash
cd /home/jules/Documents/3-git/SAP/PAYABLES
# Read the overview first
cat docs/OAUTH_RESEARCH_INDEX.md

# Then start investigation
python examples/network_logger_example.py --mode indy_oauth
```

**UNSURE → Read the Research**
```bash
# Understanding the approach
cat docs/OAUTH_TURNSTILE_RESEARCH.md | less

# Or get a quick decision tree
cat docs/TURNSTILE_DECISION_TREE.md | less
```

---

**Timeline to Complete**: 4-5 hours (one-time investment)
**ROI**: Zero manual logins for 1-2+ years
**Status**: Ready to proceed 🚀

