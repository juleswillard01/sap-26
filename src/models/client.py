"""Modele Client."""

from __future__ import annotations

from datetime import date  # noqa: TC003
from enum import StrEnum

from pydantic import BaseModel


class ClientStatus(StrEnum):
    """Statut URSSAF du client — CDC §1.1."""

    EN_ATTENTE = "EN_ATTENTE"
    INSCRIT = "INSCRIT"
    ERREUR = "ERREUR"
    INACTIF = "INACTIF"


class Client(BaseModel):
    """Represente un client (parent d'eleve) — CDC §1.1."""

    client_id: str
    nom: str
    prenom: str
    email: str
    telephone: str = ""
    adresse: str = ""
    code_postal: str = ""
    ville: str = ""
    urssaf_id: str | None = None
    statut_urssaf: ClientStatus = ClientStatus.EN_ATTENTE
    date_inscription: date | None = None
    actif: bool = True
