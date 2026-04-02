---
name: Decisions locked 2026-03-18
description: 7 architectural decisions validated by Jules for SAP-Facture MVP
type: project
---

All 7 decisions locked on 2026-03-18:

- **D1**: URSSAF polling 4h → YES
- **D2**: SMTP SAP-Facture → YES
- **D3**: CREE → EN_ATTENTE immédiat → YES (default, Jules asked to clarify, went with immediate)
- **D4**: CLI FIRST (pas web) — Jules a besoin de facturer ASAP via CLI
- **D5**: Indy Playwright (pas Swan API) → DECIDED previously
- **D6**: Lettrage MANUEL en MVP — pas d'auto-lettrage pour commencer
- **D7**: PDF factures = priorité #1, stockage Google Drive

**Why:** Jules veut facturer le plus vite possible. CLI-first change la roadmap: web dashboard passe en Phase 2.
**How to apply:** Tout sprint planning doit prioriser le CLI de facturation. Lettrage auto = Phase 2+. Web UI = Phase 2+.
