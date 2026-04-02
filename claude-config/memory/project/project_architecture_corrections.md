---
name: Architecture corrections post-recherche
description: Corrections majeures apres recherche 100+ sources — API URSSAF REST existe, Bridge API PSD2 pour banque, pas de Playwright scraping
type: project
---

## Corrections Architecture — 2026-03-21

Recherche approfondie (10 agents, 100+ sources) a révélé des erreurs dans l'architecture initiale.

### FAUX → VRAI

1. **Playwright scrape avance-immediate.fr** → **API Tiers de Prestation URSSAF (REST OAuth2)**
   - Production: api.urssaf.fr
   - Sandbox: api-edi.urssaf.fr
   - Docs: portailapi.urssaf.fr/images/Documentation/Documentation-API-TiersPrestation_v1-1-6.pdf
   - Auth: OAuth2 client_credentials
   - Habilitation: DataPass (2-4 mois)

2. **Playwright scrape Indy Banking** → **Bridge API (PSD2) ou Nordigen (gratuit)**
   - Bridge: bridgeapi.io — 300+ banques FR, ACPR-certifié, utilisé par Indy
   - Nordigen: API PSD2 gratuite pour données bancaires EU
   - CNIL interdit le scraping bancaire (amende €20M)

3. **avance-immediate.fr = portail URSSAF** → **AIS = société privée tierce**
   - AIS est 1 des 10+ logiciels compatibles (Sinao, Abby, Evoliz, Ogust...)
   - AIS utilise l'API Tiers de Prestation en backend

### Flow Réel (Avance Immédiate)
1. Provider s'habilite via DataPass (2 mois)
2. Provider reçoit client_id + client_secret
3. Provider soumet facture via API → URSSAF
4. URSSAF notifie client (email/SMS)
5. Client valide sous 48h sur particulier.urssaf.fr (auto-validé si inaction)
6. URSSAF paie provider 100% en 4 jours ouvrés
7. URSSAF débite client 50% en 2 jours ouvrés

### Statuts API Réels
- EN_ATTENTE_VALIDATION
- VALIDEE
- REFUSEE
- ANNULEE
- EN_REFUS_DE_PRELEVEMENT

### Architecture Cible Corrigée
```
src/adapters/
├── urssaf_client.py      # httpx → API Tiers de Prestation (OAuth2 REST)
├── bridge_client.py      # httpx → Bridge API (PSD2 bank data)
├── sheets_adapter.py     # gspread → Google Sheets
├── pdf_generator.py      # WeasyPrint
└── email_notifier.py     # aiosmtplib
```

**Why:** L'architecture initiale était basée sur des hallucinations. La recherche factuelle montre que des APIs officielles existent et que le scraping est illégal pour les données bancaires.

**How to apply:** Remplacer tous les adapters Playwright par des clients httpx REST. Mettre à jour les agents, rules, et CLAUDE.md.
