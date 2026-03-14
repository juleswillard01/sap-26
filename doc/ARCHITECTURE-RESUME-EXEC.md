# Résumé Exécutif - Architecture SAP-Facture

**Pour**: Jules Willard (Micro-entrepreneur SAP)
**De**: Winston (Architect BMAD)
**Date**: 14 Mars 2026
**Statut**: ✅ Prêt à coder (Semaine 1)

---

## 🎯 Le Plan en 30 Secondes

SAP-Facture est une **plateforme de facturation intégrée URSSAF** que tu vas construire en **1-2 semaines**.

**Architecture**: FastAPI (backend) + SQLite (DB) + Jinja2 templates (UI) + CLI Typer (automation)

**Stack**: Python, async HTTP, weasyprint (PDF), cryptography (secrets)

**Déploiement**: Docker + VPS Linux simple (pas Kubernetes)

**Filosofie**: KISS - résoudre ton problème réel sans over-engineering

---

## ✅ Ce qu'on Peut Faire (MVP - Semaine 1)

### Fonctionnalités Core
- ✅ **Créer factures** — Formulaire web simple
- ✅ **Générer PDF** — Professional avec ton logo
- ✅ **Soumettre URSSAF** — Via API OAuth
- ✅ **Tracker paiements** — Dashboard + status auto-sync (4h)
- ✅ **Rapprocher banque** — Swan API ↔ URSSAF match
- ✅ **Reminders email** — T+36h si client pas validé
- ✅ **CLI commands** — Automation: `sap submit`, `sap sync`, etc.
- ✅ **Export CSV** — Pour Google Sheets (manual upload)

### Infrastructure
- ✅ Sécurité: Secrets chiffrés, audit trail complet
- ✅ RGPD: Suppression client, pseudonymisation
- ✅ Monitoring: Logs structurés, health checks

---

## ❌ Ce qu'on Fait PAS en MVP (Phase 2)

