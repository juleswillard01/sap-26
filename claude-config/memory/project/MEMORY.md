# Memory Index

## User
- [user_jules.md](user_jules.md) — Jules Willard, micro-entrepreneur SAP cours particuliers

## Project
- [project_sap_facture.md](project_sap_facture.md) — SAP-Facture reset, SCHEMAS.html = source de verite, BMAD fresh start
- [project_sheets_adapter_decisions.md](project_sheets_adapter_decisions.md) — Decisions QCM SheetsAdapter CRUD: Polars, cache, circuit breaker, queue worker, sap init
- [project_architecture_corrections.md](project_architecture_corrections.md) — Corrections post-recherche: API URSSAF REST, Bridge PSD2, pas de Playwright scraping
- [project_sap_facture_role.md](project_sap_facture_role.md) — SAP-Facture = orchestrateur (PAS facturation), AIS fait la facturation, Indy fait la banque
- [project_indy_login_validated.md](project_indy_login_validated.md) — Indy login + API reverse-engineering valides (MPP-64 DONE), 14/16 endpoints REST, Firebase Auth JWT
- [project_decisions_locked.md](project_decisions_locked.md) — 7 architectural decisions validated by Jules for SAP-Facture MVP
- [project_bmad_custom_setup.md](project_bmad_custom_setup.md) — BMAD v2 Agent Teams setup

## Feedback
- [feedback_no_redo_clarification.md](feedback_no_redo_clarification.md) — Ne pas reproposer des phases deja terminees, biais vers l'action
- [feedback_schemas_source_of_truth.md](feedback_schemas_source_of_truth.md) — SCHEMAS.html intouchable, toute architecture doit s'aligner dessus
- [feedback_no_swan_api.md](feedback_no_swan_api.md) — Indy banking via REST httpx (reverse-engineered), pas Swan/Bridge/Playwright
- [feedback_golden_workflow_strict.md](feedback_golden_workflow_strict.md) — Golden workflow obligatoire, pas de vibecoding, chaque etape validee
- [feedback_playwright_own_tools.md](feedback_playwright_own_tools.md) — Playwright pour automatiser AIS + Indy (SES outils), pas d'API URSSAF directe ni Bridge
