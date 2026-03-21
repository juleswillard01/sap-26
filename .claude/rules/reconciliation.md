# Rapprochement Bancaire & Lettrage

Source de vérité : `docs/SCHEMAS.html` diagramme 6

## Import Transactions (CDC §3.1)

**Source** : Indy Banking via Playwright headless
- Export CSV → parse → onglet Transactions
- Retry 3x avec backoff exponentiel
- Screenshots erreur dans `io/cache/` (SANS données sensibles — RGPD)
- Dedup par `indy_id` lors de l'import batch
- Transactions IMMUTABLES après import (sauf `facture_id` et `statut_lettrage`)

**Fréquence** :
- Sync quotidien via cron
- `sap reconcile` manuel possible anytime
- Volume estimé : ~400 transactions/an (~33/mois)

---

## Lettrage — Score de Confiance (CDC §3.2)

### Algorithme d'appairage

Pour chaque facture **PAYEE** (statut = PAYE) dans l'onglet Factures :

1. **Fenêtre temporelle** : Filtrer transactions URSSAF dans `date_paiement ± 5 jours`
   - Minimise faux positifs (délai traitement bancaire)
   - Couvre variance calendaire URSSAF → Indy

2. **Critères de scoring** (0-100 pts) :
   - Montant exact (100% montant facture) = **+50 points**
   - Date écart < 3 jours = **+30 points**
   - Libellé contient "URSSAF" = **+20 points**

3. **Résultats** :
   - Score **≥ 80** → `LETTRE_AUTO` (rapprochement automatique)
   - Score **< 80** → `A_VERIFIER` (Jules valide manuellement)
   - Pas de transaction trouvée → `PAS_DE_MATCH` (attendre virement)

### MVP : Lettrage Semi-Automatique

- Le système **propose** des matchs avec score
- Jules **confirme** manuellement dans l'onglet Lettrage
- Pas de lettrage 100% automatique sans confirmation utilisateur
- Surligné en orange (`A_VERIFIER`) et rouge (`PAS_DE_MATCH`) dans le UI

---

## Onglet Lettrage (formules Sheets)

**Colonnes** (lecture seule — formules) :
- `facture_id` : clé étrangère vers Factures
- `montant_facture` : =Factures.montant_total
- `txn_id` : indy_id du match trouvé
- `txn_montant` : montant transaction
- `ecart` : =ABS(montant_facture - txn_montant)
- `score_confiance` : 0-100 (calculé par algo scoring)
- `statut` : LETTRE_AUTO / A_VERIFIER / PAS_DE_MATCH

**Écriture** :
- Importée depuis import Transactions (via backend)
- Colonne `facture_id` remplie par matching algo
- Jules peut éditer manuellement si besoin de correction

---

## Onglet Balances (formules Sheets)

**Colonnes** (lecture seule — agrégations mensuelles) :
- `mois` : YYYY-MM
- `nb_factures` : COUNT(Factures où date_fin DANS mois)
- `ca_total` : SUM(Factures.montant_total où date_fin DANS mois)
- `recu_urssaf` : SUM(Transactions.montant où date_import DANS mois ET facture_id NOT NULL)
- `solde` : ca_total - recu_urssaf
- `nb_non_lettrees` : COUNT(Factures où statut ≠ PAYE ET date_fin DANS mois)
- `nb_en_attente` : COUNT(Factures où statut = EN_ATTENTE ET date_fin DANS mois)

**Refresh** : Automatique via changements onglets Factures / Transactions / Lettrage

---

## Règles Opérationnelles

### Architecture : Indy Playwright headless
- **SEULEMENT** Playwright automatise le compte de Jules sur app.indy.fr
- Indy n'a pas d'API publique — pas d'intégration API bancaire possible
- Pas d'accès compte URSSAF direct (données export transactions Indy suffisent)
- AIS (Account Information Services) : non applicable — Indy ne supporte pas les standard bancaires (ex. PSD2)

### Immuabilité transactions
- Après import → colonnes `date_valeur`, `montant`, `libelle` **read-only**
- Colonnes éditables : `facture_id`, `statut_lettrage`
- Audit : logs d'édition (timestamp + ancien/nouveau valeur)

### Gestion des doublons
- Dedup lors du parsing CSV (clé `indy_id`)
- Si même `indy_id` + même `montant` + même `date_valeur` → skip

### Fenêtre de lettrage
- ±5 jours : empirique, ajustable si délais URSSAF varient
- Exemple : facture 15/01, lettrer transactions 10-20/01

### Score confiance détails
```
Cas A : Montant 100€, facture 100€, date écart 1j, libellé "VIREMENT URSSAF"
  → 50 (montant) + 30 (date) + 20 (libellé) = 100 → LETTRE_AUTO

Cas B : Montant 100€, facture 100€, date écart 1j, libellé "Virement client"
  → 50 (montant) + 30 (date) + 0 (pas URSSAF) = 80 → LETTRE_AUTO (seuil atteint)

Cas C : Montant 99€, facture 100€, date écart 6j, libellé "URSSAF"
  → 0 (montant ≠) + 0 (date > 3j) + 20 (libellé) = 20 → A_VERIFIER

Cas D : Aucune transaction dans ±5j
  → PAS_DE_MATCH
```

### Lettrage manuel (Jules)
1. Ouvre onglet Lettrage
2. Voit propositions avec scores
3. Pour statuts A_VERIFIER : valide ou corrige `facture_id` / `txn_id`
4. Sauve → backend valide cohérence et update Balances

---

## Intégration avec Machine à États Facture

**Transition PAYE → RAPPROCHE** :
- Facture statut = PAYE + LETTRE_AUTO en onglet Lettrage
- OU Jules confirme lettrage manuel (A_VERIFIER) → statut = RAPPROCHE

**Factures sans match** :
- Restent PAYE (pas RAPPROCHE)
- À suivre manuellement si virement en retard

---

## RGPD & Sécurité

### Données sensibles
- Screenshots Indy : stockés dans `io/cache/` avec **PAS de données bancaires visibles**
- CSV parsé : aucun numéro de compte, BIC/IBAN strippés
- Transactions : libellés peuvent être anonymisés en prod

### Conformité
- Logs d'import : qui, quand, combien transactions
- Logs édition onglet : qui a changé facture_id le DD/MM
- Pas de transmission URSSAF/Indy vers tiers
- Rétention : transactions 3 ans minimum (normes fiscales)

---

## Changements Futurs (Phase 2+)

- Ajustement seuil score si taux de A_VERIFIER > 30%
- Support virements multiples (facture = N transactions)
- Lettrage 100% auto après N mois de confiance établie
- Rematch rétrospectif si virement arrive tardivement