- ❌ UI super polished (c'est fonctionnel, pas beau)
- ❌ Multi-user (juste toi pour le moment)
- ❌ Google Sheets auto-sync (CSV export, tu upload manuel)
- ❌ Background task queue (SMTP sync = OK pour MVP)
- ❌ Attestations fiscales (Phase 2)

---

## 🛠️ Stack Technique

| Couche | Tech | Pourquoi |
|--------|------|---------|
| **Web Framework** | FastAPI | Async, type-safe, Python (tes skills) |
| **Database** | SQLite | Simple, file-based, parfait pour 50 factures/mois |
| **Templates** | Jinja2 | Server-side rendering, déploiement simple |
| **PDF** | weasyprint | HTML → PDF, logo embedding facile |
| **CLI** | Typer | Click wrapper, commandes simples |
| **HTTP Client** | httpx | Async, OAuth 2.0 support |
| **GraphQL** | gql | Swan API queries |
| **Crypto** | cryptography.Fernet | Encrypt secrets at rest |
| **Task Scheduling** | APScheduler | Cron-like polling |
| **Server** | Nginx + systemd | Reverse proxy + auto-restart |

**Pas de**: Node.js, React, PostgreSQL, Redis, Kubernetes, Docker Swarm

---

## 📊 Architecture 50 000 Pieds

```
User (Jules)
    ↓
[Web Browser] ← FastAPI web app (SSR)
    ↓
[Services Layer] ← Business logic
    ↓
[Repositories] ← SQLite ORM queries
    ↓
[External APIs]
├─ URSSAF (OAuth + invoice submission)
├─ Swan (GraphQL, bank transactions)
└─ SMTP (email)
```

**Principe**: Une seule couche entre UI et données = facile à comprendre + modifier.

---

## 🔒 Sécurité

**Secrets Management**:
- `.env` file (NEVER commité)
- Validated at startup (fail-fast)
- Encrypted in database (Fernet cipher)

**Audit Trail**:
- Toutes les mutations loggées (qui/quand/quoi)
- Stockées en DB pour forensics

**RGPD**:
- Suppression client = soft delete + pseudonymisation
- Données sensibles chiffrées

**Validation**:
- Pydantic models pour tous les inputs
- URSSAF payload checked strictement

---

## 📁 Structure Répertoire (Simple)

```
sap-facture/
├── app/
│   ├── web/                  # Jinja2 templates + routes
│   ├── services/             # Business logic
│   ├── models/               # SQLAlchemy ORM
│   ├── integrations/         # URSSAF, Swan, PDF, Email
│   ├── cli/                  # Typer commands
│   └── tasks/                # Periodic jobs (APScheduler)
├── alembic/                  # DB migrations
├── tests/                    # pytest
├── docker-compose.yml
└── Dockerfile
```

**Total files**: ~40-50 fichiers Python

---

## 🚀 Timeline Réaliste (Semaine 1)

**Jour 1-2**: Setup + Database
- Repo + poetry config
- SQLAlchemy models + migrations
- Docker dev environment

**Jour 2-3**: Core URSSAF Integration
- OAuth authentication
- Client registration
- Invoice submission endpoint

**Jour 3-4**: Web UI + PDF
- Dashboard (list invoices)
- Invoice creation form
- PDF generation with logo

**Jour 4-5**: Bank Reconciliation + Polling
- Swan API client
- Status polling task
- Reconciliation matching

**Jour 5-6**: Polish + CLI + Email
- Email reminders
- CLI commands
- Error handling + logging

**Jour 6-7**: Testing + Docs
- Unit tests (core flows)
- Integration tests (URSSAF sandbox)
- Deployment script

**Jour 7**: Deploy + Validate
- VPS setup
- Nginx config
- Test en sandbox URSSAF

---

## ⚠️ Risques Identifiés (à surveiller)

| Risque | Solution |
|--------|----------|
| **Format URSSAF complexe** | Validation stricte, test sandbox d'abord |
| **Token OAuth expire** | Auto-refresh, retry logic |
| **Client timeout (48h)** | Email reminder T+36h |
| **Swan API down** | Graceful degradation, manual override |
| **SIREN invalide** | Validate format, clear errors |

**Mitigation générale**: Logs détaillés + alertes email pour toute erreur.

---

## 💡 Décisions Clés (Justifiées)

### 1. SQLite, pas PostgreSQL
- **Pourquoi**: 50 factures/mois = overkill PostgreSQL, plus simple à déployer
- **Later**: Facile de migrer (Pattern Repository prêt)

### 2. FastAPI SSR, pas React SPA
- **Pourquoi**: Tu connais FastAPI, pas de build step, déploiement simplifié
- **UX**: Moins snappy (full page loads), acceptable pour admin dashboard

### 3. Async background submission
- **Pourquoi**: URSSAF API lent (3-10s), user doit avoir feedback immédiat
- **State**: DRAFT → SUBMITTED (background)

### 4. CSV export MVP, Google Sheets Phase 2
- **Pourquoi**: CSV = 95% as useful, zero complexity
- **Manual**: Tu upload CSV manuelquement si besoin (1 min par semaine)

### 5. Monolith (pas microservices)
- **Pourquoi**: Solo dev + solo user = KISS
- **Scaling**: Vertical si needed, horizontal later

---

## 🎓 Comment On Avance

### Semaine 1 (Dev)
```bash
$ cd sap-facture
$ docker-compose up                    # Dev environment
$ poetry install                       # Dependencies
$ alembic upgrade head                 # Create tables
$ python app/integrations/init_urssaf_sandbox.py  # Configure URSSAF
```

### Jour-par-jour
- Commit atomiques: `feat(invoice): add pdf generation`
- Tests écrits avant code (TDD)
- Logs à chaque étape critiques

### Semaine 2 (Sandbox Testing)
- Test chaque endpoint sur URSSAF sandbox
- Envoyer vraies factures test
- Vérifier statuts update automatiquement

### Semaine 3 (VPS + Production)
- Deploy sur VPS
- Utiliser vraies credentials URSSAF
- Premiers vraies clients

---

## 📚 Documentation Fournie

| Document | Contenu |
|----------|---------|
| **ARCHITECTURE.md** | Complet (2358 lignes) — tech stack, API design, intégrations, sécurité |
| **Ce document** | Résumé exécutif (tu es là) |
| **CODE_GUIDE.md** | (À créer) Examples de code pour chaque pattern |
| **DEPLOYMENT.md** | (À créer) VPS + Nginx + SSL step-by-step |
| **TESTING.md** | (À créer) Unit + integration test strategy |

---

## ✋ Prochaines Étapes (TOI)

1. **Revise cette architecture**
   - Stack OK?
   - Design choices sensées?
   - Questions sur intégrations?

2. **Valide avec ton équipe technique**
   - Y a-t-il des gaps?
   - Dépendances manquantes?

3. **Prépare tes credentials**
   - ZIP URSSAF (OAuth)
   - API key Swan
   - Clé d'encryption (on génère ensemble)

4. **Schedule kick-off dev**
   - Start coding ou delegate?
   - Timeline réaliste?

---

## 🤔 Questions Probables

**Q: Est-ce qu'on peut passer directement à la prod (pas sandbox)?**
A: Fortement déconseillé. URSSAF sandbox = free testing. Tester d'abord, puis prod.

**Q: Et si j'ai besoin de multi-user plus tard?**
A: Architecture ready (Repository pattern). Phase 2 = add RBAC + tenant isolation.

**Q: Google Sheets automatique dans MVP?**
A: Non, CSV export = user upload manual. MVP = 1 semaine, scope tight. Phase 2 = Google Sheets API.

**Q: Combien de réquêtes par seconde ça peut supporter?**
A: SQLite ~100-500 RPS (depending hardware). Pour 50 factures/mois = zéro problème.

**Q: Et si URSSAF API change?**
A: URSSAFClient = abstraction. Changements = localisés à 1 fichier.

**Q: Backup/disaster recovery?**
A: SQLite = file. Daily copy to backup. Phase 2 = PostgreSQL + automated backups.

---

## 🎯 Succès Définition

SAP-Facture MVP est "prêt" quand:

- ✅ Tu peux créer une facture via web UI
- ✅ PDF généré avec ton logo
- ✅ Soumis à URSSAF (réellement, en sandbox)
- ✅ Client reçoit email de validation
- ✅ Dashboard affiche statut URSSAF (mis à jour auto)
- ✅ Bank transactions de Swan affichées
- ✅ Tu peux exporter CSV pour Google Sheets
- ✅ CLI commands fonctionnent (submit, sync, reconcile)
- ✅ Logs détaillés en cas d'erreur
- ✅ Déployé sur ton VPS, accessible via https://sap.ton-domaine.fr

---

## 📞 Contact & Questions

**Pour clarifications sur architecture**:
→ Winston (System Architect)

**Pour implémentation**:
→ Code agent (BMAD development)

**Pour Product/Requirements**:
→ Sarah (Product Owner)

---

**Status**: ✅ Architecture approuvée, prête pour development

**Next checkpoint**: Validation Jules + kick-off dev

---

*"Une bonne architecture, c'est celle qui résout le problème d'aujourd'hui sans bloquant demain. SAP-Facture est juste ça."* — Winston

