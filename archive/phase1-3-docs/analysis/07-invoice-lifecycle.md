# Machine à États — Cycle de Vie Facture

**Document référence**: SCHEMAS.html § Section 7 — Machine à États
**Analysé par**: Winston (System Architect)
**Date**: 15 mars 2026
**Language**: Français

---

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [États possibles](#états-possibles)
3. [Transitions exhaustives](#transitions-exhaustives)
4. [Gardes et conditions](#gardes-et-conditions)
5. [Actions déclenchées](#actions-déclenchées)
6. [Timeouts et transitions automatiques](#timeouts-et-transitions-automatiques)
7. [Classification des états](#classification-des-états)
8. [Diagramme textuel](#diagramme-textuel)
9. [Règles de cohérence](#règles-de-cohérence)

---

## Vue d'ensemble

La facture dans SAP-Facture suit un **cycle de vie non-linéaire** avec 10 états possibles, dont 3 états terminaux et 7 états intermédiaires. Le cycle commence à la création par Jules et se termine soit par un paiement rapproché (RAPPROCHE), soit par annulation (ANNULE), soit par une erreur non-récupérable.

**Principes clés**:
- La machine à états est **déterministe** : pour chaque (état, événement), une seule transition est possible
- Plusieurs chemins peuvent mener au même état (multichemin)
- Certaines transitions sont conditionnelles (garde sur payload, délai, action client)
- Les transitions peuvent déclencher des effets de bord (API, email, PDF, mise à jour Sheets)

---

## États possibles

Tous les 10 états du cycle de vie facture, classés par catégorie :

### États initiaux et de draft
| État | Description | Durée typique | Éditable par Jules ? |
|------|-------------|----------------|----------------------|
| **BROUILLON** | Facture créée localement, PDF généré, jamais soumis à URSSAF. | Illimitée | ✓ Oui |
| | État initial après création via web/CLI | | |

### États de soumission
| État | Description | Durée typique | Éditable par Jules ? |
|------|-------------|----------------|----------------------|
| **SOUMIS** | Demande envoyée à URSSAF en attente de validation du payload. | < 1 min | ✗ Non |
| | Peut basculer rapidement en CREE ou ERREUR selon réponse API | | |

### État de création validée
| État | Description | Durée typique | Éditable par Jules ? |
|------|-------------|----------------|----------------------|
| **CREE** | URSSAF a accepté le payload, ID technique attribué. | 1 min | ✗ Non |
| | Email de validation envoyé au client | | |

### États d'attente client
| État | Description | Durée typique | Éditable par Jules ? |
|------|-------------|----------------|----------------------|
| **EN_ATTENTE** | Facture en attente de validation par le client via portail URSSAF. | 0–48 h | ✗ Non |
| | Timer 48h actif, reminder auto à T+36h | | |

### États de validation client
| État | Description | Durée typique | Éditable par Jules ? |
|------|-------------|----------------|----------------------|
| **VALIDE** | Client a validé sur portail URSSAF, URSSAF traite le paiement. | 1–5 j | ✗ Non |
| | Virement 100% du montant en cours de traitement | | |
| **REJETE** | Client a refusé la facture sur portail URSSAF. | Définitif | ✗ Non |
| | Peut être corrigée et re-soumise via BROUILLON | | |
| **EXPIRE** | Délai 48h dépassé sans validation client. | Définitif (attente relance) | ✗ Non |
| | Relance manuelle requise | | |

### États de paiement
| État | Description | Durée typique | Éditable par Jules ? |
|------|-------------|----------------|----------------------|
| **PAYE** | URSSAF a effectué le virement 100%, transaction reçue sur Swan. | 1–3 j | ✗ Non |
| | En attente de rapprochement bancaire avec transaction | | |

### États terminaux et anomalies
| État | Description | Durée typique | Éditable par Jules ? |
|------|-------------|----------------|----------------------|
| **RAPPROCHE** | Facture appairée avec transaction Swan (lettrage OK). | Définitif | ✗ Non |
| | État terminal, comptabilité clean | | |
| **ANNULE** | Facture annulée par Jules avant URSSAF. | Définitif | ✗ Non |
| | État terminal, sortie propre du cycle | | |
| **ERREUR** | Erreur API URSSAF ou données invalides. | Attente correction | ✗ Non |
| | Peut revenir en BROUILLON après correction | | |

---

## Transitions exhaustives

### Tableau de toutes les transitions

| # | Événement | État source | État cible | Condition/Garde | Pré-condition | Post-condition |
|----|-----------|-------------|-----------|------------------|---------------|----------------|
| **T1** | `create_invoice` | `[*]` | `BROUILLON` | Jules crée facture | N/A | PDF généré, clé `facture_id` créée |
| **T2** | `submit_to_urssaf` | `BROUILLON` | `SOUMIS` | Jules clique "Soumettre" | Facture > 0 | Payload envoyé à API URSSAF |
| **T3** | `cancel_before_submit` | `BROUILLON` | `ANNULE` | Jules annule | N/A | État terminal, aucun appel API |
| **T4** | `urssaf_accept` | `SOUMIS` | `CREE` | Payload valide, HTTP 200 | Code réponse = 200 | `urssaf_demande_id` stocké, email envoyer au client |
| **T5** | `urssaf_reject` | `SOUMIS` | `ERREUR` | Payload invalide ou API down | Code réponse >= 400 | Message erreur loggé, facture modifiable |
| **T6** | `fix_and_resubmit` | `ERREUR` | `BROUILLON` | Jules corrige les champs | N/A | Retour en édition, peut re-soumettre |
| **T7** | `email_sent_to_client` | `CREE` | `EN_ATTENTE` | Email URSSAF envoyé | HTTP 200 confirmé | Timer 48h lancé, rappel à T+36h planifié |
| **T8** | `client_validates` | `EN_ATTENTE` | `VALIDE` | Client clique "Valider" sur portail | webhook URSSAF reçu | URSSAF débute traitement paiement |
| **T9** | `timeout_48h_no_validation` | `EN_ATTENTE` | `EXPIRE` | Délai 48h dépassé | T >= T_soumission + 48h | Facture expirée, attente relance manuelle |
| **T10** | `client_rejects` | `EN_ATTENTE` | `REJETE` | Client clique "Refuser" | webhook URSSAF reçu | Cycle suspendu, correction requise |
| **T11** | `reminder_on_timeout` | `EN_ATTENTE` → `EN_ATTENTE` | N/A (boucle) | T = T_soumission + 36h | `created_at` < 36h | Email rappel envoyé à Jules (notification client suggérée) |
| **T12** | `resubmit_after_expiry` | `EXPIRE` | `BROUILLON` | Jules re-soumet | N/A | Nouveau `urssaf_demande_id`, timer réinitialisé |
| **T13** | `resubmit_after_rejection` | `REJETE` | `BROUILLON` | Jules corrige et re-soumet | N/A | Correction possible avant T2 |
| **T14** | `urssaf_payment_confirmed` | `VALIDE` | `PAYE` | URSSAF envoie webhook `payment_confirmed` | Virement sur Swan confirmé | Transaction importée dans onglet Transactions |
| **T15** | `transaction_matched` | `PAYE` | `RAPPROCHE` | Match automatique avec transaction Swan | Montant 100% facture trouvé | Score confiance >= 80, statut = LETTRE |
| **T16** | `transition_to_final` | `RAPPROCHE` | `[*]` | Fin du cycle | État terminal atteint | Comptabilité complete, aucune action additionnelle |
| **T17** | `transition_to_final` | `ANNULE` | `[*]` | Fin du cycle | État terminal atteint | Sortie propre |

---

## Gardes et conditions

### Garde T4 : URSSAF accepte (`SOUMIS` → `CREE`)

```
Condition: HTTP GET /demandes-paiement/{id} retourne statut == "CREE"
Pré-condition requise:
  - Payload JSON valide
  - Montant > 0
  - Date début <= Date fin
  - Client URSSAF inscrit (urssaf_id existe)

Post-condition garantie:
  - urssaf_demande_id != null
  - statut = CREE
  - created_timestamp enregistré
```

### Garde T5 : URSSAF rejette (`SOUMIS` → `ERREUR`)

```
Condition: HTTP GET /demandes-paiement/{id} retourne statut == "ERREUR"
             OU exception (APIError, Timeout, NetworkError)
             OU Code HTTP >= 400

Pré-condition requise:
  - Une tentative POST a été faite

Post-condition garantie:
  - error_message contient détail de l'erreur
  - statut = ERREUR
  - Facture reste modifiable
```

### Garde T8 : Client valide (`EN_ATTENTE` → `VALIDE`)

```
Condition: Webhook entrant de URSSAF avec event_type = "demande_validee"
           OU polling GET /demandes-paiement/{id} retourne statut == "VALIDE"

Pré-condition requise:
  - EN_ATTENTE actif depuis < 48h
  - Client a cliqué sur lien de validation URSSAF

Post-condition garantie:
  - validated_timestamp enregistré
  - statut = VALIDE
  - URSSAF prépare le virement
```

### Garde T9 : Timeout 48h (`EN_ATTENTE` → `EXPIRE`)

```
Condition: T_actuel >= T_creation + 48 heures
           ET statut actuel = EN_ATTENTE

Pré-condition requise:
  - EN_ATTENTE créé entre T_creation et T_creation + 48h
  - Aucune validation client reçue

Post-condition garantie:
  - expired_timestamp = T_actuel
  - statut = EXPIRE
  - Relance manuelle requise
```

### Garde T11 : Rappel à T+36h (boucle dans `EN_ATTENTE`)

```
Condition: T_actuel = T_creation + 36 heures
           ET statut = EN_ATTENTE
           ET reminder_sent = false

Post-condition garantie:
  - Email rappel envoyé à Jules
  - reminder_sent = true
  - EN_ATTENTE reste actif (pas de changement d'état)
  - Compteur continue (peut atteindre T+48h)
```

### Garde T15 : Transaction matchée (`PAYE` → `RAPPROCHE`)

```
Condition: Lettrage automatique trouvé dans Sheets (onglet Lettrage)
           Score confiance >= 80

Pré-condition requise:
  - Transaction Swan reçue avec montant == montant_facture
  - Date transaction dans fenêtre +/- 5 jours après VALIDE
  - Libellé contient "URSSAF"

Calcul score:
  - Montant exact match : +50
  - Date < 3 jours : +30
  - Libellé URSSAF : +20
  - Score final >= 80 : AUTO (transition immédiate)
  - Score 70-79 : A_VERIFIER (attente confirmation Jules)
  - Score < 70 : PAS_DE_MATCH (attente manuel)

Post-condition garantie:
  - facture_id écrit dans transaction
  - statut = RAPPROCHE
  - statut_lettrage = LETTRE
```

---

## Actions déclenchées

### Par transition

#### T1 : Création facture (`[*]` → `BROUILLON`)
**Actions immédiates**:
1. Générer PDF (logo + détails facture) via WeasyPrint
2. Créer clés uniques : `facture_id`, `pdf_drive_id`
3. Écrire ligne dans onglet Sheets "Factures" avec statut = BROUILLON
4. Enregistrer `created_at` timestamp

**API appelées**:
- Google Sheets API v4 (append row)
- Google Drive API (upload PDF)

**Données mises à jour**:
- Onglet Factures : nouvelle ligne avec [facture_id, client_id, montant, statut=BROUILLON, ...]

---

#### T2 : Soumission à URSSAF (`BROUILLON` → `SOUMIS`)
**Actions immédiates**:
1. Valider payload (montant > 0, dates cohérentes, client URSSAF connu)
2. POST /demandes-paiement → API URSSAF avec OAuth2 token
3. Écrire dans Sheets statut = SOUMIS, `submitted_at` = T_actuel

**Payload URSSAF** (POST /demandes-paiement):
```json
{
  "id_particulier": "urssaf_id",
  "montant_total": 1200.00,
  "nature": "HONORAIRES_PRESTATION_SERVICE",
  "date_debut": "2026-03-01",
  "date_fin": "2026-03-15",
  "description": "Cours particuliers — 20 heures"
}
```

**API appelées**:
- URSSAFClient.submit_invoice_request()
- Google Sheets API v4 (update row)

**Données mises à jour**:
- Onglet Factures : colonne statut = SOUMIS, horodatage submission

---

#### T4 : Acceptation URSSAF (`SOUMIS` → `CREE`)
**Actions immédiates**:
1. Recevoir réponse HTTP 200 avec `id_demande` et statut = CREE
2. Stocker `urssaf_demande_id` en base (ou Sheets)
3. Mettre à jour Sheets statut = CREE
4. Déclencher envoi email au client (via service URSSAF ou notification Jules)

**API appelées**:
- Polling GET /demandes-paiement/{id}
- Google Sheets API v4 (update row)
- EmailNotifier (optionnel : copie à Jules)

**Données mises à jour**:
- Onglet Factures : colonne urssaf_demande_id = [valeur URSSAF], statut = CREE

---

#### T5 : Rejet URSSAF (`SOUMIS` → `ERREUR`)
**Actions immédiates**:
1. Capturer le message d'erreur API
2. Mettre à jour Sheets : statut = ERREUR, error_message = [texte]
3. Logger l'erreur (severity = WARNING ou ERROR selon type)
4. Envoyer notification à Jules avec détails du problème

**Exemples d'erreurs**:
- Payload malformé (montant négatif, dates inversées)
- Client URSSAF non reconnu
- API URSSAF timeout
- Authentification OAuth2 expirée

**API appelées**:
- Logger (logging.error)
- Google Sheets API v4 (update row)
- EmailNotifier (alerte Jules)

**Données mises à jour**:
- Onglet Factures : statut = ERREUR, error_message = [texte complet]

---

#### T6 : Correction et ré-soumission (`ERREUR` → `BROUILLON`)
**Actions immédiates**:
1. Jules modifie les champs (montant, dates, client, etc.)
2. Mettre à jour Sheets avec valeurs corrigées
3. Revenir en BROUILLON pour re-soumission
4. Réinitialiser error_message = null

**Données mises à jour**:
- Onglet Factures : statut = BROUILLON, error_message = null, modified_at = T_actuel

---

#### T7 : Email envoyé au client (`CREE` → `EN_ATTENTE`)
**Actions immédiates**:
1. URSSAF envoie email au client avec lien de validation
2. Jules reçoit une copie (ou notification du système)
3. Mettre à jour Sheets : statut = EN_ATTENTE, `created_at` timestamp
4. Lancer timer 48h en arrière-plan
5. Planifier rappel automatique à T+36h

**Données mises à jour**:
- Onglet Factures : statut = EN_ATTENTE, en_attente_since = T_actuel

---

#### T8 : Client valide (`EN_ATTENTE` → `VALIDE`)
**Actions immédiates** (via webhook URSSAF ou polling):
1. Recevoir notification de validation client
2. Mettre à jour Sheets : statut = VALIDE, `validated_at` = T_actuel
3. Envoyer email de confirmation à Jules (optionnel)
4. Arrêter le timer 48h et la planification du rappel

**Données mises à jour**:
- Onglet Factures : statut = VALIDE, validated_at = T_actuel

---

#### T9 : Timeout 48h (`EN_ATTENTE` → `EXPIRE`)
**Actions immédiates** (déclenché par cron job toutes les 4h):
1. Check : pour chaque facture EN_ATTENTE, T_actuel - created_at > 48h ?
2. Si oui : mettre à jour Sheets : statut = EXPIRE, `expired_at` = T_actuel
3. Envoyer alerte Jules : "Facture XYZ expirée, relance requise"
4. Arrêter le timer et les rappels

**Données mises à jour**:
- Onglet Factures : statut = EXPIRE, expired_at = T_actuel

---

#### T10 : Client rejette (`EN_ATTENTE` → `REJETE`)
**Actions immédiates** (via webhook URSSAF ou polling):
1. Recevoir notification de refus client
2. Mettre à jour Sheets : statut = REJETE, `rejected_at` = T_actuel
3. Envoyer notification Jules avec raison du refus (si disponible)
4. Arrêter le timer 48h

**Données mises à jour**:
- Onglet Factures : statut = REJETE, rejected_at = T_actuel, reject_reason = [motif URSSAF]

---

#### T11 : Rappel à T+36h (boucle `EN_ATTENTE`)
**Actions immédiates** (déclenché par scheduler toutes les 4h):
1. Pour chaque facture EN_ATTENTE : T_actuel - created_at = 36h ?
2. Si oui ET reminder_sent = false :
   - Envoyer email à Jules : "Rappel : facture XYZ en attente de validation client"
   - Mettre à jour Sheets : reminder_sent = true, `reminder_sent_at` = T_actuel
3. Reste EN_ATTENTE (pas de changement d'état)

**Données mises à jour**:
- Onglet Factures : reminder_sent = true, reminder_sent_at = T_actuel

---

#### T12 : Ré-soumission après expiration (`EXPIRE` → `BROUILLON`)
**Actions immédiates**:
1. Jules clique "Relancer"
2. Réinitialiser les champs d'état : `created_at` = null, `reminder_sent` = false, `expired_at` = null
3. Passer statut = BROUILLON
4. Prêt pour T2 (nouvelle soumission avec nouveau `urssaf_demande_id`)

**Données mises à jour**:
- Onglet Factures : statut = BROUILLON, urssaf_demande_id = null, created_at = null

---

#### T13 : Ré-soumission après refus (`REJETE` → `BROUILLON`)
**Actions immédiates**:
1. Jules corrige les champs (montant, dates, client, description)
2. Mettre à jour Sheets avec valeurs corrigées
3. Passer statut = BROUILLON
4. Prêt pour T2

**Données mises à jour**:
- Onglet Factures : statut = BROUILLON, urssaf_demande_id = null, rejected_at = null

---

#### T14 : Paiement confirmé par URSSAF (`VALIDE` → `PAYE`)
**Actions immédiates** (via webhook URSSAF ou polling GET /demandes-paiement/{id}):
1. Recevoir notification statut = PAYE de URSSAF
2. Mettre à jour Sheets : statut = PAYE, `paid_at` = T_actuel
3. Déclencher SwanClient.fetch_transactions() pour importer nouvelles transactions
4. Envoyer notification Jules : "Paiement reçu, rapprochement en cours"

**Données mises à jour**:
- Onglet Factures : statut = PAYE, paid_at = T_actuel
- Onglet Transactions : import des transactions Swan depuis paid_at - 5j à paid_at + 5j

---

#### T15 : Transaction matchée (`PAYE` → `RAPPROCHE`)
**Actions immédiates** (via formules Sheets onglet Lettrage, score >= 80):
1. Trouver automatiquement transaction Swan avec montant_facture et libellé URSSAF
2. Calculer score confiance (voir Garde T15)
3. Si score >= 80 :
   - Écrire facture_id dans transaction
   - Mettre à jour Sheets : statut = RAPPROCHE, `matched_at` = T_actuel, statut_lettrage = LETTRE
4. Si score 70-79 : statut_lettrage = A_VERIFIER (attente confirmation Jules)
5. Si score < 70 : statut_lettrage = PAS_DE_MATCH (attente import manuel)

**Données mises à jour**:
- Onglet Lettrage : facture_id → transaction_id match
- Onglet Transactions : statut_lettrage = LETTRE, facture_id = [valeur]
- Onglet Factures : statut = RAPPROCHE, matched_at = T_actuel
- Onglet Balances : mise à jour montant reçu et soldes (formules)

---

#### T16/T17 : Fin du cycle (`RAPPROCHE` ou `ANNULE` → `[*]`)
**Actions immédiates**:
1. Marquer l'état terminal dans Sheets
2. Aucune action additionnelle requise
3. Facture visible dans onglet Factures avec statut final
4. Disponible dans exports et rapports

**Données mises à jour**:
- Onglet Factures : cycle_completed = true, completion_date = T_actuel

---

#### T3 : Annulation avant soumission (`BROUILLON` → `ANNULE`)
**Actions immédiates**:
1. Jules clique "Annuler"
2. Mettre à jour Sheets : statut = ANNULE, `annuled_at` = T_actuel
3. Aucun appel API URSSAF
4. Facture sortie du cycle, état terminal

**Données mises à jour**:
- Onglet Factures : statut = ANNULE, annuled_at = T_actuel

---

## Timeouts et transitions automatiques

### Timer 48h dans EN_ATTENTE

**Trigger**: Transition T7 (`CREE` → `EN_ATTENTE`)

**Durée**: 48 heures

**Vérification**: Cron job toutes les 4 heures
```
Pseudocode:
for facture in onglet_factures:
    if facture.statut == EN_ATTENTE:
        elapsed = now() - facture.created_at
        if elapsed > 48h:
            trigger T9 (EXPIRE)
        elif elapsed == 36h and reminder_sent == false:
            trigger T11 (envoi rappel, reste EN_ATTENTE)
```

**Action à T+36h**: Email rappel à Jules
**Action à T+48h**: Transition automatique EN_ATTENTE → EXPIRE

### Polling périodique des statuts URSSAF

**Trigger**: Toutes les 4 heures (configurable)

**Cron job**:
```
Pseudocode:
for facture in onglet_factures:
    if facture.statut in [SOUMIS, CREE, EN_ATTENTE, VALIDE]:
        response = urssaf_client.get_demande(facture.urssaf_demande_id)
        new_statut = response.statut

        if new_statut == CREE and current_statut == SOUMIS:
            trigger T4
        elif new_statut == ERREUR and current_statut == SOUMIS:
            trigger T5
        elif new_statut == VALIDE and current_statut == EN_ATTENTE:
            trigger T8
        elif new_statut == REJETE and current_statut == EN_ATTENTE:
            trigger T10
        elif new_statut == PAYE and current_statut == VALIDE:
            trigger T14
```

**Exceptions handling**:
- Timeout API URSSAF → log + retry dans 1h
- Malformed response → log + manual alert Jules
- OAuth2 token expired → ré-authentifier, retry

### Rappel automatique à T+36h

**Trigger**: EN_ATTENTE existe depuis 36h ET reminder_sent = false

**Fréquence**: Cron job toutes les 4 heures

**Action**: Envoyer email Jules + mettre à jour Sheets reminder_sent = true

**Message type**:
```
Sujet: [SAP-Facture] Rappel — Facture XYZ en attente validation

Contenu:
Facture #XYZ créée le 2026-03-15 14:30
Statut: EN ATTENTE (depuis 36 heures)
Client: Jean Dupont
Montant: 1 200 EUR

Action requise: Le client doit valider sur le portail URSSAF avant 2026-03-17 14:30

Lien: https://portail.urssaf.fr/...
```

---

## Classification des états

### États intermédiaires (7 états)
Ces états permettent la progression vers un état terminal :

| État | Peut progresser ? | Peut régresser ? |
|------|------------------|------------------|
| BROUILLON | Oui (→ SOUMIS ou ANNULE) | Non (état initial) |
| SOUMIS | Oui (→ CREE ou ERREUR) | Oui (← ERREUR via correction) |
| CREE | Oui (→ EN_ATTENTE) | Non |
| EN_ATTENTE | Oui (→ VALIDE, EXPIRE, ou REJETE) | Non |
| VALIDE | Oui (→ PAYE) | Non |
| PAYE | Oui (→ RAPPROCHE) | Non |
| ERREUR | Oui (→ BROUILLON) | Non |

### États terminaux (3 états)
Fin du cycle, aucune transition sortante :

| État | Définitif ? | Peut être relaunchée ? |
|------|-------------|----------------------|
| RAPPROCHE | Oui | Non (cycle complete) |
| ANNULE | Oui | Non (sortie volontaire) |
| EXPIRE | Non (attente relance) | Oui (via T12 → BROUILLON) |
| REJETE | Non (attente correction) | Oui (via T13 → BROUILLON) |

**Remarque**: EXPIRE et REJETE sont techniquement des états de "suspense" qui peuvent être relancés. Seuls RAPPROCHE et ANNULE sont véritablement terminaux.

### États avec timer actif

| État | Timer | Durée | Action déclenchée |
|------|-------|-------|-------------------|
| EN_ATTENTE | Oui | 48h | EXPIRE ou VALIDE (selon client) |
| EN_ATTENTE | Oui (secondaire) | 36h | Email rappel (reste EN_ATTENTE) |

---

## Diagramme textuel

```
                         ┌─────────────────────────────────────────────┐
                         │    CYCLE DE VIE FACTURE — Mermaid Format    │
                         └─────────────────────────────────────────────┘

                    ┌──────────────────────────────────┐
                    │            ENTREE                │
                    │          (Jules crée)            │
                    └───────────────┬──────────────────┘
                                    │
                                  T1│ create_invoice
                                    ▼
                    ┌──────────────────────────────────┐
                    │          BROUILLON               │
                    │  • PDF généré                    │
                    │  • Éditable                      │
                    │  • facture_id créée              │
                    └───────────┬──────────────┬───────┘
                                │              │
                              T2│              │T3
                   submit_to_   │cancel_before │
                    urssaf       │   submit     │
                                ▼              ▼
                    ┌────────────────┐  ┌──────────────┐
                    │    SOUMIS      │  │   ANNULE     │
                    │ • API appelée  │  │  (Terminal)  │
                    │ • Attente répon│  └──────────────┘
                    └────┬───────┬──┘
                         │       │
                       T4│       │T5
                    accept│reject │
                    │       │
            ┌───────▼──┐    ▼
            │   CREE   │  ERREUR
            │ • ID OK  │  • Fix & Retry
            │ • Email  │  ↻ T6 → BROUILLON
            └────┬────┘
                 │
               T7│ email_sent_to_client
                 │
        ┌────────▼──────────────┐
        │   EN_ATTENTE          │
        │ • Timer 48h actif     │
        │ • Rappel T+36h        │
        │ • Client valide ?     │
        └──┬─────────┬────────┬─┘
           │         │        │
         T8│       T10│      T9│
       valide│reject│expire│
           │         │        │
      ┌────▼──┐ ┌───▼──┐ ┌───▼──┐
      │ VALIDE│ │REJETE│ │EXPIRE│
      │       │ │      │ │      │
      └──┬───┘ └────┬──┘ └────┬─┘
         │          │         │
       T14│       T13│       T12│
    payment│resubmit │resubmit  │
    confirm│         │          │
         │          │         │
         ▼          ▼         ▼
      ┌────────────────┐
      │     PAYE       │
      │ • Virement OK  │
      │ • Swan reçu    │
      └────┬──────────┘
           │
         T15│ transaction_matched
            │ (score >= 80)
           ▼
      ┌──────────────────┐
      │   RAPPROCHE      │
      │  (Terminal)      │
      │  • Lettrage OK   │
      │  • Comptabilité  │
      │    complete      │
      └──────────────────┘
           │
           │ cycle_complete
           ▼
      ┌──────────────┐
      │   SORTIE     │
      │   [*]        │
      └──────────────┘

Legend:
  T1-T17 = Numéro de transition (voir tableau)
  [*] = État de départ/fin (meta-état)
  → = Transition simple
  ↻ = Boucle (rester dans l'état)
```

---

## Règles de cohérence

### Règle 1 : Une seule transition active par (état, événement)
Pour chaque combinaison (état source, événement), il existe exactement une transition cible et une seule.

**Exemple**: Dans l'état EN_ATTENTE, l'événement "timeout_48h" ne peut mener qu'à EXPIRE.

### Règle 2 : Pas de chemin circulaire infini
Aucune chaîne de transitions ne peut créer une boucle infinie sauf la boucle deliberée T11 (rappel dans EN_ATTENTE).

**Vérification**: Chaque chemin doit atteindre un état terminal dans un temps fini.

### Règle 3 : Pas de transition directe entre états terminaux
Une fois RAPPROCHE, ANNULE atteint, aucune transition n'est possible.

**Exception**: EXPIRE et REJETE peuvent revenir en BROUILLON car elles sont des "suspensions" plutôt que des états réellement terminaux.

### Règle 4 : Statut dans Google Sheets toujours synchronisé
Le champ `statut` dans l'onglet Factures doit toujours refléter l'état courant de la machine à états.

**Synchronisation**: Chaque transition met à jour Sheets en atomic (une seule write par transition).

### Règle 5 : Les timestamps sont immuables
Une fois un timestamp défini (created_at, submitted_at, etc.), il ne peut pas être modifié.

**Exception**: Lors d'une relance (EXPIRE → BROUILLON), on réinitialise les timestamps pour un cycle neuf.

### Règle 6 : Actions doivent être idempotentes
Si une action est déclenchée deux fois pour la même transition, le résultat doit être le même (pas d'effets de bord cumulatifs).

**Exemple**: Envoyer un email rappel deux fois → email reçu une fois + flagué `reminder_sent` pour éviter doublons.

### Règle 7 : Garde avant transition
Chaque transition doit vérifier sa garde AVANT de modifier l'état.

**Pseudocode**:
```
if evaluate_guard(transition):
    execute_actions(transition)
    update_state(target_state)
else:
    log_guard_failure(transition)
    stay_in_current_state()
```

### Règle 8 : Rollback en cas d'erreur d'action
Si une action échoue (ex: API Sheets timeout), la transition ne doit pas s'effectuer (et loguer l'erreur).

**Exemple**: Si PUT Sheets échoue après "pay_confirmed" webhook, rester en VALIDE et retry automatique.

---

## Annexe : Cas d'usage complet

### Scénario 1 : Cycle nominal (succès)

```
T0 : Jules crée facture "COURS_2026-03-15" (montant 1200 EUR, client Jean)
     → T1 → BROUILLON (PDF généré)

T1 : Jules soumet à URSSAF
     → T2 → SOUMIS (API appelée)

T2 : URSSAF accepte après 10 sec
     → T4 → CREE (urssaf_demande_id = "DEM123")

T3 : Email URSSAF envoyé à Jean
     → T7 → EN_ATTENTE (timer 48h lancé)

T10 : Jean valide sur portail URSSAF (T3 + 4h)
      → T8 → VALIDE

T15 : URSSAF traite virement (T10 + 2j)
      → T14 → PAYE (transaction Swan reçue)

T20 : Lettrage automatique (score 95)
      → T15 → RAPPROCHE (cycle terminé)
```

Durée totale : ~2 jours

---

### Scénario 2 : Expiration et relance

```
T0 : Jules crée facture
     → T1 → BROUILLON

T5 : Jules soumet
     → T2 → SOUMIS → T4 → CREE → T7 → EN_ATTENTE (timer lancé)

T20 : T+36h — Email rappel envoyé à Jules
      → T11 → EN_ATTENTE (reminder_sent = true)

T25 : T+48h — Timeout atteint, Jean n'a pas validé
      → T9 → EXPIRE

T30 : Jules relance facture
      → T12 → BROUILLON

T35 : Jules re-soumet
      → T2 → SOUMIS → T4 → CREE → T7 → EN_ATTENTE (cycle 2)

T40 : Jean valide rapidement (T35 + 1h)
      → T8 → VALIDE → T14 → PAYE → T15 → RAPPROCHE
```

Durée totale : ~2 jours (+ relance) = ~3-4 jours

---

### Scénario 3 : Erreur et correction

```
T0 : Jules crée facture avec client invalide
     → T1 → BROUILLON

T5 : Jules soumet
     → T2 → SOUMIS

T10 : URSSAF rejette (client non trouvé)
      → T5 → ERREUR (error_message = "Client URSSAF not found")

T15 : Jules corrige client_id
      → T6 → BROUILLON

T20 : Jules re-soumet
      → T2 → SOUMIS → T4 → CREE → T7 → EN_ATTENTE → ...
```

Durée correction : ~5-10 min

---

### Scénario 4 : Rejet client

```
T0 : Jules crée facture, soumet normalement
     → ... → EN_ATTENTE

T10 : Jean refuse sur portail (montant trop élevé)
      → T10 → REJETE

T15 : Jules corrige montant (reduce by 20%)
      → T13 → BROUILLON

T20 : Jules re-soumet
      → T2 → SOUMIS → ... → VALIDE → PAYE → RAPPROCHE
```

Durée totale : ~2.5 jours

---

### Scénario 5 : Annulation avant soumission

```
T0 : Jules crée facture
     → T1 → BROUILLON

T5 : Jules change d'avis (client a payé en liquide)
     → T3 → ANNULE (état terminal)
```

Durée totale : < 1 min

---

## Résumé technique

| Aspect | Détail |
|--------|--------|
| **Nombre d'états** | 10 (7 intermédiaires + 3 terminaux) |
| **Nombre de transitions** | 17 |
| **États avec timer** | EN_ATTENTE (48h + rappel 36h) |
| **États éditables** | BROUILLON uniquement |
| **Polling frequency** | Toutes les 4 heures |
| **API appelées** | URSSAF (OAuth2 + REST), Google Sheets, Swan, SMTP |
| **Source de vérité** | Google Sheets onglet Factures (colonne statut) |
| **Atomicité** | Chaque transition = 1 update Sheets |
| **Idempotence** | Rappels et emails flagués pour éviter doublons |
| **Rollback** | Erreurs loggées, pas d'état corrompu |

---

**Document complet, analysé depuis SCHEMAS.html Section 7**
**Fin du document**
