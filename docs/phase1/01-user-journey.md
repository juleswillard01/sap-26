# User Journey Analysis — SAP-Facture

## Executive Summary

Ce document analyse le **SCHEMA 1 "Parcours Utilisateur Quotidien"** extrait de SCHEMAS.html (section id="parcours"). Il détaille le workflow complet de Jules Willard, micro-entrepreneur en cours particuliers, du moment où il dispense un cours jusqu'à la réception du paiement URSSAF.

**Date d'analyse**: Mars 2026
**Utilisateur cible**: Jules Willard, SIREN 991552019
**Métier**: Cours particuliers (micro-entrepreneur / auto-entrepreneur)
**Durée estimée du parcours complet**: 48-96 heures (3-4 jours calendaires)

---

## 1. Persona — Jules Willard

### Profil Démographique & Professionnel

| Attribut | Description |
|----------|-----------|
| **Nom** | Jules Willard |
| **Statut juridique** | Auto-entrepreneur (micro-entrepreneur) |
| **SIREN** | 991552019 |
| **Secteur d'activité** | Services à la personne — Cours particuliers (enseignement) |
| **Fréquence d'activité** | Plusieurs cours par semaine, horaires variables |
| **Localisation** | France (client URSSAF) |
| **Charge fiscale** | Micro BNC (Bénéfices Non Commerciaux) avec abattement 34% |
| **Charges sociales estimées** | 25,8% de cotisations sur CA encaissé |
| **Deadline NOVA** | Saisie trimestrielle obligatoire (attestations fiscales) |

### Caractéristiques Comportementales

