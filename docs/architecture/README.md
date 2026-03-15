# Documentation Architecture — SAP-Facture

**Dernière mise à jour** : 15 Mars 2026
**Architecte** : Winston (BMAD System Architect)

---

## Navigation Rapide

### 📋 Commencer Ici
- **`ARCHITECTURE_UPDATE_SUMMARY.md`** (root) — Résumé pour Jules (10 min read)
- **`docs/DEVIATION_INDY_PLAYWRIGHT.md`** — Ce qui change, impact réel

### 🏗️ Architecture Complète
- **`docs/architecture/architecture.md`** — Document complet (2000+ lignes, référence)
  - Section 1 : Vue d'ensemble + diagrams
  - Section 2 : Stack technique
  - Section 3 : Architecture en couches
  - Section 9 : ADRs (decisions records)
  - Section 10 : Monitoring & observability

### 🛠️ Implémentation & Coding
- **`docs/implementation/PLAYWRIGHT_INDY_GUIDE.md`** — Guide complet (code, tests, troubleshooting)
  - Prérequis
  - Architecture du composant
  - Code pseudo-complet
  - Unit tests + Integration tests
  - Monitoring & alerting
  - Troubleshooting guide

### 📜 Architecture Decision Records (ADRs)
| ADR | Titre | Status | Référence |
|-----|-------|--------|-----------|
| ADR-001 | Google Sheets backend (vs SQL) | ✅ Accepted | `docs/architecture/architecture.md` |
| ADR-002 | Polling URSSAF 4h (vs webhooks) | ✅ Accepted | `docs/architecture/architecture.md` |
| ADR-003 | Batch operations + caching | ✅ Accepted | `docs/architecture/architecture.md` |
| ADR-004 | Monolith FastAPI (vs microservices) | ✅ Accepted | `docs/architecture/architecture.md` |
| ADR-005 | Service Account auth | ✅ Accepted | `docs/architecture/architecture.md` |
| **ADR-006** | **Playwright for Indy (vs API)** | **✅ Accepted** | **`docs/architecture/ADR-006-INDY_PLAYWRIGHT.md`** |

---

## Changement Principal : Swan → Indy via Playwright

### Avant
```
Source bancaire : Swan API (GraphQL)
Composant : SwanClient
Status : ❌ Inaccessible Jules
```

### Après
```
Source bancaire : Indy (app.indy.fr)
Composant : IndyBrowserAdapter (Playwright automation)
Status : ✅ Accessible & pragmatique
```

**Pour comprendre le changement** :
1. Lire : `ARCHITECTURE_UPDATE_SUMMARY.md` (5 min)
2. Lire : `docs/DEVIATION_INDY_PLAYWRIGHT.md` (15 min)
3. Référence : `docs/architecture/ADR-006-INDY_PLAYWRIGHT.md` (30 min)

**Pour implémenter** :
1. Lire : `docs/implementation/PLAYWRIGHT_INDY_GUIDE.md` (45 min)
2. Code : Pseudo-complet inclus, prêt pour développement

---

## Fichiers par Rôle

### Pour Jules (Product Owner)
- ✅ `ARCHITECTURE_UPDATE_SUMMARY.md` — What changed, why, impact
- ✅ `docs/DEVIATION_INDY_PLAYWRIGHT.md` — Detailed impact analysis
- ✅ `.env.example` — Configuration needed
- ✅ `docs/architecture/architecture.md` (Sections 1-2) — Overview

### Pour Développeur Phase 2
- ✅ `docs/architecture/architecture.md` — Complete reference
- ✅ `docs/implementation/PLAYWRIGHT_INDY_GUIDE.md` — Implementation guide
- ✅ `docs/architecture/ADR-006-INDY_PLAYWRIGHT.md` — Decision context
- ✅ `docs/architecture/architecture.md` (Section 3.4.2) — Component design

### Pour QA / Tester
- ✅ `docs/implementation/PLAYWRIGHT_INDY_GUIDE.md` (Testing section)
- ✅ `docs/architecture/architecture.md` (Section 11 Risques)
- ✅ `ARCHITECTURE_UPDATE_SUMMARY.md` (Fallback process)

### Pour Maintenance (Future)
- ✅ `docs/architecture/ADR-006-INDY_PLAYWRIGHT.md` — Why we chose Playwright
- ✅ `docs/DEVIATION_INDY_PLAYWRIGHT.md` — Evolution options
- ✅ `docs/implementation/PLAYWRIGHT_INDY_GUIDE.md` (Troubleshooting)

---

## Structure des Répertoires

