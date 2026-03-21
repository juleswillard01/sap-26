# Gmail IMAP Setup — Quick Start (5 minutes)

## TL;DR: Jules's Checklist

Your Gmail **does NOT work** with regular password on IMAP as of 2026. You must use an **App Password**.

### Step 1: Enable 2FA (2 minutes)

1. Go to https://myaccount.google.com/security
2. Click **2-Step Verification** → **Get started**
3. Choose SMS or authenticator app
4. Verify your phone
5. Done ✓

### Step 2: Generate App Password (1 minute)

1. Go to https://myaccount.google.com/security (still there)
2. Click **App passwords** (only appears if 2FA enabled)
3. Select **Mail**
4. Select **Linux** (or your device)
5. Click **Generate**
6. Google shows: `abcd efgh ijkl mnop` (16 chars with space)
7. **Copy** this password (remove the space: `abcdefghijklmnop`)

### Step 3: Store in `.env` (30 seconds)

```bash
# .env file
GMAIL_IMAP_USER=your-full-email@gmail.com
GMAIL_IMAP_PASSWORD=abcdefghijklmnop
```

**Note**: This is `.env`, NOT `.env.example`. Never commit `.env` to git.

### Step 4: Create Gmail Label (30 seconds)

1. Go to https://mail.google.com
2. Click **Settings** (gear icon)
3. Click **Labels** tab
4. Click **Create new label**
5. Name: `Indy-2FA`
6. Click **Create**

### Step 5: Create Gmail Filter (1 minute)

1. Still in **Settings**
2. Click **Filters and Blocked Addresses** tab
3. Click **Create a new filter**
4. In **From** field: `noreply@indy.fr`
5. Click **Create filter**
6. Check **Apply label** → Select **Indy-2FA**
7. (Optional) Check **Skip the Inbox** to hide from inbox
8. Click **Create filter**

### Step 6: Test It Works (30 seconds)

```bash
cd /home/jules/Documents/3-git/SAP/PAYABLES
python << 'EOF'
import imaplib
from src.config import Settings

settings = Settings()
imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
imap.login(settings.gmail_imap_user, settings.gmail_imap_password)
status, mailboxes = imap.list()

# Check if "Indy-2FA" label exists
for mailbox in mailboxes:
    if b"Indy-2FA" in mailbox:
        print("✓ Indy-2FA label found!")
        break
else:
    print("⚠ Indy-2FA label not found. Check step 4.")

imap.close()
EOF
```

Expected output: `✓ Indy-2FA label found!`

---

## Common Issues

### "Login failed" Error

**Problem**: `[Gmail] LOGIN failed`

**Cause**: Using regular Gmail password instead of App Password

**Fix**:
- You generated an App Password, right? (16 chars with space)
- Paste it in `.env` **without the space**
- If you lost it, delete it in Google Account → App passwords → delete, then re-generate

### "Label not found" Error

**Problem**: `Cannot select label 'Indy-2FA'`

**Cause**: Label doesn't exist in Gmail

**Fix**: Follow **Step 4** again. Label name must be **exact case**: `Indy-2FA`

### "2FA disabled" Error

**Problem**: "App passwords" option missing in Google Account

**Cause**: 2FA not enabled

**Fix**: Follow **Step 1** — must enable 2FA first to use App Passwords

---

## What Your Code Does

After setup, your code can read Indy 2FA emails like this:

```python
from src.adapters.gmail_reader import GmailReader
from src.config import Settings

reader = GmailReader(Settings())

# Read from Indy-2FA label, wait up to 60 seconds
code = reader.get_latest_2fa_code(
    label="Indy-2FA",
    timeout_sec=60,
    sender_filter="indy"
)

print(f"2FA code: {code}")
reader.close()
```

---

## Security Notes

- **App Password**: Only works for IMAP/SMTP (not Gmail web)
- **Safe to store in `.env`**: It's limited to email protocols
- **Revoke anytime**: If exposed, delete in Google Account → App passwords
- **Never commit `.env`**: Already in `.gitignore`
- **Rotate annually**: Good practice to refresh periodically

---

## Need Help?

See full documentation: `/home/jules/Documents/3-git/SAP/PAYABLES/docs/GMAIL_IMAP_RESEARCH.md`
