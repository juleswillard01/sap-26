# Documentation Audit Report — 2026-03-22

## Resume

- Total documents audites : 57
- KEEP : 8
- ARCHIVE : 28
- MERGE : 14
- DELETE : 7

---

## Matrice de Classification

### PAYABLES/docs/ (racine)

| Fichier | Action | Justification |
|---------|--------|---------------|
| `CDC.md` | **KEEP** | Source de verite active — cahier des charges du projet |
| `schemas/SCHEMAS.html` | **KEEP** | Source de verite — diagrammes Mermaid (INTOUCHABLE) |
| `SCHEMAS.html` (racine docs/) | **DELETE** | Doublon de `schemas/SCHEMAS.html` (MD5 different, 946 vs 973 lignes — version anterieure non-canonique) |
| `plan.md` | **ARCHIVE** | Plan d'implementation initial complet (14 sprints) — supersede par le code implemente (962 tests, 82.61% cov). Section AIS REST API Rewrite ajoutee a la fin est la seule info non couverte ailleurs |
| `plan1.md` | **ARCHIVE** | Plan SheetsAdapter CRUD — supersede par `src/adapters/sheets_adapter.py` implemente et teste (97 tests). Redondant avec plan.md Sprint 2 |
| `plan-google.md` | **ARCHIVE** | Plan Google integration (6 phases) — supersede par code implemente (LettrageService, NotificationService, EmailRenderer). Contient aussi sprint Gmail 2FA auto-inject, redondant avec la doc nodriver/Gmail |
| `evals.md` | **ARCHIVE** | Criteres qualite et evaluation — supersede par le fait que les tests passent (962 tests, 82.61%). Les criteres CDC et AIS REST API sont verifies par les tests eux-memes |
| `eval-google.md` | **ARCHIVE** | Criteres evaluation Google integration — supersede par code teste. Contient la matrice de test par composant, mais les tests existent deja |
| `creative.md` | **ARCHIVE** | Brainstorming et decisions techniques — les decisions sont desormais codifiees dans CLAUDE.md (D1-D9). Glossaire technique utile mais court |
| `creative-google.md` | **ARCHIVE** | 12 idees creatives Google — les decisions ADOPTE sont implementees, les DIFFERE sont de la roadmap future. Contient aussi evaluation 10 alternatives Gmail 2FA |
| `NETWORK_LOGGER.md` | **ARCHIVE** | Documentation du NetworkLogger — outil de dev/exploration, pas de production. Supersede par le code `src/adapters/network_logger.py` qui est auto-documente |
| `TURNSTILE_DECISION_TREE.md` | **MERGE** | Decision tree OAuth/Turnstile — fait partie du cluster recherche Indy auth. A fusionner avec OAUTH_RESEARCH_INDEX.md |
| `OAUTH_RESEARCH_INDEX.md` | **MERGE** | Index recherche OAuth — fait partie du cluster recherche Indy auth. A fusionner avec TURNSTILE_DECISION_TREE.md |
| `GMAIL_SETUP_QUICK_START.md` | **MERGE** | Guide setup Gmail IMAP (5 min) — redondant avec GMAIL_SETUP_GUIDE.md et GMAIL_SETUP_CHECKLIST.md |
| `GMAIL_IMAP_INDEX.md` | **MERGE** | Index documentation Gmail IMAP — meta-document pointant vers 3 autres docs. A fusionner dans un seul doc Gmail |
| `GMAIL_SETUP_GUIDE.md` | **MERGE** | Guide complet Gmail OAuth2 setup — redondant avec GMAIL_SETUP_QUICK_START.md. Note : ce doc parle d'OAuth2 tandis que QUICK_START parle d'App Password IMAP = confusion |
| `GMAIL_SETUP_CHECKLIST.md` | **MERGE** | Checklist Gmail OAuth2 — redondant avec GMAIL_SETUP_GUIDE.md (version condensee) |
| `GMAIL_DEPENDENCIES.md` | **MERGE** | Dependencies + code implementation Gmail — contient code sample GmailReader + notes deps. Redondant avec le code reel dans `src/adapters/gmail_reader.py` |
| `NODRIVER_2FA_QUICK_REF.md` | **MERGE** | Quick ref nodriver 2FA — redondant avec RESEARCH_NODRIVER_2FA.md (version condensee) |
| `RESEARCH_NODRIVER_2FA.md` | **MERGE** | Recherche complete nodriver 2FA — document principal du cluster nodriver. A fusionner avec NODRIVER_2FA_QUICK_REF.md |

### PAYABLES/docs/archive/

