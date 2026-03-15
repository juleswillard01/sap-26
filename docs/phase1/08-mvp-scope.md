# MVP Scope Analysis — SAP-Facture
**Version**: 1.0
**Date**: Mars 2026
**Product Owner**: Sarah (BMAD)
**Source de Vérité**: SCHEMAS.html — Schema 8 "Scope MVP vs Phases Futures"

---

## 1. Features MVP (Semaine 1) — Valeur Immédiate

### 1.1 Liste Exhaustive avec Estimation et Priorité

| # | Feature | Effort | Priorité | Dépendances | Justification Valeur |
|---|---------|--------|----------|------------|----------------------|
| M1 | Inscription client URSSAF | 5 jours | CRITIQUE | Aucune (bloc fondateur) | Sans client en base URSSAF, aucune facture possible. Bloc absolu. |
| M2 | Création facture web (SSR Jinja2) | 3 jours | CRITIQUE | M1 | Interface principal pour créer des factures. Besoin quotidien de Jules. |
| M3 | Génération PDF + logo | 2 jours | CRITIQUE | M2 | Facture PDF est la preuve légale requise par URSSAF. Non-négociable. |
| M4 | Soumission API URSSAF | 4 jours | CRITIQUE | M1, M2, M3 | Envoyer la facture à URSSAF déclenche le paiement. Cœur du système. |
| M5 | Polling statut auto 4h | 3 jours | HAUTE | M4 | Suivi du paiement sans action manuelle. Réduit friction. |
| M6 | Dashboard factures | 3 jours | HAUTE | M1, M2, M4 | Vue d'ensemble des factures créées et leurs statuts. Permet de gérer le flux. |
| M7 | CLI: sap submit | 2 jours | MOYENNE | M2, M4 | Alternative web pour power users. Flexibilité. |
| M8 | CLI: sap sync | 2 jours | MOYENNE | M4, M5, M6 | Sync sur-demande entre Google Sheets et API URSSAF. Fallback critique. |
| M9 | Export CSV | 1 jour | BASSE | M6 | Facilite intégration comptable et analyse ad hoc. Nice-to-have fonctionnel. |

**Total effort MVP**: ~25 jours (5 semaines réalistes avec tests + review + buffer)
**Réaliste en 1 semaine ?** Non. Revoir scope down à M1-M4 pour semaine 1.

---

### 1.2 Recommandation : Découpage Réaliste MVP

#### **MVP Phase 1a (Semaine 1 — CORE MINIMUM)**
- **M1** : Inscription client URSSAF (5j)
- **M2** : Création facture web (3j)
- **M4** : Soumission API URSSAF (4j)

**Total**: ~12 jours → **Livrable fin semaine 1** (avec buffer jour 5 pour tests e2e)

**Jour 1**: M1 backend + tests
**Jour 2-3**: M2 UI + intégration M1
**Jour 4-5**: M4 API call + polling minimal (cron 1x par jour, pas 4h)

**Critère d'acceptance minimum MVP 1a**:
- Jules peut créer un client URSSAF via web
- Jules peut créer une facture et envoyer à URSSAF
- Facture reçoit statut CREE en < 5 min
- Statut peut être rafraîchi manuellement (pas encore polling)

---

#### **MVP Phase 1b (Semaine 2 — COMPLETION)**
- **M3** : Génération PDF + logo (2j)
- **M5** : Polling 4h automatique (2j)
- **M6** : Dashboard factures (3j)

**Total**: ~7 jours → **Livrable fin semaine 2**

**Raison du découpage**: Facture PDF est légalement requise mais peut fonctionner avec brouillon texte pour tests. Polling 4h ajoute infrastructure cron (résilience, timezone). Dashboard sans lui le web est invisible.

**Critère d'acceptance MVP 1b**:
- Facture PDF valide (logo présent, format correct)
- Polling cron 4h stable pendant 24h sans erreurs
- Dashboard affiche toutes les factures avec statut en temps réel
- Export CSV depuis dashboard fonctionne

---

### 1.3 Dépendances Internes Entre Features MVP

```
M1 (Inscription URSSAF)
  ↓
M2 (Création facture) ←→ M6 (Dashboard)
  ↓
M3 (PDF)
  ↓
M4 (Soumission API) ←→ M5 (Polling)
  ↓
M8 (sap sync) — fallback manuel
M7 (sap submit) — interface alternative
M9 (Export CSV) — intégration sortante
```

