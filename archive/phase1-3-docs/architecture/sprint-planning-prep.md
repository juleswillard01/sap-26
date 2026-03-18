# Sprint Planning — SAP-Facture
**Préparation Détaillée pour Développement**

**Version**: 1.0
**Date**: 15 mars 2026
**Auteur**: BMAD Scrum Master (Automated)
**Basé sur**: SCHEMAS.html, 01-user-journey.md, 04-system-components.md, 08-mvp-scope.md, product-brief.md

---

## Executive Summary

**Scope Total Développement**: 3 sprints de 5 jours (2 semaines chacun)
- **Sprint 1** (Jours 1-5) : Infrastructure de base + Core URSSAF (12 pts estimés)
- **Sprint 2** (Jours 6-10) : Dashboard + Polling automatique (14 pts estimés)
- **Sprint 3** (Jours 11-15) : Rapprochement bancaire + Features avancées (16 pts estimés)

**Équipe Assumption** : 1 développeur full-stack (Python FastAPI + Google Sheets)
**Velocity Cible** : 12-16 points/sprint (5 jours)
**Total Estimé** : 42 points pour MVP complet + Phase 2 début

---

## Section 1 : Backlog Priorisé par Epic

### Epic 1 : Gestion Clients URSSAF (P0 - Fondateur)

**Objectif métier** : Les clients doivent être inscrits auprès d'URSSAF avant toute facturation.
**Total Points** : 9 pts
**Dépendances** : Accès API URSSAF (OAuth2)

#### US-1.1 : Inscrire client dans URSSAF via API
**Points** : 5
**Priorité** : P0 (Bloqueur absolu)
**Description** : Quand Jules crée un nouveau client, le système envoie ses données (nom, email, adresse) à l'API URSSAF et récupère l'`id_technique`.

**Acceptance Criteria**
- [ ] API POST `/particuliers` appelée avec payload structuré
- [ ] Client reçoit `id_technique` URSSAF ou erreur explicite
- [ ] Données client sauvegardées dans Sheets onglet Clients (urssaf_id)
- [ ] Gestion erreur : client sans déclaration fiscale → affiche message clair
- [ ] Logs : chaque inscription tracée (client_id, timestamp, id_urssaf)
- [ ] Validation email obligatoire avant envoi API
- [ ] Retry automatique 3x si timeout (exponential backoff)

**Technical Notes**
- Composant responsable : `ClientService` + `URSSAFClient`
- Base de données : Google Sheets onglet Clients (colonnes: client_id, nom, email, adresse, urssaf_id, statut_urssaf, date_inscription)
- OAuth2 token refresh avant appel API (cache 59 min)
- Erreurs URSSAF gérées : 400 (validation payload), 401 (token expiré), 403 (client pas eligible), 500 (API down)

**Tasks**
1. **Tâche 1.1.1** : Implémenter URSSAFClient.register_client() (4h)
   - Type: Implementation
   - Dépendances: Configuration URSSAF_CLIENT_ID/_SECRET
2. **Tâche 1.1.2** : Intégrer validation email + test unitaire (3h)
   - Type: Implementation + Testing
   - Dépendances: Tâche 1.1.1
3. **Tâche 1.1.3** : Implémenter ClientService.ensure_client_exists() (3h)
   - Type: Implementation
   - Dépendances: SheetsAdapter.read/write_clients()
4. **Tâche 1.1.4** : Tests e2e inscription nouveau client (4h)
   - Type: Testing
   - Dépendances: Toutes tâches précédentes

**Definition of Done**
- [ ] Code compile sans warning
- [ ] Tests unitaires passent (100% path heureux + edge cases)
- [ ] Erreurs URSSAF affichées à l'utilisateur sans stack trace
- [ ] Logs fichier contiennent timestamp + operation + status
- [ ] SheetsAdapter utilise credentials Google correctement
- [ ] Code review approuvé

---

#### US-1.2 : Importer clients existants depuis Sheets
**Points** : 2
**Priorité** : P0 (Support)
**Description** : Jules peut éditer la colonne `urssaf_id` dans Sheets manuellement (si déjà inscrit avant MVP). Le système lit et cache.

**Acceptance Criteria**
- [ ] SheetsAdapter.read_clients() retourne liste complète avec urssaf_id
- [ ] Cache local des clients pendant 1h (pour perf)
- [ ] Fallback : si Sheets down, utiliser cache
- [ ] Test : 100+ clients chargés en < 2s

**Technical Notes**
- Utilise gspread pour lire onglet Clients
- Caching via `functools.lru_cache` ou Redis-like simple dict (pas de Redis pour MVP)

---

#### US-1.3 : Valider existence client dans impôts (URSSAF)
**Points** : 2
**Priorité** : P1 (Error handling)
**Description** : Si API URSSAF retourne erreur "Client non connu des impôts", afficher message clair : "Client doit avoir fait ≥1 déclaration fiscale".

**Acceptance Criteria**
- [ ] Erreur URSSAF parsée et convertie en message humain
- [ ] Suggestions : demander client de faire déclaration (lien URSSAF)
- [ ] Log détaillé pour debug

---

### Epic 2 : Création & Soumission Factures (P0 - Core)

**Objectif métier** : Jules doit pouvoir créer une facture en < 3 min et la soumettre à URSSAF.
**Total Points** : 16 pts
**Dépendances** : Epic 1 (clients inscrits)

#### US-2.1 : Créer facture (formulaire web)
**Points** : 5
**Priorité** : P0 (MVP critical)
**Description** : Interface web pour remplir heures, tarif, client, dates. Formulaire valide et sauvegarde BROUILLON.

**Acceptance Criteria**
- [ ] Formulaire web (FastAPI + Jinja2) avec champs : client (dropdown), heures (nombre), tarif (€), dates (debut/fin)
- [ ] Calcul auto montant total (heures × tarif)
- [ ] Dropdown client pré-rempli si utilisé récemment
- [ ] Validation côté serveur : heures > 0, tarif > 0, client sélectionné
- [ ] Dropdown client filtrable (recherche par nom)
- [ ] Sauvegarde immediat en Sheets onglet Factures statut BROUILLON
- [ ] Confirmation utilisateur : "Facture créée, ID: {id}"
- [ ] Bouton modifier/annuler tant que BROUILLON
- [ ] Temps création < 3 min (mesurable)

