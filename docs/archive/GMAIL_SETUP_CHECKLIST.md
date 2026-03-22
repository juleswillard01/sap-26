# Gmail OAuth2 Setup — Quick Checklist

**Use this checklist while following `docs/GMAIL_SETUP_GUIDE.md`**

---

## Part 1: Google Cloud Console (5 min)

- [ ] Go to https://console.cloud.google.com
- [ ] Sign in with your Google account
- [ ] Select your existing project (used for Sheets API)
- [ ] Enable Gmail API
  - [ ] APIs & Services → Library
  - [ ] Search "Gmail API"
  - [ ] Click ENABLE
- [ ] Create OAuth2 credentials
  - [ ] APIs & Services → Credentials
  - [ ] Configure consent screen (if needed):
    - [ ] User Type: External
    - [ ] App name: "SAP-Facture"
    - [ ] User support email: jules.willard.pro@gmail.com
    - [ ] Developer contact: jules.willard.pro@gmail.com
    - [ ] Save screens (use defaults)
  - [ ] + CREATE CREDENTIALS → OAuth client ID
    - [ ] Application type: Desktop app
    - [ ] Name: "SAP-Facture Gmail"
    - [ ] Create
    - [ ] Download JSON → Save as **`credentials/gmail_oauth.json`**
    - [ ] Click OK
- [ ] Add test user
  - [ ] APIs & Services → OAuth consent screen
  - [ ] Test users → + ADD USERS
  - [ ] Email: jules.willard.pro@gmail.com
  - [ ] Add

---

## Part 2: Gmail Settings (2 min)

- [ ] Go to https://mail.google.com
- [ ] Sign in if needed
- [ ] Create label "Indy-2FA"
  - [ ] Settings (gear icon) → See all settings
  - [ ] Labels tab
  - [ ] Create new label: "Indy-2FA"
  - [ ] Create
- [ ] Create email filter
  - [ ] Settings → See all settings
  - [ ] Filters and Blocked Addresses tab
  - [ ] Create a new filter
  - [ ] From: noreply@indy.fr
  - [ ] Create filter
  - [ ] Check "Apply the label"
  - [ ] Select "Indy-2FA"
  - [ ] Create filter

---

## Part 3: First-Time OAuth Consent (1 min)

- [ ] Terminal:
  ```bash
  cd /home/jules/Documents/3-git/SAP/PAYABLES
  uv run python tools/gmail_auth.py
  ```
- [ ] Browser opens automatically
- [ ] Click blue "Allow" button
- [ ] Terminal shows: "SUCCESS! Connected to Gmail..."
- [ ] Check file created:
  ```bash
  ls -lh credentials/gmail_token.json
  ```

---

## Part 4: Verify Setup (1 min)

- [ ] Test 1 — Connection:
  ```bash
  uv run python -c "
  from src.adapters.gmail_reader import GmailReader
  reader = GmailReader()
  reader.connect()
  print('✓ Gmail connected!', reader.count_unread(), 'unread')
  reader.close()
  "
  ```
  Expected: `✓ Gmail connected! X unread`

- [ ] Test 2 — 2FA emails:
  ```bash
  uv run python -c "
  from src.adapters.gmail_reader import GmailReader
  reader = GmailReader()
  reader.connect()
  emails = reader.find_2fa_emails(max_results=3)
  print(f'✓ Found {len(emails)} 2FA emails')
  reader.close()
  "
  ```
  Expected: `✓ Found X 2FA emails`

---

## Part 5: Update .env (1 min)

- [ ] Open or create `.env`:
  ```bash
  touch .env
  ```
- [ ] Add these lines:
  ```env
  # Gmail OAuth2
  GMAIL_OAUTH_CLIENT_FILE=credentials/gmail_oauth.json
  GMAIL_OAUTH_TOKEN_FILE=credentials/gmail_token.json
  ```
- [ ] Verify files exist:
  ```bash
  ls -lh credentials/gmail*.json
  ```

---

## Security Verification

- [ ] Check `.gitignore` contains `credentials/`:
  ```bash
  grep "credentials/" .gitignore
  ```
  Expected: `credentials/`

- [ ] Verify credentials NOT in git:
  ```bash
  git status credentials/ 2>&1 | grep "nothing to commit"
  ```
  Expected: "nothing to commit" (files not tracked)

- [ ] Review token file permissions:
  ```bash
  stat credentials/gmail_token.json | grep Access
  ```
  Expected: `-rw-r--r--` (readable by you only)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `gmail_oauth.json` not found | Download from Google Cloud Console → Credentials → OAuth 2.0 Client IDs |
| Gmail API not enabled | Google Cloud Console → Library → Search "Gmail" → Enable |
| No browser window opens | Check firewall, or manually go to `http://localhost:8888` |
| "Token expired" error | Delete `credentials/gmail_token.json` and re-run `tools/gmail_auth.py` |
| No 2FA emails found | Check label created correctly, or search Gmail: `from:noreply@indy.fr` |

---

## Files Created

✓ `/home/jules/Documents/3-git/SAP/PAYABLES/docs/GMAIL_SETUP_GUIDE.md` — Full guide (11 KB)
✓ `/home/jules/Documents/3-git/SAP/PAYABLES/tools/gmail_auth.py` — Auth script (5.3 KB)
✓ `/home/jules/Documents/3-git/SAP/PAYABLES/docs/GMAIL_SETUP_CHECKLIST.md` — This checklist

---

**Total time**: ~10 minutes
**Estimated complexity**: Low (mostly clicking, 2 terminal commands)
**Support contact**: See GMAIL_SETUP_GUIDE.md for troubleshooting

**Created**: 2026-03-21