**Chemin critique**:
`M1 → M2 → M4 → M5 → M6` = **17 jours**

**Bloqueurs**:
- M1 bloque tout (API URSSAF doit être accessible)
- M4 bloque M5 (pas de polling sans soumission)
- M3 bloque légalement M4 (PDF requis pour URSSAF)

---

## 2. Features Phase 2 (Semaine 2-3) — Confort & Automatisation

| Feature | Effort | Raison du Report | Pré-requis | Impact Business |
|---------|--------|------------------|-----------|-----------------|
| P2A: Rapprochement bancaire Swan | 5 jours | Dépend de M4 (statut PAYE) + Swan API (complexe GraphQL). Après MVP, on sait si Swan est stable. | M4, M5, Swan creds | Ferme boucle comptable. Lettrage auto réduit erreurs. |
| P2B: Email reminder T+36h | 2 jours | Nécessite job scheduler robuste (vs cron basique). Peut être fallback manuel semaine 1. | M4, email SMTP | Augmente taux validation client de 15-20% estimé. ROI bas initialement. |
| P2C: Annulation / avoir | 3 jours | Rarement nécessaire initialement. Demande logique de état inverse (complexe avec URSSAF). | M2, M4 | Nice-to-have légal. Pas urgence semaine 1. |
| P2D: Historique et recherche | 2 jours | Pur UI. Impératif après 5-10 factures (lisibilité). | M6 dashboard | Usabilité. Devient obligatoire rapidement. |
| P2E: Filtres dashboard | 1 jour | Extension triviale P2D. | M6 | Filtering (statut, date, montant) = nécessaire pour gérer volume. |
| P2F: CLI sap reconcile | 3 jours | Fallback manuel si Swan API down. Permet une "réconciliation" ad hoc. | P2A Swan | Power user feature. Utile quand paiements complexes. |

**Total Phase 2**: ~16 jours → **Semaine 2-3 réalistes**

**Ordre recommandé de livraison Phase 2**:
1. **P2D + P2E** (jour 1-2): Historique + filtres dashboards — impact immédiat UX
2. **P2A** (jour 3-7): Rappro Swan — boucle comptable complète
3. **P2B** (jour 8): Email reminder — gain taux validation
4. **P2F** (jour 9-10): CLI reconcile — tool pouvoir users
5. **P2C** (jour 11-13): Annulation — légalité

---

## 3. Features Phase 3 (Mois 2+) — Scaling & Reporting

| Feature | Effort | Critères de Déclenchement | Impact | Timeline |
|---------|--------|----------------------------|--------|----------|
| P3A: Google Sheets auto-sync | 5 jours | 50+ factures, besoin de reporting NOVA trimestriel. Critères: tests en prod 2 semaines, zero erreurs lettrage. | Automatise 2h/sem tâche manuelle Jules. ROI haut après volume. | Mois 2 (après avril reporting) |
| P3B: Attestations fiscales | 4 jours | Demande comptable ou besoin fiscal annuel (juin pour déc N-1). Critères: données nettoyées, calculs BNC validés. | Génère PDF légal pour impôts. Obligatoire T+4 mois fiscal. | Mois 3 (avant juin) |
| P3C: Multi-intervenants | 7 jours | Jules recrute second intervenant. Critères: besoin opérationnel confirmé, UI clarifiée (qui facture quoi ?). | Élargit modèle économique. Permet agence / collectif. | Mois 4+ (si scaling) |
| P3D: UI mobile responsive | 3 jours | 30% traffic mobile. Critères: analytics.js montrant usage mobile, feedback utilisateur. | Améliore UX mobile Jules (consultation déplaçement). | Mois 3 (après metriques) |
| P3E: Notifications push | 2 jours | Email open rate < 25%. Critères: tests A/B avec push, opt-in clair. | Augmente activation des actions urgentes (validation client). | Mois 3+ (post MVP data) |
| P3F: Stats et reporting | 4 jours | 100+ factures/mois ou besoin reporting nouveau. Critères: dashboard NOVA complet, formules testées, SLA lettrage 95%. | Donne vision complète revenu, charges, fiscalité. Décisionnel. | Mois 2-3 |

**Total Phase 3 explorée**: ~25 jours distribués sur mois 2+

