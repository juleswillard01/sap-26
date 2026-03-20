# SAP-Facture Domain Skill

## Contexte métier
Jules est prof particulier, auto-entrepreneur (SIREN 991552019), services à la personne.
Ses clients (parents d'élèves) bénéficient de l'Avance Immédiate URSSAF = crédit d'impôt 50% instantané.

## Flux principal
1. Jules donne un cours
2. Il crée la facture dans avance-immediate.fr (logiciel externe)
3. Le logiciel soumet à l'API URSSAF Tiers de Prestation
4. Le client reçoit un email URSSAF, valide sous 48h
5. URSSAF verse 100% à Jules (sur son compte Indy)
6. Le client paye son 50% directement à l'URSSAF

## Notre périmètre (ce qu'on code)
- **SheetsAdapter** : Google Sheets = backend data (8 onglets)
- **IndyBrowserAdapter** : Playwright scrape les transactions bancaires Indy
- **BankReconciliation** : Lettrage automatique factures ↔ transactions
- **PaymentTracker** : Polling statuts (sync avec avance-immediate.fr)
- **Dashboard** : FastAPI SSR avec embeds Google Sheets
- **CLI** : `sap sync`, `sap reconcile`, `sap export`
- **Notifications** : Email reminders T+36h si client n'a pas validé

## Machine à états Facture
```
BROUILLON → SOUMIS → CREE → EN_ATTENTE → VALIDE → PAYE → RAPPROCHE
                ↓                  ↓          ↓
              ERREUR            EXPIRE      REJETE
                ↓                  ↓          ↓
           BROUILLON          BROUILLON   BROUILLON
BROUILLON → ANNULE (terminal)
```

## Lettrage bancaire — Score de confiance
- Montant exact = +50 points
- Date < 3 jours de l'expected = +30 points
- Libellé contient "URSSAF" = +20 points
- Score ≥ 80 → LETTRE AUTO
- Score < 80 → A_VERIFIER (Jules confirme manuellement)

## Google Sheets — 8 onglets
### Data brute
| Onglet | Clé primaire | Champs clés |
|--------|-------------|-------------|
| Clients | client_id | nom, prenom, email, urssaf_id, statut_urssaf |
| Factures | facture_id | client_id, nature_code, montant_total, statut, urssaf_demande_id |
| Transactions | transaction_id | indy_id, date_valeur, montant, facture_id, statut_lettrage |

### Calculés (formules)
| Onglet | Calcul principal |
|--------|-----------------|
| Lettrage | MATCH(facture, transaction) + score confiance |
| Balances | SUM par mois, soldes, nb_non_lettrées |
| Metrics NOVA | Reporting trimestriel (nb heures, nb particuliers) |
| Cotisations | CA × 25.8% charges micro-entreprise |
| Fiscal IR | Abattement BNC 34%, simulation tranches IR |

## Natures de prestation URSSAF (codes SAP)
- Soutien scolaire à domicile
- Cours particuliers à domicile
- Assistance informatique à domicile

## Chiffres clés
- Taux charges micro : 25.8%
- Abattement BNC : 34%
- Crédit d'impôt client : 50%
- Délai validation client : 48h
- Reminder : T+36h
- Polling statuts : toutes les 4h
