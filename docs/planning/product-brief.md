# Product Brief — SAP-Facture Phase 2

**Document de Synthèse pour Équipe Développement**
**Source de Vérité** : `docs/schemas/SCHEMAS.html`
**Date** : 15 mars 2026
**Version** : 1.0

---

## 1. Vision Produit

SAP-Facture est un système de facturation automatisé conçu pour micro-entrepreneurs en cours particuliers. Il transforme manuellement la création, soumission et suivi de factures auprès d'URSSAF en un processus fluide, réduisant les frictions administratives et minimisant les erreurs. L'application intègre nativement le contexte fiscal français (URSSAF, déclaration NOVA, cotisations micro) et s'appuie sur Google Sheets comme source unique de vérité pour les données.

---

## 2. Problème Résolu

Jules, micro-entrepreneur en cours particuliers (SIREN 991552019), facture ses élèves via URSSAF. Aujourd'hui :

- **Friction manuelle** : création facture PDF → email client → copie/colle données dans Sheets → soumission API URSSAF
- **Erreurs fréquentes** : écarts montants, doublons, oublis de relance si client n'a pas validé sous 48h
- **Suivi fragmenté** : pas de vision centralisée du cycle de vie (BROUILLON → SOUMIS → VALIDE → PAYE → RAPPROCHÉ)
- **Rapprochement bancaire manuel** : vérifier manuellement virements Swan ↔ factures URSSAF, écrire dans Sheets, chercher les écarts
- **Déclarations fiscales chronophages** : assembler heures, CA, cotisations de plusieurs sources fragmentées

**SAP-Facture automatise l'intégralité du flux**, de la création facture au rapprochement bancaire, en centralisant sur Google Sheets.

---

## 3. Persona Utilisateur : Jules

| Attribut | Description |
|----------|-------------|
| **Nom** | Jules Willard |
| **Activité** | Cours particuliers (soutien scolaire, préparation exams) |
| **SIREN** | 991552019 |
| **Régime fiscal** | Micro-entrepreneur (BNC, abattement 34%) |
| **Volume mensuel** | ~5-10 factures/mois (30-50h) |
| **Tech proficiency** | Intermédiaire : confortable CLI + web, édite Sheets manuellement |
| **Douleurs** | Bureaucratie administrative, time-consuming, prône aux erreurs |
| **Gains escomptés** | Automatisation 80% du workflow, zéro erreur de montants, suivi temps réel |
| **Contexte** | Solo, 1 seul utilisateur, pas de collaborateurs |

---

## 4. Proposition de Valeur Unique

