# 📚 Index Architecture - SAP-Facture

**Créé le**: 14 Mars 2026
**Version**: 1.0
**Status**: ✅ Complet et prêt pour développement

---

## 🎯 Commence Par Où?

### Si tu as **5 minutes** 
→ `ARCHITECTURE-RESUME-EXEC.md`

### Si tu dois **valider** l'architecture
→ `VALIDATION-ARCHITECTURE.md`

### Si tu vas **coder**
→ `GETTING-STARTED-DEV.md`

### Si tu veux **tous les détails**
→ `ARCHITECTURE.md` (2358 lignes)

### Si tu es **perdu**
→ `02-ARCHITECTURE.md` (ce guide de navigation)

---

## 📄 Documents d'Architecture

| # | Document | Longueur | Pour Qui | Objectif |
|---|----------|----------|----------|----------|
| 1 | **ARCHITECTURE-RESUME-EXEC.md** | 5 min | Tous | Vue d'ensemble + décisions clés |
| 2 | **VALIDATION-ARCHITECTURE.md** | 10 min | Jules | Checklist de validation |
| 3 | **GETTING-STARTED-DEV.md** | 20 min | Devs | Phase 0-4 du développement |
| 4 | **ARCHITECTURE.md** | 30 min | Architects | Design technique complet |
| 5 | **02-ARCHITECTURE.md** | 3 min | Navigateurs perdus | Guide de navigation |

---

## 🗺️ Content Quick Reference

### Stack Technologique
- **Backend**: FastAPI 0.109+ (Async ASGI web framework)
- **Database**: SQLite 3.40+ (File-based, zero complexity)
- **Templates**: Jinja2 3.1+ (Server-side rendering)
- **PDF**: weasyprint 59+ (HTML → PDF conversion)
- **CLI**: Typer 0.9+ (Command-line interface)
- **HTTP Client**: httpx 0.25+ (Async HTTP, OAuth)
- **GraphQL**: gql 3.4+ (Swan API queries)
- **Encryption**: cryptography 42+ (Fernet symmetric)
- **Task Scheduler**: APScheduler 3.10+ (Cron-like jobs)

📌 Voir `ARCHITECTURE.md` → Section "Stack Technologique" pour justification détaillée

### Architecture System
- **Couche Web**: Routes FastAPI + Jinja2 templates
- **Couche Métier**: Services (InvoiceService, ClientService, etc.)
- **Couche Données**: SQLAlchemy repositories
- **Couche Intégrations**: URSSAF client, Swan client, PDF generator

📌 Voir `ARCHITECTURE.md` → Section "Architecture Système"

### Database Schema
- **users**: Info Jules (SIREN, NOVA, API keys)
- **clients**: Particuliers enregistrés URSSAF
- **invoices**: Factures créées
- **payment_requests**: Demandes de paiement URSSAF
- **bank_transactions**: Transactions Swan/Indy
- **payment_reconciliations**: Matches URSSAF ↔ Bank
- **audit_logs**: Compliance + sécurité
- **email_queue**: Notifications (Phase 2: async)

📌 Voir `ARCHITECTURE.md` → Section "Modèle de Données"

### API Endpoints
- `GET /` — Dashboard (invoice list)
- `GET/POST /invoices` — Create/list invoices
- `POST /invoices/{id}/submit` — Submit to URSSAF
- `GET /invoices/{id}/pdf` — Download PDF
- `GET/POST /clients` — Client CRUD
- `GET /reconciliation` — Bank matching view
- `POST /sync/*` — Manual sync triggers
- `GET /health` — Health check

📌 Voir `ARCHITECTURE.md` → Section "Design API"

### URSSAF Integration
- **OAuth 2.0**: Client credentials flow
- **Register particulier** (client): POST /particuliers/register
- **Submit invoice**: POST /payment-requests
- **Poll status**: GET /payment-requests/{id}

📌 Voir `ARCHITECTURE.md` → Section "Intégrations Externes" + `GETTING-STARTED-DEV.md` → Phase 2

### Swan API Integration
- **GraphQL** endpoint
- **Get transactions**: Query recent bank transactions
- **Get account balance**: Current balance
- **Date range**: Last 7-30 days

📌 Voir `ARCHITECTURE.md` → Section "Intégrations Externes"

### Sécurité
- **Secrets**: `.env` file, Fernet encryption at rest
- **Validation**: Pydantic models on all inputs
- **Audit**: Toutes mutations loggées (who/when/what)
- **RGPD**: Soft delete + pseudonymisation

📌 Voir `ARCHITECTURE.md` → Section "Architecture de Sécurité"

