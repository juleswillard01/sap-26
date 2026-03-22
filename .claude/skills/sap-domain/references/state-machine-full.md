# Machine à États — Cycle de Vie Facture (Référence Complète)

Source de vérité : `docs/SCHEMAS.html` diagramme 7

## 11 États

| État | Description | Terminal |
|------|-------------|----------|
| BROUILLON | PDF généré, pas envoyé, modifiable | Non |
| SOUMIS | Envoyé à URSSAF | Non |
| CREE | URSSAF accepte le payload | Non |
| EN_ATTENTE | Email envoyé au client, timer 48h actif | Non |
| VALIDE | Client a validé sur portail URSSAF | Non |
| PAYE | URSSAF a effectué le virement | Non |
| RAPPROCHE | Match avec transaction Indy | Oui |
| ERREUR | Payload invalide ou API down | Non |
| EXPIRE | Délai 48h dépassé | Non |
| REJETE | Client refuse | Non |
| ANNULE | Jules annule manuellement | Oui |

## 13 Transitions Valides

| De | Vers | Trigger | Side Effect |
|----|------|---------|-------------|
| BROUILLON | SOUMIS | Envoi API URSSAF | Générer PDF, écrire Sheets |
| BROUILLON | ANNULE | Jules annule | Marquer annulé dans Sheets |
| SOUMIS | CREE | URSSAF accepte | Stocker urssaf_demande_id |
| SOUMIS | ERREUR | Payload invalide / API down | Logger erreur |
| CREE | EN_ATTENTE | Email envoyé au client (immédiat D3) | Démarrer timer 48h |
| EN_ATTENTE | VALIDE | Client valide sur portail | date_validation = now |
| EN_ATTENTE | EXPIRE | Délai 48h dépassé | Notifier Jules |
| EN_ATTENTE | REJETE | Client refuse | Notifier Jules |
| VALIDE | PAYE | URSSAF vire 100% | date_paiement = now |
| PAYE | RAPPROCHE | Match transaction Indy | date_rapprochement = now |
| ERREUR | BROUILLON | Jules corrige | Réinitialiser champs |
| EXPIRE | BROUILLON | Re-soumettre | Réinitialiser dates |
| REJETE | BROUILLON | Corriger si besoin | Réinitialiser dates |

## Transitions INTERDITES

Les transitions suivantes sont **explicitement impossibles** :
- BROUILLON → PAYE (sauter des étapes)
- BROUILLON → VALIDE (sauter des étapes)
- SOUMIS → VALIDE (sauter EN_ATTENTE)
- CREE → PAYE (sauter EN_ATTENTE et VALIDE)
- CREE → VALIDE (nécessite EN_ATTENTE intermédiaire)
- ANNULE → * (terminal, aucune transition sortante)
- RAPPROCHE → * (terminal, aucune transition sortante)
- PAYE → BROUILLON (irréversible après paiement)
- VALIDE → BROUILLON (irréversible après validation)
- VALIDE → EN_ATTENTE (pas de regress)
- PAYE → EN_ATTENTE (pas de regress)
- PAYE → VALIDE (pas de regress)

## Timers — CDC §2.3

- **T+36h** sans validation → Email reminder automatique à Jules
- **T+48h** sans validation → Transition EN_ATTENTE → EXPIRE

Les timers s'activent au moment de la transition CREE → EN_ATTENTE (email envoyé).

## Code de Référence

```python
from enum import Enum

class InvoiceStatus(str, Enum):
    BROUILLON = "BROUILLON"
    SOUMIS = "SOUMIS"
    CREE = "CREE"
    EN_ATTENTE = "EN_ATTENTE"
    VALIDE = "VALIDE"
    PAYE = "PAYE"
    RAPPROCHE = "RAPPROCHE"
    ERREUR = "ERREUR"
    EXPIRE = "EXPIRE"
    REJETE = "REJETE"
    ANNULE = "ANNULE"

VALID_TRANSITIONS = {
    InvoiceStatus.BROUILLON: [InvoiceStatus.SOUMIS, InvoiceStatus.ANNULE],
    InvoiceStatus.SOUMIS: [InvoiceStatus.CREE, InvoiceStatus.ERREUR],
    InvoiceStatus.CREE: [InvoiceStatus.EN_ATTENTE],
    InvoiceStatus.EN_ATTENTE: [InvoiceStatus.VALIDE, InvoiceStatus.EXPIRE, InvoiceStatus.REJETE],
    InvoiceStatus.VALIDE: [InvoiceStatus.PAYE],
    InvoiceStatus.PAYE: [InvoiceStatus.RAPPROCHE],
    InvoiceStatus.ERREUR: [InvoiceStatus.BROUILLON],
    InvoiceStatus.EXPIRE: [InvoiceStatus.BROUILLON],
    InvoiceStatus.REJETE: [InvoiceStatus.BROUILLON],
    InvoiceStatus.RAPPROCHE: [],
    InvoiceStatus.ANNULE: [],
}

def can_transition(current: InvoiceStatus, target: InvoiceStatus) -> bool:
    """Valide une transition selon la machine à états."""
    return target in VALID_TRANSITIONS.get(current, [])

def transition(current: InvoiceStatus, target: InvoiceStatus) -> InvoiceStatus:
    """Effectue la transition si elle est valide, sinon lève InvalidStateTransition."""
    if not can_transition(current, target):
        raise InvalidStateTransition(f"Cannot transition from {current} to {target}")
    return target
```

## Règles D3 — Immédiaineté

**CREE → EN_ATTENTE est IMMÉDIAT** : Il n'y a pas de délai entre ces deux états. Dès que URSSAF accepte le payload (CREE), l'email est envoyé au client **instantanément** et l'état passe immédiatement à EN_ATTENTE. Les timers T+36h et T+48h se démarrent à cet instant.

## Diagramme d'État

```
[START]
  ↓
BROUILLON ─────────────── (Jules crée)
  ├─→ SOUMIS ─────────── (Envoi API URSSAF)
  │     ├─→ CREE ─────── (URSSAF accepte)
  │     │    ↓ (D3 immédiat)
  │     │   EN_ATTENTE ─ (Email client, timer 48h)
  │     │    ├─→ VALIDE → PAYE → RAPPROCHE ─→ [TERMINAL]
  │     │    ├─→ EXPIRE → BROUILLON
  │     │    └─→ REJETE → BROUILLON
  │     │
  │     └─→ ERREUR → BROUILLON
  │
  └─→ ANNULE ───────────────────────────→ [TERMINAL]
```

## Transitions de Correction

Les trois états d'échec (ERREUR, EXPIRE, REJETE) permettent de revenir à BROUILLON afin que Jules puisse corriger et re-soumettre. C'est le seul chemin de rédemption après un problème.

## Statuts dans Google Sheets

La colonne `statut` de l'onglet **Factures** doit toujours refléter l'état actuel de la machine à états. Les transitions se propagent via l'API SheetsAdapter en batch writes pour éviter les race conditions.
