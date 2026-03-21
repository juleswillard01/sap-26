# Gmail IMAP — Documentation Index

Research date: 2026-03-21
Task: Enable custom Gmail label access (e.g., "Indy-2FA") in GmailReader class

---

## Documents (In Reading Order)

### 1. **GMAIL_SETUP_QUICK_START.md** (5 min read)
**For Jules**: Step-by-step setup guide

- 6-step checklist (2FA → App Password → Labels → Filter)
- Test command to verify
- Common issues + fixes
- Security notes

**Start here if you**: Need to set up Gmail for GmailReader

---

### 2. **GMAIL_IMAP_RESEARCH.md** (20 min read)
**For everyone**: Complete technical reference

Sections:
1. Executive summary (table of findings)
2. Gmail IMAP label syntax (custom vs. system)
3. Authentication: App Password (mandatory 2026)
4. Authentication timeline (2022-2026)
5. Python implementation (full working code)
6. Gmail filter setup (web UI steps)
7. Error handling & troubleshooting
8. Security best practices
9. Testing templates
10. Checklist for Jules

**Start here if you**: Want full context on Gmail IMAP + authentication

---

### 3. **GMAIL_IMAP_IMPLEMENTATION_GUIDE.md** (15 min read)
**For developers**: Code changes + testing

Sections:
1. Current state vs. target
2. Changes required (5 code sections)
3. Usage examples (3 scenarios)
4. Testing strategy (unit + integration tests)
5. Breaking changes (NONE — backward compatible)
6. Deployment checklist
7. Code review checklist
8. Next steps

**Start here if you**: Need to implement the code changes

---

## Quick Reference

### Gmail Label Syntax in Python

```python
# Custom label (user-created)
imap.select("Indy-2FA")

# System label (created by Gmail)
imap.select("[Gmail]/All Mail")
imap.select("[Gmail]/Drafts")
imap.select("[Gmail]/Spam")
```

### Authentication (2026 Requirement)

| What | Status |
|------|--------|
| Regular password | ✗ BLOCKED |
| App Password | ✓ REQUIRED |
| OAuth 2.0 | ✓ ALTERNATIVE |

### GmailReader Enhancement

**Current**: Hardcoded `self._connection.select("INBOX")`

**Target**: `reader.get_latest_2fa_code(label="Indy-2FA", timeout_sec=60)`

**Changes**: Add `label` parameter + new `_select_label()` method

**Breaking**: None (backward compatible, default `label="INBOX"`)

---

## Decision Matrix

### Should I use App Password or OAuth 2.0?

| Criteria | App Password | OAuth 2.0 |
|----------|--------------|-----------|
| Setup time | 5 min | 30 min |
| Complexity | Simple | Complex |
| Requires 2FA | Yes | No |
| Future-proof | Good | Better |
| For MVP | ✓ YES | — |
| For production | ✓ OK | ✓ BETTER |

**Recommendation**: Use App Password for MVP. Switch to OAuth 2.0 in production if needed.

---

## Implementation Workflow

```
1. Jules reads GMAIL_SETUP_QUICK_START.md
            ↓
2. Jules enables 2FA + generates App Password
            ↓
3. Jules creates label + filter in Gmail
            ↓
4. Jules stores credentials in .env
            ↓
5. Developer reads GMAIL_IMAP_IMPLEMENTATION_GUIDE.md
            ↓
6. Developer applies code changes to GmailReader
            ↓
7. Developer adds unit tests (templates provided)
            ↓
8. Manual integration test with real Indy email
            ↓
9. Deploy & monitor
```

---

## Key Takeaways

✓ **Custom labels work directly**: `imap.select("Indy-2FA")` works
✓ **App Password mandatory**: Regular password blocked as of March 2025
✓ **2FA required for App Password**: Minor inconvenience, 5-minute setup
✓ **Backward compatible**: Existing INBOX code still works
✓ **Low risk**: Error handling + tested approach
✓ **Security best practice**: App Password is safer than account password

---

## Common Questions

**Q: Do I have to enable 2FA?**
A: Yes, to use App Password. But you can choose SMS or authenticator app.

**Q: Is App Password safe?**
A: Yes. It only works for IMAP/SMTP (not Gmail web). You can revoke anytime.

**Q: Will my code break?**
A: No. The `label` parameter defaults to `"INBOX"`, so existing code works.

**Q: What if regular password still works for me?**
A: It shouldn't (Google blocked it March 2025), but if it does, switch to App Password soon.

**Q: Can I use OAuth instead?**
A: Yes, but it's more complex. App Password is simpler for MVP.

**Q: How do I test the changes?**
A: Unit tests provided. For integration, send a test email from Indy and verify GmailReader extracts the code.

---

## File Locations

| File | Purpose |
|------|---------|
| `/home/jules/Documents/3-git/SAP/PAYABLES/docs/GMAIL_SETUP_QUICK_START.md` | Setup for Jules |
| `/home/jules/Documents/3-git/SAP/PAYABLES/docs/GMAIL_IMAP_RESEARCH.md` | Full reference |
| `/home/jules/Documents/3-git/SAP/PAYABLES/GMAIL_IMAP_IMPLEMENTATION_GUIDE.md` | Code changes |
| `/home/jules/Documents/3-git/SAP/PAYABLES/src/adapters/gmail_reader.py` | Current code |
| `/home/jules/Documents/3-git/SAP/PAYABLES/tests/test_gmail_reader.py` | Existing tests |
| `/home/jules/Documents/3-git/SAP/PAYABLES/.env` | Secrets (never commit) |

---

## Next Steps

**Immediate (Today)**:
1. Read GMAIL_SETUP_QUICK_START.md
2. Enable 2FA on Gmail
3. Generate App Password
4. Store in .env

**This week**:
1. Read GMAIL_IMAP_IMPLEMENTATION_GUIDE.md
2. Apply code changes
3. Add unit tests
4. Manual integration test

**Before merge**:
1. All tests pass (unit + integration)
2. Code review checklist complete
3. Backward compatibility verified
4. Deployment checklist signed off

---

## References

- [Gmail IMAP Extensions — Google Developers](https://developers.google.com/workspace/gmail/imap/imap-extensions)
- [App Passwords — Google Account Help](https://support.google.com/accounts/answer/185833)
- [Less Secure Apps Deprecation — Google Workspace](https://workspaceupdates.googleblog.com/2023/09/winding-down-google-sync-and-less-secure-apps-support.html)
- [Python imaplib — Official Docs](https://docs.python.org/3/library/imaplib.html)
- [OAuth IMAP Reference — GitHub](https://github.com/aler9/howto-gmail-imap-oauth2)

---

**Questions?** Refer to the appropriate document above.
