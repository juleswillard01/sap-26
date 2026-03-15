# Formules Google Sheets — Implémentation

**Source** : 05-data-model.md sections Lettrage, Balances, Metrics NOVA, Cotisations, Fiscal IR

---

## Onglet LETTRAGE — Scoring & Matching

### Colonne : `score_confiance` (Nombre 0-100)

**Logique** : Montant (50) + Date (30) + Libellé (20)

```excel
=IF(ISBLANK(D2),0,
  IF(E2=0,50,IF(E2<1,25,0)) +
  IF(AND(F2<=0,F2>=0),30,IF(ABS(F2)<=1,25,IF(ABS(F2)<=3,15,IF(ABS(F2)<=5,5,0)))) +
  IF(REGEXMATCH(G2,"URSSAF"),20,IF(REGEXMATCH(G2,"DUE"),10,0))
)
```

**Cellules références** :
- D2 = `txn_id` (transaction identifiée)
- E2 = `ecart` (=ABS(montant_facture - txn_montant))
- F2 = `ecart_date` (=date_valeur - date_paye, en jours)
- G2 = `libelle` (du virement Swan)

### Colonne : `statut` (Texte)

**Logique** : AUTO si score >= 80, A_VERIFIER si 50-79, PAS_DE_MATCH si < 50

```excel
=IF(B2=0,"PAS_DE_MATCH",IF(B2>=80,"AUTO",IF(B2>=50,"A_VERIFIER","PAS_DE_MATCH")))
```

**Référence** : B2 = score_confiance (colonne précédente)

