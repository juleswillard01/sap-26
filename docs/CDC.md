# CDC — SAP-Facture

## 0. Contexte
Jules Willard, prof particulier, auto-entrepreneur (SIREN 991552019), services à la personne.
Facturation via avance-immediate.fr (offre tout-en-un ~99€/an). Ce projet est l'orchestrateur
qui gère tout autour de la facturation.

## 1. Google Sheets Backend
### 1.1 Structure — 8 onglets
**Data brute (éditables)** :
- **Clients** : client_id, nom, prenom, email, telephone, adresse, code_postal, ville, urssaf_id, statut_urssaf, date_inscription, actif
- **Factures** : facture_id, client_id, type_unite, nature_code, quantite, montant_unitaire, montant_total (formule), date_debut, date_fin, description, statut, urssaf_demande_id, dates suivi, pdf_drive_id
- **Transactions** : transaction_id, indy_id, date_valeur, montant, libelle, type, source, facture_id, statut_lettrage, date_import

**Calculés (formules, lecture seule)** :
- **Lettrage** : facture_id, montant_facture, txn_id, txn_montant, ecart, score_confiance, statut (AUTO / A_VERIFIER / PAS_DE_MATCH)
- **Balances** : mois, nb_factures, ca_total, recu_urssaf, solde, nb_non_lettrees, nb_en_attente
- **Metrics NOVA** : trimestre, nb_intervenants (1), heures_effectuees, nb_particuliers, ca_trimestre, deadline_saisie
- **Cotisations** : mois, ca_encaisse, taux_charges (25.8%), montant_charges, date_limite, cumul_ca, net_apres_charges
- **Fiscal IR** : revenu_apprentissage, seuil_exo, ca_micro, abattement (34% BNC), revenu_imposable, tranches IR, taux_marginal, simulation VL (2.2%)

### 1.2 SheetsAdapter
- gspread + Google Sheets API v4
- Batch reads : `get_all_records()` jamais cellule par cellule
- Batch writes : `update()` avec range
- Rate limit : 60 req/min/user, throttle
- Cache mémoire 30s pour reads identiques

## 2. Machine à états Facture
### 2.1 États
BROUILLON, SOUMIS, CREE, EN_ATTENTE, VALIDE, PAYE, RAPPROCHE, ERREUR, EXPIRE, REJETE, ANNULE

### 2.2 Transitions
- BROUILLON → SOUMIS → CREE → EN_ATTENTE → VALIDE → PAYE → RAPPROCHE
- SOUMIS → ERREUR → BROUILLON
- EN_ATTENTE → EXPIRE → BROUILLON
- EN_ATTENTE → REJETE → BROUILLON
- BROUILLON → ANNULE (terminal)

### 2.3 Timers
- T+36h sans validation → reminder email
- T+48h sans validation → EXPIRE

## 3. Rapprochement bancaire
### 3.1 Import Indy
- Playwright headless scrape transactions Indy Banking
- Export CSV parsé → onglet Transactions
- Retry 3x backoff exponentiel
- Screenshots erreur dans `io/cache/` (SANS données sensibles)

### 3.2 Lettrage — Score confiance
Pour chaque facture PAYEE :
1. Filtrer transactions fenêtre ± 5 jours
2. Montant exact = +50pts, date < 3j = +30pts, libellé URSSAF = +20pts
3. ≥80 → LETTRE AUTO | <80 → A_VERIFIER | pas de match → PAS_DE_MATCH
4. Mettre à jour Balances

## 4. Dashboard Web
- FastAPI SSR + Jinja2 + Tailwind
- Embeds Google Sheets pubhtml pour onglets calculés
- Vue par statut, CA mensuel, solde, filtres

## 5. CLI
- `sap sync` : polling statuts, maj onglet Factures
- `sap reconcile` : import Indy + lettrage
- `sap export` : CSV pour comptable
- `sap status` : résumé rapide

## 6. Notifications
- T+36h reminder email à Jules
- SMTP via `.env`
- Cron : sync 4h, reconcile quotidien, reminders 9h

## 7. Reporting NOVA
- Metrics trimestrielles (heures, particuliers, CA, deadline)

## 8. Calculs fiscaux
- Cotisations micro : 25.8% CA encaissé
- Abattement BNC : 34%
- Simulation tranches IR
- Versement libératoire : 2.2%

## 9. Infrastructure
- Docker : python:3.12-slim + Playwright chromium + WeasyPrint
- Credentials Google via secret Docker
- Tests ≥80%, ruff + pyright strict
- RGPD : pas de logs nominatifs, pas de screenshots bancaires
