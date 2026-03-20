"""Génération PDF factures via WeasyPrint — CDC §3.3."""

from pathlib import Path


def generate_invoice_pdf(invoice_data: dict[str, str], output_path: Path) -> Path:
    """Génère un PDF de facture.

    Args:
        invoice_data: Données de la facture.
        output_path: Chemin de destination du PDF.

    Returns:
        Chemin du PDF généré.
    """
    raise NotImplementedError("À implémenter — CDC §3.3")
