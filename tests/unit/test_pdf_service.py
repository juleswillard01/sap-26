from __future__ import annotations

import tempfile
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.models.client import Client
from app.models.invoice import Invoice, InvoiceType
from app.models.user import User
from app.services.pdf_service import PDFGenerationError, PDFService


@pytest.fixture
def temp_template_dir() -> Path:
    """Create temporary template directory with invoice.html."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        pdf_dir = tmppath / "pdf"
        pdf_dir.mkdir()

        # Create minimal HTML template
        template_content = """
        <!DOCTYPE html>
        <html>
        <head><title>{{ invoice.invoice_number }}</title></head>
        <body>
        <h1>FACTURE</h1>
        <p>Invoice: {{ invoice.invoice_number }}</p>
        <p>User: {{ user.name }}</p>
        <p>SIREN: {{ user.siren }}</p>
        <p>Client: {{ client.full_name }}</p>
        <p>Description: {{ invoice.description }}</p>
        <p>Amount: {{ invoice.amount_ht }}</p>
        <p>Type: {{ invoice.invoice_type.value }}</p>
        {% if logo_base64 %}<img src="{{ logo_base64 }}" alt="Logo">{% endif %}
        </body>
        </html>
        """
        (pdf_dir / "invoice.html").write_text(template_content)

        yield tmppath


@pytest.fixture
def mock_user() -> User:
    """Create mock user."""
    user = Mock(spec=User)
    user.id = "user-123"
    user.name = "Jules Dupont"
    user.email = "jules@example.com"
    user.siren = "12345678901234"
    user.nova = "NOVA001"
    user.logo_file_path = None
    return user


@pytest.fixture
def mock_client() -> Client:
    """Create mock client."""
    client = Mock(spec=Client)
    client.id = "client-456"
    client.first_name = "Jean"
    client.last_name = "Dupont"
    client.full_name = "Jean Dupont"
    client.email = "jean@example.com"
    client.siret = "98765432123456"
    client.address = "123 Rue de Paris, 75000 Paris"
    return client


@pytest.fixture
def mock_invoice() -> Invoice:
    """Create mock invoice."""
    invoice = Mock(spec=Invoice)
    invoice.id = "inv-789"
    invoice.invoice_number = "2025-03-001"
    invoice.description = "Cours particuliers - Français"
    invoice.invoice_type = InvoiceType.HEURE
    invoice.amount_ht = 150.00
    invoice.amount_ttc = 150.00
    invoice.tva_rate = 0.0
    invoice.date_service_from = date(2025, 3, 1)
    invoice.date_service_to = date(2025, 3, 15)
    invoice.created_at = datetime(2025, 3, 15, 10, 30, 0)
    invoice.status = "DRAFT"
    return invoice


class TestPDFServiceInitialization:
    """Test PDFService initialization."""

    def test_init_creates_jinja_environment(self, temp_template_dir: Path) -> None:
        """Test initialization with valid template directory."""
        service = PDFService(str(temp_template_dir))
        assert service._jinja_env is not None
        assert service._template_dir == temp_template_dir

    def test_init_raises_error_for_missing_directory(self) -> None:
        """Test initialization raises error for non-existent template directory."""
        with pytest.raises(PDFGenerationError) as exc_info:
            PDFService("/nonexistent/path")
        assert "Template directory not found" in str(exc_info.value)

    def test_init_with_custom_path(self, temp_template_dir: Path) -> None:
        """Test initialization with custom template path."""
        service = PDFService(temp_template_dir)
        assert service._template_dir == temp_template_dir


class TestHTMLRendering:
    """Test HTML template rendering."""

    def test_render_invoice_html_with_logo(
        self,
        temp_template_dir: Path,
        mock_invoice: Invoice,
        mock_user: User,
        mock_client: Client,
    ) -> None:
        """Test rendering invoice HTML with logo."""
        service = PDFService(str(temp_template_dir))

        # Create fake logo file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n")
            logo_path = Path(f.name)

        try:
            html = service._render_invoice_html(
                invoice=mock_invoice,
                user=mock_user,
                client=mock_client,
                logo_path=logo_path,
            )

            assert "FACTURE" in html
            assert mock_invoice.invoice_number in html
            assert mock_user.name in html
            assert mock_client.full_name in html
            assert str(mock_invoice.amount_ht) in html
            assert "data:image" in html  # Base64 encoded logo
        finally:
            logo_path.unlink()

    def test_render_invoice_html_without_logo(
        self,
        temp_template_dir: Path,
        mock_invoice: Invoice,
        mock_user: User,
        mock_client: Client,
    ) -> None:
        """Test rendering invoice HTML without logo."""
        service = PDFService(str(temp_template_dir))

        html = service._render_invoice_html(
            invoice=mock_invoice,
            user=mock_user,
            client=mock_client,
            logo_path=None,
        )

        assert "FACTURE" in html
        assert mock_invoice.invoice_number in html
        assert mock_user.name in html
        assert mock_client.full_name in html

    def test_render_invoice_contains_invoice_data(
        self,
        temp_template_dir: Path,
        mock_invoice: Invoice,
        mock_user: User,
        mock_client: Client,
    ) -> None:
        """Test that rendered HTML contains all invoice data."""
        service = PDFService(str(temp_template_dir))

        html = service._render_invoice_html(
            invoice=mock_invoice,
            user=mock_user,
            client=mock_client,
            logo_path=None,
        )

        # Check all critical data is present
        assert mock_invoice.invoice_number in html
        assert mock_user.name in html
        assert mock_user.siren in html
        assert mock_client.full_name in html
        assert mock_invoice.description in html
        assert mock_invoice.invoice_type.value in html
        assert str(mock_invoice.amount_ht) in html

    def test_render_raises_on_missing_template(
        self,
        temp_template_dir: Path,
        mock_invoice: Invoice,
        mock_user: User,
        mock_client: Client,
    ) -> None:
        """Test rendering raises error when template not found."""
        service = PDFService(str(temp_template_dir))

        # Manually delete template to force error
        template_path = temp_template_dir / "pdf" / "invoice.html"
        template_path.unlink()

        with pytest.raises(PDFGenerationError) as exc_info:
            service._render_invoice_html(
                invoice=mock_invoice,
                user=mock_user,
                client=mock_client,
                logo_path=None,
            )
        assert "Template rendering failed" in str(exc_info.value)


class TestLogoEncoding:
    """Test logo encoding to base64."""

    def test_encode_logo_base64_png(self) -> None:
        """Test encoding PNG logo to base64."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Write minimal PNG data
            f.write(b"\x89PNG\r\n\x1a\n")
            logo_path = Path(f.name)

        try:
            result = PDFService._encode_logo_base64(logo_path)
            assert result is not None
            assert result.startswith("data:image/png;base64,")
            assert "iVBO" in result  # Base64 PNG header
        finally:
            logo_path.unlink()

    def test_encode_logo_base64_jpeg(self) -> None:
        """Test encoding JPEG logo to base64."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            # Write minimal JPEG data
            f.write(b"\xff\xd8\xff\xe0")
            logo_path = Path(f.name)

        try:
            result = PDFService._encode_logo_base64(logo_path)
            assert result is not None
            assert result.startswith("data:image/jpeg;base64,")
        finally:
            logo_path.unlink()

    def test_encode_logo_returns_none_for_missing_file(self) -> None:
        """Test encoding returns None for missing file."""
        result = PDFService._encode_logo_base64(Path("/nonexistent/logo.png"))
        assert result is None

    def test_encode_logo_handles_read_errors(self) -> None:
        """Test encoding handles read errors gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a directory (not a file)
            fake_file = Path(tmpdir) / "not_a_file"
            fake_file.mkdir()

            result = PDFService._encode_logo_base64(fake_file)
            assert result is None


