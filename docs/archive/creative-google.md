# Creative Solutions — Google Integration

**Date**: 2026-03-21
**Approche**: First-principles thinking applique aux 3 domaines Google

---

## 1. Formules vs Code — La Question Fondamentale

### Pensee conventionnelle
"Les onglets calcules (Lettrage, Balances, NOVA, Cotisations, Fiscal IR) utilisent des formules Google Sheets."

### Analyse first-principles

**Faits bedrock**:
- Google Sheets formules sont **non-testables** (pas de pytest sur XLOOKUP)
- Google Sheets formules sont **fragiles** (une colonne ajoutee casse tout)
- Google Sheets formules sont **opaques** (debugging = deviner)
- Python est **testable**, **versionne**, **debuggable**
- Jules veut **voir** les resultats dans Sheets (pas dans un terminal)

**Contradiction**: Le CDC dit "formules Sheets" mais le CDC dit aussi "pytest >= 80% coverage".
On ne peut pas tester des formules Sheets avec pytest.

### Verdict: Python Pre-Compute + Sheets Display

```
┌─────────────┐    ┌──────────────┐    ┌───────────────┐
│ Polars       │ -> │ LettrageService│ -> │ SheetsAdapter  │
│ (DataFrames) │    │ (scoring)     │    │ (write results)│
└─────────────┘    └──────────────┘    └───────────────┘
                         |
                    Python calcule
                    Sheets affiche
```

