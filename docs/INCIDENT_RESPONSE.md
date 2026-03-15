# Incident Response Plan — SAP-Facture Security

**Document** : Emergency procedures for security incidents
**Author** : Security Reviewer
**Date** : 15 Mars 2026
**Status** : Final
**Escalation** : Contact immediately if security compromise suspected

---

## Quick Response Table

| Incident Type | Severity | Response Time | First Action |
|---|---|---|---|
| **Secrets Compromised (.env leak)** | CRITICAL | < 30 min | Rotate ALL credentials |
| **Google Sheets Shared Publicly** | CRITICAL | < 1 hour | Restrict sharing + audit |
| **Unauthorized API Access** | HIGH | < 2 hours | Block attacker IP + audit logs |
| **URSSAF Token Abuse** | HIGH | < 4 hours | Notify URSSAF + rotate creds |
| **Data Breach (PII exfiltration)** | CRITICAL | < 24 hours | RGPD breach notification |
| **Service Down (DoS/API error)** | MEDIUM | < 30 min | Check status + diagnostics |

---

## 1. Secrets Compromised (.env leak)

### Scenario
- `.env` file accidentally committed to GitHub
- or `.env` file leaked via email/Slack
- or server compromised, `.env` copied

### Response (30 minutes)

#### Step 1 : Immediate (5 min)
```bash
# If on GitHub:
# 1. Delete repository or make private immediately
# 2. Contact GitHub support to scrub from history
# 3. If public → assume credentials compromised

# If local only:
# Check git history for leaks
git log -p -- .env | head -20
git log --all --source --remotes -- '.env*' | wc -l

# If found, secrets are compromised → go to Step 2
```

#### Step 2 : Rotate ALL Credentials (15 min)

**URSSAF** :
1. Go to https://portailapi.urssaf.fr/
2. Regenerate OAuth2 credentials (new client_id + client_secret)
3. Update `.env`:
   ```
   URSSAF_CLIENT_ID=NEW_ID_HERE
   URSSAF_CLIENT_SECRET=NEW_SECRET_HERE
   ```
4. Redeploy application

**Google Service Account** :
1. Go to https://console.cloud.google.com/ (IAM & Admin → Service Accounts)
2. Select service account → Keys
3. Delete old key
4. Generate new JSON key
5. Encode to base64: `base64 -i /path/to/new-key.json`
6. Update `.env`:
   ```
   GOOGLE_SERVICE_ACCOUNT_B64=NEW_BASE64_KEY_HERE
   ```
7. Redeploy application

**Swan API Key** :
1. Go to https://docs.swan.io/ (Account settings)
2. Revoke old API key
3. Generate new API key
4. Update `.env`:
   ```
   SWAN_API_KEY=NEW_API_KEY_HERE
   ```
5. Redeploy application

**SMTP Password** :
1. For Gmail: https://myaccount.google.com/apppasswords
2. Delete old app password
3. Generate new app password
4. Update `.env`:
   ```
   SMTP_PASSWORD=NEW_APP_PASSWORD_HERE
   ```
5. Redeploy application

**API Key** :
```bash
# Generate new strong key
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Update .env:
API_KEY_INTERNAL=NEW_KEY_HERE
```

#### Step 3 : Clean Git History (10 min)

If `.env` was committed:

```bash
# OPTION A: Git filter-branch (destructive, rewrites history)
# WARNING: This changes all commit hashes. Only do if urgent.

git filter-branch --tree-filter 'rm -f .env' HEAD

# Force push (caution: this rewrites public history)
git push --force --all


# OPTION B: Use BFG (simpler for secrets cleanup)
bfg --delete-files .env
git reflog expire --expire=now --all && git gc --prune=now --aggressive

# OPTION C: Reset to before leak (safest)
# 1. Reset to commit before .env was added
git log --oneline | grep "add .env"
# Output: a1b2c3d add: .env accidentally

# 2. Reset to before that commit
git reset --hard a1b2c3d^

# 3. Rebuild from clean state
git push --force origin main
```

#### Step 4 : Notify Key Stakeholders (5 min)