**Alternative manuelle** : Si Jules override, cette colonne peut accepter "AUTO", "A_VERIFIER", "PAS_DE_MATCH" (la formule n'est pas appliquée si manuel)

### Onglet LETTRAGE — Colonnes de Base

```excel
# Colonne : facture_id
# Source : FILTER(Factures!A:A, Factures!K:K="PAYE")
# Formule (approximative, si tirage auto) :
=IFERROR(INDEX(FILTER(Factures!A:A,Factures!K:K="PAYE"),ROW()-1),"")

# Colonne : montant_facture
# Source : VLOOKUP facture_id → Factures.montant_total
=IFERROR(VLOOKUP(A2,Factures!A:M,13,FALSE),"")
# Note : 13 = colonne montant_total dans Factures

# Colonne : txn_id
# À matcher manuellement par algo (voir ci-dessous) ou XLOOKUP
=IFERROR(
  INDEX(
    Transactions!A:A,
    MATCH(1,
      (ABS(Transactions!E:E-C2)<5)*
      (ABS(Transactions!C:C-DATE(YEAR(D2),MONTH(D2),DAY(D2)))<=5),
      0
    )
  ),
  ""
)
# Note : Complexe, préférer code Python dans app

# Colonne : txn_montant
=IFERROR(VLOOKUP(E2,Transactions!A:E,5,FALSE),"")

# Colonne : ecart
=ABS(C2-F2)

# Colonne : date_maj
=IF(A2="","",TODAY())
```

---

## Onglet BALANCES — Agrégations Mensuelles

**Structure** : 1 ligne/mois (2026-01, 2026-02, 2026-03, etc.)

### Colonne : `nb_factures`

Nombre de factures créées ce mois (tous statuts)

```excel
=SUMPRODUCT(
  (MONTH(Factures!D:D)=MONTH(A2))*
  (YEAR(Factures!D:D)=YEAR(A2))
)
```

**Alternative COUNTIFS** (si date_creation en colonne D de Factures) :

```excel
=COUNTIFS(
  Factures!D:D,">="&DATE(YEAR(A2),MONTH(A2),1),
  Factures!D:D,"<"&DATE(YEAR(A2),MONTH(A2)+1,1)
)
```

### Colonne : `nb_factures_payees`

Factures au statut PAYE ce mois (date_paye dans le mois)

```excel
=COUNTIFS(
  Factures!K:K,"PAYE",
  Factures!O:O,">="&DATE(YEAR(A2),MONTH(A2),1),
  Factures!O:O,"<"&DATE(YEAR(A2),MONTH(A2)+1,1)
)
```

**Référence** : K = statut, O = date_paye

### Colonne : `ca_total`

Somme montants facturés ce mois (tous statuts)

```excel
=SUMIFS(
  Factures!M:M,
  Factures!D:D,">="&DATE(YEAR(A2),MONTH(A2),1),
  Factures!D:D,"<"&DATE(YEAR(A2),MONTH(A2)+1,1)
)
```

**Référence** : M = montant_total

### Colonne : `ca_encaisse`

Somme montants factures PAYE ce mois

```excel
=SUMIFS(
  Factures!M:M,
  Factures!K:K,"PAYE",
  Factures!O:O,">="&DATE(YEAR(A2),MONTH(A2),1),
  Factures!O:O,"<"&DATE(YEAR(A2),MONTH(A2)+1,1)
)
```

### Colonne : `recu_urssaf`

Somme virements URSSAF reçus ce mois

```excel
=SUMIFS(
  Transactions!D:D,
  Transactions!G:G,"URSSAF",
  Transactions!C:C,">="&DATE(YEAR(A2),MONTH(A2),1),
  Transactions!C:C,"<"&DATE(YEAR(A2),MONTH(A2)+1,1)
)
```

**Référence** : D = montant, C = date_valeur, G = source

### Colonne : `solde`

Solde caisse (recu_urssaf - frais)

```excel
=E2-SUMIFS(
  Transactions!D:D,
  Transactions!H:H,"FRAIS",
  Transactions!C:C,">="&DATE(YEAR(A2),MONTH(A2),1),
  Transactions!C:C,"<"&DATE(YEAR(A2),MONTH(A2)+1,1)
)
```

### Colonne : `nb_non_lettrees`

Factures sans match (statut PAS_DE_MATCH)

```excel
=COUNTIFS(
  Lettrage!H:H,"PAS_DE_MATCH",
  Lettrage!I:I,">="&DATE(YEAR(A2),MONTH(A2),1),
  Lettrage!I:I,"<"&DATE(YEAR(A2),MONTH(A2)+1,1)
)
```

**Référence** : H = statut lettrage, I = date_maj

### Colonne : `nb_en_attente`

Factures EN_ATTENTE (validation client URSSAF 48h)

```excel
=COUNTIFS(
  Factures!K:K,"EN_ATTENTE",
  Factures!N:N,">="&DATE(YEAR(A2),MONTH(A2),1),
  Factures!N:N,"<"&DATE(YEAR(A2),MONTH(A2)+1,1)
)
```

---

## Onglet METRICS NOVA — Reporting Trimestriel

**Structure** : 1 ligne/trimestre (Q1, Q2, Q3, Q4)

### Colonne : `nb_intervenants`

DISTINCT count de clients uniques ce trimestre

```excel
=SUMPRODUCT(
  (ROUNDUP(MONTH(Factures!D:D)/3,0)=ROUNDUP(MONTH(A2)/3,0))*
  (YEAR(Factures!D:D)=YEAR(A2))/
  COUNTIFS(Factures!B:B,Factures!B:B&"",Factures!D:D,">="&DATE(YEAR(A2),1,1),Factures!D:D,"<"&DATE(YEAR(A2),12,31))
)
```

**Alternative simple (si pas de formule UNIQUE)** :

```excel
=COUNTA(UNIQUE(FILTER(Factures!B:B,(ROUNDUP(MONTH(Factures!D:D)/3,0)=ROUNDUP(MONTH(A2)/3,0))*(YEAR(Factures!D:D)=YEAR(A2)))))
```

**Note** : Google Sheets dispose de UNIQUE, sinon utiliser SUMPRODUCT complexe

### Colonne : `heures_effectuees`

Somme quantités de type HEURE ce trimestre

```excel
=SUMIFS(
  Factures!F:F,
  Factures!E:E,"HEURE",
  Factures!D:D,">="&DATE(YEAR(A2),INT((MONTH(A2)-1)/3)*3+1,1),
  Factures!D:D,"<"&DATE(YEAR(A2),INT((MONTH(A2)-1)/3)*3+4,1)
)
```

**Référence** : F = quantite, E = type_unite

### Colonne : `ca_trimestre`

Somme montants factures PAYE ce trimestre

```excel
=SUMIFS(
  Factures!M:M,
  Factures!K:K,"PAYE",
  Factures!O:O,">="&DATE(YEAR(A2),INT((MONTH(A2)-1)/3)*3+1,1),
  Factures!O:O,"<"&DATE(YEAR(A2),INT((MONTH(A2)-1)/3)*3+4,1)
)
```

### Colonne : `deadline_saisie`

Limite déclaration NOVA (fin mois suivant trimestre, hardcoded ou formule)

```excel
=DATE(YEAR(A2),INT((MONTH(A2)-1)/3)*3+4,30)
```

---

## Onglet COTISATIONS — Charges Mensuelles

**Structure** : 1 ligne/mois

### Colonne : `ca_encaisse`

Référence directe à Balances

```excel
=VLOOKUP(A2,Balances!A:F,5,FALSE)
```

### Colonne : `montant_charges`

CA × 25.8% (taux URSSAF micro 2026)

```excel
=B2*0.258
```

### Colonne : `cumul_ca_annuel`

Somme CA encaissé depuis janvier de cette année

```excel
=SUMIFS(
  Cotisations!B:B,
  Cotisations!A:A,">="&DATE(YEAR(A2),1,1),
  Cotisations!A:A,"<="&A2
)
```

### Colonne : `cumul_vs_seuil`

Pourcentage d'utilisation du seuil micro (72 600 EUR)

```excel
=E2/72600
```

### Colonne : `alerte`

Alerte si >= 90% du seuil

```excel
=IF(F2>=0.9,"ALERTE SEUIL MICRO","OK")
```

### Colonne : `date_limite`

15 du mois suivant (paiement cotisations)

```excel
=DATE(YEAR(A2),MONTH(A2)+1,15)
```

### Colonne : `net_apres_charges`

CA net = CA - montant_charges

```excel
=B2-C2
```

---

## Onglet FISCAL IR — Simulation Annuelle

**Structure** : 1 ligne/année

### Colonne : `ca_micro_brut`

Somme montants factures PAYE cette année

```excel
=SUMIFS(
  Factures!M:M,
  Factures!K:K,"PAYE",
  Factures!O:O,">="&DATE(YEAR(A2),1,1),
  Factures!O:O,"<"&DATE(YEAR(A2)+1,1,1)
)
```

### Colonne : `ca_apres_abattement`

CA avec abattement BNC 34%

```excel
=C2*(1-0.34)
```

### Colonne : `cotisations_urssaf_annuel`

Somme charges sociales année (Cotisations.montant_charges × 12 ou somme)

```excel
=SUMIFS(
  Cotisations!C:C,
  Cotisations!A:A,">="&DATE(YEAR(A2),1,1),
  Cotisations!A:A,"<"&DATE(YEAR(A2)+1,1,1)
)
```

### Colonne : `revenu_imposable_ir`

Revenu net avant tranches = CA abattu - charges

```excel
=D2-E2
```

### Colonne : `revenu_net_total`

Revenu total imposable (apprentissage + imposable)

```excel
=B2+F2
```

**Note** : B2 = revenu_apprentissage (input manuel)

### Colonne : `taux_marginal_ir`

Taux IR par tranche 2026 (France, célibataire)

```excel
=IF(G2<=11000,0%,
   IF(G2<=28000,5.5%,
   IF(G2<=50000,10%,
   IF(G2<=75000,20%,
   IF(G2<=99233,30%,
   IF(G2<=152340,41%,45%))))))
```

### Colonne : `impot_estime_annuel`

Calcul IR par tranche (simplifié)

```excel
=IF(G2<=11000,0,
   IF(G2<=28000,(MIN(G2,28000)-11000)*0.055,
   IF(G2<=50000,(MIN(G2,50000)-28000)*0.10+(28000-11000)*0.055,
   IF(G2<=75000,(MIN(G2,75000)-50000)*0.20+(50000-28000)*0.10+(28000-11000)*0.055,
   IF(G2<=99233,(MIN(G2,99233)-75000)*0.30+...
   )))))
```

**Note** : Formule très longue ; préférer lookup table si possible

### Colonne : `simulation_mensuelle_lr`

Prélèvement mensuel estimé

```excel
=I2/12
```

### Colonne : `notes_fiscales`

Texte libre (manuelle) pour observations

```excel
=IF(H2>=72600,"Dépasser seuil MICRO ? Changement régime possible","OK")
```

---

## Récapitulatif par Onglet

| Onglet | Colonnes Formule | Complexité | Dépendances |
|--------|------------------|-----------|------------|
| LETTRAGE | score_confiance, statut | Haute | Transactions libelle, Factures dates |
| BALANCES | nb_factures, ca_total, ca_encaisse, recu_urssaf, solde, nb_lettrees, nb_non_lettrees | Moyenne | Factures, Transactions, Lettrage |
| METRICS NOVA | nb_intervenants, heures_effectuees, ca_trimestre | Moyenne | Factures (avec filtrage trimestre) |
| COTISATIONS | montant_charges, cumul_ca, cumul_vs_seuil, net_apres_charges | Basse | Balances.ca_encaisse |
| FISCAL IR | ca_apres_abattement, revenu_imposable, taux_marginal_ir, impot_estime | Haute | Factures (CA brut), Cotisations (charges annuelles) |

---

## Notes Implémentation

### Performance

- **Éviter** : ARRAYFORMULA récursive sur colonnes entières (A:A)
- **Préférer** : Plages fermées (A2:A100) ou FILTER avec limite
- **Optimisation** : Indices MATCH plutôt que VLOOKUP brut

### Google Sheets vs Excel

- Google Sheets supporte : FILTER, UNIQUE, REGEXMATCH ✓
- Excel supporte : XMATCH, XLOOKUP (mais pas FILTER identique)
- **Syntaxe dates** : Google = DATE(Y,M,D) ; Excel = DATE(Y,M,D) (identique)

### Validation & Protections

- **Onglets calculés** : Protected range (lecture seule sauf colonne manuelle si besoin)
- **Onglets brutes** : Validation data (listes enum pour statuts)
- **Formats** : Devise EUR (2 décimales), Dates ISO, Nombres entiers

### Testing

```
Cas test :
1. Créer FAC-001 (350 EUR, BROUILLON)
2. Soumettre → PAYE
3. Importer TXN-001 (350 EUR, même jour, libelle URSSAF)
4. Vérifier score_confiance = 100, statut AUTO
5. Vérifier Transactions.facture_id = FAC-001
6. Vérifier Balances.ca_encaisse = 350
7. Vérifier Cotisations.montant_charges = 90.30
```

---

**Généré** : 15 mars 2026
**Version** : 1.0
**Prêt pour implémentation** : Google Sheets API + gspread Python
