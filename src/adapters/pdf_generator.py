"""Export de rapports — Phase 3.

AIS génère les factures PDF. SAP-Facture peut générer
des rapports CSV et attestations fiscales (futur).
"""

from __future__ import annotations


class ExportService:
    """Service d'export de données — Phase 3."""

    def export_csv(self, data: list[dict[str, str]], path: str) -> None:
        """Exporte des données en CSV.

        Args:
            data: Données à exporter.
            path: Chemin de destination.
        """
        raise NotImplementedError("Phase 3")