If secrets in GitHub or other public place:

```
TO: Jules
SUBJECT: SECURITY ALERT — Credentials Compromised

SUMMARY:
- Secrets leaked in .env file (git commit / email / etc.)
- All credentials rotated (URSSAF, Google, Swan, SMTP)
- Application redeployed with new credentials
- Incident logged in audit trail

ACTION ITEMS:
1. Change all passwords on related accounts (URSSAF, Google, GitHub)
2. Monitor logs for suspicious activity (see Audit logs)
3. Check bank transactions for unauthorized activity
4. Review Google Sheets sharing (should be restricted to Jules + SA)

TIMELINE:
- Incident detected: [TIMESTAMP]
- Credentials rotated: [TIMESTAMP]
- Application redeployed: [TIMESTAMP]
```

#### Step 5 : Audit Logs Review (5 min)

Check for unauthorized activity:

```bash
# Look for suspicious URSSAF calls (before rotation)
grep "URSSAF_API_CALL" logs/audit.log | \
  awk -F'|' '{print $2}' | \
  sort | uniq -c | sort -rn

# Look for suspicious invoice creations
grep "INVOICE_CREATED" logs/audit.log | \
  awk -F'|' '{print $2}' | \
  sort | uniq -c | sort -rn

# Look for unauthorized API access
grep "AUTH_FAILED" logs/audit.log | wc -l

# If suspicious pattern found, check timestamps
tail -100 logs/audit.log | grep "2026-03-15T14:3"  # Example time range
```

---

## 2. Google Sheets Shared Publicly

### Scenario
- Jules accidentally shares entire spreadsheet with "Anyone with link"
- PII (names, emails, addresses) exposed to public
- Attacker downloads Sheets and has access to all data

### Response (1 hour)

#### Step 1 : Restrict Immediately (5 min)

```
1. Open https://docs.google.com/ → find SAP-Facture Sheets
2. Click Share (top right)
3. Change from "Public" to "Restricted"
4. Remove all non-essential permissions
5. Verify: Only "Jules" (Owner) + "Service Account" (Editor)
```

#### Step 2 : Audit Access (10 min)

Check who accessed Sheets while it was public:

```python
# Use Google Cloud Audit Logs
# Go to https://console.cloud.google.com/ → Logging → Logs Explorer

# Query:
resource.type="drive"
protoPayload.methodName="drive.files.get"
protoPayload.resourceName="SAP-FACTURE-SHEETS-ID"
timestamp>"2026-03-15T10:00:00Z"  # Adjust to incident time
```

#### Step 3 : Assess Data Exposure (15 min)

If Sheets was public for N hours:

```
AT RISK:
- Client names, emails, phone numbers (PII)
- Addresses (PII — physical security risk)
- Invoice amounts (business information)
- Bank transaction data (if visible)

NOT AT RISK:
- Formulas (calculated onglets are derived, not raw PII)
- System information
```

#### Step 4 : RGPD Notification (if data exposed > 1 hour to unknown users)

If PII accessed by unauthorized parties:

```
STEPS:
1. Notify Jules within 24 hours of discovery
2. Prepare notification for clients (template below)
3. Notify CNIL (French data authority) if > 50 clients affected
4. Document timeline and mitigation

TEMPLATE EMAIL TO CLIENTS:

Subject: Data Security Notification — Immediate Action Not Required

Dear [Client],

We are writing to inform you of a security incident affecting
your personal data that we briefly collected for invoice processing.

WHAT HAPPENED:
On March 15, 2026, our data storage (Google Sheets) was inadvertently
configured to allow public access for approximately [X] hours. During
this time, your name and email address may have been accessible to
the internet.

WHAT WE'RE DOING:
- Immediately restricted access to only authorized users
- Reviewed access logs (no evidence of misuse detected)
- Notified relevant authorities as required by GDPR

YOUR RIGHTS:
Under GDPR Article 15-20, you have the right to:
- Access your data: reply to this email
- Rectification: request data corrections
- Deletion: request data removal (right to be forgotten)
- Portability: receive your data in machine-readable format

NEXT STEPS:
1. Reply to confirm your contact info is correct
2. We will enhance security to prevent recurrence
3. No action required from you at this time

Contact: jules@example.com
```

