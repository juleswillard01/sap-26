# Machine à États — Cycle de Vie Facture

Source: `docs/SCHEMAS.html` diagramme 7

## 11 États

| État | Description | Terminal |
|------|-------------|----------|
| BROUILLON | Créée, pas envoyée | Non |
| SOUMIS | Envoyée à URSSAF | Non |
| CREE | URSSAF acceptée | Non |
| EN_ATTENTE | Email client envoyé, timer 48h | Non |
| VALIDE | Client validée | Non |
| PAYE | URSSAF virement 100% | Non |
| RAPPROCHE | Match transaction Indy | Oui |
| ERREUR | Payload invalide/API down | Non |
| EXPIRE | Délai 48h dépassé | Non |
| REJETE | Client refuse | Non |
| ANNULE | Jules annule | Oui |

## 13 Transitions Valides

| De | Vers | Trigger |
|----|------|---------|
| BROUILLON | SOUMIS | Envoi API URSSAF |
| BROUILLON | ANNULE | Jules annule |
| SOUMIS | CREE | URSSAF accepte |
| SOUMIS | ERREUR | Payload invalide |
| CREE | EN_ATTENTE | Email client (D3 immédiat) |
| EN_ATTENTE | VALIDE | Client valide |
| EN_ATTENTE | EXPIRE | Délai 48h dépassé |
| EN_ATTENTE | REJETE | Client refuse |
| VALIDE | PAYE | URSSAF vire |
| PAYE | RAPPROCHE | Match Indy ≥80pts |
| ERREUR | BROUILLON | Jules corrige |
| EXPIRE | BROUILLON | Re-soumettre |
| REJETE | BROUILLON | Corriger |

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
    return target in VALID_TRANSITIONS.get(current, [])
```

## Timers (CDC §2.3)

- **T+36h** : Email reminder Jules si pas validation
- **T+48h** : Transition EN_ATTENTE → EXPIRE (auto)

## ASCII Diagram

```
BROUILLON ──→ SOUMIS ──→ CREE ──→ EN_ATTENTE ──→ VALIDE ──→ PAYE ──→ RAPPROCHE [TERMINAL]
   │                        │          ├─→ EXPIRE ──┐
   │                        │          └─→ REJETE ──┤
   └───────────────────────→ ERREUR ───────────────┘
          (Jules)              │
                          BROUILLON (retry)

BROUILLON ──→ ANNULE [TERMINAL]
```

## Transitions Interdites

- BROUILLON → PAYE/VALIDE (sauter étapes)
- ANNULE/RAPPROCHE → * (terminales)
- Regressions (PAYE → EN_ATTENTE, etc.)
