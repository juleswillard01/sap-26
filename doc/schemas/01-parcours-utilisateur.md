# 1. Parcours Utilisateur Quotidien

> Le workflow type de Jules : du cours donne au paiement recu sur son compte.

---

```mermaid
journey
    title Journee type de Jules — Cours particuliers
    section Avant le cours
      Verifier planning clients: 3: Jules
      Confirmer RDV avec eleve: 4: Jules
    section Apres le cours
      Ouvrir SAP-Facture: 5: Jules
      Selectionner client existant: 5: Jules
      Remplir heures et tarif: 4: Jules
      Generer facture PDF: 5: Systeme
      Soumettre a URSSAF: 5: Systeme
    section Suivi (automatique)
      Client recoit notification URSSAF: 4: URSSAF
      Client valide dans 48h: 3: Client
      Reminder auto si pas valide a T+36h: 5: Systeme
      URSSAF traite le paiement: 4: URSSAF
      Virement recu sur compte Swan: 5: Swan
    section Fin de semaine
      Dashboard - voir toutes les factures: 5: Jules
      Rapprochement bancaire auto: 5: Systeme
      Export CSV pour Google Sheets: 4: Jules
```

---

## Explications

| Etape | Qui | Quoi |
|-------|-----|------|
| Avant le cours | Jules | Verifie son planning, confirme avec l'eleve |
| Apres le cours | Jules | Ouvre l'app, selectionne le client, saisit heures + tarif |
| Generation | Systeme | PDF pro avec logo, soumission automatique a URSSAF |
| Validation | Client | Recoit un email URSSAF, valide en ligne (48h max) |
| Reminder | Systeme | Si pas de validation a T+36h, email auto a Jules pour relancer |
| Paiement | URSSAF + Client | 50% credit impot URSSAF + 50% reste a charge client |
| Rapprochement | Systeme | Match auto virements Swan avec factures soumises |
| Export | Jules | CSV export pour Google Sheets, controle hebdo |
