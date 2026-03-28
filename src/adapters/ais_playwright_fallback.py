"""AIS Playwright fallback adapter — kicks in when REST API is down.

Uses async Playwright (headless Chromium) to scrape AIS UI.
Read-only: NEVER writes to AIS. Same interface as AISAPIAdapter.

Refs: MPP-48, CDC §3, D1
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from playwright.async_api import async_playwright

if TYPE_CHECKING:
    from playwright.async_api import Browser, Page

    from src.config import Settings

logger = logging.getLogger(__name__)

AIS_BASE_URL = "https://app.avance-immediate.fr"

SCREENSHOT_DIR = Path("io/cache")

# JavaScript to extract table rows as list of dicts from a standard HTML table.
# Each <th> becomes a dict key, each <td> the corresponding value.
_JS_EXTRACT_TABLE = """
() => {
    const table = document.querySelector('table');
    if (!table) return [];
    const headers = [...table.querySelectorAll('thead th')].map(th => th.textContent.trim());
    const rows = [...table.querySelectorAll('tbody tr')];
    return rows.map(row => {
        const cells = [...row.querySelectorAll('td')];
        const obj = {};
        headers.forEach((h, i) => { obj[h] = cells[i] ? cells[i].textContent.trim() : ''; });
        return obj;
    });
}
"""


class AISSelectors:
    """CSS selectors for AIS UI elements."""

    # Login form
    LOGIN_EMAIL = "input[name='email']"
    LOGIN_PASSWORD = "input[name='password']"
    LOGIN_SUBMIT = "button[type='submit']"

    # Navigation
    NAV_CLIENTS = "a[href*='clients'], nav a:has-text('Mes clients')"
    NAV_DEMANDES = "a[href*='demandes'], nav a:has-text('Mes demandes')"

    # Tables
    TABLE_ROWS = "table tbody tr"
    TABLE_HEADER = "table thead th"


class AISPlaywrightFallback:
    """Playwright fallback for AIS when REST API is unavailable.

    Implements the same public interface as AISAPIAdapter (read-only).
    Uses headless Chromium to scrape the AIS web UI.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._browser: Browser | None = None
        self._page: Page | None = None
        self._playwright_ctx: Any = None

    async def connect(self) -> None:
        """Launch headless Chromium, navigate to AIS, and login via form.

        Raises:
            RuntimeError: If login fails.
        """
        pw_ctx = async_playwright()
        self._playwright_ctx = await pw_ctx.__aenter__()
        self._browser = await self._playwright_ctx.chromium.launch(headless=True)
        context = await self._browser.new_context()
        self._page = await context.new_page()

        try:
            await self._page.goto(AIS_BASE_URL, timeout=30000)
            await self._page.fill(AISSelectors.LOGIN_EMAIL, self._settings.ais_email)
            await self._page.fill(AISSelectors.LOGIN_PASSWORD, self._settings.ais_password)
            await self._page.click(AISSelectors.LOGIN_SUBMIT)
            await self._page.wait_for_selector("table", timeout=15000)
            logger.info("AIS Playwright login successful")
        except Exception:
            await self._screenshot_on_error("login_failed")
            logger.error("AIS Playwright login failed")
            raise RuntimeError("AIS Playwright login failed") from None

    async def get_clients(self) -> list[dict[str, Any]]:
        """Scrape clients from the AIS clients page.

        Returns:
            List of client dicts with keys: client_id, nom, prenom, email, statut_urssaf.
            Deduplicated by client_id.
        """
        self._require_page()
        assert self._page is not None

        try:
            await self._page.click(AISSelectors.NAV_CLIENTS)
            await self._page.wait_for_selector(AISSelectors.TABLE_ROWS, timeout=10000)
        except Exception:
            await self._screenshot_on_error("nav_clients")
            logger.warning("AIS Playwright: failed navigating to clients page")

        raw_rows: list[dict[str, Any]] = await self._page.evaluate(_JS_EXTRACT_TABLE)

        clients: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for row in raw_rows:
            client_id = row.get("client_id", "")
            if not client_id or client_id in seen_ids:
                continue
            seen_ids.add(client_id)
            clients.append(row)

        logger.info("AIS Playwright clients scraped", extra={"count": len(clients)})
        return clients

    async def get_invoices(self, status: str | None = None) -> list[dict[str, Any]]:
        """Scrape invoices, optionally filtered by status.

        Args:
            status: Optional status to filter (e.g. 'EN_ATTENTE', 'PAYEE').

        Returns:
            List of invoice dicts.
        """
        invoices = await self.get_invoice_statuses()
        if status:
            invoices = [inv for inv in invoices if inv.get("statut") == status]
        return invoices

    async def get_invoice_statuses(self) -> list[dict[str, Any]]:
        """Scrape all invoice statuses from the AIS demandes page.

        Returns:
            List of dicts with keys: demande_id, statut, client_id, montant, date.
            Deduplicated by demande_id.
        """
        self._require_page()
        assert self._page is not None

        try:
            await self._page.click(AISSelectors.NAV_DEMANDES)
            await self._page.wait_for_selector(AISSelectors.TABLE_ROWS, timeout=10000)
        except Exception:
            await self._screenshot_on_error("nav_demandes")
            logger.warning("AIS Playwright: failed navigating to demandes page")

        raw_rows: list[dict[str, Any]] = await self._page.evaluate(_JS_EXTRACT_TABLE)

        invoices: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for row in raw_rows:
            demande_id = row.get("demande_id", "")
            if not demande_id or demande_id in seen_ids:
                continue
            seen_ids.add(demande_id)
            invoices.append(row)

        logger.info(
            "AIS Playwright invoice statuses scraped",
            extra={"count": len(invoices)},
        )
        return invoices

    async def get_invoice_status(self, demande_id: str) -> str:
        """Return the status string for a single invoice.

        Args:
            demande_id: The invoice demand ID.

        Returns:
            Status string (e.g. 'EN_ATTENTE', 'PAYEE').

        Raises:
            ValueError: If demande_id not found.
        """
        invoices = await self.get_invoice_statuses()
        for inv in invoices:
            if inv.get("demande_id") == demande_id:
                return str(inv.get("statut", "INCONNU"))
        raise ValueError(f"Demande {demande_id} non trouvée")

    async def get_pending_reminders(self, hours_threshold: int = 36) -> list[dict[str, Any]]:
        """Identify EN_ATTENTE invoices older than threshold.

        Args:
            hours_threshold: Hours since creation (default 36).

        Returns:
            List of invoice dicts with added 'hours_waiting' field.
        """
        invoices = await self.get_invoice_statuses()
        reminders: list[dict[str, Any]] = []
        now = datetime.now(UTC)

        for inv in invoices:
            if inv.get("statut") != "EN_ATTENTE":
                continue

            date_str = inv.get("date", "")
            if not date_str:
                continue

            try:
                created = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                if created.tzinfo is None:
                    created = created.replace(tzinfo=UTC)

                age_hours = (now - created).total_seconds() / 3600

                if age_hours > hours_threshold:
                    inv_copy = dict(inv)
                    inv_copy["hours_waiting"] = age_hours
                    reminders.append(inv_copy)
            except (ValueError, TypeError):
                logger.warning(
                    "AIS Playwright: unparseable date",
                    extra={"demande_id": inv.get("demande_id"), "date": date_str},
                )

        logger.info(
            "AIS Playwright pending reminders",
            extra={"count": len(reminders), "threshold": hours_threshold},
        )
        return reminders

    def register_client(self, client_data: dict[str, Any]) -> str:
        """INTERDIT -- AIS gere l'inscription clients, pas SAP-Facture."""
        raise NotImplementedError("INTERDIT -- AIS gere l'inscription clients, pas SAP-Facture")

    def submit_invoice(self, client_id: str, invoice_data: dict[str, Any]) -> str:
        """INTERDIT -- AIS gere la soumission factures, pas SAP-Facture."""
        raise NotImplementedError("INTERDIT -- AIS gere la soumission factures, pas SAP-Facture")

    async def close(self) -> None:
        """Close browser and clean up Playwright resources."""
        if self._browser:
            await self._browser.close()
        self._browser = None
        self._page = None
        if self._playwright_ctx:
            # The context manager exit is handled by _playwright_ctx
            self._playwright_ctx = None
        logger.info("AIS Playwright closed")

    async def _screenshot_on_error(self, context_label: str) -> None:
        """Capture a screenshot on error. No sensitive data in filename.

        Args:
            context_label: Short label describing the error context.
        """
        if not self._page:
            return

        try:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            filename = f"ais_error_{context_label}_{timestamp}.png"
            filepath = SCREENSHOT_DIR / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            await self._page.screenshot(path=str(filepath))
            logger.info(
                "AIS error screenshot saved",
                extra={"path": str(filepath)},
            )
        except Exception:
            logger.warning(
                "Failed to save AIS error screenshot",
                extra={"context": context_label},
            )

    def _require_page(self) -> None:
        """Raise RuntimeError if page is not initialized."""
        if self._page is None:
            raise RuntimeError("Page non initialisee -- appeler connect() d'abord")