**Technical Notes**
- Composants : FastAPI route POST /invoices + InvoiceService
- Sheets columns : facture_id (UUID), client_id, type_unite (heure), nature_code (BNC), quantite, montant_unitaire, montant_total (formule), date_debut, date_fin, description, statut, urssaf_demande_id, dates_suivi, pdf_drive_id
- Validation form stricte (montant ≥ 1€, dates cohérentes)

**Tasks**
1. **Tâche 2.1.1** : Design formulaire HTML + Tailwind (2h)
   - Type: Frontend
2. **Tâche 2.1.2** : Implémenter route POST /invoices + validation (4h)
   - Type: Implementation
   - Dépendances: SheetsAdapter.write_invoice()
3. **Tâche 2.1.3** : Tests formulaire (validation, calculs) (3h)
   - Type: Testing
4. **Tâche 2.1.4** : E2E test création facture (3h)
   - Type: Testing

**Definition of Done**
- [ ] Formulaire load < 1s
- [ ] Validation erreurs affichées en temps réel
- [ ] Facture apparaît dans Sheets < 5s après submit
- [ ] Tests passent (happy path + edge cases)

---

#### US-2.2 : Générer PDF facture
**Points** : 5
**Priorité** : P0 (MVP critical - légal)
**Description** : Générer PDF professionnel avec logo Jules, détails facture, conditions paiement. Stocker dans Google Drive.

**Acceptance Criteria**
- [ ] PDF généré automatiquement lors création facture
- [ ] Template PDF inclus : logo Jules, SIREN 991552019, adresse, dates, montant, nature (BNC), "Demande de paiement URSSAF"
- [ ] Logo chargé depuis Google Drive
- [ ] PDF nommé `Facture_{client_id}_{date}.pdf`
- [ ] PDF uploadé dans Google Drive dossier "Factures/2026"
- [ ] Lien PDF accessible depuis UI + Sheets
- [ ] Rendu correct (pas de déformation texte, police lisible)
- [ ] Format A4

**Technical Notes**
- Technologie : WeasyPrint (HTML → PDF)
- Template HTML jinja2 réutilisable
- Upload via Google Drive API (PDFGenerator component)
- Fallback : si WeasyPrint fail, générer HTML versio simple à télécharger

**Tasks**
1. **Tâche 2.2.1** : Design template PDF HTML (3h)
   - Type: Design
2. **Tâche 2.2.2** : Implémenter WeasyPrint wrapper (3h)
   - Type: Implementation
3. **Tâche 2.2.3** : Intégrer Google Drive upload (3h)
   - Type: Implementation
4. **Tâche 2.2.4** : Tests visuels PDF (2h)
   - Type: Testing

**Definition of Done**
- [ ] PDF généré en < 2s
- [ ] Logo visible et bien dimensionné
- [ ] Tous champs facture présents et lisibles
- [ ] Google Drive upload réussit > 95% cas

---

#### US-2.3 : Soumettre facture à URSSAF
**Points** : 5
**Priorité** : P0 (MVP critical)
**Description** : Envoyer facture à URSSAF via API POST /demandes-paiement. Récupérer id_demande et statut CREE.

**Acceptance Criteria**
- [ ] Bouton "Soumettre à URSSAF" visible tant que facture en BROUILLON
- [ ] Pré-check : client inscrit URSSAF (sinon auto-inscrire, voir US-1.1)
- [ ] Validation payload : montant, type_unite, nature_code, dates, client_id
- [ ] Appel API URSSAF POST /demandes-paiement avec tous champs requis
- [ ] Récupération `id_demande` (token URSSAF)
- [ ] Mise à jour Sheets : statut BROUILLON → SOUMIS → CREE
- [ ] Message succès : "Facture soumise, ID demande: {id_demande}"
- [ ] Message erreur si API fail (affichage clair, suggestion action)
- [ ] Retry automatique max 3x si timeout
- [ ] Pas de ré-soumission si déjà CREE (idempotent)

**Technical Notes**
- Composant : InvoiceService.submit_invoice() → URSSAFClient
- Payload URSSAF structure (à valider avec API docs) : id_client, montant, nature_code, date_debut, date_fin, etc.
- Gestion états : BROUILLON → SOUMIS (appel en cours) → CREE (réussi) ou ERREUR (échec)

**Tasks**
1. **Tâche 2.3.1** : Valider payload URSSAF structure + doc (2h)
   - Type: Research
2. **Tâche 2.3.2** : Implémenter InvoiceService.submit_invoice() (4h)
   - Type: Implementation
3. **Tâche 2.3.3** : Intégrer retry logic + error handling (3h)
   - Type: Implementation
4. **Tâche 2.3.4** : Tests soumission URSSAF (mock + integration) (4h)
   - Type: Testing

**Definition of Done**
- [ ] API appel effectué sans erreur
- [ ] id_demande sauvegardé dans Sheets
- [ ] Statut CREE visible immédiatement après
- [ ] Erreurs affichées utilisateur, logs serveur complets

---

#### US-2.4 : Annuler brouillon facture
**Points** : 1
**Priorité** : P1 (Support)
**Description** : Jules peut annuler facture tant qu'en BROUILLON (avant soumission).

**Acceptance Criteria**
- [ ] Bouton "Annuler" visible si statut BROUILLON
- [ ] Clique → statut ANNULE, facture plus modifiable
- [ ] Pas de suppression (audit trail)

---

### Epic 3 : Polling Automatique Statuts (P0 - Suivi)

**Objectif métier** : Système met à jour automatiquement statuts factures toutes les 4h.
**Total Points** : 8 pts
**Dépendances** : Epic 2 (factures existent)