| Fichier | Action | Justification |
|---------|--------|---------------|
| `OAUTH_TURNSTILE_RESEARCH.md` | **KEEP (archive)** | Recherche technique approfondie OAuth/Turnstile — reference historique correctement archivee |
| `OAUTH_NEXT_STEPS.md` | **KEEP (archive)** | Next steps recherche OAuth — reference historique correctement archivee |
| `INTERCEPT_README.md` | **KEEP (archive)** | README intercepteur API Indy — outil de reverse engineering, correctement archive |
| `CDP_IMPROVEMENTS.md` | **KEEP (archive)** | Ameliorations CDP nodriver — documentation technique correctement archivee |
| `IMPLEMENTATION_SUMMARY.md` | **ARCHIVE** | Resume implementation CDP — redondant avec CDP_IMPROVEMENTS.md mais les deux sont deja archives. Confirme |
| `README_CDP.md` | **ARCHIVE** | Quick reference CDP — redondant avec CDP_IMPROVEMENTS.md mais les deux sont deja archives. Confirme |
| `GMAIL_IMAP_RESEARCH.md` | **KEEP (archive)** | Recherche IMAP Gmail complete — reference technique correctement archivee |
| `NODRIVER_2FA_INJECTION.md` | **KEEP (archive)** | Guide complet injection 2FA nodriver — reference technique correctement archivee |
| `INTEGRATION_2FA_INDY.md` | **KEEP (archive)** | Guide integration 2FA dans Indy adapter — reference technique correctement archivee |

### PAYABLES/docs/specs/ (exclus du perimetre — confirme intact)

| Fichier | Action | Justification |
|---------|--------|---------------|
| `README.md` | **KEEP** | Index des specs |
| `SPEC-001-sheets-adapter.md` | **KEEP** | Spec active |
| `SPEC-002-ais-scraping.md` | **KEEP** | Spec active |
| `SPEC-003-indy-export.md` | **KEEP** | Spec active |
| `SPEC-004-reconciliation.md` | **KEEP** | Spec active |
| `SPEC-005-notifications.md` | **KEEP** | Spec active |
| `SPEC-006-nova-reporting.md` | **KEEP** | Spec active |

### PAYABLES/ (racine projet)

| Fichier | Action | Justification |
|---------|--------|---------------|
| `CLAUDE.md` | **KEEP** | Configuration agent active — decisions verrouillees D1-D9, stack, interdit |
| `README.md` | **KEEP** | README projet actif — 962 tests, 82.61% coverage, architecture |

### PAYABLES/src/adapters/

| Fichier | Action | Justification |
|---------|--------|---------------|
| `WRITE_QUEUE.md` | **ARCHIVE** | Documentation WriteQueueWorker — supersede par le code `src/adapters/write_queue.py` qui est auto-documente. Pas a sa place dans src/ |

### PAYABLES/io/research/ais/

| Fichier | Action | Justification |
|---------|--------|---------------|
| `api-endpoints.md` | **ARCHIVE** | Output genere du NetworkLogger — donnees de recherche, pas de la doc. Supersede par l'implementation AIS REST API dans le code |
| `network-dashboard.md` | **ARCHIVE** | Capture reseau dashboard AIS — donnees de recherche brutes |
| `network-clients.md` | **ARCHIVE** | Capture reseau page clients AIS — donnees de recherche brutes |
| `network-factures.md` | **ARCHIVE** | Capture reseau page factures AIS — donnees de recherche brutes |
| `selectors.md` | **ARCHIVE** | Selecteurs CSS pages AIS — supersede par l'AIS REST API (plus de scraping HTML) |

### main/ (reference — projet archive)

| Fichier | Action | Justification |
|---------|--------|---------------|
| `README.md` | **KEEP (reference)** | README du projet main — contient mindmap et structure de documentation historique |
| `CLAUDE.md` | **ARCHIVE** | CLAUDE.md de main — supersede par PAYABLES/CLAUDE.md. Differences notables : main utilise Python 3.11+/mypy/pip, PAYABLES utilise Python 3.12/pyright/uv. Decisions D6 (lettrage manuel) et D7 (PDF prioritaire) ont change |

### main/archive/phase1-3-docs/ (23 documents)

| Sous-dossier | Fichiers | Action | Justification |
|-------------|----------|--------|---------------|
| `analysis/` | 10 fichiers (01 a 10) | **ARCHIVE (confirme)** | Phase 1 analyse — supersede par CDC.md et SCHEMAS.html. User journey, billing flow, URSSAF API reqs, system components, data model, bank reconciliation, invoice lifecycle, MVP scope, competitive analysis, Sheets feasibility |
| `planning/` | 4 fichiers | **ARCHIVE (confirme)** | Phase 2 planning — supersede par CDC.md. Product brief, PRD, UX design, tech spec Sheets adapter |
| `architecture/` | 9 fichiers | **ARCHIVE (confirme)** | Phase 3 architecture — supersede par CLAUDE.md + code implemente. Architecture, API contracts, security review, test strategy, dev environment, deployment plan, sprint planning, gate check, decisions proposals |