**Critères de Déclenchement Synthèse**:
- **P3A (Sheets sync)**: Volume ≥50 factures/mois + zéro erreurs lettrage en Phase 2
- **P3B (Attestations)**: Demande fiscale confirmée OU 50+ factures
- **P3C (Multi-intervenants)**: Décision business Jules + roadmap confirmée
- **P3D (Mobile UI)**: Analytics montrant 20%+ traffic mobile OU feedback utilisateur
- **P3E (Push notifs)**: Email engagement < 30% + infrastructure notification testée
- **P3F (Stats/reporting)**: Besoin analytique exprimé + données Phase 2 stables 2 semaines

---

## 4. Matrice de Dépendances Global

### MVP → Phase 2
```
MVP Core (M1-M4)
    ↓
M5 (Polling) ────→ P2A (Rappro Swan) ────→ P2F (CLI reconcile)
    ↓                    ↓
M6 (Dashboard) ────→ P2D (Historique) ──→ P2E (Filtres)
    ↓
M9 (Export CSV) ─→ P2B (Email reminder) — fallback manuel possible

M2 ────→ P2C (Annulation)
```

### Phase 2 → Phase 3
```
P2A (Rappro Swan) ──→ P3A (Sheets auto-sync) ──→ P3F (Stats reporting)
                            ↓
                      P3B (Attestations)

M6 + P2D ─────→ P3D (Mobile UI) ──→ P3E (Push notifs)

Multi-intervenant (P3C) = indépendant, déc. business
```

**Bloqueurs Critiques**:
- **M1** bloque tout (client URSSAF)
- **M4** bloque Phase 2 (statuts = données pour lettrage)
- **Phase 2 stabil 2 semaines** bloque Phase 3 (confiance données)

---

## 5. Critères d'Acceptance MVP — "Done = Quoi ?"

### MVP 1a Est "Done" Quand :
- [ ] 1 client créé dans URSSAF via web ✅
- [ ] 1 facture créée, PDF généré localement ✅
- [ ] 1 facture soumise à URSSAF via API ✅
- [ ] Réponse URSSAF reçue (statut CREE ou ERREUR) ✅
- [ ] Statut persiste en DB/Sheets ✅
- [ ] Tests e2e couvrent parcours complet (0 erreur 5 runs) ✅
- [ ] Erreurs URSSAF API gérées gracieusement (retry, log) ✅
- [ ] Code review + merge main sans warning ✅

### MVP 1b Est "Done" Quand :
- [ ] PDF valide (logo, format A4, champs visibles) ✅
- [ ] Polling cron 4h tourne 72h sans erreur ✅
- [ ] Dashboard affiche ≥3 factures avec statuts corrects ✅
- [ ] Statuts se mettent à jour auto en Dashboard (sans refresh) ✅
- [ ] Export CSV ouverture Excel sans corruption ✅
- [ ] Tests e2e étape par étape (création → soumission → poll → dashboard) ✅
- [ ] Perf: Dashboard charge en < 2s (5 factures) ✅
- [ ] Aucune requête API non-prometteuse ou timeout > 10s ✅

### MVP Global Est "Production-Ready" Quand :
- [ ] Tous critères 1a + 1b validés ✅
- [ ] Base de données (SQLite/Postgres) stabil (zero corruption test) ✅
- [ ] Secrets (.env) pas loggés, audit OK ✅
- [ ] Documentation interne (API, flows, setup) à jour ✅
- [ ] Jules peut onboarder 5 clients en 30 min (usabilité) ✅
- [ ] Monitoring cron + API errors configuré (alertes email) ✅
- [ ] Plan incident URSSAF API down documenté ✅

---

## 6. Risques Par Feature (Complexité & Dépendances Externes)

### MVP Risques

