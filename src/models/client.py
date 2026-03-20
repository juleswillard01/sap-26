"""Modèle Client."""

from pydantic import BaseModel


class Client(BaseModel):
    """Représente un client (parent d'élève) — CDC §1.1."""

    client_id: str
    nom: str
    prenom: str
    email: str
    telephone: str = ""
    adresse: str = ""
    code_postal: str = ""
    ville: str = ""
    urssaf_id: str | None = None
    statut_urssaf: str = "NON_INSCRIT"
    actif: bool = True
