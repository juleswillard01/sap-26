# Déviation Architecturale : Indy via Playwright (vs Swan API)

**Date** : Mars 2026
**Auteur** : Winston (BMAD System Architect)
**Status** : ✅ Documenté, ADR-006 accepté
**Impact** : Changement source de données bancaires (Swan → Indy)

---

## Résumé de la Déviation

### Avant (Prévue initialement)
- **Source transactions** : Swan API (GraphQL)
- **Implémentation** : `SwanClient` avec requête GraphQL directe
- **Justification** : API officielle, déterministe, scalable

### Maintenant (Implémentation réelle)
- **Source transactions** : Indy (app.indy.fr)
- **Implémentation** : `IndyBrowserAdapter` avec Playwright automation
- **Justification** : Swan inaccessible, Indy disponible, Playwright pragmatique

### Raison du Changement
Jules utilise **Indy comme banque principale** (pas Swan). Pas d'accès API Swan documentée. Solution pragmatique :
- Utiliser **Playwright** pour automatiser l'extraction CSV depuis app.indy.fr
- Fallback **manual CSV export** si automation échoue
- **ADR-006** justifie ce choix dans `/docs/architecture/architecture.md`

---

## Impacte sur le Modèle de Données (SCHEMAS.html)

**IMPORTANT** : Le fichier `docs/schemas/SCHEMAS.html` reste **source de vérité**.

### Entité Transaction (Pas de changement)
```
Transaction {
  id: string            ← Indy transaction ID (vs Swan)
  date: date            ← Date de la transaction
  amount: float         ← Montant (EUR)
  label: string         ← Libellé (e.g., "URSSAF Virement")
  status: string        ← "COMPLETED" (Indy exports completed txns only)
}
```

La **structure de données est identique** : seule la source change (Swan API → Indy web export).

### Onglet Google Sheets "Transactions"
```
Colonnes (inchangées) :
- A: Transaction ID (from Indy)
- B: Date
- C: Montant
- D: Libellé
- E: Status
- F: Created At (Sheets timestamp)
```

**Aucun changement au schéma Sheets.**

---

## Impacte sur les Flux (Légèrement modifié)

### Flux Rapprochement Bancaire (avant)
```
BankReconciliation.reconcile()
  └─ SwanClient.get_transactions()
     └─ GraphQL query → list[Transaction]
```

### Flux Rapprochement Bancaire (maintenant)
```
BankReconciliation.reconcile()
  ├─ Option 1 (Normal)
  │  └─ IndyBrowserAdapter.get_transactions()
  │     ├─ Playwright login (INDY_EMAIL, INDY_PASSWORD)
  │     ├─ Navigate Transactions page
  │     ├─ Export CSV
  │     └─ Parse → list[Transaction]
  │
  └─ Option 2 (Fallback)
     └─ BankReconciliation.reconcile(csv_path="/path/to/export.csv")
        └─ IndyBrowserAdapter.parse_csv_export(csv_path)
```

**Algorithme de lettrage reste identique** : seule l'acquisition des transactions change.

---

## Impacte sur la Sécurité

### Avant (Swan)
- Secret : `SWAN_API_KEY` (API key)
- Authentification : Bearer token (HTTP header)
- Stockage : `.env` (base64 encoded)

### Maintenant (Indy)
- Secrets : `INDY_EMAIL`, `INDY_PASSWORD`
- Authentification : Form login (Playwright automation)
- Stockage : `.env` (plain text, SecretStr via Pydantic)
- Nouvau risque : Session expiration, credentials in process memory

### Mitigations Sécurité
1. **Rotation trimestrielle** : INDY_EMAIL / INDY_PASSWORD
2. **Headless mode** : Pas de fenêtre navigateur (prod)
3. **Screenshot on error** : Debug screenshot saved to `/tmp/indy_error_*.png`
4. **Timeout** : 30s max, retry 3x avec backoff exponentiel
5. **Alert on failure** : Email Jules si 3 tentatives échouent

---

## Impacte sur la Fiabilité (Risk Assessment)

| Aspect | Swan API | Indy Playwright | Notes |
|--------|----------|-----------------|-------|
| Availability | Very High (99.9%+) | Medium (depends UI) | Indy UI peut changer |
| Latency | Low (< 200ms) | Medium (3-5s) | Browser spin-up overhead |
| Deterministic | Very High | Medium | Fragile si UI change |
| Fallback | None | Manual CSV export | Manual process documented |
| Cost | $$ (API fees) | Free | ✅ Playwright open-source |

### Stratégie de Résilience
1. **Primary** : Playwright automation (daily cron)
2. **Fallback** : Manual CSV export + CLI import
3. **Monitoring** : Email alert si Playwright échoue 3x
4. **Maintenance** : Quarterly UI test (check selectors work)

---

## Impacte sur la Documentation

### Documents Updatés
- ✅ `docs/architecture/architecture.md` : Section 3.4.2, ADR-006
- ✅ `.env.example` : INDY_EMAIL, INDY_PASSWORD
- ✅ Checklist implémentation : Phase 2 (Playwright, fallback CSV)

### Documents Non-Impactés
- ✅ `docs/schemas/SCHEMAS.html` : Entité Transaction identique (source de vérité)
- ✅ `docs/analysis/06-bank-reconciliation.md` : Algorithme lettrage inchangé
- ✅ Autres onglets Sheets : Clients, Factures, Lettrage, etc.

---

## Migration Plan (Si Swan API devient disponible à l'avenir)

Si Jules obtient accès API Swan :
1. **Créer `SwanClient`** (parallel à `IndyBrowserAdapter`)
2. **Switch priorité** : Swan primary, Indy fallback
3. **Reverse de ce document** (or create new ADR-007)

---

## Testing Checklist

### Unit Tests (IndyBrowserAdapter)
- [ ] CSV parsing (valid + invalid formats)
- [ ] Transaction mapping (date, amount parsing)
- [ ] Error handling (timeout, login failure)

### Integration Tests
- [ ] End-to-end reconciliation avec CSV fixture
- [ ] Fallback mechanism (CSV path provided)
- [ ] Batch write to Sheets

### Manual Testing
- [ ] Playwright automation contre app.indy.fr real (monthly)
- [ ] Credentials in .env loaded correctly
- [ ] Error screenshot captured on failure
- [ ] CSV fallback import works

---

## Conclusion

**Cette déviation est pragmatique et documentée** :
- ✅ Respecte la structure de données (SCHEMAS.html inchangé)
- ✅ Justifiée par ADR-006 et ce document
- ✅ Fallback manual process documenta
- ✅ Sécurité comparable (rotation secrets, timeout)
- ✅ Fiabilité acceptable pour MVP (95%+ success rate expected)

**Contact** : Winston (BMAD System Architect) pour clarifications ou futur API Swan.

---

**Version** : 1.0
**Date** : Mars 2026
**Référence** : `docs/architecture/architecture.md` (ADR-006), `.env.example`
