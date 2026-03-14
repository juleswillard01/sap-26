from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from app.services.encryption_service import EncryptionError, EncryptionService


@pytest.fixture()
def valid_key() -> str:
    """Generate a valid Fernet key for testing."""
    return Fernet.generate_key().decode()


@pytest.fixture()
def encryption_service(valid_key: str, monkeypatch: pytest.MonkeyPatch) -> EncryptionService:
    """Create an encryption service with a test key."""
    monkeypatch.setenv("FERNET_KEY", valid_key)
    from app.config import Settings

    settings = Settings()
    return EncryptionService(settings=settings)


class TestEncryptionService:
    """Tests for the EncryptionService."""

    def test_encrypt_decrypt_roundtrip(self, encryption_service: EncryptionService) -> None:
        """Test that encrypting and decrypting returns the original plaintext."""
        plaintext = "This is a secret message"

        ciphertext = encryption_service.encrypt(plaintext)
        decrypted = encryption_service.decrypt(ciphertext)

        assert decrypted == plaintext
        assert ciphertext != plaintext

    def test_encrypt_empty_string(self, encryption_service: EncryptionService) -> None:
        """Test that encrypting an empty string returns an empty string."""
        ciphertext = encryption_service.encrypt("")

        assert ciphertext == ""

    def test_decrypt_empty_string(self, encryption_service: EncryptionService) -> None:
        """Test that decrypting an empty string returns an empty string."""
        decrypted = encryption_service.decrypt("")

        assert decrypted == ""

    def test_decrypt_with_wrong_key_raises(
        self, valid_key: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that decrypting with a wrong key raises EncryptionError."""
        # Create encryption service with first key
        monkeypatch.setenv("FERNET_KEY", valid_key)
        from app.config import Settings

        settings = Settings()
        service1 = EncryptionService(settings=settings)

        # Encrypt with first key
        ciphertext = service1.encrypt("secret message")

        # Create encryption service with different key
        different_key = Fernet.generate_key().decode()
        monkeypatch.setenv("FERNET_KEY", different_key)
        settings2 = Settings()
        service2 = EncryptionService(settings=settings2)

        # Try to decrypt with wrong key
        with pytest.raises(EncryptionError):
            service2.decrypt(ciphertext)

    def test_key_rotation_decrypt_with_old_key(
        self, valid_key: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that decryption works with key rotation (old key in list)."""
        # Create service with first key
        monkeypatch.setenv("FERNET_KEY", valid_key)
        from app.config import Settings

        settings = Settings()
        service1 = EncryptionService(settings=settings)
        plaintext = "secret message"

        # Encrypt with first key
        ciphertext = service1.encrypt(plaintext)

        # Generate second key (simulating key rotation)
        new_key = Fernet.generate_key().decode()

        # Create service with both keys (new key first, old key second)
        monkeypatch.setenv("FERNET_KEY", f"{new_key},{valid_key}")
        settings_rotated = Settings()
        service_rotated = EncryptionService(settings=settings_rotated)

        # Should decrypt successfully with old key
        decrypted = service_rotated.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_encrypt_various_data_types(self, encryption_service: EncryptionService) -> None:
        """Test encrypting various string data types."""
        test_cases = [
            "simple string",
            "string with special chars: !@#$%^&*()",
            "unicode: café, 日本語, émoji 🔒",
            "123456789",
            'json: {"key": "value"}',
        ]

        for plaintext in test_cases:
            ciphertext = encryption_service.encrypt(plaintext)
            decrypted = encryption_service.decrypt(ciphertext)
            assert decrypted == plaintext, f"Failed for: {plaintext}"

    def test_encryption_produces_different_ciphertexts(
        self, encryption_service: EncryptionService
    ) -> None:
        """Test that encrypting the same plaintext multiple times produces different ciphertexts."""
        plaintext = "test message"

        ciphertext1 = encryption_service.encrypt(plaintext)
        ciphertext2 = encryption_service.encrypt(plaintext)

        # Fernet includes timestamp and nonce, so ciphertexts should differ
        assert ciphertext1 != ciphertext2

        # But both should decrypt to the same plaintext
        assert encryption_service.decrypt(ciphertext1) == plaintext
        assert encryption_service.decrypt(ciphertext2) == plaintext

    def test_invalid_base64_raises(self, encryption_service: EncryptionService) -> None:
        """Test that decrypting invalid base64 raises EncryptionError."""
        with pytest.raises(EncryptionError):
            encryption_service.decrypt("not-valid-base64!")

    def test_initialization_without_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that initialization without fernet_key raises EncryptionError."""
        monkeypatch.setenv("FERNET_KEY", "")
        from app.config import Settings

        settings = Settings()
        with pytest.raises(EncryptionError):
            EncryptionService(settings=settings)

    def test_initialization_with_invalid_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that initialization with invalid key format raises EncryptionError."""
        monkeypatch.setenv("FERNET_KEY", "invalid-key-format")
        from app.config import Settings

        settings = Settings()
        with pytest.raises(EncryptionError):
            EncryptionService(settings=settings)
