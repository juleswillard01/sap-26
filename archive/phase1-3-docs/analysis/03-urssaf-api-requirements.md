# Analyse Technique API URSSAF — Requirements Détaillés

**Document** : Phase 1 SAP-Facture
**Source** : SCHEMA 3 — Sequence API URSSAF (docs/schemas/SCHEMAS.html)
**Auteur** : Winston (Technical Integration Analyst)
**Date** : Mars 2026
**Status** : ✅ Analysé et validé

---

## Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Flux OAuth 2.0 détaillé](#flux-oauth-20-détaillé)
3. [Liste exhaustive des endpoints](#liste-exhaustive-des-endpoints)
4. [Séquences d'appels par use case](#séquences-dappels-par-use-case)
5. [Gestion des erreurs et retry logic](#gestion-des-erreurs-et-retry-logic)
6. [Contraintes techniques](#contraintes-techniques)
7. [Dépendances et prérequis](#dépendances-et-prérequis)
8. [Environnements : Sandbox vs Production](#environnements--sandbox-vs-production)
9. [Implémentation recommandée](#implémentation-recommandée)

---

## Vue d'ensemble

### Contexte Métier

SAP-Facture s'intègre à l'API REST URSSAF pour automatiser le cycle complet des demandes de paiement des cours particuliers :

- **Inscription client** : Enregistrement d'un nouvel élève dans le système URSSAF
- **Soumission facture** : Création et transmission d'une demande de paiement
- **Polling statut** : Suivi de l'avancement (CREE → EN_ATTENTE → VALIDE → PAYE)
- **Gestion d'erreurs** : Retry et correction des payloads invalides

### Architecture d'intégration

```
┌──────────────────────────────────────────────────────────────────┐
│ SAP-Facture (App FastAPI)                                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  URSSAFClient (classe responsable de tous les appels API)       │
│  ├─ Gestion OAuth2 (token fetch + refresh)                       │
│  ├─ Endpoints : /oauth/token, /particuliers, /demandes-paiement  │
│  └─ Error handling + Circuit breaker + Retry logic              │
│                                                                   │
└───────────────────────────┬──────────────────────────────────────┘
                            │ HTTPS + TLS 1.3
                            │
                            ▼
        ┌───────────────────────────────────┐
        │ API URSSAF                        │
        │ portailapi.urssaf.fr (prod)       │
        │ sandbox.urssaf.fr (recette)       │
        └───────────────────────────────────┘
```

---

## Flux OAuth 2.0 Détaillé

### 1. Type de flux : Client Credentials

**Standard** : OAuth 2.0 RFC 6749, section 4.4
**Raison** : Communication serveur-à-serveur sans interaction utilisateur

### 2. Étapes du flux

#### Étape 1 : Demande d'un token initial

**Endpoint** : `POST /oauth/token`
**Host** : `portailapi.urssaf.fr` (production) ou `sandbox.urssaf.fr` (sandbox)

**Header HTTP**
```http
POST /oauth/token HTTP/1.1
Host: portailapi.urssaf.fr
Content-Type: application/x-www-form-urlencoded
Authorization: Basic <base64(client_id:client_secret)>
```

**Payload**
```
grant_type=client_credentials
&scope=invoicing%20read
&client_id=YOUR_CLIENT_ID
&client_secret=YOUR_CLIENT_SECRET
```

**Alternative** (form data) :
```json
{
  "grant_type": "client_credentials",
  "client_id": "YOUR_CLIENT_ID",
  "client_secret": "YOUR_CLIENT_SECRET",
  "scope": "invoicing read"
}
```

**Réponse (HTTP 200 OK)**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "invoicing read",
  "jti": "abc123def456"
}
```

**Analyse du token** (JWT décodé) :
```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "client_id_string",
    "iss": "https://oauth.urssaf.fr",
    "aud": "api.urssaf.fr",
    "iat": 1710000000,
    "exp": 1710003600,
    "scope": "invoicing read"
  }
}
```

#### Étape 2 : Stockage et utilisation du token

**Durée de vie** : 3600 secondes = 1 heure
**Stratégie de cache** :
- Stocker le token en mémoire (Redis si possible)
- Clé : `urssaf_token_{client_id}`
- Valeur : `{access_token, expiry_timestamp, scope}`
- TTL : `expires_in - 60` (renouveler 60s avant expiration)

**Utilisation dans les requêtes**
```http
GET /particuliers/{id} HTTP/1.1
Host: portailapi.urssaf.fr
Authorization: Bearer eyJhbGciOiJSUzI1NiI...
```

#### Étape 3 : Renouvellement du token (refresh)

Quand `expiry_timestamp - current_time < 60` secondes :

```python
# Pseudo-code
if time.time() >= token_expiry - 60:
    call_oauth_token()  # Refaire l'étape 1
    store_new_token()
```

**Pas de refresh token** : Chaque appel à `/oauth/token` génère un nouveau token.

### 3. Gestion du token (pattern recommandé)

```python
class TokenManager:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.expiry = None
        self.lock = asyncio.Lock()

    async def get_valid_token(self) -> str:
        # Vérifier si le token est valide
        if self.token and time.time() < self.expiry - 60:
            return self.token

        # Sinon, renouveler
        async with self.lock:
            # Double-check pattern
            if self.token and time.time() < self.expiry - 60:
                return self.token

            # Appeler /oauth/token
            self.token, self.expiry = await self._fetch_new_token()
            return self.token

    async def _fetch_new_token(self) -> tuple[str, float]:
        # Appel HTTP POST /oauth/token
        # Parser expires_in
        # Retourner (token, expiry_timestamp)
        pass
```

---

## Liste exhaustive des endpoints

### Endpoint 1 : Authentification

**POST /oauth/token**

| Aspect | Valeur |
|--------|--------|
| **Méthode HTTP** | POST |
| **Authentification** | Basic Auth (header `Authorization: Basic base64(client_id:client_secret)`) OU form-data |
| **Content-Type** | `application/x-www-form-urlencoded` |
| **Payload** | `grant_type=client_credentials&client_id=...&client_secret=...` |
| **Réponse** | JSON: `{access_token, token_type, expires_in, scope, jti}` |
| **HTTP Status** | 200 OK (succès) / 400 Bad Request (credentials invalides) / 401 Unauthorized |
| **Timeout** | 10 secondes |
| **Retry** | Oui (3 tentatives en cas d'erreur 5xx) |

---

### Endpoint 2 : Inscription client (particulier)

**POST /particuliers**

| Aspect | Valeur |
|--------|--------|
| **Méthode HTTP** | POST |
| **Authentification** | Bearer Token (header `Authorization: Bearer <access_token>`) |
| **Content-Type** | `application/json` |
| **Path** | `/api/v2/particuliers` (version API supposée) |

**Payload**

```json
{
  "identite": {
    "nom": "Dupont",
    "prenom": "Jean",
    "date_naissance": "1990-03-15"
  },
  "email": "jean.dupont@example.com",
  "telephone": "0612345678",
  "adresse": {
    "rue": "123 Rue de la Paix",
    "code_postal": "75001",
    "ville": "Paris",
    "pays": "FR"
  },
  "situation_fiscale": {
    "regime": "micro_entreprise",
    "secteur_activite": "enseignement_particulier",
    "date_debut_activite": "2024-01-15"
  }
}
```

**Réponse (HTTP 201 Created)**

```json
{
  "id_technique": "PART-2026-000001",
  "id_urssaf": "12345678901234",
  "email": "jean.dupont@example.com",
  "statut_inscription": "VALIDEE",
  "date_inscription": "2026-03-15T10:30:00Z",
  "lien_portail": "https://secure.urssaf.fr/validation/PART-2026-000001"
}
```

| Aspect | Valeur |
|--------|--------|
| **HTTP Status** | 201 Created (succès) / 400 Bad Request (données invalides) / 409 Conflict (email déjà utilisé) |
| **Timeout** | 15 secondes |
| **Validation** | Email unique, date naissance valide, adresse complète |
| **Idempotence** | Non (chaque appel crée un nouvel enregistrement) |
| **Retry** | Oui (3 tentatives, mais attention aux doublons) |

---

### Endpoint 3 : Soumission d'une facture (demande de paiement)

**POST /demandes-paiement**

| Aspect | Valeur |
|--------|--------|
| **Méthode HTTP** | POST |
| **Authentification** | Bearer Token |
| **Content-Type** | `application/json` |
| **Path** | `/api/v2/demandes-paiement` |

**Payload**

```json
{
  "id_client_urssaf": "PART-2026-000001",
  "type_particulier": "salarie_paye",
  "nature_service": "cours_particuliers",
  "montant_total_eur": 1500.00,
  "montant_contribution_salariale_eur": 750.00,
  "montant_contribution_patronale_eur": 750.00,
  "periode": {
    "date_debut": "2026-02-01",
    "date_fin": "2026-02-28",
    "nombre_heures": 20,
    "taux_horaire": 75.00
  },
  "descriptif_service": "Cours particuliers - Mathematiques et Physique",
  "devise": "EUR",
  "reference_interne": "FAC-2026-001",
  "email_validation": "jean.dupont@example.com"
}
```

**Champs obligatoires** :
- `id_client_urssaf` : ID technique du client (reçu lors de l'inscription)
- `montant_total_eur` : Montant HT en euros
- `periode.date_debut`, `periode.date_fin` : Dates de la prestation
- `nature_service` : Code URSSAF du type de service
- `email_validation` : Email où le client recevra la demande de validation

**Réponse (HTTP 201 Created)**

```json
{
  "id_demande": "DEM-2026-000001",
  "id_demande_urssaf": "987654321",
  "statut": "CREE",
  "date_creation": "2026-03-15T14:30:00Z",
  "date_expiration_validation": "2026-03-17T14:30:00Z",
  "lien_client": "https://secure.urssaf.fr/validate/DEM-2026-000001",
  "montant_accepte": 1500.00
}
```

| Aspect | Valeur |
|--------|--------|
| **HTTP Status** | 201 Created (succès) / 400 Bad Request (payload invalide) / 404 Not Found (client_id inexistant) |
| **Timeout** | 20 secondes |
| **Validation** | Montants > 0, dates cohérentes, client inscrit |
| **Idempotence** | Non (chaque appel crée une nouvelle demande) |
| **Retry** | Oui (3 tentatives, vérifier `reference_interne` pour dédupliquer) |

---

### Endpoint 4 : Récupération du statut d'une demande

**GET /demandes-paiement/{id_demande}**

| Aspect | Valeur |
|--------|--------|
| **Méthode HTTP** | GET |
| **Authentification** | Bearer Token |
| **Content-Type** | `application/json` |
| **Path** | `/api/v2/demandes-paiement/{id_demande}` |
| **Paramètres** | `id_demande` : ID retourné à la création (ex: `DEM-2026-000001`) |

**Réponse (HTTP 200 OK)**

```json
{
  "id_demande": "DEM-2026-000001",
  "id_demande_urssaf": "987654321",
  "statut": "VALIDE",
  "date_creation": "2026-03-15T14:30:00Z",
  "date_validation_client": "2026-03-16T09:15:00Z",
  "date_paiement_prevu": "2026-04-15",
  "montant_total": 1500.00,
  "montant_recu": 1500.00,
  "date_recu": "2026-04-15T12:00:00Z",
  "details_paiement": {
    "iban_beneficiaire": "FR76****",
    "reference_virement": "URSSAF-DEM-2026-000001"
  }
}
```

**Statuts possibles** :
- `CREE` : Demande créée, en attente de validation client
- `EN_ATTENTE` : Email envoyé, client n'a pas encore validé
- `VALIDE` : Client a validé, URSSAF traite le paiement
- `PAYE` : Virement effectué
- `REJETE` : Client a refusé
- `EXPIRE` : Délai de validation dépassé (48h)
- `ERREUR` : Problème lors du traitement

| Aspect | Valeur |
|--------|--------|
| **HTTP Status** | 200 OK (succès) / 404 Not Found (demande inexistante) / 401 Unauthorized |
| **Timeout** | 10 secondes |
| **Idempotence** | OUI (GET safe, pas d'effet de bord) |
| **Retry** | Oui (3 tentatives) |
| **Fréquence** | Polling toutes les 4 heures (voir section polling) |

---

### Endpoint 5 : Annulation d'une demande

**DELETE /demandes-paiement/{id_demande}** (optionnel, à vérifier avec URSSAF)

| Aspect | Valeur |
|--------|--------|
| **Méthode HTTP** | DELETE ou PUT |
| **Authentification** | Bearer Token |
| **Path** | `/api/v2/demandes-paiement/{id_demande}` |

**Payload** (si PUT)
```json
{
  "action": "annuler",
  "motif": "erreur_montant"
}
```

**Réponse**
```json
{
  "id_demande": "DEM-2026-000001",
  "statut": "ANNULEE",
  "date_annulation": "2026-03-16T10:00:00Z"
}
```

| Aspect | Valeur |
|--------|--------|
| **HTTP Status** | 204 No Content (succès) / 400 Bad Request (demande non-annulable) |
| **Restriction** | Seulement si statut = `CREE` ou `EN_ATTENTE` (pas si VALIDE ou PAYE) |

---

## Séquences d'appels par use case

### Use Case 1 : Inscription d'un nouveau client (particulier)

**Acteurs** : Jules, SAP-Facture, URSSAF

**Flux**

```
┌─────┐        ┌────────────┐        ┌──────────┐
│Jules│        │SAP-Facture │        │  URSSAF  │
└──┬──┘        └────┬───────┘        └──────┬───┘
   │                │                       │
   │ Saisir nouveau │                       │
   │ client (nom,   │                       │
   │ email, adresse)│                       │
   │──────────────>│                       │
   │                │ 1. POST /oauth/token  │
   │                │───────────────────────>
   │                │ {access_token}       │
   │                │<───────────────────────
   │                │                       │
   │                │ 2. POST /particuliers │
   │                │ {identite, email}    │
   │                │───────────────────────>
   │                │ {id_technique}       │
   │                │<───────────────────────
   │                │                       │
   │ Afficher ID    │                       │
   │ inscription    │                       │
   │<──────────────│                       │
   │                │                       │
```

**Étapes détaillées**

1. **Jules remplit le formulaire de nouveau client**
   - Nom, Prénom, Email, Téléphone, Adresse, Code postal, Ville

2. **SAP-Facture demande un token OAuth2**
   ```
   POST https://portailapi.urssaf.fr/oauth/token
   Authorization: Basic base64(client_id:client_secret)
   Content-Type: application/x-www-form-urlencoded

   grant_type=client_credentials&client_id=...&client_secret=...
   ```

   Réponse : `{access_token, expires_in: 3600}`

   Stocker en cache (Redis/memory) avec TTL 3540s (60s buffer)

3. **SAP-Facture crée le client dans URSSAF**
   ```
   POST https://portailapi.urssaf.fr/api/v2/particuliers
   Authorization: Bearer <access_token>
   Content-Type: application/json

   {
     "identite": {"nom": "Dupont", "prenom": "Jean"},
     "email": "jean.dupont@example.com",
     "telephone": "0612345678",
     "adresse": {...}
   }
   ```

   Réponse : `{id_technique: "PART-2026-000001"}`

4. **Stocker id_technique en Google Sheets (onglet Clients)**
   - Colonne `urssaf_id` = `PART-2026-000001`
   - Colonne `statut_urssaf` = `INSCRIT`

5. **Afficher le message de succès à Jules**

**Gestion des erreurs**

| Erreur | Cause | Action |
|--------|-------|--------|
| 400 Bad Request (step 3) | Email invalide ou déjà inscrit | Afficher erreur à Jules, demander correction |
| 401 Unauthorized (step 2) | Client credentials expiré | Logger, refaire /oauth/token |
| 404 Not Found | URL endpoint mal formée | Contacter support URSSAF |
| 5xx Server Error | URSSAF unavailable | Retry 3 fois, puis notifier Jules |

**Idempotence**

Attention : Le endpoint POST /particuliers n'est pas idempotent.
- **Solution** : Avant d'appeler POST, vérifier en Google Sheets si l'email existe déjà
- **Alternative** : Implémenter une `reference_interne` (numéro client local) et retourner l'erreur 409 Conflict

---

### Use Case 2 : Soumission d'une facture

**Acteurs** : Jules, SAP-Facture, URSSAF, Client (élève)

**Flux**

```
┌─────┐        ┌────────────┐        ┌──────────┐        ┌────────┐
│Jules│        │SAP-Facture │        │  URSSAF  │        │ Client │
└──┬──┘        └────┬───────┘        └────┬────┘        └───┬────┘
   │                │                     │                 │
   │ Créer facture  │                     │                 │
   │ (client,       │                     │                 │
   │  heures, tarif)│                     │                 │
   │──────────────>│                     │                 │
   │                │ Valider payload    │                 │
   │                │ Générer PDF        │                 │
   │                │ Écrire feuille     │                 │
   │                │                     │                 │
   │                │ 1. POST /oauth/    │                 │
   │                │    oauth/token     │                 │
   │                │─────────────────>  │                 │
   │                │ {access_token}     │                 │
   │                │<─────────────────  │                 │
   │                │                     │                 │
   │                │ 2. POST /demandes- │                 │
   │                │    paiement        │                 │
   │                │ {id_client,        │                 │
   │                │  montant, dates}   │                 │
   │                │─────────────────>  │                 │
   │                │ {id_demande,       │                 │
   │                │  statut: CREE}     │                 │
   │                │<─────────────────  │                 │
   │                │                     │ Email : validez │
   │                │                     │ votre facture   │
   │                │                     │────────────────>
   │                │ Maj feuille        │                 │
   │                │ (statut: SOUMIS)   │                 │
   │ Afficher OK    │                     │                 │
   │<──────────────│                     │                 │
   │                │                     │                 │
```

**Étapes détaillées**

1. **Jules ouvre le formulaire de création facture**
   - Sélectionner un client existant (dropdown)
   - Saisir date_début, date_fin, nombre d'heures, taux horaire
   - SAP-Facture calcule montant_total = nombre_heures × taux_horaire

2. **Validation du payload côté SAP-Facture**
   ```python
   # Vérifications
   assert montant_total > 0
   assert date_debut <= date_fin
   assert date_fin <= today()
   assert client_id exists in Google Sheets
   assert client.urssaf_id is not None
   ```

3. **Générer le PDF de la facture**
   - Logo SAP-Facture
   - Détails client
   - Détails prestation (dates, heures, tarif)
   - Montant en euros
   - Sauvegarder dans Google Drive

4. **Écrire la facture en Google Sheets (onglet Factures) — état BROUILLON**
   ```
   facture_id | client_id | date_debut | date_fin | montant | statut | pdf_id
   FAC-2026-1 | PART-001  | 2026-02-01 | 2026-02-28 | 1500.00 | BROUILLON | drive_id_xxx
   ```

5. **Appeler POST /demandes-paiement**
   ```
   POST https://portailapi.urssaf.fr/api/v2/demandes-paiement
   Authorization: Bearer <access_token>

   {
     "id_client_urssaf": "PART-2026-000001",
     "montant_total_eur": 1500.00,
     "montant_contribution_salariale_eur": 750.00,
     "montant_contribution_patronale_eur": 750.00,
     "periode": {
       "date_debut": "2026-02-01",
       "date_fin": "2026-02-28",
       "nombre_heures": 20,
       "taux_horaire": 75.00
     },
     "nature_service": "cours_particuliers",
     "email_validation": "jean.dupont@example.com",
     "reference_interne": "FAC-2026-1"
   }
   ```

   Réponse : `{id_demande: "DEM-2026-000001", statut: "CREE"}`

6. **Mettre à jour Google Sheets (onglet Factures)**
   ```
   facture_id | client_id | ... | statut | urssaf_demande_id
   FAC-2026-1 | PART-001  | ... | SOUMIS | DEM-2026-000001
   ```

7. **Afficher le succès à Jules**
   ```
   ✓ Facture FAC-2026-1 soumise à URSSAF
   ✓ ID demande : DEM-2026-000001
   ✓ Client recevra un email pour validation
   ```

**Gestion des erreurs de payload**

| Erreur | Cause | Action |
|--------|-------|--------|
| 400 Bad Request | Montant négatif, client_id invalide, dates incohérentes | Afficher erreur précise à Jules |
| 404 Not Found | Client URSSAF inexistant | Vérifier que le client est bien inscrit (step inscription) |
| 409 Conflict | Demande dupliquée (même `reference_interne`) | Avertir Jules, proposer créer nouveau |
| 422 Unprocessable | Email invalide ou adresse client incompète | Demander Jules de corriger le client d'abord |

---

### Use Case 3 : Polling du statut (CRON toutes les 4 heures)

**Acteurs** : SAP-Facture, URSSAF, Jules

**Contexte** : Chaque 4 heures, une tâche cron boucle sur les demandes en cours et récupère leur statut

**Pseudo-code**

```python
async def cron_sync_urssaf_status():
    """Toutes les 4 heures, sync les statuts des demandes URSSAF"""

    # 1. Récupérer toutes les factures non-finalisées
    #    Statuts : BROUILLON, SOUMIS, CREE, EN_ATTENTE, EN_ERREUR
    factures = sheets.get_factures(
        statut_in=["BROUILLON", "SOUMIS", "CREE", "EN_ATTENTE", "EN_ERREUR"]
    )

    for facture in factures:
        # 2. Si statut = BROUILLON (jamais soumise), skip
        if facture.statut == "BROUILLON":
            continue

        # 3. Récupérer l'ID demande URSSAF
        id_demande = facture.urssaf_demande_id  # ex: "DEM-2026-000001"

        # 4. Appeler GET /demandes-paiement/{id_demande}
        try:
            response = await urssaf_client.get_demande_status(id_demande)
            # response = {statut: "VALIDE", montant_recu: 1500.00, date_recu: "2026-04-15"}

            # 5. Mettre à jour la feuille Factures
            sheets.update_facture(facture.id, {
                "statut": response["statut"],
                "date_derniere_sync": now(),
                "montant_recu": response.get("montant_recu"),
                "date_paiement": response.get("date_recu")
            })

            # 6. Si PAYE, déclencher rapprochement bancaire
            if response["statut"] == "PAYE":
                await reconcile_with_swan(facture)

        except HTTPError as e:
            logger.error(f"URSSAF sync failed for {id_demande}", exc_info=True)
            # Retry sera tenté à la prochaine exécution cron
```

**API Call sequence**

```
┌────────────┐        ┌──────────┐
│SAP-Facture │        │  URSSAF  │
└────┬───────┘        └────┬─────┘
     │                     │
     │ 1. GET /oauth/token │
     │────────────────────>
     │ {access_token}      │
     │<────────────────────
     │                     │
     │ 2. GET /demandes-   │
     │    paiement/{id}    │
     │────────────────────>
     │ {statut, montant}   │
     │<────────────────────
     │                     │
     │ 3. GET /demandes-   │
     │    paiement/{id+1}  │
     │────────────────────>
     │ {statut, montant}   │
     │<────────────────────
     │                     │
     (... boucle sur N demandes ...)
```

**Fréquence**

```
┌─────────────────────────────────────────────────────────────┐
│ Cron job : Toutes les 4 heures (0, 4, 8, 12, 16, 20 heures) │
└─────────────────────────────────────────────────────────────┘
```

Configuration (exemple FastAPI + APScheduler) :
```python
scheduler.add_job(
    cron_sync_urssaf_status,
    'cron',
    hour='0,4,8,12,16,20',
    minute=0,
    id='urssaf_sync_status'
)
```

**Statuts attendus à chaque étape**

| Étape temps | Statut URSSAF | Action |
|-------------|---------------|--------|
| T+0 min | CREE | Email envoyé au client |
| T+36h | EN_ATTENTE | Reminder email auto (si pas encore validé) |
| T+48h | EXPIRE | Facture expire, Jules doit relancer manuellement |
| T+24h à T+7j | VALIDE | Client a validé, URSSAF traite le paiement |
| T+5 à T+15j | PAYE | Virement effectué vers Swan/Indy |

---

### Use Case 4 : Gestion du Reminder T+36h

**Contexte** : Si une facture reste en EN_ATTENTE depuis 36h, envoyer un email de rappel au client

**Trigger**

```python
async def cron_check_reminders():
    """Toutes les heures, vérifier les factures en attente depuis 36h"""

    factures = sheets.get_factures(statut="EN_ATTENTE")

    for facture in factures:
        # Récupérer la demande URSSAF pour avoir la date de création
        response = await urssaf_client.get_demande_status(facture.urssaf_demande_id)
        date_creation = parse_iso8601(response["date_creation"])

        time_elapsed = now() - date_creation

        # Si > 36h et pas encore de reminder envoyé
        if time_elapsed > timedelta(hours=36) and not facture.reminder_sent:
            # Envoyer email à Jules (pas au client, c'est URSSAF qui s'en charge)
            await send_email(
                to=julius_email,
                subject=f"Reminder : Client {facture.client.nom} n'a pas validé facture {facture.id}",
                body=f"""
                La facture {facture.id} est en attente de validation client depuis 36h.

                Client : {facture.client.email}
                Montant : €{facture.montant}

                Lien de validation URSSAF : https://secure.urssaf.fr/validate/{facture.urssaf_demande_id}

                Vous pouvez aussi relancer le client manuellement.
                """
            )

            # Marquer reminder comme envoyé
            sheets.update_facture(facture.id, {"reminder_sent": True, "reminder_sent_at": now()})
```

**Configuration cron**

```python
scheduler.add_job(
    cron_check_reminders,
    'cron',
    hour='*',
    minute=15,  # À chaque heure + 15 min
    id='reminder_check'
)
```

---

## Gestion des erreurs et retry logic

### Stratégie générale

```
┌─────────────────────────────────────────────────────────┐
│ Tentative 1 : Appel immédiat                            │
│  ├─ Succès (HTTP 200/201) → Fin                        │
│  └─ Erreur → Étape 2                                    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Tentative 2 : Attendre 2^1 = 2 secondes, réessayer      │
│  ├─ Succès → Fin                                        │
│  └─ Erreur → Étape 3                                    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Tentative 3 : Attendre 2^2 = 4 secondes, réessayer      │
│  ├─ Succès → Fin                                        │
│  └─ Erreur → Étape 4                                    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Tentative 4 : Circuit Breaker ouvert                    │
│  └─ Logger erreur + Notifier Jules + Stopper            │
└─────────────────────────────────────────────────────────┘
```

### Codes HTTP et actions

| Code | Nom | Retry ? | Délai | Action |
|------|-----|---------|-------|--------|
| 200 | OK | N/A | N/A | Succès |
| 201 | Created | N/A | N/A | Succès |
| 400 | Bad Request | **Non** | N/A | Erreur client : valider payload |
| 401 | Unauthorized | Oui (token refresh) | 1s | Renouveler token + retry |
| 403 | Forbidden | **Non** | N/A | Permissions insuffisantes, contacter support URSSAF |
| 404 | Not Found | **Non** (après 1 retry) | 5s | Ressource inexistante, vérifier ID |
| 409 | Conflict | **Non** (dédupliquer) | N/A | Demande dupliquée, checker reference_interne |
| 422 | Unprocessable Entity | **Non** | N/A | Validations métier URSSAF échouées |
| 429 | Too Many Requests | Oui (rate limiting) | Retry-After header | Attendre avant retry |
| 500 | Internal Server Error | Oui | 2, 4, 8s (exponentiel) | URSSAF en problème |
| 502 | Bad Gateway | Oui | 2, 4, 8s | Gateway/load balancer issue |
| 503 | Service Unavailable | Oui | 2, 4, 8s | Maintenance URSSAF |
| 504 | Gateway Timeout | Oui | 2, 4, 8s | Timeout côté URSSAF |

### Implémentation en Python (aiohttp + tenacity)

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result
)
import asyncio

class URSSAFClient:
    def __init__(self, client_id: str, client_secret: str, sandbox: bool = False):
        self.client_id = client_id
        self.client_secret = client_secret
        self.sandbox = sandbox
        self.base_url = "https://sandbox.urssaf.fr" if sandbox else "https://portailapi.urssaf.fr"
        self.token_manager = TokenManager(client_id, client_secret)

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((asyncio.TimeoutError, ConnectionError, aiohttp.ClientError)),
        reraise=True
    )
    async def post_demande_paiement(self, payload: dict) -> dict:
        """Créer une demande de paiement, avec retry automatique"""

        token = await self.token_manager.get_valid_token()

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            try:
                async with session.post(
                    f"{self.base_url}/api/v2/demandes-paiement",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as response:
                    # Non-retryable errors
                    if response.status in [400, 403, 404, 409, 422]:
                        error_body = await response.json()
                        logger.error(f"URSSAF API error {response.status}: {error_body}")
                        raise URSSAFValidationError(
                            f"Code {response.status}: {error_body.get('message', 'Unknown')}"
                        )

                    # Retryable errors
                    elif response.status in [429, 500, 502, 503, 504]:
                        logger.warning(f"Retryable URSSAF error {response.status}, will retry...")
                        raise aiohttp.ClientError(f"HTTP {response.status}")

                    # 401 : Token expiré, renouveler et retry (handled by retry decorator)
                    elif response.status == 401:
                        logger.warning("Token expired, refreshing...")
                        self.token_manager.token = None  # Forcer renouvellement
                        raise aiohttp.ClientError("Token expired")

                    # Success
                    elif response.status in [200, 201]:
                        return await response.json()

                    else:
                        logger.error(f"Unexpected URSSAF status {response.status}")
                        raise aiohttp.ClientError(f"HTTP {response.status}")

            except asyncio.TimeoutError:
                logger.error("URSSAF request timeout, will retry...")
                raise
            except ConnectionError as e:
                logger.error(f"Connection error to URSSAF: {e}, will retry...")
                raise
```

### Circuit Breaker (pour éviter surcharge)

```python
from pybreaker import CircuitBreaker

class URSSAFClientWithBreaker:
    def __init__(self, client_id: str, client_secret: str):
        self.urssaf_client = URSSAFClient(client_id, client_secret)

        # Circuit breaker : ouvre après 5 erreurs en 60s
        self.breaker = CircuitBreaker(
            fail_max=5,
            reset_timeout=60,
            name="URSSAF_API"
        )

    async def post_demande_paiement(self, payload: dict) -> dict:
        try:
            return await self.breaker.call(
                self.urssaf_client.post_demande_paiement,
                payload
            )
        except CircuitBreaker.CircuitBreakerOpen:
            logger.critical("URSSAF API circuit breaker OPEN. Stopping requests.")
            raise
```

---

## Contraintes techniques

### 1. Rate Limiting

**Limite officielle URSSAF** : À déterminer (standard : 100 req/min ou 1000 req/heure)

**Stratégie SAP-Facture**
- **Requests par endpoint** :
  - `POST /oauth/token` : 1 req par heure (renouveler token 60s avant expiration)
  - `POST /particuliers` : max 5 req/jour (inscriptions rares)
  - `POST /demandes-paiement` : max 20 req/jour (1 facture par client par jour)
  - `GET /demandes-paiement/{id}` : 144 req/jour (polling toutes les 4h × 6 × 24h)

- **Réponse HTTP 429 (Too Many Requests)** :
  ```
  HTTP/1.1 429 Too Many Requests
  Retry-After: 60
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 0
  X-RateLimit-Reset: 1710345600
  ```

  Action : Attendre `Retry-After` secondes, puis retry

### 2. Timeouts

| Opération | Timeout | Justification |
|-----------|---------|---------------|
| POST /oauth/token | 10s | Authentification critique, pas d'attente longue |
| POST /particuliers | 15s | Validation identité, peut prendre du temps |
| POST /demandes-paiement | 20s | Opération complexe (création + emails + validation) |
| GET /demandes-paiement/{id} | 10s | Lecture simple, doit être rapide |

**Configuration aiohttp**
```python
timeout = aiohttp.ClientTimeout(total=20, connect=5, sock_read=5)
async with session.post(url, timeout=timeout) as response:
    ...
```

### 3. Format de payload et validations

**JSON Schema pour POST /particuliers**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["identite", "email", "adresse"],
  "properties": {
    "identite": {
      "type": "object",
      "required": ["nom", "prenom"],
      "properties": {
        "nom": {"type": "string", "minLength": 1, "maxLength": 100},
        "prenom": {"type": "string", "minLength": 1, "maxLength": 100},
        "date_naissance": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"}
      }
    },
    "email": {
      "type": "string",
      "format": "email",
      "maxLength": 255
    },
    "adresse": {
      "type": "object",
      "required": ["rue", "code_postal", "ville"],
      "properties": {
        "rue": {"type": "string", "minLength": 1},
        "code_postal": {"type": "string", "pattern": "^\\d{5}$"},
        "ville": {"type": "string", "minLength": 1}
      }
    }
  }
}
```

**Validations côté SAP-Facture (avant d'appeler URSSAF)**

```python
from pydantic import BaseModel, EmailStr, validator
from datetime import date

class ParticularInscription(BaseModel):
    nom: str
    prenom: str
    email: EmailStr
    telephone: Optional[str] = None
    code_postal: str
    ville: str

    @validator('code_postal')
    def validate_code_postal(cls, v):
        if not v.isdigit() or len(v) != 5:
            raise ValueError("Code postal invalide (5 chiffres)")
        return v

    @validator('nom', 'prenom')
    def validate_names(cls, v):
        if len(v.strip()) == 0:
            raise ValueError("Nom et prenom requis")
        return v.strip().title()
```

### 4. Sécurité des credentials

**Stockage des client_id et client_secret**

```bash
# .env (JAMAIS committer)
URSSAF_CLIENT_ID=YOUR_CLIENT_ID_HERE
URSSAF_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
URSSAF_SANDBOX=false
```

**Chargement en Python**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    urssaf_client_id: str
    urssaf_client_secret: str
    urssaf_sandbox: bool = False

    class Config:
        env_file = ".env"

settings = Settings()
urssaf_client = URSSAFClient(
    settings.urssaf_client_id,
    settings.urssaf_client_secret,
    sandbox=settings.urssaf_sandbox
)
```

**NEVER**
- ❌ Hardcoder les credentials dans le code
- ❌ Logger les credentials complets
- ❌ Transmettre credentials en GET params (utiliser POST body ou Authorization header)
- ❌ Envoyer credentials via HTTP non-chiffré (toujours HTTPS + TLS 1.2+)

---

## Dépendances et prérequis

### Avant de commencer l'intégration

**Prérequis obligatoires**

1. **SIREN Jules**
   - Numéro SIREN : `991552019`
   - Statut : Actif chez l'URSSAF
   - Activité : Enseignement particulier

2. **Inscription URSSAF (flux administratif)**
   - Jules doit avoir un compte URSSAF existant
   - Demander auprès de l'URSSAF les credentials OAuth2 :
     - `client_id` (fourni par URSSAF)
     - `client_secret` (fourni par URSSAF)
   - Scope minimum : `invoicing` + `read`

3. **Numéro NOVA (optionnel mais recommandé)**
   - Numéro de déclaration NOVA (reporting trimestriel)
   - Utilisé pour l'onglet "Metrics NOVA" (phase 3)
   - Format : ex. `NOVA-2026-000123`

4. **Compte Swan/Indy**
   - Pour recevoir les virements URSSAF
   - IBAN : `FR76...` (à récupérer de l'API Swan GraphQL)
   - Utilisé pour le rapprochement bancaire

### Dépendances logicielles

**Python packages**

```
aiohttp>=3.9.0          # Client HTTP async
pydantic>=2.0          # Validations
pydantic-settings>=2.0 # Secrets management
tenacity>=8.2          # Retry logic
pybreaker>=0.7         # Circuit breaker
gspread>=5.10          # Google Sheets
google-auth>=2.25      # Google auth
```

**Configuration initiale**

```bash
# 1. Récupérer credentials URSSAF
echo "Demander client_id et client_secret auprès de URSSAF"

# 2. Créer .env
cat > .env << EOF
URSSAF_CLIENT_ID=your_client_id
URSSAF_CLIENT_SECRET=your_client_secret
URSSAF_SANDBOX=false  # true pour tests
EOF

# 3. Valider la connexion
python -c "
from app.integrations.urssaf_client import URSSAFClient
client = URSSAFClient(...)
token = await client.get_valid_token()
print(f'Token OK: {token[:20]}...')
"
```

---

## Environnements : Sandbox vs Production

### Environnement Sandbox

**URL** : `https://sandbox.urssaf.fr`

**Caractéristiques**
- Données réelles non affectées
- Délais instantanés (pas d'attente 48h réelle)
- Erreurs génériques (moins de détails)
- Tokens valides 1 heure (même qu'en prod)
- Rate limiting élevé (100 req/min)

**Clients de test pré-créés**

L'URSSAF fournit généralement des IDs test :
- `PART-SANDBOX-000001` (particulier valide)
- `PART-SANDBOX-INVALID` (ID invalide, pour tester 404)

**Cas de test en sandbox**

```python
# Test 1 : Inscription OK
response = await urssaf_client.post_particuliers({
    "identite": {"nom": "TEST", "prenom": "SANDBOX"},
    "email": "test.sandbox@example.com",
    "adresse": {...}
})
# Retour attendu : {id_technique: "PART-SANDBOX-000002"}

# Test 2 : Soumission facture (statut = CREE immédiatement)
response = await urssaf_client.post_demande_paiement({
    "id_client_urssaf": "PART-SANDBOX-000001",
    "montant_total_eur": 1500.00,
    ...
})
# Retour attendu : {id_demande: "DEM-SANDBOX-000001", statut: "CREE"}

# Test 3 : Polling (statut reste CREE, pas de client réel pour valider)
response = await urssaf_client.get_demande_status("DEM-SANDBOX-000001")
# Retour attendu : {statut: "CREE", ...}
```

**Configuration FastAPI**

```python
from app.integrations.urssaf_client import URSSAFClient

# Injecter l'environnement via env var
URSSAF_SANDBOX = os.getenv("URSSAF_SANDBOX", "true").lower() == "true"

urssaf_client = URSSAFClient(
    client_id=settings.urssaf_client_id,
    client_secret=settings.urssaf_client_secret,
    sandbox=URSSAF_SANDBOX
)
```

### Environnement Production

**URL** : `https://portailapi.urssaf.fr`

**Caractéristiques**
- Données réelles, impactent le système URSSAF
- Délais réels (48h pour validation client, etc.)
- Erreurs détaillées (pour debug)
- Tokens valides 1 heure
- Rate limiting strict (à déterminer avec URSSAF)

**Activation (checklist)**

- [ ] Client_id et client_secret de production validés avec URSSAF
- [ ] Google Sheets activée et onglets configurés
- [ ] Swan/Indy account créé et IBAN validé
- [ ] Logs centralisés (Sentry/ELK) configurés
- [ ] Alertes mises en place (erreurs URSSAF)
- [ ] Tests end-to-end réussis en sandbox
- [ ] Déploiement sur serveur de production
- [ ] Monitoring actif (métriques, uptime)

**Procédure de passage production**

```bash
# 1. Tester en sandbox d'abord
export URSSAF_SANDBOX=true
pytest tests/test_urssaf_integration.py

# 2. Déployer en production
export URSSAF_SANDBOX=false
export URSSAF_CLIENT_ID=prod_client_id
export URSSAF_CLIENT_SECRET=prod_client_secret
docker-compose -f docker-compose.prod.yml up -d

# 3. Vérifier
curl -H "Authorization: Bearer $(cat /tmp/token.txt)" \
  https://portailapi.urssaf.fr/api/v2/particuliers/PART-2026-000001
```

---

## Implémentation recommandée

### Architecture du code

**Arborescence suggérée**

```
sap-facture/
├── app/
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── urssaf_client.py          # ← Main URSSAF client
│   │   ├── token_manager.py          # ← Token cache + refresh
│   │   └── schemas.py                # ← Pydantic models
│   ├── services/
│   │   ├── invoice_service.py        # ← Créer facture (appelle URSSAF)
│   │   ├── client_service.py         # ← Inscrire client (appelle URSSAF)
│   │   ├── payment_tracker.py        # ← Polling statut (cron)
│   │   └── notifications.py          # ← Reminders T+36h
│   ├── models/
│   │   └── invoice.py                # ← SQLAlchemy / Pydantic models
│   └── main.py                       # ← FastAPI app
├── tests/
│   ├── test_urssaf_client.py        # ← Unit tests
│   ├── test_integration_urssaf.py    # ← Integration tests (sandbox)
│   └── fixtures/
│       └── urssaf_responses.json     # ← Mock responses
└── .env                              # ← URSSAF credentials

```

### Classe URSSAFClient (skeleton)

```python
# app/integrations/urssaf_client.py

from __future__ import annotations

import logging
from typing import Optional, Any
from datetime import datetime

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

from .token_manager import TokenManager
from .schemas import (
    ParticularInscriptionRequest,
    DemandePaiementRequest,
    DemandePaiementResponse,
)

logger = logging.getLogger(__name__)

class URSSAFError(Exception):
    """Base exception for URSSAF API errors"""
    pass

class URSSAFValidationError(URSSAFError):
    """400/422 : Client error, non-retryable"""
    pass

class URSSAFAuthError(URSSAFError):
    """401/403 : Auth error"""
    pass

class URSSAFNotFoundError(URSSAFError):
    """404 : Resource not found"""
    pass

class URSSAFServerError(URSSAFError):
    """5xx : Server error, retryable"""
    pass

class URSSAFClient:
    """Client API URSSAF avec OAuth2, retry logic, et circuit breaker"""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        sandbox: bool = False,
        timeout: int = 20
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.sandbox = sandbox
        self.timeout = timeout
        self.base_url = (
            "https://sandbox.urssaf.fr" if sandbox
            else "https://portailapi.urssaf.fr"
        )
        self.token_manager = TokenManager(client_id, client_secret, self.base_url)

    async def close(self) -> None:
        """Cleanup resources"""
        await self.token_manager.close()

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True
    )
    async def post_particulier(
        self,
        data: ParticularInscriptionRequest
    ) -> dict[str, Any]:
        """Inscrire un nouveau client particulier"""

        token = await self.token_manager.get_valid_token()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/api/v2/particuliers",
                    json=data.model_dump(),
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    return await self._handle_response(response)
            except asyncio.TimeoutError as e:
                logger.warning(f"POST /particuliers timeout, will retry: {e}")
                raise

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True
    )
    async def post_demande_paiement(
        self,
        data: DemandePaiementRequest
    ) -> DemandePaiementResponse:
        """Soumettre une demande de paiement"""

        token = await self.token_manager.get_valid_token()

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.base_url}/api/v2/demandes-paiement",
                    json=data.model_dump(),
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    return DemandePaiementResponse(**await self._handle_response(response))
            except asyncio.TimeoutError:
                logger.warning(f"POST /demandes-paiement timeout, will retry")
                raise

    async def get_demande_status(
        self,
        id_demande: str
    ) -> dict[str, Any]:
        """Récupérer le statut d'une demande de paiement"""

        token = await self.token_manager.get_valid_token()

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/v2/demandes-paiement/{id_demande}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                return await self._handle_response(response)

    async def _handle_response(self, response: aiohttp.ClientResponse) -> dict[str, Any]:
        """Parse response et lever exceptions appropriées"""

        body = await response.json()

        # Success
        if response.status in [200, 201]:
            return body

        # Client errors (non-retryable)
        if response.status == 400:
            logger.error(f"Bad request: {body}")
            raise URSSAFValidationError(f"400: {body.get('message', 'Invalid payload')}")

        if response.status == 401:
            logger.warning("Token invalid, will refresh on next request")
            self.token_manager.token = None
            raise URSSAFAuthError("401: Unauthorized")

        if response.status == 403:
            logger.error(f"Forbidden: {body}")
            raise URSSAFAuthError("403: Forbidden")

        if response.status == 404:
            logger.error(f"Not found: {body}")
            raise URSSAFNotFoundError(f"404: {body.get('message', 'Not found')}")

        if response.status == 409:
            logger.error(f"Conflict: {body}")
            raise URSSAFValidationError(f"409: {body.get('message', 'Conflict')}")

        if response.status == 422:
            logger.error(f"Unprocessable entity: {body}")
            raise URSSAFValidationError(f"422: {body.get('message', 'Validation failed')}")

        # Rate limiting (retryable)
        if response.status == 429:
            retry_after = response.headers.get("Retry-After", "60")
            logger.warning(f"Rate limited, retry after {retry_after}s")
            raise aiohttp.ClientError(f"429: Rate limited, retry after {retry_after}s")

        # Server errors (retryable)
        if response.status >= 500:
            logger.error(f"Server error {response.status}: {body}")
            raise aiohttp.ClientError(f"{response.status}: Server error")

        # Unknown
        logger.error(f"Unknown response status {response.status}: {body}")
        raise URSSAFError(f"Unexpected response {response.status}")
```

### Schema Pydantic

```python
# app/integrations/schemas.py

from __future__ import annotations

from typing import Optional, Literal
from datetime import date
from pydantic import BaseModel, EmailStr, Field

class IdentiteRequest(BaseModel):
    nom: str = Field(..., min_length=1, max_length=100)
    prenom: str = Field(..., min_length=1, max_length=100)
    date_naissance: Optional[date] = None

class AdresseRequest(BaseModel):
    rue: str = Field(..., min_length=1)
    code_postal: str = Field(..., pattern=r"^\d{5}$")
    ville: str = Field(..., min_length=1)
    pays: str = Field(default="FR", pattern=r"^[A-Z]{2}$")

class ParticularInscriptionRequest(BaseModel):
    identite: IdentiteRequest
    email: EmailStr
    telephone: Optional[str] = None
    adresse: AdresseRequest
    regime: Literal["micro_entreprise", "eirl"] = "micro_entreprise"

class ParticularInscriptionResponse(BaseModel):
    id_technique: str
    id_urssaf: str
    email: str
    statut_inscription: str
    date_inscription: str
    lien_portail: Optional[str] = None

class PeriodeRequest(BaseModel):
    date_debut: date
    date_fin: date
    nombre_heures: float = Field(..., gt=0)
    taux_horaire: float = Field(..., gt=0)

class DemandePaiementRequest(BaseModel):
    id_client_urssaf: str
    montant_total_eur: float = Field(..., gt=0)
    montant_contribution_salariale_eur: Optional[float] = None
    montant_contribution_patronale_eur: Optional[float] = None
    periode: PeriodeRequest
    nature_service: str = "cours_particuliers"
    descriptif_service: Optional[str] = None
    email_validation: EmailStr
    devise: str = "EUR"
    reference_interne: Optional[str] = None

class DemandePaiementResponse(BaseModel):
    id_demande: str
    id_demande_urssaf: str
    statut: str
    date_creation: str
    date_expiration_validation: str
    montant_accepte: float
    lien_client: Optional[str] = None
```

### Cron Jobs (APScheduler)

```python
# app/main.py ou app/tasks/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.integrations.urssaf_client import URSSAFClient
from app.services.payment_tracker import PaymentTracker
from app.services.notifications import NotificationService

scheduler = AsyncIOScheduler()

async def setup_scheduler(urssaf_client: URSSAFClient, sheets_client, email_client):
    """Setup cron jobs pour URSSAF polling et reminders"""

    payment_tracker = PaymentTracker(urssaf_client, sheets_client)
    notification_service = NotificationService(email_client, sheets_client)

    # Polling statuts toutes les 4 heures
    scheduler.add_job(
        payment_tracker.sync_all_invoice_statuses,
        'cron',
        hour='0,4,8,12,16,20',
        minute=0,
        id='urssaf_sync_status',
        name='URSSAF Status Polling'
    )

    # Reminders T+36h (vérifier toutes les heures)
    scheduler.add_job(
        notification_service.send_reminders_36h,
        'cron',
        hour='*',
        minute=15,
        id='reminder_36h_check',
        name='Check 36h Reminders'
    )

    scheduler.start()
```

---

## Résumé et points clés

### Checklist d'implémentation

- [ ] TokenManager : récupérer + cacher + renouveler tokens OAuth2
- [ ] URSSAFClient : 5 endpoints (oauth, particuliers, demandes POST, GET, DELETE)
- [ ] Retry logic : 4 tentatives, backoff exponentiel 2-8s, circuit breaker
- [ ] Validations : Pydantic schemas avant chaque appel
- [ ] Error handling : 13 codes HTTP différents, actions spécifiques
- [ ] Polling : Cron toutes les 4h, sync statuts Google Sheets
- [ ] Reminders : Email à Jules si EN_ATTENTE > 36h
- [ ] Tests : Unit (mocks) + Integration (sandbox)
- [ ] Monitoring : Logs, Sentry alerts, métriques API
- [ ] Sandbox → Production : Checklist complète avant passage

### Dépendances critiques

1. **Credentials URSSAF** : client_id + client_secret (demander à support)
2. **Google Sheets API** : Pour stocker données factures/clients
3. **Swan/Indy** : Pour rapprochement bancaire (phase 2)
4. **Email SMTP** : Pour reminders (phase 2)

### Timeline estimée

- **Phase 1 (Semaine 1)** :
  - TokenManager + URSSAFClient (oauth + particuliers + demandes)
  - Polling et cron basic
  - Tests sandbox

- **Phase 2 (Semaine 2-3)** :
  - Reminders T+36h + email
  - Rapprochement Swan
  - Circuit breaker + monitoring

- **Phase 3 (Mois 2+)** :
  - Optimisations (cache, batch requests)
  - Reporting NOVA
  - Auto-sync Google Sheets

---

**Document généré** : Winston, Analyste Technique Intégration API
**Status** : Prêt pour développement Phase 1
**Next Step** : Demander credentials URSSAF officiels auprès de support
