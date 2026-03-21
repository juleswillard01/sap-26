---
name: sheets-inspect
description: Inspecter la structure et les données Google Sheets. Utiliser pour vérifier la cohérence des onglets, valider les schémas, ou diagnostiquer des problèmes de données.
---

# Sheets Inspect — Diagnostic Google Sheets

Tu inspectes le backend Google Sheets pour : $ARGUMENTS

## Étape 1 — Vérifier la structure
1. Lire `.claude/rules/sheets-schema.md` pour le schéma attendu
2. Vérifier que les 8 onglets existent :
   - Data brute : Clients, Factures, Transactions
   - Calculés : Lettrage, Balances, Metrics NOVA, Cotisations, Fiscal IR
3. Vérifier les headers de chaque onglet

## Étape 2 — Valider les données
1. Charger les données via SheetsAdapter
2. Pour chaque onglet data brute :
   - Vérifier les types (str, float, date, bool)
   - Vérifier les contraintes (unique, FK, non-null)
   - Vérifier les valeurs enum (statut_urssaf, statut facture, statut_lettrage)
3. Pour les onglets calculés :
   - Vérifier que les formules produisent des résultats cohérents

## Étape 3 — Reporter
```
===== SHEETS INSPECT =====
Clients      : 20 lignes, schema OK
Factures     : 200 lignes, schema OK
Transactions : 400 lignes, schema OK, 3 doublons indy_id
Lettrage     : formules OK, 15 A_VERIFIER
Balances     : formules OK
Metrics NOVA : formules OK
Cotisations  : formules OK
Fiscal IR    : formules OK
Cache        : TTL 30s, 5 entrées en cache
Rate Limit   : 42/60 req disponibles
===== FIN =====
```

## Checks rapides
```bash
# Tester la connexion Sheets
uv run python -c "from src.adapters.sheets_adapter import SheetsAdapter; from src.config import get_settings; sa = SheetsAdapter(get_settings()); print('OK')"

# Lancer les tests Sheets
uv run pytest tests/ -k sheets -v
```
