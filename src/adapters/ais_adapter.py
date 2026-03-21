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
        if not self._page:
            raise RuntimeError("Page non initialisée — appeler connect() d'abord")

        try:
            # Naviguer vers la page de login
            self._page.goto(f"{self.BASE_URL}/login", timeout=LOGIN_TIMEOUT)

            # Remplir les identifiants
            self._page.fill('input[name="email"]', self._settings.ais_email)
            self._page.fill('input[name="password"]', self._settings.ais_password)

            # Cliquer sur submit
            self._page.click('button[type="submit"]')

            # Attendre la redirection après login
            self._page.wait_for_url("**/dashboard**", timeout=LOGIN_TIMEOUT)

            logger.info("Login AIS réussi")
        except Exception:
            logger.warning("Tentative login AIS échouée", exc_info=True)
            raise

    def get_clients(self) -> list[dict[str, Any]]:
        """Récupère la liste des clients AIS via Playwright.

        Retourne une liste de dicts contenant : client_id, nom, prenom, email, statut_urssaf.
        Déduplique par client_id. Retourne [] si aucun client trouvé.
        """
        if not self._page:
            raise RuntimeError("Page non initialisée — appeler connect() d'abord")

        try:
            # Naviguer vers la page clients
            self._page.goto(f"{self.BASE_URL}/clients", timeout=NAVIGATION_TIMEOUT)
            self._page.wait_for_selector("table tbody tr", timeout=NAVIGATION_TIMEOUT)

            # Récupérer toutes les lignes du tableau
            rows = self._page.locator("table tbody tr").all()
            clients: list[dict[str, Any]] = []
            seen_ids: set[str] = set()

            for row in rows:
                # Récupérer les cellules de la ligne
                cells = row.locator("td").all()
                if len(cells) < 3:
                    continue

                # Extraire les données (par position dans le tableau)
                client_id_raw = cells[0].text_content()
                nom_raw = cells[1].text_content()
                prenom_raw = cells[2].text_content() if len(cells) > 2 else ""
                email_raw = cells[3].text_content() if len(cells) > 3 else ""
                statut_raw = cells[4].text_content() if len(cells) > 4 else ""

                # Nettoyer les valeurs
                client_id = client_id_raw.strip() if client_id_raw else ""
                nom = nom_raw.strip() if nom_raw else ""
                prenom = prenom_raw.strip() if prenom_raw else ""
                email = email_raw.strip() if email_raw else ""
                statut_urssaf = statut_raw.strip() if statut_raw else ""

                # Dédupliquer par client_id
                if client_id and client_id not in seen_ids:
                    seen_ids.add(client_id)
                    clients.append(
                        {
                            "client_id": client_id,
                            "nom": nom,
                            "prenom": prenom,
                            "email": email,
                            "statut_urssaf": statut_urssaf,
                        }
                    )

            logger.info("Clients AIS récupérés", extra={"count": len(clients)})
            return clients

        except Exception:
            self._screenshot_on_error("get_clients_failed")
            raise

    def get_invoices(self, status: str | None = None) -> list[dict[str, Any]]:
        """Récupère la liste des factures AIS, optionnellement filtrées par statut.

        Args:
            status: Statut optionnel à filtrer (ex: 'EN_ATTENTE', 'PAYEE')

        Returns:
            Liste de dicts contenant : demande_id, statut, montant, date, client_id
        """
        invoices = self.get_invoice_statuses()
        if status:
            invoices = [inv for inv in invoices if inv.get("statut") == status]
        return invoices

    def register_client(self, client_data: dict[str, Any]) -> str:
        """INTERDIT — AIS gère l'inscription clients, pas SAP-Facture."""
        raise NotImplementedError("INTERDIT — AIS gère l'inscription clients, pas SAP-Facture")

    def submit_invoice(self, client_id: str, invoice_data: dict[str, Any]) -> str:
        """INTERDIT — AIS gère la soumission factures, pas SAP-Facture."""
        raise NotImplementedError("INTERDIT — AIS gère la soumission factures, pas SAP-Facture")

    def get_invoice_statuses(self) -> list[dict[str, Any]]:
        """Scrape la page des demandes et retourne les statuts actuels.

        Retourne une liste de dicts avec : demande_id, statut, montant, date, client_id.
        Déduplique par demande_id. Retourne [] si page vide ou erreur navigation.
        """
        if not self._page:
            raise RuntimeError("Page non initialisée — appeler connect() d'abord")

        try:
            # Naviguer vers la page des demandes
            self._page.goto(f"{self.BASE_URL}/demandes", timeout=NAVIGATION_TIMEOUT)
            self._page.wait_for_selector("table tbody tr", timeout=NAVIGATION_TIMEOUT)

            # Récupérer toutes les lignes du tableau
            rows = self._page.locator("table tbody tr").all()
            invoices: list[dict[str, Any]] = []
            seen_ids: set[str] = set()

            for row in rows:
                # Récupérer les cellules de la ligne
                cells = row.locator("td").all()
                if len(cells) < 3:
                    continue

                # Extraire les données (par position)
                demande_id_raw = cells[0].text_content()
                statut_raw = cells[1].text_content() if len(cells) > 1 else ""
                client_raw = cells[2].text_content() if len(cells) > 2 else ""
                montant_raw = cells[3].text_content() if len(cells) > 3 else ""
                date_raw = cells[4].text_content() if len(cells) > 4 else ""

                # Nettoyer les valeurs
                demande_id = demande_id_raw.strip() if demande_id_raw else ""
                statut = statut_raw.strip() if statut_raw else ""
                client_id = client_raw.strip() if client_raw else ""
                montant = montant_raw.strip() if montant_raw else ""
                date = date_raw.strip() if date_raw else ""

                # Dédupliquer par demande_id
                if demande_id and demande_id not in seen_ids:
                    seen_ids.add(demande_id)
                    invoices.append(
                        {
                            "demande_id": demande_id,
                            "statut": statut,
                            "client_id": client_id,
                            "montant": montant,
                            "date": date,
                        }
                    )

            logger.info(
                "Statuts AIS récupérés",
                extra={"count": len(invoices)},
            )
            return invoices

        except Exception:
            self._screenshot_on_error("get_invoice_statuses_failed")
            raise

    def get_invoice_status(self, demande_id: str) -> str:
        """Retourne le statut d'une demande spécifique.

        Args:
            demande_id: ID de la demande à chercher

        Returns:
            Statut de la demande (ex: 'EN_ATTENTE', 'PAYEE', etc.)

        Raises:
            ValueError: Si demande_id non trouvée
        """
        invoices = self.get_invoice_statuses()
        for inv in invoices:
            if inv.get("demande_id") == demande_id:
                return inv.get("statut", "INCONNU")
        raise ValueError(f"Demande {demande_id} non trouvée")

    def get_pending_reminders(self, hours_threshold: int = 36) -> list[dict[str, Any]]:
        """Identifie les demandes EN_ATTENTE depuis plus de N heures.

        Args:
            hours_threshold: Nombre d'heures (défaut 36) à partir duquel une relance est due

        Returns:
            Liste de dicts (demandes en attente) avec champ supplémentaire 'hours_waiting'
        """
        from datetime import UTC, datetime

        invoices = self.get_invoice_statuses()
        reminders: list[dict[str, Any]] = []
        now = datetime.now(UTC)

        for inv in invoices:
            if inv.get("statut") != "EN_ATTENTE":
                continue

            date_str = inv.get("date", "")
            if not date_str:
                continue

            try:
                # Parser la date ISO
                created = datetime.fromisoformat(date_str)
                if created.tzinfo is None:
                    created = created.replace(tzinfo=UTC)

                age = now - created
                age_hours = age.total_seconds() / 3600

                if age_hours > hours_threshold:
                    inv_copy = inv.copy()
                    inv_copy["hours_waiting"] = age_hours
                    reminders.append(inv_copy)

            except (ValueError, TypeError):
                logger.warning(
                    "Impossible parser date demande",
                    extra={"demande_id": inv.get("demande_id"), "date": date_str},
                )
                continue

        logger.info(
            "Relances AIS",
            extra={"count": len(reminders), "threshold": hours_threshold},
        )
        return reminders

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

    def __enter__(self) -> AISAdapter:
        """Entre le context manager — appelle connect()."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Sort le context manager — appelle close()."""
        self.close()

    def _screenshot_on_error(self, name: str) -> None:
        """Screenshot RGPD-safe en cas d'erreur."""
        if self._page:
            path = Path("io/cache") / f"error_ais_{name}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            self._page.screenshot(path=str(path))
            logger.warning("Screenshot erreur AIS: %s", path)