class AISAdapterWithFallback:
    """Facade: tries REST first, falls back to Playwright on failure.

    This adapter wraps AISAPIAdapter (sync REST) and AISPlaywrightFallback
    (async Playwright). REST is always tried first. If REST raises any
    exception, the Playwright fallback is connected lazily and used instead.
    """

    def __init__(self, settings: Settings) -> None:
        from src.adapters.ais_adapter import AISAPIAdapter

        self._settings = settings
        self._rest = AISAPIAdapter(settings)
        self._playwright = AISPlaywrightFallback(settings)

    async def connect(self) -> None:
        """Connect the REST adapter. Playwright connects lazily on fallback."""
        self._rest.connect()

    async def close(self) -> None:
        """Close both adapters."""
        self._rest.close()
        await self._playwright.close()

    async def get_clients(self) -> list[dict[str, Any]]:
        """Get clients via REST, fall back to Playwright."""
        return await self._try_rest_then_playwright(
            rest_fn=self._rest.get_clients,
            pw_fn=self._playwright.get_clients,
        )

    async def get_invoices(self, status: str | None = None) -> list[dict[str, Any]]:
        """Get invoices via REST, fall back to Playwright."""
        return await self._try_rest_then_playwright(
            rest_fn=lambda: self._rest.get_invoices(status=status),
            pw_fn=lambda: self._playwright.get_invoices(status=status),
        )

    async def get_invoice_statuses(self) -> list[dict[str, Any]]:
        """Get invoice statuses via REST, fall back to Playwright."""
        return await self._try_rest_then_playwright(
            rest_fn=self._rest.get_invoice_statuses,
            pw_fn=self._playwright.get_invoice_statuses,
        )

    async def get_invoice_status(self, demande_id: str) -> str:
        """Get single invoice status via REST, fall back to Playwright."""
        return await self._try_rest_then_playwright(
            rest_fn=lambda: self._rest.get_invoice_status(demande_id),
            pw_fn=lambda: self._playwright.get_invoice_status(demande_id),
        )

    async def get_pending_reminders(self, hours_threshold: int = 36) -> list[dict[str, Any]]:
        """Get pending reminders via REST, fall back to Playwright."""
        return await self._try_rest_then_playwright(
            rest_fn=lambda: self._rest.get_pending_reminders(hours_threshold),
            pw_fn=lambda: self._playwright.get_pending_reminders(hours_threshold),
        )

    async def _try_rest_then_playwright(
        self,
        rest_fn: Any,
        pw_fn: Any,
    ) -> Any:
        """Execute rest_fn; on failure, connect Playwright and execute pw_fn.

        Args:
            rest_fn: Sync callable (REST adapter method).
            pw_fn: Async callable (Playwright fallback method).

        Returns:
            Result from whichever adapter succeeds.

        Raises:
            Exception: If both adapters fail, re-raises the Playwright error.
        """
        try:
            return rest_fn()
        except Exception as rest_err:
            logger.warning(
                "AIS REST failed, falling back to Playwright",
                extra={"error": str(rest_err)},
            )

        # Lazy connect for Playwright
        if self._playwright._page is None:
            await self._playwright.connect()

        return await pw_fn()
