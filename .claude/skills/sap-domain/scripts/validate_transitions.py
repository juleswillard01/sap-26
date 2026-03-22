#!/usr/bin/env python3
"""Validate invoice state machine transitions."""

from __future__ import annotations

from enum import Enum


class InvoiceStatus(str, Enum):
    BROUILLON = "BROUILLON"
    SOUMIS = "SOUMIS"
    CREE = "CREE"
    EN_ATTENTE = "EN_ATTENTE"
    VALIDE = "VALIDE"
    PAYE = "PAYE"
    RAPPROCHE = "RAPPROCHE"
    ERREUR = "ERREUR"
    EXPIRE = "EXPIRE"
    REJETE = "REJETE"
    ANNULE = "ANNULE"


VALID_TRANSITIONS: dict[InvoiceStatus, list[InvoiceStatus]] = {
    InvoiceStatus.BROUILLON: [InvoiceStatus.SOUMIS, InvoiceStatus.ANNULE],
    InvoiceStatus.SOUMIS: [InvoiceStatus.CREE, InvoiceStatus.ERREUR],
    InvoiceStatus.CREE: [InvoiceStatus.EN_ATTENTE],
    InvoiceStatus.EN_ATTENTE: [
        InvoiceStatus.VALIDE,
        InvoiceStatus.EXPIRE,
        InvoiceStatus.REJETE,
    ],
    InvoiceStatus.VALIDE: [InvoiceStatus.PAYE],
    InvoiceStatus.PAYE: [InvoiceStatus.RAPPROCHE],
    InvoiceStatus.ERREUR: [InvoiceStatus.BROUILLON],
    InvoiceStatus.EXPIRE: [InvoiceStatus.BROUILLON],
    InvoiceStatus.REJETE: [InvoiceStatus.BROUILLON],
    InvoiceStatus.RAPPROCHE: [],
    InvoiceStatus.ANNULE: [],
}


def can_transition(current: InvoiceStatus, target: InvoiceStatus) -> bool:
    """Check if transition is valid."""
    return target in VALID_TRANSITIONS.get(current, [])


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <current_state> <target_state>")
        sys.exit(1)

    try:
        current = InvoiceStatus(sys.argv[1].upper())
        target = InvoiceStatus(sys.argv[2].upper())
    except ValueError as e:
        print(f"Invalid status: {e}")
        sys.exit(1)

    result = can_transition(current, target)
    status_str = "✅ VALID" if result else "❌ INVALID"
    print(f"{current.value} → {target.value}: {status_str}")
    sys.exit(0 if result else 1)
