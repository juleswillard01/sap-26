# ADR-006: Playwright pour Extraction Indy (vs API officielle)

**Date** : 15 Mars 2026
**Auteur** : Winston (BMAD System Architect)
**Status** : ✅ ACCEPTED
**Référence** : `docs/architecture/architecture.md` (Section 9)

---

## 1. Context

### Situation Actuelle
- Jules utilise **Indy comme banque principale** (app.indy.fr)
- Architecture initiale prévoyait Swan API (GraphQL) pour extraire transactions
- ❌ **Pas d'accès API Swan** : coût prohibitif, limitations accès

### Alternatives Évaluées
1. **Playwright + Headless Browser** (choix) ✅
2. Indy API officielle (non documentée publiquement)
3. Export manuel CSV (aucune automation)
4. Web scraping (RegEx, beautifulsoup4)

### Contraintes Opérationnelles
- Jules ne peut pas payer API Swan
- Indy permet export CSV depuis web UI
- MVP Phase 2 doit avoir reconciliation bancaire
- Besoin automation (pas du manuel à chaque fois)

---

## 2. Decision

### Choix Retenu
**Utiliser Playwright pour automation Indy**

### Justification Économique & Pragmatique

| Critère | Playwright | Swan API | Manual Export |
|---------|-----------|----------|---------------|
| **Coût annuel** | €0 | €€€ | €0 (labor intensive) |
| **Temps setup** | 2-3h | 1h (si accès) | 5min (mais répété) |
| **Automation** | ✅ 100% | ✅ 100% (si accessible) | ❌ 0% |
| **Fiabilité** | 95%+ (depends UI) | 99.9%+ | 100% (manual) |
| **Fallback** | ✅ Manual CSV | None | N/A |
| **Latency** | 4-6s | < 200ms | Manual duration |

### Justification Technique

**Playwright** :
- ✅ Open-source (MIT license)
- ✅ Python SDK (async support)
- ✅ Headless mode (prod-ready)
- ✅ Deterministic (same actions = same results)
- ✅ Screenshot on error (debugging)
- ⚠️ Fragile to UI changes (risk mitigated by fallback)

**Swan API** :
- ❌ Not accessible to Jules (cost/approval)
- ✅ Would be ideal if accessible
- N/A for this decision

**Manual Export** :
- ❌ Labor intensive (repeat weekly/daily)
- ❌ Error prone (human copy-paste)
- ✅ Zero technical risk
- ✅ Fallback option (documented)

---

## 3. Implementation

### Architecture Overview
```
BankReconciliation.reconcile()
  ├─ Path A (Primary) : Playwright Automation
  │  └─ IndyBrowserAdapter.get_transactions()
  │     ├─ Launch Chromium browser
  │     ├─ Login email + password
  │     ├─ Navigate to Transactions page
  │     ├─ Export CSV
  │     └─ Parse → list[Transaction]
  │
  └─ Path B (Fallback) : Manual CSV
     └─ IndyBrowserAdapter.parse_csv_export(csv_path)
        └─ Parse CSV from manual export
```

### Component Design
```python
class IndyBrowserAdapter:
    async def get_transactions(
        self,
        date_from: date,
        date_to: date,
    ) -> list[Transaction]:
        """Primary: Playwright automation"""
        # ... (see docs/implementation/PLAYWRIGHT_INDY_GUIDE.md)

    async def parse_csv_export(
        self,
        csv_path: str,
    ) -> list[Transaction]:
        """Fallback: Manual CSV parse"""
        # ... (see docs/implementation/PLAYWRIGHT_INDY_GUIDE.md)
```

### Configuration
```bash
# .env
INDY_EMAIL=jules@example.com
INDY_PASSWORD=secure_password
INDY_HEADLESS=true  # headless mode (prod)
```

### CLI Usage
```bash
# Normal: Playwright automation
sap reconcile --date-from 2026-02-15 --date-to 2026-03-15

# Fallback: Manual CSV
sap reconcile --csv ~/Downloads/indy_export.csv
```

---

## 4. Consequences