### MVP Scope (Semaine 1)
- ✅ Client registration
- ✅ Invoice creation + PDF
- ✅ URSSAF submission
- ✅ Status tracking
- ✅ Bank reconciliation view
- ✅ Email reminders
- ✅ CLI commands
- ❌ Google Sheets auto-sync (Phase 2)
- ❌ Multi-user auth (Phase 2)

📌 Voir `ARCHITECTURE.md` → Section "Scope MVP vs Phases Futures"

---

## 🚀 Développement Day-by-Day

| Jour | Phase | Objectif | Fichier Lire |
|------|-------|----------|---|
| 1-2 | Phase 0-1 | Setup + Database | `GETTING-STARTED-DEV.md` Phase 0-1 |
| 2-3 | Phase 2 | URSSAF Integration | `GETTING-STARTED-DEV.md` Phase 2 |
| 3-4 | Phase 3 | Web Routes + PDF | `GETTING-STARTED-DEV.md` Phase 3 |
| 4-5 | Phase 4+ | Bank Reconciliation | `ARCHITECTURE.md` → Bank Reconciliation |
| 5-6 | Testing | Unit + Integration tests | `GETTING-STARTED-DEV.md` Phase 4 |
| 6-7 | Deploy | VPS + Nginx | `ARCHITECTURE.md` → Deployment |

---

## ⚠️ Risques Principaux

| # | Risque | Probabilité | Mitigation |
|---|--------|-----------|-----------|
| 1 | Format URSSAF complexe | HAUTE | Test sandbox strict + validation payload |
| 2 | OAuth token expire | MOYENNE | Auto-refresh + retry logic |
| 3 | Client timeout 48h | MOYENNE | Email reminder T+36h |
| 4 | Swan API down | BASSE | Graceful degradation |
| 5 | SIREN invalide | BASSE | Validate format + clear error |

📌 Voir `ARCHITECTURE.md` → Tableau "Risques et Mitigations"

---

## ✅ Validation Checklist

Avant de coder, assure-toi que tu as:

- [ ] Validé architecture avec Jules (`VALIDATION-ARCHITECTURE.md`)
- [ ] Compris les 4 objectifs principaux
- [ ] Vérifié stack technologique
- [ ] Confirmé timeline 1 semaine
- [ ] Identifié risques + mitigations
- [ ] Revu les décisions clés (ADRs)
- [ ] Setup dev local (Docker, poetry)

---

## 🎓 Documents Préalables (Context)

**These provide context but are NOT architecture**:

- `00-README.md` — Project overview par Sarah
- `01-analyse-besoins-initiale.md` — Initial analysis
- `02-priorisation-scenarios.md` — User workflows
- `03-questions-clarification.md` — Requirements questions
- `QUESTIONNAIRE-JULES.txt` — Jules's answers
- `SYNTHESE-PHASE-ANALYSE.md` — Analysis summary

---

## 📞 Questions?

**Sur architecture générale**:
→ Winston (System Architect)

**Sur code/implémentation**:
→ Code agent / Dev senior

**Sur product/requirements**:
→ Sarah (Product Owner)

---

## 🎯 Success Criteria

L'architecture est "good" si:

✅ Dev peut coder sans poser questions
✅ Design est pragmatique (KISS)
✅ Sécurité by design
✅ Extensible pour Phase 2
✅ Déployable en 1 semaine
✅ MVP utilisable par Jules

---

## 📊 Architecture Metrics

| Métrique | Valeur | Target |
|----------|--------|--------|
| **Lines of Architecture Docs** | 2358 (ARCHITECTURE.md) | ✅ Complet |
| **Tech Stack Size** | 9 dépendances core | ✅ Minimal |
| **Database Entities** | 8 tables | ✅ Couvrir MVP |
| **API Endpoints** | 15+ routes | ✅ Enough for MVP |
| **Development Timeline** | 7 jours | ✅ Realistic |
| **Deployment Complexity** | Low (Docker + VPS) | ✅ Simple |

---

## 🔄 Version History

| Version | Date | Changes |
|---------|------|---------|
| **1.0** | 14 Mar 2026 | Initial architecture complete |

---

## 📋 Checklist Avant Kick-Off

- [ ] Architecture `ARCHITECTURE.md` révisée
- [ ] Résumé exécutif `ARCHITECTURE-RESUME-EXEC.md` approuvé
- [ ] Validation Jules `VALIDATION-ARCHITECTURE.md` complétée
- [ ] Dev ready guide `GETTING-STARTED-DEV.md` lu
- [ ] Stack technologique validée
- [ ] Timeline confirmée
- [ ] Risques identifiés + mitigations
- [ ] Credentials URSSAF disponibles
- [ ] Swan API access confirmé
- [ ] Dev environment setup possible

---

**Status**: ✅ Complet et prêt pour développement

**Next**: Démarrer avec `GETTING-STARTED-DEV.md`

