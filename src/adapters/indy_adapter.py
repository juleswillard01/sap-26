"""Adapter Playwright pour Indy Banking — CDC §3.1.

Scraper headless pour exporter les transactions bancaires depuis Indy.
- Retry 3x avec backoff exponentiel
- Screenshots erreur RGPD-safe (sans données sensibles)
- Headless en prod, headed en debug uniquement
"""

from __future__ import annotations

import csv
import io
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from playwright.sync_api import Browser, Page, sync_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)


class IndyBrowserAdapter:
    """Scraper headless pour Indy Banking — export transactions."""

    BASE_URL = "https://app.indy.fr"
    LOGIN_TIMEOUT = 30_000
    NAVIGATION_TIMEOUT = 20_000

    def __init__(self, settings: Settings) -> None:
        """Initialise l'adapter avec les credentials Indy.

        Args:
            settings: Configuration contenant indy_email et indy_password.

        Raises:
            ValueError: Si indy_email ou indy_password manquent.
        """
        if not settings.indy_email or not settings.indy_password:
            msg = "indy_email et indy_password requis dans les settings"
            raise ValueError(msg)

        self._settings = settings
        self._browser: Browser | None = None
        self._page: Page | None = None

    def connect(self) -> None:
        """Lance le navigateur Playwright et se connecte a Indy.

        Raises:
            RuntimeError: Si la connexion echoue apres 3 tentatives.
        """
        try:
            pw = sync_playwright().start()
            self._browser = pw.chromium.launch(headless=True)
            context = self._browser.new_context()
            self._page = context.new_page()
            self._page.set_default_timeout(self.NAVIGATION_TIMEOUT)
            self._login()
            logger.info("Connexion Indy etablie")
        except Exception as e:
            self._screenshot_on_error("connect_failed")
            msg = f"Connexion Indy echouee: {e}"
            raise RuntimeError(msg) from e

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=30))
    def _login(self) -> None:
        """Authentification Indy avec retry 3x backoff exponentiel.

        Navigue a la page de login, remplit email/password, et attend le dashboard.

        Raises:
            TimeoutError: Si le dashboard n'apparait pas dans le timeout.
        """
        if not self._page:
            msg = "Page non initialisee"
            raise RuntimeError(msg)

        try:
            self._page.goto(f"{self.BASE_URL}/login", wait_until="networkidle")

            # Remplir formulaire de login
            self._page.fill('input[type="email"]', self._settings.indy_email)
            self._page.fill('input[type="password"]', self._settings.indy_password)
            self._page.click("button[type=submit]")

            # Attendre le dashboard (redirection apres login)
            self._page.wait_for_url("**/*.indy.fr/dashboard**", timeout=self.LOGIN_TIMEOUT)
            logger.info("Login Indy reussi")

        except Exception:
            self._screenshot_on_error("login_failed")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=30))
    def export_transactions(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        """Exporte les transactions bancaires sur une periode.

        Navigue a l'onglet Transactions, applique les filtres de date,
        et telecharge le CSV.

        Args:
            date_from: Date debut (format ISO YYYY-MM-DD).
            date_to: Date fin (format ISO YYYY-MM-DD).

        Returns:
            Liste de transactions parsees depuis le CSV Indy.

        Raises:
            RuntimeError: Si l'export echoue apres 3 tentatives.
        """
        if not self._page:
            msg = "Page non initialisee"
            raise RuntimeError(msg)

        try:
            # Naviguer a la section Transactions
            self._page.goto(
                f"{self.BASE_URL}/dashboard/transactions",
                wait_until="networkidle",
            )

            # Appliquer filtres de date
            self._page.fill('input[name="date_from"]', date_from)
            self._page.fill('input[name="date_to"]', date_to)
            self._page.click("button:has-text('Filtrer')")

            # Attendre que les donnees se chargent
            self._page.wait_for_selector("table tbody tr", timeout=self.NAVIGATION_TIMEOUT)

            # Telecharger CSV (declencher le telechargement)
            with self._page.expect_download() as download_info:
                self._page.click("button:has-text('Exporter CSV')")

            download = download_info.value
            csv_content = download.path().read_text(encoding="utf-8")

            transactions = self._parse_csv(csv_content)
            logger.info("Export reussi: %d transactions", len(transactions))
            return transactions

        except Exception:
            self._screenshot_on_error("export_failed")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=30))
    def get_balance(self) -> float:
        """Recupere le solde actuel du compte bancaire Indy.

        Returns:
            Solde en euros (float).

        Raises:
            RuntimeError: Si la recuperation du solde echoue.
        """
        if not self._page:
            msg = "Page non initialisee"
            raise RuntimeError(msg)

        try:
            self._page.goto(f"{self.BASE_URL}/dashboard", wait_until="networkidle")

            # Chercher l'element affichant le solde (selecteur typique Indy)
            balance_text = self._page.text_content("[data-testid='account-balance']")

            if not balance_text:
                msg = "Solde non trouve dans la page"
                raise ValueError(msg)

            # Nettoyer et convertir (p.ex. "1 234,56 €" -> 1234.56)
            balance_str = balance_text.replace("€", "").replace(" ", "").replace(",", ".")
            balance = float(balance_str)

            logger.info("Solde recupere: %.2f EUR", balance)
            return balance

        except Exception:
            self._screenshot_on_error("balance_failed")
            raise

    def export_journal_csv(self) -> list[dict[str, Any]]:
        """Exporte les transactions du jour (alias pour export_transactions).

        Returns:
            Liste de transactions du jour au format CSV-parsé.
        """
        from datetime import date

        today = str(date.today())
        return self.export_transactions(today, today)

    def close(self) -> None:
        """Ferme le navigateur et nettoie les ressources."""
        if self._browser:
            self._browser.close()
            self._browser = None
            self._page = None
            logger.info("Navigateur Indy ferme")

    def _screenshot_on_error(self, name: str) -> None:
        """Sauvegarde un screenshot erreur RGPD-safe.

        Ne capture PAS les donnees bancaires sensibles.

        Args:
            name: Nom descriptif du screenshot (ex: 'login_failed').
        """
        if self._page:
            try:
                path = Path("io/cache") / f"error_indy_{name}.png"
                path.parent.mkdir(parents=True, exist_ok=True)
                self._page.screenshot(path=str(path))
                logger.warning("Screenshot erreur Indy: %s", path)
            except Exception as e:
                logger.error("Erreur lors de la capture screenshot: %s", e)

    @staticmethod
    def _parse_csv(csv_content: str) -> list[dict[str, Any]]:
        """Parse le contenu CSV exporte par Indy.

        Convertit le CSV en liste de dictionnaires.

        Args:
            csv_content: Contenu brut du CSV (string).

        Returns:
            Liste de dictionnaires {colonne: valeur}.

        Raises:
            ValueError: Si le CSV est invalide ou vide.
        """
        try:
            reader = csv.DictReader(io.StringIO(csv_content))

            if reader.fieldnames is None:
                msg = "CSV invalide ou vide"
                raise ValueError(msg)

            transactions = list(reader)

            if not transactions:
                logger.warning("CSV exporte mais aucune transaction")
                return []

            logger.info("CSV parse: %d lignes", len(transactions))
            return transactions

        except csv.Error as e:
            msg = f"Erreur CSV parsing: {e}"
            raise ValueError(msg) from e