#### Step 5 : Prevent Recurrence (10 min)

```python
# Add code to check permissions at startup
# See: docs/phase1/11-security-implementation-phase1.md (Task 3)

# This will verify permissions are correct and alert if changed
python app/security/audit_sheets.py
```

---

## 3. Unauthorized API Access

### Scenario
- Attacker guesses or obtains valid API key
- Creates 100+ invoices in 1 minute
- Modifies client records

### Response (2 hours)

#### Step 1 : Detect (automated)

Monitoring script should alert:

```python
# Detect spike in API calls
THRESHOLD_INVOICES_PER_HOUR = 50
THRESHOLD_API_CALLS_PER_MINUTE = 100

if (invoices_created_this_hour > THRESHOLD_INVOICES_PER_HOUR):
    send_alert("SECURITY: Suspicious invoice creation rate")

if (api_calls_this_minute > THRESHOLD_API_CALLS_PER_MINUTE):
    send_alert("SECURITY: Rate limit exceeded")
```

#### Step 2 : Immediate Actions (10 min)

```bash
# 1. Check recent audit logs for suspicious activity
tail -1000 logs/audit.log | grep "2026-03-15T14:"

# 2. Identify attacker IP (if available from logs)
grep "AUTH_FAILED\|INVOICE_CREATED" logs/audit.log | \
  tail -50 | grep "suspicious_pattern"

# 3. Block attacker IP (if known)
# In fastapi, add to blocklist:
BLOCKED_IPS = ["192.168.1.100"]  # Attacker IP

# 4. Rotate API key immediately
NEW_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
# Update .env
sed -i "s/API_KEY_INTERNAL=.*/API_KEY_INTERNAL=$NEW_API_KEY/" .env
git add .env
git commit -m "security: rotate API key after unauthorized access"
```

#### Step 3 : Investigate Damage (30 min)

```bash
# 1. Count fraudulent invoices
grep "INVOICE_CREATED" logs/audit.log | wc -l

# 2. List all invoices created in suspicious time window
grep "INVOICE_CREATED" logs/audit.log | \
  awk -F'|' '$NF ~ /2026-03-15T14:3[0-9]/ {print}' | \
  cut -d'=' -f3 | cut -d' ' -f1

# 3. Check if URSSAF was called with fraudulent data
grep "URSSAF_API_CALL" logs/audit.log | \
  awk -F'|' '$NF ~ /2026-03-15T14:3[0-9]/ {print}' | wc -l

# 4. Review Google Sheets for unauthorized changes
# Sheets → Version history → check edits from attacker
```

#### Step 4 : Remediate (30 min)

```bash
# 1. Delete fraudulent invoices from Sheets
# Open Sheets → Factures onglet → select fraudulent rows → delete

# 2. Reverse URSSAF submissions if applicable
# For each fraudulent invoice, call URSSAF to cancel/withdraw
# See URSSAF API docs for cancellation endpoint

# 3. Update audit logs
echo "2026-03-15T14:35 | INCIDENT: Fraudulent invoices deleted (IDs: ...)" >> logs/audit.log

# 4. Notify URSSAF (if they received fraudulent requests)
# Email: support@urssaf.fr
# Subject: Security Incident - Unauthorized API Access
# Body: Explain fraudulent invoices, request review & cancellation
```

---

## 4. URSSAF Token Abuse

### Scenario
- Attacker uses URSSAF credentials to:
  - Create fake invoices in Jules' account
  - Register fake clients
  - Receive payments intended for Jules

### Response (4 hours)

#### Step 1 : Immediate (15 min)

