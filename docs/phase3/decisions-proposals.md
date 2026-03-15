# Propositions de Décision — 7 Points Critiques SAP-Facture MVP

**Document** : Réponses argumentées aux questions de gate-check
**Destinataire** : Jules Willard (Product Owner) + Tech Lead
**Date** : 15 mars 2026
**Statut** : EN ATTENTE VALIDATION JULES
**Version** : 1.0

---

## Introduction

Le gate-check a identifié **7 décisions ouvertes** qui bloquent le démarrage du développement MVP. Ce document propose une réponse chaque décision, avec contexte, arguments, alternatives et impact de l'indécision.

**Format pour chaque décision** :
- Rappel du contexte et de l'enjeu
- Proposition recommandée avec justification technique/métier
- Alternative(s) envisagée(s)
- Impact si on ne décide pas
- Signature Jules pour validation

---

## D1 : Fréquence Polling URSSAF — 4h vs 2h vs Événementiel ?

### Contexte & Enjeu

Le gate-check pose la question : **Polling URSSAF toutes les 4h suffisant pour MVP ?**

**Baseline actuelle** (product-brief.md H1) : 4h.

**Scenario critique** :
- Jules crée facture 10h du matin
- Client URSSAF reçoit email et valide immédiatement (10h30)
- Polling suivant : 14h (délai 4h)
- Jules ne voit "VALIDE" que 4h plus tard alors que client a validé immédiatement
- Délai d'attente perçu : inutile frustration

**Impacte** : M5 (PaymentTracker), CPU + Google Sheets API quota.

### Proposition Recommandée : **Démarrer 4h, escalader à 2h en Phase 2**

#### Justification

1. **Réalité facturation Jules**
   - Jules ~5-10 factures/mois = 1-2 par jour en moyenne
   - Delai paiement URSSAF nominale : J+1 à J+3 (pas ultra-urgent)
   - Validation client : généralement dans 24h (95% cas H7)
   - **Conclusion** : Attendre 4h entre polling ne coûte rien en pratique

2. **Coûts ressource**
   - Polling 4h = 6 appels/jour par facture en cours = manageable
   - Polling 2h = 12 appels/jour = double la charge API URSSAF + Sheets
   - Pour auto-entrepreneur solo : coût CPU négligeable, mais quota Sheets Google = 300 req/min
   - **Conclusion** : 4h c'est un bon sweet spot MVP

3. **Hypothèse H1 validable**
   - Statut URSSAF : CREE → EN_ATTENTE (quelques min après soumission)
   - EN_ATTENTE → VALIDE (client peut valider immédiatement ou 48h max)
   - Polling 4h max = 12 updates en 48h = sufficient de couverture
   - **Conclusion** : H1 acceptée pour MVP, revisiter Phase 2 si données prouvent TTL client < 4h

#### Implémentation MVP

```python
# APScheduler : 4h fix
POLLING_INTERVAL_HOURS = 4

# Logging
logger.info(f"Polling URSSAF {len(pending_invoices)} invoices, next check in {POLLING_INTERVAL_HOURS}h")

# Dashboard : afficher "Dernière synchro : X min ago" (rouge si > 4.5h)
```

#### Phase 2 : Escalade Conditionnelle