**Technologie:**
- Utilisateur intermédiaire (web + CLI à l'aise)
- Accès régulier à navigateur moderne et terminal
- Familiarité avec Google Sheets pour suivi financier

**Motivations principales:**
1. **Facturation rapide** : Créer et soumettre une facture en < 5 min après un cours
2. **Automatisation** : Minimiser les tâches administratives récurrentes
3. **Visibilité financière** : Savoir en temps réel quel paiement est attendu et quand
4. **Conformité** : Respecter les obligations URSSAF sans friction
5. **Résilience** : Pouvoir continuer en cas de problème système (fallback sur Sheets)

**Frustrations actuelles:**
- Inscription manuelle des clients à URSSAF (erreurs saisie)
- Suivi manuel du statut des factures (polls réguliers)
- Pas de visibilité sur les montants reçus en attente
- Risque d'oubli de relance client si validation > 48h

**Contexte d'utilisation:**
- Avant un cours : vérification rapide du planning (mobile/PC)
- Juste après un cours : création facture (PC préféré)
- Fin de semaine : suivi tableau de bord et rapprochement (PC)
- À la demande : exports CSV pour comptable

---

## 2. User Stories Extraites du Parcours

### Epic 1: Gestion Avant le Cours

#### US-1.1: Consulter son planning clients
**En tant que** Jules (micro-entrepreneur)
**Je veux** voir rapidement l'horaire de mes cours du jour/semaine
**Afin que** je puisse confirmer les RDV avec mes élèves et me préparer

**Acceptance Criteria:**
- [ ] Vue du planning accessible en < 2 sec (web + mobile)
- [ ] Affichage nom élève, horaire début/fin, lieu (si pertinent)
- [ ] Indication du statut "confirmé" ou "à confirmer"
- [ ] Intégration facultative avec calendrier externe (Google Calendar, Outlook)

**Estimation:** 3 (faible importance, gain marginal)

---

#### US-1.2: Confirmer/annuler RDV avec l'élève
**En tant que** Jules
**Je veux** envoyer une confirmation au client (SMS/email) avant un cours
**Afin que** le client sait que je viens et peut prévoir

**Acceptance Criteria:**
- [ ] Un-click pour envoyer confirmation SMS ou email
- [ ] Template pré-rempli (prénom élève, heure, adresse)
- [ ] Historique des confirmations envoyées
- [ ] Option d'annulation avec raison (maladie, urgence, etc.)

**Estimation:** 4 (comfort, hors MVP core)

---

### Epic 2: Création et Soumission Facture (Parcours Critique)

#### US-2.1: Créer une nouvelle facture
**En tant que** Jules
**Je veux** saisir les détails d'un cours (client, heures, tarif) et générer une facture
**Afin que** je puisse la soumettre à URSSAF pour déclencher le paiement

**Acceptance Criteria:**
- [ ] Formulaire web pré-rempli (dernier client, tarif standard)
- [ ] Sélection client existant ou création rapide (nom, email, adresse)
- [ ] Champs: type unité (heure), nature code (service BNC), quantité, montant unitaire
- [ ] Calcul auto montant total (quantité × unitaire)
- [ ] Dates début/fin du service (généralement même jour pour cours)
- [ ] Description libre (optionnel, ex: "Cours de maths niveau 1ère")
- [ ] Validation minimale: client ≠ vide, montant > 0, dates cohérentes
- [ ] Sauvegarde immédiate en statut BROUILLON dans Sheets

**Estimation:** 5 (core MVP, chemin heureux)

---

#### US-2.2: Générer la facture PDF
**En tant que** Jules
**Je veux** obtenir un PDF professionnel avec logo et en-tête standard
**Afin que** la facture soit lisible et complète pour l'URSSAF

**Acceptance Criteria:**
- [ ] PDF généré automatiquement lors de la création (ou bouton "Générer")
- [ ] Template PDF inclus: logo Jules, SIREN, adresse, dates, montant, conditions de paiement
- [ ] Logo personnalisé stocké dans Google Drive (réutilisable)
- [ ] Texte légal "Demande de paiement en ligne URSSAF" visible
- [ ] PDF nommé: `Facture_{client_id}_{date_facture}.pdf`
- [ ] PDF uploadé dans Google Drive dossier "Factures/2026"
- [ ] Lien PDF accessible depuis la ligne facture (UI + Sheets)

**Estimation:** 5 (core MVP, génération technique simple)

---

#### US-2.3: Soumettre la facture à URSSAF
**En tant que** Jules
**Je veux** envoyer ma facture via l'API URSSAF en un clic
**Afin que** le processus de paiement commence et l'élève reçoit une demande de validation

**Acceptance Criteria:**
- [ ] Bouton "Soumettre à URSSAF" dans UI web
- [ ] Validation pré-envoi: client inscrit URSSAF OU auto-inscription si nouveau
- [ ] Appel API URSSAF POST /demandes-paiement avec payload:
  - `id_client` (URSSAF)
  - `montant` (100% du montant facture)
  - `nature_code` (BNC)
  - `dates` (début/fin service)
  - Autres champs requis par URSSAF
- [ ] Récupération `id_demande` et `statut: CREE` de la réponse
- [ ] Mise à jour immédiate statut Sheets: BROUILLON → SOUMIS → CREE
- [ ] Message de succès affiché: "Facture soumise, ID demande: {id_demande}"
- [ ] Gestion erreurs URSSAF: affichage message d'erreur, re-tentative possible

**Estimation:** 5 (core MVP, intégration URSSAF critique)

---

#### US-2.4: Auto-inscrire un client URSSAF (nouveau client)
**En tant que** Jules
**Je veux** que mon système inscrive automatiquement un nouveau client URSSAF
**Afin que** je n'ai pas à remplir un formulaire séparé et que le paiement soit possible

**Acceptance Criteria:**
- [ ] Détection client pas inscrit à URSSAF lors de création facture
- [ ] Appel API URSSAF POST /particuliers avec: nom, prénom, email, adresse, code postal, ville
- [ ] Récupération `urssaf_id` (identifiant technique URSSAF)
- [ ] Vérification que client a fait ≥1 déclaration fiscale (sinon erreur bloquante)
- [ ] Sauvegarde `urssaf_id` dans onglet Clients (Sheets)
- [ ] Confirmation utilisateur: "Client X inscrit, URSSAF ID: {id}"
- [ ] Pas de relancé, facture peut être créée immédiatement après inscription

**Estimation:** 4 (MVP, conditionnelle / edge case géré)

---

### Epic 3: Suivi Automatique Post-Soumission

#### US-3.1: Client reçoit notification URSSAF
**En tant que** Client (élève)
**Je reçois** un email URSSAF pour valider le paiement
**Afin que** je confirme les détails et que le paiement avance

**Acceptance Criteria:**
- [ ] Email envoyé par URSSAF (système, pas Jules)
- [ ] Email contient lien portail URSSAF pour validation
- [ ] Délai envoi: < 1 min après soumission facture
- [ ] Template URSSAF: lien de confirmation + données facture
- [ ] Pas de responsabilité Jules (URSSAF gère)

**Estimation:** N/A (système externe, dependency)

---

#### US-3.2: Polling automatique du statut (4h)
**En tant que** Jules (indirectement)
**Je veux** que le système interroge URSSAF toutes les 4h pour mettre à jour le statut
**Afin que** je n'ai pas besoin de vérifier manuellement et je suis toujours à jour

**Acceptance Criteria:**
- [ ] Cron job ou scheduler toutes les 4 heures
- [ ] Appel GET /demandes-paiement/{id_demande} pour chaque facture SOUMIS/CREE/EN_ATTENTE/VALIDE
- [ ] Mise à jour statut Sheets si changement: CREE → EN_ATTENTE → VALIDE → PAYE
- [ ] Log des appels (pour debug)
- [ ] Gestion timeout/erreur API (retry dans 1h)
- [ ] Pas de bruit utilisateur si pas de changement

**Estimation:** 4 (importante mais asynchrone)

---

#### US-3.3: Client valide (ou pas) dans 48h
**En tant que** Client
**Je valide** (ou non) la demande de paiement dans le délai
**Afin que** le paiement soit autorisé ou refusé

**Acceptance Criteria:**
- [ ] Client a accès portail URSSAF pour validation
- [ ] Délai 48h depuis email URSSAF
- [ ] Jules ne contrôle pas cette action (URSSAF gère)
- [ ] Statut final: VALIDE ou REJETE (détecté par polling)

**Estimation:** N/A (système externe)

---

#### US-3.4: Reminder automatique si T+36h sans validation
**En tant que** Jules
**Je reçois** un email rappel si un client n'a pas validé après 36h
**Afin que** je puisse le relancer et éviter l'expiration

**Acceptance Criteria:**
- [ ] Calcul temps écoulé depuis création (CREE)
- [ ] Si 36h < temps < 48h → envoyer email rappel à Jules
- [ ] Email: "Facture client X en attente de validation, delai 12h restants"
- [ ] Include: lien facture + contact client (téléphone/email)
- [ ] Pas de re-reminder si déjà envoyé
- [ ] Status reste EN_ATTENTE

**Estimation:** 5 (feature comfort, important pour taux validation)

---

#### US-3.5: URSSAF traite le paiement (après validation client)
**En tant que** URSSAF
**Je déduis** 50% du montant pour charges client + 50% reste versé à Jules
**Afin que** le virement se fasse sur le compte Swan

**Acceptance Criteria:**
- [ ] Client paye ses 50% directement à URSSAF (never reaches Jules)
- [ ] URSSAF vire 100% du montant original à Jules (Swan)
- [ ] Statut: VALIDE → PAYE
- [ ] Jules voit transaction dans Swan (rapprochement bancaire)

**Estimation:** N/A (système URSSAF)

---

#### US-3.6: Virement reçu sur Swan
**En tant que** Jules
**Je reçois** un virement d'URSSAF sur mon compte bancaire
**Afin que** j'ai l'argent en caisse

**Acceptance Criteria:**
- [ ] Swan enregistre transaction entrante (libelle: "URSSAF", montant 100%)
- [ ] Jules voit virement dans appli Swan
- [ ] Date valeur = date paiement URSSAF (J+1 généralement)
- [ ] Rapprochement automatique possible (voir US-4.1)

**Estimation:** N/A (système bancaire)

---

### Epic 4: Suivi Fin de Semaine

#### US-4.1: Consulter dashboard des factures
**En tant que** Jules
**Je veux** voir un tableau avec toutes mes factures (statuts, montants, dates)
**Afin que** j'ai une visibilité complète sur mon flux entrant

**Acceptance Criteria:**
- [ ] Tableau web (FastAPI SSR avec Jinja2 + Tailwind)
- [ ] Colonnes: Facture ID, Client, Montant, Dates, Statut, Date dernière mise à jour
- [ ] Statuts visibles: BROUILLON, SOUMIS, CREE, EN_ATTENTE, VALIDE, PAYE, RAPPROCHE, REJETE, EXPIRE, ANNULE
- [ ] Couleurs: vert (OK), orange (en attente), rouge (problème)
- [ ] Filtres: par statut, par client, par date
- [ ] Tri: par date création (plus récent en haut), par montant
- [ ] Nombre total CA visible (somme montants PAYE)
- [ ] Nombre factures en attente visible
- [ ] Lien vers PDF pour chaque facture
- [ ] Responsive mobile (liste simplifiée)

**Estimation:** 5 (MVP, feature clé de visibilité)

---

#### US-4.2: Rapprochement bancaire automatique
**En tant que** Jules
**Je veux** que le système relie automatiquement les virements Swan aux factures
**Afin que** j'évite les erreurs de suivi manuel et je vois rapidement ce qui est payé

**Acceptance Criteria:**
- [ ] Appel API Swan GraphQL: GET /transactions (filtre 5 derniers jours)
- [ ] Pour chaque facture PAYE: chercher 1 transaction correspondante
- [ ] Critères matching:
  - Montant transaction = 100% montant facture
  - Libellé contient "URSSAF" ou correspond pattern
  - Date transaction ± 5 jours de la date paiement URSSAF attendue
- [ ] Scoring confiance:
  - Montant exact: +50 pts
  - Date < 3j écart: +30 pts
  - Libellé URSSAF: +20 pts
  - Total >= 80 → AUTO-LETRAGE
  - Total 60-80 → A VERIFIER (surligné orange)
  - Total < 60 → PAS DE MATCH (surligné rouge)
- [ ] Écriture dans onglet Lettrage (avec score)
- [ ] Mise à jour statut facture: PAYE → RAPPROCHE (si auto)
- [ ] Onglet Balances mis à jour (sommes lettrage)

**Estimation:** 5 (MVP phase 2, impact accounting important)

---

#### US-4.3: Exporter les factures en CSV
**En tant que** Jules
**Je veux** exporter mes factures / transactions en CSV
**Afin que** je puisse les importer dans un logiciel comptable tiers

**Acceptance Criteria:**
- [ ] Bouton "Export CSV" dans dashboard
- [ ] Colonnes export:
  - Pour factures: facture_id, client_nom, montant, nature_code, dates, statut, pdf_link
  - Pour transactions: transaction_id, date, montant, libelle, statut_lettrage
- [ ] Filtres: date plage, statut
- [ ] Format CSV: UTF-8 BOM, délimiteur `,`
- [ ] Nom fichier: `SAP-Facture_Factures_{YYYYMMDD}.csv`
- [ ] Téléchargement direct

**Estimation:** 3 (nice-to-have, faible effort)

---

### Epic 5: CLI & Automation

#### US-5.1: Soumettre facture via CLI
**En tant que** Jules (mode avancé)
**Je veux** créer et soumettre une facture en ligne de commande
**Afin que** je peux automatiser ou utiliser un script batch

**Acceptance Criteria:**
- [ ] Commande: `sap submit --client <id> --hours <n> --rate <montant> --dates <YYYY-MM-DD>`
- [ ] Alternative JSON: `sap submit --json facture.json`
- [ ] Affichage: confirmation créée + ID demande URSSAF
- [ ] Gestion erreurs: message clair, exit code 0/1

**Estimation:** 3 (nice-to-have, CLI power user)

---

#### US-5.2: Synchroniser les statuts via CLI
**En tant que** Jules
**Je veux** forcer un polling immédiat des statuts URSSAF
**Afin que** j'ai une réponse synchrone (pas 4h d'attente)

