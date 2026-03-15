# Flux de Facturation End-to-End — SAP-Facture

**Document Version**: 1.0
**Date**: 15 mars 2026
**Source**: SCHEMAS.html — Schéma 2 "Flux de Facturation End-to-End"
**Scope**: MVP Phase 1 — Gestion complète de la facturation clients particuliers via API URSSAF

---

## 1. Vue d'ensemble du flux

Le flux de facturation end-to-end représente le cycle de vie complet d'une facture, de sa création jusqu'à la confirmation de paiement et le rapprochement bancaire.

**Durée totale estimée**: 4 à 7 jours
- T+0 : Création et soumission facture
- T+0 à T+48h : Validation client
- T+48h à T+5j : Traitement paiement URSSAF
- T+5j à T+7j : Virement et rapprochement bancaire

---

## 2. Étapes du flux détaillées

### Étape 1 : Création de la facture (T+0)

**État initial**: BROUILLON

#### Description
Jules crée une nouvelle facture via:
- Interface web (formulaire)
- CLI (ligne de commande) : `sap submit`

#### Données saisies
- **Client existant ou nouveau**:
  - Nom, prénom
  - Email
  - Adresse (rue, code postal, ville)
  - Téléphone (optionnel)
- **Détails facture**:
  - Type d'unité: heures, forfait, session
  - Nature du code (code activité URSSAF)
  - Quantité (ex: 2h)
  - Montant unitaire (ex: 30 €/h)
  - Montant total (calculé = quantité × montant unitaire)
  - Dates : début et fin d'exécution de service
  - Description (notes libres)

#### Règles métier
- **Validation d'entrée obligatoire**:
  - Tous les champs obligatoires doivent être remplis
  - Email doit être valide (format @ et domaine)
  - Montant total > 0
  - Date fin ≥ date début
  - Quantité > 0

- **Vérification client**:
  - Chercher si client existe déjà dans la base via email
  - Si nouveau client: enregistrement en base (sans appel URSSAF à ce stade)
  - Si client existant: récupérer les données pré-remplies

#### Actions système
- Génération du PDF facture avec:
  - Logo Jules (depuis Google Drive)
  - Données client
  - Détails facture (dates, heures, montants)
  - Numéro de facture unique (facture_id généré)
- Enregistrement en base Google Sheets (onglet "Factures"):
  - État: BROUILLON
  - PDF Drive ID (référence fichier Google Drive)
  - Timestamp création

#### Validation de payload
Le système valide que le payload contient:
- Client data structure cohérente
- Montants numériques et positifs
- Dates valides (format ISO 8601)
- Pas de caractères problématiques (SQL injection, XSS)

#### Délais
- Création immédiate (< 5s)
- PDF généré < 10s
- Enregistrement base < 2s

---

### Étape 2 : Vérification inscription client URSSAF (T+0)

**États possibles**: BROUILLON → CREE (succès) ou ERREUR (échec inscription)

#### Description
Avant soumission à URSSAF, le système vérifie/enregistre le client.

#### Cas 1 : Client déjà inscrit URSSAF
- Vérifier si `urssaf_id` existe dans la base
- Si oui : passer directement à étape 3 (soumission)

#### Cas 2 : Client nouveau (pas d'urssaf_id)
- **Appel API URSSAF**: `POST /particuliers`
- **Données transmises**:
  - Identité complète (nom, prénom)
  - Email
  - Adresse (rue, code postal, ville)
  - Téléphone (optionnel)
- **Réponse URSSAF**:
  - `id_technique` (identifiant unique URSSAF pour ce particulier)
  - Confirmation d'inscription

#### Règles métier
- **Client doit être reconnu par les impôts**:
  - Si client n'a jamais fait de déclaration fiscale: **ERREUR** (blocage)
  - Message d'erreur: "Ce client doit avoir effectué au moins une déclaration d'impôts sur le revenu"
  - Action corrective: Jules contacte le client pour déclaration préalable

- **Validation côté URSSAF**:
  - Email unique par client (pas de doublon)
  - Identité bien formée (pas de caractères spéciaux invalides)
  - Adresse complète et valide (au moins rue + code postal + ville)

#### Gestion des erreurs
- **Erreur API URSSAF** (timeout, indisponibilité):
  - Retry automatique 3 fois (délai 5s entre tentatives)
  - Si échec persistant: statut = ERREUR, message "URSSAF indisponible, réessayer"
  - Action manuelle: Jules clique "Réessayer" ou "Re-soumettre"

- **Client non reconnu**:
  - URSSAF retourne 404 ou code 40X
  - Statut = ERREUR
  - Message: "Client non trouvé aux impôts — demander déclaration"
  - Facture reste en BROUILLON, rééditable

#### Transitions d'état
- Si inscription réussie: ajouter `urssaf_id` en base, continuer à Étape 3
- Si inscription échoue: statut = ERREUR, arrêt du flux

---

### Étape 3 : Génération du PDF facture (T+0)

**États**: BROUILLON → BROUILLON (avant soumission URSSAF)

#### Description
Génération du fichier PDF officiel de facturation avec tous les détails.

#### Contenu du PDF
- **En-tête Jules**:
  - Nom complet: Jules Willard
  - SIREN: 991552019
  - Logo personnel
  - Adresse professionnelle

- **Bloc client**:
  - Nom, prénom
  - Email
  - Adresse complète

