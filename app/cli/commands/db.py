from __future__ import annotations

# Compatibility shim for Python <3.11
import logging
from datetime import date
from uuid import uuid4

import typer

from app.database import Base, engine
from app.models.client import Client
from app.models.invoice import Invoice, InvoiceStatus, InvoiceType
from app.models.user import User

from .utils import get_db_session

logger = logging.getLogger(__name__)

db_app = typer.Typer(help="Database management commands")


@db_app.command()
def db_init_command() -> None:
    """Initialize database and create all tables.

    Creates the schema for all models. Safe to run multiple times.

    Examples:
        sap db init
    """
    try:
        typer.echo("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        typer.echo("Database tables created successfully!")
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@db_app.command()
def db_seed_command() -> None:
    """Seed database with test data.

    Creates:
    - 1 test user (SIREN, NOVA)
    - 3 test clients
    - 5 test invoices with various statuses

    Examples:
        sap db seed
    """
    db = get_db_session()
    try:
        # Check if data already exists
        existing_user = db.query(User).first()
        if existing_user:
            typer.echo(
                "Warning: Database already contains data. Skipping seed.",
                err=True,
            )
            return

        typer.echo("Seeding database with test data...")

        # Create test user
        user = User(
            id=str(uuid4()),
            email="test@sap-facture.fr",
            name="Test User SARL",
            siren="12345678901234",
            nova="NOVA12345678",
        )
        db.add(user)
        db.flush()

        # Create test clients
        clients = []
        for i in range(1, 4):
            client = Client(
                id=str(uuid4()),
                user_id=user.id,
                first_name=f"Client{i}",
                last_name=f"Test{i}",
                email=f"client{i}@example.com",
                siret=f"1234567890{i:03d}",
                urssaf_registered=True,
            )
            db.add(client)
            clients.append(client)

        db.flush()

        # Create test invoices
        statuses = [
            InvoiceStatus.DRAFT,
            InvoiceStatus.SUBMITTED,
            InvoiceStatus.VALIDATED,
            InvoiceStatus.PAID,
            InvoiceStatus.REJECTED,
        ]

        for i, status in enumerate(statuses, 1):
            invoice = Invoice(
                id=str(uuid4()),
                user_id=user.id,
                client_id=clients[i % len(clients)].id,
                invoice_number=f"2026-03-{i:03d}",
                description=f"Test invoice {i}",
                invoice_type=InvoiceType.HEURE,
                nature_code="100",
                date_service_from=date(2026, 3, 1),
                date_service_to=date(2026, 3, 31),
                amount_ht=100.0 * i,
                tva_rate=0.0,
                amount_ttc=100.0 * i,
                status=status,
            )
            db.add(invoice)

        db.commit()
        typer.echo("Test data created successfully!")
        typer.echo(f"  - User: {user.email} (SIREN: {user.siren})")
        typer.echo(f"  - Clients: {len(clients)}")
        typer.echo(f"  - Invoices: {len(statuses)}")
        logger.info("Database seeded with test data")

    except Exception as e:
        db.rollback()
        logger.error(f"Database seeding failed: {e}", exc_info=True)
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        db.close()
