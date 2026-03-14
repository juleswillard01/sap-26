# 3. Sequence API URSSAF — Appels Techniques

> Diagramme de sequence montrant chaque appel API entre SAP-Facture, l'API URSSAF, Swan et les autres acteurs.

---

```mermaid
sequenceDiagram
    actor Jules
    participant App as SAP-Facture
    participant Sheets as Google Sheets
    participant URSSAF as API URSSAF
    participant Client as Client (eleve)
    participant Swan as Swan/Indy

    Note over App,URSSAF: Phase 1 — Authentification OAuth2
    App->>URSSAF: POST /oauth/token {client_id, client_secret}
    URSSAF-->>App: {access_token, expires_in}
    App->>Sheets: Stocker token + expiry

    Note over Jules,App: Phase 2 — Inscription client (une seule fois)
    Jules->>App: Nouveau client (nom, email, adresse)
    App->>URSSAF: POST /particuliers {identite, email, adresse}
    URSSAF-->>App: {id_technique}
    App->>Sheets: Sauver client + id_technique

    Note over Jules,URSSAF: Phase 3 — Soumission facture
    Jules->>App: Creer facture (client, heures, tarif, dates)
    App->>App: Valider payload (nature, unite, dates, montant)
    App->>App: Generer PDF avec logo
    App->>Sheets: Sauver facture statut=BROUILLON
    App->>URSSAF: POST /demandes-paiement {id_client, montant, nature, dates, type_unite}
    URSSAF-->>App: {id_demande, statut: CREE}
    App->>Sheets: Maj statut = SOUMIS

    Note over URSSAF,Client: Phase 4 — Validation par le client
    URSSAF->>Client: Email - validez votre facture
    Client->>URSSAF: Validation en ligne (48h max)

    Note over App,URSSAF: Phase 5 — Polling statut (cron toutes les 4h)
    loop Toutes les 4 heures
        App->>URSSAF: GET /demandes-paiement/{id}
        URSSAF-->>App: {statut: VALIDE ou PAYE ou REJETE}
        App->>Sheets: Maj statut facture
    end

    Note over App,Jules: Phase 5b — Reminder si pas valide a T+36h
    App->>App: Check delai sans validation
    App->>Jules: Email - relancer client X

    Note over URSSAF,Swan: Phase 6 — Paiement
    URSSAF->>Swan: Virement 100% du montant facture
    Note right of Client: Client paye son 50%\ndirectement a l'URSSAF\n(jamais a Jules)

    Note over App,Sheets: Phase 7 — Rapprochement bancaire
    App->>Swan: GET transactions (GraphQL query)
    Swan-->>App: Liste transactions
    App->>Sheets: Import onglet Transactions
    Note over Sheets: Onglet Lettrage : 1 facture = 1 virement URSSAF
    App->>Sheets: Maj statut RAPPROCHE
```

---

## Detail des endpoints URSSAF

| Phase | Methode | Endpoint | Payload | Reponse |
|-------|---------|----------|---------|---------|
| Auth | POST | `/oauth/token` | `client_id`, `client_secret`, `grant_type=client_credentials` | `access_token`, `expires_in` |
| Inscription | POST | `/particuliers` | `identite` (nom, prenom), `email`, `adresse` | `id_technique` |
| Soumission | POST | `/demandes-paiement` | `id_client`, `montant`, `nature_code`, `date_debut`, `date_fin`, `type_unite` | `id_demande`, `statut` |
| Statut | GET | `/demandes-paiement/{id}` | - | `statut`, `info_rejet`, `info_virement` |
| Annulation | DELETE | `/demandes-paiement/{id}` | - | confirmation |

## Detail Swan GraphQL

```graphql
query GetTransactions($accountId: ID!, $after: DateTime) {
  account(id: $accountId) {
    transactions(filter: { afterDate: $after }) {
      edges {
        node {
          id
          amount { value currency }
          label
          bookingDate
          side  # Credit ou Debit
        }
      }
    }
  }
}
```

## Notes techniques

- **Token OAuth** : expire apres `expires_in` secondes, auto-refresh avant expiration
- **Rate limit** : pas documente officiellement, implementer retry avec backoff exponentiel
- **Sandbox** : tester tous les appels en sandbox avant production
- **NOVA** : le numero `SAP991552019` est utilise comme identifiant intervenant dans chaque facture
