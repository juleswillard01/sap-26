---
name: Indy login + API reverse-engineering validated
description: Indy login nodriver + 2FA Gmail valide. API REST reverse-engineered (MPP-64 DONE) — 14/16 endpoints valides, Firebase Auth, Bearer JWT 1h, refresh sans browser.
type: project
---

## Indy Login — Validated 2026-03-22

Flow complet nodriver + Gmail IMAP 2FA fonctionne.

## API Reverse-Engineering — Validated 2026-03-26 (MPP-64 DONE)

CDP interception via `tools/indy_intercept.py` a decouvert l'API REST complete :

### Auth Flow (Firebase Auth, projet georges-prod)
1. POST `/api/auth/login` (email + password + turnstileToken + mfaVerifyPayload.emailCode)
2. POST `identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken` → Bearer JWT 1h
3. POST `securetoken.googleapis.com/v1/token` → refresh SANS browser

### Endpoints bancaires (Bearer JWT)
- GET `/api/transactions/transactions-list?startDate=X&endDate=Y` → transactions JSON
- GET `/api/transactions/transactions-pending-list` → pending
- GET `/api/compte-pro/bank-account` → solde, lastSyncAt
- GET `/api/compte-pro/account-statements` → releves PDF (URLs Swan pre-signees)
- GET `/api/bank-connector/bank-accounts` → liste comptes

### IDs
- Bank Account: `Xv7tiXcgbqoiKJ97k`
- Firebase API Key: `AIzaSyAVJ8xwjy0uG-zgPKQKUADa2-c-4KKHryI`

### Next: MPP-65
Creer `IndyAPIAdapter` (httpx) qui encapsule ces endpoints.

**Why:** Playwright = 30s/requete, fragile. httpx = 200ms, JSON stable. Nodriver reste uniquement pour login initial (Turnstile).
**How to apply:** Branche `feat/mpp-64-indy-reverse-api` contient INDY_API_CONTRACTS.md + tools valides.