class TestPDFFilenameGeneration:
    """Test PDF filename generation."""

    def test_generate_pdf_filename_format(self, mock_invoice: Invoice, mock_client: Client) -> None:
        """Test PDF filename format."""
        filename = PDFService._generate_pdf_filename(mock_invoice, mock_client)

        assert filename.startswith("Invoice_")
        assert filename.endswith(".pdf")
        assert "2025" in filename  # Year from date
        assert "03" in filename  # Month
        assert "15" in filename  # Day
        assert mock_client.last_name in filename

    def test_generate_pdf_filename_sanitizes_client_name(
        self, mock_invoice: Invoice, mock_client: Client
    ) -> None:
        """Test that special characters in client name are sanitized."""
        mock_client.last_name = "O'Reilly/Smith"
        filename = PDFService._generate_pdf_filename(mock_invoice, mock_client)

        # Check that special chars are replaced
        assert "/" not in filename
        assert "Invoice_" in filename
        assert ".pdf" in filename


class TestPDFDirectoryEnsuring:
    """Test PDF directory creation."""

    def test_ensure_pdf_directory_creates_structure(self, mock_invoice: Invoice) -> None:
        """Test that PDF directory structure is created."""
        with tempfile.TemporaryDirectory():
            # Mock storage path
            Path.cwd()
            mock_invoice.created_at = datetime(2025, 3, 15, 10, 30, 0)

            # This would normally create storage/pdfs/2025/03
            # For testing, we just verify the path logic
            pdf_dir = PDFService._ensure_pdf_directory(mock_invoice)

            assert "2025" in str(pdf_dir)
            assert "03" in str(pdf_dir)
            assert "pdfs" in str(pdf_dir)

    def test_ensure_pdf_directory_uses_correct_date_format(self, mock_invoice: Invoice) -> None:
        """Test that directory uses YYYY/MM format."""
        mock_invoice.created_at = datetime(2025, 1, 5, 10, 30, 0)
        pdf_dir = PDFService._ensure_pdf_directory(mock_invoice)

        assert str(pdf_dir).endswith("2025/01")

    def test_ensure_pdf_directory_handles_different_months(self, mock_invoice: Invoice) -> None:
        """Test directory creation for different months."""
        for month in [1, 6, 12]:
            mock_invoice.created_at = datetime(2025, month, 15, 10, 30, 0)
            pdf_dir = PDFService._ensure_pdf_directory(mock_invoice)

            assert f"2025/{month:02d}" in str(pdf_dir)


