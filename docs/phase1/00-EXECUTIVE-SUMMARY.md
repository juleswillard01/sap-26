# SAP-Facture: Executive Summary — MVP Scope & Roadmap

**Pour Jules** | **Mars 2026** | **Sarah (Product Owner)**

---

## Tl;dr — Le MVP en 4 Points

1. **Semaine 1 (5 jours dev)**: Tu peux créer un client URSSAF, créer une facture, l'envoyer à URSSAF, et voir le statut CREE.
2. **Semaine 2 (7 jours dev)**: PDF valide, polling auto de statut toutes les 4h, dashboard avec tout visible.
3. **Semaine 3-4 (16 jours dev)**: Rapprochement bancaire auto, reminders email si client valide pas, historique/filtres factures.
4. **Mois 2+ (selon besoin)**: Sync Google Sheets auto, attestations fiscales, multi-intervenant, mobile responsive.

**Total 12 jours MVP core** (semaine 1 + 2) → **Tu factures déjà.**

---

## Why This Scope? (Justification Valeur)

### MVP 1 Semaine 1 : Les 3 Features Essentielles
- **Inscription client URSSAF** — Sans ça, aucune facture possible.
- **Création facture (web)** — L'interface que tu utilises chaque jour.
- **Soumission API URSSAF** — C'est ce qui déclenche le paiement.

**Total effort**: ~12 jours dev robuste.
**What You Get**: Fin janvier, tu envoies ta 1ère facture par SAP-Facture. URSSAF reçoit, client reçoit email pour valider.

### MVP 2 Semaine 2 : Les 3 Features de "Production"
- **PDF facture + logo** — Légalement requis par URSSAF.
- **Polling statut auto 4h** — Tu n'as plus à refresh manuellement.
- **Dashboard factures** — Tu vois toutes tes factures d'un coup d'œil.

**Total effort**: ~7 jours.
**What You Get**: Fin février, tu as un vrai système. Factures générées proprement, statuts suivis auto, vue d'ensemble complète.