#### US-3.1 : Implémenter cron polling URSSAF 4h
**Points** : 5
**Priorité** : P0 (MVP critical)
**Description** : Scheduler automatique qui appelle URSSAF toutes les 4h pour mettre à jour statuts factures.

**Acceptance Criteria**
- [ ] Cron job s'exécute toutes les 4h (UTC)
- [ ] Lit factures avec statut SOUMIS, CREE, EN_ATTENTE, VALIDE
- [ ] Appel GET /demandes-paiement/{id_demande} pour chaque
- [ ] Mise à jour Sheets si changement : CREE → EN_ATTENTE → VALIDE → PAYE
- [ ] Statuts mai jamais rétrograder (VALIDE → CREE = erreur, log)
- [ ] Duplicate prevention : ne pas re-poll facture RAPPROCHE
- [ ] Log chaque appel (timestamp, facture_id, ancien_statut → nouveau_statut)
- [ ] Gestion timeout API : retry dans 1h si timeout
- [ ] Pas d'email utilisateur si pas changement

**Technical Notes**
- Composant : PaymentTracker (service) + APScheduler
- Idempotent : même poll plusieurs fois = même résultat
- Lock mécanisme : utiliser `last_polled` timestamp dans Sheets pour eviter race condition
- Timezone : toujours UTC internals, afficher heure locale dashboard

**Tasks**
1. **Tâche 3.1.1** : Configurer APScheduler (2h)
   - Type: Implementation
2. **Tâche 3.1.2** : Implémenter PaymentTracker.poll_all() (4h)
   - Type: Implementation
3. **Tâche 3.1.3** : Tests scheduler (timezone, idempotence) (4h)
   - Type: Testing

**Definition of Done**
- [ ] Cron tourne sans erreur 24h
- [ ] Statuts Sheets mise à jour correctement après poll
- [ ] Logs détaillés pour chaque cycle

---

#### US-3.2 : Reminder T+36h si client n'a pas validé
**Points** : 3
**Priorité** : P1 (UX amélioration)
**Description** : Si facture reste EN_ATTENTE après 36h, envoyer email à Jules pour relancer client.

**Acceptance Criteria**
- [ ] Détection : temps écoulé depuis statut CREE ou EN_ATTENTE
- [ ] Trigger : si 36h < temps < 48h et statut EN_ATTENTE
- [ ] Email envoyé à Jules (sujet clair, contient client name + montant + lien facture)
- [ ] Pas de re-email si déjà envoyé (flag dans Sheets)
- [ ] Template email professionnel
- [ ] Gestion SMTP fail : log erreur, re-try next cycle

**Technical Notes**
- Appelé par PaymentTracker lors polling
- Composant : NotificationService → EmailNotifier

**Tasks**
1. **Tâche 3.2.1** : Templater email reminder (1h)
   - Type: Design
2. **Tâche 3.2.2** : Implémenter NotificationService (2h)
   - Type: Implementation
3. **Tâche 3.2.3** : Tests email (mock SMTP) (2h)
   - Type: Testing

**Definition of Done**
- [ ] Email envoyé sans erreur
- [ ] Template lisible + actionnable

---

### Epic 4 : Dashboard & Visibilité (P0 - User Experience)

**Objectif métier** : Jules voit toutes ses factures, statuts à jour, en une seule vue.
**Total Points** : 9 pts
**Dépendances** : Epic 2-3

#### US-4.1 : Dashboard factures (liste + filtres)
**Points** : 5
**Priorité** : P0 (MVP critical)
**Description** : Tableau web affichant toutes les factures, statuts, montants, dates. Filtres par statut/client/date.

**Acceptance Criteria**
- [ ] Tableau HTML (FastAPI + Jinja2 + Tailwind)
- [ ] Colonnes visibles : Facture ID, Client, Montant, Dates, Statut, Dernière mise à jour
- [ ] Statuts codés couleur : vert (OK), orange (attente), rouge (problème)
- [ ] Filtres : par statut dropdown, par client, par plage date
- [ ] Tri : par date création (plus récent en haut), par montant, par statut
- [ ] KPIs en haut : Total CA (factures PAYE), Nb factures EN_ATTENTE, Prochaine deadline rappel
- [ ] Lien vers PDF facture
- [ ] Responsive mobile (liste simplifiée)
- [ ] Load < 2s pour 50 factures
- [ ] Auto-refresh 30s (polling JS, spinner discret)

**Technical Notes**
- Route : GET /
- Sheets adapter : read_invoices_by_filters(status, client_id, date_range)
- Frontend : Bootstrap ou Tailwind, pagination 50/page

**Tasks**
1. **Tâche 4.1.1** : Design layout dashboard HTML (3h)
   - Type: Frontend
2. **Tâche 4.1.2** : Implémenter route + filtres (4h)
   - Type: Implementation
3. **Tâche 4.1.3** : Frontend JS auto-refresh (2h)
   - Type: Frontend
4. **Tâche 4.1.4** : Tests perf + filtering (3h)
   - Type: Testing

**Definition of Done**
- [ ] Dashboard load < 2s
- [ ] Filtres fonctionnent correctement
- [ ] Statuts affichés correctement
- [ ] KPIs calculés juste

---

#### US-4.2 : Export CSV factures
**Points** : 2
**Priorité** : P2 (Nice-to-have)
**Description** : Bouton export CSV pour utilisation comptable externe.

**Acceptance Criteria**
- [ ] Bouton "Export CSV" dans dashboard
- [ ] Format UTF-8 BOM, délimiteur `,`
- [ ] Colonnes : facture_id, client_nom, montant, nature_code, dates, statut, pdf_link
- [ ] Applique filtres actuels (si filtrés, exporte que résultats filtrés)
- [ ] Nom fichier : `SAP-Facture_Factures_{YYYYMMDD}.csv`
- [ ] Téléchargement direct navigateur

**Technical Notes**
- Utilise Python csv.writer (gère escaping UTF-8)

**Tasks**
1. **Tâche 4.2.1** : Implémenter route export CSV (2h)
   - Type: Implementation
