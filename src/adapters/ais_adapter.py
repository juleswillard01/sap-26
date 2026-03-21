"""Adapter Playwright pour AIS (app.avance-immediate.fr) — CDC §3."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)

LOGIN_TIMEOUT = 30_000
NAVIGATION_TIMEOUT = 20_000


class AISAdapter:
    """Automatise le compte AIS de Jules via Playwright headless.

    AIS (Avance Immédiate Services) gère l'avance immédiate URSSAF.
    Jules utilise AIS (~99€/an). Ce adapter automatise SON compte.
    """

    BASE_URL = "https://app.avance-immediate.fr"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._playwright_instance: Any = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    def connect(self) -> None:
        """Lance le navigateur headless et se connecte à AIS."""
        self._playwright_instance = sync_playwright().start()
        self._browser = self._playwright_instance.chromium.launch(headless=True)
        if self._browser is None:
            raise RuntimeError("Failed to launch browser")
        self._context = self._browser.new_context(accept_downloads=True)
        self._page = self._context.new_page()
        self._page.set_default_timeout(NAVIGATION_TIMEOUT)
        self._login()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=30))
    def _login(self) -> None:
        """Authentification sur AIS avec retry 3x backoff."""
        raise NotImplementedError("À implémenter — login AIS Playwright")

    def get_clients(self) -> list[dict[str, Any]]:
        """Récupère la liste des clients AIS."""
        raise NotImplementedError("À implémenter — clients AIS")

    def get_invoices(self, status: str | None = None) -> list[dict[str, Any]]:
        """Récupère la liste des factures AIS."""
        raise NotImplementedError("À implémenter — factures AIS")

    def register_client(self, client_data: dict[str, Any]) -> str:
        """Inscrit un client via le formulaire AIS. Retourne l'ID URSSAF."""
        raise NotImplementedError("À implémenter — inscription client AIS")

    def submit_invoice(self, client_id: str, invoice_data: dict[str, Any]) -> str:
        """Soumet une demande de paiement via AIS. Retourne l'ID demande."""
        raise NotImplementedError("À implémenter — soumission facture AIS")

    def get_invoice_statuses(self) -> list[dict[str, Any]]:
        """Scrape la page des demandes et retourne les statuts actuels."""
        raise NotImplementedError("À implémenter — polling statuts AIS")

    def get_invoice_status(self, demande_id: str) -> str:
        """Retourne le statut d'une demande spécifique."""
        raise NotImplementedError("À implémenter — statut spécifique AIS")

    def get_pending_reminders(self, hours_threshold: int = 36) -> list[dict[str, Any]]:
        """Identifie les demandes en attente depuis plus de N heures."""
        raise NotImplementedError("À implémenter — relances AIS")

    def close(self) -> None:
        """Ferme le navigateur."""
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright_instance:
            self._playwright_instance.stop()
        self._browser = None
        self._context = None
        self._page = None

    def _screenshot_on_error(self, name: str) -> None:
        """Screenshot RGPD-safe en cas d'erreur."""
        if self._page:
            path = Path("io/cache") / f"error_ais_{name}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            self._page.screenshot(path=str(path))
            logger.warning("Screenshot erreur AIS: %s", path)
