# CDC — SAP-Facture (Orchestrateur)

## 0. Contexte et Positionnement

Jules Willard, prof particulier, auto-entrepreneur (SIREN 991552019), services à la personne.

**Architecture logicielle** :
- **AIS** (app.avance-immediate.fr, ~99€/an) : gère la facturation + soumission URSSAF + avance immédiate
- **Indy** (app.indy.fr) : comptabilité + banque pro + journal des transactions
- **SAP-Facture** : orchestrateur qui synchronise AIS + Indy + Google Sheets

**Rôles distincts** :
- **AIS créé les factures.** Jules remplit le formulaire dans AIS, AIS soumet à URSSAF
- **AIS soumet à URSSAF.** SAP-Facture ne touche pas à URSSAF
- **SAP-Facture synchronise, rapproche et alerte.** Lecture seule d'AIS et Indy, écriture dans Sheets

**Pas de création d'invoice dans SAP-Facture.** Pas d'appel API URSSAF direct. SAP-Facture lit les demandes créées par AIS et en détecte les changements d'état.

---

## 1. Google Sheets Backend

### 1.1 Structure — 8 onglets

**Data brute (éditables)** :
- **Clients** : client_id, nom, prenom, email, telephone, adresse, code_postal, ville, urssaf_id, statut_urssaf, date_inscription, actif
- **Factures** : facture_id, client_id, type_unite, nature_code, quantite, montant_unitaire, montant_total (formule), date_debut, date_fin, description, statut, urssaf_demande_id, date_soumission, date_validation, date_paiement, date_rapprochement
- **Transactions** : transaction_id, indy_id, date_valeur, montant, libelle, type, source, facture_id, statut_lettrage, date_import

**Calculés (formules, lecture seule)** :
- **Lettrage** : facture_id, montant_facture, txn_id, txn_montant, ecart, score_confiance, statut (LETTRE_AUTO / A_VERIFIER / PAS_DE_MATCH)
- **Balances** : mois, nb_factures, ca_total, recu_urssaf, solde, nb_non_lettrees, nb_en_attente
- **Metrics NOVA** : trimestre, nb_intervenants (1), heures_effectuees, nb_particuliers, ca_trimestre, deadline_saisie
- **Cotisations** : mois, ca_encaisse, taux_charges (25.8%), montant_charges, date_limite, cumul_ca, net_apres_charges
- **Fiscal IR** : revenu_apprentissage, seuil_exo, ca_micro, abattement (34% BNC), revenu_imposable, tranches IR, taux_marginal, simulation VL (2.2%)

### 1.2 SheetsAdapter

- gspread + Google Sheets API v4 + Polars + Patito
- Batch reads : `get_all_records()` jamais cellule par cellule
- Batch writes : `update()` / `append_rows()` avec range
- Rate limit : 60 req/min/user, throttle (TokenBucketRateLimiter)
- Cache mémoire 30s (cachetools.TTLCache)
- Circuit breaker (pybreaker)
- Write queue sérialisée (threading.Queue)

---

## 2. Machine à États Facture

### 2.1 États

BROUILLON, SOUMIS, CREE, EN_ATTENTE, VALIDE, PAYE, RAPPROCHE, ERREUR, EXPIRE, REJETE, ANNULE

### 2.2 Transitions

- Chemin normal : BROUILLON → SOUMIS → CREE → EN_ATTENTE → VALIDE → PAYE → RAPPROCHE
- Erreurs : SOUMIS → ERREUR → BROUILLON
- Expiration : EN_ATTENTE → EXPIRE → BROUILLON
- Rejet : EN_ATTENTE → REJETE → BROUILLON
- Annulation : BROUILLON → ANNULE (terminal)
- CREE → EN_ATTENTE est IMMÉDIAT (pas de délai)

**Note cruciale** : Ces transitions sont **détectées** par SAP-Facture via le sync AIS, elles ne sont **pas déclenchées** par SAP-Facture. AIS et URSSAF gèrent les transitions réelles.

### 2.3 Timers

- T+36h sans validation → reminder email à Jules (factures en attente depuis trop longtemps)
- T+48h sans validation → SAP-Facture détecte EXPIRE

---

## 3. Sync AIS — Lecture Seule (Playwright)

### 3.1 Qu'est-ce que SAP-Facture lit dans AIS

AIS (Avance Immédiate Services, app.avance-immediate.fr) est habilité par URSSAF et gère :
- L'inscription des clients particuliers auprès d'URSSAF
- La soumission des demandes de paiement (factures) à URSSAF
- Les statuts des demandes (CREE, EN_ATTENTE, VALIDE, PAYE, REJETE, EXPIRE)

SAP-Facture lit dans AIS (Playwright headless) :
- **Page Clients** : client_id, nom, prenom, email, statut_urssaf, date_inscription
- **Page Demandes** : facture_id, montant, client, statut, urssaf_demande_id, date_soumission, date_validation, date_paiement

SAP-Facture met à jour :
- **Onglet Clients** avec les infos lues
- **Onglet Factures** avec les statuts et dates lues

### 3.2 Ce que SAP-Facture NE fait PAS dans AIS

- **PAS de création de facture** : Jules crée la facture dans AIS
- **PAS d'inscription de client** : Jules inscrit le client dans AIS
- **PAS de soumission à URSSAF** : AIS soumet à URSSAF directement
- **PAS de modification de demande** : AIS et URSSAF gèrent les modifications

### 3.3 AISAdapter (Playwright)

