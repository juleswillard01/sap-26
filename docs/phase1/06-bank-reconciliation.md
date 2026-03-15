# Rapprochement Bancaire & Lettrage — Swan / URSSAF

**Version**: 1.0
**Date**: Mars 2026
**Auteur**: Sarah, BMAD Product Owner
**Contexte**: Phase 2 de SAP-Facture — Automatisation du lettrage des virements URSSAF sur Swan

---

## 1. Vue d'ensemble métier

### Objectif
Matcher automatiquement les virements reçus sur le compte Swan (provenant d'URSSAF) avec les factures émises, afin de passer les factures en statut `RAPPROCHE` et d'assurer la cohérence comptable.

### Acteurs
- **Jules** (utilisateur final) : valide ou corrige manuellement les matchs douteux
- **Système** (BankReconciliation Service) : importe les transactions Swan, lance l'algorithme de scoring, propose les lettres
- **Google Sheets** : stocke les résultats (onglet Lettrage, Balances)

### Statuts cibles
À la fin du lettrage, chaque transaction est soit :
- **LETTRE** : matchée automatiquement avec une facture (score ≥ 80)
- **A_VERIFIER** : matchée mais score faible < 80 (Jules confirme manuellement)
- **PAS_DE_MATCH** : aucune facture correspondante trouvée (en attente de correction)

---

## 2. Flux de rapprochement détaillé

### 2.1 Cycle de rapprochement complet

```
┌─────────────────────────────────────────────────────────────┐
│ FLUX RAPPROCHEMENT BANCAIRE                                │
└─────────────────────────────────────────────────────────────┘

[1] Import des transactions Swan
    └─ Query Swan GraphQL : toutes transactions des 30 derniers jours
    └─ Filter : montants > 0, type = CREDIT, source = URSSAF (libelle)
    └─ Ecrire dans onglet Transactions (Google Sheets)

[2] Lancement du matching automatique
    └─ Pour chaque transaction importée
    └─ Pour chaque facture en statut PAYE
    └─ Calculer score confiance

[3] Decision scoring
    ├─ Score >= 80
    │  └─ LETTRE AUTO : lier transaction ↔ facture
    │  └─ Colorer vert
    │  └─ Marquer STATUT = LETTRE dans Sheets
    │
    ├─ Score 50-79
    │  └─ A_VERIFIER : proposer le match a Jules
    │  └─ Colorer orange
    │  └─ Marquer STATUT = A_VERIFIER
    │  └─ Jules peut confirmer ou ignorer
    │
    └─ Score < 50 ou pas de match
       └─ PAS_DE_MATCH : attendre
       └─ Colorer rouge
       └─ Marquer STATUT = PAS_DE_MATCH

[4] Mise a jour des soldes
    └─ Onglet Balances recalcule (formules)
    └─ nb_non_lettrees, solde_total mises a jour
    └─ Alertes si discrepance > seuil

[5] Actions manuelles (Jules)
    └─ Valider les matchs en A_VERIFIER
    └─ Forcer un match manuel pour PAS_DE_MATCH
    └─ Ignorer un match propose
    └─ Tracer les modifications
```

### 2.2 Timeline pour une facture type

```
Jour 0 : Jules cree facture 1500€
  ↓
Jour 1 : Client valide sur portail URSSAF
  ↓
Jour 2-5 : URSSAF effectue virement 1500€ → Swan
  ↓
Jour 5 18h : Cron import Swan (toutes les 4h)
  ↓
Jour 5 19h : Matching auto exécuté
  └─ Transaction trouvée avec montant 1500€, date virement J+2
  └─ Score = 50 (montant) + 30 (date) + 20 (libelle URSSAF) = 100
  └─ Facture = LETTRE
  ↓
Jour 5 23h : Balances recalcule
  └─ Solde augmente de 1500€
  └─ nb_non_lettrees decremente de 1
```

---

## 3. Algorithme de matching

### 3.1 Définition des critères

Pour chaque facture `PAYE` et chaque transaction `importée`, on applique ces critères en **fenêtre glissante** de 5 jours autour de la date de paiement estimée :

#### Critère 1 : Montant
```
SI montant_transaction = montant_facture * 1.0 (exactement 100%)
  ✓ Match montant : 50 points
SINON SI montant_transaction = montant_facture * 0.5 (paiement partiel)
  ✓ Paiement partiel identifie : 25 points (cas limite, voir section 6)
SINON
  ✗ Pas de match montant : 0 points
```

**Justification métier** : URSSAF vire 100% de la facture à Jules. Le client paye sa moitié directement à l'URSSAF. Un écart montant est le signal d'alerte principal.

#### Critère 2 : Date de paiement
```
date_transaction = date_soumis_facture + N jours

SI N ∈ [-5, -1] (paiement avant la soumission, cas rare URSSAF rapide)
  ✓ Date anticipee : +5 points

SI N ∈ [0, 3] (paiement dans les 3 jours, normal)
  ✓ Date dans le delai normal : +30 points

SI N ∈ [4, 5] (paiement legerement en retard)
  ✓ Date legerement retardee : +15 points

SI N > 5 (paiement > 5 jours)
  ✗ Date anormale : 0 points (possible paiement fusion ou doublon)

SI N < -5 (transaction trop ancienne)
  ✗ Date anormale : 0 points
```

**Justification métier** : Entre la soumission et le virement, URSSAF prend 2-4 jours. Une transaction > 5 jours est soit un paiement distinct (multi-factures agrégées), soit un doublon.

#### Critère 3 : Libellé bancaire
```
SI libelle_transaction CONTIENT "URSSAF"
  ✓ Source URSSAF confirmée : +20 points

SI libelle_transaction CONTIENT nom_client
  ✓ Reference client : +10 points (bonus, max 20 total)

SI libelle_transaction CONTIENT numero_facture (optionnel)
  ✓ Reference facture trouvée : +15 points (bonus, max 20 total)

SINON
  ✗ Libellé incomplet : 0 points
```

**Justification métier** : Le libellé "URSSAF" confirme l'origine officielle. Le nom du client ou le numéro de facture facilite la traçabilité manuelle.

### 3.2 Pseudo-code de l'algorithme

```python
def compute_match_score(facture, transaction) -> int:
    """
    Calcule le score de confiance pour un match facture ↔ transaction.
    Retourne entier entre 0 et 100.
    """
    score = 0

    # Critère montant (50 points max)
    if transaction.montant == facture.montant:
        score += 50  # Match exact
    elif transaction.montant == facture.montant * 0.5:
        score += 25  # Paiement partiel
    else:
        return 0  # Pas de match sur montant = score minimum

    # Critère date (30 points max)
    days_diff = (transaction.date - facture.date_soumis).days
    if days_diff < -5 or days_diff > 5:
        return 0  # Date anormale = score minimum
    elif 0 <= days_diff <= 3:
        score += 30  # Délai normal
    elif days_diff == 4 or days_diff == 5:
        score += 15  # Légèrement retardé
    elif -5 <= days_diff < 0:
        score += 5   # Anticipé (rare)

    # Critère libellé (20 points max)
    libelle_lower = transaction.libelle.lower()
    if "urssaf" in libelle_lower:
        score += 20  # Source URSSAF
    elif "paiement" in libelle_lower or "virement" in libelle_lower:
        score += 10  # Virement generique
    else:
        return 0  # Pas de libellé reconnu = score minimum

    return min(score, 100)  # Capped at 100


def lettrer_factures() -> None:
    """
    Fonction cron : lettrer toutes les factures PAYE.
    """
    factures_paye = get_factures_with_statut("PAYE")
    transactions = get_transactions_from_swan()

    for facture in factures_paye:
        # Fenêtre de recherche : ±7 jours autour de la date de paiement estimée
        window_start = facture.date_soumis - timedelta(days=5)
        window_end = facture.date_soumis + timedelta(days=5)

        # Filtrer les transactions dans la fenêtre
        window_txns = [t for t in transactions
                       if window_start <= t.date <= window_end
                       and t.montant > 0
                       and "URSSAF" in t.libelle.upper()]

        # Chercher le meilleur match
        best_match = None
        best_score = 0

        for txn in window_txns:
            score = compute_match_score(facture, txn)
            if score > best_score:
                best_score = score
                best_match = txn

        # Appliquer la decision
        if best_match is None:
            facture.statut_lettrage = "PAS_DE_MATCH"
            facture.score_confiance = 0
        elif best_score >= 80:
            facture.statut_lettrage = "LETTRE"
            facture.score_confiance = best_score
            facture.transaction_id = best_match.id
        else:  # 50 <= best_score < 80
            facture.statut_lettrage = "A_VERIFIER"
            facture.score_confiance = best_score
            facture.transaction_suggeree_id = best_match.id

        save_to_sheets(facture)
```

---

## 4. Scoring de confiance : pondération détaillée

### 4.1 Matrice de scoring

| Critère | Points | Condition | Raison métier |
|---------|--------|-----------|---------------|
| **MONTANT** | 50 | Égal 100% | URSSAF vire le montant exact |
| | 25 | Égal 50% | Paiement partiel détecté |
| | 0 | Différent | Reject automatique (autre facture) |
| **DATE** | 30 | J+0 à J+3 | Délai URSSAF normal (2-4j) |
| | 15 | J+4 à J+5 | Délai légèrement allongé |
| | 5 | J-5 à J-1 | Anticipé (URSSAF rapide) |
| | 0 | > J+5 ou < J-5 | Hors fenêtre (fusion/doublon) |
| **LIBELLÉ** | 20 | URSSAF | Source officielle confirmée |
| | 10 | Paiement/Virement | Crédit généralisé |
| | 0 | Autre | Pas de contexte bancaire |

### 4.2 Distribution des scores

```
EXEMPLE 1 : Match parfait
├─ Montant : 50/50
├─ Date : J+2 → +30/30
└─ Libellé : "URSSAF PARIS" → +20/20
TOTAL = 100 ✓ LETTRE AUTO

EXEMPLE 2 : Match bon mais date legerement tardive
├─ Montant : 50/50
├─ Date : J+5 → +15/30
└─ Libellé : "Virement URSSAF" → +20/20
TOTAL = 85 ✓ LETTRE AUTO (seuil >= 80)

EXEMPLE 3 : Match moyen, libellé faible
├─ Montant : 50/50
├─ Date : J+2 → +30/30
└─ Libellé : "Paiement recu" → +10/20
TOTAL = 90 ✓ LETTRE AUTO

EXEMPLE 4 : Match faible, julescroit qu'il faut verifier
├─ Montant : 50/50
├─ Date : J+1 → +30/30
└─ Libellé : "Virement" (pas URSSAF) → +0/20
TOTAL = 80 ✓ LETTRE AUTO (seul, peu de contexte)

EXEMPLE 5 : Match avec paiement partiel
├─ Montant : 1500€ facture, 750€ transaction → +25/50
├─ Date : J+2 → +30/30
└─ Libellé : "URSSAF" → +20/20
TOTAL = 75 ⚠ A_VERIFIER (voir section cas limites)

EXEMPLE 6 : Match impossible
├─ Montant : 1500€ vs 2000€ → 0/50
└─ (score auto = 0, pas de poursuite)
TOTAL = 0 ✗ PAS_DE_MATCH
```

---

## 5. Seuils de décision et actions

### 5.1 Règles de décision

```
┌──────────────────────────────────────┐
│ Score de confiance                   │
├──────────────────────────────────────┤
│ >= 80  │ LETTRE AUTO                 │
│        │ ✓ Appliquer le match        │
│        │ ✓ Statut facture = RAPPROCHE│
│        │ ✓ Colorer vert              │
├──────────────────────────────────────┤
│ 50-79  │ A_VERIFIER                  │
│        │ ⚠ Proposer le match         │
│        │ ⚠ Jules confirme/ignore     │
│        │ ⚠ Colorer orange            │
├──────────────────────────────────────┤
│ 0-49   │ PAS_DE_MATCH                │
│        │ ✗ Aucun match viable        │
│        │ ✗ En attente d'action       │
│        │ ✗ Colorer rouge             │
└──────────────────────────────────────┘
```

### 5.2 Actions système et manuelles

#### Seuil >= 80 : Lettrage automatique
```
Système :
  1. Cherche le meilleur match (score max)
  2. Si score >= 80, applique le lettrage
  3. Ecrire dans Sheets :
     - onglet Factures : colonne facture_id = transaction_id
     - onglet Factures : colonne statut_lettrage = "LETTRE"
     - onglet Transactions : statut = "LETTRE"
  4. Mise à jour horodatée (date_lettrage = now)
  5. Log : {facture_id, transaction_id, score, action="AUTO"}

Jules ne fait rien → match validé.
```

#### Seuil 50-79 : Vérification manuelle requise
```
Système :
  1. Chercherait le match (50 <= score < 80)
  2. NE PAS appliquer automatiquement
  3. Ecrire dans Sheets :
     - onglet Lettrage : colonne score_confiance = score
     - onglet Lettrage : colonne statut = "A_VERIFIER"
     - onglet Lettrage : colonne transaction_suggeree_id = txn_id
  4. Colorer en orange pour alerter Jules
  5. Log : {facture_id, transaction_id, score, action="SUGGESTED"}

Jules doit :
  ✓ Confirmer (click "Valider") → applique le lettrage
  ✗ Ignorer (click "Ignorer") → statut = "PAS_DE_MATCH"
  → Forcer un autre match (dropdown liste) → change transaction_suggeree
```

#### Seuil 0-49 : Pas de match trouvé
```
Système :
  1. Aucune transaction dans la fenêtre
  2. OU toutes les transactions échouent à score < 50
  3. Ecrire dans Sheets :
     - onglet Factures : statut_lettrage = "PAS_DE_MATCH"
     - onglet Factures : score_confiance = 0
  4. Colorer en rouge pour alerter Jules
  5. Log : {facture_id, action="NO_MATCH"}

Jules peut :
  → Chercher manuellement dans Transactions
  → Traîner-déposer une transaction sur la facture (drag-drop)
  → Ou modifier les dates/montants si erreur saisie
  → Le match devient alors manuel (flag = "MANUAL")
```

---

## 6. Intégration API Swan GraphQL

### 6.1 Architecture d'intégration

```
SAP-Facture (FastAPI)
  │
  ├─ SwanClient (class)
  │  └─ async def get_transactions(
  │         account_id: str,
  │         limit: int = 100,
  │         after_date: date = None
  │     ) -> list[Transaction]
  │
  └─ BankReconciliation Service
     └─ lettrer_factures()
        └─ appelle Swan.get_transactions()
        └─ lance matching automatique
```

### 6.2 Query GraphQL (Swan API)

```graphql
query GetTransactions(
  $accountId: ID!
  $first: Int
  $after: String
) {
  account(id: $accountId) {
    transactions(
      first: $first
      after: $after
      orderBy: CREATION_DATE_DESC
    ) {
      edges {
        node {
          id
          reference
          amount {
            value
            currency
          }
          bookingDate
          valueDate
          label
          counterparty {
            name
          }
          direction
          status
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
```

### 6.3 Champs extraits et mapping

| Champ Swan | Type | Mapping SAP | Utilité |
|-----------|------|-----------|---------|
| `id` | String | `transaction_id` | Clé unique |
| `reference` | String | `swan_reference` | Ref interne Swan |
| `amount.value` | Decimal | `montant` | Montant TTC |
| `amount.currency` | String | `devise` | EUR (assertion) |
| `valueDate` | ISO Date | `date_valeur` | Date de crédit compte |
| `label` | String | `libelle` | "URSSAF PARIS…" |
| `counterparty.name` | String | `nom_tiers` | "URSSAF" confirmé |
| `direction` | ENUM | filter | IN (tous les credits) |
| `status` | ENUM | filter | IN (BOOKED, SETTLED) |
| `bookingDate` | ISO Date | `date_comptable` | Jour comptage |

### 6.4 Pagination et limites

```python
class SwanClient:
    async def get_transactions(
        self,
        account_id: str,
        days_back: int = 30,  # Par défaut, 30 derniers jours
        limit: int = 100      # Transactions par requête
    ) -> list[Transaction]:
        """
        Récupère toutes les transactions des N derniers jours.
        Gère la pagination Swan automatiquement (curseurs).
        """
        transactions = []
        after_cursor = None
        date_min = date.today() - timedelta(days=days_back)

        while True:
            response = await self.execute_query(
                query=GET_TRANSACTIONS_QUERY,
                variables={
                    "accountId": account_id,
                    "first": limit,
                    "after": after_cursor
                }
            )

            edges = response["account"]["transactions"]["edges"]
            for edge in edges:
                txn = edge["node"]
                parsed = Transaction(
                    id=txn["id"],
                    montant=txn["amount"]["value"],
                    devise=txn["amount"]["currency"],
                    date_valeur=parse_date(txn["valueDate"]),
                    libelle=txn["label"],
                    counterparty=txn["counterparty"]["name"],
                    status=txn["status"]
                )
                if parsed.date_valeur >= date_min:
                    transactions.append(parsed)

            # Pagination
            page_info = response["account"]["transactions"]["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            after_cursor = page_info["endCursor"]

        return transactions
```

### 6.5 Erreurs et retry

```python
async def get_transactions_with_retry(
    self,
    account_id: str,
    max_retries: int = 3
) -> list[Transaction]:
    """Gère les erreurs Swan (rate limit, timeout, 5xx)."""

    for attempt in range(max_retries):
        try:
            return await self.get_transactions(account_id)

        except RateLimitError as e:
            # Swan rate limit (429)
            wait_time = int(e.retry_after) if hasattr(e, 'retry_after') else 60
            logger.warning(f"Swan rate limit, attente {wait_time}s")
            await asyncio.sleep(wait_time)

        except ConnectionError as e:
            # Timeout ou réseau
            if attempt < max_retries - 1:
                wait_time = 5 * (2 ** attempt)  # Backoff exponentiel
                logger.warning(f"Retry Swan {attempt+1}/{max_retries}, attente {wait_time}s")
                await asyncio.sleep(wait_time)
            else:
                raise

        except AuthError as e:
            # Token expiré ou invalide
            logger.error("Swan auth failed, token invalide")
            # Chercher nouveau token (refresh)
            await self.refresh_access_token()
            # Relancer
            if attempt < max_retries - 1:
                continue
            else:
                raise

    raise Exception("Swan fetch failed after retries")
```

---

## 7. Cas limites et gestion spécifique

### 7.1 Paiement partiel

**Scénario** : Jules facture 1500€, mais URSSAF vire seulement 750€ (paiement échelonné ou réduction).

```
Montant detecté : 1500€ facture vs 750€ transaction
│
├─ Option 1 : Créer une note de crédit
│  └─ BankReconciliation détecte le partial
│  └─ Marque statut = "PARTIAL" (nouveau statut)
│  └─ Jules crée avoir 750€ automatiquement
│  └─ Relance paiement reste (750€)
│  └─ Lettrage appliqué sur le partial
│
├─ Option 2 : Accepter le partial (pour MVP)
│  └─ Score : 25 (montant partial) + 30 (date) + 20 (libellé) = 75
│  └─ Statut : A_VERIFIER
│  └─ Jules confirme ou crée avoir
│
└─ Recommandation Phase 2
   └─ Automatiser la création d'avoirs
   └─ Ajouter logique "multi-virements" : facture peut être lettree avec N transactions
```

### 7.2 Doublon de transaction

**Scénario** : Swan importe 2 fois la même transaction (bug import, webhook double).

```
Transaction 1 : ID=TXN-001, 1500€, "URSSAF", J+2
Transaction 2 : ID=TXN-002, 1500€, "URSSAF", J+2 (doublon)

Lettrage pour facture 1500€ :
├─ Match TXN-001 : score 100 → LETTRE
├─ Match TXN-002 : score 100, mais facture déjà lettrée
│  └─ Flag "DOUBLON_DETECTE"
│  └─ Marquer TXN-002 statut = "DOUBLON"
│  └─ Alerte : "Transaction dupliquée détectée"
│
Action Jules :
└─ Suppression du doublon dans Swan (ou marquer ignore dans SAP)
```

**Prevention** :
- Deduplication au niveau Swan (garder transaction la plus récente)
- Hash transactions (montant + date + libellé) pour détecter doublons avant matching

### 7.3 Transaction non-URSSAF

**Scénario** : Virement entrant sur Swan qui n'a rien à voir avec les factures (remboursement bancaire, virement privé).

```
Transaction : 100€, "Remboursement intérêts compte"
│
Matching :
├─ Libellé ≠ "URSSAF" → 0 points de libellé
├─ Montant ne correspond à aucune facture
└─ Score = 0 pour toute facture → PAS_DE_MATCH

Jules voit :
└─ Onglet Transactions : colonne "facture_id" = vide
└─ Onglet Balances : ligne "Solde inclut transactions non-lettrees"
└─ Action : ignorer manuellement ou classer en "Autre revenu"
```

**Prevention** :
- Filter Swan : ne chercher que montants >= seuil minimum (ex: 500€)
- Filter libellé : chercher "URSSAF" obligatoirement dans la phase matching
- Donner option à Jules de "classer" les transactions orphelines

### 7.4 Paiement fusion (multi-factures)

**Scénario** : Jules a 2 factures non-payées (1200€ + 800€). URSSAF les agrège et vire 2000€ en une seule transaction.

```
Factures :
  FAC-001 : 1200€, date_soumis J-5 → état PAYE, en attente lettrage
  FAC-002 : 800€, date_soumis J-3 → état PAYE, en attente lettrage

Swan Transaction :
  TXN-100 : 2000€, "URSSAF FUSION", J+2

Matching :
├─ FAC-001 vs TXN-100
│  └─ Montant : 1200€ ≠ 2000€ → 0 points → PAS_DE_MATCH
│
├─ FAC-002 vs TXN-100
│  └─ Montant : 800€ ≠ 2000€ → 0 points → PAS_DE_MATCH
│
└─ Aucune facture lettree

Jules doit :
├─ Option 1 : Créer facture "FUSION" de 2000€ → lettrer TXN-100
├─ Option 2 : Split manuel de TXN-100 (créer TXN-100A=1200€, TXN-100B=800€)
│             → puis lettrer chacun
├─ Option 3 : Forcer lettrage manuel sur les 2 factures
│  └─ Drag TXN-100 sur FAC-001 → "Lettrage partiel 1200€ de 2000€"
│  └─ Drag TXN-100 sur FAC-002 → "Lettrage partiel 800€ de 2000€"
│
Recommandation :
└─ Pour MVP : détection fusion (montant TXN = SUM montants factures)
└─ Pour Phase 2 : UI multi-select pour lettrer 1 txn avec N factures
```

### 7.5 Transaction antidatée (Swan import retardé)

**Scénario** : URSSAF a virement le 5 mars, mais Swan le reporte le 12 mars (sync retard).

```
Facture FAC-001 : date_soumis = 01-Mar
  ↓ (normalement URSSAF transfère J+2-4)
Virement URSSAF réel : 05-Mar
  ↓ (Swan sync retard)
Apparait dans Swan : 12-Mar

Matching le 12 mars :
├─ date_facture = 01-Mar, date_transaction = 12-Mar
├─ Écart = +11 jours > fenêtre +5j
└─ Score = 0 → PAS_DE_MATCH

Jules le 13 mars :
├─ Remarque la transaction orpheline
├─ Vérifie manually : "Transaction du 12 Mars, mais vraiment reçue le 5"
├─ Corrige la date dans Swan (ou clique "Corriger date de valeur")
├─ Relance le matching → trouve FAC-001
└─ Lettrage appliqué
```

**Prevention** :
- Lors import Swan, capturer `valueDate` (date crédit réel) et `bookingDate` (date comptable)
- Utiliser `valueDate` pour matching (plus fiable)
- Log écarts entre valueDate et importDate pour audit

---

## 8. Actions manuelles — UI et workflows

### 8.1 Interface utilisateur proposée

#### Onglet Lettrage (Google Sheets)
```
┌─────────┬────────────┬─────────┬──────────────┬──────────────┬────────────┐
│ Facture │ Montant FA │ Transac │ Montant TXN  │ Score        │ Statut     │
├─────────┼────────────┼─────────┼──────────────┼──────────────┼────────────┤
│ FAC-001 │ 1500.00    │ TXN-100 │ 1500.00      │ 100 (vert)   │ LETTRE     │
│ FAC-002 │ 2300.00    │ TXN-101 │ 2300.00      │ 85 (vert)    │ LETTRE     │
│ FAC-003 │ 1200.00    │ TXN-102 │ 1200.00      │ 75 (orange)  │ A_VERIFIER │
│ FAC-004 │ 900.00     │ -       │ -            │ 0 (rouge)    │ PAS_DE_MATCH
└─────────┴────────────┴─────────┴──────────────┴──────────────┴────────────┘

Colonnes supplémentaires (non visibles par défaut, scroll horizontal) :
│ Écart Montant │ Écart Jours │ Libellé TXN │ Déjà Lettrée │ Date Lettrage │ Notes Jules │
```

#### Dashboard Jules (web UI)
```
RECONCILIATION BANCAIRE — Tableau de Bord

┌─ Filtres ─────────────────────┐
│ Statut : [ Toutes ▼ ]        │
│  ├─ Lettree (N=42)          │
│  ├─ A_verifier (N=5)        │
│  └─ Pas_de_match (N=2)      │
│ Mois : [ Mars 2026 ▼ ]     │
│ Montant min : [ 0 ]        │
└──────────────────────────────┘

RÉSUMÉ
├─ Factures en attente : 5
├─ Montant non-lettré : 8 400€
├─ Transactions orphelines : 2
├─ Dernier lettrage : 12 mars 19h45

ACTIONS NECESSAIRES
┌─────────────────────────────────────────────────────┐
│ ⚠ 5 factures A_VERIFIER (score 50-79)            │
│   [Valider tout]  [Examiner 1 par 1]             │
│                                                  │
│ 🔴 FAC-003 : 1200€ vs TXN-102 (score 75)        │
│    Date OK, montant OK, libellé "Virement"      │
│    [✓ Valider]  [✗ Ignorer]  [+ Autre txn]     │
│                                                  │
│ 🔴 FAC-004 : 900€ — PAS_DE_MATCH                │
│    Aucune transaction <= 5j trouvée             │
│    [+ Forcer match manuel]  [Creer avoir]      │
└─────────────────────────────────────────────────────┘

HISTORIQUE RECENT
├─ ✓ FAC-002 lettrée auto (score 100)
├─ ⚠ FAC-003 en attente (score 75)
├─ ✓ FAC-001 lettrée auto (score 100)
└─ ...
```

### 8.2 Workflow de validation manuelle

**Cas 1 : Jules valide un match A_VERIFIER**

```
Jules voit : "FAC-003 : 1200€ vs TXN-102 : 1200€, score 75"
│
Jules clique : [✓ Valider ce lettrage]
│
Système :
├─ Statut FAC-003 : PAYE → RAPPROCHE
├─ Statut TXN-102 : A_VERIFIER → LETTRE
├─ Onglet Lettrage : score = 75 → flag="VALIDATED_MANUAL"
├─ Log : {facture_id=FAC-003, action="VALIDATED_MANUAL", user=Jules, ts=12-Mar-19h50}
└─ Balances recalculé
```

**Cas 2 : Jules ignore une suggestion**

```
Jules voit : "FAC-003 : 1200€ vs TXN-102 : 1200€, score 75"
│
Jules clique : [✗ Ignorer ce match]
│
Système :
├─ Statut FAC-003 : PAYE → PAS_DE_MATCH (changé de A_VERIFIER)
├─ Statut TXN-102 : A_VERIFIER → ORPHELINE
├─ Onglet Lettrage : score = 75 → flag="IGNORED"
├─ Log : {facture_id=FAC-003, action="IGNORED_SUGGESTION", reason=Jules}
└─ Jules doit chercher autre transaction pour FAC-003
```

**Cas 3 : Jules force un match différent**

```
Jules voit : "FAC-003 : 1200€ — PAS_DE_MATCH"
│
Jules cherche dans liste Transactions
│ "Chercher autre transaction..." dropdown
│ Affiche les 10 dernières transactions non-lettrees
│
Jules sélectionne : TXN-200 (1200€, "Virement URSSAF", 10 jours avant)
│
Système :
├─ Score auto = 50 (montant) + 5 (date J-10) + 20 = 75
├─ Demande confirmation : "Score 75, êtes-vous sûr ?"
├─ [✓ Oui, forcer]  [✗ Non, chercher autre]
│
Si YES :
├─ Statut FAC-003 : PAS_DE_MATCH → RAPPROCHE
├─ Statut TXN-200 : ORPHELINE → LETTRE
├─ Onglet Lettrage : flag="FORCED_MANUAL"
├─ Log : {facture_id=FAC-003, transaction_id=TXN-200, action="FORCED_MATCH", user=Jules}
└─ Balances recalculé
```

**Cas 4 : Jules crée une note de crédit (paiement partiel)**

```
Jules voit : "FAC-003 : 1200€ vs TXN-102 : 600€, score 75 (partial)"
│
Jules clique : [Créer avoir pour différence]
│
Système propose :
├─ Facture d'origine : FAC-003 (1200€)
├─ Montant virement : 600€
├─ Montant avoir : 600€ (1200 - 600)
│
Jules confirme :
├─ Crée FAC-003-AV (avoir 600€) automatiquement
├─ Lettrer FAC-003 vs TXN-102 pour 600€ (partial lettrage)
├─ Statut FAC-003 : RAPPROCHE_PARTIAL (nouveau)
├─ Statut FAC-003-AV : BROUILLON (Jules peut rejustifier ou annuler)
└─ Log : {facture_id=FAC-003, action="PARTIAL_WITH_AVOIR", avoir_id=FAC-003-AV}
```

### 8.3 Trace d'audit

```python
class LettragAuditLog(BaseModel):
    """Chaque action de lettrage est enregistrée pour audit."""

    id: str
    timestamp: datetime
    user: str  # "SYSTEM" ou "Jules"
    facture_id: str
    transaction_id: Optional[str]
    action: Literal[
        "AUTO",           # Lettrage automatique (score >= 80)
        "VALIDATED_MANUAL",  # Jules a validé (score 50-79)
        "IGNORED_SUGGESTION",  # Jules a ignoré
        "FORCED_MATCH",   # Jules a forcé un match différent
        "PARTIAL_WITH_AVOIR",  # Créé avoir pour différence
        "DOUBLON_DETECTED",  # Doublon détecté système
        "CONFLICT_RESOLVED"   # Conflit résolu
    ]
    score_before: int
    score_after: int
    status_before: str
    status_after: str
    notes: Optional[str]

    class Config:
        # Sauvegarder dans onglet "Audit" de Sheets
        sheet_range = "Audit!A:K"
```

---

## 9. Intégration système : dépendances et timeline

### 9.1 Dépendances fonctionnelles

```
Phase 1 (MVP)
├─ ✓ API URSSAF (creation factures)
├─ ✓ Polling statuts URSSAF (4h)
└─ ✓ Google Sheets storage

Phase 2 (Cette spec)
├─ ✓ Swan API GraphQL (récupération transactions)
├─ ✓ BankReconciliation Service (matching algo)
├─ ✓ Onglet Lettrage (Sheets avec formules)
└─ ✓ Dashboard Jules (web UI pour validations)

Phase 3+
├─ Google Sheets auto-sync (formules complexes)
├─ Multi-intervenants (partage lettrage)
└─ Export comptable (fichier rapprochement)
```

### 9.2 Cron et timing

```
# Toutes les 4 heures (00h, 04h, 08h, 12h, 16h, 20h)
cron:
  job: "sap reconcile"
  schedule: "0 */4 * * *"
  timeout: "15 min"
  action:
    1. Import Swan transactions (30 derniers jours)
    2. Lance algorithme matching pour factures PAYE
    3. Applique lettres auto (score >= 80)
    4. Crée suggestions (50 <= score < 80)
    5. Notifie Jules si A_VERIFIER >= 5
    6. Recalcule Balances

# Rappel quotidien (09h)
cron:
  job: "sap recall-pending"
  schedule: "0 9 * * *"
  timeout: "5 min"
  action:
    1. Compte factures PAYE sans lettrage > 7 jours
    2. Envoie reminder Jules : "X factures non-rapprochees"
    3. Lien vers dashboard Lettrage

# Audit mensuel (1er du mois, 23h)
cron:
  job: "sap audit-reconciliation"
  schedule: "0 23 1 * *"
  timeout: "20 min"
  action:
    1. Vérifie solde Sheets = solde Swan (tolerance +/- 0.01€)
    2. Exporte rapport audit Lettrage
    3. Marque toutes les transactions comme "RECONCILED" si OK
```

### 9.3 Monitoring et alertes

```
Métrique : Taux de lettrage automatique
├─ Objectif : >= 90% (score >= 80)
├─ Threshold alerte : < 80%
├─ Action : investigate (changement pattern transactions Swan ?)

Métrique : Montant non-lettré par mois
├─ Seuil critique : > 10% du CA mensuel
├─ Action : Jules en avertissement email

Métrique : Temps resolution A_VERIFIER
├─ Objectif : < 1 jour (Jules traite rapidement)
├─ Seuil alerte : > 3 jours
├─ Action : Email Jules "X suggestions oubliées"

Métrique : Erreurs API Swan
├─ Seuil critique : > 5 erreurs par jour
├─ Action : log + alerter support
```

---

## 10. Pseudo-code complet (BankReconciliation Service)

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Literal
from enum import Enum
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ============================================================================
# TYPES & ENUMS
# ============================================================================

class LettragStatus(str, Enum):
    LETTRE = "LETTRE"
    A_VERIFIER = "A_VERIFIER"
    PAS_DE_MATCH = "PAS_DE_MATCH"
    DOUBLON = "DOUBLON"
    PARTIAL = "PARTIAL"

class MatchingAction(str, Enum):
    AUTO = "AUTO"
    VALIDATED_MANUAL = "VALIDATED_MANUAL"
    IGNORED_SUGGESTION = "IGNORED_SUGGESTION"
    FORCED_MATCH = "FORCED_MATCH"

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class Transaction:
    """Représente une transaction bancaire Swan importée."""
    id: str
    montant: float
    devise: str = "EUR"
    date_valeur: date = field(default_factory=date.today)
    date_comptable: date = field(default_factory=date.today)
    libelle: str = ""
    counterparty: str = ""
    status: str = "BOOKED"

    def is_credit(self) -> bool:
        """Vérifier que c'est un crédit (pas débit)."""
        return self.montant > 0

    def is_urssaf(self) -> bool:
        """Vérifier que le libellé contient 'URSSAF'."""
        return "URSSAF" in self.libelle.upper()

@dataclass
class Facture:
    """Facture interne."""
    id: str
    montant_total: float
    date_soumis: date
    statut: str  # PAYE, EN_ATTENTE, etc.
    client_nom: str = ""

    def is_payable(self) -> bool:
        """Facture eligible au lettrage."""
        return self.statut == "PAYE"

@dataclass
class MatchResult:
    """Résultat d'un matching facture ↔ transaction."""
    facture_id: str
    transaction_id: Optional[str]
    score: int = 0
    status: LettragStatus = LettragStatus.PAS_DE_MATCH

    def is_auto_letter(self) -> bool:
        return self.score >= 80

    def requires_validation(self) -> bool:
        return 50 <= self.score < 80

# ============================================================================
# MATCHING ALGORITHM
# ============================================================================

class BankReconciliationService:

    MONTANT_EXACT_SCORE = 50
    MONTANT_PARTIAL_SCORE = 25

    DATE_IDEAL_SCORE = 30
    DATE_SLIGHT_DELAY_SCORE = 15
    DATE_ANTICIPATE_SCORE = 5

    LIBELLE_URSSAF_SCORE = 20
    LIBELLE_GENERIC_SCORE = 10

    SCORE_THRESHOLD_AUTO = 80
    SCORE_THRESHOLD_SUGGEST = 50

    WINDOW_DAYS = 5  # ±5 jours autour de la date de soumis

    def __init__(self, swan_client, sheets_adapter):
        self.swan_client = swan_client
        self.sheets = sheets_adapter

    async def reconcile_all(self) -> dict:
        """
        Lance le processus de lettrage complet.
        """
        logger.info("Starting bank reconciliation")

        # Étape 1 : Importer transactions Swan
        transactions = await self.import_swan_transactions()
        logger.info(f"Imported {len(transactions)} transactions from Swan")

        # Étape 2 : Récupérer factures PAYE
        factures_paye = self.get_factures_with_status("PAYE")
        logger.info(f"Found {len(factures_paye)} invoices with PAYE status")

        # Étape 3 : Matcher chaque facture
        results = []
        for facture in factures_paye:
            match = self.find_best_match(facture, transactions)
            results.append(match)

        # Étape 4 : Sauvegarder résultats
        self.save_matching_results(results)

        # Étape 5 : Recalculer balances
        self.update_balance_sheet()

        logger.info(f"Reconciliation completed: {len(results)} matches processed")
        return {
            "total_processed": len(factures_paye),
            "auto_lettered": sum(1 for r in results if r.is_auto_letter()),
            "to_verify": sum(1 for r in results if r.requires_validation()),
            "no_match": sum(1 for r in results if r.status == LettragStatus.PAS_DE_MATCH)
        }

    async def import_swan_transactions(self) -> List[Transaction]:
        """Récupère les transactions Swan des 30 derniers jours."""
        account_id = self.sheets.get_swan_account_id()

        try:
            transactions = await self.swan_client.get_transactions(
                account_id=account_id,
                days_back=30
            )
        except Exception as e:
            logger.error(f"Swan import failed: {e}", exc_info=True)
            transactions = []

        # Filter : crédits URSSAF uniquement
        filtered = [
            t for t in transactions
            if t.is_credit() and t.is_urssaf()
        ]

        return filtered

    def get_factures_with_status(self, status: str) -> List[Facture]:
        """Récupère les factures avec le statut donné."""
        return self.sheets.get_factures_by_status(status)

    def find_best_match(
        self,
        facture: Facture,
        transactions: List[Transaction]
    ) -> MatchResult:
        """
        Trouve le meilleur match pour une facture donnée.
        """
        best_match = None
        best_score = 0

        # Fenêtre de recherche
        window_start = facture.date_soumis - timedelta(days=self.WINDOW_DAYS)
        window_end = facture.date_soumis + timedelta(days=self.WINDOW_DAYS)

        for txn in transactions:
            # Vérifier que la transaction est dans la fenêtre
            if not (window_start <= txn.date_valeur <= window_end):
                continue

            # Calculer le score
            score = self.compute_score(facture, txn)

            if score > best_score:
                best_score = score
                best_match = txn

        # Créer le résultat
        if best_match is None:
            result = MatchResult(
                facture_id=facture.id,
                transaction_id=None,
                score=0,
                status=LettragStatus.PAS_DE_MATCH
            )
        elif best_score >= self.SCORE_THRESHOLD_AUTO:
            result = MatchResult(
                facture_id=facture.id,
                transaction_id=best_match.id,
                score=best_score,
                status=LettragStatus.LETTRE
            )
        elif best_score >= self.SCORE_THRESHOLD_SUGGEST:
            result = MatchResult(
                facture_id=facture.id,
                transaction_id=best_match.id,
                score=best_score,
                status=LettragStatus.A_VERIFIER
            )
        else:
            result = MatchResult(
                facture_id=facture.id,
                transaction_id=None,
                score=0,
                status=LettragStatus.PAS_DE_MATCH
            )

        return result

    def compute_score(self, facture: Facture, txn: Transaction) -> int:
        """
        Calcule le score de confiance pour un match facture ↔ transaction.
        """
        score = 0

        # --- CRITÈRE MONTANT (50 points max) ---
        if txn.montant == facture.montant_total:
            score += self.MONTANT_EXACT_SCORE
        elif txn.montant == facture.montant_total * 0.5:
            score += self.MONTANT_PARTIAL_SCORE
        else:
            # Montants ne correspondent pas → reject automatique
            return 0

        # --- CRITÈRE DATE (30 points max) ---
        days_diff = (txn.date_valeur - facture.date_soumis).days

        if days_diff < -self.WINDOW_DAYS or days_diff > self.WINDOW_DAYS:
            # Hors fenêtre → reject
            return 0
        elif 0 <= days_diff <= 3:
            # Délai normal
            score += self.DATE_IDEAL_SCORE
        elif days_diff == 4 or days_diff == 5:
            # Légèrement retardé
            score += self.DATE_SLIGHT_DELAY_SCORE
        elif -5 <= days_diff < 0:
            # Anticipé
            score += self.DATE_ANTICIPATE_SCORE

        # --- CRITÈRE LIBELLÉ (20 points max) ---
        libelle_lower = txn.libelle.lower()
        if "urssaf" in libelle_lower:
            score += self.LIBELLE_URSSAF_SCORE
        elif "paiement" in libelle_lower or "virement" in libelle_lower:
            score += self.LIBELLE_GENERIC_SCORE
        else:
            # Pas de libellé reconnu → reject
            return 0

        return min(score, 100)

    def save_matching_results(self, results: List[MatchResult]) -> None:
        """Sauvegarde les résultats de matching dans Sheets."""
        for result in results:
            row_data = {
                "facture_id": result.facture_id,
                "transaction_id": result.transaction_id or "",
                "score_confiance": result.score,
                "statut_lettrage": result.status.value,
                "date_lettrage": datetime.now().isoformat(),
                "action": "AUTO" if result.status == LettragStatus.LETTRE else "SUGGESTED"
            }
            self.sheets.append_to_lettrage(row_data)

    def update_balance_sheet(self) -> None:
        """Recalcule l'onglet Balances."""
        # Récupérer les factures lettrees et les montants
        total_lettre = self.sheets.sum_factures_by_status("LETTRE")
        total_a_verifier = self.sheets.sum_factures_by_status("A_VERIFIER")
        total_pas_match = self.sheets.sum_factures_by_status("PAS_DE_MATCH")

        # Mettre à jour les lignes de synthèse
        balances = {
            "month": datetime.now().strftime("%Y-%m"),
            "total_facturé": self.sheets.sum_all_factures(),
            "total_lettré": total_lettre,
            "total_à_vérifier": total_a_verifier,
            "total_non_lettré": total_pas_match,
            "taux_lettrage": (total_lettre / self.sheets.sum_all_factures() * 100)
                            if self.sheets.sum_all_factures() > 0 else 0
        }
        self.sheets.update_balances(balances)

# ============================================================================
# VALIDATION MANUELLE
# ============================================================================

class ManualValidationHandler:
    """Gère les actions manuelles de Jules (validation, ignore, force)."""

    def __init__(self, bank_recon: BankReconciliationService):
        self.bank_recon = bank_recon

    def validate_suggestion(self, facture_id: str, transaction_id: str) -> None:
        """Jules confirme un match A_VERIFIER."""
        # Mettre à jour Sheets
        self.bank_recon.sheets.update_lettrage_status(
            facture_id, transaction_id, LettragStatus.LETTRE,
            action=MatchingAction.VALIDATED_MANUAL
        )
        # Log audit
        self.log_audit(facture_id, transaction_id, MatchingAction.VALIDATED_MANUAL)

    def ignore_suggestion(self, facture_id: str) -> None:
        """Jules rejette une suggestion."""
        self.bank_recon.sheets.update_lettrage_status(
            facture_id, None, LettragStatus.PAS_DE_MATCH,
            action=MatchingAction.IGNORED_SUGGESTION
        )
        self.log_audit(facture_id, None, MatchingAction.IGNORED_SUGGESTION)

    def force_match(self, facture_id: str, transaction_id: str) -> None:
        """Jules force un match avec une autre transaction."""
        self.bank_recon.sheets.update_lettrage_status(
            facture_id, transaction_id, LettragStatus.LETTRE,
            action=MatchingAction.FORCED_MATCH
        )
        self.log_audit(facture_id, transaction_id, MatchingAction.FORCED_MATCH)

    def log_audit(self, facture_id: str, transaction_id: Optional[str],
                  action: MatchingAction) -> None:
        """Enregistre l'action dans l'onglet Audit."""
        audit_row = {
            "timestamp": datetime.now().isoformat(),
            "user": "Jules",
            "facture_id": facture_id,
            "transaction_id": transaction_id or "",
            "action": action.value,
            "notes": ""
        }
        self.bank_recon.sheets.append_to_audit(audit_row)
```

---

## 11. Summary & Checklist d'implémentation

### Fonctionnalités clés

- [x] Import automatique transactions Swan (GraphQL, pagination)
- [x] Algorithme scoring à 3 critères (montant, date, libellé)
- [x] Lettrage auto pour score >= 80
- [x] Suggestions pour 50 <= score < 80
- [x] PAS_DE_MATCH pour score < 50
- [x] UI dashboard Jules (validation manuelle)
- [x] Cas limites (paiement partiel, doublon, fusion)
- [x] Trace d'audit complète
- [x] Onglet Lettrage & Balances (Sheets)
- [x] Cron quotidienne + alertes

### Fichiers à créer/modifier

| Fichier | Type | Contenu |
|---------|------|---------|
| `app/services/bank_reconciliation.py` | Feature | BankReconciliationService + matching |
| `app/clients/swan_client.py` | Integration | SwanClient GraphQL |
| `app/routers/reconciliation.py` | API | Endpoints valider/ignorer/forcer |
| `app/sheets_adapter.py` | Adapter | Append Lettrage, update Balances |
| `app/tasks/cron_reconcile.py` | Cron | Task APScheduler |
| `tests/test_bank_reconciliation.py` | Test | 20+ test cases |

### Next Steps

1. **Implémenter SwanClient** (GraphQL queries, error handling)
2. **Coder BankReconciliationService** (matching algorithm)
3. **Créer endpoints FastAPI** (validate, ignore, force)
4. **Setup cron job** (APScheduler, logging)
5. **Tests unitaires** (happy path, edge cases, erreurs)
6. **Intégration Sheets** (formules, formatage couleurs)
7. **Dashboard UI** (validation form, listing)
8. **Documentation API** (OpenAPI, examples)

---

**Document version**: 1.0
**Auteur**: Sarah, BMAD Product Owner
**Date**: Mars 2026
**Statut**: Specification complète, prête pour Phase 2
