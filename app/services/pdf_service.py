from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

from app.models.client import Client
from app.models.invoice import Invoice
from app.models.user import User

logger = logging.getLogger(__name__)


class PDFGenerationError(Exception):
    """Raised when PDF generation fails."""

    pass


class PDFService:
    """Service for generating PDF invoices."""

    def __init__(self, template_dir: Path | str = "app/web/templates") -> None:
        """Initialize PDF service with Jinja2 template environment.

        Args:
            template_dir: Path to templates directory.

        Raises:
            PDFGenerationError: If template directory does not exist.
        """
        template_path = Path(template_dir)
        if not template_path.exists():
            raise PDFGenerationError(f"Template directory not found: {template_path}")

        self._template_dir = template_path
        self._jinja_env = Environment(
            loader=FileSystemLoader(str(template_path)),
            autoescape=True,
        )

    def generate_invoice_pdf(
        self, invoice: Invoice, user: User, client: Client, logo_path: Path | None = None
    ) -> Path:
        """Generate PDF invoice from invoice data.

        Args:
            invoice: Invoice instance.
            user: User instance.
            client: Client instance.
            logo_path: Optional path to user logo file.

        Returns:
            Path to generated PDF file.

        Raises:
            PDFGenerationError: If PDF generation fails.
        """
        try:
            # Render HTML from template
            html_content = self._render_invoice_html(
                invoice=invoice,
                user=user,
                client=client,
                logo_path=logo_path,
            )

            # Generate PDF filename
            pdf_filename = self._generate_pdf_filename(invoice, client)
            pdf_path = self._ensure_pdf_directory(invoice)
            full_pdf_path = pdf_path / pdf_filename

            # Convert HTML to PDF
            self._html_to_pdf(html_content, full_pdf_path)

            logger.info(
                "PDF invoice generated",
                extra={
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "pdf_path": str(full_pdf_path),
                },
            )

            return full_pdf_path

        except PDFGenerationError:
            raise
        except Exception as e:
            logger.error(
                "PDF generation failed",
                extra={"invoice_id": invoice.id, "error": str(e)},
                exc_info=True,
            )
            raise PDFGenerationError(f"PDF generation failed: {e}") from e

    def _render_invoice_html(
        self,
        invoice: Invoice,
        user: User,
        client: Client,
        logo_path: Path | None = None,
    ) -> str:
        """Render invoice HTML from template.

        Args:
            invoice: Invoice instance.
            user: User instance.
            client: Client instance.
            logo_path: Optional path to user logo.

        Returns:
            Rendered HTML string.

        Raises:
            PDFGenerationError: If template rendering fails.
        """
        try:
            template = self._jinja_env.get_template("pdf/invoice.html")

            # Prepare context data
            context = {
                "invoice": invoice,
                "user": user,
                "client": client,
                "logo_base64": self._encode_logo_base64(logo_path) if logo_path else None,
                "now": datetime.utcnow(),
            }

            return template.render(**context)

        except Exception as e:
            logger.error("Template rendering failed", exc_info=True)
            raise PDFGenerationError(f"Template rendering failed: {e}") from e

    @staticmethod
    def _encode_logo_base64(logo_path: Path) -> str | None:
        """Encode logo file to base64 for embedding in HTML.

        Args:
            logo_path: Path to logo file.

        Returns:
            Base64-encoded image string, or None if file not found.
        """
        try:
            if not logo_path.exists():
                logger.warning(f"Logo file not found: {logo_path}")
                return None

            import base64

            with open(logo_path, "rb") as f:
                image_data = f.read()

            # Determine image type
            suffix = logo_path.suffix.lower()
            if suffix == ".png":
                mime_type = "image/png"
            elif suffix in [".jpg", ".jpeg"]:
                mime_type = "image/jpeg"
            else:
                mime_type = "image/png"

            b64_string = base64.b64encode(image_data).decode()
            return f"data:{mime_type};base64,{b64_string}"

        except Exception as e:
            logger.warning(f"Failed to encode logo: {e}", exc_info=False)
            return None

    @staticmethod
    def _generate_pdf_filename(invoice: Invoice, client: Client) -> str:
        """Generate PDF filename.

        Args:
            invoice: Invoice instance.
            client: Client instance.

        Returns:
            Filename string.
        """
        client_name = client.last_name.replace(" ", "_").replace("/", "_")
        date_str = invoice.created_at.strftime("%Y%m%d")
        return f"Invoice_{date_str}_{client_name}.pdf"

    @staticmethod
    def _ensure_pdf_directory(invoice: Invoice) -> Path:
        """Ensure PDF storage directory exists.

        Args:
            invoice: Invoice instance.

        Returns:
            Path to PDF directory.
        """
        date_parts = invoice.created_at.strftime("%Y/%m")
        pdf_dir = Path("storage/pdfs") / date_parts
        pdf_dir.mkdir(parents=True, exist_ok=True)
        return pdf_dir

    @staticmethod
    def _html_to_pdf(html_content: str, output_path: Path) -> None:
        """Convert HTML string to PDF file.

        Args:
            html_content: HTML content as string.
            output_path: Path where PDF will be saved.

        Raises:
            PDFGenerationError: If conversion fails.
        """
        try:
            # Create HTML object and generate PDF
            html = HTML(string=html_content, base_url=Path.cwd())
            html.write_pdf(output_path)

        except Exception as e:
            logger.error(
                "Weasyprint PDF conversion failed",
                extra={"output_path": str(output_path)},
                exc_info=True,
            )
            raise PDFGenerationError(f"Weasyprint conversion failed: {e}") from e