| Feature | Risque Technique | Probabilité | Mitigation |
|---------|------------------|-------------|-----------|
| **M1: Inscription URSSAF** | API URSSAF validation payload stricte. Erreurs obscures. | HAUTE (70%) | Contacter URSSAF support avant dev. Mock API réponses avant intégration. |
| **M1** | Client URSSAF doit avoir "fait 1 déclaration fiscale" — validation côté URSSAF. | MOYENNE (50%) | Tester avec vrais SIRET/email. Plan fallback: afficher erreur lisible à Jules. |
| **M2: Web form** | Validation form complexe (heures, tarifs, dates). Edge case: mois partiel, tarifs variables. | BASSE (30%) | Tests unitaires combinatoires. Contrainte form: heures > 0, tarif > 0. |
| **M3: PDF** | Weasyprint rendering inconsistency (logo/police). CSS complexe. | MOYENNE (40%) | Tests visuels PDF (exact match image). Fallback: generer HTML instead si weasyprint fail. |
| **M4: API URSSAF** | OAuth2 token expiry. Retry logic si timeout. Payload JSON schema strict. | HAUTE (60%) | Refresh token avant expiry (cache 59min). Retry exponential backoff max 3x. Valider JSON avant submit. |
| **M5: Polling cron** | Timezone issues (UTC vs CET). Duplicate jobs si crashes. Statut inconsistency. | MOYENN (50%) | Toujours UTC internals. Idempotent poll (check last_polled timestamp). Lock DB pour eviter race. |
| **M6: Dashboard** | Statut en temps réel nécessite refresh (pas websocket semaine 1). UX poll naïf = lag. | BASSE (25%) | Polling JS frontend 30s. Spinner pendant refresh. Acceptable semaine 1. |
| **M7: CLI submit** | Click CLI parsing args, erreurs utilisateur. Dépend M2 validation. | BASSE (20%) | Help text clair. Validation input stricte (reuse M2). Unit tests args. |
| **M8: sap sync** | Bidirectional sync risqué (conflit si Julian modifie Sheets + sync). | MOYENNE (45%) | Sync unidirectionnel: Sheets → App initialement. Queue manuelle si conflit. |
| **M9: Export CSV** | CSV malformed si caract. spéciaux ou encoding. | BASSE (15%) | csv.writer Python (gère escaping). Test UTF-8. |

### Phase 2 Risques

| Feature | Risque | Probabilité | Mitigation |
|---------|--------|-------------|-----------|
| **P2A: Swan Rappro** | Swan GraphQL API rate limit / timeout. Matching false positive montant. | HAUTE (65%) | Caching transactions 1h. Scoring lettrage 80%+ confiance. UI "à verifier" pour < 80. |
| **P2B: Email reminder** | SMTP fail, bounces. Template email non-deliverable. | MOYENNE (35%) | Fallback: pas d'email = pas de rappel (acceptable phase 2). Queue + retry. |
| **P2C: Annulation** | Annuler facture URSSAF demande — API support? | HAUTE (75%) | Contacter URSSAF: est-ce un endpoint annulation? Fallback: statut ANNULE local, document manuellement. |
| **P2D/E: Historique/Filtres** | Perf sur 1000 factures. Index DB manquant. | MOYENNE (40%) | Index sur client_id, date, statut. Pagination 50 items. |

---

## 7. Métriques de Succès Par Phase

### MVP Métriques Primaires

| Métrique | Cible MVP | Definition | Mesure |
|----------|-----------|------------|--------|
| **Time to Invoice** | < 5 min | Temps Jules: clic "créer facture" à soumission URSSAF. | Chronomètre manuel 5 fois. Moyenne. |
| **API Success Rate** | ≥ 95% | % soumissions URSSAF acceptées (non erreur syntax). | Dashboard: COUNT(statut CREE) / COUNT(soumis). |
| **Uptime Système** | ≥ 99% | Disponibilité web + cron. Exclut URSSAF outages. | Monitoring: logs d'erreur 500 par jour. |
| **Feature Completeness** | 100% | Tous critères acceptance M1-M6 validés. | Checklist test. |
| **Zéro Production Data Loss** | 100% | Aucune facture/client perdu après MVP. | Audit DB intégrité post-semaine 1. |

### Phase 2 Métriques

| Métrique | Cible Phase 2 | Definition |
|----------|---------------|------------|
| **Rappro Accuracy** | ≥ 90% | % factures PAYEES correctement lettrées (auto + manual). |
| **Client Validation Rate** | ≥ 80% | % factures EN_ATTENTE passent VALIDE (vs EXPIRE). |
| **Email Open Rate** | ≥ 30% | Reminders T+36h. Click through = validation client. |
| **Dashboard Performance** | < 1s load | Dashboard 50 factures charge en < 1000ms. |

### Phase 3 Métriques

| Métrique | Cible Phase 3 | Definition |
|----------|---------------|------------|
| **Sheets Sync Reliability** | ≥ 99.5% | Sync auto 0 erreurs, délai < 5min. |
| **Reporting Adoption** | ≥ 80% | Jules utilise stats NOVA pour décisions. |
| **Multi-intervenant Readiness** | TBD | 2nd intervenant peut facturer indépendantly. |
| **Mobile Traffic** | 20%+ | Analytics: visitors mobile / total. |

---

## 8. Roadmap Synthétique & Timeline

