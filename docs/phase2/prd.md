# PRD Phase 2 — SAP-Facture
## Confort, Automatisation & Rapprochement Bancaire

**Destinataire**: Jules Willard, micro-entrepreneur
**Date**: Mars 2026
**Version**: 1.0
**Statut**: ✅ Prêt pour développement
**Product Owner**: Sarah (BMAD)
**Source de Vérité**: docs/schemas/SCHEMAS.html + docs/phase1/

---

## Table des Matières

1. [Résumé Exécutif](#résumé-exécutif)
2. [Contexte & Justification](#contexte--justification)
3. [Objectifs & Métriques de Succès](#objectifs--métriques-de-succès)
4. [Personas & Cas d'Usage](#personas--cas-dusage)
5. [Exigences Fonctionnelles](#exigences-fonctionnelles)
6. [Exigences Non-Fonctionnelles](#exigences-non-fonctionnelles)
7. [Contraintes Techniques](#contraintes-techniques)
8. [Hors Scope Phase 2](#hors-scope-phase-2)
9. [Risques & Mitigations](#risques--mitigations)
10. [Timeline & Phasing](#timeline--phasing)
11. [Critères d'Acceptance](#critères-daccceptance)

---

## Résumé Exécutif

### Vision Phase 2
**"Fermer la boucle comptable et automatiser le suivi des paiements"**

Après le succès du MVP Phase 1 (semaines 1-2), Phase 2 doit transformer un système fonctionnel en **outil de gestion complète** : automatisation du rapprochement bancaire, rappels intelligents des clients qui oublient, historique et recherche des factures, et outils CLI pour l'utilisateur avancé.

### Le Problème Résolu
- **Phase 1 resout** : Jules peut créer une facture et la soumettre à URSSAF
- **Phase 2 resout** :
  - Jules ne sait pas si les paiements sont arrivés sur Swan (lettrage manuel = charge 3-5 min/semaine)
  - 30-40% des clients oublient de valider dans les 48h → relances manuelles répétées
  - Impossible de chercher une facture parmi 50+ (historique = défilement sans fin)
  - Pas de CLI pour les utilisateurs avancés (batch operations, intégration scripts)

### Valeur Attendue
- **Rapprochement automatique** : -3 heures administratives/mois (lettrage auto ≥ 90%)
- **Taux de validation client** : +20-30% (rappels T+36h)
- **Visibilité financière** : +instant (historique, filtres, dashboard temps-réel)
- **Flexibilité** : +CLI pour power users et automations

### Le Scope Phase 2
6 fonctionnalités clés, effort total ~16 jours :

| Epic | Feature | Effort | Priorité | Impact |
|------|---------|--------|----------|--------|
| **Epic 1** | Historique & Recherche Factures | 2j | HAUTE | UX : trouver une facture en < 5 sec |
| **Epic 1** | Filtres Dashboard (statut, date, montant) | 1j | HAUTE | Gérer 50+ factures sans scroll infini |
| **Epic 2** | Rapprochement Bancaire Swan Auto | 5j | CRITIQUE | Fermer comptabilité auto (ROI majeur) |
| **Epic 3** | Reminder Email T+36h | 2j | MOYENNE | +20-30% taux validation client |
| **Epic 4** | Annulation / Avoir | 3j | MOYENNE | Légalité + récupération erreurs |
| **Epic 5** | CLI : sap reconcile | 3j | MOYENNE | Fallback + power users |

**Résultat Phase 2 complet** : Système exploitation robuste pour 50-100 factures/mois.

---

## Contexte & Justification

### Transitions depuis MVP
**MVP Phase 1** (semaines 1-2) livre :
- ✅ Création client URSSAF
- ✅ Création facture web + PDF
- ✅ Soumission API URSSAF
- ✅ Polling statut auto 4h
- ✅ Dashboard basique

**Feedback Jules post-MVP** (hypothétique, à confirmer) :
- "Je ne sais pas si le virement est arrivé" → **Epic 2 : Rapprochement**
- "Trop de clients oublient la validation" → **Epic 3 : Reminders**
- "Impossible de retrouver une facture du mois dernier" → **Epic 1 : Historique**
- "Besoin de corriger une facture erreur" → **Epic 4 : Annulation**
- "Je veux automatiser batch factures" → **Epic 5 : CLI reconcile**

### Dépendances sur Phase 1
Phase 2 **repose entièrement** sur Phase 1 :
- Tous les statuts (CREE, EN_ATTENTE, VALIDE, PAYE) doivent être stables
- Google Sheets onglet Factures et Transactions doivent être opérationnels
- API URSSAF polling toutes les 4h doit tourner sans erreur

### Prérequis Go/No-Go Phase 2
Avant de lancer Phase 2, valider :
- [ ] MVP Phase 1 tourne 5 jours en prod sans erreur critique
- [ ] Au moins 5 factures complètes (BROUILLON → RAPPROCHE)
- [ ] Zéro perte de données (audit DB intégrité)
- [ ] Statuts URSSAF cohérents avec reality (test via portail URSSAF)
- [ ] Swan API credentials + GraphQL docs disponibles
- [ ] Google Sheets API quota suffisant pour appels fréquents

---

## Objectifs & Métriques de Succès

### Objectifs Métier

| Objectif | Définition | Mesure | Cible Phase 2 |
|----------|-----------|--------|---------------|
| **Fermer comptabilité auto** | % factures PAYEES correctement lettrées sans intervention Jules | Lettrage: AUTO + MANUEL / Total PAYEES | ≥ 90% |
| **Augmenter validation client** | % factures EN_ATTENTE passant VALIDE (vs EXPIRE) | VALIDE / (VALIDE + EXPIRE) | ≥ 80% |
| **Réduire charge admin** | Temps Jules / facture en phase 2 vs 1 | Chronomètre: création → lettrage | -50% (de 10 min → 5 min) |
| **Visibilité financière** | Jules capable de dire "combien j'attends" et "combien j'ai reçu" | Dashboard stats en temps-réel | 100% disponible |
| **Flexibilité avancée** | Utilisateurs tech peuvent batch-operate (CLI, scripts) | % utilisation CLI sap reconcile | ≥ 30% factures traitées par CLI |

### Métriques Opérationnelles

| Métrique | MVP (Baseline) | Phase 2 (Cible) | Definition |
|----------|---|---|---|
| **Dashboard Load Time** | 2-3s (5 factures) | < 1s (50 factures) | Temps page affichée |
| **API URSSAF Success Rate** | ≥ 95% | ≥ 98% | Polling + call réussis |
| **Swan API Sync Delay** | 10-30 min (manual) | < 5 min (auto) | Delta entre paiement réel et détection système |
| **Lettrage Accuracy** | N/A (Phase 1) | ≥ 95% (auto + manual) | Montants matchés correctement |
| **Email Delivery Rate** | N/A | ≥ 95% | Reminders T+36h reçues |
| **Uptime Système** | ≥ 99% | ≥ 99.5% | Disponibilité web + cron + integrations |

### Success Criteria Globale Phase 2
Phase 2 est **"Done"** quand :
- [ ] ≥ 25 factures traitées de BROUILLON → RAPPROCHE sans erreur
- [ ] Lettrage auto ≥ 90% (≤ 10% "à vérifier" orange)
- [ ] Taux validation ≥ 80% (email reminders envoyés et effectifs)
- [ ] Historique + filtres permettent retrouver facture en < 5 sec
- [ ] CLI sap reconcile fonctionne end-to-end
- [ ] Tests e2e couvrent chaque epic
- [ ] Zéro perte de donnée audit post-phase 2

---

## Personas & Cas d'Usage

### Persona Principale : Jules Willard
*Déjà défini en Phase 1, renforcé Phase 2*

| Aspect | Détail |
|--------|--------|
| **Rôle** | Micro-entrepreneur, cours particuliers auto-entrepreneur |
| **Tech Proficiency** | Intermédiaire (web + CLI à l'aise) |
| **Frustrations Phase 1** | Pas de visibilité paiements; clients oublient; historique; corrections erreur |
| **Goals Phase 2** | Comptabilité auto; moins de relances manuelles; tracer chaque centime |
| **Usage Fréquence** | 5-7 factures/semaine; 1x/semaine rapprochement; 3-5x/week dashboard |

### Cas d'Usage Principaux Phase 2

#### CU1: Rapprochement Bancaire Automatique
**Acteurs**: Jules, Système (BankReconciliation), Swan API

**Scenario Happy Path**:
```
Jour J (T+72h après validation client):
1. URSSAF effectue virement 100€ sur Swan
2. Système (cron 6h) : sync Swan → onglet Transactions
3. Formules lettrage (onglet Lettrage) : matching montant + libellé
4. Score confiance ≥ 80 ? → AUTO-LETTRE
5. Dashboard facture : state = RAPPROCHE, couleur verte
6. Jules consulte dashboard lundi matin : "Facture X lettree, C'est bon"
```

**Effort Jules**: 0 (automatique)
**Effort Système**: Cron 1x par 6h (~1 min)
**Délai**: Détection auto < 6h après virement réel

#### CU2: Rappel Client qui Oublie (T+36h)
**Acteurs**: Jules, Système (NotificationService), Email SMTP, Client

**Scenario Happy Path**:
```
Jour J+0 (T+0): Facture soumise, statut CREE → EN_ATTENTE
Jour J+1 (T+36h):
1. Cron job (4h) détecte : EN_ATTENTE depuis 36h
2. Envoie email Jules : "Rappel — Facture XXXX attente validation, délai 12h"
3. Jules lit email, appelle client : "T'as pas vu l'email URSSAF ?"
4. Client : "Ah non, je vais le chercher..."
5. Client clique lien URSSAF, valide
6. Polling (4h) détecte VALIDE
7. Cycle continue normalement
```

**Impact**: +20-30% taux validation (baseline: 50-60% auto, + reminders = 80%+)
**Effort Jules**: 1-2 min (appel client)
**Délai**: Email reçu < 5 min après T+36h

#### CU3: Recherche Historique
**Acteurs**: Jules, Dashboard (web)

**Scenario**:
```
Lundi matin, Jules besoin facture "Jean Dupont, février":
1. Ouvre Dashboard → clique onglet "Historique"
2. Filtre : Client = "Jean", Mois = "Février 2026"
3. Liste affiche 3 factures correspondantes
4. Clique la bonne → PDF s'affiche
5. Envoie comptable si besoin
Temps total: < 30 sec
```

**Effort Jules**: 30 sec
**Critère Succès**: Retrouver facture < 5 sec (vs avant: 5-10 min scroll)

#### CU4: Correction & Avoir (Annulation Facture)
**Acteurs**: Jules, URSSAF API

**Scenario Erreur**:
```
Jour J: Jules a créé facture 100€ mais devrait être 95€
État facture : BROUILLON (avant soumission)
1. Jules : modifie montant 95€, sauvegarde
2. Jules : clique "Soumettre"
Résultat: Facture correcte soumise, ancienne jamais partie

Alternatively, facture déjà SOUMIS:
1. Jules clique "Annuler" → statut ANNULE
2. Crée nouvelle facture 95€ correcte
3. Commentaire : "Annule facture V1 (montant erroné)"
Résultat: Audit trail propre, comptabilité OK
```

**Effort Jules**: 2-3 min (correction + note)
**Impact**: Légalité (avoirs documentés) + confiance

#### CU5: CLI Batch Reconciliation
**Acteurs**: Jules (power user), CLI tool, Swan API, Sheets

**Scenario Batch**:
```
Vendredi, Jules veut relancer all paiements pending:
$ sap reconcile

Output:
  ✓ Sync Swan: 15 transactions importées
  ✓ Matching: 12 lettres AUTO, 2 à VERIFIER, 1 PAS_MATCH
  ✓ Sheets updated: onglet Transactions + Lettrage
  ✓ Summary: 80% completion, 1 manual action needed
```

**Utilité**: Fallback si polling 4h missed; power user workflow
**Impact**: < 2 min pour 50 factures vs 15-20 min manuel

---

## Exigences Fonctionnelles

### Epic 1: Historique & Recherche + Filtres Dashboard

#### Story 1.1: Historique Factures avec Recherche
**US ID**: E1-S1
**Priorité**: HAUTE
**Effort**: 2 jours

**Description**:
Jules doit pouvoir consulter TOUTES les factures passées (depuis MVP) avec recherche rapide par critères (client, date, montant, statut).

**Acceptance Criteria**:
- [ ] Vue "Historique" accessible depuis menu principal (ou onglet dashboard)
- [ ] Table affiche : Facture ID, Client, Montant, Dates, Statut, PDF Link
- [ ] Recherche texte : client nom (fuzzy match ou contains)
- [ ] Résultats: max 50 par page, pagination
- [ ] Tri: par date création (défaut DESC), par montant, par statut
- [ ] Click facture → détails complets (client, montant, statut, date soumis, réponse URSSAF)
- [ ] Lien direct PDF depuis détails
- [ ] Performance: < 2 sec pour 100 factures (query optimisé)

**Technical Notes**:
- Index DB/Sheets sur `client_id`, `date_creation`, `statut`
- Pagination côté serveur (Sheets API: batchGet + offset)
- Fuzzy search: utiliser `difflib.SequenceMatcher` ou Sheets SEARCH()

**Definition of Done**:
- Tests: search "john" find "Jean" (fuzzy)
- Tests: pagination 50 items OK
- Perf: 100 factures en < 2 sec

---

#### Story 1.2: Filtres Dashboard
**US ID**: E1-S2
**Priorité**: HAUTE
**Effort**: 1 jour

**Description**:
Ajouter filtres multiples au dashboard : par statut (dropdown), date range (date picker), montant (range), pour réduire bruit.

**Acceptance Criteria**:
- [ ] Filtre Statut: dropdown multi-select (BROUILLON, SOUMIS, CREE, EN_ATTENTE, VALIDE, PAYE, RAPPROCHE, REJETE, EXPIRE, ANNULE)
- [ ] Filtre Date: date picker "De" / "À" (ISO format YYYY-MM-DD)
- [ ] Filtre Montant: range slider ou inputs min/max (€)
- [ ] Filtre Client: dropdown ou search (pré-rempli from Clients list)
- [ ] "Apply Filters" button → refresh tableau
- [ ] "Reset Filters" → réinitialise tous (affiche tous)
- [ ] État filtres persiste en session (pas de recharge)
- [ ] Performance: appliquer filtres < 1 sec

**Technical Notes**:
- Filtres = côté client (JS) OU côté serveur (query Sheets)
- Recommandation: côté client pour MVP (plus rapide, moins d'API call)
- Option advanced: sauvegarde filtres préférés en localstorage Jules

**Definition of Done**:
- Filter par statut PAYE + date = fevrier → affiche 3 factures
- Reset → affiche tous
- < 1 sec refresh

---

### Epic 2: Rapprochement Bancaire Automatique (Swan + Lettrage)

#### Story 2.1: Sync Transactions Swan
**US ID**: E2-S1
**Priorité**: CRITIQUE
**Effort**: 2 jours

**Description**:
Importer automatiquement les transactions bancaires depuis Swan (API GraphQL) dans onglet Transactions (Sheets), toutes les 6 heures.

**Acceptance Criteria**:
- [ ] Cron job "sync_swan" tourne toutes les 6h (configurable, ex: 00:00, 06:00, 12:00, 18:00 UTC)
- [ ] GraphQL query Swan : toutes transactions dernières 30 jours
- [ ] Filter: montants > 0, type = CREDIT entrant, source ≠ virement perso (libellé contient "URSSAF" optionnel dans phase 2)
- [ ] Pour chaque transaction : écrire onglet Transactions (Sheets)
  - transaction_id (unique key)
  - montant
  - libellé
  - date valeur
  - compte source IBAN (partiellement)
  - statut_lettrage = "A_TRAITER" (défaut)
- [ ] Pas de doublons (check transaction_id exists)
- [ ] Logging: chaque sync, # transactions, erreurs
- [ ] Alertes: si Swan API fail → email Jules + retry dans 1h

**Technical Notes**:
- Swan API: `query { transactions(dateFrom: .., dateTo: ..) { id, amount, label, ... } }`
- OAuth2: réutiliser client Swan credentials from .env
- Timeout: 20 sec (retry 2x)
- Google Sheets API: append rows batch

**Definition of Done**:
- 15 transactions importées, no doublons
- Cron 6h tourne 72h sans erreur
- Logging OK

---

#### Story 2.2: Algorithme de Scoring & Lettrage Auto
**US ID**: E2-S2
**Priorité**: CRITIQUE
**Effort**: 2 jours

**Description**:
Implémenter algorithme de matching: pour chaque facture PAYE, chercher transaction Swan correspondante via scoring confiance (montant, date, libellé), puis lettrer automatiquement si score ≥ 80, ou signaler "à vérifier" si 60-79.

**Acceptance Criteria**:
- [ ] Onglet Lettrage (Sheets) : colonnes
  - facture_id
  - montant_facture
  - transaction_id (cherchée)
  - montant_transaction
  - écart (montant_facture - montant_transaction)
  - date_facture (date paiement estimée URSSAF)
  - date_transaction
  - score_confiance (calculé)
  - statut_lettrage (AUTO, A_VERIFIER, PAS_DE_MATCH)
- [ ] Scoring:
  - Montant exact (facture = transaction) : +50 pts
  - Date écart < 3 jours : +30 pts
  - Libellé contient "URSSAF" : +20 pts
  - **Score ≥ 80** → statut = "AUTO" (lettre immédiate)
  - **Score 60-79** → statut = "A_VERIFIER" (surligne orange, email Jules)
  - **Score < 60** → statut = "PAS_DE_MATCH" (surligne rouge, attendre)
- [ ] Formules Sheets (VLOOKUP, SUMIF, etc.) OR Python script
- [ ] Pour chaque facture PAYE : chercher UNE transaction (pas multiples)
- [ ] Si lettre AUTO : écrire facture_id dans transaction + mettre à jour Factures statut = RAPPROCHE
- [ ] Si A_VERIFIER : email Jules "Lettrage manuel requis — facture XXX montant YYY"
- [ ] Performance: matching < 30 sec pour 50 factures

**Technical Notes**:
- Recommandation: formules Sheets pour intégrité transactionnelle
- Fallback: Python script BankReconciliation.match_transactions()
- Window search: date_transaction dans [date_paiement - 5j, date_paiement + 5j]
- Edge case: plusieurs transactions même montant → scoring by libellé/date/IBAN
- Idempotence: si facture déjà RAPPROCHE → skip

**Definition of Done**:
- Facture 100€ + transaction 100€ (libellé URSSAF, date ±1j) → score 100 → AUTO
- Facture 100€ + transaction 100€ (libellé "Virement Jean", date ±2j) → score 60 → A_VERIFIER
- Facture 100€ + transaction 95€ (aucune match) → PAS_DE_MATCH (red flag)
- 50 factures PAYE : 45 AUTO, 4 A_VERIFIER, 1 PAS_DE_MATCH → OK

---

#### Story 2.3: Interface Validation Manuelle des "À Vérifier"
**US ID**: E2-S3
**Priorité**: HAUTE
**Effort**: 1 jour

**Description**:
Jules doit pouvoir confirmer manuellement les lettres "À Vérifier" (score 60-79) via UI simple : affiche facture + transaction candidates, Jules clique "C'est bon" ou "C'est pas ça".

**Acceptance Criteria**:
- [ ] Dashboard tab "Lettrage" affiche toutes transactions "A_VERIFIER" en orange
- [ ] Click row orange → modal affiche :
  - Facture: #ID, Client, Montant €
  - Transaction: montant €, libellé, date
  - Score : "70/100 — montant exact (+50) + date ±2j (+30) = pas libellé URSSAF"
  - Jules options:
    - [ ] Bouton "C'est bon, lettrer" → écrire facture_id, statut = LETTRE, facture = RAPPROCHE
    - [ ] Bouton "C'est pas ça" → statut = PAS_DE_MATCH, chercher autre transaction
- [ ] Après confirmation : modal ferme, dashboard refresh
- [ ] Option "Lettrer Manuellement" (textarea notes) → créer match même si score < 60
- [ ] Logging: qui a validé, quand, notes

**Technical Notes**:
- Modal simple HTML/Tailwind
- On save : PUT Sheets onglet Lettrage + Factures (atomic)
- No undo (mais logging pour audit)

**Definition of Done**:
- 4 lignes orange (A_VERIFIER) listées
- Click 1ère → modal, Jules clique "C'est bon"
- Ligne passe vert (LETTRE), facture = RAPPROCHE
- Dashboard stats mise à jour

---

#### Story 2.4: Onglet Balances (Calculs Automatiques)
**US ID**: E2-S4
**Priorité**: MOYENNE
**Effort**: 1 jour

**Description**:
Onglet "Balances" (Sheets) affiche synthèse mensuelle : # factures, CA lettré, # en attente, solde.

**Acceptance Criteria**:
- [ ] Onglet Balances (lecture seule, formules) :
  - Mois (clé)
  - nb_factures (COUNTIF statut != ANNULE)
  - ca_total (SUMIF montant où statut != ANNULE)
  - ca_lettree (SUMIF montant où statut = RAPPROCHE)
  - solde = ca_lettree
  - nb_en_attente (COUNTIF statut IN [EN_ATTENTE, VALIDE, PAYE])
  - nb_non_lettrees (COUNTIF statut = PAYE ET pas transaction_id)
- [ ] Dashboard affiche synthèse Balances (cards ou mini-graph)
- [ ] Jules peut voir en 1 coup d'œil "J'attends encore 2 paiements" vs "Tout est OK"

**Definition of Done**:
- Cards: "100€ reçus", "2 en attente", "20 factures traitées" → actualisé toutes les heures

---

### Epic 3: Rappels Email T+36h sans Validation

#### Story 3.1: Reminder Email Service
**US ID**: E3-S1
**Priorité**: MOYENNE
**Effort**: 2 jours

**Description**:
Envoyer email automatique à Jules si une facture reste EN_ATTENTE après 36h (sans validation client). Contient contexte (client, montant, délai restant) et CTA (relancer client ou annuler).

**Acceptance Criteria**:
- [ ] Cron job "send_reminders" toutes les 4h (réutilise existing polling job)
- [ ] Pour chaque facture EN_ATTENTE : `elapsed = now - created_at`
  - Si `36h <= elapsed < 48h` ET `reminder_sent = false` :
    - Envoyer email Jules
    - Mettre à jour Sheets : reminder_sent = true, reminder_sent_at = now
    - Pas de re-email même si cron re-run (flag reminder_sent)
- [ ] Email template :
  ```
  Sujet: [SAP-Facture] Rappel — Facture XXXX en attente validation (délai 12h)

  Contenu:
  Bonjour Jules,

  Facture #F12345 créée le 15/03/2026 14:30 reste en attente de validation.
  Client: Jean Dupont
  Montant: 100€
  Email client: jean@example.com

  URGENT: Client doit valider avant 2026-03-17 14:30 (délai 12h restants)

  Actions:
  - Appeler Jean pour le relancer: +33 6 XX XX XX XX
  - Ou via email: jean@example.com
  - Dashboard: [lien facture]

  Merci,
  SAP-Facture
  ```
- [ ] Email envoyé via SMTP (réutilise creds Phase 1)
- [ ] Retry: 3x en cas bounce (délai 5 min, 10 min, 20 min)
- [ ] Fallback: si SMTP fail → pas d'alerte (acceptable Phase 2, log warning)
- [ ] Logging: email envoyé, destinataire, timestamp

**Technical Notes**:
- Réutiliser EmailNotifier service (FastAPI/SMTP)
- Template: Jinja2 HTML + plain-text fallback
- Queue async (Celery optional, ou simple async await)

**Definition of Done**:
- Facture créée, EN_ATTENTE à T+36h
- Email reçu Jules < 5 min après T+36h
- Contenu correct (client, montant, délai)
- No double-email si cron run multiple fois

---

#### Story 3.2: Dashboard Countdown Timer
**US ID**: E3-S2
**Priorité**: MOYENNE
**Effort**: 1 jour

**Description**:
Afficher visuellement sur le dashboard la facture EN_ATTENTE avec countdown 48h (ex: "⏱ Expires in 12h").

**Acceptance Criteria**:
- [ ] Dashboard: colonne "Délai Restant" ou badge de couleur :
  - `48h - (now - created_at)` = délai en heures
  - ≥ 36h: couleur verte (OK)
  - 12-36h: couleur orange (ATTENTION, reminder envoyé)
  - < 12h: couleur rouge (CRITIQUE)
- [ ] Affichage format : "23h 45 min restantes"
- [ ] Tri possible par délai restant (urgent en haut)
- [ ] Refresh auto JS toutes les 60 sec (countdown en temps-réel)

**Definition of Done**:
- Facture EN_ATTENTE depuis 40h → badge orange "8h 00 restantes"
- F5 → délai descend (refresh auto)
- Délai 48h min ≥ 36h après T+48h → passe rouge (EXPIRE)

---

### Epic 4: Annulation & Avoirs

#### Story 4.1: Annulation Facture (BROUILLON et SOUMIS)
**US ID**: E4-S1
**Priorité**: MOYENNE
**Effort**: 2 jours

**Description**:
Jules doit pouvoir annuler une facture si elle est en BROUILLON ou SOUMIS (erreur de saisie, client payé cash). Crée un avoir / trace d'audit.

**Acceptance Criteria**:
- [ ] Dashboard: bouton "Annuler" sur factures BROUILLON et SOUMIS
- [ ] Click "Annuler" → confirmation modal :
  - "Confirmer annulation facture XXXX ? Cette action est irréversible."
  - Jules saisit raison (ex: "Montant erroné", "Client payé cash", etc.)
- [ ] Après confirmation :
  - Mettre à jour Sheets : statut = ANNULE, annuled_at = now, reason = [Jules input]
  - Aucun appel API URSSAF (facture jamais soumis anyway)
  - Créer entrée audit (logging complet)
- [ ] Dashboard: facture ANNULE affichée grise (pas comptabilité)
- [ ] Historique: facture ANNULE visible (pour audit trail)
- [ ] Impact: ANNULE est état terminal (pas de relance)

**Technical Notes**:
- Annulation ~= soft delete (jamais supprimer, just marquer ANNULE)
- Si facture SOUMIS → contacte URSSAF ? (vérifier si annulation API exist)
- Fallback semaine 1: juste marquer ANNULE, documenter manuellement si besoin URSSAF contact

**Definition of Done**:
- Facture BROUILLON montant erroné → "Annuler" → modale → raison → ANNULE avec timestamp
- Historique affiche facture grise ANNULE
- Pas de comptabilité (pas inclus CA total)

---

#### Story 4.2: Avoir (Facture Partielle Annulée)
**US ID**: E4-S2
**Priorité**: MOYENNE
**Effort**: 1 jour

**Description**:
Si facture PAYE et Jules découvre montant erroné, créer un "avoir" (facture négative) pour corriger comptabilité.

**Acceptance Criteria**:
- [ ] Dashboard: facture RAPPROCHE → bouton "Créer Avoir"
- [ ] Modal :
  - "Montant avoir" (pré-rempli: montant_facture, modifiable)
  - Raison
  - Checkbox "Soumettre avoir à URSSAF" (optionnel Phase 2, fallback: manual URSSAF contact)
- [ ] Après création:
  - Crée facture AVOIR avec montant_avoir négatif (ex: -20€)
  - Statut AVOIR = BROUILLON (optionnel soumettre après)
  - Commentaire lié (facture original #XXX)
  - Logging audit complet
- [ ] Dashboard: factures parent + avoir affichées ensemble (indentation ou lien "voir avoir")

**Technical Notes**:
- Avoir = facture normale montant négatif
- Optionnel Phase 2: auto-soumettre avoir à URSSAF (API support ?)
- Fallback: avoir local + contact URSSAF manuel

**Definition of Done**:
- Facture 100€ RAPPROCHE → "Créer Avoir" 20€ → facture_avoir_20€ créée, statut BROUILLON
- Dashboard affiche "-20€ Avoir" lié à facture original

---

### Epic 5: CLI Advanced — Reconcile

#### Story 5.1: CLI Command `sap reconcile`
**US ID**: E5-S1
**Priorité**: MOYENNE
**Effort**: 3 jours

**Description**:
Ajouter commande CLI `sap reconcile` pour déclencher rapprochement bancaire manuellement (fallback vs cron 6h), avec résumé détaillé des matchs.

**Acceptance Criteria**:
- [ ] Commande: `$ sap reconcile [--force] [--from YYYY-MM-DD] [--to YYYY-MM-DD]`
- [ ] Options:
  - `--force` : ré-matcher même transactions déjà LETTREES
  - `--from`, `--to` : date range (défaut: derniers 30 jours)
- [ ] Exécution:
  1. Sync Swan : GET /transactions (30j) → import Sheets
  2. Matching algo (score)
  3. Écrire Sheets onglet Lettrage
  4. Mettre à jour factures : PAYE → RAPPROCHE (si AUTO)
  5. Afficher résumé
- [ ] Output format:
  ```
  $ sap reconcile --from 2026-03-01

  ========================================
  Bank Reconciliation Report
  ========================================

  Period: 2026-03-01 to 2026-03-15

  Swan Transactions Imported: 12
  Invoices Processed: 15

  Matching Results:
    ✓ AUTO (score ≥ 80): 12 factures
    ⚠ A_VERIFIER (60-79): 2 factures
    ✗ PAS_DE_MATCH: 1 facture

  Details:
    F12345 (100€) ↔ SWAN_TX_ABC (100€) - Score 95 ✓ AUTO
    F12346 (50€)  ↔ SWAN_TX_DEF (50€)  - Score 65 ⚠ VERIFY
    ...

  Summary:
    Lettered: 14/15 (93.3%)
    Ready for approval: 2
    Action: 1 manual review

  Sheets updated: ✓ Lettrage, ✓ Factures, ✓ Balances

  ========================================
  ```
- [ ] Exit codes : 0 (success), 1 (error)
- [ ] Logging: fichier log détaillé
- [ ] Idempotence: si déjà LETTRE → skip sauf --force

**Technical Notes**:
- Réutilise BankReconciliation.py service
- Réutilise SwanClient GraphQL
- Output: Python Click + Rich lib (couleurs)

**Definition of Done**:
- `sap reconcile` → 12 AUTO, 2 VERIFY, 1 NOMATCH
- `sap reconcile --force` → re-match tous (ok)
- Exit code 0
- Sheets updated

---

#### Story 5.2: CLI Batch Status Check
**US ID**: E5-S2
**Priorité**: MOYENNE
**Effort**: 1 jour (optionnel, Phase 2b)

**Description**:
CLI `sap sync` (Phase 1) extended pour afficher statut factures URSSAF en tableau CLI (pas juste web dashboard).

**Acceptance Criteria**:
- [ ] Commande: `$ sap sync [--format table|json|csv]`
- [ ] Affiche tableau factures actives (EN_ATTENTE, VALIDE, PAYE) + statuts
- [ ] Format défaut: pretty table (colors)
- [ ] Option JSON/CSV pour scripting
- [ ] Filtre optionnel: `--client "Jean"`, `--status PAYE`, etc.

---

### Cross-Epic Features (Transversal)

#### Feature: Notifications Système (Toutes Epics)
**Priorité**: MOYENNE
**Effort**: Included in each epic (email templates, etc.)

**Acceptance Criteria**:
- [ ] Email Jules notification lors de changement majeur:
  - Facture EXPIRE (T+48h no validation)
  - Facture VALIDE (client validated)
  - Facture PAYE (URSSAF traite)
  - Lettrage A_VERIFIER (intervention manuelle requise)
- [ ] Email Subject lisible et urgent (ex: "[URGENT] Facture expire demain")
- [ ] Unsubscribe link (optionnel Phase 2)
- [ ] Log : qui a reçu, quand, statut delivery

---

## Exigences Non-Fonctionnelles

### Performance

| Métrique | Cible | Justification |
|----------|-------|---------------|
| **Dashboard Load** | < 1s (50 factures) | Jules consulte 3-5x/jour, doit être rapide |
| **Search/Filter** | < 2s (100 factures) | Retrouver facture doit être instant |
| **Reconciliation** | < 5 min (50 factures) | Cron 6h batch operation, pas critique timing |
| **Email Send** | < 30s per email | Reminders non-blocking, async OK |
| **API URSSAF call** | < 30s timeout | Polling 4h, retries tolérés |
| **Swan sync** | < 20s timeout | Graphql call, rate limits |
| **Sheets write** | < 5s per batch | Atomic updates, concurrent writes? |

### Sécurité

| Aspect | Exigence | Implémentation |
|--------|----------|-----------------|
| **Authentication** | Jules seul user, token session | Réutiliser Phase 1 (FastAPI session) |
| **Data Privacy** | Clients (élèves) email PII dans Sheets | GDPR compliance OK (logged in France) |
| **Secret Management** | Swan API key, SMTP pwd, URSSAF OAuth | .env file, never committed, rotate monthly |
| **Email Security** | TLS/SMTP over SSL | Standard SMTP lib (Python) |
| **Audit Trail** | Toute action logged (qui, quand, quoi) | Logging + Sheets commentaires |
| **Rate Limiting** | API URSSAF quota respecté | Cron spacing (4h), batch sizing |

### Disponibilité & Résilience

| Scenario | Mitigation | SLA |
|----------|-----------|-----|
| **Swan API down** | Cache 1h transactions, retry 2x | Lettrage delayed max 6h |
| **URSSAF API down** | Polling retry, fallback manual sync | Status update delayed, no data loss |
| **Sheets API quota hit** | Batch writes, queue retry avec backoff | No loss, retry auto next cycle |
| **SMTP bounces** | Queue + retry 3x (5, 10, 20 min) | Reminder delayed, not critical |
| **Cron job crashes** | Logging alerts, manual trigger CLI | `sap sync` / `sap reconcile` workaround |
| **Database corruption** | Sheets is source of truth, atomic writes | Rollback via Sheets version history |

### Usabilité

| Critère | Cible |
|---------|-------|
| **Time-to-value** | Jules opère lettrage auto sans training (< 5 min onboarding) |
| **Error messages** | Clairs et actionnables (pas "Erreur 500") |
| **Visual feedback** | Statuts couleurs (vert=OK, orange=attente, rouge=erreur) |
| **Mobile responsiveness** | Dashboard adapté tablette/phone (Phase 3 priority) |
| **Accessibility** | WCAG 2.1 AA (alt text, keyboard nav, color contrast) |

### Maintenabilité

| Aspect | Standard |
|--------|----------|
| **Code Quality** | Ruff + mypy --strict; 80%+ test coverage |
| **Documentation** | Docstrings, README, inline comments |
| **Logging** | Structured JSON logs (stackdriver compatible) |
| **Monitoring** | Email alerts on cron failures, API errors |
| **Backup** | Sheets auto-version (Google), export CSV weekly |

---

## Contraintes Techniques

### Architecture : Google Sheets as Backend
**Decision (Non-Negotiable)**: Google Sheets reste backend data pour Phase 2 (accepté design).

- **Implication** : Toutes données = Sheets onglets (Factures, Clients, Transactions, Lettrage, Balances, etc.)
- **API**: Google Sheets API v4 (append, update, batchGet)
- **Limite**: Quota 300 req/min, 500k cells/day → OK pour Jules (< 100 factures/mois)
- **Fallback**: CLI `sap export` → JSON local (offline cache)

### API Rate Limits & Quotas

| API | Limit | Mitigation |
|-----|-------|-----------|
| **Google Sheets v4** | 300 req/min | Batch operations max 5 rows/call |
| **Swan GraphQL** | 100 req/min (est.) | Cache 1h transactions |
| **URSSAF REST** | Unknown (contact support) | Polling 4h = 6 req/jour/facture |
| **SMTP** | Depends on provider | Queue + retry OK |

### External Dependencies

| Service | Required | Fallback | Criticality |
|---------|----------|----------|------------|
| **Google Sheets** | OUI | JSON local export | CRITICAL (data storage) |
| **Swan API** | OUI (Phase 2A) | Manual reconciliation | HIGH (lettrage auto) |
| **URSSAF API** | OUI | Manual polling via web | CRITICAL (cycle de base) |
| **SMTP** | Reminders | None (but acceptable) | MEDIUM (nice-to-have) |

### Frameworks & Libraries (Phase 1 réutilisés)

| Component | Tech | Version | Notes |
|-----------|------|---------|-------|
| **Backend** | FastAPI | 0.104+ | Async ready |
| **ORM** | SQLAlchemy | 2.0+ (si SQLite) | Optional pour Phase 2 (Sheets primary) |
| **Frontend** | Jinja2 + Tailwind | Latest | SSR only |
| **PDF** | WeasyPrint | 52+ | Stable |
| **Google API** | google-auth, gspread | Latest | async support |
| **Swan SDK** | Python (custom GQL) | N/A | Home-built |
| **Scheduler** | APScheduler | 3.10+ | Cron jobs |
| **Email** | smtplib | stdlib | OK |
| **CLI** | Click | 8.0+ | Command parsing |
| **Testing** | pytest, pytest-asyncio | Latest | Coverage ≥80% |

---

## Hors Scope Phase 2

### Features Deferées à Phase 3+

| Feature | Raison | Timeline |
|---------|--------|----------|
| **Google Sheets Auto-Sync** | Complexité bidirectional, risk conflict. Test Phase 2 data stabil en prod 2 sem d'abord. | Phase 3 (April+) |
| **Attestations Fiscales** | BNC tax logic complex. Aucune demande juridique urgent Phase 2. | Phase 3 (avant juin) |
| **Multi-Intervenants** | Design change majeure (qui facture?). Business decision required. | Phase 4 (si scaling) |
| **Mobile UI Optimized** | Phase 1-2 responsive "OK", Phase 3 PWA + offline. | Phase 3 (March+ analytics data) |
| **Push Notifications** | SMTP reminders suffisent Phase 2. SMS/push Phase 3 if email engagement < 30%. | Phase 3+ |
| **Webhooks URSSAF** | API support unknown. Polling 4h acceptable pour MVP. | Phase 3 (si URSSAF enable) |
| **Signature Électronique** | PDF bête OK. Signature Phase 3+ if tax compliance require. | Phase 3+ |
| **Payment Links** | Client peut payer direct (optionnel feature). Out of scope. | Future |
| **Invoicing Templates** | PDF basic = OK. Branding templates Phase 3. | Phase 3 |

### Known Limitations Phase 2

1. **No Offline Mode** : Requiert Sheets access (no local cache fallback yet)
2. **No Webhooks** : Polling 4h latency max (vs instant webhooks)
3. **No Bulk Operations** : No batch upload Excel (must CLI or web one-by-one)
4. **No Signature Validation** : Factures not digitally signed
5. **No Multi-Language** : FR only (EN Phase 3 if demand)
6. **No Advanced Reporting** : Balances basic (no NOVA fiscal Phase 2)

---

## Risques & Mitigations

### Risques Phase 2 (Probabilité & Impact)

| Risque | Proba | Impact | Sévérité | Mitigation | Propriétaire |
|--------|-------|--------|----------|-----------|--------------|
| **Swan API instable** | 30% | Phase 2A bloquée | HIGH | Fallback manual reconciliation; cache 1h; scoring robuste (80%+ auto) | Dev |
| **Lettrage faux positif** | 20% | Mauvaise comptabilité | MEDIUM | Scoring strict (80% seuil); A_VERIFIER UI pour 60-79; audit trail | Dev |
| **Email SMTP fail** | 15% | Reminders manqués | LOW | Fallback: Jules voit deadline dashboard; log warn; queue retry | Dev |
| **URSSAF API rate limit** | 10% | Polling delayed | LOW | Batch sizing; spacing 4h; contact URSSAF proactif | PM |
| **Google Sheets quota exceeded** | 5% | Write fail | MEDIUM | Archive old factures; batch operation; contact Google if issue | Ops |
| **Cron job duplicate run** | 25% | Double-lettrage / double-email | MEDIUM | Idempotent logic (check reminder_sent, last_run); DB lock | Dev |
| **Timezone bugs** | 20% | Deadline calculation wrong | MEDIUM | Always UTC internals; test T+36h / T+48h scenario | Dev |
| **Data loss** | 5% | Facture disappear | CRITICAL | Sheets atomic writes + version history; backup CSV weekly | Ops |
| **OAuth2 token expiry** | 30% | URSSAF API fail | MEDIUM | Refresh token 59 min; retry auto | Dev |

### Risk Mitigation Strategy

#### Critical Risks (Data Loss, Swan Down)
- **Backup Plan**: Export all Sheets → CSV nightly to .claude/ folder (automated)
- **Monitoring**: Email alerts on cron failures within 1 min
- **Incident Response**: Contact URSSAF/Swan support; manual intervention SOP documented
- **Testing**: Weekly backup restore test; lettrage accuracy audit

#### High Risks (Lettrage accuracy, Email)
- **Testing**: Unit tests each scoring rule; integration test 50 invoice scenarios
- **Validation**: Jules reviews "A_VERIFIER" cases (not auto-locked)
- **Audit Trail**: All lettres logged with timestamp/user
- **Revert**: Manual "unletter" capability if error detected

#### Medium Risks (Timezone, OAuth, Quota)
- **Logging**: Structured logs capture all state transitions
- **Alerts**: Email Jules on warning level (not just errors)
- **Runbooks**: SOP for each failure scenario (documented)
- **Testing**: Edge cases (month boundaries, DST, leap seconds, etc.)

---

## Timeline & Phasing

### Phase 2 Development Roadmap

#### Week 1 (Days 1-5)
**Goal**: Historique + Filtres + fondations rappro

| Day | Feature | Effort | Dependencies | Status |
|-----|---------|--------|--------------|--------|
| 1 | E1-S1 (Search) backend | 1.5d | Phase 1 DB ready | Dev |
| 2 | E1-S1 (Search) UI | 0.5d | ^ | Dev |
| 3 | E1-S2 (Filters) | 1d | E1-S1 | Dev |
| 4 | E2-S1 (Swan sync) + E2-S2 (Scoring) | 2d | Swan API creds | Dev |
| 5 | E2-S1 tests, Swan integration | 1.5d | ^ | QA |

**Livrable**: Dashboard avec search, filtres, Swan sync 1x (manual test)

---

#### Week 2 (Days 6-10)
**Goal**: Lettrage complete, Reminders, UI validation

| Day | Feature | Effort | Dependencies | Status |
|-----|---------|--------|--------------|--------|
| 6 | E2-S3 (Manual validation UI) | 1d | E2-S2 | Dev |
| 7 | E2-S4 (Balances onglet) | 1d | E2 complete | Dev |
| 8 | E3-S1 (Email service) + E3-S2 (Countdown) | 2d | SMTP config | Dev |
| 9 | E3 tests + Phase 1 integration | 1d | ^ | QA |
| 10 | Buffer + perf tuning | 1d | All epic | Dev/QA |

**Livrable**: Lettrage complete (auto+manual), reminders, countdown dashboard

---

#### Week 3 (Days 11-15)
**Goal**: Annulation, CLI, Tests e2e

| Day | Feature | Effort | Dependencies | Status |
|-----|---------|--------|--------------|--------|
| 11 | E4-S1 (Annulation) | 1.5d | Phase 1 | Dev |
| 12 | E4-S2 (Avoir) optional | 0.5d | E4-S1 | Dev |
| 13 | E5-S1 (CLI reconcile) | 2d | E2 complete | Dev |
| 14 | E5 tests + CLI edge cases | 1d | ^ | QA |
| 15 | E2E tests + documentation + UAT avec Jules | 2d | All | QA/PM |

**Livrable**: CLI reconcile, annulation, full Phase 2 feature complete

---

### Acceptance & Go-Live Criteria

#### Pre-Launch Checklist
- [ ] All 6 epics feature-complete (todos in each story)
- [ ] Unit test coverage ≥ 80%
- [ ] Integration tests cover happy path + 5 error scenarios each
- [ ] E2E test : création → soumission → lettrage → dashboard
- [ ] Performance: dashboard < 1s, reconcile < 5 min
- [ ] Security: .env never committed, no secrets in logs
- [ ] Documentation: README, API docs, runbooks
- [ ] UAT with Jules: 3 factures create→reconcile manually
- [ ] Monitoring: alerts configured (cron fail, API error, email bounce)
- [ ] Backup: nightly export working, restore tested

#### Launch Day SOP
1. **Phase 1 stability check**: 48h zero errors
2. **Backup current Sheets**: Manual export to Drive
3. **Deploy Phase 2** to production
4. **Monitor 4h**: Check logs, cron runs, no alerts
5. **Jules test**: 2-3 factures live test
6. **Green light**: All clear → go-live

#### Rollback Plan
If Phase 2 breaks:
1. Revert app code to Phase 1 commit
2. Restore Sheets from backup (Google version history)
3. Contact Jules: revert status
4. Incident post-mortem (1-2 hours investigation)
5. Fix + re-deploy next day

---

## Critères d'Acceptance

### Definition of Done (per story)

#### Epic 1: Historique & Filtres
**E1-S1: Search**
- [ ] Search box finds "jean" in "Jean Dupont" (case-insensitive, fuzzy)
- [ ] Results paginate 50 items
- [ ] Click result → detail view with PDF link
- [ ] Perf: 100 factures in < 2 sec
- [ ] Test case: search 5 times = 5 correct results
- [ ] Unit test: `test_search_fuzzy_match()`

**E1-S2: Filters**
- [ ] Dropdown statut multi-select (all 10 statuts)
- [ ] Date range picker ISO format
- [ ] Montant range slider
- [ ] Client dropdown pre-populated
- [ ] "Apply" button works, "Reset" clears all
- [ ] Perf: apply filters < 1 sec
- [ ] Test case: filter PAYE + fév 2026 = 3 results

---

#### Epic 2: Rapprochement Bancaire
**E2-S1: Swan Sync**
- [ ] Cron every 6h imports 12+ transactions
- [ ] No duplicates in DB (transaction_id unique)
- [ ] Each transaction : id, amount, label, date, status = "A_TRAITER"
- [ ] 72h cron run = 0 errors in logs
- [ ] Perf: 12 txn import < 5 min
- [ ] Test case: manual trigger `sap reconcile` imports correct data

**E2-S2: Scoring**
- [ ] Facture 100€ + txn 100€ libellé URSSAF date ±1j = score 95 (AUTO)
- [ ] Facture 100€ + txn 100€ libellé autre date ±2j = score 60 (VERIFY)
- [ ] Facture 100€ + txn 95€ = no match (score < 60)
- [ ] 50 factures PAYE: 90% AUTO, 8% VERIFY, 2% NOMATCH (acceptable)
- [ ] Test case: `test_lettrage_scoring_rules()` covers 10 scenarios

**E2-S3: Manual Validation UI**
- [ ] 4 "A_VERIFIER" rows visible in orange
- [ ] Click row → modal shows facture + transaction + score
- [ ] Jules click "C'est bon" → lettrage écrit, facture RAPPROCHE
- [ ] Dashboard updates (row now green)
- [ ] Test case: manual lettrage 4 rows = all green after

**E2-S4: Balances**
- [ ] Card "100€ reçus" (RAPPROCHE CA)
- [ ] Card "2 en attente" (VALIDE + PAYE not RAPPROCHE)
- [ ] Card "25 factures traitées" (all statuts != ANNULE)
- [ ] Refresh hourly (formule auto)
- [ ] Test case: facture state change → balances update < 5 min

---

#### Epic 3: Reminders
**E3-S1: Email Service**
- [ ] Facture EN_ATTENTE T+36h → email Jules reçu < 5 min
- [ ] Email contient client, montant, délai restant
- [ ] Pas double-email si cron run 2x
- [ ] Retry 3x si SMTP bounce
- [ ] Logging: email sent, timestamp
- [ ] Test case: create facture, wait 36h (mock clock), send email, check inbox

**E3-S2: Countdown**
- [ ] Dashboard col "Délai Restant" affiche heures:minutes
- [ ] ≥36h = vert, 12-36h = orange, <12h = rouge
- [ ] Refresh JS auto toutes les 60 sec
- [ ] Tri par délai possible (urgent first)
- [ ] Test case: EN_ATTENTE 40h old = orange badge "8h restantes"

---

#### Epic 4: Annulation & Avoir
**E4-S1: Annulation**
- [ ] Dashboard button "Annuler" on BROUILLON et SOUMIS
- [ ] Modal confirmation + raison textbox
- [ ] Facture statut = ANNULE, reason logged
- [ ] Historique shows facture grey ANNULE
- [ ] Test case: annule BROUILLON "montant erroné" → visible historique

**E4-S2: Avoir** (optional Phase 2)
- [ ] Click "Créer Avoir" on RAPPROCHE
- [ ] Modal montant + raison
- [ ] Facture_avoir créée, lien parent
- [ ] Test case: avoir 20€ on 100€ facture → comptabilité clean

---

#### Epic 5: CLI
**E5-S1: sap reconcile**
- [ ] `sap reconcile` imports Swan, matches, outputs summary
- [ ] Output: AUTO 12, VERIFY 2, NOMATCH 1
- [ ] Sheets updated (Lettrage, Factures, Balances)
- [ ] Exit code 0
- [ ] Perf: 50 factures < 5 min
- [ ] Test case: run twice = idempotent (2nd run no change if --force not used)

**E5-S2: sap sync** (extended)
- [ ] `sap sync` affiche status factures EN_ATTENTE, VALIDE, PAYE
- [ ] Format table, JSON, CSV options
- [ ] Test case: 3 VALIDE, 2 PAYE affichées correctement

---

### Acceptance Audit Checklist

#### Code Quality
- [ ] Ruff check --fix: 0 errors
- [ ] MyPy --strict: 0 errors
- [ ] Black/format: consistent
- [ ] No `print()`, only logging
- [ ] Docstrings on all functions
- [ ] No secrets in code (grep for keys)

#### Testing
- [ ] Unit tests ≥ 80% coverage
- [ ] Integration tests 3+ scenarios per epic
- [ ] E2E test: 1 facture full lifecycle
- [ ] Error handling: 5 error scenarios tested
- [ ] Mocking: all external APIs mocked (no live calls in tests)
- [ ] Deterministic: tests pass 100% (no flakes)

#### Documentation
- [ ] README: Phase 2 features listed
- [ ] API docs: new endpoints documented
- [ ] Runbooks: how to handle alerts (email fail, Swan down, etc.)
- [ ] User guide: how to use search, filters, reminders
- [ ] Database schema: Sheets onglets schema documented

#### Performance & Security
- [ ] Dashboard < 1s load (5, 50, 100 factures benchmarked)
- [ ] Reconcile < 5 min (50 factures)
- [ ] No sensitive data in logs
- [ ] SMTP credentials not hardcoded
- [ ] API tokens refresh before expiry
- [ ] Rate limits respected (Sheets, Swan, URSSAF)

#### Monitoring & Incidents
- [ ] Alert emails configured (cron fail, API error)
- [ ] Cron logs captured (success/fail)
- [ ] Error rate < 1% (monitoring 48h)
- [ ] Backup export running nightly
- [ ] Restore backup tested (can recover data)

---

## Appendix A: Google Sheets Onglets Schéma Phase 2

### Onglet "Transactions" (nouveau, data brute)
| Colonne | Type | Éditable | Notes |
|---------|------|----------|-------|
| transaction_id | TEXT | NON | Unique Swan ID |
| montant | NUMBER | NON | EUR |
| libellé | TEXT | NON | Swan label |
| date_valeur | DATE | NON | Payment date |
| statut_lettrage | TEXT ("A_TRAITER", "LETTRE", "A_VERIFIER", "PAS_DE_MATCH") | OUI (Jules manual) | Default A_TRAITER |
| facture_id | TEXT (FK) | OUI (auto ou Jules) | Linked invoice |
| date_import | TIMESTAMP | NON | When imported |

### Onglet "Lettrage" (nouveau, calculé via formules)
| Colonne | Type | Contenu | Notes |
|---------|------|---------|-------|
| facture_id | TEXT | Key from Factures | |
| montant_facture | FORMULA | =VLOOKUP(facture_id, Factures, 3) | |
| transaction_id | TEXT | Manually matched or AUTO | |
| montant_transaction | FORMULA | =VLOOKUP(transaction_id, Transactions, 2) | |
| écart | FORMULA | =montant_facture - montant_transaction | Difference |
| score_confiance | FORMULA | =... (scoring logic: +50 +30 +20) | Calculated |
| statut_lettrage | FORMULA/MANUAL | =IF(score≥80, "AUTO", IF(score≥60, "A_VERIFIER", "PAS_DE_MATCH")) | |
| date_lettrage | TIMESTAMP | When matched | |
| notes | TEXT | Jules remarks | Optional |

### Onglet "Balances" (nouveau, calculé)
| Colonne | Contenu | Formule | Notes |
|---------|---------|---------|-------|
| month | "2026-03" | | Key |
| nb_factures | COUNTIF | =COUNTIF(Factures[statut], "<>ANNULE") | Active only |
| ca_total | SUMIF | =SUMIF(Factures[statut], "<>ANNULE", Factures[montant]) | |
| ca_lettree | SUMIF | =SUMIF(Factures[statut], "RAPPROCHE", Factures[montant]) | Received |
| solde | FORMULA | =ca_lettree | What we have |
| nb_en_attente | COUNTIF | =COUNTIF(Factures[statut], ["EN_ATTENTE", "VALIDE", "PAYE"]) | Pending |
| nb_non_lettrees | COUNTIF | =COUNTIF(Factures[statut]="PAYE") - COUNTIF(Lettrage[transaction_id]<>"") | Missing match |

---

## Appendix B: Email Templates

### Template 1: Reminder T+36h
```
From: Jules (via SAP-Facture)
To: [JULES_EMAIL]
Subject: [SAP-Facture] RAPPEL — Facture XXXX en attente validation (délai 12h)

---

Bonjour Jules,

Rappel: Facture en attente de validation depuis 36 heures.

Facture #F12345
Client: Jean Dupont
Montant: 100 EUR
Email client: jean.dupont@example.com
Téléphone: +33 6 12 34 56 78

Date soumission: 15/03/2026 14:30
Délai restant: 12 heures
EXPIRATION: 17/03/2026 14:30 (lundi 14:30)

⚠️ CLIENT DOIT VALIDER AVANT LUNDI 14H30 ⚠️

--- ACTIONS ---

Option 1: Appeler le client
  Téléphone: +33 6 12 34 56 78
  Message: "Bonjour Jean, tu as reçu un email d'URSSAF pour valider ma facture ? Faut cliquer le lien avant lundi."

Option 2: Envoyer SMS / Email
  Email: jean.dupont@example.com
  Message: Lien portail URSSAF: [copier du portail]

Option 3: Voir sur le Dashboard
  Dashboard: https://sap-facture.example.com/dashboard
  Chercher facture #F12345, voir countdown

--- INFO DASHBOARD ---

Historique factures du client Jean Dupont:
  - F12343 (80€, 10/03) — RAPPROCHE ✓
  - F12344 (95€, 12/03) — RAPPROCHE ✓
  - F12345 (100€, 15/03) — EN_ATTENTE ⏱ 12h 00m

--- NOTES SYSTÈME ---
Rappel automatique envoyé à T+36h (une seule fois).
Si facture expire à T+48h sans validation, tu pourras la relancer.

---

Merci,
SAP-Facture Team
```

### Template 2: Lettrage A_VERIFIER
```
From: SAP-Facture
To: [JULES_EMAIL]
Subject: [SAP-Facture] ⚠ Lettrage manuel requis — Facture XXXX

---

Bonjour Jules,

Le rapprochement bancaire a détecté une correspondance possible mais demande ta validation manuelle.

Facture:
  #F12345 (100 EUR)
  Client: Jean Dupont
  Date: 15/03/2026
  Statut: PAYE

Transaction Swan détectée:
  Montant: 100 EUR
  Libellé: "VIRUR FRANCE 001 XXX"
  Date: 18/03/2026
  Montant détecté: 100 EUR

Score confiance: 60/100
  ✓ Montant exact (100€ = 100€): +50 pts
  ✓ Date écart < 3j (3 jours): +30 pts
  ✗ Libellé ne contient pas "URSSAF": 0 pts
  = 60 pts total

--- VALIDATION REQUISE ---

La transaction match le montant exact et la date est OK (±3j), mais le libellé est différent.

C'est probablement la bonne transaction? Clique le bouton ci-dessous pour confirmer.

[BOUTON: Confirmer Lettrage] [BOUTON: C'est pas ça, chercher autre]

Dashboard (validation manuelle): https://sap-facture.example.com/dashboard#lettrage

---

Si c'est la bonne transaction → je la mets en vert et ta comptabilité sera à jour.
Si c'est pas ça → je continue chercher une autre transaction.

Merci,
SAP-Facture
```

---

## Appendix C: Runbooks (Troubleshooting)

### Runbook: "Email Reminders Not Sent"

**Symptom**: Jules says "Je n'ai pas reçu le rappel T+36h"

**Diagnosis**:
1. Check logs: `grep "reminder sent" sap.log` → found "reminder_sent_at=X"?
   - If no → cron didn't run or facture not EN_ATTENTE 36h yet
2. Check Sheets: onglet Factures, facture statut + reminder_sent flag
3. Check SMTP: test email manuellement
   ```bash
   $ python -c "
   from utils.email import send_email
   send_email(to='jules@mail.fr', subject='Test', body='Test email')
   "
   ```
   - If fail → SMTP config broken

**Solutions**:
- **Cron didn't run**: Check APScheduler logs, restart: `systemctl restart sap-scheduler`
- **Email config**: Re-set SMTP password in .env, restart
- **Facture not 36h yet**: Wait or manually trigger `python -m sap.tasks.reminders --force`
- **Email bounced**: Check SMTP bounce log, retry

---

### Runbook: "Reconciliation Failed (Swan API)"

**Symptom**: `sap reconcile` fails with "Swan API timeout"

**Diagnosis**:
1. Check if Swan API is down: ping Swan status page
2. Check rate limits: Are we over 100 req/min?
3. Check network: `curl https://api.swan.io`

**Solutions**:
- **API down**: Wait 10 min, retry. Meanwhile, manually check Swan app for transactions
- **Rate limit**: Space out cron jobs (don't run reconcile + polling together)
- **Network**: Check VPN/proxy, restart app

---

### Runbook: "Lettrage Accuracy Low (< 90%)"

**Symptom**: Dashboard shows "45% AUTO, 40% VERIFY, 15% NOMATCH" = bad

**Diagnosis**:
1. Review "A_VERIFIER" cases: Are montants close? Dates OK?
2. Review "PAS_DE_MATCH": Are transactions actually missing?
3. Check Swan sync: are all transactions imported?

**Solutions**:
- **Montants mismatch**: URSSAF may have deducted charges. Contact URSSAF support.
- **Libellé variations**: Add more fuzzy matching to scoring algo
- **Missing transactions**: Check Swan date range, ensure all 30 days imported
- **Manual fix**: Jules validate manually via dashboard UI

---

## Document Metadata

- **Version**: 1.0
- **Status**: ✅ Ready for Development
- **Last Updated**: March 2026
- **Product Owner**: Sarah (BMAD)
- **Tech Lead**: [TBD]
- **Stakeholders**: Jules Willard (user), Finance (QA), IT (DevOps)

---

**Signature Line** (if needed for approval):

Product Owner: ________________________ Date: ___________

Tech Lead: ________________________ Date: ___________

Jules Willard: ________________________ Date: ___________

---

*End of PRD Phase 2 — SAP-Facture*
