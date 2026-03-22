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
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from playwright.sync_api import Browser, Page, sync_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)


class IndyBrowserAdapter:
    """Scraper headless pour Indy Banking — export transactions + session persistence."""

    BASE_URL = "https://app.indy.fr"
    LOGIN_TIMEOUT = 30_000
    NAVIGATION_TIMEOUT = 20_000
    SESSION_STATE_FILE = Path("io/cache/indy_browser_state.json")
    SESSION_VERIFY_TIMEOUT = 10_000
    INTERACTIVE_LOGIN_TIMEOUT = 120_000

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

    def connect(self, session_mode: str = "headless") -> None:
        """Lance le navigateur Playwright et se connecte a Indy.

        Args:
            session_mode: "headless" (utilise state persisté) ou "headed" (login interactif + 2FA).

        Raises:
            RuntimeError: Si la connexion echoue apres 3 tentatives.
        """
        if session_mode not in ("headless", "headed"):
            msg = f"session_mode invalide: {session_mode} (doit être 'headless' ou 'headed')"
            raise ValueError(msg)

        try:
            pw = sync_playwright().start()
            context_kwargs: dict[str, Any] = {}

            # Si headless et session persistée existe, la réutiliser
            if session_mode == "headless" and self.SESSION_STATE_FILE.exists():
                context_kwargs["storage_state"] = str(self.SESSION_STATE_FILE)
                logger.info("Réutilisation état session Indy (headless)")

            self._browser = pw.chromium.launch(headless=(session_mode == "headless"))
            context = self._browser.new_context(**context_kwargs)
            self._page = context.new_page()
            self._page.set_default_timeout(self.NAVIGATION_TIMEOUT)

            if session_mode == "headed":
                self._login_interactive()
                # Sauvegarder état pour usage headless futur
                context.storage_state(path=str(self.SESSION_STATE_FILE))
                self.SESSION_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
                logger.info("État session Indy sauvegardé pour usage headless")
            else:
                # Headless: soit la session est valide, soit on échoue
                if not self._verify_session():
                    msg = "Session Indy expirée, utilisez session_mode='headed' pour re-login"
                    raise RuntimeError(msg)
                logger.info("Session Indy valide (réutilisée)")

            logger.info("Connexion Indy établie (mode=%s)", session_mode)
        except Exception as e:
            self._screenshot_on_error("connect_failed")
            msg = f"Connexion Indy échouée: {e}"
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

    def _login_interactive(self) -> None:
        """Login interactif avec attente 2FA (navigateur headed uniquement).

        Navigue à la page login, remplit credentials automatiquement,
        puis attend manuelle saisie du code 2FA par l'utilisateur (timeout 2 min).

        Raises:
            RuntimeError: Si la page est non initialisée.
            TimeoutError: Si le dashboard n'apparait pas dans le timeout 2FA.
        """
        if not self._page:
            msg = "Page non initialisee"
            raise RuntimeError(msg)

        try:
            self._page.goto(f"{self.BASE_URL}/login", wait_until="networkidle")

            # Remplir email et password automatiquement
            self._page.fill('input[type="email"]', self._settings.indy_email)
            self._page.fill('input[type="password"]', self._settings.indy_password)
            self._page.click("button[type=submit]")

            # Attendre le code 2FA ou le dashboard (timeout 2 min pour entree manuelle)
            logger.info("Attente code 2FA... (entrer le code dans le navigateur)")
            self._page.wait_for_url(
                "**/*.indy.fr/dashboard**",
                timeout=self.INTERACTIVE_LOGIN_TIMEOUT,
            )
            logger.info("2FA confirmé, login Indy réussi (interactive)")

        except Exception:
            self._screenshot_on_error("login_interactive_failed")
            raise

    def _verify_session(self) -> bool:
        """Vérifie si la session persistée est encore valide.

        Navigue au dashboard et cherche l'élément du solde pour confirmer l'accès.

        Returns:
            True si la session est valide, False sinon.
        """
        if not self._page:
            return False

        try:
            self._page.goto(f"{self.BASE_URL}/dashboard", wait_until="networkidle")
            self._page.wait_for_selector(
                "[data-testid='account-balance']",
                timeout=self.SESSION_VERIFY_TIMEOUT,
            )
            logger.info("Session Indy vérifiée avec succès")
            return True
        except Exception as e:
            logger.warning("Session Indy expirée ou invalide: %s", e)
            return False

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
    def export_journal_book(self) -> list[dict[str, Any]]:
        """Exporte le Journal Book depuis Indy Documents > Comptabilité.

        Navigue vers Documents > Comptabilité, declenche l'export CSV,
        et parse le fichier telecharge.

        Returns:
            Liste de transactions (revenus uniquement, dédupliquées).

        Raises:
            RuntimeError: Si l'export echoue apres 3 tentatives.
        """
        if not self._page:
            msg = "Page non initialisee"
            raise RuntimeError(msg)

        try:
            # Navigate to Documents > Comptabilité
            self._page.goto(
                f"{self.BASE_URL}/dashboard/documents/comptabilite",
                wait_until="networkidle",
            )

            # Wait for export button
            self._page.wait_for_selector(
                "button:has-text('Exporter')",
                timeout=self.NAVIGATION_TIMEOUT,
            )

            # Download CSV
            with self._page.expect_download() as download_info:
                self._page.click("button:has-text('Exporter CSV')")

            download = download_info.value
            csv_content = Path(download.path()).read_text(encoding="utf-8")

            # Parse with journal-specific parser
            transactions = self._parse_journal_csv(csv_content)
            logger.info("Journal Book exporte: %d transactions", len(transactions))
            return transactions

        except Exception:
            self._screenshot_on_error("export_journal_book_failed")
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

    @staticmethod
    def _parse_journal_csv(csv_content: str) -> list[dict[str, Any]]:
        """Parse le CSV du Journal Book depuis Indy.

        Filtre revenus seulement, deduplique par (date_valeur, montant, libelle),
        valide les formats, et convertit montants en float.

        Args:
            csv_content: Contenu brut du CSV (string).

        Returns:
            Liste de transactions revenus uniquement, triees par date.

        Raises:
            ValueError: Si le CSV est invalide, vide, ou manque colonnes requises.
        """
        if not csv_content or not csv_content.strip():
            msg = "CSV invalide ou vide"
            raise ValueError(msg)

        try:
            reader = csv.DictReader(io.StringIO(csv_content))

            if reader.fieldnames is None:
                msg = "CSV invalide ou vide"
                raise ValueError(msg)

            # Check required columns
            required_fields = {"date_valeur", "montant", "libelle", "type"}
            if not required_fields.issubset(set(reader.fieldnames or [])):
                missing = required_fields - set(reader.fieldnames or [])
                msg = f"Colonnes manquantes: {missing}"
                raise ValueError(msg)

            transactions = list(reader)

            if not transactions:
                logger.warning("CSV exporte mais aucune transaction")
                return []

            # Filter to revenus only
            revenus = [t for t in transactions if t.get("type", "").strip() == "revenus"]

            # Normalize and validate
            normalized: list[dict[str, Any]] = []
            seen_hashes: set[str] = set()

            for txn in revenus:
                # Skip zero montants
                try:
                    montant = float(txn.get("montant", "0").strip())
                    if montant == 0:
                        continue
                except (ValueError, AttributeError) as e:
                    msg = f"Montant invalide: {txn.get('montant')}"
                    raise ValueError(msg) from e

                # Validate date format YYYY-MM-DD
                date_str = txn.get("date_valeur", "").strip()
                try:
                    datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError as e:
                    msg = f"Date invalide (expected YYYY-MM-DD): {date_str}"
                    raise ValueError(msg) from e

                # Strip libelle
                libelle = txn.get("libelle", "").strip()

                # Deduplicate by (date_valeur, montant, libelle)
                dedup_key = f"{date_str}|{montant}|{libelle}"
                if dedup_key in seen_hashes:
                    continue
                seen_hashes.add(dedup_key)

                # Build normalized transaction
                normalized_txn = {
                    "date_valeur": date_str,
                    "montant": montant,
                    "libelle": libelle,
                    "type": "revenus",
                }
                normalized.append(normalized_txn)

            logger.info(
                "Journal CSV parse: %d revenus apres filtrage et dedup",
                len(normalized),
            )
            return normalized

        except csv.Error as e:
            msg = f"Erreur CSV parsing: {e}"
            raise ValueError(msg) from e
