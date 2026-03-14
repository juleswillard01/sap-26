# 📋 Architecture Technique - SAP-Facture

**Bienvenue!** Ceci est le document **complet** d'architecture technique pour SAP-Facture.

**Si tu as peu de temps**: Lis d'abord `ARCHITECTURE-RESUME-EXEC.md` (5 min).

**Si tu vas coder**: Lis `GETTING-STARTED-DEV.md` et `ARCHITECTURE.md` en parallèle.

---

## 📄 Documents d'Architecture (This Section)

### 1. **ARCHITECTURE-RESUME-EXEC.md** (5 min read)
📌 **COMMENCE PAR CELUI-CI**

Résumé exécutif pour décideurs/sponsors:
- 30-second overview
- Stack technique (table)
- MVP scope vs Phase 2
- Timeline réaliste (Jour-par-jour)
- Décisions clés justifiées
- Risques identifiés

👉 **Lis si**: Tu veux comprendre le plan rapidement sans rentrer dans les détails.

---

### 2. **ARCHITECTURE.md** (30 min read)
📌 **COMPLET + TECHNIQUE**

Document architectural complet (2358 lignes):
- Vue d'ensemble + diagrammes
- Principes architecturaux
- Stack technologique détaillé
- Architecture système (couches, flows)
- Modèle de données SQL complet
- Design API (HTTP + URSSAF + Swan)
- Architecture de sécurité
- Intégrations externes (code examples)
- Structure module + code
- Déploiement (Docker, VPS, Nginx, systemd)
- Performance + scalabilité
- Fiabilité + monitoring
- Scope MVP vs Phases futures
- ADRs (Architecture Decision Records)

👉 **Lis si**: Tu es dev/architect et tu vas implémenter.

---

### 3. **GETTING-STARTED-DEV.md** (Day-by-day guide)
📌 **FOR DEVELOPERS - STEP-BY-STEP**

Guide pratique de démarrage:
- Phase 0: Setup initial (30 min)
- Phase 1: Database + Models (1 jour)
- Phase 2: URSSAF Integration (1 jour)
- Phase 3: Web Routes (1 jour)
- Phase 4: Testing Strategy
- Checklist de démarrage
- Commandes utiles

👉 **Lis si**: Tu vas commencer à coder demain.

---

## 🗺️ Navigation Rapide

### Si tu es...

**🛍️ Product Owner / Sponsor**
→ Lis: `ARCHITECTURE-RESUME-EXEC.md`

**👨‍💻 Developer qui va coder**
→ Lis: `GETTING-STARTED-DEV.md` + `ARCHITECTURE.md`

**🏗️ System Architect**
→ Lis: `ARCHITECTURE.md` en entier + ADRs

**🧪 QA / Tester**
→ Section: "Phase 4: Testing Strategy" dans `GETTING-STARTED-DEV.md`

**🚀 DevOps / SRE**
→ Section: "Déploiement et Infrastructure" dans `ARCHITECTURE.md`

---

## ✅ Checklist de Compréhension

Avant de coder, tu dois pouvoir répondre:

**Architecture Level**:
- [ ] Quelle est la différence entre FastAPI SSR et SPA React?
- [ ] Pourquoi SQLite et pas PostgreSQL pour MVP?
- [ ] Comment fonctionne le flow URSSAF (submit → validate → pay)?
- [ ] Quel est le rôle de Swan API?
- [ ] Où les secrets (URSSAF keys) sont stockés?

**Implementation Level**:
- [ ] Quelle est la structure du répertoire?
- [ ] Qu'est-ce qu'une migration Alembic?
- [ ] Comment un invoice passe de DRAFT → SUBMITTED → PAYÉ?
- [ ] Où se trouve le code URSSAF client?
- [ ] Comment générer un PDF invoice?

**Deployment Level**:
- [ ] Qu'est-ce que docker-compose?
- [ ] Comment Nginx est utilisé?
- [ ] Où est le `.env` file?
- [ ] Comment les secrets sont chiffrés?

---

## 📊 Architecture en 1 Minute

```
User (Jules)
    ↓
[Web Browser] ← FastAPI (SSR)
    ↓
[Database: SQLite] ← ORM (SQLAlchemy)
    ↓
[Services] ← Business Logic
    ↓
[External APIs]
├─ URSSAF (OAuth + invoice submit)
├─ Swan (GraphQL, bank sync)
└─ SMTP (email notifications)
```

**Philosophie**: Monolith simple, pas microservices. SQLite OK pour MVP. FastAPI SSR = moins de complexité que SPA.

---

## 🔄 Progression Recommandée

**Jour 1-2**:
- Lis `ARCHITECTURE-RESUME-EXEC.md` ← comprends le plan
- Setup local (`GETTING-STARTED-DEV.md` Phase 0)
- Créer DB schema (Phase 1)

**Jour 2-3**:
- Intégration URSSAF (Phase 2)
- Web routes basiques (Phase 3)

**Jour 3-5**:
- PDF generation
- Bank reconciliation
- Email notifications

**Jour 5-7**:
- Testing
- CLI commands
- Deployment

---

## ❓ Questions Fréquentes

**Q: Par où je commence?**
A: `ARCHITECTURE-RESUME-EXEC.md` (5 min) + `GETTING-STARTED-DEV.md` Phase 0.

**Q: Je suis pas sûr du design?**
A: Lis les ADRs dans `ARCHITECTURE.md` — chaque décision est justifiée.

**Q: Comment tester en sandbox URSSAF?**
A: Voir section "URSSAF Integration" dans `ARCHITECTURE.md`.

**Q: Et si je dois ajouter une feature?**
A: Pattern: Repository → Service → Route. Voir examples dans `ARCHITECTURE.md`.

**Q: Quel est le risque principal?**
A: Format URSSAF API complexe. Mitigation: test sandbox d'abord, validation stricte.

---

## 📞 Support & Questions

**Sur architecture générale**:
→ Winston (System Architect)

**Questions de code**:
→ Code agent / Senior dev

**Questions produit**:
→ Sarah (Product Owner)

---

## 🎯 Success Criteria

Architecture est "bonne" si:

✅ **Dev peut coder sans poser questions** (spécifications claires)
✅ **Design est pragmatique** (pas over-engineered)
✅ **Sécurité par design** (secrets, encryption, audit)
✅ **Extensible pour Phase 2** (no breaking changes needed)
✅ **Déployable en 1 semaine** (MVP viable)

---

## 📚 Documents Liés

| Document | Purpose |
|----------|---------|
| `00-README.md` | Overview du projet SAP-Facture |
| `01-analyse-besoins-initiale.md` | Analyse initiale (Sarah) |
| `QUESTIONNAIRE-JULES.txt` | Answers from Jules |
| `SYNTHESE-PHASE-ANALYSE.md` | Analysis summary |
| **`ARCHITECTURE-RESUME-EXEC.md`** | ← Short summary |
| **`ARCHITECTURE.md`** | ← Full technical details |
| **`GETTING-STARTED-DEV.md`** | ← Dev starter guide |

---

**Status**: ✅ Architecture validée, prête pour implémentation

**Next Step**: Kick-off dev avec GETTING-STARTED-DEV.md

