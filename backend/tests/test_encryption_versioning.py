"""Tests for encryption key versioning — zero-downtime KEK rotation."""
import json
import base64
import os
import pytest
from unittest.mock import patch

from app.services.encryption import EncryptionService


@pytest.fixture
def service():
    """Standard encryption service with default settings."""
    return EncryptionService()


class TestKeyVersioning:
    """Key versioning in the wrapped DEK envelope."""

    def test_encrypt_dek_includes_version(self, service):
        """Wrapped DEK JSON contains a 'v' (version) field."""
        dek = service.generate_dek()
        wrapped = service.encrypt_dek(dek)
        envelope = json.loads(base64.b64decode(wrapped))
        assert "v" in envelope
        assert envelope["v"] == 1  # Default version

    def test_decrypt_dek_current_version(self, service):
        """Decrypt works with the current KEK version."""
        dek = service.generate_dek()
        wrapped = service.encrypt_dek(dek)
        decrypted = service.decrypt_dek(wrapped)
        assert decrypted == dek

    def test_decrypt_dek_no_version_field_legacy(self, service):
        """Old DEKs without 'v' field decrypt using current key (backward compat)."""
        dek = service.generate_dek()
        # Simulate legacy envelope (no "v" field)
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(service._kek)
        nonce = os.urandom(12)
        encrypted = aesgcm.encrypt(nonce, dek, None)
        legacy_envelope = {
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(encrypted).decode(),
        }
        wrapped = base64.b64encode(json.dumps(legacy_envelope).encode()).decode()

        decrypted = service.decrypt_dek(wrapped)
        assert decrypted == dek

    def test_encrypt_always_uses_current_version(self, service):
        """New encryptions always stamp current version number."""
        for _ in range(5):
            dek = service.generate_dek()
            wrapped = service.encrypt_dek(dek)
            envelope = json.loads(base64.b64decode(wrapped))
            assert envelope["v"] == service._current_version

    def test_decrypt_with_previous_key_version(self):
        """Encrypt with v1, switch to v2, decrypt still works via version map."""
        old_key = "old-master-key-for-testing-32b!"
        new_key = "new-master-key-for-testing-32b!"

        # Step 1: Encrypt with v1
        with patch.multiple("app.config.settings",
            ENCRYPTION_MASTER_KEY=old_key,
            ENCRYPTION_KEY_VERSION=1,
            ENCRYPTION_MASTER_KEY_V1="",
        ):
            svc_v1 = EncryptionService()
            dek = svc_v1.generate_dek()
            wrapped_v1 = svc_v1.encrypt_dek(dek)

        # Verify it's version 1
        envelope = json.loads(base64.b64decode(wrapped_v1))
        assert envelope["v"] == 1

        # Step 2: Rotate — new key is current, old key is V1
        with patch.multiple("app.config.settings",
            ENCRYPTION_MASTER_KEY=new_key,
            ENCRYPTION_KEY_VERSION=2,
            ENCRYPTION_MASTER_KEY_V1=old_key,
        ):
            svc_v2 = EncryptionService()

            # Decrypt old v1 DEK with new service
            decrypted = svc_v2.decrypt_dek(wrapped_v1)
            assert decrypted == dek

            # New encryptions use v2
            new_dek = svc_v2.generate_dek()
            wrapped_v2 = svc_v2.encrypt_dek(new_dek)
            envelope_v2 = json.loads(base64.b64decode(wrapped_v2))
            assert envelope_v2["v"] == 2

            # v2 decrypts correctly
            assert svc_v2.decrypt_dek(wrapped_v2) == new_dek