**Acceptance Criteria:**
- [ ] Commande: `sap sync`
- [ ] Appel GET /demandes-paiement pour toutes factures en cours
- [ ] Affichage tableau statuts mis à jour
- [ ] Export Sheets mis à jour
- [ ] Durée: < 30 sec

**Estimation:** 4 (feature comfort, évite attente)

---

#### US-5.3: Réconcilier les transactions via CLI
**En tant que** Jules
**Je veux** forcer un rapprochement bancaire immédiat
**Afin que** je vois tout de suite quel paiement est arrivé

**Acceptance Criteria:**
- [ ] Commande: `sap reconcile`
- [ ] Appel Swan API + matching factures
- [ ] Affichage: résumé (AUTO: X, A VERIFIER: Y, PAS_MATCH: Z)
- [ ] Sheets lettrage mis à jour
- [ ] Durée: < 20 sec

**Estimation:** 4 (feature comfort, nice-to-have phase 2)

---

## 3. Points de Friction Identifiés

### Friction 1: Inscription Client URSSAF Manuelle
**Où:** Avant création facture (US-2.4)
**Symptôme:** Jules doit remplir à la main les données client (nom, email, adresse, etc.)
**Impact:** Lenteur, risque erreurs saisie (email mal tapé = notification client non reçue)
**Sévérité:** Haute (blocage facture si nouveau client)
**Mitigation:**
- Auto-inscription API URSSAF (USA-2.4)
- UI pré-complète champs depuis Sheets clients
- Validation email live (format check)