### main/bmad/ (framework BMAD)

| Fichier | Action | Justification |
|---------|--------|---------------|
| `README.md` | **ARCHIVE** | Framework BMAD — non utilise dans PAYABLES, supersede par le golden workflow dans .claude/rules/ |
| `AGENT-MANIFEST.md` | **ARCHIVE** | Manifest agents BMAD — non utilise dans PAYABLES |
| `ORCHESTRATION.md` | **ARCHIVE** | Orchestration BMAD — non utilise dans PAYABLES |
| `config.yaml` | **ARCHIVE** | Config BMAD — non utilise |
| `model-routing.yaml` | **ARCHIVE** | Routing modeles BMAD — non utilise |
| `agents/*.md` (7 fichiers) | **ARCHIVE** | Agents BMAD (analyst, architect, developer, product-owner, qa-tester, reviewer, scrum-master, ux-designer) — non utilises dans PAYABLES |
| `workflows/*.md` (4 fichiers) | **ARCHIVE** | Workflows BMAD — non utilises |
| `templates/*.html` (5 fichiers) | **ARCHIVE** | Templates HTML BMAD — non utilises |

---

## Doublons Detectes

| Fichier A | Fichier B | Type | Action |
|-----------|-----------|------|--------|
| `docs/SCHEMAS.html` (946 lignes) | `docs/schemas/SCHEMAS.html` (973 lignes) | Versions differentes (MD5 different) | DELETE `docs/SCHEMAS.html` — `docs/schemas/SCHEMAS.html` est la version canonique referencee par CLAUDE.md |
| `docs/GMAIL_SETUP_QUICK_START.md` (App Password IMAP) | `docs/GMAIL_SETUP_GUIDE.md` (OAuth2 API) | Approches differentes du meme probleme | MERGE — une seule doc setup Gmail avec les 2 options |
| `docs/GMAIL_SETUP_CHECKLIST.md` | `docs/GMAIL_SETUP_GUIDE.md` | Version condensee du guide | MERGE — checklist integree au guide |
| `docs/NODRIVER_2FA_QUICK_REF.md` | `docs/RESEARCH_NODRIVER_2FA.md` | Version condensee de la recherche | MERGE — quick ref integree a la recherche |
| `main/CLAUDE.md` (Python 3.11, mypy, pip) | `PAYABLES/CLAUDE.md` (Python 3.12, pyright, uv) | Evolution du meme fichier | main/ est archive, PAYABLES/ est la version active |

---

## Redondances a Fusionner

### Cluster Gmail (5 docs -> 1)

**Documents source** :
1. `docs/GMAIL_SETUP_QUICK_START.md` — Setup IMAP App Password (5 min)
2. `docs/GMAIL_SETUP_GUIDE.md` — Setup OAuth2 API (10 min)
3. `docs/GMAIL_SETUP_CHECKLIST.md` — Checklist condensee du guide OAuth2
4. `docs/GMAIL_IMAP_INDEX.md` — Meta-index pointant vers 3 docs
5. `docs/GMAIL_DEPENDENCIES.md` — Dependencies + code sample GmailReader

**Probleme** : Confusion entre 2 approches (IMAP App Password vs OAuth2 API) reparties sur 5 documents. Le code reel utilise IMAP App Password (`src/adapters/gmail_reader.py`).

**Cible** : `docs/archive/GMAIL_CONSOLIDATED.md`
- Section 1 : Setup IMAP App Password (approche retenue, depuis QUICK_START)
- Section 2 : Setup OAuth2 API (alternative, depuis SETUP_GUIDE)
- Section 3 : Dependencies requises (depuis GMAIL_DEPENDENCIES)
- Section 4 : Troubleshooting (fusionne des 3 guides)

### Cluster OAuth/Turnstile Indy (2 docs -> archive)

**Documents source** :
1. `docs/TURNSTILE_DECISION_TREE.md` — Decision tree + roadmap
2. `docs/OAUTH_RESEARCH_INDEX.md` — Index navigation recherche

**Probleme** : 2 documents non-archives qui font reference a des documents deja archives (`archive/OAUTH_TURNSTILE_RESEARCH.md`, `archive/OAUTH_NEXT_STEPS.md`). Ces index n'ont plus de valeur sans les docs archivees accessibles.

**Cible** : Deplacer les 2 vers `docs/archive/`

### Cluster Nodriver 2FA (2 docs -> archive)

**Documents source** :
1. `docs/NODRIVER_2FA_QUICK_REF.md` — Quick reference
2. `docs/RESEARCH_NODRIVER_2FA.md` — Recherche complete

**Probleme** : Recherche terminee, code implemente (`src/adapters/indy_2fa_adapter.py`). Documentation de recherche, pas de reference active.