```bash
# 1. Rotate URSSAF credentials NOW
# Go to https://portailapi.urssaf.fr/ → regenerate client_id + secret

# 2. Update .env
URSSAF_CLIENT_ID=NEW_ID
URSSAF_CLIENT_SECRET=NEW_SECRET

# 3. Redeploy application
git add .env && git commit -m "security: rotate URSSAF creds after token abuse"

# 4. Contact URSSAF support
# Email: support@urssaf.fr
# Subject: SECURITY INCIDENT - Unauthorized API Access
# Body:
#   - Explain token was compromised
#   - List any fraudulent invoices/clients created
#   - Request review of all requests between [START_TIME] and [END_TIME]
#   - Request cancellation of fraudulent submissions
```

#### Step 2 : Investigate (1 hour)

```bash
# 1. Pull all URSSAF API calls from logs
grep "URSSAF_API_CALL" logs/audit.log | sort

# 2. Identify fraudulent entries by:
#    - Timestamps outside normal working hours
#    - Unusual client_ids (not in legitimate list)
#    - Unusual montants (amount outside normal range)

# 3. Create list of fraudulent requests
# Save to file: fraudulent_urssaf_requests.csv
cat << EOF > fraudulent_requests.csv
timestamp,endpoint,client_id,montant,status
2026-03-15T02:35,/demandes-paiement,FAKE_CLIENT_1,50000,CREE
2026-03-15T02:40,/demandes-paiement,FAKE_CLIENT_2,75000,CREE
EOF

# 4. Send to URSSAF for investigation
# Attach: fraudulent_requests.csv
```

#### Step 3 : Monitor Bank Account (2 hours)

```bash
# 1. Check Swan account for unauthorized transactions
# Go to Swan dashboard → Recent transactions

# 2. If fake invoices were paid:
#    a) Document transaction IDs
#    b) Contact Swan support to dispute (request chargeback)
#    c) File complaint with bank (official dispute)

# 3. Block any suspicious transactions:
swan_client.freeze_account()  # If urgent
```

#### Step 4 : Notify Stakeholders (30 min)

```
TO: Jules
CC: Bank, URSSAF

SUBJECT: SECURITY INCIDENT — URSSAF Credentials Compromised

INCIDENT SUMMARY:
- URSSAF API credentials were compromised
- Fraudulent invoices were created in your account
- Credentials have been rotated
- Investigating unauthorized transactions

IMPACT:
- [N] fraudulent invoices created
- [N] fraudulent clients registered
- [N] fraudulent payments processed (if any)

ACTION ITEMS:
1. Change URSSAF password immediately
2. Review URSSAF portal for unauthorized activity
3. Contact your bank if payments received for fraudulent invoices
4. Confirm legitimate invoices with clients (to prevent confusion)

TIMELINE:
- Incident detected: [TIME]
- Credentials rotated: [TIME]
- URSSAF notified: [TIME]
- Investigation completed: [TIME]
```

---

## 5. Data Breach (PII Exfiltration)

### Scenario
- Attacker gains access to Sheets
- Downloads all client data (names, emails, addresses)
- PII is now in attacker's hands (RGPD violation)

### Response (24 hours)

#### Step 1 : Confirmation (1 hour)

```bash
# 1. Review access logs (Google Cloud Audit Logs)
# Go to https://console.cloud.google.com/ → Logging

# 2. Determine:
#    - When access occurred
#    - Which files were accessed
#    - How much data was downloaded
#    - Who accessed (if identifiable)

# 3. Check for data exfiltration patterns:
#    - Bulk downloads (hundreds of rows)
#    - Access from unusual IP or country
#    - Access at unusual time
```

#### Step 2 : Immediate Actions (2 hours)

```bash
# 1. Restrict all access to Sheets
# Remove all permissions except Jules (owner)

# 2. Change all authentication methods
# - Rotate Google Service Account key
# - Change Jules' Google password
# - Enable 2-factor authentication

# 3. Review sharing history
# Sheets → Share → Advanced → See all sharing changes

# 4. Take backup of Sheets (for evidence)
# Download CSV of all onglets
# Archive with timestamp
```

#### Step 3 : GDPR Breach Notification (within 24 hours)

**Notify Data Subjects** (within 72 hours if high risk):