```
docs/
├── architecture/
│   ├── README.md (ce fichier)
│   ├── architecture.md ← DOCUMENT PRINCIPAL (2000+ lignes)
│   ├── ADR-006-INDY_PLAYWRIGHT.md ← Decision record (Playwright)
│   ├── security-review.md
│   ├── test-strategy.md
│   ├── deployment-plan.md
│   └── ...
│
├── implementation/
│   ├── PLAYWRIGHT_INDY_GUIDE.md ← Implémentation détaillée
│   └── ...
│
├── DEVIATION_INDY_PLAYWRIGHT.md ← Analyse déviation Swan→Indy
├── analysis/
├── planning/
└── schemas/
    └── SCHEMAS.html ← SOURCE DE VERITE (données models)
```

---

## Recommandations de Lecture

### Parcours 1 : Comprendre le Changement (20 min)
1. `ARCHITECTURE_UPDATE_SUMMARY.md` (5 min)
2. `docs/DEVIATION_INDY_PLAYWRIGHT.md` (15 min)

### Parcours 2 : Implémenter Phase 2 (2 heures)
1. `docs/architecture/architecture.md` (Sections 1-3) (30 min)
2. `docs/architecture/ADR-006-INDY_PLAYWRIGHT.md` (30 min)
3. `docs/implementation/PLAYWRIGHT_INDY_GUIDE.md` (60 min)

### Parcours 3 : Deep Dive Complet (4 heures)
1. `docs/architecture/architecture.md` (entièrement) (120 min)
2. `docs/implementation/PLAYWRIGHT_INDY_GUIDE.md` (60 min)
3. `docs/DEVIATION_INDY_PLAYWRIGHT.md` (15 min)
4. `docs/architecture/ADR-006-INDY_PLAYWRIGHT.md` (30 min)
5. Autres sections (security, deployment, etc) (15 min)

---

## Points Clés (TL;DR)

✅ **Ce qui ne change pas** :
- Modèle de données (SCHEMAS.html reste source de vérité)
- Algorithme lettrage (scoring identique)
- Interfaces utilisateur (web, CLI, Sheets)
- Autres composants (URSSAF, Google Sheets, SMTP, etc)

✅ **Ce qui change** :
- Source transactions : Swan API → Indy app.indy.fr
- Composant : `SwanClient` → `IndyBrowserAdapter` (Playwright)
- Configuration : SWAN_API_KEY → INDY_EMAIL + INDY_PASSWORD
- Latency : ~2-3s → ~4-6s (imperceptible pour utilisateur)

✅ **Fallback** :
- Si automation échoue : export manual CSV
- `sap reconcile --csv /path/to/export.csv`

✅ **Avantages** :
- Coût : €€€ (Swan) → €0 (Playwright)
- Pragmatique : fonctionne avec accès réel Jules
- Documenté : implementation guide complet

⚠️ **Risques** :
- UI change (mitigé par fallback manual)
- Timeout (mitigé par retry + fallback)
- Session expiration (mitigé par auth error handling)
- Credentials leak (mitigé par .env protection + rotation)

---

## Configuration Jules

### Fichier .env
```bash
# Ajouter :
INDY_EMAIL=your_indy_email@example.com
INDY_PASSWORD=your_indy_password
INDY_HEADLESS=true

# Supprimer ou commenter :
# SWAN_API_KEY=deprecated
# SWAN_API_BASE_URL=deprecated
# SWAN_ACCOUNT_ID=deprecated

# Garder tous les autres (URSSAF, Google, SMTP, etc)
```

### Vérification
```bash
# Tester login Indy
# 1. Go to app.indy.fr
# 2. Login avec email/password du .env
# 3. Vérifier accès Transactions page

# Pas besoin de tester Playwright (automated in Phase 2)
```

---

## Commandes Utiles

```bash
# Lancer reconciliation avec Playwright (une fois Phase 2 implémenté)
sap reconcile --date-from 2026-02-15 --date-to 2026-03-15

# Fallback : manual CSV import
sap reconcile --csv ~/Downloads/indy_export.csv

# Check git history
git log --oneline docs/architecture/

# See what changed
git diff HEAD~3 docs/architecture/architecture.md
```

---

## Checklist

- [x] Architecture document updated (`docs/architecture/architecture.md`)
- [x] ADR-006 created (`docs/architecture/ADR-006-INDY_PLAYWRIGHT.md`)
- [x] Implementation guide (`docs/implementation/PLAYWRIGHT_INDY_GUIDE.md`)
- [x] Deviation analysis (`docs/DEVIATION_INDY_PLAYWRIGHT.md`)
- [x] Configuration updated (`.env.example`)
- [x] Summary created (`ARCHITECTURE_UPDATE_SUMMARY.md`)
- [ ] Phase 2 implementation (to be done)
- [ ] Phase 2 testing (to be done)
- [ ] Phase 2 deployment (to be done)

---

## Questions ?

**Contact** : Winston (BMAD System Architect)

**Ressources** :
- Email architecture team
- Message slack #sap-facture
- Create issue on GitHub (if applicable)

---

**Version** : 1.0
**Last Updated** : 15 Mars 2026
**Next Review** : Après Phase 2 implementation
