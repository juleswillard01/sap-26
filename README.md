# SAP-Facture

Plateforme de facturation URSSAF pour micro-entrepreneurs en services a la personne.

## Stack

- **Backend** : FastAPI, SQLAlchemy, SQLite
- **Frontend** : Jinja2, Tailwind CSS, HTMX
- **Integrations** : API URSSAF (OAuth 2.0), Swan (GraphQL)
- **PDF** : WeasyPrint
- **Scheduler** : APScheduler (polling URSSAF, rappels, sync bancaire)

## Demarrage rapide

```bash
cp .env.example .env
pip install -e ".[dev]"
python -m app.main
# ou avec Docker
docker compose up -d
```

L'app tourne sur `http://localhost:8000`.

## Tests

```bash
pytest tests/ --cov=app
```

## Documentation

| Fichier | Contenu |
|---------|---------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Design technique complet (stack, DB, API, securite) |
| [GETTING-STARTED-DEV.md](docs/GETTING-STARTED-DEV.md) | Guide dev phase par phase |
| [UX-SPECIFICATIONS.md](docs/UX-SPECIFICATIONS.md) | Specifications UX/UI |
| [SPRINT-PLAN.md](docs/SPRINT-PLAN.md) | Planning sprint, estimation effort |
| [SETUP.md](docs/SETUP.md) | Setup dev et production |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deploiement VPS, Nginx, SSL |
| [schemas/](docs/schemas/) | Diagrammes Mermaid (flux, donnees, API, scope MVP) |
