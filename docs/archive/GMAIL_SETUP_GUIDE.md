# Gmail OAuth2 Setup Guide for SAP-Facture

**Objective**: Enable SAP-Facture to read 2FA emails from Gmail (specifically from `noreply@indy.fr`) to automate bank transaction verification.

**Estimated time**: ~10 minutes total
**Requirements**:
- Google Cloud project (already created for Sheets API)
- Gmail account: `jules.willard.pro@gmail.com`
- Browser with login access to Google Cloud Console and Gmail

---

## Overview

SAP-Facture needs to:
1. **Read 2FA emails** from Indy Banking (noreply@indy.fr) to extract verification codes
2. **Auto-inject 2FA** into Playwright Indy login flow
3. **Scale Indy scraping** without manual code entry each time

This guide walks you through:
- **Part 1**: Google Cloud setup (5 min) — enable Gmail API, create OAuth2 credentials
- **Part 2**: Gmail label + filter (2 min) — organize Indy 2FA emails
- **Part 3**: First-time OAuth consent (1 min) — browser click to authorize
- **Part 4**: Verify setup works (1 min)
- **Part 5**: Update .env variables (1 min)

---

## Part 1: Google Cloud Console Setup (5 minutes)

### 1.1 Navigate to Google Cloud Console

1. Go to **https://console.cloud.google.com**
2. **Sign in** with your Google account (if not already logged in)

### 1.2 Select Your Existing Project

1. At the top of the page, click the **project selector dropdown** (shows your current project name)
2. Look for the project used for **Sheets API** — it likely contains "sheets" or "sap" in the name
   - **If unsure**: check what's in your current `credentials/` folder (if it exists)
   - Look for any files like `sheets_credentials.json` or `google_credentials.json`
3. **Click** on the project to select it

### 1.3 Enable Gmail API

1. In the left sidebar, click **"APIs & Services"** → **"Library"**
2. In the search box at the top, type **"Gmail"**
3. Click on **"Gmail API"** from the results
4. Click the blue **"ENABLE"** button
   - This may take 10-30 seconds
   - You'll see a confirmation page once enabled

### 1.4 Create OAuth2 Credentials

#### Step A: Check if OAuth consent screen is configured

1. In the left sidebar, click **"APIs & Services"** → **"Credentials"**
2. Look for a section called **"OAuth 2.0 Client IDs"**
3. If there's a message saying "You need to create an OAuth consent screen first":
   - Click the blue **"Configure Consent Screen"** button
   - **User Type**: Select **"External"** (not Internal)
   - Click **"CREATE"**

#### Step B: Configure consent screen (if needed)