**Avantages**:
- 100% testable avec pytest
- Scoring exact CDC §3.2 garanti
- Pas de debugging XLOOKUP imbriques
- Jules voit les memes resultats dans Sheets
- Version controlable (git blame sur l'algo)

**Inconvenient**:
- Pas de recalcul temps-reel dans Sheets (mais sync 4h suffit)

**Decision**: ADOPTE pour v1. Les formules Sheets restent comme "vue" supplementaire, pas source de verite.

---

## 2. Google Drive — Est-ce vraiment necessaire ?

### Pensee conventionnelle
"Les factures PDF doivent etre stockees dans Google Drive avec un folder hierarchy."

### Analyse first-principles

**Faits bedrock**:
- AIS **genere et stocke** deja les PDFs (Decision D7)
- SAP-Facture **ne cree PAS** de factures (Decision D1)
- Jules accede aux PDFs via le portail AIS
- Le champ `pdf_drive_id` dans Factures est **optionnel** (nullable)
- Jules a ~50 factures/an = ~50 PDFs = ~2.5 MB

**Questions destructrices**:
1. Pourquoi dupliquer des PDFs qui existent deja dans AIS ?
2. Qui consulte ces PDFs ? Jules (via AIS) ou son comptable ?
3. Si comptable: un lien AIS suffit-il, ou faut-il un fichier telecharge ?

### Verdict: DIFFERE, pas necessaire en v1

**Si besoin futur**: Lazy archive. Quand Jules exporte pour son comptable, telecharger depuis AIS a ce moment-la. Pas de sync permanente.

**Alternative creative**: Stocker l'URL AIS directe dans Sheets au lieu du pdf_drive_id. Zero API Drive, zero stockage, meme valeur pour Jules.

```python
# Au lieu de:
facture.pdf_drive_id = drive_adapter.upload(pdf_bytes)  # API Drive, stockage, dedup

# Faire:
facture.ais_pdf_url = f"https://app.avance-immediate.fr/demande/{ais_demande_id}/pdf"  # Zero cost
```

**Decision**: Phase 2+ uniquement si comptable a besoin de fichiers locaux.

---

## 3. Gmail — Simplification IMAP vs API

### Pensee conventionnelle
"Utiliser l'API Gmail (OAuth2) pour une meilleure securite et rate limits."

### Analyse first-principles

**Faits bedrock**:
- GmailReader (IMAP) est **deja implemente et teste** (215 lignes, 25+ tests)
- EmailNotifier (SMTP) est **deja implemente et teste** (183 lignes, 28 tests)
- Volume: ~10-20 emails/jour (1% du quota free Gmail)
- App password + 2FA = securite suffisante pour un micro-entrepreneur
- OAuth2 Gmail ajoute: consentement interactif, token refresh, scopes, complexity

**Cout de migration vers Gmail API**:
- Nouvelle dependance: `google-auth-oauthlib`
- Flow consentement: Jules doit ouvrir un navigateur la premiere fois
- Token storage: fichier `token.json` a securiser
- Token refresh: logique supplementaire
- Tests a reecrire
- **Zero valeur ajoutee** pour Jules

### Verdict: GARDER IMAP/SMTP (app password)

Le systeme actuel fonctionne. Migrer vers l'API Gmail n'apporte rien pour le volume de Jules. La complexite ajoutee est negative.

**Seul trigger de migration**: Si Google deprecie les app passwords (pas prevu avant 2028+).

---

## 4. SQLite + Sheets Hybrid — Architecture Alternative

### Idee creative

```
┌──────────┐    ┌──────────┐    ┌──────────────┐
│ SQLite    │ <- │ Services │ -> │ Google Sheets │
│ (local DB)│    │ (logique)│    │ (vue Jules)   │
└──────────┘    └──────────┘    └──────────────┘
  Source          Processing       Display
  de verite       layer            layer
```

**Principe**: SQLite est la source de verite locale. Google Sheets est un "dashboard" en lecture pour Jules.

**Avantages**:
- Queries SQL natives (JOIN, GROUP BY, WHERE) — pas de Polars gymnastics
- Offline-first: fonctionne sans internet
- Backup trivial: un fichier `.db`
- Migrations schema avec Alembic
- Transactions ACID (pas de race conditions Sheets)
- Tests 10x plus rapides (SQLite in-memory)

**Inconvenients**:
- Jules ne peut plus editer directement dans Sheets (perte d'interactivite)
- Sync bidirectionnelle complexe (Sheets -> SQLite si Jules modifie)
- Nouvelle dependance (alembic, aiosqlite)
- Le CDC specifie Google Sheets comme backend

### Verdict: Phase 2+ (apres validation v1)

**Quand considerer**: Si les limitations Sheets deviennent bloquantes:
- Race conditions sur writes concurrents
- Besoin de queries complexes (lettrage multi-factures)
- Volume > 1000 transactions/an
- Besoin de rollback/undo

**Pour v1**: Sheets reste le backend. Python (Polars) fait les calculs. Pas de SQLite.

---

## 5. Telegram Bot vs Email — Notifications

### Idee creative

Au lieu d'emails, un bot Telegram pour notifier Jules:

```
Jules                    Telegram Bot              SAP-Facture
  |                          |                         |
  |   <-- "Facture F001     |  <-- notify()           |
  |       en attente 36h"   |                         |
  |                          |                         |
  | "confirmer" -->          | --> confirm_lettrage()  |
  |                          |                         |
  | <-- "Lettrage OK,       |  <-- response           |
  |      score 100"          |                         |
```

**Avantages**:
- Reponse instantanee (push, pas pull)
- Jules peut **agir** depuis Telegram (confirmer lettrage, valider)
- Historique conversation (pas d'emails perdus)
- Pas de spam folder
- API simple (python-telegram-bot)

**Inconvenients**:
- Nouvelle dependance + setup (BotFather, token)
- Pas de templates HTML riches
- Moins formel (comptable prefere email)
- Jules doit utiliser Telegram

### Verdict: Phase 2+ (complement, pas remplacement)

Telegram pour les alertes urgentes (T+48h), email pour les confirmations formelles.
Implementation: ~2h avec `python-telegram-bot`. Pas prioritaire.

---

## 6. Template Spreadsheet vs API Creation

### Idee creative pour `sap init`

Au lieu de creer les 8 onglets programmatiquement via API:

**Option A**: Template spreadsheet
1. Creer manuellement un spreadsheet "template" avec les 8 onglets, headers, formules, formatage
2. `sap init` = `drive.files().copy(templateId)` (1 appel API)
3. Puis renommer et configurer

**Option B**: YAML formula config
```yaml
# config/sheets_formulas.yaml
lettrage:
  score_confiance: |
    =IF(ABS(Factures!J{row}-Transactions!D{row})=0, 50, 0)
    + IF(ABS(Factures!P{row}-Transactions!C{row})<=3, 30, 0)
    + IF(SEARCH("URSSAF", Transactions!E{row}), 20, 0)
  statut: |
    =IF(F{row}>=80, "LETTRE_AUTO", IF(F{row}>=1, "A_VERIFIER", "PAS_DE_MATCH"))
```

**Option C** (recommandee): API creation avec formules hardcodees en Python
- Plus de controle
- Versionnable
- Testable
- Pas de dependance sur un template externe

### Verdict: Option C (API creation) pour v1

Template spreadsheet = fragile (si quelqu'un modifie le template). API = deterministe.

---

## 7. Event-Driven vs Polling — Architecture Sync

### Pensee conventionnelle
"Cron job toutes les 4h qui scrape AIS + Indy."

### Analyse first-principles

**Faits bedrock**:
- AIS n'a pas de webhooks (pas d'API publique)
- Indy n'a pas de webhooks (pas d'API publique)
- Google Sheets n'a pas de push notifications vers Python
- Jules a ~4-8 factures/mois → 1 changement d'etat tous les 2-3 jours en moyenne
- Polling toutes les 4h = 6 scrapes/jour pour detecter 0-1 changement

**Question**: Est-ce que 6 scrapes inutiles par jour sont un probleme ?
**Reponse**: Non. Playwright prend ~10s par scrape. 60s/jour total. Cout zero.

**Alternative creative**: Event-driven via email parsing

```
AIS envoie email quand statut change
  --> GmailReader detecte l'email
    --> Parse le contenu (facture_id + nouveau statut)
      --> Update Sheets immediatement
```

**Avantages**: Detection instantanee, pas de scraping inutile
**Inconvenient**: AIS n'envoie pas forcement un email pour chaque changement

### Verdict: GARDER POLLING 4h (simple, fiable)

Le cout du polling est negligeable. La complexite d'un systeme event-driven ne se justifie pas pour ~1 event/2-3 jours.

**Optimisation future**: Reduire a 2 syncs/jour (9h et 17h) si les 4 syncs/jour n'apportent pas de valeur.

---

## 8. Polars Vectorise pour le Lettrage

### Idee creative: Lettrage 100% Polars (zero boucle)

Au lieu de:
```python
for invoice in invoices:
    for txn in transactions:
        score = compute_score(invoice, txn)
```

Faire:
```python
matched = (
    invoices_df
    .filter(pl.col("statut") == "PAYE")
    .join(transactions_df, how="cross")
    .with_columns([
        (pl.col("montant_total") == pl.col("montant")).cast(pl.Int32) * 50,
        (pl.col("date_diff").abs() <= 3).cast(pl.Int32) * 30,
        pl.col("libelle").str.contains("URSSAF").cast(pl.Int32) * 20,
    ])
    .with_columns(
        (pl.col("montant_score") + pl.col("date_score") + pl.col("label_score"))
        .alias("score_confiance")
    )
)
```

**Performance**:
- 50 factures x 400 transactions = 20,000 paires
- Polars vectorise: ~5ms
- Python boucles: ~50ms
- **10x plus rapide**, et le code est declaratif (lisible comme une spec)

### Verdict: ADOPTE pour LettrageService

Le lettrage Polars est plus rapide, plus lisible, et plus maintenable que des boucles imbriquees.

---

## 9. Cache Intelligent — Invalidation Selective

### Idee creative: Au lieu d'invalider tout le cache apres un write, invalider seulement l'onglet modifie.

**Pattern actuel**: `self._cache.clear()` apres tout write → force re-read de TOUS les onglets

**Pattern ameliore**:
```python
def append_rows(self, sheet_name: str, data: list) -> None:
    self._do_append(sheet_name, data)
    self._cache.invalidate(sheet_name)  # Seulement cet onglet
    # Les 7 autres onglets restent en cache
```

**Impact**: Si `sap sync` update Factures, les reads sur Clients/Transactions restent cached.
Reduction de 75% des reads API post-write.

### Verdict: ADOPTE (deja partiellement implemente dans SheetsAdapter)

---

## 10. Spreadsheet comme API — Pattern "Sheets as Backend"

### Observation creative

Google Sheets est utilise ici comme un backend **avec UI gratuite**. C'est un pattern sous-estime:

**Ce que Sheets donne gratuitement**:
- Interface CRUD (Jules peut editer directement)
- Filtrage, tri, recherche (Sheets native)
- Historique des modifications (version history)
- Partage avec comptable (permissions Google)
- Export CSV/Excel/PDF natif
- Formules pour calculs simples
- Graphiques (Balances, CA/mois)
- Mobile app (Google Sheets sur telephone)

**Ce que Sheets ne donne PAS**:
- Transactions ACID
- Queries complexes (JOIN multi-onglets)
- Webhooks / triggers
- Index / performance sur gros volumes
- Schema enforcement strict

**Pour ~50 factures/an et ~400 transactions**: Sheets est le backend **parfait**. Un PostgreSQL serait over-engineered. Un SQLite serait under-featured (pas d'UI).

### Verdict: VALIDE la decision D2 (Google Sheets 8 onglets)

Le CDC a fait le bon choix. Pour le volume de Jules, Sheets > SQLite > PostgreSQL.

---

## 11. Resilience Pattern — Graceful Degradation

### Idee creative: Que faire quand Google est down ?

```
Scenario: Google Sheets API renvoie 503 pendant 2h

Sans graceful degradation:
  sap sync → crash → Jules ne sait pas ce qui se passe

Avec graceful degradation:
  sap sync → detecte 503 → circuit breaker ouvert
    → log local JSON des changements non-ecrits
    → email Jules "Sheets indisponible, changements en attente"
    → prochain sync: rejouer les changements JSON
    → circuit breaker ferme → retour a la normale
```

**Implementation**:
```python
class SheetsAdapter:
    async def append_rows(self, sheet_name, data):
        try:
            self._do_append(sheet_name, data)
        except CircuitOpenError:
            # Sauvegarder localement
            self._save_to_local_queue(sheet_name, data)
            logger.warning("Sheets unavailable, queued locally")
```

### Verdict: Phase 2+ (nice-to-have)

Pour v1, le circuit breaker + retry 3x suffit. Le local queue est un luxe pour un micro-entrepreneur.

---

## 12. Scoring Adaptatif — Machine Learning Leger

### Idee creative pour Phase 3+

Apres N mois de lettrage, les poids du scoring (50/30/20) pourraient s'adapter:

```python
# Si historiquement le libelle est toujours "URSSAF":
#   → reduire le poids libelle (pas discriminant)
#   → augmenter le poids date (plus discriminant)

# Si historiquement l'ecart date est toujours 1-2 jours:
#   → resserrer la fenetre (3 jours → 2 jours)

# Si le taux A_VERIFIER > 30%:
#   → ajuster les seuils (80 → 75 ou 85)
```

**Implementation**: Simple regression logistique sur l'historique des confirmations manuelles de Jules.

### Verdict: Phase 3+ (apres 6 mois de donnees)

Pas de ML sans donnees. Commencer avec les poids fixes CDC, ajuster apres experience.

---

## Resume des Decisions Creatives

| # | Idee | Verdict | Phase |
|---|------|---------|-------|
| 1 | Python pre-compute + Sheets display | ADOPTE | v1 |
| 2 | Pas de Google Drive (URL AIS suffit) | ADOPTE | v1 (Drive en Phase 2+) |
| 3 | Garder IMAP/SMTP (pas Gmail API) | ADOPTE | v1 |
| 4 | SQLite + Sheets hybrid | DIFFERE | Phase 2+ |
| 5 | Telegram bot pour alertes | DIFFERE | Phase 2+ |
| 6 | API creation (pas template) pour sap init | ADOPTE | v1 |
| 7 | Polling 4h (pas event-driven) | ADOPTE | v1 |
| 8 | Polars vectorise pour lettrage | ADOPTE | v1 |
| 9 | Cache invalidation selective | ADOPTE | v1 |
| 10 | Sheets = backend parfait pour ce volume | VALIDE | v1 |
| 11 | Graceful degradation (local queue) | DIFFERE | Phase 2+ |
| 12 | Scoring adaptatif ML | DIFFERE | Phase 3+ |

---

## Gmail 2FA Auto-Inject — 10 Alternatives Évaluées

| # | Alternative | Verdict | Raison |
|---|---|---|---|
| 1 | IMAP + App Password | **ADOPTÉ** | Simple, stdlib, testé (GmailReader existe) |
| 2 | Gmail API + OAuth2 | DIFFÉRÉ | Over-engineered pour lire 1 email |
| 3 | Service Account Gmail | **REJETÉ** | Impossible sur Gmail personnel |
| 4 | POP3 | **REJETÉ** | Pas de labels, IMAP supérieur |
| 5 | Cloud Pub/Sub push | DIFFÉRÉ | Overkill pour ~4 events/mois |
| 6 | Zapier/Make.com webhook | **REJETÉ** | Dépendance externe, coût |
| 7 | TOTP (Authenticator) | N/A | Indy ne supporte pas TOTP |
| 8 | Session persistence seule | **ADOPTÉ** | Primary tier (30-90j cookies) |
| 9 | Manuel headed mode | FALLBACK | Dernier recours quand tout échoue |
| 10 | Google OAuth bypass | À INVESTIGUER | Bypass Turnstile + 2FA, tools/discover_indy_oauth.py |

### Architecture retenue (3 tiers)
```
Primary: Session cache (cookies nodriver, 30-90 jours)
Fallback 1: IMAP auto-2FA (GmailReader label Indy-2FA → code → inject)
Fallback 2: Headed manuel (Jules entre le code)
Future v2: Google OAuth (bypass total si client_id découvert)
```

### First-principles : Faut-il automatiser le 2FA ?
- Session persistence = 4 refreshs manuels/an = 20 min/an
- IMAP auto-2FA = 3h de dev, 0 min/an ensuite
- ROI positif dès la 2ème année (break-even à 9 mois)
- Mais surtout : permet le cron headless quotidien sans intervention
