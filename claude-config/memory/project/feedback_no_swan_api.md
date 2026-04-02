---
name: Indy banking — REST httpx, pas Swan API ni Bridge
description: Transactions bancaires via API REST Indy reverse-engineered (httpx), pas Swan GraphQL ni Bridge PSD2. Nodriver uniquement pour login initial (Turnstile + 2FA).
type: feedback
---

Pas d'acces a l'API Swan ni Bridge PSD2. Les transactions bancaires sont recuperees via l'API REST Indy reverse-engineered (MPP-64).

**Why:** Jules utilise Indy comme outil bancaire. MPP-64 a decouvert que Indy expose une API REST interne (Firebase Auth + Bearer JWT). httpx remplace Playwright pour toutes les operations bancaires (200ms vs 30s).

**How to apply:**
- Auth : nodriver 1x pour Turnstile + 2FA → Firebase JWT → refresh httpx (0 browser apres login)
- Endpoints REST : `/api/transactions/*`, `/api/compte-pro/*`, `/api/bank-connector/*`
- `IndyAPIAdapter` (httpx) remplace `IndyBrowserAdapter` (Playwright) pour les donnees
- Secrets : email Indy, password Indy, Firebase API key (dans .env)
- Contrat API documente dans `docs/specs/INDY_API_CONTRACTS.md`