```
SEMAINE 1 (MVP 1a)
├─ Jour 1: M1 backend + tests unitaires
├─ Jour 2-3: M2 web form + intégration
├─ Jour 4-5: M4 API URSSAF + e2e test
└─ Livrable: 1 client → 1 facture → URSSAF reçoit

SEMAINE 2 (MVP 1b)
├─ Jour 1: M3 PDF + logo test
├─ Jour 2-3: M5 polling + cron setup
├─ Jour 4-5: M6 dashboard + export CSV
├─ Jour 6: Tests + fixes
└─ Livrable: MVP complet en prod

SEMAINE 3-4 (Phase 2)
├─ Jour 1-2: P2D historique + P2E filtres
├─ Jour 3-7: P2A Swan rappro
├─ Jour 8: P2B email reminder
├─ Jour 9-11: P2F CLI reconcile + P2C annulation
├─ Jour 12: Tests + perf tunning
└─ Livrable: Confort + lettrage complet

MOIS 2+ (Phase 3)
├─ P3A Sheets sync (si 50+ factures)
├─ P3B Attestations (si besoin fiscal)
├─ P3D Mobile UI (si analytics montrent demand)
├─ P3C Multi-intervenant (si scaling)
├─ P3E Push notifs (si email engagement bas)
└─ P3F Stats reporting (si demande analytique)
```

---

## 9. Assumptions Clés & Leviers de Risque

### Assumptions Critiques
1. **API URSSAF stable** — Toute instabilité ajoute 2-3 jours buffer.
2. **Swan API docs/credentials dispo** — Sinon Phase 2A repousse.
3. **Google Sheets API quota suffisant** — Pas de limits sur appels (vérifier compte).
4. **Jules peut tester avec vrai SIRET** — Sinon mock requis.
5. **PostgreSQL ou SQLite dispo** — Pas d'infrastructure complexe semaine 1.

### Leviers pour Accélérer
- **Réduire M3 PDF** à template HTML simple (pas weasyprint) → -1 jour.
- **Polling manuel refresh button** vs cron auto → -2 jours Phase 1a, ajouter cron Phase 2.
- **Dashboard sans filtres** initialement → -1 jour.
- **Ignorer M9 export CSV** semaine 1 → -1 jour.
- **Email reminder fallback texte** (pas template) → -1 jour.

**Scénario "Vraiment Pressé": MVP 1a en 8 jours**
- M1 (4j) + M2 (2j) + M4 (2j) = 8 jours (tests minimaux)
- M3/M5/M6 = Phase 2

---

## 10. Decision Points & Gates

### Gate MVP 1a → 1b
**Décision**: Les 3 features core (M1, M2, M4) tournent-elles sans erreur en prod 48h?
- **Oui** → Lancer M3/M5/M6 immédiatement
- **Non** → 3-5 jours stabilisation, retest

### Gate MVP 1b → Phase 2
**Décision**: Dashboard affiche données correctes? Zéro perte facture?
- **Oui** → Lancer Phase 2 (P2D/P2E/P2A)
- **Non** → 2-3 jours fixe + audit DB

### Gate Phase 2 → Phase 3
**Décision**: 50+ factures traitées sans erreur? Taux lettrage ≥ 90%?
- **Oui** → Lancer P3A/P3B/P3F
- **Non** → Stay Phase 2, monitor 2 semaines plus

---

## Conclusion: Pragmatisme MVP

**Le vrai MVP n'est PAS tous les 9 points du SCHEMA 8 semaine 1.**

Le vrai MVP est:
1. **Jules crée client URSSAF** ✅
2. **Jules crée facture et envoie à URSSAF** ✅
3. **URSSAF répond avec un statut** ✅
4. **Jules peut voir le statut** ✅

Cela c'est **12 jours de dev robuste**, décomposés:
- **Semaine 1 (5j)**: M1, M2, M4 core
- **Semaine 2 (7j)**: M3, M5, M6, tests, perf, docs

**Phase 2** ajoute le confort: rappro bancaire, rappels, historique — nécessaire pour opérer 100+ factures/mois.

**Phase 3** c'est la scaling: multi-intervenant, reporting fiscal, attestations — après data en production et pattern de usage claire.

**Aucune feature n'est nice-to-have** dans le contexte Jules (micro-entrepreneur). Toutes ont ROI. Mais **ordre séquentiel critique**.

---

**Signatures d'Accord**
- Product Owner: Sarah ✅
- Jules (User): _____________
- Tech Lead: _____________
- Date Signature: _____________