class TestHTMLToPDFConversion:
    """Test HTML to PDF conversion."""

    @patch("app.services.pdf_service.HTML")
    def test_html_to_pdf_success(self, mock_html_class: Mock) -> None:
        """Test successful HTML to PDF conversion."""
        # Setup mock
        mock_html_instance = MagicMock()
        mock_html_class.return_value = mock_html_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"

            PDFService._html_to_pdf("<html><body>Test</body></html>", output_path)

            # Verify HTML was created with correct parameters
            mock_html_class.assert_called_once()
            assert mock_html_instance.write_pdf.called

    @patch("app.services.pdf_service.HTML")
    def test_html_to_pdf_weasyprint_error(self, mock_html_class: Mock) -> None:
        """Test error handling for weasyprint failures."""
        # Setup mock to raise error
        mock_html_class.side_effect = Exception("Weasyprint error")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"

            with pytest.raises(PDFGenerationError) as exc_info:
                PDFService._html_to_pdf("<html><body>Test</body></html>", output_path)

            assert "Weasyprint conversion failed" in str(exc_info.value)


class TestFullPDFGeneration:
    """Test complete PDF generation flow."""

    @patch("app.services.pdf_service.HTML")
    def test_generate_invoice_pdf_creates_file(
        self,
        mock_html_class: Mock,
        temp_template_dir: Path,
        mock_invoice: Invoice,
        mock_user: User,
        mock_client: Client,
    ) -> None:
        """Test that PDF generation creates file and returns path."""
        # Setup mock
        mock_html_instance = MagicMock()
        mock_html_class.return_value = mock_html_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            # Change to temp directory for storage
            original_cwd = Path.cwd()
            import os

            os.chdir(tmpdir)

            try:
                service = PDFService(str(temp_template_dir))
                pdf_path = service.generate_invoice_pdf(
                    invoice=mock_invoice,
                    user=mock_user,
                    client=mock_client,
                    logo_path=None,
                )

                assert pdf_path is not None
                assert isinstance(pdf_path, Path)
                # Path should contain invoice number
                assert "Invoice_" in pdf_path.name

            finally:
                os.chdir(original_cwd)

    @patch("app.services.pdf_service.HTML")
    def test_generate_invoice_pdf_with_logo(
        self,
        mock_html_class: Mock,
        temp_template_dir: Path,
        mock_invoice: Invoice,
        mock_user: User,
        mock_client: Client,
    ) -> None:
        """Test PDF generation includes logo when provided."""
        # Setup mock
        mock_html_instance = MagicMock()
        mock_html_class.return_value = mock_html_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create fake logo
            logo_path = Path(tmpdir) / "logo.png"
            logo_path.write_bytes(b"\x89PNG\r\n\x1a\n")

            original_cwd = Path.cwd()
            import os

            os.chdir(tmpdir)

            try:
                service = PDFService(str(temp_template_dir))
                pdf_path = service.generate_invoice_pdf(
                    invoice=mock_invoice,
                    user=mock_user,
                    client=mock_client,
                    logo_path=logo_path,
                )

                assert pdf_path is not None

                # Verify write_pdf was called
                assert mock_html_instance.write_pdf.called

            finally:
                os.chdir(original_cwd)

    def test_generate_invoice_pdf_raises_on_template_error(
        self,
        temp_template_dir: Path,
        mock_invoice: Invoice,
        mock_user: User,
        mock_client: Client,
    ) -> None:
        """Test that PDF generation raises error on template problems."""
        # Remove template file
        template_path = temp_template_dir / "pdf" / "invoice.html"
        template_path.unlink()

        service = PDFService(str(temp_template_dir))

        with pytest.raises(PDFGenerationError) as exc_info:
            service.generate_invoice_pdf(
                invoice=mock_invoice,
                user=mock_user,
                client=mock_client,
                logo_path=None,
            )

        # Check that error message indicates generation failure
        error_msg = str(exc_info.value)
        assert "generation failed" in error_msg or "Template rendering failed" in error_msg

    @patch("app.services.pdf_service.HTML")
    def test_generate_invoice_pdf_correct_path_format(
        self,
        mock_html_class: Mock,
        temp_template_dir: Path,
        mock_invoice: Invoice,
        mock_user: User,
        mock_client: Client,
    ) -> None:
        """Test that PDF path follows correct format: storage/pdfs/YYYY/MM/."""
        # Setup mock
        mock_html_instance = MagicMock()
        mock_html_class.return_value = mock_html_instance

        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = Path.cwd()
            import os

            os.chdir(tmpdir)

            try:
                service = PDFService(str(temp_template_dir))
                mock_invoice.created_at = datetime(2025, 3, 15, 10, 30, 0)

                pdf_path = service.generate_invoice_pdf(
                    invoice=mock_invoice,
                    user=mock_user,
                    client=mock_client,
                    logo_path=None,
                )

                # Check path format
                path_str = str(pdf_path)
                assert "storage/pdfs/2025/03" in path_str
                assert "Invoice_" in path_str
                assert ".pdf" in path_str

            finally:
                os.chdir(original_cwd)


