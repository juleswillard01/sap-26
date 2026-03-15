# Modèle de Données SAP-Facture — Guide Rapide (2 pages)

**Source**: SCHEMAS.html — SCHEMA 5 (15 mars 2026)

---

## Les 8 Onglets Google Sheets

### Data Brute (Éditables)

#### 1. CLIENTS — 4-10 lignes
Qui factures-tu ?

```
client_id | nom    | email          | urssaf_id    | statut_urssaf | actif
----------|--------|----------------|--------------|---------------|-------
CLT-001   | Dupont | j@mail.fr      | id_xyz123    | INSCRIT       | OUI
CLT-002   | Martin | m@mail.fr      | (vide)       | EN_ATTENTE    | OUI
```
- `client_id` : Immuable (créé par app)
- `urssaf_id`, `statut_urssaf` : Maj auto par app (polling URSSAF)
- Éditable : nom, email, téléphone, adresse (par Jules ou app)

#### 2. FACTURES — 15-50 lignes/mois
Les factures qu'elle crée

```
facture_id | client_id | montant_total | date_paiement | statut    | pdf_id
-----------|-----------|---------------|---------------|-----------|----------
FAC-001    | CLT-001   | 350.00 EUR    | 2026-03-05    | RAPPROCHE | file_abc
FAC-002    | CLT-001   | 175.00 EUR    | (vide)        | EN_ATTENTE| file_def
```
- **Cycle de vie** : BROUILLON → SOUMIS → CREE → EN_ATTENTE → VALIDE → PAYE → RAPPROCHE
- Éditable BROUILLON uniquement (montant, quantite, dates)
- Maj auto : statut, urssaf_demande_id, dates suivi (par polling API URSSAF)
- `montant_total = quantite × montant_unitaire` (formule)

#### 3. TRANSACTIONS — 10-30 lignes/mois
Les virements reçus (Swan)

```
transaction_id | montant | date_valeur | libelle           | facture_id | statut_lettrage
---------------|---------|-------------|-------------------|------------|------------------
TXN-001        | 350.00  | 2026-03-05  | VIR URSSAF DUE001 | FAC-001    | LETTREE
TXN-002        | 175.00  | 2026-03-21  | VIR URSSAF DUE002 |            | A_VERIFIER
```
- Import auto depuis Swan (sauf édition manuelle en A_VERIFIER)
- `facture_id` : Remplie par lettrage automatique (score >= 80)

---

### Calculées — Formules Seules (Lecture Seule)

#### 4. LETTRAGE — Matching Auto Factures ↔ Virements

**Logique** : Pour chaque facture PAYE, chercher 1 transaction dans fenêtre ±5j

```
Score Confiance =
  (montant exact → +50) +
  (date gap <= 0j → +30 ; <= 5j → +5) +
  (libelle ~ "URSSAF" → +20)

Résultat :
  Score >= 80 → AUTO (match confirmé, facture_id remplie dans Transactions)
  50-79 → A_VERIFIER (surligner orange, Jules confirme)
  < 50 → PAS_DE_MATCH (surligner rouge, attendre virement)
```

#### 5. BALANCES — KPIs Mensuels

```
mois    | nb_factures | ca_encaisse | recu_urssaf | solde  | nb_lettrees | nb_non_lettrees
--------|-------------|------------|-------------|--------|------------|------------------
2026-03 | 3           | 350.00     | 350.00      | 350.00 | 2          | 1
```
Agrégations SUMIF/COUNTIF des 3 onglets brutes + lettrage.

#### 6. METRICS NOVA — Reporting Trimestriel

```
trimestre | nb_intervenants | heures_effectuees | ca_trimestre
----------|-----------------|-------------------|-------------
2026-Q1   | 5               | 120               | 3500.00
```
Pour déclarations NOVA URSSAF (1 ligne/trimestre).

#### 7. COTISATIONS — Charges Mensuelles

```
mois    | ca_encaisse | taux_charges | montant_charges | cumul_ca_annuel | seuil_micro | alerte
--------|-------------|--------------|-----------------|-----------------|-------------|-------
2026-03 | 350.00      | 25.8%        | 90.30           | 1950.00         | 72600.00    | 2.7% OK
```
- Taux URSSAF 25.8% (micro-entrepreneur 2026)
- Alerte si cumul_annuel >= 90% du seuil (72 600 EUR)

#### 8. FISCAL IR — Simulation Impôt Annuel

```
annee | ca_micro_brut | abattement_bnc | revenu_imposable | taux_marginal_ir | impot_estime | simulation_mensuelle
------|---------------|--------------------|--|-------|-----|-----
2026  | 1950.00       | 34%                | 783.60           | 5.5%             | 86.10       | 7.18 EUR/mois
```
- Abattement BNC 34% (auto-entrepreneur)
- Tranches IR 2026 : 0% | 5.5% | 10% | 20% | ...
- `revenu_imposable = CA(1-34%) - charges_sociales`

---

## Flux de Données (Vue Simplifiée)

