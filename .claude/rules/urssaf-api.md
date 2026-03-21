# AIS Sync — Lecture Playwright

**Source de vérité** : `docs/CDC.md` §2

---

## Principe Fondamental

**SAP-Facture LIT les données depuis AIS (app.avance-immediate.fr) via Playwright headless.**
**AIS gère la facturation URSSAF. SAP-Facture ne fait que SYNCHRONISER.**

```
┌─────────────────────┐
│  SAP-Facture        │
│  (Lecture + Sync)   │
└──────────┬──────────┘
           │
           │ Lecture (Playwright)
           │ Écriture (Sheets)
           │
┌──────────▼──────────┐          ┌──────────────────┐
│  AIS Portal         │◄────────►│  URSSAF API      │
│  (Gestion Clients   │  Facturation   │  Paiements       │
│   & Factures)       │          │                  │
└─────────────────────┘          └──────────────────┘
```

---

## Ce que SAP-Facture LIT dans AIS

- **Clients** : nom, prénom, email, statut URSSAF, ID technique
- **Factures/Demandes** : montant, statut, dates de suivi, références de virement
- **Statuts** : CREE, EN_ATTENTE, VALIDEE, PAYEE, REJETE, EXPIRE, ANNULE

---

## Ce que SAP-Facture NE FAIT PAS

