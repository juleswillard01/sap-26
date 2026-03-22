---
name: project-config
description: >
  Configuration services externes SAP-Facture. TRIGGER : setup Google Sheets
  service account, config AIS credentials, setup Indy export, SMTP Gmail,
  Playwright chromium install.
---

# Project Config

Setup guide for external services.

## Google Sheets

- Service account JSON base64 in .env (GOOGLE_SERVICE_ACCOUNT_B64)
- Spreadsheet ID in .env
- Share spreadsheet with service account email

## AIS (avance-immediate.fr)

- AIS_EMAIL and AIS_PASSWORD in .env
- Playwright chromium: uv run playwright install chromium

## Indy Banking

- INDY_EMAIL and INDY_PASSWORD in .env
- Same Playwright chromium install

## SMTP Gmail

- SMTP_EMAIL and SMTP_PASSWORD (app password) in .env

## Gotchas

- All secrets in .env ONLY, never in code
- .env is in .gitignore
- Use pydantic-settings BaseSettings for validation
