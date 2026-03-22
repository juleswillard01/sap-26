# Tools — Scripts Dev & Exploration

Scripts utilitaires pour le reverse-engineering des APIs Indy et la configuration Gmail.
**Ne font PAS partie du code source** — usage ponctuel uniquement.

## Scripts

| Script | Usage | Bibliothèque |
|--------|-------|-------------|
| `gmail_auth.py` | Setup OAuth2 Gmail (token first-time) | google-auth |
| `indy_2fa.py` | Login Indy avec 2FA auto (nodriver + Gmail IMAP) | nodriver |
| `indy_intercept.py` | Interception CDP network Indy (capture API calls) | nodriver |
| `indy_oauth.py` | Automation Google OAuth pour Indy (bypass Turnstile) | Playwright |
| `indy_oauth_discovery.py` | Discovery OAuth config Indy (client_id, scopes) | nodriver |

## Prérequis

- Credentials dans `.env` ou `.env.mcp`
- `uv sync` pour les dépendances

## Lancer

```bash
uv run python tools/<script>.py
```