---

### Friction 2: Expiration Facture si Client Oublie Validation 48h
**Où:** Phase EN_ATTENTE → EXPIRE (diagramme états)
**Symptôme:** Client ne voit pas email URSSAF, facture expire, Jules doit re-soumettre
**Impact:** Retard paiement 3-7 jours, frustration Jules
**Sévérité:** Haute (récurrence probable)
**Mitigation:**
- Email reminder à T+36h (US-3.4) → Jules relance client directement
- Affichage prominent du compte à rebours (dashboard)
- Notification push (phase 3)

---

### Friction 3: Pas de Visibilité sur Paiements en Attente
**Où:** Entre soumission et validation URSSAF
**Symptôme:** Jules ne sait pas si une facture attend validation ou est perdue
**Impact:** Stress, relances inutiles, mauvaise cash flow visibility
**Sévérité:** Moyenne (mitigée par polling auto)
**Mitigation:**
- Dashboard avec statuts actualisés toutes les 4h (US-4.1)
- Rappels visuels (couleurs, icônes)
- Nombre factures "en attente" prominent

---

### Friction 4: Rapprochement Bancaire Manuel
**Où:** Après réception virement Swan
**Symptôme:** Jules doit vérifier manuellement que transaction Swan = facture URSSAF
**Impact:** Risque oublis/erreurs, charge administrative, pas de trace
**Sévérité:** Moyenne (acceptable si 5-10 factures/semaine)
**Mitigation:**
- Rapprochement automatique avec scoring confiance (US-4.2)
- Onglet Lettrage dans Sheets (auto-formula basée matching)
- Flag "A VERIFIER" pour cas ambigus

