# 6. Rapprochement Bancaire & Lettrage — Swan / URSSAF

> Comment le systeme matche automatiquement les virements URSSAF recus sur Swan
> avec les factures. L'URSSAF paye 100% a Jules. Le client paye son reste a charge
> directement a l'URSSAF (jamais a Jules). Tout se passe dans Google Sheets.

---

## Vue d'ensemble du flux

```mermaid
flowchart LR
    subgraph "Sources"
        U["API URSSAF\nStatut factures"]
        S["API Swan\nTransactions bancaires"]
    end

    subgraph "SAP-Facture (App)"
        SYNC["Sync Service\n(cron 4h)"]
    end

    subgraph "Google Sheets"
        GF["Onglet Factures\nmaj statuts"]
        GT["Onglet Transactions\nimport virements"]
        GL["Onglet Lettrage\nformules matching"]
        GB["Onglet Balances\nsoldes calcules"]
    end

    subgraph "Resultat"
        OK["LETTRE\nFacture + virement OK"]
        WAIT["EN ATTENTE\nPas encore paye"]
        MANUAL["A VERIFIER\nScore < 80%"]
    end

    U --> SYNC
    S --> SYNC
    SYNC --> GF
    SYNC --> GT
    GF --> GL
    GT --> GL
    GL --> GB
    GL --> OK
    GL --> WAIT
    GL --> MANUAL
```

---

## Algorithme de lettrage (formules Sheets)

```mermaid
flowchart TD
    START["Pour chaque facture PAYEE\ndans onglet Factures"] --> WINDOW["Filtrer transactions URSSAF\ndate_paiement +/- 5 jours"]

    WINDOW --> SEARCH["Chercher 1 transaction :\nMontant = 100% facture\nLibelle contient URSSAF"]

    SEARCH --> FOUND{"Transaction\ntrouvee ?"}

    FOUND -- Oui --> SCORE["Score confiance :\nmontant exact = +50\ndate < 3j = +30\nlibelle URSSAF = +20"]

    SCORE --> HIGH{"Score >= 80 ?"}
    HIGH -- Oui --> AUTO["LETTRE AUTO\nEcrire facture_id dans transaction\nStatut = LETTRE"]
    HIGH -- Non --> SUGGEST["A VERIFIER\nSurligner en orange\nJules confirme manuellement"]

    FOUND -- "Non" --> NOMATCH["PAS DE MATCH\nAttendre le virement URSSAF\nSurligner en rouge"]

    AUTO --> BALANCE["Mettre a jour\nonglet Balances"]
    SUGGEST --> BALANCE

    style START fill:#1e40af,stroke:#3b82f6,color:#fff
    style AUTO fill:#059669,stroke:#34d399,color:#fff
    style BALANCE fill:#059669,stroke:#34d399,color:#fff
    style SUGGEST fill:#d97706,stroke:#fbbf24,color:#fff
    style NOMATCH fill:#dc2626,stroke:#f87171,color:#fff
```

---

## Exemple concret dans Sheets

```mermaid
flowchart TB
    subgraph "Onglet Factures"
        F1["SAP-2026-0001\nMarie D. — 120 EUR\nStatut: PAYE le 14/03"]
    end

    subgraph "Onglet Transactions (import Swan)"
        T1["12/03 — VIR URSSAF SAP\n+120.00 EUR"]
        T2["14/03 — VIR INCONNU\n+45.00 EUR"]
    end

    subgraph "Onglet Lettrage (formules)"
        L1["F001 ↔ T1 : 120 = 100% de 120\nlibelle URSSAF → Score 100\n→ LETTRE AUTO"]
        L2["T2 : 45 EUR\nAucune facture 45 EUR\n→ NON LETTRE"]
    end

    subgraph "Onglet Balances"
        B1["Mars 2026\nCA: 120 EUR\nRecu URSSAF: 120\nSolde: 0 → OK"]
    end

    F1 --> L1
    T1 --> L1
    T2 --> L2
    L1 --> B1

    style L1 fill:#059669,stroke:#34d399,color:#fff
    style L2 fill:#dc2626,stroke:#f87171,color:#fff
    style B1 fill:#059669,stroke:#34d399,color:#fff
```

---

## Regles de matching

| Critere | Points | Detail |
|---------|--------|--------|
| Montant exact (100% facture) | +50 | Transaction = exactement le total facture |
| Date proche (< 3 jours du statut PAYE) | +30 | Plus la date est proche, plus le score est haut |
| Libelle contient "URSSAF" | +20 | Confirme que c'est bien un virement URSSAF |
| **Seuil auto-lettrage** | **>= 80** | En dessous = surligne orange pour verification manuelle |

## Mise en forme conditionnelle Sheets

| Couleur | Signification |
|---------|---------------|
| Vert | Lettre automatiquement (score >= 80) |
| Orange | A verifier manuellement (score 50-79) |
| Rouge | Pas de match — transaction orpheline ou virement pas encore recu |

## Cas speciaux

- **Transaction orpheline** : virement recu sans facture correspondante → flag rouge, verification manuelle
- **Retard URSSAF** : le virement URSSAF peut arriver 2-5 jours apres le statut PAYE → tolerance temporelle elargie
- **Edit manuel** : Jules peut forcer un lettrage dans l'onglet Transactions en mettant le facture_id a la main