- **Détails facture**:
  - Numéro de facture unique (facture_id)
  - Date émission (T+0)
  - Dates d'exécution (début — fin)
  - Description du service
  - Tarification:
    - Quantité (heures, sessions, etc.)
    - Tarif unitaire
    - Montant TTC (= montant brut, pas de TVA car micro-entrepreneur)

- **Mentions légales**:
  - "Micro-entrepreneur, franchise de TVA"
  - Mode de paiement URSSAF
  - Délai de paiement: 48h après validation client

#### Technologie
- Outil: WeasyPrint
- Format: PDF
- Stockage: Google Drive (dossier "PDFs SAP-Facture")
- Référence: `pdf_drive_id` enregistré en base

#### Validation du PDF
- Fichier généré correctement (pas vide)
- Taille > 0 bytes
- Lisible (pas d'erreur WeasyPrint)
- Storable sur Google Drive

#### Délais
- Génération < 10 secondes
- Upload Google Drive < 5 secondes
- Récupération Drive ID < 2 secondes

---

### Étape 4 : Soumission à URSSAF (T+0)

**États**: BROUILLON → SOUMIS → CREE (succès) ou ERREUR

#### Description
Transmission de la demande de paiement à l'API URSSAF.

#### Appel API
- **Endpoint**: `POST /demandes-paiement` (API URSSAF)
- **Headers**: Authorization Bearer {access_token}
- **Payload**:
  ```json
  {
    "id_client": "{urssaf_id}",
    "montant": 100.00,
    "nature": "{nature_code}",
    "date_debut": "2026-03-15",
    "date_fin": "2026-03-15",
    "description": "Cours particuliers",
    "email_client": "eleve@example.com"
  }
  ```

#### Validation du payload
**Règles strictes avant envoi**:
- `id_client` non vide et format valide
- `montant` > 0 et ≤ 10000 € (seuil URSSAF micro)
- `nature` dans liste des codes acceptés URSSAF
- `date_debut` et `date_fin` format ISO 8601 valide
- `date_fin` ≥ `date_debut`
- `email_client` format valide
- Aucun caractère spécial problématique

#### Gestion des erreurs de payload
- **Payload invalide**:
  - URSSAF retourne 400 Bad Request + message d'erreur spécifique
  - Statut facture = ERREUR
  - Message utilisateur: "Erreur de soumission — [détail erreur URSSAF]"
  - Jules peut modifier la facture (retour à BROUILLON) et re-soumettre
  - Pas de limite de tentatives (tant que facture en BROUILLON/ERREUR)

#### Gestion des erreurs réseau
- **Timeout** (> 30s): Retry automatique 2 fois (délai 10s)
- **5XX** (erreur serveur URSSAF): Retry automatique 3 fois (délai 5s + délai croissant)
- **Indisponibilité persistante**: Statut ERREUR, message "API URSSAF indisponible"

#### Cas de succès
- **Réponse URSSAF** (`201 Created`):
  ```json
  {
    "id_demande": "DEMANDE_ABC123",
    "statut": "CREE",
    "date_creation": "2026-03-15T14:30:00Z"
  }
  ```
- Enregistrement en base:
  - `urssaf_demande_id` = DEMANDE_ABC123
  - État facture = CREE
  - Timestamp soumission = T+0

#### Transition
- Succès: Étape 5 (notification client)
- Erreur: Statut ERREUR, retour à Étape 3 (correction + re-soumission)

---

### Étape 5 : Notification et validation client URSSAF (T+0 à T+48h)

**États**: CREE → EN_ATTENTE → VALIDE (succès) / EXPIRE / REJETE

#### Description
URSSAF envoie un email au client pour validation dans un délai de 48h.

#### Communication client
- **Email URSSAF** (automatique):
  - À: client_email
  - Objet: "Validation facture cours particuliers"
  - Contenu: Lien de validation + détails facture
  - Lien valable 48h (après: expiration)

#### État du système
- État facture = EN_ATTENTE
- Timer 48h activé
- Timestamp attente = T+0
- Deadline validation = T+48h

#### Actions client possibles

**Cas 1 : Client valide (avant T+48h)**
- Client clique lien URSSAF
- Confirme identité et montant
- URSSAF valide la demande
- État facture devient VALIDE
- Workflow continue → Étape 6

**Cas 2 : Client rejette (avant T+48h)**
- Client refuse la facture sur portail URSSAF
- État facture = REJETE
- Jules reçoit notification d'échec
- Possibilité re-soumettre après correction

**Cas 3 : Timeout sans validation (T > 48h)**
- Aucune action client
- État facture = EXPIRE
- Jules doit relancer manuellement
- Retour à BROUILLON pour re-soumission

#### Rappel automatique (T+36h)

**Détection**: Tous les 4 heures, job cron vérifie factures EN_ATTENTE
- Si `(now - timestamp_attente) > 36h` ET statut = EN_ATTENTE:
  - Envoyer email rappel Jules: "Facture [#XXX] client [nom] en attente depuis 36h"
  - CC: email client (rappel)
  - CTA: "Relancer client" / "Annuler facture"

#### Règles métier
- **Délai strict 48h**:
  - Non extensible
  - Décompte commence à T+0 (timestamp création URSSAF)
- **Rappel opportuniste** (T+36h):
  - Notification, pas automatisation
  - Jules reste décisionnaire
- **Pas de re-notification auto**:
  - Rappel envoyé une seule fois (T+36h)
  - Pas de spam (max 1 email rappel par facture)

---

### Étape 6 : Polling statut URSSAF (T+0 à T+7j) — Processus continu

**États**: SOUMIS / CREE / EN_ATTENTE / VALIDE → PAYE

#### Description
Job cron récurrent qui interroge URSSAF pour mettre à jour le statut des factures.

#### Planification
- **Fréquence**: Toutes les 4 heures
- **Heures**: 00h, 04h, 08h, 12h, 16h, 20h (UTC)
- **Timeout par requête**: 30 secondes
- **Retry**: 2 tentatives en cas d'erreur

#### Logique du job
```
Pour chaque facture où statut IN (SOUMIS, CREE, EN_ATTENTE, VALIDE):
  1. Appeler GET /demandes-paiement/{urssaf_demande_id}
  2. Récupérer statut URSSAF actuel
  3. Comparer avec statut en base
  4. Si changement détecté:
     a. Mettre à jour base (Google Sheets)
     b. Déclencher actions annexes (voir ci-dessous)
     c. Enregistrer timestamp du changement
```

#### Appel API
- **Endpoint**: `GET /demandes-paiement/{id_demande}`
- **Réponse**:
  ```json
  {
    "id_demande": "DEMANDE_ABC123",
    "statut": "VALIDE" ou "PAYE" ou "REJETE" ou "EXPIRE",
    "date_validation": "2026-03-16T10:00:00Z",
    "date_paiement": "2026-03-20T15:30:00Z"
  }
  ```

#### Transitions détectées

| Ancien statut | Nouveau statut | Action |
|---|---|---|
| SOUMIS | CREE | Enregistrer changement, attendre validation |
| CREE | EN_ATTENTE | Email client envoyé (via URSSAF) — passif |
| EN_ATTENTE | VALIDE | Jules notifié, paiement en cours |
| VALIDE | PAYE | Jules notifié, attendre virement, Étape 7 |
| EN_ATTENTE | EXPIRE | Jules notifié, action manuelle requise |
| EN_ATTENTE / VALIDE | REJETE | Jules notifié, re-soumission possible |

#### Enregistrement en base
- Mettre à jour colonne "statut" dans onglet Factures
- Mettre à jour colonne "date_suivi" avec timestamp du polling
- Mettre à jour colonne "date_validation" ou "date_paiement" si fourni par URSSAF

#### Notifications Jules
- **Email notification** envoyé lors de changements majeurs (VALIDE, PAYE, EXPIRE, REJETE)
- Contenu: Numéro facture, client, montant, nouveau statut, action si requise

#### Gestion des erreurs
- **API indisponible**: Logging, retry lors du prochain cycle (4h plus tard)
- **Facture non trouvée (404)**: Logger warning, garder statut en base (peut être vieille facture)
- **Erreur 5XX**: Logging, retry lors du prochain cycle

#### Performances
- Parcours limité aux factures "actives" (statut ≠ PAYE, RAPPROCHE, ANNULE)
- Batch queries par 50 demandes max (limite API)
- Durée totale job: < 5 minutes pour 100 factures

---

### Étape 7 : Réception du virement URSSAF (T+48h à T+5j)

**États**: VALIDE → PAYE

#### Description
Une fois facture validée par le client, URSSAF traite le paiement et effectue un virement sur le compte Swan de Jules.

#### Processus URSSAF
- Virement 100% du montant facture
- Destination: Compte Swan de Jules (IBAN configuré)
- Délai standard: 3 à 5 jours ouvrés après validation client

#### Enregistrement en base
État facture = PAYE (détecté lors du polling — Étape 6)

#### Données virement
- Montant: 100% du montant facture
- Libellé: "URSSAF [montant] client [nom]" (format Swan)
- Date valeur: J+1 à J+3 après émission
- Identifiant: Transaction ID Swan (récupéré lors de sync Swan)

#### Cas spécial : Partage avec client
- **Important**: Le montant reçu par Jules est 100% du montant facture
- Le client particulier paie ses 50% (ou part variable) **directement à URSSAF**, pas à Jules
- Jules ne gère que la facturation, pas la collecte auprès du client
- Ceci est un détail organisationnel URSSAF (partage de cotisations)

#### Validation par Jules
- Vérifier que virement reçu sur compte Swan
- Montant = montant facture (via rapprochement — Étape 8)
- Sinon: enquête manuelle ou relance URSSAF

---

### Étape 8 : Rapprochement bancaire (T+5j à T+7j)

**États**: PAYE → RAPPROCHE

#### Description
Matching automatique entre factures payées (onglet Factures) et virements reçus (onglet Transactions Swan).

#### Flux général
1. **Récupération transactions Swan**:
   - Appel GraphQL Swan toutes les 6 heures
   - Date range: derniers 7 jours
   - Filtrer: montant > 0, libellé contient "URSSAF"
   - Enregistrement en base (onglet Transactions)

2. **Algorithme de matching** (onglet Lettrage — formules Google Sheets):
   - Pour chaque facture avec statut PAYE
   - Chercher transaction Swan:
     - Montant = montant facture (match exact, tolérance 0€)
     - Date: date_paiement URSSAF +/- 5 jours calendaires
     - Libellé: contient "URSSAF"

3. **Scoring de confiance**:
   - **+50 points**: Montant exact
   - **+30 points**: Date virement < 3 jours après validation
   - **+20 points**: Libellé contient "URSSAF" + montant cohérent
   - **Seuil auto-match**: Score ≥ 80 → Lettre automatique
   - **Seuil vérification**: Score 60-79 → Surligner orange, Jules valide
   - **Pas de match**: Score < 60 → Surligner rouge, attendre manuellement

#### Lettrage automatique (score ≥ 80)
- Écrire `facture_id` dans colonne "facture_id" de la transaction
- Écrire `transaction_id` dans colonne "transaction_id" de la facture
- État facture = RAPPROCHE
- Pas de notification Jules (normal)

#### À vérifier (score 60-79)
- Surligner transaction en orange
- Envoyer email Jules: "Lettrage manuel requis — facture [#XXX] montant [€XXX]"
- Jules clique lien → formulaire confirmation
- Après confirmation: lettre manuellement, état = RAPPROCHE

#### Pas de match
- Surligner transaction en rouge
- Email Jules: "Pas de correspondance — transaction [€XXX] [date]"
- Attendre livraison du virement URSSAF (délai peut s'étirer)
- Option Jules: Créer facture manuelle si besoin ou attendre

#### Mise à jour onglet Balances
Une fois lettrage complété:
- Mettre à jour colonne "nb_factures_lettrees"
- Mettre à jour colonne "solde_total"
- Mettre à jour colonne "nb_en_attente"
- Recalculer CA mensuel (somme factures RAPPROCHE)

#### Performances
- Sync Swan: < 2 minutes pour 100 transactions
- Matching formules: Calcul < 30 secondes (Google Sheets)
- Notifications: < 10 secondes

---

### Étape 9 : Fin du cycle (T+7j)

**État final**: RAPPROCHE

#### Description
Facture complètement traitée, paiement confirmé et lettré.

#### État final de la facture
- Statut: RAPPROCHE
- Tous les champs remplis (création, soumission, validation, paiement, lettrage)
- PDF généré et conservé en Drive
- Transaction bancaire identifiée

#### Archivage
- Facture reste en base (jamais supprimée)
- Historique préservé (dates, statuts, transactions)
- Export CSV possible pour comptabilité

#### Dashboard Jules
- Facture apparaît comme "Complète" en vert
- Visible dans historique et rapports
- Incluse dans totaux mensuels/trimestriels (CA, cotisations, IR)

---

## 3. Gestion des erreurs et flux de rattrapage

### 3.1 Erreurs d'inscription client URSSAF

#### Erreur 1 : Client non reconnu aux impôts
**Trigger**: `POST /particuliers` retourne 404 ou code 40X

**Symptômes**:
- État facture: ERREUR
- Message: "Client non trouvé aux impôts — demander déclaration"

**Récupération**:
1. Jules contacte client (email/SMS)
2. Client effectue déclaration d'impôts (si jamais faite)
3. Attendre 1-2 jours (délai de sync impôts)
4. Jules clique "Réessayer inscription"
5. Appel `POST /particuliers` à nouveau
6. Si succès: continuer flux
7. Si échec persistent: escalade manuelle URSSAF

**SLA**: Résolution 2-3 jours

#### Erreur 2 : Email invalide ou doublon
**Trigger**: `POST /particuliers` retourne 400 (email mal formé ou déjà utilisé)

**Symptômes**:
- État facture: ERREUR
- Message: "Email invalide ou déjà utilisé — vérifier avec URSSAF"

**Récupération**:
1. Jules corriges données client (email valide)
2. Clique "Modifier facture"
3. État revient à BROUILLON
4. Corrige email en base
5. Clique "Soumettre" à nouveau
6. Validation depuis 0

**SLA**: Résolution immédiate (< 5 min)

#### Erreur 3 : Adresse incomplète
**Trigger**: `POST /particuliers` retourne 400 (rue OU code postal OU ville manquant)

**Symptômes**:
- État facture: ERREUR
- Message: "Adresse incomplète — rue, code postal et ville requis"

**Récupération**:
1. Jules modifie facture (retour BROUILLON)
2. Complète adresse client
3. Clique "Soumettre"
4. Retry inscription

**SLA**: Résolution < 2h (dépend de Jules)

---

### 3.2 Erreurs de soumission à URSSAF

#### Erreur 1 : Payload invalide (montant, dates, nature)
**Trigger**: `POST /demandes-paiement` retourne 400

**Symptômes**:
- État facture: ERREUR
- Message: "Erreur soumission URSSAF — [détail erreur API]"

**Récupération**:
1. Jules clique "Modifier"
2. Facture revient à BROUILLON
3. Corrige champ problématique (montant, dates, code nature)
4. Valide changes (check montant > 0, date fin ≥ début, etc.)
5. Clique "Soumettre"
6. Retry API

**SLA**: Résolution < 5 min

#### Erreur 2 : API URSSAF indisponible (timeout, 5XX)
**Trigger**: `POST /demandes-paiement` timeout ou erreur serveur URSSAF

**Symptômes**:
- État facture: ERREUR
- Message: "API URSSAF indisponible — réessayer dans quelques minutes"

**Récupération (automatique)**:
1. Système retry automatiquement 3 fois (délai 5s, 10s, 20s)
2. Si succès sur retry: état passe à CREE, continue
3. Si échec persistant: statut ERREUR, attendre

**Récupération (manuelle)**:
1. Jules attend quelques minutes
2. Clique "Réessayer"
3. Nouvelle tentative API
4. Si succès: état CREE

**SLA**: Résolution 30-60 min (dépend de downtime URSSAF)

---

### 3.3 Erreurs de validation client (délai 48h)

#### Erreur 1 : Client ne valide pas à temps (T > 48h)
**Trigger**: Timer 48h expiré, statut reste EN_ATTENTE

**Symptômes**:
- État facture: EXPIRE
- Notification Jules reçue (email)
- Facture devrait être re-lancée

**Récupération**:
1. Jules contacte client (appel/SMS)
2. Client re-valide sur portail URSSAF (lien toujours valide pendant expiration)
3. Système détecte changement lors prochain polling (4h max)
4. État facture: VALIDE → continue vers PAYE
5. OU Jules clique "Re-soumettre" (créer nouvelle demande)

**Option "Re-soumettre"**:
1. Facture revient à BROUILLON
2. Jules clique "Soumettre"
3. Nouvelle demande API URSSAF
4. Nouveau délai 48h commence
5. Ancien URL validation expire

**SLA**: Résolution 24h (après contact client)

#### Erreur 2 : Client rejette la facture
**Trigger**: Client clique "Rejeter" sur portail URSSAF

**Symptômes**:
- État facture: REJETE
- Notification Jules: "Facture [#XXX] refusée par client"

**Récupération**:
1. Jules contacte client pour raison du refus
2. Possible correction: montant erroné, période service, etc.
3. Modifie facture (BROUILLON)
4. Corrige données
5. Clique "Soumettre"
6. Nouvelle demande URSSAF
7. Client valide à nouveau

**SLA**: Résolution 1-2 jours (dépend client feedback)

---

### 3.4 Erreurs de rapprochement bancaire

#### Erreur 1 : Virement non reçu (T+7j sans virement)
**Trigger**: Facture PAYE mais aucune transaction Swan non-lettree

**Symptômes**:
- Lettrage impossible
- Email Jules: "Facture [#XXX] [€XXX] — pas de virement détecté"
- Surlignage rouge dans Lettrage

**Diagnostic**:
1. Vérifier date paiement URSSAF vs aujourd'hui
2. Vérifier compte Swan activé
3. Vérifier IBAN correct en paramètres

**Récupération**:
1. Jules attend max 2 jours supplémentaires (délai URSSAF J+5 nominal)
2. Si toujours absent:
   - Contacter URSSAF par email/phone
   - Requête numéro demande paiement (urssaf_demande_id)
   - Demander statut virement
3. Pendant ce temps: facture reste PAYE (pas encore RAPPROCHE)

**SLA**: Résolution 5-7 jours (dépend URSSAF)

#### Erreur 2 : Montant virement différent
**Trigger**: Transaction Swan montant ≠ facture montant

**Symptômes**:
- Lettrage impossible (montant exact requis)
- Email Jules: "Discordance montants — [€XXX] facture vs [€XXX] virement"

**Diagnostic**:
1. Verifier si facture correcte (montant saisi bien validé)
2. Vérifier libellé transaction (identifiant client?)
3. Vérifier si URSSAF a appliqué déduction (cotisations client?)

**Récupération**:
1. Jules compare montants
2. Si erreur saisie facture:
   - Annuler facture (note: "Montant erroné, re-soumtre")
   - Créer nouvelle facture avec montant correct
3. Si URSSAF a déduit:
   - Contacter URSSAF pour comprendre
   - Enregistrer si cotisation client déduite
   - Lettrer manuellement (créer note explicative)
4. Si divergence > 2 €:
   - Escalade manuelle à comptable

**SLA**: Résolution 3-5 jours

#### Erreur 3 : Transaction non identifiée (score < 60)
**Trigger**: Algorithme scoring trouve transaction mais score trop bas

**Symptômes**:
- Surlignage orange dans Lettrage
- Email Jules: "Lettrage à vérifier — [€XXX] [date]"

**Vérification Jules**:
1. Ouvre onglet Lettrage
2. Examine transaction surlignée (date, montant, libellé)
3. Compare manuellement avec facture correspondante
4. Si conforme: clique "Valider" → lettre automatique
5. Si non-conforme: rejette (démarquer)

**SLA**: Résolution immédiate (< 5 min)

---

## 4. Acteurs impliqués à chaque étape

| Étape | Acteur principal | Acteurs secondaires | Actions |
|---|---|---|---|
| 1. Création | Jules | SAP-Facture (système) | Remplir, générer, enregistrer |
| 2. Vérification client URSSAF | SAP-Facture | Jules (sur erreur), URSSAF API | Appel inscription, gestion erreur |
| 3. PDF | SAP-Facture | Google Drive (stockage) | Génération, upload |
| 4. Soumission | SAP-Facture | Jules (correction si erreur) | Appel API, validation |
| 5. Notification client | URSSAF | Client particulier, Jules (notification) | Email validation |
| 6. Polling statut | SAP-Facture (système cron) | URSSAF API, Jules (notification) | Check statut, notification |
| 7. Virement | URSSAF, Swan | Jules (détection) | Traitement, paiement |
| 8. Rapprochement | SAP-Facture (système), Jules | Swan API, Google Sheets | Matching, validation |
| 9. Fin cycle | Archivage | Jules (si besoin export) | Clôture, historique |

---

## 5. Données échangées entre chaque étape

### 5.1 Étape 1 → Étape 2 : Création vers Inscription client

**Direction**: Jules (saisie) → SAP-Facture → URSSAF API

**Données**:
```json
{
  "client": {
    "nom": "Dupont",
    "prenom": "Amélie",
    "email": "amelie@email.com",
    "telephone": "+33612345678",
    "adresse": "123 rue de la Paix",
    "code_postal": "75001",
    "ville": "Paris"
  },
  "facture": {
    "type_unite": "heures",
    "nature_code": "4903A",
    "quantite": 2.0,
    "montant_unitaire": 35.00,
    "montant_total": 70.00,
    "date_debut": "2026-03-14",
    "date_fin": "2026-03-15",
    "description": "Cours maths 3e — prépa brevet"
  }
}
```

**Réponse URSSAF**:
```json
{
  "urssaf_id": "PARTICULIER_F34K92",
  "statut": "inscrit",
  "date_inscription": "2026-03-15T14:00:00Z"
}
```

### 5.2 Étape 2 → Étape 3 : Inscription vers PDF

**Direction**: Données client (confirmées URSSAF) → PDF Generator

**Données**:
```json
{
  "facture_id": "FACTURE_2026_001",
  "urssaf_id": "PARTICULIER_F34K92",
  "client_data": { /* idem 5.1 */ },
  "facture_details": { /* idem 5.1 */ },
  "Jules": {
    "nom": "Willard",
    "siren": "991552019",
    "logo_url": "drive://file_id_logo"
  }
}
```

**Sortie**: PDF URL (Google Drive)

### 5.3 Étape 3 → Étape 4 : PDF vers Soumission URSSAF

**Direction**: Facture complète (avec PDF) → API URSSAF

**Données transmises**:
```json
{
  "id_client": "PARTICULIER_F34K92",
  "montant": 70.00,
  "nature": "4903A",
  "date_debut": "2026-03-14",
  "date_fin": "2026-03-15",
  "email_client": "amelie@email.com",
  "pdf_url": "drive://pdf_facture_2026_001",
  "description": "Cours maths 3e — prépa brevet"
}
```

**Réponse URSSAF**:
```json
{
  "id_demande": "DEMANDE_URSSAF_XYZ789",
  "statut": "CREE",
  "date_creation": "2026-03-15T14:30:00Z"
}
```

### 5.4 Étape 4 → Étape 5 : Soumission vers Notification client

**Direction**: URSSAF (interne) → Email client

**Email contenu**:
- Lien validation portail URSSAF
- Détails facture (montant, dates, service)
- Délai: 48h
- Lien valable jusqu'à T+48h

### 5.5 Étape 5 → Étape 6 : Validation vers Polling

**Direction**: URSSAF (base interne) → API polling

**Call polling**:
```
GET /demandes-paiement/DEMANDE_URSSAF_XYZ789
```

**Réponse**:
```json
{
  "id_demande": "DEMANDE_URSSAF_XYZ789",
  "statut": "VALIDE",
  "date_validation": "2026-03-16T09:00:00Z"
}
```

### 5.6 Étape 6 → Étape 7 : Polling vers Virement

**Direction**: Polling détecte statut PAYE → Swan reçoit virement

**Call polling** (T+3j):
```
GET /demandes-paiement/DEMANDE_URSSAF_XYZ789
```

**Réponse URSSAF**:
```json
{
  "statut": "PAYE",
  "montant": 70.00,
  "date_paiement": "2026-03-18T16:30:00Z"
}
```

**Virement Swan**:
- Montant: 70.00 EUR
- Libellé: "URSSAF 70.00 Dupont"
- Compte Jules (IBAN configuré)
- Date valeur: J+1 à J+2

### 5.7 Étape 7 → Étape 8 : Virement vers Rapprochement

**Direction**: Swan transactions → Google Sheets lettrage

**Sync Swan** (toutes les 6h):
```graphql
query {
  transactions(dateFrom: "2026-03-15", dateTo: "2026-03-22") {
    id
    amount
    label
    executionDate
    iban_from
  }
}
```

**Enregistrement Transactions**:
```json
{
  "transaction_id": "SWAN_TXN_ABC123",
  "montant": 70.00,
  "libelle": "URSSAF 70.00 Dupont",
  "date_valeur": "2026-03-19",
  "iban_from": "FR76****",
  "statut_lettrage": "A_TRAITER"
}
```

### 5.8 Étape 8 → Étape 9 : Rapprochement vers Archivage

**Direction**: Lettrage confirmé → État final facture

**Mise à jour base**:
```json
{
  "facture_id": "FACTURE_2026_001",
  "statut": "RAPPROCHE",
  "transaction_id": "SWAN_TXN_ABC123",
  "date_lettrage": "2026-03-20T14:30:00Z",
  "cycle_complet": true
}
```

---

## 6. SLA et délais attendus

### 6.1 SLA globaux

| Jalon | Délai cible | Délai max | Notes |
|---|---|---|---|
| **T+0: Création → Soumission** | < 30s | 2 min | User Jules, système auto |
| **T+0 à T+48h: Validation client** | 24-36h (moyen) | 48h (strict) | Client doit valider |
| **T+48h à T+72h: URSSAF traite paiement** | < 24h | 48h | Après validation |
| **T+72h à T+120h: Virement reçu** | 3-5j ouvré | 7j | Standard bancaire |
| **T+120h à T+7j: Rapprochement** | < 12h après réception | 24h | Automatique matching |
| **Total cycle** | **4-5 jours** | **7 jours** | Du début au fin |

### 6.2 SLA par étape

#### Étape 1 : Création (T+0)
- **Cible**: < 30 secondes (création + PDF + enregistrement)
- **Tolérance**: Jusqu'à 2 minutes si PDF volumineux
- **Notification**: Immediate (vert succès)

#### Étape 2 : Inscription client (T+0 à T+5 min)
- **Cible**: < 5 secondes (API appel + réponse)
- **Retry**: 3 tentatives auto (5s, 10s, 20s) si erreur
- **Escalade**: Après 3 échecs, manuel Jules

#### Étape 3 : PDF Génération (T+0)
- **Cible**: < 10 secondes
- **Upload Drive**: < 5 secondes
- **Acceptable**: Jusqu'à 30s avec retry

#### Étape 4 : Soumission URSSAF (T+0 à T+5 min)
- **Cible**: < 5 secondes (API call)
- **Retry**: 2 tentatives auto si network error
- **Erreur persistante**: Statut ERREUR, retry manuel

#### Étape 5 : Validation client (T+0 à T+48h)
- **SLA client**: 48h max (ferme)
- **Rappel**: Email T+36h (non-bloquant)
- **Expiration**: Strict à T+48h (pas d'extension)

#### Étape 6 : Polling statut (T+0 à T+5j)
- **Fréquence**: Toutes les 4 heures
- **Latence détection**: Jusqu'à 4h après changement réel URSSAF
- **Notification Jules**: < 5 min après polling détecte changement

#### Étape 7 : Virement (T+2j à T+5j après validation)
- **Cible**: T+3j (standard URSSAF)
- **Max**: T+5j ouvré (délai URSSAF garantie)
- **Inspection**: Jules peut vérifier compte Swan

#### Étape 8 : Rapprochement (T+5j à T+7j)
- **Détection auto**: Lettrage automatique < 1h après sync Swan
- **Notification Jules**: Si à vérifier (orange) < 10 min
- **Résolution manuelle**: Jules < 2h

#### Étape 9 : Archivage (T+7j)
- **Automatique**: Immédiat après lettrage
- **Historique**: Conservé à perpétuité (pas de suppression)

### 6.3 Timeouts critiques

| Événement | Timeout | Action |
|---|---|---|
| API URSSAF appel | 30s | Retry 3x puis erreur |
| Swan API graphql | 20s | Retry 2x puis attendre prochain cycle |
| Google Sheets API | 15s | Retry 2x puis logger |
| PDF génération | 20s | Retry 1x puis alerter Jules |
| Email envoi | 10s | Fire & forget (async) |

---

## 7. Cas d'erreur synthétisés et récupération

### Matrice risques et mitigations

| Risque | Probabilité | Détection | Mitigation |
|---|---|---|---|
| **Client non aux impôts** | Basse (10%) | Inscription URSSAF 404 | Jules demande déclaration, retry |
| **Email client invalide** | Basse (5%) | Inscription URSSAF 400 | Modification + re-soumission |
| **Montant erroné** | Basse (5%) | Validation saisie + soumission | Modification brouillon + re-soumettre |
| **Délai validation 48h dépasse** | Moyenne (30%) | Timer + rappel T+36h | Email rappel + re-soumission possible |
| **Client refuse facture** | Basse (10%) | Statut REJETE polling | Correction + re-soumettre |
| **URSSAF API down** | Basse (5%) | Timeout/5XX soumission | Retry auto, puis attendre puis retry manuel |
| **Virement non reçu T+7j** | Basse (3%) | Absence transaction Swan | Inspection + contacter URSSAF |
| **Montants discordants** | Très basse (1%) | Lettrage impossible (montant exact) | Escalade manuelle + inspection URSSAF |
| **Rapprochement score faible** | Moyenne (20%) | Lettrage orange | Validation manuelle Jules (< 5 min) |

### Parcours récupération standard

```
Erreur détectée
    ├─ Retryable (network, temporary)?
    │   ├─ Oui → Retry auto (2-3 fois)
    │   │   ├─ Succès → Continuer flux
    │   │   └─ Échec persistent → Notif Jules + Manuel
    │   └─ Non (validation, business logic) → Notif Jules
    │
    └─ Jules action requise?
        ├─ Oui → Email notif + décision Jules
        │   ├─ Corriger → Modification base/facture
        │   ├─ Réessayer → Re-soumission API
        │   └─ Escalade → Contact direct URSSAF/Swan
        └─ Non (automation) → Attendre prochain cycle polling
```

---

## 8. Contexte système et intégrations

### 8.1 Système support (SAP-Facture)
- **Backend**: FastAPI (Python) + SQLAlchemy
- **Frontend**: Jinja2 SSR + Tailwind CSS
- **Data**: Google Sheets (onglets Factures, Clients, Transactions, Lettrage, Balances)
- **Externe**: API URSSAF, Swan GraphQL, Google Drive, Google Sheets API

### 8.2 Autorité source
- **Vérité factures**: Onglet Factures (Google Sheets)
- **Vérité clients**: Onglet Clients (Google Sheets)
- **Vérité paiements**: URSSAF API (statuts) + Swan (transactions)
- **Vérité lettrage**: Formules onglet Lettrage (Google Sheets)

### 8.3 Responsabilités

| Composant | Responsabilité | Propriétaire |
|---|---|---|
| Création/saisie | Données client + facture fiables | Jules |
| Validation payload | Format + business rules | SAP-Facture (système) |
| Soumission URSSAF | Call API, gestion erreurs | SAP-Facture (système) |
| Validation client | Signature facture par client | URSSAF + Client |
| Traitement paiement | Effectuer virement | URSSAF |
| Réception virement | Débiter/créditer compte | Swan (banque) |
| Rapprochement | Matching montants/dates | SAP-Facture (formules Sheets) |
| Corrections manuelles | Interventions exceptionnelles | Jules |

---

## 9. Points critiques et recommandations

### 9.1 Points critiques du flux

1. **Validation client 48h** (Étape 5):
   - Non extensible → Risque oubli client
   - **Recommandation**: Rappel T+36h obligatoire + SMS optionnel
   - Impact: Majorité retards dûs à client oubli

2. **Matching rapprochement** (Étape 8):
   - Montant exact requis → Risque incompatibilité si URSSAF déduit
   - **Recommandation**: Scorer plus souple (tolérance ±2€) ou communication URSSAF
   - Impact: Possible lettrage incomplet si montants divergent

3. **Délai virement URSSAF** (Étape 7):
   - Nominalement 3-5j mais parfois J+7
   - **Recommandation**: Dashboard "En attente paiement" pour visibilité
   - Impact: Trésorerie incertaine

4. **Statut EXPIRE** (Étape 5):
   - URL validation devient inaccessible après T+48h
   - **Recommandation**: Re-générer automatiquement ou lien valable plus longtemps?
   - Impact: Réticence à re-soumettre (semble perte de travail)

5. **Intégrité données Google Sheets**:
   - Édition manuelle possible de Jules
   - **Recommandation**: Protéger colonnes système (urssaf_demande_id, statut, dates)
   - Impact: Risque corruption données

### 9.2 Optimisations futures (post-MVP)

- **Push notifications**: SMS/app au lieu d'email rappel
- **Webhook URSSAF**: Si disponible, plutôt que polling 4h
- **Batch submissions**: Soumettre 10 factures en une seule requête (performance)
- **Client portal**: Clients voient statut facture + rappel auto T+36h (décharge Jules)
- **Avoirs/annulations**: Gestion retours client (MVP pas inclus)
- **Pénalités retard**: Alertes si T > 7j sans rapprochement

---

## 10. Résumé des transitions d'état

```
BROUILLON
  ├─ (Jules clique "Soumettre") → SOUMIS
  ├─ (Jules clique "Annuler") → ANNULE [FIN]
  └─ (Erreur saisie) → reste BROUILLON (éditable)

SOUMIS
  ├─ (URSSAF accepte) → CREE
  └─ (Payload invalide) → ERREUR

ERREUR
  ├─ (Jules corrige + "Soumettre") → SOUMIS (retry)
  └─ (Jules "Annuler") → ANNULE [FIN]

CREE
  └─ (Email envoyé client) → EN_ATTENTE [auto, immédiat]

EN_ATTENTE
  ├─ (Client valide < 48h) → VALIDE
  ├─ (Client rejette) → REJETE
  ├─ (T > 48h) → EXPIRE
  └─ (Jules clique "Re-soumettre") → BROUILLON (rééditable)

VALIDE
  └─ (Polling détecte PAYE URSSAF) → PAYE

REJETE
  └─ (Jules modifie + "Soumettre") → SOUMIS (retry)

EXPIRE
  └─ (Jules "Re-soumettre") → SOUMIS

PAYE
  ├─ (Rapprochement lettrage auto) → RAPPROCHE [FIN]
  ├─ (Rapprochement lettrage manuel) → RAPPROCHE [FIN]
  └─ (En attente virement, attendre) → reste PAYE

RAPPROCHE → [FIN]
  └─ (Historique, pas d'action)

ANNULE → [FIN]
  └─ (Annulation, pas d'action)
```

---

## 11. Appendice : Exemple parcours happy path

### Scenario: Jules facture 1 client en 20 min

**T+0:00** — Jules ouvre SAP-Facture web
- Clique "Créer facture"
- Saisit client existant (Amélie) — auto-complete
- Heures: 2, Tarif: 35€/h
- Clique "Soumettre"

**T+0:30** — Système
- Vérifie client déjà inscrit URSSAF (oui, urssaf_id connu)
- Génère PDF facture
- Appelle API URSSAF POST /demandes-paiement
- Reçoit réponse CREE + id_demande
- Enregistre base Google Sheets

**T+0:45** — URSSAF
- Envoie email Amélie "Validez votre facture"
- Facture état EN_ATTENTE
- Jules reçoit confirmation "Facture soumise, attente validation client"

**T+24h** — Amélie
- Clique lien email URSSAF
- Valide facture (confirme montant)

**T+24h:05** — Polling (4h)
- Détecte statut VALIDE (lors prochain cycle)
- Notif Jules: "Facture validée, paiement en cours"

**T+72h** — URSSAF
- Effectue virement 70€ compte Swan Jules

**T+72h:30** — Sync Swan (6h)
- Récupère transaction 70€ libellé URSSAF
- Enregistre onglet Transactions

**T+75h** — Lettrage
- Formules matching trouvent exact: 70€ = 70€
- Score: 100 (50 montant + 30 date < 3j + 20 libellé)
- Lettre AUTO
- Facture état RAPPROCHE
- Dashboard Jules affiche "Complète" vert

**Total**: 3.5 jours du début à fin — dans SLA

---

## 12. Conclusion

Ce document décrit le **flux de facturation end-to-end complet** de SAP-Facture, de la création de facture par Jules jusqu'au rapprochement bancaire final.

Le flux implique:
- **5 acteurs principaux**: Jules, SAP-Facture (système), URSSAF, Client particulier, Swan
- **9 étapes majeures** avec transitions d'état strictes
- **8 onglets Google Sheets** pour stocker et calculer les données
- **SLA respectés**: 4-7 jours du début à fin, avec délai client 48h crit
- **Gestion d'erreurs exhaustive**: 15+ cas d'erreur avec récupération définie

Le système est conçu pour être **fiable, transparent, et auditablepour la comptabilité trimestrielle NOVA**.

---

**Document rédigé par**: Sarah (Product Owner)
**Source de vérité**: /home/jules/Documents/3-git/SAP/main/docs/schemas/SCHEMAS.html (Schéma 2)
**Scope**: MVP Phase 1
**Date**: 15 mars 2026
