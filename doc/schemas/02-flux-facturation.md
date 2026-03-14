# 2. Flux de Facturation End-to-End

> De la creation de la facture jusqu'au paiement recu et rapproche.

---

```mermaid
flowchart TD
    A["Jules cree la facture\n(web UI ou CLI)"] --> B{"Client deja\ninscrit URSSAF ?"}

    B -- Non --> C["Inscrire client\nvia API URSSAF"]
    C --> D{"Client reconnu\npar les impots ?"}
    D -- Non --> E["ERREUR\nClient doit avoir fait\n1 declaration fiscale"]
    D -- Oui --> F["Client inscrit\nID technique recu"]

    B -- Oui --> F

    F --> G["Generer PDF facture\n(logo + details cours)"]
    G --> H["Soumettre demande\nde paiement URSSAF"]

    H --> I{"Payload\nvalide ?"}
    I -- Non --> J["ERREUR URSSAF\nCorriger champs\net re-soumettre"]
    J --> H

    I -- Oui --> K["Demande acceptee\nstatut = CREE"]

    K --> L["Client recoit email\nURSSAF pour valider"]

    L --> M{"Client valide\ndans 48h ?"}
    M -- "Non, T+36h" --> N["Reminder email\nautomatique a Jules"]
    N --> M
    M -- "Non, expire" --> O["Facture expiree\nrelancer manuellement"]

    M -- Oui --> P["Statut = VALIDE\nURSSAF traite paiement"]

    P --> Q["URSSAF vire 100% a Jules\n(sur compte Swan/Indy)"]
    Q --> R["Client paye son 50%\na l'URSSAF (pas a Jules)"]

    Q --> U["Statut = PAYE\nrapprochement bancaire"]
```

---

## Legende

| Couleur | Signification |
|---------|---------------|
| Bleu | Action de Jules |
| Violet | Generation automatique |
| Vert | Succes / progression |
| Orange | Warning / attente |
| Rouge | Erreur / blocage |

## Points cles

- **Inscription client** : obligatoire une seule fois par client, necessite que le client ait fait au moins 1 declaration fiscale
- **Validation 48h** : le client a 48h pour valider la facture sur le portail URSSAF, sinon elle expire
- **Reminder T+36h** : le systeme previent Jules 12h avant expiration pour qu'il relance le client
- **Paiement unique** : URSSAF verse 100% a Jules sur Swan. Le client paye son 50% reste a charge directement a l'URSSAF (jamais a Jules)
- **Rapprochement** : 1 facture = 1 virement URSSAF a matcher sur Swan