```
Login (email + password) → Session authentifiée
  ↓
Scrape page "Mes demandes" → Extraire statuts
  ↓
Pour chaque demande : parser id, montant, statut, dates
  ↓
Dedup par urssaf_demande_id
  ↓
Maj onglet Factures (statut, date_validation, date_paiement, etc.)
  ↓
Détect demandes EN_ATTENTE > 36h → Logger alerte
```

- Retry 3x backoff exponentiel
- Screenshots erreur dans `io/cache/` (SANS données sensibles)
- Cron : `sap sync` toutes les 4h

---

## 4. Sync Indy — Transactions (Playwright)

### 4.1 Ce que SAP-Facture lit dans Indy

Indy (app.indy.fr) gère la comptabilité et les transactions bancaires.

SAP-Facture lit dans Indy (Playwright headless) :
- **Journal Book (CSV)** : Documents > Comptabilité > Export CSV
- Transactions datées, montants, libellés, catégorisées

SAP-Facture met à jour :
- **Onglet Transactions** avec les lignes du Journal Book

### 4.2 IndyAdapter (Playwright)

```
Login (email + password) → Session authentifiée
  ↓
Naviguer vers Documents > Comptabilité
  ↓
Exporter Journal Book (CSV)
  ↓
Parser CSV → Extraire transaction_id, date_valeur, montant, libelle, type
  ↓
Dedup par indy_id
  ↓
Maj onglet Transactions (date_import, source="indy")
```

- Retry 3x backoff exponentiel
- Screenshots erreur dans `io/cache/` (SANS données sensibles)
- Cron : `sap reconcile` quotidien

---

## 5. Rapprochement Bancaire (Lettrage)

### 5.1 Lettrage — Score Confiance

Pour chaque facture en état PAYE (statut venant d'AIS) :

1. **Fenêtrer les transactions** : filtrer celles dans la fenêtre ±5 jours (date_paiement ± 5j)
2. **Scorer chaque match potentiel** :
   - Montant exact → +50pts
   - Date < 3 jours → +30pts
   - Libellé contient "URSSAF" → +20pts
3. **Décider** :
   - Score ≥80 → LETTRE_AUTO
   - Score <80 et ≥1 match → A_VERIFIER
   - Pas de match → PAS_DE_MATCH
4. **Mettre à jour onglet Lettrage** avec le meilleur match et le score

### 5.2 Mise à Jour

- **Onglet Lettrage** (formules Sheets) : affiche matches + scores
- **Onglet Balances** (formules Sheets) : agrégation mensuelle CA / solde
- **Onglet Factures** : transition PAYE → RAPPROCHE si LETTRE_AUTO

---

## 6. CLI

- `sap init` : créer le spreadsheet Google Sheets (8 onglets + headers + formules)
- `sap sync` : scrape AIS → maj onglets Factures + Clients
- `sap reconcile` : scrape Indy → import transactions → lettrage
- `sap status` : résumé rapide (factures en attente, solde, impayés)
- `sap nova` : générer données NOVA trimestriel
- `sap export` : CSV pour comptable

---

## 7. Notifications

- **T+36h reminder** : email à Jules si factures en attente trop longtemps
- **Alerte sync** : si sync AIS ou Indy échoue, notifier Jules
- **Résumé quotidien** (optionnel) : CA du jour, solde, factures lettrées
- **SMTP Gmail** via .env (GMAIL_USER, GMAIL_APP_PASSWORD)
- **Cron scheduling** : sync AIS 4h, reconcile Indy quotidien, reminders 9h

---

## 8. Reporting

### 8.1 NOVA Trimestriel

- **heures_effectuees** : agrégation depuis onglet Factures (sum quantité)
- **nb_particuliers** : count distinct client_id avec statut PAYE
- **ca_trimestre** : sum montant_total sur le trimestre

Jules déclare manuellement sur nova.entreprises.gouv.fr (SAP-Facture génère juste les données).

### 8.2 Cotisations Micro

- Taux : 25.8% du CA encaissé (PAYE)
- Agrégation mensuelle depuis onglet Balances
- Cumul annuel, net après charges

### 8.3 Fiscal IR

- Abattement BNC : 34% du CA encaissé
- Simulation tranches IR progressives
- Versement libératoire : 2.2% (optionnel)

---

## 9. Infrastructure

- **Docker** : python:3.12-slim + Playwright chromium
- **Credentials** : .env (AIS_EMAIL, AIS_PASSWORD, INDY_EMAIL, INDY_PASSWORD, GOOGLE_CREDENTIALS_JSON, GMAIL_USER, GMAIL_APP_PASSWORD)
- **Secrets Docker** : never commit .env
- **Tests** : ≥80% coverage, ruff + pyright --strict
- **RGPD** : pas de logs nominatifs, pas de screenshots bancaires, dédélation données sur demande

---

## 10. Points Clés Architecturaux

1. **Orchestration, pas création** : SAP-Facture synchronise, AIS crée
2. **Lecture seule d'AIS et Indy** : aucune écriture directe, pas d'API URSSAF
3. **Détection d'états, pas déclenchement** : SAP-Facture détecte les changements d'état des demandes, AIS/URSSAF les gèrent
4. **Google Sheets comme backend** : source de vérité, formules calculées, versionning historique
5. **Playwright pour scraping** : AIS et Indy n'ont pas d'API stables, scraping headless + cache + retry
6. **Lettrage par score confiance** : rapprochement bancaire robuste, manuel si doute
7. **TDD strict** : RED → GREEN → REFACTOR, test-driven