---

### Friction 5: Délai Polling 4h Trop Long
**Où:** Après validation client, avant statut PAYE visible
**Symptôme:** Jules peut attendre 4h pour voir "PAYE" alors que client a validé immédiatement
**Impact:** Incertitude, tentatives re-soumission, support requests
**Sévérité:** Basse (acceptable pour auto-entrepreneur)
**Mitigation:**
- CLI `sap sync` force appel immédiat (US-5.2)
- Lien webhook URSSAF (future, phase 3)

---

### Friction 6: Pas de Mobile-First
**Où:** Avant cours (consultation planning) + après cours (création facture)
**Symptôme:** Interface desktop non optimisée pour téléphone
**Impact:** Friction UX, Julius doit utiliser PC après chaque cours
**Sévérité:** Basse (MVP desktop accepté, phase 3 mobile)
**Mitigation:**
- MVP: responsive design Tailwind (tableau adaptable)
- Phase 3: Progressive Web App (PWA) + offline support

---

### Friction 7: Dépendance Google Sheets
**Où:** Stockage données, calculs taux charges, simulations fiscales
**Symptôme:** Si Sheets down ou formule cassée, système bloqué
**Impact:** Perte data, calculs faux (conséquences fiscales graves)
**Sévérité:** Moyenne (mitigée par backup manuel Jules)
**Mitigation:**
- Sheets comme backend volontaire (accepté design)
- Backup régulier (API export nuit)
- Fallback: CLI read-only sur cache local

---

## 4. Fréquence d'Utilisation Estimée par Action

| Action | Fréquence | Durée | Contexte | Criticité |
|--------|-----------|-------|---------|-----------|
| Vérifier planning clients | 5-7x/semaine | 30 sec | Avant chaque cours | Haute |
| Confirmer RDV avec élève | 5-7x/semaine | 1-2 min | Jour du cours | Moyenne |
| Créer facture | 5-7x/semaine | 3-5 min | Juste après cours | Critique |
| Générer PDF | 5-7x/semaine | < 1 sec | Auto après création | Critique |
| Soumettre URSSAF | 5-7x/semaine | < 10 sec | Immediat après création | Critique |
| Consulter dashboard | 3-5x/semaine | 2-5 min | Fin d'après-midi / soirée | Haute |
| Rapprochement bancaire | 1x/semaine | 3-5 min | Vendredi / lundi | Moyenne |
| Exporter CSV | 1x/trimestre | 1-2 min | Demande comptable | Basse |
| CLI sync/submit | 2-3x/mois | < 1 min | Mode avancé, debug | Basse |
| Reminder relance client | 1-2x/mois | < 1 min | Automatique, Jules lit email | Moyenne |

