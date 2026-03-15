# Résumé Mise à Jour Architecturale — SAP-Facture

**Date** : 15 Mars 2026
**Architecte** : Winston (BMAD System Architect)
**Changement** : Swan API → Indy via Playwright
**Impact** : Phase 2 (Réconciliation Bancaire)

---

## Situation Initiale vs Changement

### Avant (Prévue)
```
Source de transactions bancaires : Swan API (GraphQL)
Composant : SwanClient
Authentication : API Key Bearer token
Coût : €€€ (accès API payant)
Status : ❌ Inaccessible pour Jules
```

### Maintenant (Réalité)
```
Source de transactions bancaires : Indy (app.indy.fr)
Composant : IndyBrowserAdapter
Automation : Playwright (browser automation)
Authentication : Email + Password (from .env)
Coût : Gratuit (Playwright open-source)
Status : ✅ Accessible et fonctionnel
```

---

## Fichiers Mis à Jour

### 1. **docs/architecture/architecture.md** (Document Principal)
   - Section 2.2 : Stack Tech → remplacé `gql (GraphQL)` par `Playwright (Python)`
   - Section 3.2.4 : BankReconciliation → ajout support flag `--csv` (fallback)
   - Section 3.4.2 : **Nouveau** IndyBrowserAdapter (remplace SwanClient)
   - Section 9 : **ADR-006** - Justification architecturale Playwright vs API
   - Section 11 : Risques & Mitigations → ajout scenarios Playwright (timeout, UI change)
   - Checklist Phase 2 : Playwright automation + fallback CSV

### 2. **docs/DEVIATION_INDY_PLAYWRIGHT.md** (Nouveau)
   - Impact sur le modèle de données (SCHEMAS.html inchangé)
   - Impact sur les flux de réconciliation (algorithme identique)
   - Implications sécurité (rotation des credentials)
   - Assessment fiabilité vs Swan
   - Plan migration future si Swan API disponible

### 3. **docs/implementation/PLAYWRIGHT_INDY_GUIDE.md** (Nouveau)
   - Guide implémentation détaillé
   - Code pseudo-complet pour IndyBrowserAdapter
   - Intégration dans BankReconciliation + CLI
   - Unit tests + Integration tests
   - Monitoring & Alerting
   - Troubleshooting

### 4. **.env.example** (Mise à Jour)
   ```bash
   # Ajout:
   INDY_EMAIL=your_indy_email@example.com
   INDY_PASSWORD=your_indy_password_here_replace_me
   INDY_HEADLESS=true  # false pour debug

   # Dépréciation:
   # SWAN_API_KEY=deprecated
   # SWAN_API_BASE_URL=deprecated
   # SWAN_ACCOUNT_ID=deprecated
   ```

---

## Ce Qui Change (Pour Jules)

### Configuration
- ❌ Supprimer `SWAN_API_KEY` de `.env`
- ✅ Ajouter `INDY_EMAIL`, `INDY_PASSWORD` dans `.env`
- ✅ Garder toutes les autres variables (URSSAF, Google Sheets, SMTP, etc.)

### Workflow Réconciliation Bancaire
```
Avant:  Jules → click "Réconcile" → SwanClient.get_transactions() → ...
                                     (API call direct)

Maintenant: Jules → click "Réconcile" → IndyBrowserAdapter.get_transactions()
                                         (Playwright automation)
                                         ├─ Login Indy
                                         ├─ Navigate Transactions page
                                         ├─ Export CSV
                                         └─ Parse & import to Sheets
```

**Temps d'exécution** : ~4-6s (vs ~2-3s avant)
- 3-5s pour lancer browser + login
- 1-2s pour navigation + export
- Imperceptible pour l'utilisateur final

### Fallback Manuel (Si Automation Échoue)
```bash
1. Login manuellement à app.indy.fr
2. Aller à Transactions
3. Exporter en CSV
4. Importer via CLI:
   sap reconcile --csv /chemin/vers/export.csv
```

**Documentation** : Voir `/docs/DEVIATION_INDY_PLAYWRIGHT.md`

---

## Ce Qui NE Change PAS

### Modèle de Données
✅ Structure Transaction (id, date, montant, libellé, status) **identique**
✅ Onglet Google Sheets "Transactions" **inchangé**
✅ **SCHEMAS.html reste source de vérité**

### Algorithme Lettrage
✅ Scoring confiance inchangé :
   - Montant exact = +50 points
   - Date < 3j = +30 points
   - Libellé "URSSAF" = +20 points
   - Score >= 80 → LETTRE_AUTO
   - Score >= 50 → A_VERIFIER
   - Score < 50 → PAS_DE_MATCH

