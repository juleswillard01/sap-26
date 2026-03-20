"""Adapter Indy Banking via Playwright — CDC §5.1.

ATTENTION : Playwright = fragile.
- Toujours avec retry (3 tentatives, backoff exponentiel)
- Screenshots d'erreur pour debug (SANS données bancaires sensibles)
- Headless en prod, headed en debug uniquement
- Credentials via variables d'environnement JAMAIS dans le code
"""


class IndyBrowserAdapter:
    """Adapter pour Indy Banking via Playwright scraping."""

    def __init__(self, email: str, password: str) -> None:
        """Initialise l'adapter Indy."""
        self._email = email
        self._password = password

    async def export_transactions_csv(self) -> str:
        """Exporte les transactions en CSV depuis Indy.

        Returns:
            Contenu CSV des transactions.
        """
        raise NotImplementedError("À implémenter — CDC §5.1")
