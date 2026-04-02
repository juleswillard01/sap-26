# Intégration URSSAF/AIS (Référence Complète)

## Architecture : AIS Playwright Headless

**Contrainte fondamentale** : URSSAF ne fournit pas d'API publique directe. L'intégration passe par AIS (avance-immediate.fr), une plateforme SaaS qui expose un formulaire web pour les demandes d'avance.

### Flux

1. Jules crée facture dans AIS UI (PDF généré, client enregistré)
2. SAP-Facture scrapy AIS via Playwright (LECTURE seule)
3. API URSSAF interne (via AIS backend) accepte demande
4. Email client reçoit lien validation
5. Client valide → URSSAF transfère → Indy reçoit virement

### Limitation

- **PAS d'API URSSAF public** — AIS gère authentication/authorization
- **PAS d'API AIS public** — Playwright est le seul vecteur

---

## Playwright Patterns

### Login AIS

```python
async def login_ais(page, email: str, password: str):
    await page.goto("https://avance-immediate.fr/login")
    await page.fill("input[name='email']", email)
    await page.fill("input[name='password']", password)
    await page.click("button[type='submit']")
    await page.wait_for_url("**/dashboard", timeout=10000)
    return page
```

### Polling URSSAF Status

```python
async def poll_urssaf_status(page, demande_id: str, max_retries: int = 6):
    """Poll avec backoff exponentiel jusqu'à CREE ou ERREUR."""
    for attempt in range(max_retries):
        await page.goto(f"https://avance-immediate.fr/demandes/{demande_id}")
        status_el = await page.query_selector("[data-status]")
        if status_el:
            status = await status_el.get_attribute("data-status")
            if status in ["CREE", "ERREUR"]:
                return status
        await asyncio.sleep(2 ** attempt)  # backoff : 1s, 2s, 4s, 8s, 16s, 32s
    raise TimeoutError(f"Polling URSSAF timeout after {max_retries} retries")
```

### Retry Logic

```python
async def with_retry(func, max_retries: int = 3):
    """Retry avec backoff exponentiel."""
    for attempt in range(max_retries):
        try:
            return await func()
        except PlaywrightError as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
```

---

## Intégration API URSSAF (via AIS)

### Payload Soumission

Envoyé via formulaire AIS, qui transmet à URSSAF backend :

```python
payload = {
    "client_id": "C123",
    "client_name": "Dupont",
    "client_email": "dupont@example.com",
    "montant": 1000.0,
    "nature_travaux": "COURS_PARTICULIERS",
    "date_debut": "2026-01-15",
    "date_fin": "2026-01-31",
    "description": "Cours de maths",
}
```

### Réponses URSSAF

- **CREE** : Payload accepté, demande_id stocké, email client envoyé
- **ERREUR** : Montant hors limites, client non inscrit, données invalides
- **EN_ATTENTE** → **VALIDE** : Client a cliqué lien, validation en place
- **VALIDE** → **PAYE** : URSSAF a effectué le virement

---

## Gestion 2FA et Authentification

### Indy 2FA (OAuth)

Indy Banking utilise OAuth Google. Playwright peut injecter token si disponible :

```python
async def setup_indy_oauth(page, google_token: str):
    """Injecter token OAuth pour Indy (simulé)."""
    await page.goto("https://app.indy.fr")
    # Indy OAuth flow nécessite navigation vers Google puis back
    # Pas d'injection directe possible sans MFA
```

### Fallback : Email + Password

```python
async def login_indy_password(page, email: str, password: str):
    await page.goto("https://app.indy.fr/login")
    await page.fill("input[type='email']", email)
    await page.fill("input[type='password']", password)
    await page.click("button[type='submit']")
    # Attendre MFA (TOTP, SMS, etc.)
```

### Turnstile (Cloudflare)

AIS et Indy utilisent Cloudflare Turnstile pour anti-bot. Playwright peut :
1. Passer automatiquement (requiert compte valide)
2. Utilisateur résout manuellement (mode headless=false)

```python
async def handle_turnstile(page):
    """Attendre Turnstile auto-résolu ou timeout."""
    try:
        await page.wait_for_selector("[data-cf-turnstile].done", timeout=30000)
    except PlaywrightError:
        logger.warning("Turnstile non résolu dans 30s")
```

---

## Session & Cookies

### Persistence

```python
context = await browser.new_context(
    storage_state="/path/to/cookies.json"
)
page = await context.new_page()
# Cookies restaurés automatiquement
```

### Timeout

- AIS : session 30 min inactivité
- Indy : session 60 min inactivité
- Playwright default : 30s par action

---

## Gestion Erreurs

### Erreurs Transientes

- 429 (rate limit) → retry backoff
- Timeout réseau → retry
- Playwright timeout → screenshot + log

### Erreurs Permanentes

- Sélecteur cassé (AIS UI changé) → alert + screenshot
- Credentials invalides → log + abort
- Client non inscrit URSSAF → attendre inscription

### Screenshots

```python
if error:
    await page.screenshot(path=f"io/cache/error_{timestamp}.png")
    # SANS données sensibles (email, password, IBAN strippés)
```

---

## Rate Limiting

### Indy Export Journal

- Limit : 4h entre deux exports (empirique)
- Raison : risque rate limit Indy ou trigger alertes fraude

### AIS Polling

- Limit : 4h entre deux polls de statut (évite bot detection)
- Batching : poll max 3 demandes en parallèle

---

## Secrets & Configuration

### .env Variables

```
AIS_EMAIL=jules@example.com
AIS_PASSWORD=secure_password_ais
INDY_EMAIL=jules@example.com
INDY_PASSWORD=secure_password_indy
INDY_TOTP_SECRET=XXXXX (optionnel, si TOTP configuré)
PLAYWRIGHT_HEADLESS=true
```

### Validation Pydantic

```python
from pydantic_settings import BaseSettings

class PlaywrightConfig(BaseSettings):
    ais_email: str
    ais_password: str
    indy_email: str
    indy_password: str
    playwright_headless: bool = True

    class Config:
        env_file = ".env"
```

---

## Monitoring & Logging

### Logs Critiques

```python
logger.info("AIS login successful", extra={"email": email})
logger.warning("URSSAF polling timeout", extra={"demande_id": demande_id})
logger.error("Turnstile failed", exc_info=True)
```

### Métriques

- Login success/fail rate
- Polling retry count
- Indy export success rate
- Moyenne temps URSSAF CREE → VALIDE

---

## Avenir

Phase 2 : si URSSAF expose API publique, remplacer Playwright par HTTP client.
