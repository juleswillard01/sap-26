# Gmail Setup Guide

Configurer Gmail pour l'extraction automatique des codes 2FA Indy dans SAP-Facture.

**Compte cible** : `jules.willard.pro@gmail.com`
**Objectif** : Lire les emails 2FA de `noreply@indy.fr` pour automatiser le login Indy via Playwright.

---

## 1. Choix du mode d'authentification

| Critere | IMAP + App Password | OAuth2 API |
|---------|---------------------|------------|
| Setup | 5 min | 15 min |
| Complexite | Simple | Moyenne |
| Necessite 2FA Google | Oui | Non |
| Future-proof | Bon | Meilleur |
| Rate limits | Standard IMAP | API quotas (Gmail API) |
| Recommandation | MVP / dev local | Production |

Les deux modes sont implementes dans `src/adapters/gmail_reader.py` :
- `GmailReader` : IMAP (App Password)
- `GmailAPIReader` : Gmail API (OAuth2)

---

## 2. Prerequisites

### Dependencies (pyproject.toml)

```toml
[project]
dependencies = [
    # IMAP : aucune dep supplementaire (stdlib imaplib)
    # OAuth2 :
    "google-auth>=2.30",
    "google-auth-oauthlib>=1.2.0",
    "google-auth-httplib2>=0.2.0",
    "google-api-python-client>=2.110.0",
]
```

```bash
uv add google-auth-oauthlib google-auth-httplib2 google-api-python-client
uv sync
```

---

## 3. Gmail : label et filtre (commun aux deux modes)

### 3.1 Creer le label `Indy-2FA`

1. Aller sur https://mail.google.com
2. Settings (icone engrenage) > See all settings > Labels
3. Create new label : `Indy-2FA`

### 3.2 Creer le filtre email

1. Settings > Filters and Blocked Addresses > Create a new filter
2. From : `noreply@indy.fr`
3. Create filter > Apply the label : `Indy-2FA`
4. Create filter

---

## 4. Configuration IMAP (App Password)

### 4.1 Activer la 2FA Google

1. https://myaccount.google.com/security
2. 2-Step Verification > Get started
3. Choisir SMS ou authenticator app, verifier

### 4.2 Generer un App Password

1. https://myaccount.google.com/security > App passwords
2. Select Mail > Select Linux > Generate
3. Copier le mot de passe 16 caracteres (sans espaces)

### 4.3 Stocker dans `.env`

```env
GMAIL_IMAP_USER=jules.willard.pro@gmail.com
GMAIL_IMAP_PASSWORD=abcdefghijklmnop
```

### 4.4 Tester

```bash
uv run python -c "
from src.adapters.gmail_reader import GmailReader
from src.config import Settings
reader = GmailReader(Settings())
reader.connect()
print('IMAP OK')
reader.close()
"
```

---

## 5. Configuration OAuth2 (Gmail API)

### 5.1 Google Cloud Console

1. https://console.cloud.google.com > selectionner le projet existant (Sheets API)
2. APIs & Services > Library > chercher "Gmail API" > ENABLE

### 5.2 Consent screen (si pas deja configure)

1. APIs & Services > OAuth consent screen
2. User Type : External > CREATE
3. App name : `SAP-Facture`, email support : `jules.willard.pro@gmail.com`
4. SAVE AND CONTINUE sur chaque ecran
5. Test users : + ADD USERS > `jules.willard.pro@gmail.com`

### 5.3 Creer les credentials OAuth

1. APIs & Services > Credentials > + CREATE CREDENTIALS > OAuth client ID
2. Application type : Desktop app, Name : `SAP-Facture Gmail`
3. CREATE > DOWNLOAD le JSON
4. Sauver sous `credentials/gmail_oauth.json`

### 5.4 Premier consentement OAuth

```bash
uv run python tools/gmail_auth.py
```

- Le navigateur s'ouvre, cliquer Allow
- Token sauvegarde dans `credentials/gmail_token.json`

### 5.5 Stocker dans `.env`

```env
GMAIL_OAUTH_CLIENT_FILE=credentials/gmail_oauth.json
GMAIL_OAUTH_TOKEN_FILE=credentials/gmail_token.json
```

### 5.6 Tester

```bash
uv run python -c "
from src.adapters.gmail_reader import GmailAPIReader
reader = GmailAPIReader('credentials/gmail_oauth.json', 'credentials/gmail_token.json')
reader.connect()
print('OAuth2 OK')
reader.close()
"
```

---

## 6. Securite

- `credentials/gmail_oauth.json` et `credentials/gmail_token.json` : dans `.gitignore`, jamais commites
- `.env` : dans `.gitignore`
- Scope OAuth2 : `gmail.readonly` uniquement (pas de send/delete)
- App Password : limite IMAP/SMTP, revocable a tout moment
- Rotation : revoquer et re-generer si expose

Verification :
```bash
grep "credentials/" .gitignore       # doit matcher
git status credentials/ 2>&1         # rien ne doit etre tracked
```

---

## 7. Troubleshooting

| Probleme | Cause | Solution |
|----------|-------|----------|
| `gmail_oauth.json not found` | Fichier absent | Re-telecharger depuis Cloud Console > Credentials > OAuth 2.0 Client IDs |
| `Gmail API not enabled` | API desactivee | Cloud Console > Library > Gmail API > ENABLE |
| `LOGIN failed` (IMAP) | Mot de passe Gmail classique | Utiliser un App Password (section 4.2) |
| `App passwords` invisible | 2FA non activee | Activer 2FA d'abord (section 4.1) |
| `Token expired` | Refresh token invalide | Supprimer `credentials/gmail_token.json`, relancer `tools/gmail_auth.py` |
| `No 2FA emails found` | Label/filtre manquant | Verifier label `Indy-2FA` et filtre `from:noreply@indy.fr` (section 3) |
| Navigateur ne s'ouvre pas | Firewall/WSL | Aller manuellement sur `http://localhost:8888` |

---

## References

- Gmail API : https://developers.google.com/gmail/api
- OAuth2 Scopes : https://developers.google.com/identity/protocols/oauth2/scopes#gmail
- App Passwords : https://support.google.com/accounts/answer/185833
- google-auth-oauthlib : https://github.com/googleapis/google-auth-library-python-oauthlib