1. **App name**: Type **"SAP-Facture"**
2. **User support email**: Type **"jules.willard.pro@gmail.com"**
3. Scroll down to **"Developer contact information"**
4. **Email addresses**: Type **"jules.willard.pro@gmail.com"**
5. Click the blue **"SAVE AND CONTINUE"** button at the bottom
6. On the next page ("Scopes"), just click **"SAVE AND CONTINUE"** again (leave default)
7. On "Test users" page, click **"SAVE AND CONTINUE"** (we'll add test user next)
8. Click **"BACK TO DASHBOARD"** button

#### Step C: Create OAuth Client ID

1. In the left sidebar, click **"APIs & Services"** → **"Credentials"**
2. Click the blue **"+ CREATE CREDENTIALS"** button near the top
3. Select **"OAuth client ID"** from the dropdown
4. A form appears:
   - **Application type**: Select **"Desktop app"** from the dropdown
   - **Name**: Type **"SAP-Facture Gmail"**
5. Click the blue **"CREATE"** button
6. A dialog box appears with your credentials — **IMPORTANT**: click **"DOWNLOAD"** button
   - Save the JSON file as: **`credentials/gmail_oauth.json`**
   - Create the `credentials/` folder if it doesn't exist
7. Click **"OK"** to close the dialog

### 1.5 Add Test User

1. In the left sidebar, click **"APIs & Services"** → **"OAuth consent screen"**
2. Scroll down to the **"Test users"** section
3. Click the blue **"+ ADD USERS"** button
4. Type your email: **`jules.willard.pro@gmail.com`**
5. Click the blue **"ADD"** button
6. You should see your email listed as a test user

**✓ Part 1 complete!**

---

## Part 2: Gmail Label + Filter Setup (2 minutes)

This step organizes incoming 2FA emails from Indy Banking into a dedicated label for easy access.

### 2.1 Create Gmail Label

1. Go to **https://mail.google.com**
2. Sign in with **`jules.willard.pro@gmail.com`** if needed
3. Click the **settings gear icon** (⚙️) in the top right
4. Select **"See all settings"** from the dropdown
5. Click the **"Labels"** tab at the top
6. Scroll to the bottom of the "Labels" section
7. Click **"Create new label"**
8. Type the label name: **`Indy-2FA`**
9. **Parent label**: Leave blank (none)
10. Click the blue **"Create"** button
11. Close the settings tab (or navigate back to inbox)

### 2.2 Create Email Filter

1. Go back to **https://mail.google.com**
2. Click the **settings gear icon** (⚙️) in the top right
3. Select **"See all settings"** from the dropdown
4. Click the **"Filters and Blocked Addresses"** tab
5. Scroll to the bottom and click **"Create a new filter"**
6. In the form that appears:
   - **From** field: Type **`noreply@indy.fr`**
   - Leave all other fields blank
7. Click the blue **"Create filter"** button
8. A dialog appears with actions:
   - Check the box **"Apply the label"**
   - From the dropdown, select **`Indy-2FA`**
   - **ALSO check** "Apply the label" and select `Indy-2FA` again to apply to existing matching emails
9. Click the blue **"Create filter"** button
10. You should see the filter listed in the "Filters and Blocked Addresses" tab

**✓ Part 2 complete!**

---

## Part 3: First-Time OAuth Consent (1 minute)

After you've completed Parts 1-2, the code is ready to request access. The first time you run the auth script, you'll authorize SAP-Facture to read your Gmail.

### 3.1 Run the Auth Script

Open your terminal and navigate to the SAP-Facture project folder:

```bash
cd /home/jules/Documents/3-git/SAP/PAYABLES
uv run python tools/gmail_auth.py
```

### 3.2 Browser Consent

1. Your **default browser opens automatically**
2. You see the Google login page (may be pre-filled with your account)
3. A page appears saying:
   ```
   SAP-Facture wants access to your Google Account
   ```
4. Click the blue **"Allow"** button to grant permission
5. You see a success message: "The authentication flow has completed successfully."
6. The browser closes automatically, and the terminal shows:
   ```
   Token saved to credentials/gmail_token.json
   SUCCESS! Connected to Gmail. Found X recent emails.
     - From: ... | Subject: ...
   ```

**⚠️ IMPORTANT**: The token file (`credentials/gmail_token.json`) is **sensitive** — it allows reading Gmail. It's listed in `.gitignore` and should NEVER be committed.

**✓ Part 3 complete!**

---

## Part 4: Verify Setup Works (1 minute)

Test that Gmail integration is working end-to-end:

```bash
cd /home/jules/Documents/3-git/SAP/PAYABLES

# Test 1: List recent 2FA emails
uv run python -c "
from src.adapters.gmail_reader import GmailReader
reader = GmailReader()
reader.connect()
count = reader.count_unread()
print(f'✓ Gmail connected! Unread emails: {count}')
reader.close()
"

# Test 2: List emails from Indy label
uv run python -c "
from src.adapters.gmail_reader import GmailReader
reader = GmailReader()
reader.connect()
emails = reader.find_2fa_emails(max_results=3)
print(f'✓ Found {len(emails)} recent 2FA emails from Indy')
for email in emails:
    print(f'  - {email[\"from\"]} | {email[\"subject\"][:60]}...')
reader.close()
"
```

If both commands print `✓`, your Gmail setup is working!

**✓ Part 4 complete!**

---

## Part 5: Update .env Variables (1 minute)

Add Gmail credentials paths to your `.env` file:

### 5.1 Open or Create `.env`

If `.env` doesn't exist, create it in the project root:

```bash
touch /home/jules/Documents/3-git/SAP/PAYABLES/.env
```

### 5.2 Add Gmail Variables

Add these lines to `.env`:

```env
# Gmail OAuth2
GMAIL_OAUTH_CLIENT_FILE=credentials/gmail_oauth.json
GMAIL_OAUTH_TOKEN_FILE=credentials/gmail_token.json
```

### 5.3 Verify

Check that both files exist:

```bash
ls -lh /home/jules/Documents/3-git/SAP/PAYABLES/credentials/gmail*.json
```

Expected output:
```
-rw-r--r-- 1 jules julius 1234 Mar 21 12:00 credentials/gmail_oauth.json
-rw-r--r-- 1 jules julius 5678 Mar 21 12:05 credentials/gmail_token.json
```

**✓ Part 5 complete!**

---

## Security Checklist

- ✅ **`credentials/gmail_oauth.json`** — OAuth client secret, listed in `.gitignore` ✓
- ✅ **`credentials/gmail_token.json`** — Refresh token, listed in `.gitignore` ✓
- ✅ **Never commit** these files to Git
- ✅ **Never paste** the contents into Slack, emails, or documents
- ✅ **Rotate credentials** if accidentally exposed (revoke in Google Cloud Console)

---

## Troubleshooting

### "gmail_oauth.json not found"

**Solution**:
1. Check `credentials/` folder exists: `ls -d credentials/`
2. Re-download OAuth client from Google Cloud Console:
   - APIs & Services → Credentials → OAuth 2.0 Client IDs → SAP-Facture Gmail → Download JSON
3. Save as `credentials/gmail_oauth.json`

### "Gmail API not enabled"

**Solution**:
1. Go to Google Cloud Console → APIs & Services → Library
2. Search for "Gmail API"
3. Click "ENABLE" (should show "Disable" if already enabled)

### "The authentication flow has completed, but no token saved"

**Solution**:
1. Ensure `credentials/` folder exists and is writable:
   ```bash
   mkdir -p credentials/
   chmod 755 credentials/
   ```
2. Re-run: `uv run python tools/gmail_auth.py`

### "Token expired" error in production

**Solution**:
- Tokens auto-refresh using the refresh token
- If refresh fails, delete `credentials/gmail_token.json` and re-run auth:
  ```bash
  rm credentials/gmail_token.json
  uv run python tools/gmail_auth.py
  ```

### "No recent emails found"

**Possibilities**:
1. Indy hasn't sent 2FA email yet
2. Email went to spam/promotions folder
3. Check Gmail label setup in Part 2.2
4. Search Gmail for "from:noreply@indy.fr" to verify emails exist

---

## Next Steps

Once Gmail is set up:

1. **Implement 2FA injection** in `src/adapters/indy_adapter.py`:
   - Read 2FA code from Gmail
   - Auto-fill in Indy login form
   - Remove manual 2FA entry

2. **Run Indy scraper** without interactive prompts:
   ```bash
   uv run python -m src.cli reconcile --auto-2fa
   ```

3. **Schedule cron job** to sync every 4 hours:
   ```bash
   # Via APScheduler in src/services/scheduler.py
   sap sync --2fa-auto
   ```

---

## Reference

- **Google Cloud Console**: https://console.cloud.google.com
- **Gmail Settings**: https://mail.google.com/mail/u/0/#settings
- **Google OAuth 2.0 Scopes**: https://developers.google.com/identity/protocols/oauth2/scopes#gmail
- **Gmail API Docs**: https://developers.google.com/gmail/api/guides

---

**Created**: 2026-03-21
**Last Updated**: 2026-03-21
**Project**: SAP-Facture Orchestrateur
