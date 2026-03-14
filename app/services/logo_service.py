from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class LogoUploadError(Exception):
    """Raised when logo upload fails."""

    pass


class LogoService:
    """Service for managing user logos."""

    ALLOWED_FORMATS = {".jpg", ".jpeg", ".png"}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    MIN_WIDTH = 100
    MIN_HEIGHT = 100

    def __init__(self, storage_dir: Path | str = "storage/logos") -> None:
        """Initialize logo service.

        Args:
            storage_dir: Base directory for logo storage.
        """
        self._storage_dir = Path(storage_dir)

    def upload_logo(self, user_id: str, file_content: bytes, filename: str) -> Path:
        """Upload and validate user logo.

        Args:
            user_id: User ID.
            file_content: Logo file content as bytes.
            filename: Original filename.

        Returns:
            Path to stored logo file.

        Raises:
            LogoUploadError: If validation fails.
        """
        try:
            # Validate file
            self._validate_logo_file(file_content, filename)

            # Create user directory
            user_logo_dir = self._storage_dir / user_id
            user_logo_dir.mkdir(parents=True, exist_ok=True)

            # Store file
            file_path = user_logo_dir / filename
            with open(file_path, "wb") as f:
                f.write(file_content)

            logger.info(
                "Logo uploaded",
                extra={"user_id": user_id, "filename": filename, "path": str(file_path)},
            )

            return file_path

        except LogoUploadError:
            raise
        except Exception as e:
            logger.error(
                "Logo upload failed",
                extra={"user_id": user_id, "filename": filename, "error": str(e)},
                exc_info=True,
            )
            raise LogoUploadError(f"Logo upload failed: {e}") from e

    def get_logo_path(self, user_id: str) -> Path | None:
        """Get path to user's logo file.

        Args:
            user_id: User ID.

        Returns:
            Path to logo file, or None if not found.
        """
        user_logo_dir = self._storage_dir / user_id
        if not user_logo_dir.exists():
            return None

        # Look for any supported format logo
        for ext in self.ALLOWED_FORMATS:
            # Try common filenames
            for name in ["logo", "avatar"]:
                logo_path = user_logo_dir / f"{name}{ext}"
                if logo_path.exists():
                    return logo_path

        # Return first matching file found
        try:
            matching_files = [
                f for f in user_logo_dir.iterdir() if f.suffix.lower() in self.ALLOWED_FORMATS
            ]
            if matching_files:
                return matching_files[0]
        except OSError:
            pass

        return None

    def delete_logo(self, user_id: str) -> bool:
        """Delete user's logo.

        Args:
            user_id: User ID.

        Returns:
            True if deleted, False if not found.
        """
        logo_path = self.get_logo_path(user_id)
        if not logo_path:
            return False

        try:
            logo_path.unlink()
            logger.info("Logo deleted", extra={"user_id": user_id})
            return True
        except Exception as e:
            logger.error(
                "Failed to delete logo",
                extra={"user_id": user_id, "error": str(e)},
                exc_info=True,
            )
            return False

    def _validate_logo_file(self, file_content: bytes, filename: str) -> None:
        """Validate logo file.

        Args:
            file_content: File content as bytes.
            filename: Original filename.

        Raises:
            LogoUploadError: If validation fails.
        """
        # Check file extension
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_FORMATS:
            raise LogoUploadError(
                f"Invalid file format. Allowed: {', '.join(self.ALLOWED_FORMATS)}"
            )

        # Check file size
        if len(file_content) > self.MAX_FILE_SIZE:
            raise LogoUploadError(f"File size exceeds {self.MAX_FILE_SIZE / 1024 / 1024}MB limit")

        # Check minimum file size (empty file check)
        if len(file_content) == 0:
            raise LogoUploadError("File cannot be empty")

        # Validate image format and dimensions
        self._validate_image_dimensions(file_content, ext)

    def _validate_image_dimensions(self, file_content: bytes, ext: str) -> None:
        """Validate image dimensions.

        Args:
            file_content: Image file content.
            ext: File extension.

        Raises:
            LogoUploadError: If dimensions are invalid.
        """
        try:
            from io import BytesIO

            from PIL import Image

            img = Image.open(BytesIO(file_content))
            width, height = img.size

            if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
                raise LogoUploadError(
                    f"Image dimensions too small. Minimum {self.MIN_WIDTH}x{self.MIN_HEIGHT}px"
                )

        except ImportError:
            # PIL not available, skip dimension check (weasyprint will handle sizing)
            logger.debug("PIL not available, skipping dimension validation")
        except LogoUploadError:
            raise
        except Exception as e:
            # Log but don't fail - file may still be valid
            logger.warning(f"Could not validate image dimensions: {e}", exc_info=False)