class TestLogoService:
    """Test logo service functionality."""

    def test_logo_upload_valid_file(self) -> None:
        """Test uploading valid logo file."""
        from app.services.logo_service import LogoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = LogoService(tmpdir)

            # Create valid PNG content
            logo_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

            logo_path = service.upload_logo(
                user_id="user-123",
                file_content=logo_content,
                filename="logo.png",
            )

            assert logo_path.exists()
            assert logo_path.name == "logo.png"
            assert "user-123" in str(logo_path)

    def test_logo_upload_invalid_format_raises(self) -> None:
        """Test uploading invalid format raises error."""
        from app.services.logo_service import LogoService, LogoUploadError

        with tempfile.TemporaryDirectory() as tmpdir:
            service = LogoService(tmpdir)

            with pytest.raises(LogoUploadError) as exc_info:
                service.upload_logo(
                    user_id="user-123",
                    file_content=b"invalid content",
                    filename="logo.txt",
                )

            assert "Invalid file format" in str(exc_info.value)

    def test_logo_upload_oversized_file_raises(self) -> None:
        """Test uploading oversized file raises error."""
        from app.services.logo_service import LogoService, LogoUploadError

        with tempfile.TemporaryDirectory() as tmpdir:
            service = LogoService(tmpdir)

            # Create oversized file (6 MB)
            oversized_content = b"x" * (6 * 1024 * 1024)

            with pytest.raises(LogoUploadError) as exc_info:
                service.upload_logo(
                    user_id="user-123",
                    file_content=oversized_content,
                    filename="logo.png",
                )

            assert "exceeds" in str(exc_info.value)

    def test_logo_upload_empty_file_raises(self) -> None:
        """Test uploading empty file raises error."""
        from app.services.logo_service import LogoService, LogoUploadError

        with tempfile.TemporaryDirectory() as tmpdir:
            service = LogoService(tmpdir)

            with pytest.raises(LogoUploadError) as exc_info:
                service.upload_logo(
                    user_id="user-123",
                    file_content=b"",
                    filename="logo.png",
                )

            assert "empty" in str(exc_info.value).lower()

    def test_get_logo_path_existing(self) -> None:
        """Test getting path to existing logo."""
        from app.services.logo_service import LogoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = LogoService(tmpdir)

            # Create logo
            logo_content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
            service.upload_logo(
                user_id="user-123",
                file_content=logo_content,
                filename="logo.png",
            )

            # Get path
            logo_path = service.get_logo_path("user-123")
            assert logo_path is not None
            assert logo_path.exists()

    def test_get_logo_path_nonexistent_user(self) -> None:
        """Test getting logo for non-existent user returns None."""
        from app.services.logo_service import LogoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = LogoService(tmpdir)
            logo_path = service.get_logo_path("nonexistent-user")
            assert logo_path is None
