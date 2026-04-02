---
name: Playwright pour automatiser SES propres outils
description: Jules utilise AIS et Indy — Playwright automatise SES comptes, pas de scraping tiers. Ne pas proposer l'API URSSAF directe ni Bridge API.
type: feedback
---

Jules utilise deux plateformes SANS API publique :
- **AIS (app.avance-immediate.fr)** — logiciel facturation SAP à 99€/an. AIS parle à l'API URSSAF pour Jules. Jules ne doit PAS demander une habilitation URSSAF.
- **Indy (app.indy.fr)** — comptabilité/banque. Indy utilise Bridge en interne, mais Jules n'a PAS accès à Bridge directement.

**Playwright headless** automatise les comptes de Jules sur ces deux plateformes. C'est l'automatisation de SES propres outils, pas du scraping de données tierces.

**Why:** J'ai proposé l'API Tiers de Prestation URSSAF directe + Bridge API. Jules m'a corrigé : il ne veut pas parler à l'URSSAF ni à Bridge. Il veut contrôler AIS et Indy via Playwright.

**How to apply:** Toujours proposer Playwright pour AIS et Indy. Ne JAMAIS suggérer l'API URSSAF directe ou Bridge comme alternative. L'architecture est : Playwright → AIS (facturation) + Playwright → Indy (banque) → SheetsAdapter (stockage).
