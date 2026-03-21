# Schéma Google Sheets — 8 Onglets

**Source de vérité** : `docs/SCHEMAS.html` diagramme 5 + `docs/CDC.md` §1.1

---

## Onglets Data Brute (lectures/écritures)

### 1. Clients

Répertoire des clients (élèves particuliers).

| Colonne | Type | Requis | Contraintes |
|---------|------|--------|-------------|
| client_id | str | ✅ | Unique, format `C###` |
| nom | str | ✅ | Non vide |
| prenom | str | ✅ | Non vide |
| email | str | ✅ | Format email valide |
| telephone | str | ❌ | Format `+33 9 XX XX XX XX` ou vide |
| adresse | str | ❌ | Adresse postale complète |
| code_postal | str | ❌ | 5 chiffres ou vide |
| ville | str | ❌ | Commune française |
| urssaf_id | str | ❌ | ID technique URSSAF après inscription |
| statut_urssaf | str | ✅ | `EN_ATTENTE`, `INSCRIT`, `ERREUR`, `INACTIF` |
| date_inscription | date | ❌ | ISO 8601 (YYYY-MM-DD) |
| actif | bool | ✅ | `TRUE` ou `FALSE` |

**Règles métier** :
- `urssaf_id` = NULL jusqu'à inscription URSSAF réussie
- `statut_urssaf = EN_ATTENTE` au moment de la création
- `date_inscription` = premier cours avec ce client
- `actif` sert à archiver sans supprimer

---

### 2. Factures

Factures émises, statuts, et suivi complet du cycle de vie.

| Colonne | Type | Requis | Contraintes |
|---------|------|--------|-------------|
| facture_id | str | ✅ | Unique, format `F###` |
| client_id | str | ✅ | FK → `Clients.client_id` |
| type_unite | str | ✅ | `HEURE` ou `FORFAIT` |
| nature_code | str | ✅ | `COURS_PARTICULIERS` (extensible) |
| quantite | float | ✅ | > 0, ex: `2.5` pour 2h30 |
| montant_unitaire | float | ✅ | > 0, montant HT par unité |
| montant_total | float | calc | Formule : `quantite × montant_unitaire` |
| date_debut | date | ✅ | ISO 8601, jour du premier cours |
| date_fin | date | ✅ | ISO 8601, ≥ `date_debut` |
| description | str | ❌ | Libellé court (ex: "Maths 1er S semaines 1-4") |
| statut | str | ✅ | 11 états (voir machine à états §2) |
| urssaf_demande_id | str | ❌ | ID URSSAF reçu après soumission |
| date_soumission | date | ❌ | ISO 8601, enregistrée au `SOUMIS` |
| date_validation | date | ❌ | ISO 8601, client a validé dans URSSAF |
| date_paiement | date | ❌ | ISO 8601, URSSAF a versé les 100% |
| date_rapprochement | date | ❌ | ISO 8601, lettrage auto confirmé |
| pdf_drive_id | str | ❌ | ID Google Drive du PDF généré |

**Règles métier** :
- État initial = `BROUILLON`
- `date_soumission` remplie au passage à `SOUMIS`
- `date_validation` = timestamp client valid dans URSSAF
- `date_paiement` = transaction Indy reçue
- `date_rapprochement` = match auto dans onglet Lettrage (score ≥ 80)

---

### 3. Transactions

Import des transactions bancaires Indy + lettrage.

