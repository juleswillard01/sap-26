"""Adapter Google Sheets via gspread — CDC §7.

IMPORTANT : Google Sheets est le backend data. Traiter comme un ORM.
- Batch reads : worksheet.get_all_records()
- Batch writes : worksheet.update() avec range
- JAMAIS cellule par cellule (worksheet.update_cell en boucle)
- Rate limit : 60 req/min/user → throttle intégré
"""


class SheetsAdapter:
    """Adapter pour Google Sheets API v4 via gspread."""

    def __init__(self, spreadsheet_id: str, credentials_path: str) -> None:
        """Initialise la connexion Google Sheets."""
        self._spreadsheet_id = spreadsheet_id
        self._credentials_path = credentials_path

    def get_all_clients(self) -> list[dict[str, str]]:
        """Lit tous les enregistrements de l'onglet Clients."""
        raise NotImplementedError("À implémenter — CDC §7.1")

    def get_all_invoices(self) -> list[dict[str, str]]:
        """Lit tous les enregistrements de l'onglet Factures."""
        raise NotImplementedError("À implémenter — CDC §7.1")

    def get_all_transactions(self) -> list[dict[str, str]]:
        """Lit tous les enregistrements de l'onglet Transactions."""
        raise NotImplementedError("À implémenter — CDC §7.1")

    def update_invoice_status(self, facture_id: str, new_status: str) -> None:
        """Met à jour le statut d'une facture dans l'onglet Factures."""
        raise NotImplementedError("À implémenter — CDC §7.1")
