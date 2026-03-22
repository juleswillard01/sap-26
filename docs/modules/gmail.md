# Module Gmail

Cartographie du module Gmail pour SAP-Facture.

**Role** : Extraction automatique des codes 2FA Indy depuis Gmail pour supporter le scraping Playwright headless.

---

## Fichiers

| Fichier | Role |
|---------|------|
| `src/adapters/gmail_reader.py` | Deux classes reader (IMAP + OAuth2 API) |
| `tools/gmail_auth.py` | Script one-shot d'authentification OAuth2 |
| `tests/test_gmail_reader.py` | Tests GmailReader (IMAP) + GmailAPIReader (init/close) |
| `tests/test_gmail_api_reader.py` | Tests RED GmailAPIReader (connect/search/polling, tous skipped) |
| `docs/guides/gmail-setup.md` | Guide de configuration consolide |

---

## Architecture

```
src/config.py (Settings)
    |
    |-- gmail_imap_user / gmail_imap_password  --> GmailReader (IMAP)
    |-- gmail_oauth_client_file / gmail_oauth_token_file --> GmailAPIReader (OAuth2)
    |
src/adapters/gmail_reader.py
    |
    +-- GmailReader         IMAP4_SSL, App Password
    |     connect()         Login IMAP
    |     get_latest_2fa_code(timeout_sec, poll_interval_sec, sender_filter, label_name)
    |     _check_inbox()    SELECT label, SEARCH UNSEEN, FETCH RFC822
    |     _get_email_body() Parse MIME (plaintext/HTML)
    |     _extract_code()   Regex 4-8 digits, preference 6 digits
    |     close()           IMAP logout
    |
    +-- GmailAPIReader      google-api-python-client, OAuth2
          __init__(client_file, token_file)   Valide existence client_file
          connect()         Credentials.from_service_account_file + build()
          get_latest_2fa_code(timeout_sec, poll_interval_sec, sender_filter, label_name)
          _search_and_extract_code()   query "from:X is:unread newer_than:5m"
          _get_email_body(msg_id)      GET message format=full, base64 decode
          _extract_code()              Meme regex que GmailReader
          close()                      Reset service a None
```

---

## Configuration (src/config.py)

```python
# Settings fields
gmail_imap_user: str = ""
gmail_imap_password: str = ""
gmail_oauth_client_file: str = "credentials/gmail_oauth.json"
gmail_oauth_token_file: str = "credentials/gmail_token.json"
```

---

## Pattern d'utilisation

### IMAP (GmailReader)

```python
from src.adapters.gmail_reader import GmailReader
from src.config import Settings

reader = GmailReader(Settings())
reader.connect()
code = reader.get_latest_2fa_code(
    timeout_sec=60,
    poll_interval_sec=5,
    sender_filter="indy",
    label_name="Indy-2FA",
)
reader.close()
```

### OAuth2 (GmailAPIReader)

```python
from src.adapters.gmail_reader import GmailAPIReader

reader = GmailAPIReader(
    client_file="credentials/gmail_oauth.json",
    token_file="credentials/gmail_token.json",
)
reader.connect()
code = reader.get_latest_2fa_code(
    timeout_sec=60,
    sender_filter="noreply@indy.fr",
    label_name="Indy-2FA",
)
reader.close()
```

---

## Integration prevue

Le code 2FA extrait est injecte dans le flow Playwright Indy :

```
Indy login page --> 2FA prompt --> GmailReader.get_latest_2fa_code()
                                        |
                                   code 6 digits
                                        |
                                   page.fill("input[name='2fa']", code)
```

---

## Extraction du code 2FA

Regex partagee entre les deux readers :

```python
CODE_PATTERN = re.compile(r"\b(\d{4,8})\b")
```

- Accepte 4 a 8 digits
- Preference pour les codes 6 digits (standard 2FA)
- Ignore les nombres < 4 digits

---

## Tests

### test_gmail_reader.py (actifs)

| Classe | Methodes | Statut |
|--------|----------|--------|
| TestGmailReaderConnect | 3 tests | GREEN |
| TestGmailReaderGetLatest2FACode | 5 tests | GREEN |
| TestGmailReaderCheckInbox | 4 tests | GREEN |
| TestGmailReaderExtractCode | 7 tests | GREEN |
| TestGmailReaderGetEmailBody | 5 tests | GREEN |
| TestGmailReaderClose | 3 tests | GREEN |
| TestGmailAPIReaderInit | 3 tests | GREEN |
| TestGmailAPIReaderConnect | 2 tests (1 skipped) | PARTIAL |

### test_gmail_api_reader.py (RED / skipped)

Tous les tests sont commentes ou `@pytest.mark.skip`. Ce fichier contient les specs pour une implementation complete de GmailAPIReader avec :
- OAuth2 token load/refresh (InstalledAppFlow)
- Gmail API search
- Base64 body decoding
- Polling avec timeout
- Filtrage sender

**Statut** : Tests RED en attente d'implementation. Le GmailAPIReader actuel utilise `service_account` au lieu de `InstalledAppFlow` -- divergence avec les tests prevus.

---

## Dependances

| Package | Usage | Necessaire pour |
|---------|-------|-----------------|
| `imaplib` (stdlib) | Connexion IMAP4_SSL | GmailReader |
| `google-auth` | Credentials OAuth2 | GmailAPIReader |
| `google-auth-oauthlib` | InstalledAppFlow (consent browser) | tools/gmail_auth.py |
| `google-auth-httplib2` | Transport HTTP | GmailAPIReader |
| `google-api-python-client` | `build("gmail", "v1")` | GmailAPIReader |

---

## Securite

- Scope OAuth2 : `gmail.readonly` -- lecture seule, pas de send/delete
- Credentials dans `credentials/` : .gitignore
- App Password : limite aux protocoles IMAP/SMTP
- Aucun secret dans les logs (logger.error masque les credentials)
- `.env` pour toutes les valeurs sensibles

---

## Points d'attention

1. **GmailAPIReader.connect()** utilise `Credentials.from_service_account_file` alors que `tools/gmail_auth.py` genere des tokens OAuth2 utilisateur (InstalledAppFlow). Ces deux mecanismes sont incompatibles -- le reader devrait utiliser `Credentials.from_authorized_user_file` pour consommer les tokens generes par le script auth.

2. **`_extract_code`** est duplique (methode statique identique dans les deux classes). Candidat pour extraction en fonction module-level.

3. **test_gmail_api_reader.py** contient uniquement des tests commentes/skipped. L'implementation GmailAPIReader complete avec InstalledAppFlow reste a faire.
