"""
SAP-Facture Application

Plateforme de facturation URSSAF pour micro-entrepreneurs en services à la personne.
Architecture: Monolith FastAPI + Google Sheets as single source of truth
"""

__version__ = "0.1.0"
__author__ = "Jules Willard"

from .main import create_app

__all__ = ["create_app"]