### vs. Faire à la Main (Approche Actuelle)
- **Temps économisé** : 15 min/facture → 2 min/facture (87% d'économie)
- **Erreurs éliminées** : zéro risque montants mal saisis, oubli relances
- **Suivi centralisé** : un seul onglet Sheets pour tout (vs. fichiers éparpillés)
- **Reminder automatique** : pas d'oubli client, email T+36h si besoin validation

### vs. Concurrents (Facture.net, Zoom, Devis Facture)
| Critère | SAP-Facture | Concurrents |
|---------|-------------|------------|
| **URSSAF native** | Oui, intégration 100% | Non, via Zapier/n8n |
| **Backend Sheets** | Oui, data en temps réel | Non, silos propriétaires |
| **Rappro bancaire** | Oui, automatisé Swan | Non ou limité |
| **Déclaration NOVA** | Oui, calcul auto | Jamais |
| **Cotisations micro** | Oui, simulées | Jamais |
| **CLI** | Oui | Jamais |
| **Coût** | Gratuit (APIs Google, Swan) | 20-50€/mois |

---

## 5. Objectifs Mesurables — KPIs MVP

### KPI 1 : Temps de Création Facture
- **Baseline** : 15 min (manuelle) → saisie + PDF + email
- **Target MVP** : **2 min** (web form + auto-submit)
- **Mesure** : Chrono utilisateur dans logs
- **Succès** : 90% factures créées en < 3 min

### KPI 2 : Taux d'Erreur Montants
- **Baseline** : ~5% (erreurs saisie manuelles)
- **Target MVP** : **0%** (validation stricte, formules Sheets)
- **Mesure** : Écart détecté lors rappro (montant ≠ facture)
- **Succès** : 100% factures créées sans écart montant

### KPI 3 : Couverture Cycle Vie Facture
- **Baseline** : 40% suivi (manque visibility VALIDE/PAYE)
- **Target MVP** : **100%** (polling auto URSSAF 4h, dashboard)
- **Mesure** : % factures avec statut à jour
- **Succès** : Tous les statuts actualisés dans 4h après changement URSSAF

### KPI 4 : Lettrage Bancaire Automatisé
- **Baseline** : 0% (entièrement manuel)
- **Target MVP** : **80% auto** (score ≥ 80 confidence)
- **Mesure** : % factures PAYEE qui match automatique Swan
- **Succès** : 80% factures auto-lettrées, 20% à vérifier manuellement

### KPI 5 : Taux de Validation Client (URSSAF)
- **Baseline** : ~70% (certains clients oublient, pas de reminder)
- **Target MVP** : **95%** (reminder T+36h auto)
- **Mesure** : % factures qui passent EN_ATTENTE → VALIDE
- **Succès** : Reminders entraînent validation avant T+48h dans 95% cas

---

## 6. Contraintes Connues

### Backend : Google Sheets
- **Source unique de vérité** : 8 onglets = Clients, Factures, Transactions, Lettrage, Balances, Metrics NOVA, Cotisations, Fiscal IR
- **Limite** : Pas de SQL, donc requêtes complexes via formules Sheets
- **Avantage** : Jules peut éditer directement, audit trail natif Google
- **Implication** : SheetsAdapter = couche d'abstraction critique, doit gérer retry/timeouts API

### API URSSAF
- **Limitation** : Webhooks non disponibles → polling obligatoire (4h)
- **Authentification** : OAuth2 (client_id, client_secret)
- **Dépendance** : API criticité haute, doit gérer fallback gracieux si down
- **Délai validation** : Client a 48h pour valider sur portail URSSAF (pas contrôlable)

### Compte Bancaire : Swan
- **API limitation** : Transactions ne remontent que J+1/J+2
- **Matching** : Doit chercher virement avec fenêtre ±5j (pas de certitude absolue)
- **Implication** : Lettrage "semi-auto" avec confirmation Jules si score < 80

### Utilisateurs : 1 Seul (Jules)
- **Pas de multi-user** : Pas de gestion droits, conflits concurrence simples
- **Admin = Product Owner** : Jules gère aussi Google Sheets directement
- **Implication** : Pas de verrouillage ligne, audit trail lightweight suffisant

### Données Sensibles
- **Émails clients** : Stockés dans Sheets (pas de conformité RGPD stricte requis MVP)
- **Montants factures** : Publics URSSAF
- **Credentials** : `.env` local, jamais committé

---

## 7. Hypothèses à Valider

| # | Hypothèse | Validation Plan | Impact |
|---|-----------|-----------------|--------|
| H1 | **Polling URSSAF 4h suffisant** | Vérifier TTL validation client < 48h cover | Haut : si polling trop lent → factures expirent |
| H2 | **Swan API stable 99%** | Tester indisponibilité API, fallback | Moyen : rappro décalé de quelques heures OK |
| H3 | **Matching 80% auto valide** | Tester avec données réelles Swan/URSSAF | Haut : si < 70% → charge manuel important |
| H4 | **Jules comfortable CLI/Web 50/50** | Tracker usage après MVP | Bas : préparer interface par défaut |
| H5 | **Google Sheets perf OK pour 10k rows** | Benchmark gspread + formules | Moyen : si lent → pré-filter avant import |
| H6 | **Email SMTP jamais bloqué** | Utiliser SMTP free tier (Gmail) ou service payant | Bas : fallback log alert manually |
| H7 | **Client URSSAF valide toujours email** | Vérifier taux confirmation > 90% | Haut : si < 80% → auto-resubmit après T+48h |
| H8 | **Formules Sheets sufficient for fiscal calc** | Valider calcul cotisations vs. vrai montant | Haut : doit être exact pour déclaration |

---

## 8. Hors Scope Explicite — Phase 2+

| Feature | Raison | Phase |
|---------|--------|-------|
| **Multi-utilisateurs (intervenants)** | Complexité droits, audit ; solo pour Jules | Phase 3 |
| **Annulations et avoirs** | Logique complexe URSSAF, peu fréquent MVP | Phase 2 |
| **Attestations fiscales** | Format déclaration NOVA complexe | Phase 3 |
| **API Webhook URSSAF** | N'existe pas, polling seul option | N/A |
| **Mobile app native** | Web responsive suffit MVP | Phase 3 |
| **Notifications push** | Email + SMS suffisent | Phase 3 |
| **Backup automatique Sheets** | Google Drive natif suffit | Phase 3 |
| **Synchronisation temps réel** | Polling 4h acceptable | Phase 3 |
| **Multi-comptes bancaires** | Jules utilise 1 seul Swan | Future |
| **Conversions devises** | Uniquement EUR, pas multi-devises | Future |

---

## 9. Modèle de Données — Rappel Schéma

**8 Onglets Google Sheets** (détails complets dans SCHEMAS.html § 5) :

### Data Brute (Éditable)
1. **Clients** : client_id, nom, email, adresse, urssaf_id, statut_urssaf
2. **Factures** : facture_id, client_id, montant_total, dates, statut (BROUILLON→SOUMIS→CREE→EN_ATTENTE→VALIDE→PAYE→RAPPROCHÉ)
3. **Transactions** : transaction_id, swan_id, date_valeur, montant, libelle, type

### Data Calculée (Formules, Lecture Seule)
4. **Lettrage** : Matching facture ↔ transaction, score confiance (AUTO/À_VÉRIFIER/PAS_DE_MATCH)
5. **Balances** : Soldes mensuels, nb factures non-lettrées, CA total
6. **Metrics NOVA** : Trimestres, heures, nb particuliers, CA trimestriel
7. **Cotisations** : Calcul charges mensuelles (25.8%), net après charges
8. **Fiscal IR** : Revenu imposable, tranches IR, simulation impôt annuel

---

## 10. Interfaces Utilisateur — Résumé

### FastAPI Web (SSR + Jinja2 + Tailwind)
- `/` Dashboard factures (liste + statuts)
- `/invoices/create` Formulaire créer facture
- `/clients` Gestion clients (inscriptions)
- `/reconcile` Interface rappro bancaire manuelle
- `/metrics` Dashboard iframes (Sheets embeds read-only)

### CLI (Click)
- `sap submit` Créer + soumettre facture
- `sap sync` Polling URSSAF statuts
- `sap reconcile` Lettrage bancaire
- `sap export --format csv` Export données

### Google Sheets Direct
- Jules édite Clients, Factures, Transactions directement
- SheetsAdapter gère sync automatique

---

## 11. Roadmap Phases

### Phase 1 (COMPLÉTÉE)
Architecture, composants, intégrations URSSAF de base.

### Phase 2 (EN COURS)
- Rappro bancaire Swan (lettrage auto/semi-auto)
- Email reminder T+36h
- Dashboard amélioré + filtres
- CLI `sap reconcile`

### Phase 3 (FUTURES)
- Annulation/avoir
- Historique + recherche avancée
- Attestations fiscales
- Multi-intervenants (NOVA)
- UI mobile responsive
- Notifications push

---

## 12. Dépendances Critiques

### APIs Externes (Production-Ready Required)
- **API URSSAF** : OAuth2 + REST, production credentials en `.env`
- **API Swan** : GraphQL ou REST, production token en `.env`
- **Google Sheets API v4** : Service account JSON
- **Google Drive API** : Service account JSON (upload PDFs)
- **SMTP** : Email relay (Gmail free ou service payant)

### Frameworks/Libs
- **FastAPI** : Web server
- **Click** : CLI
- **Gspread** : Google Sheets abstraction
- **WeasyPrint** : PDF generation
- **APScheduler** : Cron jobs (polling 4h)

### Données de Référence
- **Taux cotisations micro** : 25.8% (valide 2026)
- **Seuil apprentissage** : €5,500 (exonération si inclus)
- **Abattement BNC** : 34% revenu brut
- **Délai URSSAF validation** : 48h max

---

## 13. Métriques de Succès Phase 2

| Métrique | Target | Seuil d'Acceptation |
|----------|--------|-------------------|
| Temps moyen création facture | 2 min | ≤ 3 min |
| Taux erreurs montants | 0% | 0 erreurs / 100 factures |
| Couverture statuts à jour | 100% (4h) | ≥ 95% |
| Lettrage auto (score ≥ 80) | ≥ 80% | ≥ 70% acceptable |
| Validation client (T+48h) | ≥ 95% | ≥ 85% acceptable |
| Uptime système | 99.5% | ≥ 98% acceptable |
| Taux reminder reçus | 100% | ≥ 98% acceptable |

---

## 14. Risques & Mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|-----------|
| API URSSAF down | Moyenne | Haut | Graceful fallback, queue locale, retry auto |
| Matching bancaire < 70% | Basse | Haut | Améliorer algo scoring, vérif manuelle Jules |
| Délai polling 4h trop long | Très basse | Moyen | Accepter, ou passer 2h si critique |
| Sheets formules trop lentes | Très basse | Bas | Pre-filter rows, cache results |
| Credentials compromises | Très basse | Critique | Jamais commit `.env`, rotation auto |
| Client URSSAF oublie valider | Moyenne | Moyen | Email reminder T+36h automatique |

---

## 15. Définition de Fait (DoD)

Une feature Phase 2 est complète si :

1. ✓ Code implémenté + unit tests (80% couverture)
2. ✓ Intégration testée (avec stubs APIs si extérieures)
3. ✓ Documentée dans README + code comments
4. ✓ Validée avec Jules (tests manuels)
5. ✓ Performance OK : création facture < 3s, lettrage < 10s pour 100 factures
6. ✓ Erreurs gracieux, logs détaillés
7. ✓ Pas d'exposition données sensibles (mots passe, tokens)

---

## 16. Références & Documents

- **SCHEMAS.html** : Tous les diagrammes (parcours, flux, architecture, data model, etc.)
- **04-system-components.md** : Détail composants et dépendances
- **Google Sheets** : Source unique de vérité données
- **API Docs** :
  - URSSAF : `portailapi.urssaf.fr`
  - Swan : `docs.swan.io`
  - Google : `sheets.googleapis.com`, `drive.googleapis.com`

---

**Document version 1.0 — 15 mars 2026**
**Rédigé par** : Sarah (BMAD Product Owner)
**Source de Vérité** : `docs/schemas/SCHEMAS.html`
**État** : À valider avec Jules (signature Product Owner)