- **Si données réelles montrent** : 80%+ clients valident < 2h → passer à 2h
- **Sinon** : rester 4h (plus économe)
- **Alternative future** : Webhook URSSAF (n'existe pas MVP, rester sur polling)

### Alternatives Considérées

| Alternative | Avantages | Inconvénients | Verdict |
|-----------|-----------|---------------|---------|
| **2h (agressif)** | Visibilité immédiate client valide | Double quota API + CPU ; overkill MVP | Rejeter MVP, Phase 2 OK |
| **6h (économe)** | Réduit quota ; parfait si factures pas urgentes | Trop long, client oublie + délai expiration | Rejeter, trop risqué |
| **Événementiel (webhook)** | Zéro polling, immédiat | N'existe pas URSSAF API | Future seulement |
| **Hybrid 4h + CLI sync** | 4h auto + Jules peut forcer `sap sync` immédiat | Meilleur des deux | Retenir pour Phase 2 |

### Impact si Pas de Décision

- Coding atrophié : dev hésite sur le sleep() du scheduler
- Test suite incomplète : pas de fixture délai polling standardisé
- Phase 2 bloquée : impossible évaluer performance réelle

### Signature Jules

**Décision** : [À signer]
Proposé : **4h MVP, escalade 2h Phase 2 si données justifient**
Jules valide :  _____________  Date : _______

---

## D2 : Email Sender — URSSAF vs SAP-Facture vs Hybride ?

### Contexte & Enjeu

Le gate-check soulève : **Qui envoie email reminder T+36h ? SAP-Facture ou URSSAF ?**

**Background** :
- URSSAF envoie email validation initiale (natif, obligatoire)
- Reminder T+36h si client n'a pas validé = **enhancement SAP-Facture**
- **Question** : Quel sender pour que client reconnaisse ?

**3 scenarios** :

| Scenario | Email From | Pro | Con |
|---------|-----------|-----|-----|
| **A: URSSAF envoie tout** | `no-reply@urssaf.fr` | Client reconnaît source officielle | API URSSAF n'a pas endpoint reminder |
| **B: SAP-Facture envoie** | `no-reply@sap-facture.fr` ou `jules@...` | Contrôle total, peut ajouter contexte perso | Risque SPAM, "unknown sender" |
| **C: Hybride (D2 recommandée)** | URSSAF initial + SAP-Facture T+36h relance | Meilleur des deux, chaque acteur son rôle | Légèrement plus complexe |

**Enjeu** : Acceptabilité client, délivrabilité email, conformité.

### Proposition Recommandée : **Hybride — URSSAF Initial + SAP-Facture Relance**

#### Justification

1. **Rôles clairs et légitimes**
   - URSSAF = autorité officielle pour validation initial
   - SAP-Facture = assistant Jules pour relance intermédiaire
   - **Psychologie client** : Moins de SPAM perçu, deux sources = crédibilité

2. **Contenu différencié**
   - Email URSSAF (T+0) : "Validez votre demande paiement [lien portail officiel]"
   - Email SAP-Facture (T+36h) : "Jules vous relance : encore 12h pour valider votre facture [lien + contexte perso]"
   - **Avantage** : Email relance peut inclure contexte (nom cours, montant) que URSSAF ne ferait pas

3. **Implémentation simple**
   - EmailNotifier envoie juste depuis config SMTP (Gmail ou Brevo)
   - Template : "Rappel de Jules Willard : validez ici" (pas imitation URSSAF)
   - **Techniquement** : 20 lignes Python, no OAuth2 bearer token needed

4. **Délivrabilité**
   - SAP-Facture depuis adresse perso Jules (`jules@...` ou relay pro) = mieux que no-reply générique
   - SPF/DKIM config simples (Gmail OK)
   - **Risk** : Faible pour micro volume (1-2 emails/jour)

#### Implémentation MVP

```python
# EmailNotifier service
class EmailNotifier:
    def __init__(self, smtp_host: str, smtp_user: str, smtp_pass: str):
        self.smtp = smtplib.SMTP(smtp_host, 587)
        self.from_addr = smtp_user  # e.g., "jules@exemple.fr"

    def send_reminder_t36h(self, invoice: Invoice, client_email: str):
        subject = f"Rappel Jules Willard : validez votre facture"
        body = f"""
        Bonjour,

        Jules vous relance : vous avez reçu une demande de paiement URSSAF
        (montant: {invoice.montant}€) et devez la valider dans les 12 prochaines heures.

        Lien de validation : https://monespace.urssaf.fr/...
        Contact Jules : {jules.contact}

        Cordialement,
        SAP-Facture
        """
        self.smtp.send_message(subject, self.from_addr, client_email, body)
```

### Alternatives Considérées

| Alt | Sender | Contenu | Verdict |
|-----|--------|---------|---------|
| **A: URSSAF tout** | URSSAF API | "Deuxième rappel" imitation | Impossible : pas d'endpoint URSSAF reminder |
| **B: SAP-Facture tout** | `no-reply@sap-facture` | "Validez votre facture" | Risque SPAM, confusant (quoi difference avec URSSAF ?) |
| **C: Hybride (prop)** | URSSAF + SAP-Facture perso | Deux emails clairs | **Meilleur** |
| **D: SMS au lieu email** | SMS provider (Twilio) | "Jules vous relance" | Phase 2 OK, MVP trop coûteux |

### Impact si Pas de Décision

- EmailNotifier stub vide, phase 2 codefreeze
- Reminder T+36h implémenté mais pas testé
- Client confusion : plusieurs emails, pas clair qui envoie

### Signature Jules

**Décision** : [À signer]
Proposé : **Hybride — URSSAF initial + SAP-Facture relance T+36h depuis adresse perso**
Jules valide :  _____________  Date : _______

---

## D3 : CREE → EN_ATTENTE Transition — Trigger Automatique ou Polling ?

### Contexte & Enjeu

Gate-check point critique : **Comment SAP-Facture sait que statut URSSAF = EN_ATTENTE ?**

**Scenario actuel** :
1. Jules soumet facture → API URSSAF accepte → réponse `{statut: CREE}`
2. SAP-Facture reçoit CREE, met à jour Sheets
3. **Question** : Quand passer CREE → EN_ATTENTE ?
   - **Option A** : Immédiatement après réception CREE (assumption : email client parti)
   - **Option B** : Polling détecte EN_ATTENTE (garantie email reçu)

**Impacte** : M4, M5 — timing reminder T+36h dépend du moment où EN_ATTENTE est détecté.

### Proposition Recommandée : **Immediate après POST /demandes-paiement (Assumption)**

#### Justification

1. **URSSAF Behavior Probable**
   - URSSAF API responds `{statut: CREE}` = demande créée ET email envoient asynchrone
   - Email généralement parti < 1min après création
   - **Assumption basée** : Si API accepte POST, email est en queue URSSAF
   - **Validation** : À tester Phase 1 gate review avec données réelles

2. **Timing Reminder Critique**
   - Reminder T+36h dépend du timestamp EN_ATTENTE
   - Si on attend polling 4h pour marquer EN_ATTENTE, reminder décalé -4h à +4h (9h spread !)
   - **Consequence** : Client peut ne pas recevoir reminder (si validation rapide J+1 16h vs reminder J+1 20h)

3. **Implémentation Simple**
   - Après `response.status_code == 201` from POST /demandes-paiement :
   - Statut Sheets : BROUILLON → SOUMIS → CREE → **EN_ATTENTE** (immédiatement)
   - Timestamp `en_attente_at` = now()
   - **Code** : 3 lignes dans InvoiceService

#### Implémentation MVP

```python
class InvoiceService:
    async def submit_to_urssaf(self, invoice_id: str) -> Invoice:
        invoice = self.sheets_adapter.get_invoice(invoice_id)

        # Step 1: Create demand at URSSAF
        payload = build_urssaf_payload(invoice)
        response = await self.urssaf_client.post_demands(payload)

        if response.status_code != 201:
            raise SubmissionError(response.text)

        # Step 2: Parse response
        data = response.json()
        urssaf_demand_id = data["id"]

        # Step 3: Immediately mark EN_ATTENTE (email gone to URSSAF queue)
        invoice.statut = "EN_ATTENTE"
        invoice.urssaf_demand_id = urssaf_demand_id
        invoice.en_attente_at = datetime.now(timezone.utc)

        self.sheets_adapter.update_invoice(invoice)
        logger.info(f"Invoice {invoice_id} → EN_ATTENTE, reminder scheduled T+36h")

        return invoice
```

### Alternatives Considérées

| Alt | Trigger | Pro | Con |
|-----|---------|-----|-----|
| **A: Immediate (prop)** | POST accepts → EN_ATTENTE | Reminder timing accurate | Assumes email sent (unconfirmed) |
| **B: Polling detects** | GET /demandes-paiement shows EN_ATTENTE | Garantie email détecté | Reminder délai +0 to +4h, suboptimal |
| **C: Webhook URSSAF** | Email delivery webhook | Parfait, certainty 100% | N'existe pas URSSAF |

### Validation Phase 1 Gate Review

**Action avant dev** : Tester avec 5 factures réelles :
- Soumettre via SAP-Facture
- Mesurer : temps entre POST response et email client reçu
- Si < 1 min : assumption validée, go immediate
- Si > 5 min : revenir polling

### Impact si Pas de Décision

- Reminder T+36h implémentation floue
- Test fixtures indéterministes (timestamp varie)
- Phase 1 gate : impossible mesurer "reminder fonctionne"

### Signature Jules

**Décision** : [À signer]
Proposé : **Immediate EN_ATTENTE après POST accepté (valider T+1h en gate review)**
Jules valide :  _____________  Date : _______

---

## D4 : Priorité CLI vs Web pour MVP ?

### Contexte & Enjeu

Gate-check note : **M7 (CLI submit) et M2 (web form) = duplicate features. Qui d'abord ?**

**Baseline** (MVP scope) :
- M2 : Web form créer facture (UI web)
- M7 : CLI `sap submit` (terminal)
- Effort estimé : M2 = 8 points, M7 = 5 points
- **Question** : On les fait tous deux MVP ? Ou prioriser ?

**Contexte utilisateur Jules** :
- Utilise 50/50 CLI + Web (hypothèse H4 non validée)
- Après cours : web UI (rapide, visuel, à côté du planning)
- Batch operations (dimanche soir) : CLI possible (JSON batch)

### Proposition Recommandée : **Web Prioritaire MVP1, CLI Phase 2**

#### Justification

1. **MVP Critique = Web**
   - **First-time experience** : Jules doit pouvoir créer facture sans terminal
   - **UX friction** : 90% utilisateurs préfèrent UI graphique pour data entry
   - **Accessibility** : Web mobile-friendly (futur), CLI terminal-only
   - **Donnée manquante** : H4 jamais validée (savoir si Jules aime vraiment CLI)
   - **Conclusion** : Web est le "must-have" pour MVP validation utilisateur

2. **Effort Trade-off**
   - Web M2 : 8 points = ui form + validation + pdf generation + submission
   - CLI M7 : 5 points = click wrapper autour InvoiceService
   - **If we delay CLI** : Nous économisons 5 points, accélérons Phase 1 livraison
   - **Itération rapide** : Jules peut utiliser Web MVP1, feedback pour CLI Phase 2

3. **Réalité Phase 1**
   - Phase 1 gate review : 48h prod test, E2E web form → VALIDE
   - Pas de time pour tester CLI simultaneously
   - **Decision** : Keep scope focused, Phase 2 ajoute CLI comfort

4. **Fallback Web**
   - Si Jules réclame CLI urgence Phase 2 : "OK, faisons-le"
   - Si usage data montre 10% utilisation web vs 90% CLI : Pivot Phase 2
   - **Flexibility** : Pas de commitments long-term, data-driven

#### Implémentation MVP

```python
# FastAPI web endpoint (MVPv1 prioritaire)
@app.post("/invoices")
async def create_invoice(
    client_id: str,
    hours: float,
    rate: float,
    dates_start: date,
    dates_end: date,
) -> dict:
    """Web form endpoint — prioritaire MVP"""
    invoice = await invoice_service.create(...)
    return {"invoice_id": invoice.id, "status": "BROUILLON"}

# CLI stub (Phase 2 impl, keep skeleton MVP)
@click.command()
@click.option("--client", required=True)
@click.option("--hours", type=float, required=True)
def submit_cli(client: str, hours: float):
    """CLI stub for Phase 2"""
    click.echo("Phase 2 feature, use web for now")
```

### Alternatives Considérées

| Alt | Priorité | Avantage | Inconvénient |
|-----|----------|----------|-------------|
| **A: Web MVP** (prop) | Web first, CLI Phase 2 | MVP focused, faster delivery, flexible | CLI users wait 2 weeks |
| **B: Both MVP** | Web + CLI parallel | Choice pour Jules day 1 | Effort +13 points, Phase 1 bloated, less stable |
| **C: CLI MVP** | CLI first, Web Phase 2 | Terminal-native, scriptable | 90% users frustrated, UX weak |
| **D: Defer both** | GoogleSheets only MVP | MVP super lean | Jules can't use, defeats purpose |

### Validation & Monitoring Phase 1

**Metrics** : Track dans logs
```python
# Dashboard analytics
POST /invoices → web_count += 1
sap submit → cli_count += 1
# At Phase 1 gate : web_count vs cli_count → decide escalation
```

### Impact si Pas de Décision

- Dev paralysé : "Do we code CLI first or web?"
- UI/CLI team conflict : unclear prioritization
- Phase 1 delayed : trying to do both → quality suffers

### Signature Jules

**Décision** : [À signer]
Proposé : **Web prioritaire MVP1 (8 pts), CLI Phase 2 (5 pts) — basé usage réel**
Jules valide :  _____________  Date : _______

---

## D5 : SwanClient Implementation — GraphQL vs REST ?

### Contexte & Enjeu

Gate-check critique : **Swan API pour rappro bancaire (P2A). GraphQL ou REST ?**

**Background** :
- Swan = banque digitale, API transactions pour rapprochement
- Gate-check says : "Product-brief.md dit 'Swan GraphQL ou REST' sans décider"
- **Enjeu** : Architecture client SwanClient, test fixtures, performance
- **Impacte** : P2A (Phase 2, mais affect architecture MVP)

**Comparaison** :

| Aspect | GraphQL | REST |
|--------|---------|------|
| **Flexibilité** | Query exact fields needed | Fixed response shape |
| **N+1 problem** | Mitigated (single query) | Possible (multiple endpoints) |
| **Complexity** | Apollo client, query DSL | Standard HTTP lib |
| **Testing** | Mock server complex | Mock HTTP responses simple |
| **Docs** | May be less clear | Standard REST conventions |

### Proposition Recommandée : **REST pour MVP, GraphQL Phase 3**

#### Justification

1. **MVP = Simplicité**
   - REST : 1 endpoint GET /accounts/{id}/transactions?date_from=...&date_to=...
   - Return JSON array, simple mapping
   - **No** query language learning curve
   - **No** Apollo client/middleware layer

2. **Swan API Reality**
   - Docs.swan.io supports both GraphQL AND REST
   - REST endpoints bien documentés, RESTful design
   - MVP case : "get last 30 transactions" = 1 REST GET call, done
   - **No need** for GraphQL flexibility MVP

3. **Testing & Performance**
   - REST mocks : gotta `responses.add()` library, pytest trivial
   - GraphQL mocks : need mock server setup, more fragile
   - Performance : both negligible for Jules (10 transactions/day)
   - **MVP pragmatic** : REST wins for velocity

4. **Phase 2 Reality**
   - Rappro bancaire phase 2 = 1-2 queries simple
   - Pas besoin GraphQL nested aliasing ou fragments
   - Si Phase 3 ajoute reporting complexe → GraphQL optionnel futur

#### Implémentation MVP

```python
# SwanClient using REST (MVP simple)
class SwanClient:
    def __init__(self, api_token: str, account_id: str):
        self.base_url = "https://api.swan.io/rest"
        self.headers = {"Authorization": f"Bearer {api_token}"}
        self.account_id = account_id

    async def get_transactions(
        self,
        date_from: date,
        date_to: date,
    ) -> list[Transaction]:
        """GET /accounts/{id}/transactions — REST simple"""
        params = {
            "dateFrom": date_from.isoformat(),
            "dateTo": date_to.isoformat(),
        }
        response = await self.http_client.get(
            f"{self.base_url}/accounts/{self.account_id}/transactions",
            headers=self.headers,
            params=params,
        )
        data = response.json()
        return [Transaction.parse_obj(t) for t in data["transactions"]]
```

### Test Fixture (REST simple)

```python
# tests/fixtures/swan_fixtures.py
@pytest.fixture
def mock_swan_transactions():
    transactions = [
        {
            "id": "TXN001",
            "date": "2026-03-10",
            "amount": 100.00,
            "libelle": "URSSAF VIREMENT",
        },
        ...
    ]
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            "https://api.swan.io/rest/accounts/ACC123/transactions",
            json={"transactions": transactions},
            status=200,
        )
        yield rsps
```

### Alternatives Considérées

| Alt | API Type | Avantage | Inconvénient | Verdict |
|-----|----------|----------|-------------|---------|
| **A: REST (prop)** | REST | Simple, documented, MVP focus | Less flexible future | **MVP GO** |
| **B: GraphQL** | GraphQL | Flexible, elegant | Over-engineered MVP | Phase 3 if needed |
| **C: Both (adaptive)** | REST + GraphQL abstraction layer | Future-proof | Complexity overkill | Avoid complexity |

### Migration Path Phase 3

- If reporting demands complexe query nested → refactor SwanClient to GraphQL
- Abstraction: `class TransactionRepository` wraps both clients
- **No rework** : Just add GraphQL endpoint under same interface

### Impact if Decision Deferred

- P2A (Phase 2) coding stalled : "Which API format?"
- Test suite partial : can't mock without known endpoint format
- Architecture undecided : SheetsAdapter calls SwanClient, needs contract

### Signature Jules

**Décision** : [À signer]
Proposé : **REST pour MVP (simpler), GraphQL Phase 3 (if needed)**
Jules valide :  _____________  Date : _______

---

## D6 : Rapprochement Bancaire — Auto vs Manual Confirmation ?

### Contexte & Enjeu

Gate-check asks : **BankReconciliation PAYE → RAPPROCHE : auto ou Jules confirms ?**

**Two approaches**:

| Approche | Flow | Pros | Cons |
|----------|------|------|------|
| **Auto if score ≥ 80** | Scoring algorithm → auto-lettre facture si confident | Zéro friction Jules, 80% cas OK | 20% cas ambigus non-résolu, faux positifs possible |
| **Manual always** | Scoring suggest → Jules click "lettre" manuellement | 100% accuracy, Jules controls | Charge +30min/mois per 10 factures, tedious |
| **Hybrid (prop)** | Score ≥ 80 → auto, < 80 → "À VERIFIER" flag | Best of both, safe by default | Slightly more code (workflow states) |

**Enjeu** : Automatisation target vs Risk contrôle qualité.

### Proposition Recommandée : **Hybrid — Auto (≥80) + Manual Review (<80)**

#### Justification

1. **H3 Validation nécessaire**
   - Gate-check : H3 = "Matching 80% auto valide" = **non testé**
   - Réalité : Peut-être seulement 60% auto en pratique
   - **Risk** : Si < 70%, charge manual = 1-2h/mois = inacceptable
   - **Mitigation** : Hybrid permet validation progressive

2. **MVP Pragmatique**
   - Commencer hybrid : permet démarrer dev (R9 mitigation clear)
   - Phase 1 gate : Tester matching algo sur 20-30 transactions réelles
   - Phase 2 : Escalade à 100% auto si données prouvent 80%+ ratio
   - **Flexibility** : Pas de commitments prematures

3. **Score Meaning**
   - **≥ 80** = "Very Confident" (montant exact + date close + libellé match)
   - **60-79** = "Probably OK" (2 critères OK, 1 weak)
   - **< 60** = "Uncertain" (might be different payment)
   - **Psychological** : Jules voit orange flag = "vérifie quand tu as 2 min"

4. **User Experience**
   - Dashboard affiche onglet "Rapprochement Bancaire" avec 3 sections :
     - ✅ Auto-lettrées (score ≥ 80) : juste affichage, done
     - ⚠️ À Vérifier (60-79) : orange row, Jules peut cliquer "OK" ou "Non c'est pas ça"
     - ❌ Pas de match : red, attendre virement URSSAF ou Jules matche manuellement
   - **Effort Jules** : < 30 sec par facture ambigüe (optionnel)

#### Implémentation MVP

```python
class BankReconciliation:
    def match_transactions(self, invoice: Invoice) -> MatchResult:
        """Hybrid scoring : auto if ≥ 80, else manual review"""
        transactions = self.swan_client.get_transactions(
            date_from=invoice.payment_date - timedelta(days=5),
            date_to=invoice.payment_date + timedelta(days=5),
        )

        best_match = None
        best_score = 0

        for txn in transactions:
            score = self._score_transaction(invoice, txn)
            if score > best_score:
                best_score = score
                best_match = txn

        if best_match is None:
            return MatchResult(
                status="PAS_DE_MATCH",
                score=0,
                requires_manual_review=True,
            )

        if best_score >= 80:
            # Auto-lettre
            self.sheets_adapter.mark_lettered(invoice.id, best_match.id, best_score)
            logger.info(f"Invoice {invoice.id} auto-lettered, score {best_score}")
            return MatchResult(
                status="LETTRE_AUTO",
                score=best_score,
                transaction_id=best_match.id,
            )
        else:
            # Flag for manual review
            self.sheets_adapter.flag_review(invoice.id, best_match.id, best_score)
            logger.info(f"Invoice {invoice.id} flagged review, score {best_score}")
            return MatchResult(
                status="A_VERIFIER",
                score=best_score,
                transaction_id=best_match.id,
                requires_manual_review=True,
            )

    def _score_transaction(self, invoice: Invoice, txn: Transaction) -> int:
        """Scoring algorithm : max 100 points"""
        score = 0

        # Montant exact : +50
        if abs(invoice.montant - txn.amount) < 0.01:
            score += 50
        elif abs(invoice.montant - txn.amount) < 1.00:
            score += 25  # Close enough (rounding tolerance)

        # Date < 3j : +30
        days_diff = abs((invoice.payment_date - txn.date).days)
        if days_diff == 0:
            score += 30
        elif days_diff <= 3:
            score += 20
        elif days_diff <= 5:
            score += 10

        # Libellé contient URSSAF : +20
        if "URSSAF" in txn.libelle.upper() or "VIREMENT" in txn.libelle.upper():
            score += 20

        return score
```

### Dashboard UI Mockup

```
┌─────────────────────────────────────────────┐
│ Rapprochement Bancaire (P2A)                │
├─────────────────────────────────────────────┤
│ ✅ Auto-Lettrées (8)                        │
│   Invoice#1 : 100€ ← TXN#001 score 95      │
│   Invoice#2 : 50€ ← TXN#002 score 92       │
│   ...                                       │
├─────────────────────────────────────────────┤
│ ⚠️  À Vérifier (2) — Click to confirm      │
│   Invoice#10 : 75€ ↔ TXN#010 score 65      │
│   └─ [✓ OK] [✗ C'est pas ça]               │
│   Invoice#11 : 50€ ↔ TXN#011 score 72      │
│   └─ [✓ OK] [✗ C'est pas ça]               │
├─────────────────────────────────────────────┤
│ ❌ Pas de Match (1) — Attendre URSSAF      │
│   Invoice#12 : 120€ (virement non reçu)    │
│   └─ Attendre J+3 ou matcher manuellement  │
└─────────────────────────────────────────────┘

Résumé : 8 auto, 2 pending review, 1 waiting
```

### H3 Validation Plan (Phase 1 Gate)

Before Phase 2 coding:
1. Export 50 dernières factures PAYE + transactions Swan réelles
2. Run matching algo offline
3. Mesurer : % auto vs manual ratio
4. **If ≥ 80% auto** → escalade Phase 2 à "100% auto if desired"
5. **If 60-79%** → keep hybrid, acceptable
6. **If < 60%** → reweigh scoring (add heuristics) or accept manual charge

### Alternatives Considérées

| Alt | Strategy | Pro | Con |
|-----|----------|-----|-----|
| **A: Hybrid (prop)** | Auto ≥80, else review | Safe, flexible, MVP-ready | Slightly complex workflow |
| **B: Always auto** | All lettrage auto (≥80 or > best match) | Simplest | Risk faux positifs, no human check |
| **C: Always manual** | Jules confirms every | 100% accurate | 1-2h/month tedious, defeats automation |
| **D: Defer entirely** | Phase 2 only, not MVP | Focus MVP core | No lettrage MVP, incomplete cycle |

### Impact if Decision Deferred

- P2A architecture unclear : "Should we build manual workflow or auto?"
- Tests incomplete : no hypothesis on auto %
- Phase 1 gate : cannot validate "80% auto works"

### Signature Jules

**Décision** : [À signer]
Proposé : **Hybrid — Auto (score ≥80) + Manual Review (<80), validate H3 Phase 1 gate**
Jules valide :  _____________  Date : _______

---

## D7 : PDF Storage — Google Drive vs Local Repo ?

### Contexte & Enjeu

Gate-check asks : **PDFs générés : où stockés ? Google Drive vs local repo ?**

**Scenario**:
- Jules crée facture → PDF généré (WeasyPrint) → Où sauvegarde-t-on ?
- M3 (PDF generation) dépend de cette décision
- **Impact** : Architecture file storage, retention, accessibilité Jules

| Approche | Stockage | Avantages | Inconvénients |
|----------|----------|-----------|--------------|
| **Local Repo** | `/invoices/pdfs/` dans git (ou gitignore LFS) | Simpl, backup git natif | Git bloat, not accessible remote, local-only |
| **Google Drive** | Folder "SAP-Facture/Factures", API upload | Persistent, shareable Jules, cloud native | API quota, additional dependency |
| **Hybrid (prop)** | Local cache + Drive sync | Best perf + persistence | Slightly more code (sync logic) |

### Proposition Recommandée : **Google Drive + Local Cache (Hybrid)**

#### Justification

1. **Accessibilité Jules**
   - Jules doit pouvoir retrouver facture PDF 3 mois après
   - **Local only** = dépend du laptop, problème si device perte
   - **Drive** = accessible anywhere, web browser, shared avec comptable optional
   - **UX Win** : Jules clique lien dans Sheets → PDF opens Drive

2. **Architecture Cloud-Native**
   - SAP-Facture déjà centralisé Google Sheets
   - PDFs dans Drive = cohérent, une source (Sheets + Drive)
   - **Fallback** : Si SAP-Facture down, Jules still has Sheets + PDFs
   - **Not lock-in** : PDFs standard format, can export anytime

3. **Local Cache pour Performance**
   - Drive API : upload 100KB PDF ~500ms, acceptable mais not instant
   - **Solution** : Cache local `/tmp/pdf_cache/`, réutiliser si exists
   - Sync async : upload en background, répondre Jules immédiatement "PDF prêt"
   - **Benefit** : Feel fast for user, no network blocker

4. **Quota & Costs**
   - Google Drive free : 15GB (plenty for micro entrepreneur)
   - PDFs : ~100-500KB per invoice
   - 50 invoices/year = ~30MB max, non-issue
   - **Cost** : Zero (free tier)

#### Implémentation MVP

```python
# PDFGenerator avec caching + async upload
class PDFGenerator:
    def __init__(self, sheets_adapter, drive_client):
        self.sheets_adapter = sheets_adapter
        self.drive_client = drive_client
        self.cache_dir = Path("/tmp/pdf_cache")
        self.cache_dir.mkdir(exist_ok=True)

    async def generate_and_store(self, invoice: Invoice) -> str:
        """Return PDF download URL (local first, then Drive)"""
        # Check cache
        cache_path = self.cache_dir / f"{invoice.id}.pdf"
        if cache_path.exists():
            return str(cache_path)

        # Generate PDF
        html = self._render_template(invoice)
        pdf_bytes = weasyprint.HTML(string=html).write_pdf()

        # Save local
        cache_path.write_bytes(pdf_bytes)

        # Upload Drive async (non-blocking)
        asyncio.create_task(self._upload_to_drive(invoice.id, pdf_bytes))

        # Return local for immediate access
        return str(cache_path)

    async def _upload_to_drive(self, invoice_id: str, pdf_bytes: bytes):
        """Async background upload to Drive"""
        drive_file_id = await self.drive_client.upload(
            filename=f"Facture_{invoice_id}.pdf",
            folder_id="FACTURES_FOLDER_ID",
            data=pdf_bytes,
        )
        logger.info(f"PDF uploaded to Drive: {drive_file_id}")

        # Update Sheets with Drive link
        self.sheets_adapter.update_invoice_pdf_link(
            invoice_id,
            f"https://drive.google.com/file/d/{drive_file_id}",
        )
```

### Alternatives Considérées

| Alt | Stockage | Pro | Con | Verdict |
|-----|----------|-----|-----|---------|
| **A: Local only** | `/invoices/pdfs/` git-ignored | Simple | Inaccessible remote, device-bound | ❌ MVP not ideal |
| **B: Drive only** | Cloud Google Drive | Cloud-native, shared | API call required, ~500ms latency | ✅ Acceptable |
| **C: Hybrid (prop)** | Local cache + Drive sync | Best perf + persistence | Async sync logic | ✅ **Best** |
| **D: S3/Minio** | Cloud object storage | Scalable | Overkill micro (coûteux), external account | ❌ Avoid |

### Migration Path Phase 2

- If Drive API quota issues arise : add caching TTL (e.g., 24h before purge)
- If users need advanced org : Drive folder structure per year → easily expand

### Impact if Decision Deferred

- M3 implementation partial : where to `write_bytes(pdf)`?
- Test fixtures uncertain : mock local path vs Drive API?
- Phase 2 : no versioning/history of PDFs (if local-only)

### Signature Jules

**Décision** : [À signer]
Proposé : **Hybrid — Google Drive + Local Cache (async upload, zero API cost)**
Jules valide :  _____________  Date : _______

---

## Synthèse : Tableau de Décisions

| Décision | Proposition | Justification Clé | Phase | Risque |
|----------|-------------|------------------|-------|--------|
| **D1** | 4h polling MVP, 2h Phase 2 | Sweet spot quota API, H1 validable | MVP→2 | Basse : escalade facile |
| **D2** | Hybride : URSSAF + SAP-Facture | Rôles clairs, meilleure délivrabilité | MVP→2 | Très basse : email simple |
| **D3** | Immediate EN_ATTENTE post-API | Reminder timing correct, 3 lignes code | MVP | Moyenne : valider T+1h gate |
| **D4** | Web MVP, CLI Phase 2 | UX priority, flexible, faster delivery | MVP→2 | Très basse : CLI facile ajouter |
| **D5** | REST MVP, GraphQL Phase 3 | Simplicité dev, P2A non-urgent | MVP→3 | Très basse : abstraction possible |
| **D6** | Hybrid (auto ≥80, review <80) | H3 validation, safe progressive | MVP→2 | Haute : valider H3 en gate |
| **D7** | Google Drive + Local Cache | Accessibilité Jules, quota-free, perf | MVP | Très basse : standard pattern |

---

## Actions Immédiates — Sprint 0

**Avant dev code** (ordre critique) :

1. **Jules signe 7 décisions** (J+0, EOD)
   - Documents = decision-proposals.md signed
   - Pas de blocage dev après ça

2. **Tech Lead valide contraintes** (J+1 morning)
   - D1 : APScheduler config compatible
   - D2 : SMTP provider choisi (Gmail free ou Brevo ?)
   - D3 : Test fixture pour EN_ATTENTE timing
   - D5 : Swan REST endpoints mappés
   - D6 : Scoring algo pseudo-code review
   - D7 : Google Drive API access configured

3. **Phase 1 Gate Validation Plan** (J+1 afternoon)
   - Write `docs/phase1/gate-review-checklist.md`
   - D3 : Mesurer temps EN_ATTENTE (target < 2 min)
   - D6 : H3 validation test sur 20 transactions réelles

4. **Démarrage Dev** (J+2)
   - MVP code commence, decisions locked
   - No scope creep mid-sprint

---

## Signature Finale — Approbation Jules + Tech Lead

### Product Owner (Jules Willard)

**Je confirme** que j'ai lu toutes les 7 propositions de décision et je valide l'approche recommandée pour démarrer le développement MVP de SAP-Facture.

**Signature Jules** : _________________________
**Date** : _______

---

### Tech Lead

**Je confirme** que les décisions proposées sont techniquement faisables dans les délais MVP (1 semaine pour Phase 1, 2-3 semaines pour Phase 2).

**Signature Tech Lead** : _________________________
**Date** : _______

---

## Annexe : Risques Résiduels Acceptés

| Risque | Mitigation | Owner | Review |
|--------|-----------|-------|--------|
| H3 validation (D6) | Test algo phase 1 gate avec données réelles | QA | J+5 |
| D3 timing EN_ATTENTE | Measure < 2 min latency post-API response | Dev | J+3 |
| D2 email deliverability | Test Gmail SMTP, SPF/DKIM config | Dev | J+2 |
| D5 Swan API schema | Document REST endpoints before coding | Tech Lead | J+1 |

---

**Document Version** : 1.0
**Créé** : 15 mars 2026
**Auteur** : Sarah (BMAD Product Owner)
**Source** : gate-check.md sections 6.1 et 6.2
**État** : EN ATTENTE SIGNATURES JULES + TECH LEAD