**Insights:**
- **Parcours critique quotidien:** Vérifier planning → Confirmer RDV → Créer facture → Soumettre URSSAF (total: ~10 min/cours)
- **Prise de risque acceptée:** Polling 4h OK car factures pas urgentes (paiement J+1 à J+2)
- **Effort administratif cible:** < 30 min/semaine (hors cours eux-mêmes)

---

## 5. Parcours Critique (Happy Path) vs Alternatifs

### 5.1 Parcours Critique — "From Lesson to Payment"

```
[Jour J] Après cours
├─ Jules ouvre SAP-Facture (web UI)
├─ Sélectionne client dans dropdown (déjà inscrit URSSAF)
├─ Remplit: heures=1, tarif=30€, dates=aujourd'hui
├─ Clique "Créer facture"
│  └─ Système génère PDF + sauvegarde BROUILLON dans Sheets
├─ Clique "Soumettre URSSAF"
│  └─ API POST /demandes-paiement → répond {id_demande, statut: CREE}
│  └─ Statut Sheets: BROUILLON → SOUMIS → CREE
├─ Message succès: "Facture soumise, ID: {id_demande}"
└─ Jules ferme l'appli

[Jour J, dans l'heure]
├─ URSSAF envoie email client pour validation
└─ Client clique lien validation

[Jour J, T+36h]
├─ Polling auto: statut reste EN_ATTENTE (client pas encore validé)
└─ Pas d'action Jules

[Jour J, T+36h-40h]
├─ Système détecte T+36h sans validation
├─ Email rappel à Jules: "Client X : validation en attente, 12h restants"
└─ Jules peut appeler client optionnellement

[Jour J+1, matin]
├─ Client valide enfin
├─ Polling auto 4h détecte: statut VALIDE → PAYE
├─ URSSAF vire 100€ à Swan
└─ Sheets mis à jour: PAYE

[Jour J+1, fin de semaine (ex: vendredi)]
├─ Jules consulte dashboard: facture verte "PAYE"
├─ Rapprochement auto détecte transaction Swan
├─ Lettrage auto: score 95 → "LETTRE AUTO"
└─ Statut final: RAPPROCHE
```

**Durée totale:** 1-2 jours calendaires (T+24 à T+48h)
**Actions Jules:** 3 clics + optionnel 1 appel téléphone
**Résultat:** Argent reçu, tracé comptable OK

---

### 5.2 Parcours Alternatif 1: Nouveau Client

```
[Jour J] Après cours
├─ Jules clique "Créer facture"
├─ Rentre nom, email, adresse client (nouveau)
├─ Clique "Créer facture"
│  └─ Système détecte: pas d'urssaf_id
│  └─ Auto-appel API URSSAF POST /particuliers
│  └─ Récupère urssaf_id, sauvegarde Sheets onglet Clients
│  └─ PDF généré, statut BROUILLON
├─ Clique "Soumettre URSSAF"
│  └─ Normale submission flow
└─ Succès

[Différence vs happy path:]
├─ +30 sec pour saisie données client
├─ +1 appel API (auto-inscription URSSAF)
└─ Puis identique
```

---

### 5.3 Parcours Alternatif 2: Client Oublie Validation 48h

```
[Jour J, T+36h]
├─ Polling détecte EN_ATTENTE depuis > 36h
├─ Email rappel à Jules
└─ Jules lit email

[Jour J, T+40h]
├─ Jules appelle client: "T'as reçu un email URSSAF pour ma facture ?"
├─ Client répond: "Oui mais j'ai pas eu le temps"
├─ Jules: "Va sur le lien, faut valider sous 8h"
└─ Client valide

[Jour J+1, matin]
├─ Polling détecte VALIDE → PAYE
├─ Virement en cours
└─ Cf. happy path

[Différence:]
├─ +1 action Jules (appel client)
├─ Délai +12h potentiel si Jules n'intervient pas
└─ Risque expiration → re-soumission manuelle (rare)
```