```
TEMPLATE BREACH NOTIFICATION:

TO: All Clients (email)
SUBJECT: Data Security Incident Notification

Dear [Client],

We are writing to inform you of a data security incident that may
have affected your personal data.

WHAT HAPPENED:
On [DATE] at [TIME], unauthorized access to our data storage was
detected. Your name, email address, and physical address may have
been accessed by an unauthorized third party.

SCOPE:
- Number of individuals affected: [N]
- Data types exposed: Name, Email, Address
- No financial data (invoice amounts) was accessible
- No bank account information was exposed

MEASURES TAKEN:
- Immediate access restriction implemented
- Security credentials rotated
- Investigation launched with cybersecurity team
- Authorities notified (CNIL)

YOUR RIGHTS (GDPR Article 15-21):
- Right of Access: Request copy of your data
- Right to Rectification: Correct any inaccurate data
- Right to Erasure: Request deletion of your data
- Right to Portability: Receive data in machine-readable format

RECOMMENDED ACTIONS:
1. Monitor your email and phone for phishing attempts
2. Change passwords if you reused credentials elsewhere
3. Consider fraud monitoring (free services available in France)
4. Contact us if you have concerns

CONTACT:
Jules Willard
Email: jules@example.com
Phone: +33 6 XX XX XX XX

Sincerely,
SAP-Facture Team
```

**Notify CNIL** (if > 50 individuals affected):

```
STEPS:
1. Go to https://www.cnil.fr/
2. File data breach report (dossier de violation)
3. Include:
   - Date/time incident discovered
   - Description of what happened
   - Data categories involved
   - Number of affected individuals
   - Impact assessment
   - Measures taken
4. CNIL will investigate and may impose fines

TEMPLATE CNIL NOTIFICATION:

Incident: Unauthorized access to Google Sheets
Date Discovered: 2026-03-15
Data Exposed: Client names, emails, addresses (PII)
Individuals Affected: [N]
Cause: Credentials compromised / access misconfiguration
Measures: Credentials rotated, access restricted, investigation ongoing
```

---

## 6. Service Down (DoS / API Error)

### Scenario
- API not responding (timeout 5xx errors)
- Google Sheets API quota exceeded
- URSSAF API down

### Response (30 minutes)

#### Step 1 : Diagnose (5 min)

```bash
# 1. Check if service is responding
curl -X GET http://localhost:8000/health
# Expected: {"status": "ok"}

# 2. Check recent logs
tail -50 logs/app.log

# 3. Check Google Sheets quota
curl -X GET https://sheets.googleapis.com/v4/spreadsheets/[SHEET_ID] \
  -H "Authorization: Bearer $GOOGLE_TOKEN"

# 4. Check URSSAF API status
curl https://portailapi.urssaf.fr/health

# 5. Check system resources
free -h  # Memory
df -h    # Disk
ps aux | grep python  # Process count
```

#### Step 2 : Identify Root Cause (5 min)

| Symptom | Likely Cause | Fix |
|---|---|---|
| `Connection timeout` | Network issue / firewall | Check connectivity, restart service |
| `429 Rate Limited` | API quota exceeded | Wait 1 minute, implement batching |
| `500 Internal Server Error` | Code exception | Check logs, restart service |
| `Service unreachable` | Server crashed | Check process, restart |
| `Certificate error` | TLS issue | Renew cert, check CA bundle |

#### Step 3 : Immediate Recovery (10 min)

```bash
# If service crashed
systemctl restart sap-facture

# If rate limit hit, wait and retry
sleep 60
curl -X POST http://localhost:8000/invoices

# If cert expired
# Renew: certbot renew
systemctl restart nginx

# If disk full
df -h | grep 100%
rm -rf logs/archive/*  # Clean old logs
```

#### Step 4 : Notify Users (5 min)

```
TO: Jules
SUBJECT: Service Status — [INCIDENT]

STATUS: [RECOVERING / RESOLVED]
IMPACT: [N] minutes of unavailability
CAUSE: [ROOT CAUSE]
FIX: [WHAT WAS DONE]

NEXT STEPS:
1. Verify service is working: curl http://api/health
2. Test critical functionality
3. Review logs for any data corruption

TIMELINE:
- Incident started: [TIME]
- Root cause identified: [TIME]
- Service recovered: [TIME]
```