### Interfaces Utilisateur
✅ Web dashboard (FastAPI routes) **identique**
✅ Onglets Sheets iframes **identiques**
✅ CLI commandes **identiques** (juste option `--csv` ajoutée)

### Sécurité Globale
✅ Validation Pydantic **identique**
✅ Google Sheets API **identique**
✅ URSSAF polling **identique**

---

## Avantages du Changement

| Aspect | Swan (Avant) | Indy/Playwright (Maintenant) |
|--------|------------|------|
| **Coût** | €€€ (API payante) | ✅ Gratuit |
| **Accès** | ❌ Pas d'accès | ✅ Jules a accès |
| **Fiabilité** | Très haute (99.9%+) | Haute (95%+ expected) |
| **Latency** | < 200ms | 4-6s (browser startup) |
| **Fallback** | Aucun | ✅ Manual CSV |
| **Pragmatisme** | Idéal (si accessible) | ✅ Pragmatique (réalité Jules) |

---

## Risques & Mitigations

### Risque 1 : Indy UI Change (Sélecteurs Playwright brisés)
**Probabilité** : Moyenne
**Impact** : Reconciliation automatique échoue
**Mitigation** :
- Fallback manual CSV (documenté, facile)
- Monthly UI test (check selectors still work)
- Email alert si 3 failures consécutifs
- Fix dans 24h si UI change détecté

### Risque 2 : Timeout Playwright (30s)
**Probabilité** : Basse
**Impact** : Reconciliation slow ou fails
**Mitigation** :
- Retry 3x avec exponential backoff (1s, 2s, 4s)
- Fallback manual CSV
- Configurable timeout_ms en cas de besoin

### Risque 3 : Session Expiration Indy
**Probabilité** : Basse (credentials in .env, auto-login)
**Impact** : Auth fails
**Mitigation** :
- Catch auth errors, screenshot for debug
- Retry avec fresh browser instance
- Notify Jules if persistent

### Risque 4 : Credentials Leak (.env)
**Probabilité** : Très basse (but never zero)
**Impact** : Indy account compromise
**Mitigation** :
- `.env` in `.gitignore` (verified)
- Quarterly rotation INDY_EMAIL/PASSWORD
- Use app-specific password if Indy supports (future)

---

## Documentation à Lire

### Pour Comprendre le Changement
1. **docs/DEVIATION_INDY_PLAYWRIGHT.md** (5-10 min)
   - Quoi a changé, pourquoi, impact réel

### Pour Implémenter
1. **docs/implementation/PLAYWRIGHT_INDY_GUIDE.md** (30-45 min)
   - Code complet, tests, troubleshooting
   - Prêt pour développeur Phase 2

### Pour Référence Architecturale
1. **docs/architecture/architecture.md** (sections 3.4.2, ADR-006)
   - Justification complète
   - Diagrammes et pseudo-code

---

## Prochaines Étapes

### Phase 2 (Implementation)
- [ ] Implémenter `IndyBrowserAdapter` (classe Python)
- [ ] Intégrer dans `BankReconciliation.reconcile()`
- [ ] CLI support pour `--csv` (fallback)
- [ ] Unit tests + Integration tests
- [ ] Test manual avec Indy real account
- [ ] Documentation de déploiement

### Après Phase 2
- [ ] Monitoring alertes (3x failures → email Jules)
- [ ] Monthly UI test script (automated)
- [ ] Documentation fallback process pour Jules

### Futur (Si Swan API Devient Accessible)
- [ ] Créer `SwanClient` parallel
- [ ] Switch priorité (Swan primary, Indy fallback)
- [ ] Créer ADR-007 justifiant le changement

---

## Questions ?

**Contact** : Winston (BMAD System Architect)
- `docs/DEVIATION_INDY_PLAYWRIGHT.md` → Why change
- `docs/implementation/PLAYWRIGHT_INDY_GUIDE.md` → How to implement
- `docs/architecture/architecture.md` (ADR-006) → Detailed justification

**Configuration** :
- `.env.example` → What values needed
- `docs/architecture/architecture.md` (Section 6) → Security review

---

## Checklist Configuration Jules

- [ ] Copier `.env.example` → `.env`
- [ ] Remplir `INDY_EMAIL` (votre email Indy)
- [ ] Remplir `INDY_PASSWORD` (votre password Indy)
- [ ] Garder `INDY_HEADLESS=true` (prod) ou `false` (debug)
- [ ] Vérifier autres variables (URSSAF, Google, SMTP)
- [ ] Tester login Indy manuellement (app.indy.fr)
- [ ] Faire commit des changes de code Phase 2

---

**Version** : 1.0
**Date** : 15 Mars 2026
**Référence** : `docs/architecture/architecture.md` (commit c92511d)
