---
name: SAP-Facture project status
description: SAP-Facture project reset - SCHEMAS.html is the source of truth, prototype v1 archived, BMAD fresh start
type: project
---

SAP-Facture: plateforme facturation URSSAF pour micro-entrepreneurs SAP (cours particuliers).

**Status (2026-03-15)**: Projet reset. Prototype v1 archive. BMAD repart de Phase 1 avec SCHEMAS.html comme source de verite.

**Architecture cible (SCHEMAS.html)**:
- Backend data: Google Sheets (8 onglets via gspread/Sheets API v4)
- Frontend: FastAPI SSR + Jinja2 + Tailwind + iframes Sheets
- CLI: Click
- Integrations: URSSAF OAuth2 REST, Swan GraphQL, SMTP, Google Drive API
- Services: InvoiceService, ClientService, PaymentTracker, BankReconciliation, NotificationService, NovaReporting

**Jules profile**:
- Micro-entrepreneur solo, cours particuliers
- SIREN: 991552019, NOVA: SAP991552019
- 15-50 factures/mois, 4-10 clients, 50-200 EUR par facture

**BMAD workflow**: Repart de Phase 1 (product-brief) base sur SCHEMAS.html

**Why:** Le prototype v1 (FastAPI/SQLite) divergeait de la maquette SI validee. Jules veut un vrai cahier des charges technique/fonctionnel produit par BMAD avant de coder.

**How to apply:** SCHEMAS.html = intouchable. BMAD produit PRD, architecture, specs a partir des schemas. L'analyste propose les schemas fonctionnels, l'architecte produit les specs techniques.