---

## Incident Log Template

File: `logs/INCIDENTS.log`

```
# SAP-Facture Incident Log

## Incident #001: Credentials Leaked in Git

**Date**: 2026-03-15
**Time**: 14:35 UTC
**Severity**: CRITICAL
**Status**: RESOLVED

### Timeline
- 14:35: Incident discovered (GitHub secret scan)
- 14:40: All credentials rotated
- 14:50: Application redeployed
- 15:00: Audit logs reviewed (no unauthorized activity detected)

### Root Cause
Developer accidentally committed .env to git

### Resolution
- Rotated URSSAF (client_id, client_secret)
- Rotated Google SA key
- Rotated Swan API key
- Rotated SMTP password
- Rotated API key
- Cleaned git history with BFG

### Impact
- No unauthorized invoices created
- No financial loss
- No data breach

### Prevention
- Added pre-commit hook to block .env commits
- Added .env* to .gitignore permanently
- Trained on secret management best practices

### Follow-up
- [ ] Implement automated secret scanning
- [ ] Setup alerts for git commits containing secrets
- [ ] Quarterly credential rotation policy
```

---

## Emergency Contacts

**Internal** :
- Jules (owner): +33 6 XX XX XX XX
- Bank: [Bank Name] Incident Line

**External** :
- CNIL (GDPR authority): https://www.cnil.fr/ | +33 1 53 73 22 22
- URSSAF Support: support@urssaf.fr | +33 1 XX XX XX XX
- Swan Support: support@swan.io
- Google Cloud Support: https://cloud.google.com/support

**Law Enforcement** (if criminal activity suspected):
- Police: 17 (France)
- Cybercrime Unit: https://www.cnil.fr/

---

## Post-Incident Review (1 week after)

After any security incident, conduct review:

```markdown
## Incident #[N] Post-Mortem

**What happened**: [Description]
**When**: [Date/Time]
**Impact**: [Severity, Duration, Data Loss]
**Root cause**: [Technical reason]
**How we detected it**: [Detection method]
**How we fixed it**: [Steps taken]

### What went well
- [Positive aspect 1]
- [Positive aspect 2]

### What could be better
- [Area for improvement 1]
- [Area for improvement 2]

### Action items
- [ ] [Prevention measure 1] (Owner: X, Deadline: Y)
- [ ] [Prevention measure 2] (Owner: X, Deadline: Y)
```

---

**Last Updated** : 15 Mars 2026
**Next Review** : Every 6 months or after incident

---

## Quick Reference Card (Print This)

```
═══════════════════════════════════════════════════════════════════
        SAP-FACTURE SECURITY INCIDENT — QUICK RESPONSE
═══════════════════════════════════════════════════════════════════

INCIDENT TYPE              │ SEVERITY │ FIRST ACTION
─────────────────────────────────────────────────────────────────
Secrets Leaked (.env)      │ CRITICAL │ Rotate ALL credentials
Sheets Public              │ CRITICAL │ Restrict sharing NOW
Unauthorized API Access    │ HIGH     │ Block IP + rotate key
Token Abuse (URSSAF)       │ HIGH     │ Rotate + contact URSSAF
Data Breach (PII)          │ CRITICAL │ Confirm + notify CNIL
Service Down               │ MEDIUM   │ Restart + diagnose

─────────────────────────────────────────────────────────────────
EMERGENCY CONTACTS:
• Jules: +33 6 XX XX XX XX
• CNIL (breach): https://www.cnil.fr/
• URSSAF: support@urssaf.fr
• Police (criminal): 17

─────────────────────────────────────────────────────────────────
CHECKLIST (always do these):
☐ Document timeline (date/time incident started)
☐ Review audit logs (grep logs/audit.log)
☐ Notify affected parties within 24h
☐ Rotate ALL compromised credentials
☐ Redeploy with new credentials
☐ File CNIL report if PII breach > 50 people
═══════════════════════════════════════════════════════════════════
```

