# Phase 3 — Documentation Index

**Phase**: MVP → Production Ready
**Statut**: In Progress
**Dates**: Semaines 2-4 de développement

---

## Documents

### 1. [01-dev-environment.md](01-dev-environment.md)
**Sujet**: Configuration locale (Docker Compose, dev tools, debug)
**Audience**: Développeurs
**Longueur**: ~900 lignes

Contient:
- Docker Compose setup (FastAPI + services)
- IDE configuration (VS Code, PyCharm)
- Git workflow et pre-commit hooks
- Local debugging + testing
- Database seeding (données test)

### 2. [02-deployment-plan.md](02-deployment-plan.md)
**Sujet**: Infrastructure déploiement (VPS, Docker, SSL, monitoring)
**Audience**: DevOps, Infrastructure team
**Longueur**: ~1250 lignes

Contient:
- Architecture 3 environnements (Dev/Staging/Prod)
- VPS setup (Ubuntu 22.04, firewall, systemd)
- Docker build + push to registry
- Nginx reverse proxy + Let's Encrypt
- Health check + JSON logging + Prometheus
- Backup strategy (Google Sheets versioning)
- Security (UFW, Fail2ban, SSH key-only)
- Deployment scripts + rollback
- Disaster recovery procedures
- ADRs (Architecture Decision Records)

### 2.5. [02-system-architecture.md](../../.claude/specs/02-system-architecture.md) **← NEW BLUEPRINT**
**Sujet**: Architecture technique détaillée (layers, components, APIs, patterns)
**Audience**: Tous les développeurs, Tech Lead
**Longueur**: ~1250 lignes
**Qualité Score**: 95/100

Contient:
- Architecture haute niveau (diagrammes)
- 5 couches (Présentation, API, Métier, Persistance, Intégrations)
- SheetsAdapter design + patterns
- Modèles de données Pydantic détaillés
- Endpoints API complète (/api/v1/*)
- Intégrations externes (URSSAF, Swan, SMTP)
- Déploiement Nginx + Docker
- Résilience (circuit breaker, retry, health checks)
- Sécurité (validation, rate limiting, secrets)
- Performance & caching
- Monitoring (Prometheus, logs JSON, Sentry)
- Roadmap implémentation (3 phases)

**Pour commencer l'implémentation**: Lire ce document en entier.

### 3. [gate-check.md](gate-check.md)
**Sujet**: Gate criteria avant production
**Audience**: Tech Lead, Product Manager
**Longueur**: ~800 lignes

Contient:
- Functional completeness checklist
- Performance criteria
- Security review
- User acceptance testing (UAT)
- SLA definition
- Go/No-go decision matrix

### 4. [test-strategy.md](test-strategy.md)
**Sujet**: Test coverage, strategies, CI/CD
**Audience**: QA, Developers
**Longueur**: ~1400 lignes

Contient:
- Unit test strategy (pytest)
- Integration tests (Google Sheets API)
- E2E tests (full workflow)
- Performance benchmarks
- Security testing
- Monitoring & alerting strategy
- CI/CD pipeline (GitHub Actions)

---

## Lecteur Recommandé

### Pour **Jules** (Product Owner):
1. Lire **gate-check.md** (comprendre critères MVP)
2. Consulter **02-deployment-plan.md** (section "Coûts" + "Estimation temps")

### Pour **Développeurs**:
1. **02-system-architecture.md** (blueprint technique complet) ← Commencer ici
2. **01-dev-environment.md** (setup local + Docker)
3. **test-strategy.md** (coverage requirements)
4. **02-deployment-plan.md** (sections 4-5: déploiement et monitoring)

### Pour **DevOps/Infrastructure**:
1. **02-deployment-plan.md** (complet)
2. **test-strategy.md** (section CI/CD)

### Pour **QA/Testing**:
1. **test-strategy.md** (complet)
2. **gate-check.md** (acceptance criteria)

---

## Timeline Phase 3

```
Semaine 2 (en cours):
- [ ] Feature development (Invoices, Clients, Reconciliation)
- [ ] Unit tests (80% coverage target)
- [ ] Local Docker Compose testing

Semaine 3:
- [ ] Integration testing (Google Sheets API)
- [ ] VPS provisioning (Staging + Prod)
- [ ] Deployment pipeline setup (Docker registry, systemd)
- [ ] SSL certificate provisioning (Let's Encrypt)
- [ ] Staging deployment + 1 week testing

Semaine 4:
- [ ] Production deployment
- [ ] 24h monitoring post-launch
- [ ] Fix critical issues
- [ ] Documentation finalization
- [ ] Team training (deployment, rollback)

Post-MVP:
- [ ] Weekly backups
- [ ] Monthly security updates
- [ ] Quarterly secret rotation
- [ ] Annual infrastructure review
```

---

## Artefacts Clés

### Code
- `Dockerfile` (multi-stage build)
- `docker-compose.yml` (dev environment)
- `requirements.txt` (Python dependencies)

### Infrastructure as Code
- `/etc/systemd/system/sap-*.service` (service files)
- `/etc/nginx/sites-available/sap-*.conf` (Nginx config)
- `deploy.sh` (deployment automation)

### Configuration
- `.env.local` (dev secrets, git-ignored)
- `.env.staging` (staging secrets, git-ignored)
- `.env.production` (prod secrets, git-ignored)

### Secrets (Secured)
- Google Service Account JSON
- URSSAF OAuth2 credentials
- Swan API key
- SMTP credentials
- Fernet encryption key

---

## État Courant

| Aspect | Status |
|--------|--------|
| **Architecture Design** | ✅ Complete (SCHEMAS.html) |
| **Component Specification** | ✅ Complete (04-system-components.md) |
| **Google Sheets Feasibility** | ✅ Complete (10-google-sheets-feasibility.md) |
| **Development Environment** | ✅ Complete (01-dev-environment.md) |
| **Deployment Plan** | ✅ Complete (02-deployment-plan.md) |
| **System Architecture Doc** | ✅ Complete (02-system-architecture.md) **← NEW** |
| **Test Strategy** | ✅ Complete (test-strategy.md) |
| **Gate Criteria** | ✅ Complete (gate-check.md) |
| **Code Implementation** | 🟡 Starting (Foundation sprint) |
| **Staging Deployment** | ⏳ Pending (Week 3-4) |
| **Production Launch** | ⏳ Scheduled Week 4 |

---

## Points de Contact

### Infrastructure Setup
Faire référence à **02-deployment-plan.md**:
- Section "Préparation VPS" pour setup initial
- Section "Procédure de Déploiement" pour deployment
- Section "Sécurité Infrastructure" pour hardening

### Monitoring Setup
Faire référence à **02-deployment-plan.md**:
- Section "Monitoring et Alerting" pour health check + logs
- Appendix A pour scripts de monitoring

### Disaster Recovery
Faire référence à **02-deployment-plan.md**:
- Section "Backup et Disaster Recovery" pour procedures
- Appendix B (ADRs) pour contexte décisions

---

## Document Versions

| Document | Version | Date | Auteur |
|----------|---------|------|--------|
| 01-dev-environment.md | 1.0 | Mar 15, 2026 | Winston |
| 02-deployment-plan.md | 1.0 | Mar 15, 2026 | Winston |
| gate-check.md | 1.0 | Mar 15, 2026 | Winston |
| test-strategy.md | 1.0 | Mar 15, 2026 | Winston |

---

**Next Review**: End of Week 3 (Mar 22, 2026)

