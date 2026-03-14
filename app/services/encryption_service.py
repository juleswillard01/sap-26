from __future__ import annotations

import base64
import logging
from typing import Annotated

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, Field

from app.config import Settings

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""

    pass


class EncryptionService(BaseModel):
    """Service for encrypting and decrypting sensitive data using Fernet."""

    settings: Annotated[Settings, Field(default_factory=Settings)]
    _fernet_keys: list[Fernet] = []

    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize encryption service with Fernet keys.

        Args:
            settings: Settings instance containing fernet_key(s).

        Raises:
            EncryptionError: If no valid Fernet key is configured.
        """
        super().__init__(settings=settings or Settings())

        if not self.settings.fernet_key:
            raise EncryptionError("fernet_key must be configured in settings")

        # Parse keys (support comma-separated for key rotation)
        keys_str = self.settings.fernet_key.split(",")
        self._fernet_keys = []

        for key_str in keys_str:
            key_str = key_str.strip()
            if not key_str:
                continue
            try:
                self._fernet_keys.append(Fernet(key_str.encode()))
            except Exception as e:
                logger.error("Invalid Fernet key format", exc_info=True)
                raise EncryptionError(f"Invalid Fernet key: {e}") from e

        if not self._fernet_keys:
            raise EncryptionError("At least one valid Fernet key must be configured")

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string using the primary Fernet key.

        Args:
            plaintext: The string to encrypt.

        Returns:
            Base64-encoded encrypted string.

        Raises:
            EncryptionError: If encryption fails.
        """
        if not plaintext:
            return ""

        try:
            # Use the first (primary) key for encryption
            ciphertext = self._fernet_keys[0].encrypt(plaintext.encode())
            return base64.b64encode(ciphertext).decode()
        except Exception as e:
            logger.error("Encryption failed", exc_info=True)
            raise EncryptionError(f"Encryption failed: {e}") from e

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string, trying all configured Fernet keys.

        Supports key rotation by trying keys in order until one succeeds.

        Args:
            ciphertext: Base64-encoded encrypted string.

        Returns:
            Decrypted plaintext string.

        Raises:
            EncryptionError: If decryption fails with all keys.
        """
        if not ciphertext:
            return ""

        try:
            # Decode from base64
            encrypted_bytes = base64.b64decode(ciphertext.encode())
        except Exception as e:
            logger.error("Invalid base64 format", exc_info=True)
            raise EncryptionError(f"Invalid base64 format: {e}") from e

        # Try decrypting with each key (for rotation support)
        last_error = None
        for i, fernet_key in enumerate(self._fernet_keys):
            try:
                plaintext = fernet_key.decrypt(encrypted_bytes).decode()
                return plaintext
            except InvalidToken as e:
                last_error = e
                logger.debug(f"Key {i} failed, trying next", exc_info=False)
                continue

        # No key worked
        logger.error("Decryption failed with all keys", exc_info=True)
        raise EncryptionError(
            "Decryption failed: no valid key found (may indicate key rotation issue)"
        ) from last_error
