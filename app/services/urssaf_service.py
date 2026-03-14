from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.integrations.urssaf_client import URSSAFClient
from app.integrations.urssaf_exceptions import URSSAFError
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment_request import PaymentRequest, PaymentRequestStatus
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.payment_request_repository import PaymentRequestRepository
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class URSSAFService:
    """Service for URSSAF invoice submission and status polling."""

    def __init__(
        self,
        db: Session,
        urssaf_client: URSSAFClient,
    ) -> None:
        """Initialize URSSAF service.

        Args:
            db: SQLAlchemy database session.
            urssaf_client: URSSAF API client.
        """
        self._db = db
        self._urssaf_client = urssaf_client
        self._invoice_repo = InvoiceRepository(db)
        self._payment_repo = PaymentRequestRepository(db)
        self._audit_service = AuditService(db)

    async def submit_invoice(self, invoice_id: str) -> PaymentRequest:
        """Submit an invoice to URSSAF.

        Converts invoice to URSSAF payload, submits, creates PaymentRequest,
        updates invoice status to SUBMITTED.

        Args:
            invoice_id: Invoice ID to submit.

        Returns:
            Created PaymentRequest instance.

        Raises:
            ValueError: If invoice not found or not in DRAFT status.
            URSSAFError: If URSSAF submission fails.
        """
        invoice = self._invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")

        if invoice.status != InvoiceStatus.DRAFT:
            raise ValueError(
                f"Can only submit DRAFT invoices, current status: {invoice.status.value}"
            )

        # Build URSSAF payload
        payload = self._build_urssaf_payload(invoice)

        logger.info(
            "Submitting invoice to URSSAF",
            extra={"invoice_id": invoice_id, "invoice_number": invoice.invoice_number},
        )

        try:
            # Submit to URSSAF
            response = await self._urssaf_client.submit_payment_request(
                intervenant_code=invoice.user.nova,
                particulier_email=invoice.client.email,
                date_debut=invoice.date_service_from.isoformat(),
                date_fin=invoice.date_service_to.isoformat(),
                montant=invoice.amount_ttc,
                unite_travail=payload["unite_travail"],
                code_nature=invoice.nature_code,
                reference=invoice.invoice_number,
            )

            # Create payment request record
            payment_request = self._payment_repo.create(
                invoice_id=invoice_id,
                amount=invoice.amount_ttc,
            )

            # Store URSSAF response
            payment_request.urssaf_request_id = response.get("id")
            payment_request.raw_response = json.dumps(response)
            self._db.commit()
            self._db.refresh(payment_request)

            # Update invoice status to SUBMITTED
            self._invoice_repo.update_status(invoice_id, InvoiceStatus.SUBMITTED)
            invoice.payment_request_id = payment_request.id
            self._db.commit()

            # Audit log
            self._audit_service.log_action(
                action="SUBMIT_URSSAF",
                entity_type="invoice",
                entity_id=invoice_id,
                user_id=invoice.user_id,
                new_value={
                    "status": InvoiceStatus.SUBMITTED.value,
                    "payment_request_id": payment_request.id,
                },
                metadata={"urssaf_request_id": payment_request.urssaf_request_id},
            )

            logger.info(
                "Invoice submitted to URSSAF successfully",
                extra={
                    "invoice_id": invoice_id,
                    "payment_request_id": payment_request.id,
                    "urssaf_request_id": payment_request.urssaf_request_id,
                },
            )

            return payment_request

        except URSSAFError as e:
            logger.error(
                "URSSAF submission failed",
                exc_info=True,
                extra={"invoice_id": invoice_id, "error": str(e)},
            )
            raise

    async def poll_status(self, payment_request_id: str) -> PaymentRequestStatus:
        """Poll payment request status from URSSAF.

        Updates PaymentRequest and Invoice status based on URSSAF response.

        Args:
            payment_request_id: Payment request ID to poll.

        Returns:
            Updated PaymentRequestStatus.

        Raises:
            ValueError: If payment request not found.
            URSSAFError: If URSSAF API call fails.
        """
        payment_request = self._payment_repo.get_by_id(payment_request_id)
        if not payment_request:
            raise ValueError(f"Payment request not found: {payment_request_id}")

        if not payment_request.urssaf_request_id:
            raise ValueError(f"Payment request has no URSSAF ID: {payment_request_id}")

        invoice = payment_request.invoice

        logger.info(
            "Polling URSSAF status",
            extra={
                "payment_request_id": payment_request_id,
                "urssaf_request_id": payment_request.urssaf_request_id,
            },
        )

        try:
            response = await self._urssaf_client.get_payment_status(
                payment_request.urssaf_request_id
            )

            # Map URSSAF status to PaymentRequestStatus
            urssaf_status = response.get("status", "").upper()
            new_status = self._map_urssaf_status(urssaf_status)

            # Update payment request
            self._payment_repo.update_status(
                payment_request_id,
                new_status,
                json.dumps(response),
            )

            # Update invoice status based on payment request status
            invoice_status = self._map_payment_status_to_invoice_status(new_status)
            self._invoice_repo.update_status(invoice.id, invoice_status)

            # Audit log
            self._audit_service.log_action(
                action="UPDATE",
                entity_type="payment_request",
                entity_id=payment_request_id,
                user_id=invoice.user_id,
                new_value={
                    "status": new_status.value,
                    "invoice_status": invoice_status.value,
                },
                metadata={"urssaf_status": urssaf_status},
            )

            logger.info(
                "Status polled and updated",
                extra={
                    "payment_request_id": payment_request_id,
                    "urssaf_status": urssaf_status,
                    "payment_status": new_status.value,
                    "invoice_status": invoice_status.value,
                },
            )

            return new_status

        except URSSAFError as e:
            logger.error(
                "Status polling failed",
                exc_info=True,
                extra={"payment_request_id": payment_request_id, "error": str(e)},
            )
            raise

    async def sync_all_pending(self) -> list[dict[str, Any]]:
        """Sync status of all pending payment requests.

        Finds all payment requests with non-final status and polls each one.
        Implements retry logic: mark as ERROR after MAX_RETRIES failures.

        Returns:
            List of update dictionaries with results.
        """
        pending_requests = self._payment_repo.list_submitted()

        results: list[dict[str, Any]] = []

        logger.info(
            "Starting sync of pending payment requests",
            extra={"count": len(pending_requests)},
        )

        for payment_request in pending_requests:
            result = {
                "payment_request_id": payment_request.id,
                "success": False,
                "status": None,
                "error": None,
            }

            try:
                status = await self.poll_status(payment_request.id)
                result["success"] = True
                result["status"] = status.value
                logger.debug(
                    "Successfully polled status",
                    extra={"payment_request_id": payment_request.id, "status": status.value},
                )

            except URSSAFError as e:
                # Handle retry logic
                self._payment_repo.increment_retry_count(payment_request.id)
                retry_count = payment_request.retry_count

                if retry_count >= MAX_RETRIES:
                    # Mark as ERROR after max retries
                    self._payment_repo.set_error(
                        payment_request.id,
                        f"Max retries ({MAX_RETRIES}) exceeded: {str(e)}",
                    )
                    self._invoice_repo.update_status(
                        payment_request.invoice_id,
                        InvoiceStatus.ERROR,
                    )
                    result["error"] = f"Max retries exceeded: {str(e)}"

                    logger.error(
                        "Marked payment request as ERROR after max retries",
                        extra={
                            "payment_request_id": payment_request.id,
                            "retry_count": retry_count,
                        },
                    )
                else:
                    result["error"] = f"Retry {retry_count}/{MAX_RETRIES}: {str(e)}"
                    logger.warning(
                        "Status polling failed, will retry",
                        extra={
                            "payment_request_id": payment_request.id,
                            "retry_count": retry_count,
                            "max_retries": MAX_RETRIES,
                            "error": str(e),
                        },
                    )

            except Exception as e:
                result["error"] = f"Unexpected error: {str(e)}"
                logger.error(
                    "Unexpected error during sync",
                    exc_info=True,
                    extra={"payment_request_id": payment_request.id},
                )

            results.append(result)

        logger.info(
            "Sync completed",
            extra={
                "total": len(pending_requests),
                "successful": sum(1 for r in results if r["success"]),
                "errors": sum(1 for r in results if not r["success"]),
            },
        )

        return results

    def _build_urssaf_payload(self, invoice: Invoice) -> dict[str, Any]:
        """Build URSSAF payment request payload from invoice.

        Args:
            invoice: Invoice model instance.

        Returns:
            URSSAF payload dictionary.
        """
        # Determine work unit based on invoice type
        unite_travail = "H" if invoice.invoice_type.value == "HEURE" else "J"

        payload = {
            "intervenant_code": invoice.user.nova,
            "particulier_email": invoice.client.email,
            "date_debut": invoice.date_service_from.isoformat(),
            "date_fin": invoice.date_service_to.isoformat(),
            "montant": invoice.amount_ttc,
            "unite_travail": unite_travail,
            "code_nature": invoice.nature_code,
            "reference": invoice.invoice_number,
        }

        logger.debug(
            "Built URSSAF payload",
            extra={
                "invoice_id": invoice.id,
                "payload": payload,
            },
        )

        return payload

    def _map_urssaf_status(self, urssaf_status: str) -> PaymentRequestStatus:
        """Map URSSAF API status to PaymentRequestStatus enum.

        Args:
            urssaf_status: Status from URSSAF API.

        Returns:
            PaymentRequestStatus enum value.
        """
        status_map = {
            "VALIDATED": PaymentRequestStatus.VALIDATED,
            "PAID": PaymentRequestStatus.PAID,
            "REJECTED": PaymentRequestStatus.REJECTED,
            "EXPIRED": PaymentRequestStatus.EXPIRED,
            "PENDING": PaymentRequestStatus.PENDING,
        }

        mapped = status_map.get(urssaf_status.upper(), PaymentRequestStatus.PENDING)

        logger.debug(
            "Mapped URSSAF status",
            extra={"urssaf_status": urssaf_status, "mapped_status": mapped.value},
        )

        return mapped

    def _map_payment_status_to_invoice_status(
        self,
        payment_status: PaymentRequestStatus,
    ) -> InvoiceStatus:
        """Map PaymentRequestStatus to InvoiceStatus enum.

        Args:
            payment_status: PaymentRequestStatus value.

        Returns:
            InvoiceStatus enum value.
        """
        status_map = {
            PaymentRequestStatus.PENDING: InvoiceStatus.SUBMITTED,
            PaymentRequestStatus.VALIDATED: InvoiceStatus.VALIDATED,
            PaymentRequestStatus.PAID: InvoiceStatus.PAID,
            PaymentRequestStatus.REJECTED: InvoiceStatus.REJECTED,
            PaymentRequestStatus.EXPIRED: InvoiceStatus.REJECTED,
            PaymentRequestStatus.ERROR: InvoiceStatus.ERROR,
        }

        mapped = status_map.get(payment_status, InvoiceStatus.SUBMITTED)

        logger.debug(
            "Mapped payment status to invoice status",
            extra={"payment_status": payment_status.value, "invoice_status": mapped.value},
        )

        return mapped