### Positive
✅ **Cost** : €0 (vs €€€ Swan)
✅ **Accessibility** : Works with Jules's real Indy account
✅ **Automation** : 100% coverage, repeatable
✅ **Pragmatic** : Reflects actual constraints Jules faces
✅ **Fallback** : Manual CSV process documented & tested
✅ **Timeline** : Unblocks Phase 2 (no waiting for Swan approval)

### Negative (Risks)
⚠️ **UI Fragility** : If Indy UI changes, selectors break
   - Mitigation: Fallback manual CSV, monthly UI test
⚠️ **Latency** : 4-6s (vs < 200ms Swan)
   - Mitigation: Acceptable for async reconciliation (daily cron)
⚠️ **Session Management** : Browser session can expire
   - Mitigation: Retry with fresh browser, catch auth errors
⚠️ **Process Memory** : Credentials in memory during execution
   - Mitigation: Headless mode, secure cleanup, .env rotation

---

## 5. Risks & Mitigations

### Risk 1: Indy UI Change
| Aspect | Value |
|--------|-------|
| **Probability** | Medium (quarterly updates typical) |
| **Impact** | High (automation breaks) |
| **Severity** | Medium (fallback available) |

**Mitigation Strategy** :
1. **Fallback CSV** : Manual export documented
2. **Monthly Testing** : Automated script to verify selectors
3. **Error Screenshot** : Auto-capture on failure (debug)
4. **Alerting** : Email Jules after 3 consecutive failures
5. **Fix SLA** : 24h to update selectors if detected

### Risk 2: Timeout / Network Issues
| Aspect | Value |
|--------|-------|
| **Probability** | Low (Indy should be stable) |
| **Impact** | Medium (reconciliation delayed) |
| **Severity** | Low (fallback + retry) |

**Mitigation Strategy** :
1. **Timeout** : 30s configurable
2. **Retry Logic** : 3x with exponential backoff (1s, 2s, 4s)
3. **Fallback** : Manual CSV import
4. **Monitoring** : Log all failures with context

### Risk 3: Session Expiration
| Aspect | Value |
|--------|-------|
| **Probability** | Low (fresh browser each run) |
| **Impact** | Medium (reconciliation fails) |
| **Severity** | Low (retry + fallback) |

**Mitigation Strategy** :
1. **Auto-Login** : Credentials from .env each time
2. **Auth Error Catch** : Detect auth failures
3. **Screenshot** : Capture page for debugging
4. **Retry** : Fresh browser instance

### Risk 4: Credentials Leak
| Aspect | Value |
|--------|-------|
| **Probability** | Very Low (but never zero) |
| **Impact** | High (Indy account compromise) |
| **Severity** | High (financial risk) |

**Mitigation Strategy** :
1. **`.env` Protection** : Verified in `.gitignore`
2. **No Logging** : Credentials never logged
3. **Rotation** : Quarterly INDY_EMAIL/PASSWORD change
4. **Isolation** : Process runs in secure context
5. **Cleanup** : Browser session cleared after each run

---

## 6. Alternatives Considered (But Rejected)

### Alternative A: Swan API (If Accessible)
```
Pros:
- ✅ Official, stable, documented
- ✅ Low latency (< 200ms)
- ✅ High reliability (99.9%+)
- ✅ No UI fragility

Cons:
- ❌ Not accessible to Jules (cost)
- ❌ Blocks on approval/payment
- ❌ No fallback to manual process
```
**Decision** : Rejected (not accessible currently)
**Future** : If Swan becomes accessible, switch (create ADR-007)

### Alternative B: Manual CSV Export Only
```
Pros:
- ✅ Zero technical risk
- ✅ No UI dependency
- ✅ Human-in-the-loop safety

Cons:
- ❌ Labor intensive (weekly task)
- ❌ Error prone (human copy-paste)
- ❌ Not truly automated
- ❌ Blocks on Jules's availability
```
**Decision** : Rejected as primary (but kept as fallback)
**Usage** : Emergency/fallback when automation fails

### Alternative C: Web Scraping (RegEx / BeautifulSoup4)
```
Pros:
- ✅ Lower-level than Playwright
- ✅ Lightweight (no browser)
- ✅ Fast response times

Cons:
- ❌ Very fragile to HTML changes
- ❌ No JavaScript execution (Indy uses dynamic rendering)
- ❌ Harder to debug (no screenshot)
- ❌ Maintenance burden (regex hell)
```
**Decision** : Rejected (HTML scraping unmaintainable for Indy)

