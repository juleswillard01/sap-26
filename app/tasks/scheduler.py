from __future__ import annotations

import logging

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SchedulerConfig:
    """Configuration for APScheduler."""

    JOBSTORES = {"default": SQLAlchemyJobStore(url="sqlite:///./data/jobs.db")}
    EXECUTORS = {
        "default": AsyncIOExecutor(),
    }
    JOB_DEFAULTS = {
        "coalesce": True,
        "max_instances": 1,
    }
    TIMEZONE = "UTC"


def setup_scheduler(db: Session | None = None) -> AsyncIOScheduler:
    """
    Initialize and configure APScheduler.

    Args:
        db: Optional database session for job persistence.

    Returns:
        AsyncIOScheduler instance configured with jobs.
    """
    config = {
        "apscheduler.timezone": SchedulerConfig.TIMEZONE,
        "apscheduler.jobstores.default": {
            "type": "sqlalchemy",
            "url": "sqlite:///./data/jobs.db",
        },
        "apscheduler.executors.default": {
            "type": "asyncio",
        },
        "apscheduler.job_defaults.coalesce": True,
        "apscheduler.job_defaults.max_instances": 1,
    }

    scheduler = AsyncIOScheduler(config)

    # Register jobs
    _register_jobs(scheduler)

    return scheduler


def _register_jobs(scheduler: AsyncIOScheduler) -> None:
    """
    Register all scheduled jobs.

    Args:
        scheduler: AsyncIOScheduler instance.
    """
    # Job 1: Poll URSSAF status every 4 hours
    scheduler.add_job(
        _poll_urssaf_status,
        "interval",
        hours=4,
        id="poll_urssaf_status",
        name="Poll URSSAF Status",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Scheduled job: poll_urssaf_status (every 4 hours)")

    # Job 2: Send email reminders for 36h-old unvalidated invoices
    scheduler.add_job(
        _send_invoice_reminders,
        "interval",
        hours=6,
        id="send_invoice_reminders",
        name="Send Invoice Reminders",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Scheduled job: send_invoice_reminders (every 6 hours)")

    # Job 3: Sync bank transactions every 6 hours
    scheduler.add_job(
        _sync_bank_transactions,
        "interval",
        hours=6,
        id="sync_bank_transactions",
        name="Sync Bank Transactions",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Scheduled job: sync_bank_transactions (every 6 hours)")


async def _poll_urssaf_status() -> None:
    """
    Poll URSSAF API for invoice status updates.

    This job runs every 4 hours and updates the status of invoices
    that have been submitted to URSSAF.
    """
    try:
        logger.info("Starting URSSAF status poll job")

        # TODO: Import service when available
        # from app.services.urssaf_service import UrssafService
        # service = UrssafService()
        # updated = await service.poll_invoice_status()
        # logger.info(f"URSSAF poll completed: {updated} invoices updated")

        logger.debug("URSSAF status poll job completed (stub)")
    except Exception as e:
        logger.error(
            "URSSAF status poll job failed",
            exc_info=True,
            extra={"error": str(e)},
        )
        raise


async def _send_invoice_reminders() -> None:
    """
    Send email reminders for unvalidated invoices older than 36 hours.

    This job runs every 6 hours and identifies invoices that have been
    pending validation for more than 36 hours, then sends reminder emails
    to the users.
    """
    try:
        logger.info("Starting invoice reminder job")

        # TODO: Import service when available
        # from app.services.invoice_service import InvoiceService
        # from app.services.email_service import EmailService
        # invoice_service = InvoiceService()
        # email_service = EmailService()
        # old_invoices = await invoice_service.get_unvalidated_invoices(hours=36)
        # count = 0
        # for invoice in old_invoices:
        #     await email_service.send_reminder(invoice)
        #     count += 1
        # logger.info(f"Invoice reminder job completed: {count} reminders sent")

        logger.debug("Invoice reminder job completed (stub)")
    except Exception as e:
        logger.error(
            "Invoice reminder job failed",
            exc_info=True,
            extra={"error": str(e)},
        )
        raise


async def _sync_bank_transactions() -> None:
    """
    Sync bank transactions from Swan API.

    This job runs every 6 hours and fetches recent transactions from
    the Swan bank API and updates the local database.
    """
    try:
        logger.info("Starting bank transaction sync job")

        # TODO: Import service when available
        # from app.services.swan_service import SwanService
        # service = SwanService()
        # synced = await service.sync_transactions()
        # logger.info(f"Bank transaction sync completed: {synced} transactions synced")

        logger.debug("Bank transaction sync job completed (stub)")
    except Exception as e:
        logger.error(
            "Bank transaction sync job failed",
            exc_info=True,
            extra={"error": str(e)},
        )
        raise