2. **Tâche 4.2.2** : Tests CSV format + intégration (1h)
   - Type: Testing

---

#### US-4.3 : Page gestion clients
**Points** : 2
**Priorité** : P1 (Support)
**Description** : Interface pour voir/éditer clients (avant inscription URSSAF si besoin).

**Acceptance Criteria**
- [ ] Route GET /clients → liste clients
- [ ] Bouton créer nouveau client
- [ ] Affichage : client_id, nom, email, urssaf_id, statut_urssaf, date_inscription
- [ ] Bouton modifier (nom, email, adresse) si pas encore facturé
- [ ] Suppression logique (flag archive, pas vraiment delete)

---

### Epic 5 : Rapprochement Bancaire (P1 - Phase 2)

**Objectif métier** : Lettrage automatique factures URSSAF ↔ virements Swan.
**Total Points** : 12 pts
**Dépendances** : Epic 3 (factures PAYE), Swan API credentials

#### US-5.1 : Importer transactions Swan
**Points** : 3
**Priorité** : P1 (Phase 2 start)
**Description** : Appel API Swan pour récupérer transactions bancaires, stockage dans Sheets onglet Transactions.

**Acceptance Criteria**
- [ ] Appel GET API Swan (GraphQL ou REST) pour last 30 jours transactions
- [ ] Filtre : entré incoming (virements reçus)
- [ ] Import dans Sheets onglet Transactions : transaction_id, swan_id, date_valeur, montant, libelle, type, source
- [ ] De-duplication : pas d'import doublon même si appelé 2x
- [ ] Fallback : si API Swan down, utiliser cache 24h
- [ ] Tri : date décroissant (plus récent d'abord)

**Technical Notes**
- Composant : SwanClient
- Gestion : BankReconciliation component

**Tasks**
1. **Tâche 5.1.1** : Implémenter SwanClient (3h)
   - Type: Implementation
2. **Tâche 5.1.2** : Tests mock Swan API (2h)
   - Type: Testing

---

#### US-5.2 : Lettrage automatique factures ↔ transactions
**Points** : 5
**Priorité** : P1 (Phase 2 core)
**Description** : Pour chaque facture PAYEE, chercher transaction correspondante. Scoring confiance (montant, date, libelle).

**Acceptance Criteria**
- [ ] Matching automatique : montant = 100% facture, date ±5j, libelle contient URSSAF
- [ ] Scoring confiance : montant exact = +50, date < 3j = +30, libelle URSSAF = +20
- [ ] Score >= 80 → LETTRE AUTO (statut facture RAPPROCHE)
- [ ] Score 50-80 → A_VERIFIER (surligné orange, Jules confirme)
- [ ] Score < 50 → PAS_DE_MATCH (attendre virement)
- [ ] Écriture dans onglet Lettrage : facture_id, montant_facture, txn_id, txn_montant, ecart, score_confiance, statut
- [ ] Gestion écart : si montant differ < 2€, accepter (frais bancaires)
- [ ] Idempotent : relancer réconciliation = même résultat

**Technical Notes**
- Composant : BankReconciliation.reconcile()
- Logique scoring : à affiner avec cas réels

**Tasks**
1. **Tâche 5.2.1** : Implémenter algo matching + scoring (5h)
   - Type: Implementation
2. **Tâche 5.2.2** : Tests matching (happy path + edge cases) (4h)
   - Type: Testing

---

#### US-5.3 : Mise à jour onglet Balances (formules)
**Points** : 2
**Priorité** : P1 (Phase 2 support)
**Description** : Après lettrage, mettre à jour onglet Balances (soldes, nb non-lettrées, CA).

**Acceptance Criteria**
- [ ] Recalcul automatique après lettrage
- [ ] Onglet Balances : mois, nb_factures, ca_total, recu_urssaf, solde, nb_non_lettrees, nb_en_attente
- [ ] Formules auto-calc (pas de hard-code)

---

#### US-5.4 : Interface lettrage manuel (A_VERIFIER)
**Points** : 2
**Priorité** : P1 (Phase 2 UX)
**Description** : Page pour Jules de vérifier/confirmer matches ambigus (score < 80).

**Acceptance Criteria**
- [ ] Route POST /reconcile
- [ ] Affiche factures "A_VERIFIER" (orange)
- [ ] Pour chaque match ambigu : facture vs. transaction proposée, score, differences
- [ ] Bouton "Valider" (user confirme lettrage) ou "Rejeter" (pas ce match)
- [ ] Après validation, statut facture → RAPPROCHE

---

### Epic 6 : CLI Avancée (P2 - Confort)

**Objectif métier** : Jules peut gérer factures en ligne de commande (batch, automation).
**Total Points** : 7 pts
**Dépendances** : Epic 2-3

#### US-6.1 : CLI `sap submit` (créer + soumettre facture)
**Points** : 3
**Priorité** : P2 (Nice-to-have)
**Description** : Commande CLI pour créer et soumettre facture directement.

**Usage**
```bash
sap submit --client <id> --hours 1.5 --rate 30 --date 2026-03-15
sap submit --json factures.json
```

**Acceptance Criteria**
- [ ] Arguments : client ID, hours (nombre), rate (€/h), date (YYYY-MM-DD)
- [ ] Alternative JSON file pour batch
- [ ] Affichage : "✓ Facture créée, soumise, ID: {id_demande}"
- [ ] Exit code 0 (succès) ou 1 (erreur)
- [ ] Erreurs affichées lisiblement

**Technical Notes**
- Utilise Python Click framework

**Tasks**
1. **Tâche 6.1.1** : Implémenter CLI submit command (3h)
   - Type: Implementation
2. **Tâche 6.1.2** : Tests CLI (args, JSON parsing) (2h)
   - Type: Testing

---

#### US-6.2 : CLI `sap sync` (polling immédiat)
**Points** : 2
**Priorité** : P2 (Confort)
**Description** : Forcer appel immédiat polling URSSAF (au lieu attendre 4h).

**Usage**
```bash
sap sync
```

**Acceptance Criteria**
- [ ] Appel GET URSSAF pour toutes factures en cours
- [ ] Affichage tableau statuts
- [ ] Mise à jour Sheets immédiat
- [ ] Durée : < 30 sec

---

#### US-6.3 : CLI `sap reconcile` (lettrage immédiat)
**Points** : 2
**Priorité** : P2 (Phase 2 nice)
**Description** : Forcer appel immédiat Swan + lettrage (au lieu polling manuel).

**Usage**
```bash
sap reconcile
```

**Acceptance Criteria**
- [ ] Appel Swan + matching factures
- [ ] Affichage : résumé (AUTO: X, A_VERIFIER: Y, PAS_MATCH: Z)
- [ ] Sheets lettrage mise à jour
- [ ] Durée : < 20 sec

---

### Epic 7 : Infrastructure & DevOps (P0 - Fondatrice)

**Objectif métier** : Application déployable, logs, monitoring, config.
**Total Points** : 5 pts
**Dépendances** : Toutes les features

#### US-7.1 : Configuration .env sécurisée
**Points** : 1
**Priorité** : P0 (Non-négociable)
**Description** : Gérer secrets (URSSAF_CLIENT_SECRET, SWAN_API_KEY, Google credentials, SMTP).

**Acceptance Criteria**
- [ ] `.env` chargé via pydantic-settings
- [ ] `.env` jamais committé (`.gitignore`)
- [ ] Credentials validés au démarrage
- [ ] Template `.env.example` dans repo

---

#### US-7.2 : Logging structuré
**Points** : 2
**Priorité** : P0 (Debug essential)
**Description** : Logs détaillés pour chaque opération (création facture, appels API, erreurs).

**Acceptance Criteria**
- [ ] Logger Python structuré (timestamps, level, operation)
- [ ] Logs : création facture, appel URSSAF, poll cycle, erreurs API
- [ ] Pas d'exposition secrets dans logs
- [ ] Rotation logs (max 7 jours, 10 MB fichier)

---

#### US-7.3 : Monitoring basique
**Points** : 2
**Priorité** : P1 (Phase 2)
**Description** : Alertes sur erreurs critiques (API URSSAF down, polling fail).

**Acceptance Criteria**
- [ ] Dashboard logs errors (fichier ou simple page web)
- [ ] Email alert si API URSSAF fail > 3x consécutif
- [ ] Métriques : uptime, API success rate, avg response time

---

## Section 2 : Sprint 1 — Infrastructure + Core URSSAF (Jours 1-5)

**Objectif Sprint** : Jules peut créer un client URSSAF et soumettre une facture complète.
**Velocity Cible** : 12 points
**Durée** : 5 jours (lun-ven)

### Committed Stories

| Story ID | Titre | Points | Priorité | Effort (jours) |
|----------|-------|--------|----------|---------|
| US-1.1 | Inscrire client URSSAF | 5 | P0 | 1.5 |
| US-1.2 | Importer clients depuis Sheets | 2 | P0 | 0.5 |
| US-2.1 | Créer facture (form web) | 5 | P0 | 1.5 |
| **Total Sprint 1** | | **12** | | **3.5 jours dev** |

**Reserve Buffer** : 1.5 jours (tests, fixes, intégration)

### Découpage Journalier (Ideal Timeline)

**Jour 1 (Lundi)**
- AM : Setup repo, config OAuth2 URSSAF, .env template
- PM : Implémenter URSSAFClient (base), tests unitaires
- EOD : Token refresh logic testé

**Jour 2 (Mardi)**
- AM : Finir ClientService, error handling inscription
- PM : Intégrer SheetsAdapter.read/write_clients(), tests Sheets
- EOD : Inscription client fonctionnelle (e2e test 1 client)

**Jour 3 (Mercredi)**
- AM : Design formulaire facture HTML (Tailwind)
- PM : Implémenter route POST /invoices, validation
- EOD : Création facture sauvegardée BROUILLON dans Sheets

**Jour 4 (Jeudi)**
- AM : Implémenter InvoiceService.submit_invoice()
- PM : Tests soumission URSSAF, gestion erreurs
- EOD : Soumission facture complète, statut CREE visible

**Jour 5 (Vendredi)**
- AM : E2E test complet (client → facture → URSSAF)
- PM : Code review, fixes mineurs, docs
- EOD : **MVP 1a livrable** (client + facture + soumission fonctionne)

### Key Deliverables

- [ ] 1 client créé dans URSSAF via API ✓
- [ ] 1 facture créée web, PDF généré localement ✓
- [ ] 1 facture soumise URSSAF, statut CREE reçu ✓
- [ ] Sheets Clients + Factures onglets remplis correctement ✓
- [ ] Tests e2e couvrent parcours complet (0 erreur 3 runs) ✓
- [ ] Erreurs gérées, user-facing messages clairs ✓
- [ ] Code review clean, merge main ✓

### Dependencies & Blockers

**Externe (résoudre avant Jour 1)**
- [ ] URSSAF_CLIENT_ID, URSSAF_CLIENT_SECRET disponibles
- [ ] Google Sheets service account credentials
- [ ] Accès API URSSAF sandbox (test mode)

**Interne**
- Story US-1.1 bloque US-2.1 (client doit exister)
- US-1.2 peut paralléliser avec US-1.1 (mais pas essentiel)

### Risks & Mitigations

| Risk | Prob | Impact | Mitigation |
|------|------|--------|-----------|
| URSSAF API non disponible sandbox | Moyen (40%) | Haut | Contacter support URSSAF T-1 jour, mock endpoint if needed |
| Google Sheets API quota limit | Bas (15%) | Moyen | Vérifier quota initial, pré-filter reads |
| WeasyPrint problème rendering | Bas (20%) | Moyen | Fallback HTML simple, pas critique Sprint 1 |
| OAuth2 token refresh timing | Moyen (35%) | Moyen | Tester expires_in, cache token 59min |

---

## Section 3 : Sprint 2 — Dashboard + Polling (Jours 6-10)

**Objectif Sprint** : Jules voit ses factures sur dashboard, système met à jour statuts auto 4h.
**Velocity Cible** : 14 points
**Dépendances** : Sprint 1 complété

### Committed Stories

| Story ID | Titre | Points | Priorité | Effort (jours) |
|----------|-------|--------|----------|---------|
| US-2.2 | Générer PDF facture | 5 | P0 | 1.5 |
| US-3.1 | Cron polling URSSAF 4h | 5 | P0 | 1.5 |
| US-4.1 | Dashboard factures | 5 | P0 | 1.5 |
| US-4.2 | Export CSV | 2 | P2 | 0.5 |
| US-3.2 | Reminder T+36h | 3 | P1 | 0.5 |
| **Total Sprint 2** | | **20** | | **5.5 jours dev** |

**Réduction à 14 pts** : Reporter US-3.2 + US-4.2 à Sprint 3 si needed

### Découpage Journalier

**Jour 6 (Lundi)**
- AM : Design template PDF HTML, logo import
- PM : Implémenter WeasyPrint wrapper, Google Drive upload
- EOD : PDF généré et uploadé avec succès

**Jour 7 (Mardi)**
- AM : Configurer APScheduler, base PaymentTracker
- PM : Implémenter polling logic, Sheets update
- EOD : Cron exécuté 1x, statuts mise à jour

**Jour 8 (Mercredi)**
- AM : Design dashboard layout, filtres HTML
- PM : Route GET /, Sheets query avec filters
- EOD : Dashboard affiche 5+ factures, filtres travaillent

**Jour 9 (Jeudi)**
- AM : Frontend JS auto-refresh 30s, spinner
- PM : Tests perf (load < 2s), E2E dashboard
- EOD : Dashboard responsive, filtres + refresh fonctionnel

**Jour 10 (Vendredi)**
- AM : Export CSV route, tests format
- PM : Sprint review, code review final, docs
- EOD : **MVP 1b livrable** (full dashboard + polling 4h)

### Key Deliverables

- [ ] PDF valide généré, stocké Google Drive ✓
- [ ] Polling cron 4h exécuté sans erreur 72h ✓
- [ ] Dashboard affiche ≥3 factures avec statuts corrects ✓
- [ ] Statuts se mettent à jour auto en Dashboard ✓
- [ ] Export CSV ouverture Excel sans corruption ✓
- [ ] Tests e2e étape par étape (création → soumission → poll → dashboard) ✓
- [ ] Perf : Dashboard charge en < 2s (5 factures) ✓
- [ ] Aucune requête API timeout > 10s ✓

### Risks & Mitigations

| Risk | Prob | Impact | Mitigation |
|------|------|--------|-----------|
| Polling loop race condition | Moyen (40%) | Haut | Utiliser lock DB (`last_polled` timestamp) |
| Email SMTP fail | Bas (25%) | Bas | Fallback : log alert, pas critique Sprint 2 |
| Sheets formulas trop lentes | Très bas (10%) | Moyen | Pre-filter rows, cache 1h |
| PDF rendering inconsistent | Bas (25%) | Moyen | Tests visuels, fallback HTML |

---

## Section 4 : Sprint 3 — Rapprochement + Features Avancées (Jours 11-15)

**Objectif Sprint** : Lettrage automatique factures ↔ virements Swan, CLI avancée.
**Velocity Cible** : 16 points
**Dépendances** : Sprint 2 complété, Swan API credentials

### Committed Stories

| Story ID | Titre | Points | Priorité | Effort (jours) |
|----------|-------|--------|----------|---------|
| US-5.1 | Importer transactions Swan | 3 | P1 | 1 |
| US-5.2 | Lettrage auto factures | 5 | P1 | 1.5 |
| US-5.3 | Mise à jour Balances | 2 | P1 | 0.5 |
| US-5.4 | Interface lettrage manuel | 2 | P1 | 0.5 |
| US-6.1 | CLI sap submit | 3 | P2 | 1 |
| US-6.2 | CLI sap sync | 2 | P2 | 0.5 |
| US-7.1 | Config .env sécurisée | 1 | P0 | 0.25 |
| US-7.2 | Logging structuré | 2 | P0 | 0.75 |
| **Total Sprint 3** | | **20** | | **6 jours dev** |

**Réduction à 16 pts** : Reporter US-5.3 + US-5.4 + US-7.2 à Phase 2 follow-up si needed

### Découpage Journalier

**Jour 11 (Lundi)**
- AM : Implémenter SwanClient, tests mock
- PM : BankReconciliation.reconcile() base, matching algo
- EOD : Transactions Swan importées, matching test

**Jour 12 (Mardi)**
- AM : Finir scoring confiance, lettrage auto/à vérifier
- PM : Tests matching edge cases (écarts €, dates, libelles)
- EOD : Lettrage AUTO (score ≥ 80) fonctionnel

**Jour 13 (Mercredi)**
- AM : Interface POST /reconcile pour A_VERIFIER
- PM : Frontend validation manuelle, Sheets update
- EOD : Jules peut confirmer matches ambigus

**Jour 14 (Jeudi)**
- AM : Implémenter CLI sap submit + sap sync
- PM : Tests CLI (args parsing, JSON batch)
- EOD : Commandes CLI testées et documentées

**Jour 15 (Vendredi)**
- AM : Finir logging + config .env, sécurité
- PM : Sprint review, code review final
- EOD : **MVP complet + Phase 2 start livrable**

### Key Deliverables

- [ ] Transactions Swan importées Sheets ✓
- [ ] Lettrage AUTO (score ≥ 80) fonctionnel ✓
- [ ] Lettrage À_VERIFIER identifiées (orange) ✓
- [ ] Onglet Balances recalculé après lettrage ✓
- [ ] CLI sap submit créé + soumis facture ✓
- [ ] CLI sap sync polling immédiat ✓
- [ ] .env sécurisé (credentials pas loggés) ✓
- [ ] Logging détaillé pour debug ✓
- [ ] Tests e2e complet (client → facture → URSSAF → Swan → lettrage) ✓

---

## Section 5 : Definitions of Ready & Done

### Definition of Ready (Avant Sprint Start)

Une story est "Ready" si :

- [ ] Story description complète avec acceptance criteria explicités
- [ ] Composants système identifiés (services, routes, Sheets columns)
- [ ] Dépendances externes validées (API, credentials, libs)
- [ ] Effort estimé (points story)
- [ ] Test scenarios listés (happy path + edge cases)
- [ ] Product Owner a validé (priorité OK)

### Definition of Done (After Sprint End)

Une story est "Done" si :

- [ ] Code implémenté (composant principal + integrations)
- [ ] Unit tests écrits et passants (min 80% path heureux + edge cases)
- [ ] Integration tests (avec stubs si APIs externes)
- [ ] E2E test (full flow du point vue utilisateur)
- [ ] Code review approuvé (pas de warnings)
- [ ] Documentation mise à jour (README, API docs, comments)
- [ ] Performance validée (< 3s création facture, < 2s dashboard)
- [ ] Erreurs gérées gracieusement (user messages clairs, logs détaillés)
- [ ] Pas d'exposition secrets (credentials, tokens, emails)
- [ ] Merge sur main + branch supprimée

---

## Section 6 : Estimation de Capacité & Velocity

### Assumptions

**Team Size** : 1 développeur full-stack
**Sprint Length** : 5 jours (lun-ven)
**Heures par jour** : 8h (excluant meetings)

### Velocity Historical

Baseline (première estimation MVP) :
- **Sprint 1** : 12 points (3.5j dev + 1.5j buffer/tests)
- **Sprint 2** : 14 points (4j dev + 1j buffer)
- **Sprint 3** : 16 points (4.5j dev + 0.5j buffer)

**Total 42 points** pour MVP complet + Phase 2 début

### Capacity Planning

**Disponibilité réelle par sprint**
- Jours: 5
- Heures: 40h
- Réunions (standups, review, retro): 3h
- **Heures dev réelles**: 37h/sprint

**Points/Heure Ratio**
- Estimation : 0.3 points/heure (complexité moyenne URSSAF + APIs)
- **Velocity réaliste** : ~11 points/sprint (37h × 0.3)

**Ajustement recommandé**
- Réduire Sprint 1 à 10 pts (buffer 20%)
- Réduire Sprint 2 à 12 pts
- Réduire Sprint 3 à 14 pts
- **Total 36 pts** = plus réaliste

---

## Section 7 : Risques & Mitigations Sprint par Sprint

### Sprint 1 Risques Critiques

| Risk | Prob | Impact | Mitigation |
|------|------|--------|-----------|
| URSSAF API credentials non dispo | Moyen (45%) | Critique | Obtenir T-2 jours, tester connexion |
| Payload URSSAF mal documenté | Moyen (40%) | Haut | Contacter support URSSAF, reverse-engineer |
| Google Sheets quota limit atteint | Bas (10%) | Haut | Vérifier quota, demander augmentation early |
| OAuth2 refresh timing bug | Moyen (35%) | Haut | Tests automatisés refresh, alerte 5min avant expiry |

### Sprint 2 Risques Critiques

| Risk | Prob | Impact | Mitigation |
|------|------|--------|-----------|
| Polling race condition (doublon) | Moyen (40%) | Haut | Lock DB via `last_polled`, tests concurrence |
| WeasyPrint font rendering | Bas (20%) | Moyen | Tests visuels PDF, fallback HTML |
| Sheets API timeout sous polling load | Bas (15%) | Moyen | Pagination, cache, async calls si needed |

### Sprint 3 Risques Critiques

| Risk | Prob | Impact | Mitigation |
|------|------|--------|-----------|
| Swan API non documenté / unstable | Moyen (35%) | Haut | Contacter Swan early, tests with sandbox |
| Matching score < 80% en prod | Moyen (40%) | Moyen | Affiner algo avec données réelles, UI fallback |
| CLI args parsing erreurs | Bas (15%) | Bas | Validation stricte, help text détaillé |

---

## Section 8 : Ceremonies Proposées (Jours 1-15)

### Daily Standup (15 min)
**Quand** : 09:00 chaque jour (lun-ven)
**Format** :
- What I did yesterday
- What I'm doing today
- Blockers/help needed

**Notes** : Alternatif async si 1 dev solo (Slack message EOD)

### Sprint Planning (2h)
**Quand** : Jour 1 matin (avant dev)
**Format** :
- Review backlog priorisé (Product Owner)
- Sélection stories pour sprint
- Estimation effort + task breakdown
- Identifier dépendances/blockers

### Daily Standup Alternatif (Async)
**Si solo dev** : Slack channel `#sap-sprint` messages EOD
```
✅ DONE: US-2.1 form validation
🔨 IN PROGRESS: US-2.1 route POST /invoices
🚧 BLOCKED: Waiting URSSAF credentials
```

### Sprint Review (1.5h)
**Quand** : Jour 5 après-midi (ven)
**Attendees** : Dev + Product Owner (Jules optionnel)
**Format** :
- Demo stories complétées (live ou vidéo)
- Metrics : velocity, bugs escapés, tests coverage
- Feedback Product Owner

### Sprint Retrospective (1h)
**Quand** : Jour 5 fin après-midi (ven)
**Format** :
- What went well
- What needs improvement
- Actions pour prochain sprint

---

## Section 9 : Monitoring & Success Metrics

### Sprint Velocity Tracking

**Spreadsheet simple** (ou Jira si disponible)

| Sprint | Planned (pts) | Completed (pts) | Velocity | Burn Rate |
|--------|--------------|-----------------|----------|-----------|
| Sprint 1 | 12 | TBD | TBD | TBD |
| Sprint 2 | 14 | TBD | TBD | TBD |
| Sprint 3 | 16 | TBD | TBD | TBD |

### Quality Metrics (End of Each Sprint)

- **Test Coverage** : Target 80%+ (measured by pytest-cov)
- **Bugs Escapés** : Target 0 critical, < 2 medium per sprint
- **Performance** : Creation < 3s, Dashboard < 2s, API calls < 10s
- **Uptime** : Target 99%+ (measured by cron logs)

### User Satisfaction (End of Phase 1 MVP)

- **Time to Create Facture** : Baseline 15min → Target 2min
- **Validation Client Rate** : Baseline 70% → Target 95% (avec reminder)
- **Lettrage Auto Rate** : Baseline 0% → Target 80%
- **Error Rate** : Baseline 5% → Target 0%

---

## Section 10 : Recommandations & Next Steps

### Avant Sprint 1 Start (T-2 jours)

1. **Valider Credentials Externes**
   - [ ] URSSAF OAuth2 client_id + client_secret (sandbox)
   - [ ] Swan API key (sandbox)
   - [ ] Google Service Account JSON
   - [ ] SMTP credentials (ou setup GMail)

2. **Valider Documentation API**
   - [ ] URSSAF endpoint `/particuliers` et `/demandes-paiement` structure
   - [ ] Swan GraphQL schema (ou REST endpoints)
   - [ ] Google Sheets API rate limits

3. **Setup Repository**
   - [ ] Repo structure (src/app, tests, docs, config)
   - [ ] .env.example template
   - [ ] GitHub Actions pour CI/CD (optional Sprint 1)

4. **Plan Communication**
   - [ ] Standup daily async (Slack) ou 09:00 meeting
   - [ ] Sprint review/retro Friday
   - [ ] Contact URSSAF support pour questions API

### Après Sprint 1 (Gate Décision)

**Critères Go/No-Go Sprint 2** :
- [ ] E2E test complet : client → facture → URSSAF reçoit (0 erreur 3 runs)
- [ ] Pas de data loss (Sheets intégrité)
- [ ] Erreurs URSSAF gérées gracieusement
- [ ] Code review clean (main branch)

**Si NO-GO** : 2-3 jours fixes + retest, puis décision

### Après Sprint 2 (Gate Décision)

**Critères Go/No-Go Sprint 3** :
- [ ] Dashboard affiche données correctes
- [ ] Polling 4h tourne 72h sans erreur
- [ ] Performance < 2s dashboard pour 50 factures

### Après Sprint 3 (Livraison MVP)

**Production Readiness Checklist** :
- [ ] All stories Done
- [ ] No critical/high bugs
- [ ] Documentation complète (README, API docs)
- [ ] Monitoring configuré (error alerts)
- [ ] Backup plan si API down
- [ ] Jules trained + comfortable using

**Deployment Plan** :
- [ ] Test environment (staging)
- [ ] Production environment (cloud ou VPS)
- [ ] Data migration (manual initial)
- [ ] Monitoring + alerting setup

---

## Section 11 : Dépendances & Blockers Critiques

### Dépendances Externes (Résoudre T-3 jours)

| Dépendance | Détail | Owner | Status |
|-----------|--------|-------|--------|
| URSSAF credentials | OAuth2 sandbox client_id/secret | Jules | TBD |
| Swan API key | Sandbox token | Jules | TBD |
| Google Service Account | JSON credentials | Jules | TBD |
| SMTP relay | Email service (Gmail free ou payant) | Jules | TBD |
| Google Sheets document | ID du spreadsheet (8 onglets créés) | Jules | TBD |

### Blockers Potentiels (Mitigations)

| Blocker | Mitigation | Fallback |
|---------|-----------|----------|
| URSSAF API non réactive | Contacter support T-3j | Mock endpoint local pour tests |
| Swan API docs incomplets | Reverse-engineer ou contacter | Importer transactions manuellement CSV |
| Google quota limit | Demander augmentation | Cache/pre-filter requests |
| Cron job système unavailable | APScheduler (Python) vs. system cron | Manual polling button dans UI |

---

## Section 12 : Checklist Pre-Sprint Launch

### Dev Environment

- [ ] Python 3.9+ installed
- [ ] FastAPI, Click, gspread libraries
- [ ] pytest + pytest-cov installed
- [ ] .env.example créé et documenté
- [ ] Database schema (Sheets) créé avec 8 onglets

### Credentials & Secrets

- [ ] URSSAF_CLIENT_ID, URSSAF_CLIENT_SECRET in .env
- [ ] SWAN_API_KEY in .env
- [ ] GOOGLE_CREDENTIALS_JSON in .env ou file
- [ ] SMTP_HOST, SMTP_USER, SMTP_PASSWORD in .env
- [ ] .gitignore includes .env

### Documentation

- [ ] README.md avec setup instructions
- [ ] API endpoints documented
- [ ] Composants architecture documented
- [ ] Test scenarios listed

### Testing Infrastructure

- [ ] Unit test template created
- [ ] Mock fixtures for APIs
- [ ] Pytest configuration (.ini or pyproject.toml)
- [ ] CI/CD pipeline baseline (GitHub Actions optional)

---

## Conclusion

Ce **sprint planning** fournit une roadmap détaillée pour développer SAP-Facture en **3 sprints (15 jours)**, guidé par l'architecture définie dans SCHEMAS.html. Les sprints sont séquentiels avec gating decisions critiques après chaque sprint.

**MVP Objectives** (Fin Sprint 2)
- Jules crée client URSSAF ✓
- Jules crée et soumet facture ✓
- Système polling statuts automatiquement 4h ✓
- Dashboard affiche visibilité temps réel ✓

**Phase 2 Start** (Sprint 3)
- Lettrage automatique factures ↔ virements Swan ✓
- CLI avancée pour power users ✓
- Infrastructure + logging production-ready ✓

**Success Criteria Finales** :
- Zéro erreurs montants factures (validation stricte)
- 95% factures validées clients dans 48h (reminders auto)
- 80% lettrage auto (matching confiance > 80)
- < 2 min création facture pour Jules
- Uptime 99%+ (hors API URSSAF outages)

---

**Document Version**: 1.0
**Date**: 15 mars 2026
**Auteur**: BMAD Scrum Master (Automated)
**Status**: Prêt pour développement
**Validation**: En attente Product Owner signature
