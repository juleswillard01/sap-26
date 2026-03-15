# Modèle de Données SAP-Facture — Synthèse Complète

**Analyse de** : docs/schemas/SCHEMAS.html — SCHEMA 5 ("Modèle de Données — Google Sheets")
**Date** : 15 mars 2026
**Statut** : Version 1.0 — Prêt pour implémentation Phase 1

---

## 1. Vue d'Ensemble (30 secondes)

SAP-Facture = **Google Sheets comme backend de données** avec **8 onglets**

**3 onglets DATA BRUTE** (éditables sous contrôle par l'app)
- **CLIENTS** : Identités + statuts URSSAF
- **FACTURES** : Factures créées avec cycle de vie (BROUILLON → RAPPROCHE)
- **TRANSACTIONS** : Virements reçus depuis Swan

**5 onglets CALCULÉS** (formules Excel/Sheets, lecture seule)
- **LETTRAGE** : Matching automatique factures ↔ virements avec scoring confiance
- **BALANCES** : KPIs comptables par mois
- **METRICS NOVA** : Reporting trimestriel URSSAF
- **COTISATIONS** : Charges sociales mensuelles (25.8% URSSAF)
- **FISCAL IR** : Simulation impôt annuel

---

## 2. Architecture Données (Diagramme Relationnel)

```
┌─────────────────────────────────────────────────────────────┐
│              GOOGLE SHEETS : 8 ONGLETS                      │
└─────────────────────────────────────────────────────────────┘

Entrées (Jules + API URSSAF + Swan)
           ↓
┌─────────────────────────────────────┐
│    DATA BRUTE (3 onglets)           │
├─────────────────────────────────────┤
│ 1. CLIENTS         (4-10 lignes)    │  ← Qui tu factures
│ 2. FACTURES        (15-50 lig/mois) │  ← Tes factures
│ 3. TRANSACTIONS    (10-30 lig/mois) │  ← Virements reçus
└─────────────────────────────────────┘
           ↓ (via formules)
┌─────────────────────────────────────┐
│    CALCULÉ (5 onglets)              │
├─────────────────────────────────────┤
│ 4. LETTRAGE        (auto matching)  │
│ 5. BALANCES        (KPIs mensuels)  │
│ 6. METRICS NOVA    (trim reporting) │
│ 7. COTISATIONS     (charges sociales)│
│ 8. FISCAL IR       (simulation IR)  │
└─────────────────────────────────────┘
           ↓
        Sorties (Dashboard Jules)
```

---

## 3. Détail des 8 Onglets

### ONGLET 1 : CLIENTS (Data Brute)

**Statut** : Éditable (app + Jules)
**Volume** : 4-10 clients actifs
**Clé primaire** : `client_id` (UUID ou CLT-001)

| Colonne | Type | Éditable | Rôle |
|---------|------|----------|------|
| `client_id` | UUID | NON | ID unique (app genère) |
| `nom` | Texte | OUI | Nom client |
| `prenom` | Texte | OUI | Prénom |
| `email` | Email | OUI | Contact |
| `telephone` | Texte | OUI | Mobile/fixe |
| `adresse` | Texte | OUI | Lieu de résidence |
| `code_postal` | Texte | OUI | Code postal FR |
| `ville` | Texte | OUI | Commune |
| `urssaf_id` | Texte | NON | ID retourné URSSAF (API) |
| `statut_urssaf` | Enum | NON | INSCRIT, EN_ATTENTE, ERREUR, SUSPENDU (polling API) |
| `date_inscription` | Date | NON | Quand inscrit (API) |
| `date_maj` | Date | NON | Dernière update (app) |
| `actif` | Booléen | OUI | Client actif ou archivé |

**Clés étrangères** :
- Factures.client_id → Clients.client_id (NOT NULL)

---

### ONGLET 2 : FACTURES (Data Brute)

**Statut** : Éditable (app, limité aux BROUILLON)
**Volume** : 15-50/mois = ~300/an
**Clé primaire** : `facture_id` (UUID ou FAC-2026-001)

| Colonne | Type | Éditable | Rôle |
|---------|------|----------|------|
| `facture_id` | UUID | NON | ID unique (app genère) |
| `client_id` | UUID(FK) | NON | Référence Clients (immuable) |
| `type_unite` | Enum | OUI(BROUILLON) | HEURE, JOUR, FORFAIT, SEANCE |
| `nature_code` | Enum | OUI(BROUILLON) | COURS_PARTICULIER, BABY_SITTING, AIDE_MENAGE (URSSAF) |
| `quantite` | Nombre | OUI(BROUILLON) | Heures/jours/forfaits |
| `montant_unitaire` | EUR | OUI(BROUILLON) | Tarif TTC |
| `montant_total` | EUR | NON | = quantite × montant_unitaire (FORMULE) |
| `date_debut` | Date | OUI(BROUILLON) | Première prestation |
| `date_fin` | Date | OUI(BROUILLON) | Dernière prestation |
| `description` | Texte | OUI(BROUILLON) | Notes libres (objet) |
| `statut` | Enum | NON | BROUILLON, SOUMIS, CREE, EN_ATTENTE, VALIDE, PAYE, RAPPROCHE, ANNULE, ERREUR, REJETE, EXPIRE |
| `urssaf_demande_id` | Texte | NON | ID retourné POST URSSAF (API) |
| `date_creation` | DateTime | NON | Timestamp création (app) |
| `date_soumis` | DateTime | NON | Timestamp soumission URSSAF (polling) |
| `date_cree` | DateTime | NON | Timestamp réponse CREE (polling) |
| `date_valide` | DateTime | NON | Timestamp client valide portail (polling) |
| `date_paye` | DateTime | NON | Timestamp URSSAF vire argent (polling) |
| `pdf_drive_id` | Texte | NON | ID Google Drive PDF généré |
| `pdf_url` | URL | NON | URL public partage PDF |
| `notes_erreur` | Texte | OUI | Messages erreur URSSAF |

**Cycle de vie (Machine à états)** :
```
BROUILLON (créée, modifiable)
    ↓
SOUMIS (envoyée à URSSAF)
    ├→ CREE (URSSAF accepte)
    │   ├→ EN_ATTENTE (email client)
    │   │   ├→ VALIDE (client valide)
    │   │   │   └→ PAYE (URSSAF vire)
    │   │   │       └→ RAPPROCHE (matched) ✓
    │   │   ├→ EXPIRE (48h sans validation)
    │   │   │   └→ BROUILLON (re-soumettre)
    │   │   └→ REJETE (client refuse)
    │   │       └→ BROUILLON
    │   └→ ERREUR (API invalide)
    │       └→ BROUILLON (corriger)
    └→ ANNULE (suppression logique) ✓
```

---

### ONGLET 3 : TRANSACTIONS (Data Brute)

**Statut** : Éditable (app import auto + Jules override si A_VERIFIER)
**Volume** : 10-30/mois = ~180/an
**Clé primaire** : `transaction_id` (UUID ou txn_swan_xyz)

| Colonne | Type | Éditable | Rôle |
|---------|------|----------|------|
| `transaction_id` | UUID | NON | ID unique interne |
| `swan_id` | UUID | NON | ID retourné Swan API |
| `date_valeur` | Date | NON | Date caisse |
| `montant` | EUR | NON | Montant virement reçu |
| `libelle` | Texte | NON | Description bancaire brute |
| `type` | Enum | NON | VIREMENT_RECU, FRAIS, INTERET, PRELEVEMENT |
| `source` | Enum | NON | URSSAF, CLIENT_DIRECT, AUTRE |
| `facture_id` | UUID(FK) | OUI(A_VERIFIER) | Référence facture (remplie par lettrage AUTO si score >= 80) |
| `statut_lettrage` | Enum | NON | LETTREE, A_VERIFIER, PAS_DE_MATCH (maj par lettrage) |
| `score_confiance` | 0-100 | NON | Score confiance matching (formule) |
| `date_import` | DateTime | NON | Timestamp import Swan (app) |

**Clés étrangères** :
- Transactions.facture_id → Factures.facture_id (OPTIONAL)

---

### ONGLET 4 : LETTRAGE (Calculé — Formules)

**Statut** : Lecture seule (formules + override manuel si score < 80)
**Source** : Factures (PAYE) × Transactions (importées)
**Volume** : 1 ligne/facture PAYE
**Logique** : Matching auto avec scoring confiance

| Colonne | Formule | Description |
|---------|---------|-------------|
| `facture_id` | FILTER(Factures, statut=PAYE) | Facture proposée |
| `montant_facture` | =Factures.montant_total | Montant TTC facture |
| `txn_id` | Matching algo | Transaction candidate |
| `txn_montant` | =Transactions.montant | Montant virement |
| `ecart` | =ABS(montant_facture - txn_montant) | Différence |
| `score_confiance` | Voir ci-dessous | Score 0-100 |
| `statut` | AUTO / A_VERIFIER / PAS_DE_MATCH | État matching |

**Scoring Confiance (100 points max)** :

```
Score = 0 (départ)

+ Montant (50 pts)
  50 pts : montant_facture == txn_montant
  25 pts : écart < 1 EUR
  0 pts  : écart > 1 EUR

+ Date (30 pts)
  30 pts : écart date = 0 jours (même jour)
  25 pts : écart date <= 1 jour
  15 pts : écart date <= 3 jours
  5 pts  : écart date <= 5 jours
  0 pts  : écart date > 5 jours

+ Libellé (20 pts)
  20 pts : libelle ~ "URSSAF"
  10 pts : libelle ~ "DUE"
  0 pts  : aucun match

Seuil :
  Score >= 80 → AUTO (confiance haute, match auto-validé)
  50-79       → A_VERIFIER (orange, Jules confirme manuellement)
  < 50        → PAS_DE_MATCH (rouge, attendre virement URSSAF)
```

**Fenêtre matching** : Facture PAYE ± 5 jours

---

### ONGLET 5 : BALANCES (Calculé — Formules)

**Statut** : Lecture seule (agrégations)
**Source** : Factures + Transactions + Lettrage
**Volume** : 1 ligne/mois (12/an)
**Utilisation** : Dashboard KPIs, suivi caisse

| Colonne | Formule | Description |
|---------|---------|-------------|
| `mois` | Manuelle (YYYY-MM) | Période (2026-03, 2026-04, ...) |
| `nb_factures` | COUNTIFS(date_creation mois) | Factures créées |
| `nb_factures_payees` | COUNTIFS(statut=PAYE, date_paye mois) | Factures payées |
| `ca_total` | SUMIFS(montant_total, date_creation mois) | CA encaissable |
| `ca_encaisse` | SUMIFS(montant_total, statut=PAYE, date_paye mois) | CA effectif |
| `recu_urssaf` | SUMIFS(Transactions.montant, source=URSSAF, date_valeur mois) | Virements reçus |
| `solde` | recu_urssaf - frais_bancaires | Disponibilités caisse |
| `nb_lettrees` | COUNTIFS(statut=AUTO ou A_VERIFIER) | Factures matchées |
| `nb_non_lettrees` | COUNTIFS(statut=PAS_DE_MATCH) | Factures sans match |
| `nb_en_attente` | COUNTIFS(Factures.statut=EN_ATTENTE) | En validation URSSAF 48h |

---

### ONGLET 6 : METRICS NOVA (Calculé — Formules)

**Statut** : Lecture seule
**Source** : Factures + Clients
**Volume** : 1 ligne/trimestre (4/an)
**Utilisation** : Déclarations NOVA URSSAF

| Colonne | Formule | Description |
|---------|---------|-------------|
| `trimestre` | Manuelle (YYYY-Qn) | Période (2026-Q1, 2026-Q2, ...) |
| `nb_intervenants` | COUNTA(DISTINCT clients) | Clients uniques |
| `heures_effectuees` | SUMIFS(quantite, type_unite=HEURE) | Total heures |
| `nb_particuliers` | = nb_intervenants | Alias pour NOVA |
| `ca_trimestre` | SUMIFS(montant_total, statut=PAYE, date_paye trim) | CA trimestriel |
| `ca_net_charges` | ca_trimestre × (1 - 25.8%) | CA net charges |
| `deadline_saisie` | DATE fin mois+1 trim | Limite déclaration NOVA |

---

### ONGLET 7 : COTISATIONS (Calculé — Formules)

**Statut** : Lecture seule
**Source** : Balances (ca_encaisse)
**Volume** : 1 ligne/mois (12/an)
**Utilisation** : Budget, provisions charges URSSAF

| Colonne | Formule | Description |
|---------|---------|-------------|
| `mois` | Manuelle (YYYY-MM) | Période |
| `ca_encaisse` | =Balances.ca_encaisse | CA effectivement payé |
| `taux_charges` | 25.8% (constant 2026) | Taux URSSAF micro |
| `montant_charges` | ca_encaisse × 0.258 | Charges dues |
| `cumul_ca_annuel` | SUM(ca_encaisse depuis jan) | Total CA 1er janvier → maintenant |
| `cumul_vs_seuil` | cumul_ca_annuel / 72600 | % utilisation seuil micro |
| `alerte` | IF(cumul_vs_seuil >= 90%, "ALERTE", "OK") | Dépassement? |
| `date_limite` | 15 du mois suivant | Limite paiement cotisations |
| `net_apres_charges` | ca_encaisse - montant_charges | Disponibilités |
| `seuil_micro` | 72600 EUR (constant) | Seuil dépassement régime |

---

### ONGLET 8 : FISCAL IR (Calculé — Formules)

**Statut** : Lecture seule
**Source** : Factures (CA) + Cotisations (charges)
**Volume** : 1 ligne/année (1/an)
**Utilisation** : Prévision impôt, conseils comptables

| Colonne | Formule | Description |
|---------|---------|-------------|
| `annee` | Manuelle (YYYY) | Exercice |
| `revenu_apprentissage` | Input manuel | Revenus bourse/apprentissage (exonérés) |
| `seuil_exoneration` | 19000 EUR (const 2026) | Limite cumulée |
| `ca_micro_brut` | SUMIFS(montant_total, année) | CA brut |
| `abattement_bnc` | 34% (constant) | Abattement BNC auto-entrepreneur |
| `ca_apres_abattement` | ca_micro_brut × (1 - 0.34) | CA net |
| `cotisations_urssaf_annuel` | SUM(montant_charges × 12 mois) | Charges versées |
| `revenu_imposable_ir` | ca_apres_abattement - cotisations_urssaf | Revenu imposable |
| `revenu_net_total` | revenu_apprentissage + revenu_imposable | Base tranches IR |
| `taux_marginal_ir` | Lookup tranches 2026 | Taux IR applicable (5.5%, 10%, 20%, ...) |
| `impot_estime_annuel` | Calcul par tranche | IR estimé 2026 |
| `simulation_mensuelle_lr` | impot_estime / 12 | Prélèvement mensuel |
| `notes_fiscales` | Manuelle | Observations |

**Tranches IR 2026 (France, célibataire)** :
```
Revenu net    | Taux marginal
0-11k         | 0%
11k-28k       | 5.5%
28k-50k       | 10%
50k-75k       | 20%
75k-99.2k     | 30%
99.2k-152.3k  | 41%
> 152.3k      | 45%
```

---

## 4. Relations Entre Onglets

### Flux de Données

```
[CLIENTS] ──────→ [FACTURES] ──────→ [LETTRAGE] ──────→ [BALANCES]
                      ↓                   ↓                   ↓
                   (création)         (matching)         (KPIs mensuels)
                      ↓                   ↓
                  [TRANSACTIONS] ────────────
                   (import Swan)

[FACTURES] ────→ [METRICS NOVA] (reporting trim)
[CLIENTS]   ────→

[FACTURES] ────→ [COTISATIONS] (charges mensuelles)
[BALANCES] ────→

[FACTURES] ────→ [FISCAL IR] (simulation IR annuelle)
[COTISATIONS] ──→
```

### Clés Étrangères & Contraintes

| FK | Table Source | Table Cible | Contrainte |
|----|--------------|-------------|-----------|
| `client_id` | Factures | Clients | NOT NULL, Clients.statut_urssaf=INSCRIT |
| `facture_id` | Transactions | Factures | OPTIONAL, Factures.statut >= PAYE |
| `facture_id` | Lettrage | Factures | Filtre statut=PAYE |

---

## 5. Volumes & Performance

### Taille Attendue

| Onglet | Lignes/mois | Lignes/an | Lignes/5ans | Taille/ligne |
|--------|-----------|---------|-----------|------------|
| CLIENTS | 1-2 (création) | 5-8 | 20-30 | 500 B |
| FACTURES | 15-50 | 180-300 | 900-1500 | 300 B |
| TRANSACTIONS | 10-30 | 120-180 | 600-900 | 250 B |
| LETTRAGE | 12-20 | 144-240 | 720-1200 | 200 B |
| BALANCES | 1 | 12 | 60 | 150 B |
| METRICS NOVA | 1 | 4 | 20 | 100 B |
| COTISATIONS | 1 | 12 | 60 | 150 B |
| FISCAL IR | 0.08 | 1 | 5 | 200 B |

**Total estimé** : < 500 KB (Google Sheets supporte 10M cells)

### Configuration Optimale

- **Archivage** : Factures > 7 ans (limite fiscale) peuvent être archivées
- **Nettoyage** : Transactions LETTREES > 1 an → optionnel
- **Historique** : Conserver BALANCES, METRICS, COTISATIONS, FISCAL (petit volume)

---

## 6. Protections & Éditions

### Matrice Éditable

| Onglet | Éditable ? | Qui ? | Quand ? | Champs modifiables |
|--------|-----------|-------|--------|------------------|
| CLIENTS | OUI | Jules + app | Toujours | nom, prenom, email, telephone, adresse, actif |
| FACTURES | OUI | App | BROUILLON | quantite, montant_unitaire, date_debut, date_fin, description |
| TRANSACTIONS | OUI* | Jules | A_VERIFIER | facture_id (override après vérif) |
| LETTRAGE | NON | Formules | Auto | score_confiance, statut (auto si score >= 80) |
| BALANCES | NON | Formules | Auto | - |
| METRICS NOVA | NON | Formules | Auto | - |
| COTISATIONS | NON | Formules | Auto | - |
| FISCAL IR | NON | Formules | Auto | - |

*Éditable uniquement en cas de besoin (override manuel)

### Validations (App-side)

- `montant_total > 0` et `<= 50 000 EUR`
- `quantite > 0` et `<= 1000`
- `date_fin >= date_debut`
- `client_id` immuable après création
- Deduplication : bloque facture identique dans 5j
- Statuts enum (pas de valeurs arbitraires)

---

## 7. Cas d'Usage Complet

### Scénario 1 : Facture Normale (Créée → Payée → Lettrée)

```
JOUR 1 @ 15:00 : Jules crée facture
  Factures.FAC-001 = {
    client_id: CLT-001, quantite: 10h, montant_unitaire: 35 EUR,
    montant_total: 350 EUR (formule), statut: BROUILLON, date_paiement: (vide)
  }

JOUR 1 @ 15:30 : Jules soumet à URSSAF
  App → POST /demandes-paiement (URSSAF API)
  Factures.FAC-001.statut = SOUMIS
  Factures.FAC-001.urssaf_demande_id = dem_xyz123

JOUR 1 @ 15:35 : App polling (cron 4h)
  App → GET /demandes-paiement/dem_xyz123
  Retour : statut = CREE
  Factures.FAC-001.statut = CREE
  URSSAF envoie email client

JOUR 2 @ 14:00 : Client valide portail URSSAF
  App polling détecte changement
  Factures.FAC-001.statut = EN_ATTENTE → VALIDE
  Factures.FAC-001.date_valide = 2026-03-02 14:20

JOUR 5 @ 09:15 : URSSAF vire argent
  App polling détecte
  Factures.FAC-001.statut = PAYE
  Factures.FAC-001.date_paye = 2026-03-05 09:15

JOUR 5 @ 10:00 : App importe Swan
  App → GET /transactions (Swan GraphQL)
  Transactions.TXN-001 = {
    swan_id: uuid, montant: 350 EUR,
    date_valeur: 2026-03-05, libelle: "VIR URSSAF DUE00001 DUPONT"
  }

JOUR 5 @ 10:15 : Lettrage auto-score
  Lettrage engine :
    Facture FAC-001 (PAYE, date 2026-03-05)
    Transaction TXN-001 (date 2026-03-05)
    Score = 50 (exact) + 30 (0j) + 20 (URSSAF) = 100
    100 >= 80 → AUTO
  Transactions.TXN-001.facture_id = FAC-001
  Transactions.TXN-001.statut_lettrage = LETTREE

JOUR 5 @ 10:30 : Balances auto-maj
  Balances.2026-03 = {
    nb_factures: 1, ca_total: 350, ca_encaisse: 350,
    recu_urssaf: 350, solde: 350, nb_lettrees: 1, nb_non_lettrees: 0
  }

RÉSULTAT FINAL : FAC-001.statut = RAPPROCHE ✓ (comptabilité clean)
```

### Scénario 2 : Match Incertain (A_VERIFIER)

```
JOUR 8 : FAC-002 = 175 EUR, date_paye = 2026-03-07 (depuis 1j)
  Pas de transaction encore
  Lettrage.statut = PAS_DE_MATCH (rouge)
  Balances.nb_non_lettrees = 1

JOUR 12 : Virement arrive enfin (délai URSSAF)
  Transactions.TXN-003 = {
    montant: 175 EUR, date_valeur: 2026-03-12,
    libelle: "VIR URSSAF DUE00002"
  }
  Lettrage score = 50 (exact) + 5 (5j écart) + 20 (URSSAF) = 75
  75 < 80 → A_VERIFIER (orange)

JOUR 12 : Jules confirme
  Jules clique "Confirmer match"
  Transactions.TXN-003.facture_id = FAC-002 (override manuel)
  Transactions.TXN-003.statut_lettrage = LETTREE

JOUR 12 : Balances maj
  Balances.nb_lettrees = 2, nb_non_lettrees = 0

RÉSULTAT : FAC-002.statut = RAPPROCHE (manuel)
```

---

## 8. Formules Clés (Google Sheets)

### Lettrage : Scoring

```excel
=IF(ISBLANK(txn_id),0,
  (montant_exact ? 50 : ecart<1 ? 25 : 0) +
  (date_gap<=0 ? 30 : <=1 ? 25 : <=3 ? 15 : <=5 ? 5 : 0) +
  (REGEXMATCH(libelle,"URSSAF") ? 20 : REGEXMATCH(libelle,"DUE") ? 10 : 0)
)
```

### Balances : CA Encaissé (SUMIFS)

```excel
=SUMIFS(
  Factures!M:M,
  Factures!K:K,"PAYE",
  Factures!O:O,">="&DATE(YEAR(A2),MONTH(A2),1),
  Factures!O:O,"<"&DATE(YEAR(A2),MONTH(A2)+1,1)
)
```

### Cotisations : Charges Mensuelles

```excel
=ca_encaisse * 0.258
```

### Fiscal IR : Revenu Imposable

```excel
=ca_apres_abattement - cotisations_urssaf_annuel
```

**Voir `formules-sheets.md` pour liste complète & implémentation détaillée**

---

## 9. Implémentation (Checklist)

### Phase 1 : Structuration Google Sheets

- [ ] Créer 8 onglets (noms exacts)
- [ ] Ajouter colonnes data brute (Clients, Factures, Transactions)
- [ ] Ajouter colonnes calculées (Lettrage, Balances, etc.)
- [ ] Implémenter formules scoring (Lettrage)
- [ ] Implémenter formules agrégation (SUMIFS, COUNTIFS)
- [ ] Protéger onglets calculés (lecture seule)
- [ ] Format devise (EUR 2 décimales), dates ISO, enums

### Phase 2 : Intégration App

- [ ] SheetsAdapter (gspread / Google Sheets API v4)
- [ ] CRUD Clients (créer, éditer, archiver)
- [ ] CRUD Factures (créer, soumettre, polling statut)
- [ ] Import Transactions (Swan GraphQL sync)
- [ ] Trigger Lettrage (matching auto)
- [ ] Maj Balances (après lettrage)
- [ ] Export CSV (Balances pour Jules)

### Phase 3 : Validation & Tests

- [ ] Test cas 1 : Facture créée → payée → lettrée
- [ ] Test cas 2 : Match incertain (A_VERIFIER)
- [ ] Test cas 3 : Pas de match → attendre
- [ ] Test volume : 50 factures/mois, 30 transactions/mois
- [ ] Perf : Formules optimisées (pas ARRAYFORMULA lourde)
- [ ] Sécurité : Pas d'édition manuelle statut par Jules

---

## 10. Documents Liés

**Dans cette documentation :**
- `00-quick-ref.md` : Guide rapide (2 pages)
- `formules-sheets.md` : Implémentation formules Google Sheets
- `05-data-model.md` : Analyse complète (1039 lignes)

**Dans phase1 globale :**
- `02-billing-flow.md` : Flux facturation détaillé
- `03-urssaf-api-requirements.md` : API URSSAF
- `06-bank-reconciliation.md` : Lettrage & rapprochement
- `07-invoice-lifecycle.md` : Machine à états facture

---

## Résumé Exécutif (TLDR)

**8 onglets Google Sheets = toute la donnée SAP-Facture**

- **3 brutes** (Clients, Factures, Transactions) : Jules + API éditent
- **5 calculées** : Formules auto (lettrage, balances, charges, IR)

**Scoring lettrage** = montant (50) + date (30) + libelle (20) → AUTO >= 80

**Volumes** : 4-10 clients, 15-50 factures/mois, < 500 KB data

**Clé de succès** : Formules robustes, fenêtre ±5j matching, polling API URSSAF 4h

---

**Généré** : 15 mars 2026
**Statut** : Version 1.0 — Prêt implémentation
**Sources** : SCHEMAS.html SCHEMA 5 + détails