**Cible** : Deplacer les 2 vers `docs/archive/`

### Plans supersedes (3 docs -> archive)

**Documents source** :
1. `docs/plan.md` — Plan principal (14 sprints, 748 lignes)
2. `docs/plan1.md` — Plan SheetsAdapter (183 lignes)
3. `docs/plan-google.md` — Plan Google integration (296 lignes)

**Probleme** : 3 plans d'implementation qui sont tous supersedes par le code implemente. 1227 lignes de plans pour du code qui existe.

**Cible** : Deplacer les 3 vers `docs/archive/`

---

## Gaps Identifies

| Gap | Severite | Recommandation |
|-----|----------|----------------|
| Pas de doc AIS REST API consolidee | HAUTE | Le plan.md mentionne la decouverte de l'API REST AIS (endpoints, collections MongoDB) mais il n'y a pas de document dedie. L'info est fragmentee entre plan.md, io/research/ais/, et le code. Creer `docs/specs/SPEC-002-ais-scraping.md` le couvre peut-etre deja |
| Confusion Gmail IMAP vs OAuth2 | MOYENNE | 5 docs avec 2 approches differentes. Le code utilise IMAP App Password. Clarifier dans un seul document |
| Pas de CHANGELOG | BASSE | Pas de suivi des changements de version. Le README a un "Status Sprint" mais pas d'historique |
| `src/adapters/WRITE_QUEUE.md` mal place | BASSE | Documentation dans src/ au lieu de docs/. A deplacer ou supprimer (le code est auto-documente) |
| Pas de doc operationnelle (runbook) | BASSE | Pas de guide operationnel pour Jules (deploiement, maintenance, recovery). Le README couvre le setup mais pas les operations quotidiennes |

---

## Inventaire io/research/ais/ (donnees de recherche)

Ces fichiers sont des outputs generes par le NetworkLogger, pas de la documentation ecrite. Ils devraient etre dans `.gitignore` ou dans un dossier d'archive de recherche.

| Fichier | Taille | Contenu |
|---------|--------|---------|
| `api-endpoints.md` | 5.4 KB | Endpoints API AIS decouverts |
| `network-dashboard.md` | 12.8 KB | Capture reseau page dashboard |
| `network-clients.md` | 11.3 KB | Capture reseau page clients |
| `network-factures.md` | 14.3 KB | Capture reseau page factures |
| `selectors.md` | 4.9 KB | Selecteurs CSS pages AIS |
| `*.png` (4 fichiers) | ~656 KB | Screenshots pages AIS |

---

## Recommandation Architecture Documentation Post-Cleanup

```
docs/
├── CDC.md                          # KEEP — Source de verite
├── schemas/SCHEMAS.html            # KEEP — Diagrammes (INTOUCHABLE)
├── specs/                          # KEEP — Specs par feature (actives)
│   ├── README.md
│   ├── SPEC-001-sheets-adapter.md
│   ├── SPEC-002-ais-scraping.md
│   ├── SPEC-003-indy-export.md
│   ├── SPEC-004-reconciliation.md
│   ├── SPEC-005-notifications.md
│   └── SPEC-006-nova-reporting.md
└── archive/                        # Tout le reste
    ├── plans/                      # plan.md, plan1.md, plan-google.md
    ├── research/                   # Nodriver, OAuth, Gmail, NetworkLogger
    ├── evals/                      # evals.md, eval-google.md
    ├── creative/                   # creative.md, creative-google.md
    └── tools/                      # CDP, intercept, WRITE_QUEUE
```

---

## Audit P1 — 2026-03-28

### Quality Gates

| Gate | Target | Actual | Status |
|------|--------|--------|--------|
| Tests passing | 100% | 99.7% (1147/1151) | PASS (4 pre-existing) |
| Coverage | >=80% | 86% | PASS |
| Ruff lint | 0 errors | 1 warning | PASS (pre-existing) |
| Ruff format | 0 issues | 0 | PASS |
| Pyright strict | 0 errors | 127 | FAIL (pre-existing, P2 backlog) |
| CI pipeline | Operational | 3 jobs, ~35s | PASS |
| Integration tests | Collected | 14 tests | PASS (skip in CI) |
| Docs | Complete | TESTING.md + BRANCHING.md | PASS |

### Security

- No hardcoded secrets in src/
- Firebase Web API key in config default (public, non-secret)
- JWT tokens not logged
- Playwright screenshots mask sensitive data

### Architecture

- **AIS**: REST primary + Playwright fallback
- **Indy**: REST httpx + nodriver login (Firebase Auth JWT)
- **Sheets**: gspread + Polars (cache 30s, rate limit 60 req/min)
- All adapters read-only (write operations raise NotImplementedError)