```
CLIENTS + FACTURES + TRANSACTIONS (DATA BRUTE)
           ↓
        LETTRAGE (matching auto, scoring)
           ↓
    BALANCES (KPIs/soldes mensuels)
    METRICS NOVA (reporting trim)
    COTISATIONS (charges = CA × 25.8%)
    FISCAL IR (simulation IR annuel)

1. Jules crée facture (BROUILLON)
2. App soumet à URSSAF (SOUMIS → CREE)
3. Client valide (EN_ATTENTE → VALIDE)
4. URSSAF vire argent (PAYE)
5. App importe transactions Swan
6. Lettrage auto-match (score >= 80 → AUTO, sinon A_VERIFIER)
7. Balances maj (solde, nb_lettrees, etc.)
```

---

## Protections & Éditions

| Onglet | Éditable ? | Qui ? | Quand ? |
|--------|-----------|-------|--------|
| Clients | OUI | Jules + app | Toujours (sauf client_id, urssaf_id) |
| Factures | OUI | App | BROUILLON uniquement (montant, quantite, dates) |
| Transactions | OUI* | Jules | A_VERIFIER (override manuel si besoin) |
| Lettrage | NON | Formules | Auto (score) ou manuel (statut si < 80) |
| Balances | NON | Formules | SUMIF/COUNTIF auto |
| Metrics NOVA | NON | Formules | Agrégations auto |
| Cotisations | NON | Formules | CA × 25.8% auto |
| Fiscal IR | NON | Formules | Tranches IR auto |

*Uniquement facture_id en A_VERIFIER (Jules confirme match après vérif)

---

## Exemples Numériques

### Cas 1 : Facture Créée → Payée → Lettrée (Jour 5)

```
Jour 1 : Jules crée FAC-001
  Factures.FAC-001 = { montant_total: 350 EUR, statut: BROUILLON }

Jour 1 (+1h) : App soumet URSSAF
  Factures.FAC-001.statut = SOUMIS → CREE

Jour 2 : Client valide portail URSSAF
  Factures.FAC-001.statut = EN_ATTENTE → VALIDE

Jour 5 : URSSAF vire argent
  Factures.FAC-001.statut = PAYE
  Factures.FAC-001.date_paye = 2026-03-05

Jour 5 (+1h) : App importe Swan
  Transactions.TXN-001 = { montant: 350 EUR, date_valeur: 2026-03-05, libelle: "VIR URSSAF" }

Jour 5 (+2h) : Lettrage auto-score
  Score = 50 (exact) + 30 (même jour) + 20 (URSSAF) = 100
  Statut = AUTO
  Transactions.TXN-001.facture_id = FAC-001

Jour 5 (+3h) : Balances maj
  Balances.2026-03 = { ca_encaisse: 350, recu_urssaf: 350, nb_lettrees: 1 }

Résultat : FAC-001.statut = RAPPROCHE ✓ (comptabilité clean)
```

### Cas 2 : Facture sans match initial (délai URSSAF)

```
Jour 8 : FAC-002 = 175 EUR, date_paye = 2026-03-07 (payée depuis 1j)
  Pas de transaction encore
  Lettrage.statut = PAS_DE_MATCH (rouge)

Jour 12 : Virement enfin reçu
  Transactions.TXN-003 = { montant: 175 EUR, date_valeur: 2026-03-12 }
  Score = 50 (montant) + 5 (5j) + 20 (URSSAF) = 75
  75 < 80 → A_VERIFIER (orange, surligner)
  Jules clique "Confirmer" → Transactions.TXN-003.facture_id = FAC-002

Jour 12 : FAC-002.statut = RAPPROCHE ✓ (manuel)
```

### Cas 3 : Calculs Charges + IR (Mars)

```
Balances.2026-03 = { ca_encaisse: 350 EUR }

Cotisations.2026-03 :
  montant_charges = 350 × 25.8% = 90.30 EUR
  cumul_ca_annuel = 1950 EUR (Jan+Fév+Mars)
  cumul_vs_seuil = 1950 / 72600 = 2.7% ✓

Fiscal IR.2026 (annuel) :
  ca_micro_brut = 1950 EUR
  ca_apres_abattement = 1950 × (1 - 34%) = 1287 EUR
  revenu_imposable = 1287 - 503 (charges annuelles) = 784 EUR
  taux_marginal_ir = 5.5% (tranche <= 28k)
  impot_estime_annuel = ~86 EUR
  simulation_mensuelle = 7.18 EUR (si prélèvement mensuel)
```

---

## Volumes

- **Clients** : 4-10 actifs/mois
- **Factures** : 15-50/mois = ~300/an
- **Transactions** : 10-30/mois = ~180/an
- **Lettrage** : 1 ligne/facture PAYE (~12-20/mois)
- **Balances** : 1 ligne/mois (12/an)
- **Metrics** : 1 ligne/trimestre (4/an)
- **Cotisations** : 1 ligne/mois (12/an)
- **Fiscal** : 1 ligne/année (1/an)

**Total Google Sheets** : < 1000 cells/an (quota 10M cells) ✓

---

**Document rapide** : 2 pages, 1600 mots
**Pour la version complète** : Voir `05-data-model.md` (1039 lignes)
**Généré** : 15 mars 2026