| Colonne | Type | Requis | Contraintes |
|---------|------|--------|-------------|
| transaction_id | str | ✅ | Unique, format `TRX-###` (généré à l'import) |
| indy_id | str | ✅ | ID transaction Indy Banking |
| date_valeur | date | ✅ | ISO 8601, date du virement |
| montant | float | ✅ | > 0, en euros |
| libelle | str | ✅ | Texte complet de la transaction |
| type | str | ❌ | `credit` ou `debit` (optionnel si déductible du signe montant) |
| source | str | ✅ | `indy` (pour extensibilité) |
| facture_id | str | ❌ | FK → `Factures.facture_id` si lettré |
| statut_lettrage | str | ✅ | `NON_LETTRE`, `LETTRE_AUTO`, `A_VERIFIER`, `PAS_DE_MATCH` |
| date_import | date | ✅ | ISO 8601, moment de l'import Playwright |

**Règles métier** :
- `transaction_id` auto-généré lors du batch import
- `statut_lettrage = NON_LETTRE` initialement
- Populated par onglet Lettrage (formules) après matching
- `facture_id` remplie manuellement ou par formule si score ≥ 80

---

## Onglets Calculés (lectures seules — formules Sheets)

### 4. Lettrage

Matching automatique factures ↔ transactions bancaires.

**Source** : Factures (data brute) + Transactions (data brute)

| Colonne | Type | Logique |
|---------|------|---------|
| facture_id | str | FK de la facture en cours de matching |
| montant_facture | float | Montant total de la facture |
| txn_id | str | ID transaction candidate |
| txn_montant | float | Montant de la transaction |
| ecart | float | Valeur absolue : `ABS(montant_facture - txn_montant)` |
| score_confiance | int | Somme des critères (voir détail ci-dessous) |
| statut | str | `LETTRE_AUTO`, `A_VERIFIER`, ou `PAS_DE_MATCH` |

**Algorithme de score** (pour chaque facture PAYEE dans fenêtre ± 5 jours) :
```
Score = 0
Si montant exact match → +50 pts
Si date_valeur - date_paiement ≤ 3 jours → +30 pts
Si libelle contient "URSSAF" ou client.nom → +20 pts

Résultat :
  ≥ 80 → LETTRE_AUTO (auto-match, facture_id écrite dans Transactions)
  < 80 → A_VERIFIER (surligné orange, Jules confirme manuellement)
  Pas de transaction → PAS_DE_MATCH (surligné rouge, attend virement URSSAF)
```

**Formules Sheets** :
- XLOOKUP + SUMIFS pour fenêtre temporelle
- FILTER pour transactions non-lettrées
- IF nesting pour score_confiance
- Plage dynamic : A:F (factures) ↔ A:E (transactions)

---

### 5. Balances

Agrégation mensuelle : CA, solde, lettrage.

**Source** : Factures (statut = PAYE) + Transactions + Lettrage

| Colonne | Type | Logique |
|---------|------|---------|
| mois | date | Première du mois (YYYY-MM-01) |
| nb_factures | int | COUNT factures statut=PAYE du mois |
| ca_total | float | SUM montant_total du mois |
| recu_urssaf | float | SUM montant de transactions du mois |
| solde | float | `recu_urssaf - ca_total` (diff si retenue client) |
| nb_non_lettrees | int | COUNT factures statut=PAYE non lettrees |
| nb_en_attente | int | COUNT factures statut=EN_ATTENTE |

**Mises à jour** :
- Auto-recalc dès qu'une facture passe à PAYE ou RAPPROCHE
- Plage dynamic : agrégation par mois (EOMONTH)

---

### 6. Metrics NOVA

Reporting trimestriel pour déclarations fiscales.

**Source** : Factures + Transactions

| Colonne | Type | Logique |
|---------|------|---------|
| trimestre | str | Ex: `2026-Q1` |
| nb_intervenants | int | Toujours `1` (Jules seul) |
| heures_effectuees | float | SUM quantite WHERE type_unite=HEURE |
| nb_particuliers | int | COUNT DISTINCT client_id (factures du trim) |
| ca_trimestre | float | SUM montant_total du trimestre |
| deadline_saisie | date | 15 du mois suivant clôture trim |

**Mises à jour** :
- Générées fin trimestre (auto ou manual trigger)
- Extensible pour multi-intervenants futurs

---

### 7. Cotisations

Charges sociales mensuelles (micro-social 25.8%).

**Source** : Factures (statut = PAYE)

| Colonne | Type | Logique |
|---------|------|---------|
| mois | date | Première du mois |
| ca_encaisse | float | SUM montant transactions du mois |
| taux_charges | float | `25.8%` (constant) |
| montant_charges | float | `ca_encaisse × 0.258` |
| cumul_ca | float | SUM CA depuis début année |
| net_apres_charges | float | `ca_encaisse - montant_charges` |
| date_limite | date | 15 du mois suivant (versement obligatoire) |

**Règles métier** :
- Appliqué qu'après réception URSSAF (PAYE)
- Simulation seuil micro (24,000€/an) : si dépassement → passage réel micro
- Cumul YTD pour tracking versement libératoire

---

### 8. Fiscal IR

Simulation impôt annuel (abattement BNC + tranches IR).

**Source** : Factures (année complète) + Cotisations

| Colonne | Type | Logique |
|---------|------|---------|
| revenu_apprentissage | float | CA annuel encaissé |
| seuil_exo | float | Seuil micro 24,000€ |
| ca_micro | float | MIN(revenu, seuil_exo) |
| abattement_bnc | float | `ca_micro × 34%` (abattement BNC) |
| revenu_imposable | float | `ca_micro - abattement_bnc` |
| tranches_ir | str | Détail par tranche (ex: "0-10064€ @ 0%, 10064-27748€ @ 11%...") |
| taux_marginal | float | Taux tranche max atteinte (ex: `41%`) |
| simulation_vl | float | Versement libératoire : `revenu_imposable × 2.2%` (optionnel) |

**Règles métier** :
- Abattement BNC = 34% (forfaitaire, régime micro-BIC)
- Tranches IR 2026 (à actualiser chaque année)
- Simulation VL = alternative au micro-IR classique
- Colonne informative pour déclaration fiscale

---

## Règles d'Accès et d'Utilisation

### Permissions

| Onglet | SheetsAdapter | Jules (UI) | Formules |
|--------|---------------|-----------|----------|
| Clients | READ/WRITE | READ/WRITE | — |
| Factures | READ/WRITE | READ/WRITE | montant_total |
| Transactions | READ/WRITE | READ ONLY | — |
| Lettrage | READ ONLY | READ ONLY | ✅ (full) |
| Balances | READ ONLY | READ/WRITE (manual) | ✅ (full) |
| Metrics NOVA | READ ONLY | READ/WRITE (manual) | ✅ (full) |
| Cotisations | READ ONLY | READ/WRITE (manual) | ✅ (full) |
| Fiscal IR | READ ONLY | READ/WRITE (manual) | ✅ (full) |

### Performance et Throttling

- **Cache mémoire** : 30 secondes sur reads identiques (clé : onglet + range)
- **Rate limit** : 60 req/min/user (API Google Sheets v4)
- **Batch reads** : `get_all_records()` uniquement (jamais cellule par cellule)
- **Batch writes** :
  - `append_rows(data)` pour INSERT lignes nouvelles
  - `update(range, data)` pour UPDATE existants
  - **JAMAIS** `update_cell()` (interdit pour perf)

### Stratégie d'Import

1. **Lecture initiale** : `get_all_records('Clients')` → cache 30s
2. **Écriture** : batch `append_rows()` pour 10+ lignes nouvelles
3. **Modification** : XLOOKUP range existant → `update(A2:L100, new_data)`
4. **Retry** : exponential backoff 3× sur 429 (rate limited)

### Intégrité des Données

- **Clés primaires** : non-nullable, validées côté Sheets (data validation)
- **Clés étrangères** : FK validation côté app (avant write)
- **Contraintes de date** : ISO 8601 strictement (`YYYY-MM-DD`)
- **Montants** : floats, toujours > 0 sauf solde (peut être négatif)
- **États** : enum fermé (11 états facture, 4 statuts lettrage, etc.)

---

## Flux de Synchronisation

### SheetsAdapter : Lecture

```python
# Cache TTL 30s
data = sheets_adapter.get_all_records('Factures')
# → Dict[facture_id, {client_id, statut, montant, ...}]
```

### SheetsAdapter : Écriture

```python
# Ajout de nouvelles factures
sheets_adapter.append_rows('Factures', [
  {facture_id: 'F001', client_id: 'C123', ...},
  {facture_id: 'F002', client_id: 'C456', ...}
])

# Mise à jour statuts existants
sheets_adapter.update('Factures', 'A2:L20', updated_data)
```

### Workflow Complet

1. Jules crée facture → INSERT ligne `Factures` (BROUILLON)
2. Soumission URSSAF → UPDATE `statut=SOUMIS`, `urssaf_demande_id=...`
3. Polling 4h → UPDATE `statut=VALIDE` si réponse OK URSSAF
4. Virement reçu → Playwright scrape Indy → INSERT `Transactions`
5. Formule Lettrage → match auto (score ≥ 80) → UPDATE `Transactions.facture_id`
6. Jules valide → UPDATE `Transactions.statut_lettrage=LETTRE`
7. Onglets Balances/Fiscal → recalc auto

---

## Colonnes Calculées (Formules Sheets)

### montant_total (Factures.J)
```
= quantite × montant_unitaire
```

### score_confiance (Lettrage.F)
```
= IF(
    montant_match_exact, 50, 0
  ) + IF(
    date_diff ≤ 3, 30, 0
  ) + IF(
    SEARCH("URSSAF", libelle), 20, 0
  )
```

### statut_lettrage (Lettrage.G)
```
= IF(score_confiance ≥ 80, "LETTRE_AUTO",
    IF(score_confiance ≥ 1, "A_VERIFIER", "PAS_DE_MATCH"))
```

### ca_total (Balances.D)
```
= SUMIFS(Factures!$J:$J, Factures!$L:$L, "PAYE", Factures!$E:$E, mois)
```

### montant_charges (Cotisations.E)
```
= ca_encaisse × 0.258
```

### revenu_imposable (Fiscal IR.F)
```
= (ca_micro × (1 - 0.34))
```

---

## Checklist d'Implémentation

- [ ] SheetsAdapter peut lire tous les 8 onglets
- [ ] SheetsAdapter peut écrire sur Clients, Factures, Transactions
- [ ] Cache TTL 30s implémenté
- [ ] Rate limiting 60 req/min + retry exponentiel
- [ ] Batch append/update, pas de `update_cell()`
- [ ] Validation FK avant write
- [ ] Formules Lettrage + Balances testées
- [ ] Tests end-to-end : sync + lettrage + export CSV
- [ ] Logging des writes (audit trail)
- [ ] Documentation API SheetsAdapter publique

---

## Références

- **Diagramme complet** : `docs/SCHEMAS.html#donnees`
- **Machine à états** : `docs/CDC.md#2-machine-à-états-facture`
- **Lettrage détaillé** : `docs/CDC.md#3.2-lettrage--score-confiance`
- **SheetsAdapter pattern** : `app/adapters/sheets_adapter.py`