### Alternative D: Indy API (If It Exists)
```
Pros:
- ✅ If documented, would be ideal
- ✅ Better than Playwright

Cons:
- ❌ Not publicly documented
- ❌ May require approval
- ❌ Unknown cost
- ❌ Unknown timeline
```
**Decision** : Rejected for now (blocked on Indy support response)
**Future** : Research opportunity for Q2 2026

---

## 7. Testing Strategy

### Unit Tests
```python
# CSV parsing with valid/invalid data
# Date format handling (YYYY-MM-DD, DD/MM/YYYY, etc)
# Edge cases: empty CSV, missing columns, malformed rows
```

### Integration Tests
```python
# End-to-end reconciliation with CSV fixture
# Fallback mechanism (CSV path provided)
# Batch write to Sheets
# Lettrage algorithm unchanged
```

### Manual Testing
```bash
# Monthly: Test against real app.indy.fr
# Verify selectors still match UI
# Verify CSV format unchanged
# Verify login still works
# Verify error screenshots captured
```

---

## 8. Rollback Plan

### If Playwright Fails Catastrophically

1. **Immediate** : Switch to manual CSV fallback
   ```bash
   sap reconcile --csv /path/to/indy_export.csv
   ```

2. **Short-term** : Document manual process for Jules
   - Login Indy
   - Export CSV
   - Run CLI with --csv flag

3. **Medium-term** :
   - If UI change detected, fix selectors (24h)
   - If issue persists > 3 days, escalate to Indy support

4. **Long-term** :
   - Evaluate Indy API (if becomes available)
   - Evaluate Swan API (if becomes accessible)
   - Consider alternative banks (if Indy issues persist)

---

## 9. Future Considerations

### Q2 2026: Indy API Research
- [ ] Contact Indy support → ask about API
- [ ] Evaluate cost + approval timeline
- [ ] If available + affordable, plan migration (ADR-007)

### Q3 2026: Swan API Revisit
- [ ] Re-evaluate Swan accessibility
- [ ] If available, plan migration back (ADR-007)
- [ ] Keep Indy Playwright as fallback

### Q4 2026+: Advanced Monitoring
- [ ] ML-based selector validation (detect UI changes early)
- [ ] Automated daily UI testing
- [ ] Pro-active alerts before failures
- [ ] Historical analytics (success rate, latency tracking)

---

## 10. References

### Implementation
- `docs/implementation/PLAYWRIGHT_INDY_GUIDE.md` — Complete implementation guide
- `docs/architecture/architecture.md` — Section 3.4.2 (IndyBrowserAdapter)

### Context
- `docs/DEVIATION_INDY_PLAYWRIGHT.md` — Impact analysis
- `ARCHITECTURE_UPDATE_SUMMARY.md` — Summary for Jules

### Related ADRs
- ADR-001 : Google Sheets backend (unchanged)
- ADR-002 : Polling URSSAF 4h (unchanged)
- ADR-003 : Batch operations + caching (unchanged)
- ADR-004 : Monolith FastAPI (unchanged)
- ADR-005 : Service Account auth (unchanged)

---

## 11. Approval Checklist

- [x] Winston (System Architect) — Accepted ✅
- [ ] Jules (Product Owner) — Review & approval (async)
- [ ] Developer Phase 2 — Implementation planning
- [ ] QA — Testing strategy review

---

## 12. Conclusion

**ADR-006 accepts Playwright for pragmatic, cost-effective automation of Indy transaction extraction**, with robust fallback mechanism and documented mitigation strategies.

This decision unblocks Phase 2 without waiting for Swan API approval or other external dependencies. It reflects Jules's actual constraints and provides a workable solution within MVP scope.

Future ADRs (007+) will be created if API access becomes available, at which point we can re-evaluate prioritization.

---

**Document Version** : 1.0
**Last Updated** : 15 Mars 2026
**Next Review** : Q2 2026 (Indy API availability check)