---

### 5.4 Parcours Alternatif 3: Erreur Soumission URSSAF

```
[Jour J, après création facture]
├─ Jules clique "Soumettre URSSAF"
├─ API respond: 400 Bad Request {error: "Email format invalide"}
├─ UI affiche: "Erreur : Email client invalide. Corrigez et re-tentez."
└─ Statut Sheets: BROUILLON (inchangé)

[Jour J, +5 min]
├─ Jules va sur onglet Clients, corrige email
├─ Revient à facture, clique "Soumettre" à nouveau
├─ API accepte → statut CREE
└─ Succès (délai +5 min vs nominal)

[Différence:]
├─ +1 action Jules (correction données)
├─ Délai +5 min
└─ Pas grave (email valide check côté API)
```

---

### 5.5 Parcours Alternatif 4: Rapprochement Ambigü

```
[Jour J+2, rapprochement auto]
├─ Facture: 30€, "Cours math"
├─ Transaction Swan: 30€, "VIRURT FRANCE X", date J+1
├─ Score confiance: montant exact(50) + date OK(30) + libellé pas URSSAF(-20) = 60
├─ Status onglet Lettrage: "A VERIFIER"
├─ Surligné orange dans UI
└─ Jules voit couleur orange

[Jour J+2, vendredi soir]
├─ Jules consulte dashboard, voit onglet "Reconciliation"
├─ Clique sur ligne orange: "Transaction X, score 60"
├─ Lit: "libellé ne contient pas URSSAF, manuellement verifier"
├─ Click radio "C'est bon, je reconnais" (ou "C'est pas ça")
├─ Manuellement lettrage validé
├─ Status facture: RAPPROCHE (manuel)
└─ Comptabilité OK

[Différence:]
├─ +1 action Jules (validation manuelle)
├─ Délai +30 sec
├─ Sécurité: humain valide cas ambigu
└─ Acceptable 5-10% des cas
```

---

### 5.6 Parcours Alternatif 5: Rejet Client

```
[Jour J+1, polling]
├─ Status URSSAF: REJETE
├─ Sheets mis à jour: REJETE
├─ Email notification à Jules (future feature)
└─ Facture visible en rouge dashboard

[Jour J+1, +2h]
├─ Jules voit rouge sur dashboard
├─ Clique facture, lit: "Rejet client - Raison: [raison URSSAF]"
├─ Appelle client pour rectifier
├─ Client me dit: "Ah je me suis trompé d'adresse"
└─ Jules: "OK, je re-génère"

[Jour J+1, +1h après appel]
├─ Jules clique "Re-soumettre" (crée nouvelle facture version 2)
├─ Facture V1: REJETE → ANNULE (flag manuel)
├─ Facture V2: BROUILLON → ... (redémarre happy path)
└─ Total délai +24-48h vs nominal

[Différence:]
├─ +1-2 actions Jules (appel + re-submission)
├─ Délai +24-48h
├─ Client fault (erreur saisie)
└─ Gérable, rare
```

---

### 5.7 Parcours CLI Avancé

```
[Dimanche, Jules batch ses cours de la semaine]
├─ Crée JSON file: factures.json
│  [
│    {client_id: "C1", heures: 1, tarif: 30, dates: "2026-03-15"},
│    {client_id: "C2", heures: 1.5, tarif: 30, dates: "2026-03-16"},
│    ...
│  ]
├─ Terminal: sap submit --json factures.json
├─ Output:
│  ✓ Facture C1 créée, soumise, ID: URD-{uuid}
│  ✓ Facture C2 créée, soumise, ID: URD-{uuid}
│  ✓ Total: 3 factures, 90€, soumis
└─ Sheets auto-updated

[Lundi, quickcheck]
├─ Terminal: sap sync
├─ Output:
│  - Facture C1: EN_ATTENTE (soumis hier, attends validation)
│  - Facture C2: VALIDE (client a validé hier soir)
│  - Facture C3: PAYE (virement détecté)
└─ Jules: "Parfait, on est à jour"

[Différence:]
├─ CLI mode: power user, batch operations
├─ +1 min setup, -5 min UI clics pour 10 factures
└─ Nice-to-have, phase 2
```

