# SAP-Facture — Orchestrateur Services à la Personne

Orchestrateur Python/FastAPI autour d'[avance-immediate.fr](https://avance-immediate.fr) pour la gestion SAP (Services à la Personne).

## Architecture

```
avance-immediate.fr ──→ Facturation + URSSAF (délégué)
        │
SAP-Facture (ce projet) ──→ Google Sheets (8 onglets backend)
        │                  ──→ Indy Banking (Playwright scraping)
        │                  ──→ Dashboard FastAPI (SSR)
        │                  ──→ CLI (sap sync/reconcile/export)
        │                  ──→ Notifications email (SMTP)
```

## Prérequis

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 18+ (pour Context7 MCP)
- Docker (optionnel)
- Compte Google (Sheets API)
- Compte Indy Banking

## Setup rapide

```bash
git clone <repo-url>
cd sap-facture
make install          # uv sync + playwright install

cp .env.example .env  # Configurer credentials
make test             # Vérifier que tout passe
make dev              # Lancer le serveur dev
```

## CLI

```bash
sap sync              # Synchroniser statuts depuis avance-immediate.fr
sap reconcile         # Lettrage bancaire automatique
sap export            # Export CSV
sap status            # Résumé dashboard
```

## Développement — Golden Workflow

10 agents Claude Code couvrent les 7 étapes :

| Étape | Agents |
|-------|--------|
| CDC | orchestrator, cdc-validator |
| Plan | architect (+ Context7) |
| TDD | tdd-engineer |
| Review | code-reviewer, security-auditor, sheets-specialist |
| Verify | quality-gate-keeper |
| Infra | infra-engineer |
| Refactor | refactor-guide |

## Licence

MIT — Jules Willard — SIREN 991552019