### Pas Inclus Semaine 1-2:
- ✗ Rapprochement bancaire auto (c'est Phase 2, semaine 3)
- ✗ Reminders email si client valide pas (c'est Phase 2, semaine 3)
- ✗ Attestations fiscales (c'est Phase 3, avril+)
- ✗ Multi-intervenant (c'est Phase 3, si tu scales)

**Why not?** Parce que si on fait tout à la fois, on livre rien en 2 semaines. Séquentiellement: **create → soumit → track → rapproche**.

---

## The Roadmap at a Glance

```
JANV (Semaine 1-2)           | FEVR (Semaine 3-4)          | MARS+ (Mois 2+)
─────────────────────────────┼────────────────────────────┼──────────────────
MVP Core (M1-M4)             | Phase 2 Confort (P2)        | Phase 3 Scaling (P3)
├─ Créer client URSSAF       | ├─ Rappro Swan auto        | ├─ Sheets sync auto
├─ Créer facture web         | ├─ Email reminder T+36h    | ├─ Attestations fiscales
├─ Envoyer à URSSAF          | ├─ Annulation/avoir        | ├─ Multi-intervenant
└─ Voir statut CREE          | ├─ Historique + filtres    | ├─ Mobile UI responsive
                             | └─ CLI reconcile           | ├─ Push notifications
                             |                            | └─ Stats/reporting NOVA

"Ta facture passe URSSAF"    | "Tout est automatisé"      | "Tu scalopes"
```

---

## What Unlocks Each Phase?

### MVP 1a (Semaine 1) Unlocks What?
- **Proof of concept** que le système fonctionne
- **Test real URSSAF API** behavior
- **48h prod stability** = go/no-go pour MVP 1b

### MVP 1b (Semaine 2) Unlocks What?
- **Production-ready factures** (PDF valide, branding)
- **Automated polling** (pas de refresh manual)
- **Dashboard visibility** (tu vois ton business)
- **Green light for Phase 2** si zéro facture perdue en 48h

### Phase 2 (Semaine 3-4) Unlocks What?
- **Rapprochement bancaire complet** (factures = virements Swan)
- **Email automations** (reminder si client valide pas)
- **Scalability** (gérer 50+ factures/mois sans friction)
- **Green light for Phase 3** si 50+ factures traitées, taux lettrage ≥90%

### Phase 3 (Mois 2+) Unlocks What?
- **Zero-touch Google Sheets sync** (data flows automatic)
- **Fiscal compliance** (attestations, charges, impôts)
- **Multi-intervenant** (recruit partner, chacun facture indépendamment)
- **Mobile-first** (manage from phone, not just desktop)

---

## Risk Mitigation: What Could Go Wrong?

### MVP Risks (Semaine 1-2)

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|-----------|
| URSSAF API payload validation trop stricte | 70% | Bloque M4 | Tester avec support URSSAF avant dev. Mock API réponses. |
| PDF rendering bugs (logo, font) | 40% | Facture illisible | Tests visuels PDF. Fallback HTML simple. |
| OAuth2 token expiry / refresh | 60% | API auth fails | Refresh token 59min. Retry exponential backoff. |
| Polling cron duplicate/miss jobs | 50% | Statut manqué ou dupliqué | Idempotent logic (check last_polled). DB lock. |
| Google Sheets API rate limit | 20% | Sync fails | Monitor quota. Cache 1h. |

**Mitigation Globale**: 3 jours buffer tests/fixes intégrés dans les 12 jours.

### Phase 2 Risks (Semaine 3-4)

| Risque | Mitigation |
|--------|-----------|
| Swan GraphQL API timeout | Caching transactions 1h. Scoring 80%+ confiance. "À verifier" if < 80. |
| Email SMTP bounce | Fallback: pas d'email = pas de rappel (acceptable phase 2). Queue + retry 3x. |
| Lettrage faux positif (montant égal = pas même facture) | Historique + libellé URSSAF. Score confiance: montant exact + date < 3j + libellé = confiant. |

---

## Success Metrics: How Do We Know It Works?

### MVP (Semaine 1-2)

- **Time to Invoice**: < 5 min du clic "créer" à URSSAF reçoit. (Baseline: manual = 15-20 min)
- **API Success Rate**: ≥ 95% soumissions acceptées (non erreur syntax).
- **Zero Data Loss**: Aucune facture perdue après MVP (audit DB intégrité).
- **Uptime**: ≥ 99% (web + cron availability, exclut URSSAF outages).

### Phase 2 (Semaine 3-4)

- **Rappro Accuracy**: ≥ 90% factures PAYEES lettrées correctement (auto + manual confirm).
- **Client Validation Rate**: ≥ 80% factures EN_ATTENTE → VALIDE (vs expirent).
- **Email Engagement**: ≥ 30% reminder opens (tes propres emails à toi, donc baseline unknown).
- **Dashboard Perf**: < 1s load pour 50 factures.

### Phase 3 (Mois 2+)

- **Sheets Sync Reliability**: ≥ 99.5% (zero errors, < 5min delay).
- **Reporting Adoption**: Tu utilises stats NOVA pour décisions (qualitatif).
- **Mobile Traffic**: If 20%+ analytics = design for mobile.

---

## Decision Gates: When Do We Move Forward?

### Gate 1: MVP 1a → 1b (End Semaine 1)
**Question**: Ces 3 features (M1, M2, M4) tournent 48h en prod sans crash?
- **Oui** → Launch MVP 1b (M3, M5, M6) immédiatement.
- **Non** → Stabilise 3-5 jours, retest.

### Gate 2: MVP 1b → Phase 2 (End Semaine 2)
**Question**: Dashboard correct? Zéro facture perdue en 48h prod?
- **Oui** → Phase 2 (P2A, P2B, P2D, P2E).
- **Non** → Audit DB, fix, monitor +2 semaines.

### Gate 3: Phase 2 → Phase 3 (End Semaine 4 or +)
**Question**: 50+ factures traitées? Lettrage ≥ 90% accuracy?
- **Oui** → Phase 3 (Sheets sync, attestations, etc.).
- **Non** → Stay Phase 2, monitor, optimize.

---

## What Gets Shipped When?

| Week | Feature | Delivered To You | Effort |
|------|---------|------------------|--------|
| 1 | M1 (client URSSAF), M2 (form), M4 (API submit) | Web: create client + facture. See status CREE. | 5 days |
| 2 | M3 (PDF), M5 (polling), M6 (dashboard) | Beautiful PDF. Auto status check. Dashboard. | 7 days |
| 3 | P2D/E (historique, filtres) | Search factures. Filter by statut/date/montant. | 3 days |
| 3 | P2A (rappro Swan) | Factures auto-matched avec virements Swan. | 5 days |
| 4 | P2B (reminder email), P2F (CLI), P2C (annulation) | Email if client doesn't validate. Fallback CLI. | 8 days |
| M2+ | P3A/B/F (Sheets sync, attestations, stats) | Zero-touch data. Fiscal compliance. Reporting. | Variable |

---

## The "Vraiment Pressé" Option (8 Days)

If you absolutely need MVP in **1 week tight**, cut:
- ✗ PDF branding (ship HTML invoice)
- ✗ Polling auto (user refresh button instead)
- ✗ Dashboard (just CLI output)

**Gets you**: M1 + M2 + M4 in **8 days**. Minimal, but working.
**Cost**: Less polished UX. You'll hate the 2nd week adding M3/M5/M6.

**Recommendation**: **Stay 12 days.** Worth it.

---

## How Do You Decide? (Questions for You)

1. **Timeline**: Can you wait 2 weeks for full MVP? Or 1 week minimum?
2. **Comfort**: Do you want auto-polling week 1, or manual refresh is OK?
3. **Branding**: Does the invoice PDF need your logo week 1, or is text OK?
4. **Multi-intervenant**: Are you recruiting a 2nd teacher soon? Or solo for months?
5. **Fiscal**: Do you need attestations for tax filing (usually June)? Or later?

**Your answers inform phasing decisions.**

---

## Next Steps

1. **Read Full Document**: `docs/phase1/08-mvp-scope.md` for detailed breakdown.
2. **Align on MVP Scope**: You (Jules) + Tech Lead agree on M1-M4 timeline.
3. **Detailed Planning**: Tech Lead creates user stories, story points, sprint plan.
4. **Signature**: You sign off on PRD = legal go/no-go.
5. **Kick Off**: Dev starts Week 1.

---

## Bottom Line

**You have a working invoicing system by end of February.**
It's lean, focused, and automates your daily pain points.
Then you scale intelligently based on real usage patterns.

No bloat. No "nice-to-haves" that don't matter.
Every feature has ROI for your micro-entrepreneur business.

**Let's build it.**

---

*Questions? → Review full PRD in `docs/phase1/08-mvp-scope.md`*
*Or ping Sarah (Product Owner) for clarifications.*