---

## 6. Synthèse & Matrice de Complexité

### User Stories par Priorité & Effort

| US ID | Titre | Priorité | Effort | Module | Dépendance |
|-------|-------|----------|--------|--------|-----------|
| US-2.1 | Créer facture | P0 (MVPx) | 5 | Core | Sheets |
| US-2.2 | Générer PDF | P0 (MVP) | 5 | Core | Drive |
| US-2.3 | Soumettre URSSAF | P0 (MVP) | 5 | Core | URSSAF API |
| US-2.4 | Auto-inscrire client | P0 (MVP) | 4 | Core | URSSAF API |
| US-3.2 | Polling statut 4h | P1 (MVP) | 4 | Auto | URSSAF API |
| US-3.4 | Reminder T+36h | P2 (Phase 2) | 5 | Notify | Polling |
| US-4.1 | Dashboard factures | P0 (MVP) | 5 | UI | Sheets |
| US-4.2 | Rapprochement auto | P2 (Phase 2) | 5 | Accounting | Swan API + Sheets |
| US-4.3 | Export CSV | P3 (Nice) | 3 | Export | Sheets |
| US-1.1 | Planning clients | P3 (Nice) | 3 | UI | Sheets |
| US-1.2 | Confirmer RDV | P3 (Nice) | 4 | Notify | Email/SMS |
| US-5.1 | CLI submit | P2 (Phase 2) | 3 | CLI | Core |
| US-5.2 | CLI sync | P2 (Phase 2) | 4 | CLI | Core |
| US-5.3 | CLI reconcile | P3 (Phase 3) | 4 | CLI | Core |

### Groupement par Sprint

**Sprint 1 (MVP Core):**
- US-2.1, US-2.2, US-2.3, US-2.4 (Création & soumission)
- US-3.2 (Polling automatique)
- US-4.1 (Dashboard)
- Effort estimé: 27 points

**Sprint 2 (Phase 2 — Comfort & Accounting):**
- US-3.4 (Reminder)
- US-4.2 (Rapprochement)
- US-5.1, US-5.2 (CLI)
- US-4.3 (Export CSV)
- Effort estimé: 19 points

**Sprint 3+ (Phase 3 — Advanced):**
- US-1.1, US-1.2 (Planning & RDV)
- US-5.3 (CLI reconcile)
- Mobile, notifications push, etc.

---

## 7. Assumptions & Constraints

### Assumptions Validées
1. Jules a un compte Swan/Indy actif (pas de création compte bancaire dans MVP)
2. URSSAF API disponible + documentation OAuth2 OK
3. Google Sheets API v4 accessible (service account credentials)
4. Clients (élèves) ont email valide (requis URSSAF)
5. Cycle de paiement URSSAF nominale: Client valide J+0-1, paiement J+1-2

### Constraints Système
1. **Mono-utilisateur MVP:** Seul Jules utilise le système (pas multi-user yet)
2. **Google Sheets comme DB:** Volontaire, accepté design (fallback JSON local)
3. **Polling 4h fixed:** Pas de webhooks URSSAF (future)
4. **PDF via weasyprint:** Pas de signature électronique (future)
5. **SMS contingent:** Confirmation RDV via email principalement

### Constraints Légales
1. **GDPR:** Données clients (nom, email, adresse) stockées dans Sheets (accepté, conforme)
2. **URSSAF Compliance:** Format demande-paiement doit match spec officielle
3. **Micro BNC:** Abattement 34%, taux charges 25.8% fixe (codé en dur phase 1)

---

## 8. Conclusion

Le **parcours utilisateur quotidien** de Jules est un workflow **critique et répétitif** optimisé pour la **vélocité** (création facture en 3-5 min) et l'**automatisation** (polling, rappels, rapprochement). Les **points de friction majeurs** (inscription client, expiration 48h, visibilité paiement) sont couverts par des **user stories MVP bien définis** (US-2.1 à US-4.2).

Le système cible une réduction de **charge administrative de 80%** (vs. processus manuel) tout en maintenant la **traçabilité comptable** et la **conformité URSSAF**.

---

**Document Version:** 1.0
**Date:** Mars 2026
**Auteur:** Sarah (Analyseur Product)
**Validation:** En cours (remontée feedback Jules)
