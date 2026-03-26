# Indy API Contracts — Reverse Engineering

> Discovered 2026-03-26 via CDP network interception on app.indy.fr
> Source: MPP-64

## Architecture

```
Client (httpx)
    │
    ├─ POST /api/auth/login  ──→  Indy Server (Node.js)
    │      {email, password, turnstileToken, mfaVerifyPayload?}
    │      ← 401 (triggers 2FA email) or 200 (returns Firebase custom token)
    │
    ├─ POST identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken
    │      {token: <custom_token>}
    │      ← {idToken (Bearer JWT, 1h TTL), refreshToken}
    │
    ├─ POST securetoken.googleapis.com/v1/token  (refresh, no browser needed)
    │      {grant_type: "refresh_token", refresh_token: <refresh_token>}
    │      ← {id_token (new Bearer), refresh_token (new)}
    │
    └─ GET/POST /api/*  ──→  Indy Server
           Authorization: Bearer <idToken>
```

**Firebase Project**: `georges-prod`
**Firebase API Key**: `AIzaSyAVJ8xwjy0uG-zgPKQKUADa2-c-4KKHryI`
**Backend**: Swan (PSD2 banking) via `bankConnector.type: "swan"`

## Auth Flow

### 1. Login (requires Turnstile — nodriver one-time)

```http
POST https://app.indy.fr/api/auth/login
Content-Type: application/json

# Step 1: Trigger 2FA
{"email": "...", "password": "...", "turnstileToken": "...", "h": false}
← 401 (2FA email sent to user)

# Step 2: Submit with 2FA code
{"email": "...", "password": "...", "turnstileToken": "...",
 "mfaVerifyPayload": {"type": "email", "emailCode": "888267"}, "h": false}
← 200 {customToken: "eyJ..."}
```

### 2. Exchange custom token → Bearer JWT

```http
POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key=AIzaSyAVJ8xwjy0uG-zgPKQKUADa2-c-4KKHryI
Content-Type: application/json

{"token": "<customToken>", "returnSecureToken": true}
← 200 {"idToken": "eyJ...", "refreshToken": "AMf-...", "expiresIn": "3600"}
```

### 3. Refresh token (no browser, no captcha, no 2FA)

```http
POST https://securetoken.googleapis.com/v1/token?key=AIzaSyAVJ8xwjy0uG-zgPKQKUADa2-c-4KKHryI
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token&refresh_token=<refreshToken>
← 200 {"id_token": "eyJ...", "refresh_token": "AMf-...", "expires_in": "3600"}
```

## Endpoints — Banking (SAP-Facture scope)

All endpoints require `Authorization: Bearer <idToken>`.

### Transactions

```http
GET /api/transactions/transactions-list
GET /api/transactions/transactions-list?bankAccountId={id}
GET /api/transactions/transactions-list?startDate=2025-01-01&endDate=2026-03-31
```

**Response**:
```json
{
  "transactions": [{
    "_id": "AzbkfKqk2G8dF4wes",
    "date": "2025-01-01",
    "description": "...",
    "rawDescription": "...",
    "amountInCents": 0,
    "totalAmountInCents": 0,
    "transactionType": "od",
    "bankAccountId": "Xv7tiXcgbqoiKJ97k",
    "isVerified": false,
    "isDeleted": false,
    "subdivisions": [{
      "amount_in_cents": 0,
      "accounting_account": {"number": "512001"},
      "tva_rate": 0
    }]
  }],
  "nbTransactions": 1,
  "toCategorizeCount": 0
}
```

### Transactions en attente

```http
GET /api/transactions/transactions-pending-list
```

**Response**:
```json
{"pendingTransactions": [], "upcomingTransactions": []}
```

### Compte Pro — Bank Account

```http
GET /api/compte-pro/bank-account
```

**Response**:
```json
{
  "_id": "Xv7tiXcgbqoiKJ97k",
  "name": "Compte courant",
  "balanceInCents": 0,
  "availableBalanceInCents": 0,
  "lastSyncAt": "2026-03-26T05:39:18.276Z",
  "bankConnector": {
    "id": "76e14af1-a2db-452d-b818-5b3b37b305a8",
    "type": "swan",
    "accountStatus": "Opened"
  }
}
```

### Compte Pro — Account Statements (relevés mensuels)

```http
GET /api/compte-pro/account-statements
```

**Response**: Array of monthly statements with pre-signed Swan PDF URLs.
```json
[
  {
    "closingDate": "2026-02-28",
    "url": "https://documents-v2.swan.io/accounts/{id}/account-statements/ReleveCompte_...pdf?Expires=...&Signature=..."
  }
]
```

**Download**: Les URLs sont pré-signées (pas besoin d'auth Indy). `GET <url>` retourne le PDF directement.
- Content-Type: `application/pdf`
- Taille typique: ~80KB
- Expiration URL: quelques heures

### Bank Accounts

```http
GET /api/bank-connector/bank-accounts?withAvailableBalanceInCents=true&withConnectorBankAccountStatus=true
```

**Response**:
```json
{
  "bankAccounts": [{
    "_id": "Xv7tiXcgbqoiKJ97k",
    "name": "Compte courant",
    "balanceInCents": 0,
    "bankConnector": {"id": "...", "type": "swan"}
  }]
}
```

### Accounting Summary

```http
POST /api/accounting/transactions/summary
Content-Type: application/json

{}
# ou avec filtre dates:
{"startDate": "2025-09-01", "endDate": "2026-03-31"}
```

**Response**:
```json
{
  "totalTransactionsCount": 1,
  "totalAmountInCents": 0,
  "totalIncomeAmountInCents": 0,
  "totalExpenseAmountInCents": 0
}
```

## IDs de référence

| Ressource | ID |
|---|---|
| User (Firebase) | `kyJdpYjE4k5BspsKo` |
| Bank Account | `Xv7tiXcgbqoiKJ97k` |
| Swan Connector | `76e14af1-a2db-452d-b818-5b3b37b305a8` |
| Bank Auth | `MMDdCQYdZQ8xuvq8y` |

## Decision: REST httpx vs Playwright

| Critère | Playwright (avant) | httpx REST (maintenant) |
|---|---|---|
| Login | nodriver + Turnstile + 2FA | nodriver Turnstile (1x) + httpx auth |
| Token refresh | Re-login complet | `POST securetoken.googleapis.com` (0 browser) |
| Transactions | Scrape DOM | `GET /api/transactions/transactions-list` |
| Relevés PDF | Click bouton + download | `GET /api/compte-pro/account-statements` → URL directe |
| Fiabilité | Fragile (selectors, timing) | Stable (API JSON) |
| Performance | ~30s (browser) | ~200ms (HTTP) |

**Decision: httpx pour toutes les opérations bancaires.** nodriver uniquement pour le login initial (Turnstile).