- **PAS** de création de factures (AIS les crée)
- **PAS** d'inscription de clients (AIS le fait)
- **PAS** de soumission à URSSAF (AIS l'envoie)
- **PAS** d'accès à l'API URSSAF directement
- **PAS** de modification de données dans AIS (lecture seule)

---

## 1. Configuration Générale

### Identifiants AIS

```
AIS_BASE_URL=https://app.avance-immediate.fr
AIS_EMAIL=jules@example.com
AIS_PASSWORD=***  # stocké en .env, jamais en codebase
```

### Pydantic Settings

```python
from pydantic_settings import BaseSettings

class AISSettings(BaseSettings):
    ais_email: str
    ais_password: str
    ais_base_url: str = "https://app.avance-immediate.fr"
    ais_headless: bool = True
    ais_timeout_sec: int = 30
    ais_max_retries: int = 3
    ais_retry_backoff_factor: float = 2
    ais_screenshot_dir: str = "io/cache/ais-errors"
    ais_sync_cron: str = "0 9,13,17,21 * * *"

    class Config:
        env_file = ".env"
        case_sensitive = False
```

### Browser Management

- **Headless** : toujours vrai (pas d'interface graphique)
- **Cookies persistés** : localStorage/sessionStorage entre appels
- **Timeout obligatoire** : 30s par action (sinon abort)
- **User-Agent** : standard Playwright (pas de détection bot)
- **SSL validation** : activer par défaut

---

## 2. AISAdapter — Implémentation Lecture Playwright

### Classe Principale

```python
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class AISSettings(BaseModel):
    email: str
    password: str
    base_url: str = "https://app.avance-immediate.fr"
    timeout_sec: int = 30
    max_retries: int = 3


class AISAdapter:
    def __init__(self, settings: AISSettings) -> None:
        self._settings = settings
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    async def connect(self) -> None:
        """Initialiser browser Playwright et logger à AIS"""
        async with async_playwright() as p:
            self._browser = await p.chromium.launch(headless=True)
            context = await self._browser.new_context()
            self._page = await context.new_page()
            await self._login()

    async def _login(self) -> None:
        """Se connecter à AIS avec retry 3x"""
        for attempt in range(self._settings.max_retries):
            try:
                await self._page.goto(
                    f"{self._settings.base_url}/login",
                    timeout=self._settings.timeout_sec * 1000
                )
                await self._page.fill("input[name='email']", self._settings.email)
                await self._page.fill("input[name='password']", self._settings.password)
                await self._page.click("button[type='submit']")
                await self._page.wait_for_selector(".dashboard, .clients", timeout=10000)
                logger.info("AIS login successful", extra={"attempt": attempt + 1})
                return

            except Exception as e:
                logger.warning(
                    "AIS login attempt failed",
                    extra={"attempt": attempt + 1, "error": str(e)}
                )
                if attempt == self._settings.max_retries - 1:
                    await self._screenshot_error("login-failed")
                    logger.error("AIS login failed after retries", exc_info=True)
                    raise
                await asyncio.sleep(2 ** attempt)

    async def _screenshot_error(self, context: str) -> None:
        """Capturer screenshot en cas d'erreur (RGPD-safe)"""
        if self._page:
            try:
                from uuid import uuid4
                filename = f"{self._settings.screenshot_dir}/{context}-{uuid4()}.png"
                await self._page.screenshot(path=filename)
                logger.info("Error screenshot saved", extra={"file": filename})
            except Exception as e:
                logger.error("Failed to capture screenshot", exc_info=True)

    async def close(self) -> None:
        """Fermer browser"""
        if self._browser:
            await self._browser.close()
```

---

## 3. Méthodes Lecture — Scraping AIS

### 3.1 Lire Clients

**But** : Synchroniser la liste clients depuis AIS vers Google Sheets.

**Étapes Playwright** :
1. Naviguer vers page clients AIS
2. Attendre tableau clients
3. Extraire : nom, prénom, email, statut URSSAF, ID technique
4. Écrire dans onglet Clients (batch)

**Pseudo-code** :

```python
async def scrape_clients(self) -> list[dict[str, str]]:
    """Scraper liste clients depuis AIS"""
    try:
        await self._page.goto(
            f"{self._settings.base_url}/clients",
            timeout=self._settings.timeout_sec * 1000
        )
        await self._page.wait_for_selector("table tbody tr", timeout=10000)

        clients = []
        rows = await self._page.query_selector_all("table tbody tr")

        for row in rows:
            nom = await row.text_content("td:nth-child(1)")
            prenom = await row.text_content("td:nth-child(2)")
            email = await row.text_content("td:nth-child(3)")
            statut = await row.text_content("td:nth-child(4)")
            ais_id = await row.text_content("td:nth-child(5)")

            clients.append({
                "nom": nom.strip(),
                "prenom": prenom.strip(),
                "email": email.strip(),
                "statut_urssaf": statut.strip(),
                "ais_id": ais_id.strip(),
            })

        logger.info("Clients scrapés", extra={"count": len(clients)})
        return clients

    except Exception as e:
        await self._screenshot_error("scrape-clients-failed")
        logger.error("Failed to scrape clients", exc_info=True)
        raise
```

---

### 3.2 Lire Factures/Demandes

**But** : Synchroniser la liste factures depuis AIS vers Google Sheets (statuts, montants, références).

**Étapes Playwright** :
1. Naviguer vers page demandes AIS
2. Attendre tableau demandes
3. Extraire : ID demande, montant, statut, dates, référence virement (si PAYEE)
4. Écrire dans onglet Factures (batch)

**Pseudo-code** :

```python
async def scrape_invoices(self) -> list[dict[str, str]]:
    """Scraper liste factures depuis AIS"""
    try:
        await self._page.goto(
            f"{self._settings.base_url}/demandes",
            timeout=self._settings.timeout_sec * 1000
        )
        await self._page.wait_for_selector("table tbody tr", timeout=10000)

        invoices = []
        rows = await self._page.query_selector_all("table tbody tr")

        for row in rows:
            demande_id = await row.text_content("td:nth-child(1)")
            montant = await row.text_content("td:nth-child(2)")
            statut = await row.text_content("td:nth-child(3)")
            date_creation = await row.text_content("td:nth-child(4)")
            reference_virement = await row.text_content("td:nth-child(5)")  # peut être vide

            invoices.append({
                "ais_demande_id": demande_id.strip(),
                "montant": montant.strip(),
                "statut": statut.strip(),
                "date_creation": date_creation.strip(),
                "reference_virement": reference_virement.strip() if reference_virement else "",
            })

        logger.info("Factures scrapées", extra={"count": len(invoices)})
        return invoices

    except Exception as e:
        await self._screenshot_error("scrape-invoices-failed")
        logger.error("Failed to scrape invoices", exc_info=True)
        raise
```

---

## 4. Machine à États — Synchronisation Statuts

**États (lecture depuis AIS)** :

```
EN_ATTENTE
  ├─→ VALIDEE (client a cliqué email AIS)
  │    ├─→ PAYEE (URSSAF a effectué virement)
  │    │    └─→ RAPPROCHE (lettrage OK)
  │    └─→ EXPIREE (délai 48h dépassé)
  └─→ REFUSEE (client a refusé)

CREE → EN_ATTENTE (AIS a accepté et envoyé email)
```

**Correspondance AIS → SAP-Facture** :
- AIS `EN_ATTENTE_VALIDATION` → SAP-Facture `EN_ATTENTE`
- AIS `VALIDEE` → SAP-Facture `VALIDEE`
- AIS `PAYEE` → SAP-Facture `PAYEE`
- AIS `REFUSEE` → SAP-Facture `REFUSEE`
- AIS `EXPIREE` → SAP-Facture `EXPIREE`

---

## 5. Cron Job — Synchronisation 4h

**Fréquence** : Toutes les 4 heures (9h, 13h, 17h, 21h)

**Étapes** :
1. Se connecter à AIS (login)
2. Scraper clients
3. Scraper factures/demandes
4. Écrire dans Sheets (batch)
5. Identifier alertes (relances T+36h, expirations T+48h)
6. Envoyer emails notifications si needed
7. Fermer browser

**Pseudo-code** :

```python
async def sync_ais(sheets_adapter: SheetsAdapter) -> None:
    """Sync AIS → Sheets complet"""
    adapter = AISAdapter(settings)
    try:
        await adapter.connect()

        # Clients
        clients = await adapter.scrape_clients()
        await sheets_adapter.write_clients_batch(clients)

        # Factures
        invoices = await adapter.scrape_invoices()
        await sheets_adapter.write_invoices_batch(invoices)

        # Alertes
        reminders = identify_reminders(invoices)
        for reminder in reminders:
            send_email_reminder(reminder)

        logger.info("AIS sync completed successfully")

    except Exception as e:
        logger.error("AIS sync failed", exc_info=True)
        # Notifier Jules d'une erreur sync
        send_email_error_notification()
        raise
    finally:
        await adapter.close()
```

---

## 6. Détection Alertes (Relances & Expirations)

### Relance T+36h

**But** : Envoyer email à Jules pour relancer client qui n'a pas validé.

**Logique** :
- Pour chaque facture EN_ATTENTE :
  - Calculer durée = now - date_creation
  - Si durée ∈ [36h, 48h[ → ajouter à liste "À relancer"
  - Envoyer email Jules : lien direct vers demande AIS

**Pseudo-code** :

```python
def identify_reminders(invoices: list[dict]) -> list[dict]:
    """Identifier factures à relancer (T+36h)"""
    reminders = []
    now = datetime.now()

    for inv in invoices:
        if inv["statut"] != "EN_ATTENTE":
            continue

        created_at = datetime.fromisoformat(inv["date_creation"])
        duration = now - created_at

        if timedelta(hours=36) < duration < timedelta(hours=48):
            reminders.append({
                "demande_id": inv["ais_demande_id"],
                "client_name": inv.get("client_name", "?"),
                "montant": inv["montant"],
                "ais_url": f"https://app.avance-immediate.fr/demande/{inv['ais_demande_id']}"
            })

    return reminders
```

### Expiration T+48h

**But** : Automatiser transition EXPIREE quand délai client dépasse 48h.

**Logique** :
- Pour chaque facture EN_ATTENTE :
  - Si durée > 48h → changer statut local à EXPIREE
  - Notifier Jules : "Facture X a expiré"

---

## 7. Intégration SheetsAdapter — Batch Writes

### Écriture Clients

```python
async def write_clients_batch(self, clients: list[dict]) -> None:
    """Écrire clients en batch (pas cellule par cellule)"""
    if not clients:
        return

    # Construire rows : [nom, prénom, email, statut_urssaf, ais_id]
    rows = [
        [
            c["nom"],
            c["prenom"],
            c["email"],
            c["statut_urssaf"],
            c["ais_id"],
        ]
        for c in clients
    ]

    # Écrire range entier (append mode)
    self.sheets.values().append(
        spreadsheetId=self.spreadsheet_id,
        range="Clients!A2",  # Commencer ligne 2 (headers en 1)
        valueInputOption="RAW",
        body={"values": rows}
    ).execute()

    logger.info("Clients batch written", extra={"count": len(rows)})
```

### Écriture Factures

```python
async def write_invoices_batch(self, invoices: list[dict]) -> None:
    """Écrire factures en batch"""
    if not invoices:
        return

    # Construire rows : [ais_demande_id, montant, statut, date_creation, reference_virement]
    rows = [
        [
            inv["ais_demande_id"],
            inv["montant"],
            inv["statut"],
            inv["date_creation"],
            inv["reference_virement"],
        ]
        for inv in invoices
    ]

    self.sheets.values().append(
        spreadsheetId=self.spreadsheet_id,
        range="Factures!A2",
        valueInputOption="RAW",
        body={"values": rows}
    ).execute()

    logger.info("Invoices batch written", extra={"count": len(rows)})
```

---

## 8. Gestion des Erreurs — Stratégie

| Catégorie | Cause | Action | Retry ? |
|-----------|-------|--------|---------|
| **Login échoué** | Credentials invalides, compte fermé | Log erreur, notify Jules | Oui, 3x |
| **Timeout navigation** | AIS lent ou down | Retry 3x backoff | Oui |
| **XPath/CSS cassé** | AIS a changé UI | Screenshot, log, notify Jules | Non (correction manuelle) |
| **Session expirée** | Cookies invalides | Re-login automatique | Oui, 1x |
| **Scraping incomplet** | Champ manquant en page | Screenshot, wait + retry | Oui |
| **Network error** | Connexion perdue | Retry 3x backoff | Oui |

### Retry avec Backoff Exponentiel

```python
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(3),
)
async def scrape_with_retry(self) -> list[dict]:
    """Scraper avec retry automatique"""
    try:
        return await self.scrape_invoices()
    except Exception as e:
        await self._screenshot_error("scrape-failed")
        raise
```

---

## 9. Logging — Règles RGPD

### BON ✓

```python
logger.info(
    "Factures scrapées",
    extra={
        "count": 5,
        "statuts": ["PAYEE", "EN_ATTENTE"],
    }
)

logger.error(
    "AIS login failed",
    extra={
        "email": "***",  # masquer
        "error": "Invalid credentials",
    }
)
```

### MAUVAIS ✗

```python
logger.error(f"Page content: {page.content()}")  # Peut contenir secrets
logger.error(f"Password: {ais_password}")  # JAMAIS
logger.info(f"Scraping {client_email}")  # Pas de données nominatives
```

---

## 10. Screenshots d'Erreur

- **OBLIGATOIRE** : chaque erreur non-retry → screenshot
- **Stockage** : `io/cache/ais-errors/` (local ou object storage)
- **Retention** : 7 jours, puis auto-supprimer
- **RGPD** : ne pas capturer données sensibles (redact si needed)

---

## 11. Testing

### Mocks Obligatoires

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from playwright.async_api import Page

@pytest.mark.asyncio
async def test_scrape_clients_success(mock_ais_page: Page):
    """Scraper clients avec succès"""
    mock_ais_page.goto = AsyncMock()
    mock_ais_page.wait_for_selector = AsyncMock()

    mock_rows = [MagicMock(), MagicMock()]
    mock_ais_page.query_selector_all.return_value = mock_rows

    for row in mock_rows:
        row.text_content = AsyncMock(
            side_effect=["Jules", "Willard", "j@example.com", "ACTIF", "AIS-123"]
        )

    adapter = AISAdapter(settings)
    adapter._page = mock_ais_page
    clients = await adapter.scrape_clients()

    assert len(clients) == 2
    assert clients[0]["email"] == "j@example.com"


@pytest.mark.asyncio
async def test_scrape_invoices_retry_on_timeout():
    """Retry 3x si timeout"""
    # Mock timeout then success
    adapter = AISAdapter(settings)
    adapter._page = MagicMock()
    adapter._page.goto.side_effect = [TimeoutError(), None]

    # Décorer avec @retry handling
    # ... test retry logic


@pytest.mark.asyncio
async def test_login_retry_on_invalid_credentials():
    """Login retente 3x si credentials invalides"""
    # ...
```

### Couverture Requise

- Login (succès, credentials invalides, session expirée, retry)
- Scrape clients (succès, tableau vide, timeout)
- Scrape invoices (succès, données partielles, network error)
- Retry logic (3 tentatives, backoff exponentiel, screenshot)
- Sheets integration (batch writes, no partial writes)
- Alert detection (relance T+36h, expiration T+48h)

**Minimum coverage** : 80% (`--cov-fail-under=80`)

---

## 12. Checklist Implémentation

- [ ] Classe `AISAdapter` avec Playwright
  - [ ] `connect()` et `_login()` avec retry 3x
  - [ ] `scrape_clients() -> list[dict]`
  - [ ] `scrape_invoices() -> list[dict]`
  - [ ] `close()`

- [ ] Browser management
  - [ ] Context persistent (cookies)
  - [ ] Screenshot d'erreur automatique
  - [ ] Timeout 30s par action
  - [ ] Re-login automatique si session expirée

- [ ] Intégration SheetsAdapter
  - [ ] `write_clients_batch(clients)`
  - [ ] `write_invoices_batch(invoices)`
  - [ ] Batch writes (pas cellule par cellule)
  - [ ] Pas de surcharge Sheets API

- [ ] Cron jobs (APScheduler ou Celery)
  - [ ] Sync 4h (9h, 13h, 17h, 21h)
  - [ ] Email reminder T+36h (Jules)
  - [ ] Auto-transition EXPIREE T+48h
  - [ ] Error notifications

- [ ] Tests (≥80% couverture)
  - [ ] Unit tests AISAdapter (mocks Playwright)
  - [ ] Integration tests avec Sheets
  - [ ] Retry + backoff logic
  - [ ] Fixtures : HTML snapshots pages AIS

- [ ] Sécurité
  - [ ] Secrets via `.env` (jamais en code)
  - [ ] Logs sans passwords/tokens
  - [ ] SSL validation on
  - [ ] Timeout obligatoire 30s
  - [ ] Screenshots RGPD-compliant

- [ ] Documentation
  - [ ] Docstrings (type hints, return types)
  - [ ] README intégration AIS
  - [ ] Exemples appels Playwright
  - [ ] Troubleshooting (UI changée, etc)

---

## 13. INTERDIT (Breaking Rules)

- ❌ **PAS d'appel API URSSAF direct** — c'est AIS qui le fait
- ❌ **PAS de création factures via Playwright** — AIS crée, on lit
- ❌ **PAS de modification données AIS** — lecture seule
- ❌ **Passwords en clair** — .env uniquement
- ❌ **Logging credentials/tokens** — masquer toujours
- ❌ **Pas de timeout** — 30s obligatoire
- ❌ **Pas de screenshot d'erreur** — mandatory pour debug
- ❌ **Scraping sans wait_for_selector** — timing obligatoire
