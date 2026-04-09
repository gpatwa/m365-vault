"""AES-256-GCM envelope encryption service.

Implements a two-layer encryption scheme similar to Rubrik:
- Data Encryption Key (DEK): Unique per snapshot, encrypts actual backup data
- Key Encryption Key (KEK): Encrypts/wraps DEKs, derived from master key
"""
import os
import json
import base64
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings


class EncryptionService:
    """Envelope encryption service using AES-256-GCM.

    Supports key versioning for zero-downtime master key rotation:
    - encrypt_dek always uses the current version (ENCRYPTION_KEY_VERSION)
    - decrypt_dek reads the "v" field and selects the correct KEK
    - Old DEKs without "v" field use the current key (backward compat)

    Rotation workflow:
    1. Set new ENCRYPTION_MASTER_KEY, move old to ENCRYPTION_MASTER_KEY_V1
    2. Increment ENCRYPTION_KEY_VERSION
    3. New wraps use new key, old unwraps still work via version map
    """

    def __init__(self):
        self._current_version = getattr(settings, "ENCRYPTION_KEY_VERSION", 1)
        self._kek_versions = {}

        # Current key
        self._kek = self._normalize_key(settings.ENCRYPTION_MASTER_KEY)
        self._kek_versions[self._current_version] = self._kek

        # Previous key (for decrypt-only during rotation)
        prev_key = getattr(settings, "ENCRYPTION_MASTER_KEY_V1", "")
        if prev_key:
            prev_version = self._current_version - 1
            self._kek_versions[prev_version] = self._normalize_key(prev_key)

    @staticmethod
    def _normalize_key(key_str: str) -> bytes:
        """Ensure key is exactly 32 bytes for AES-256."""
        key_bytes = key_str.encode("utf-8")
        if len(key_bytes) < 32:
            key_bytes = key_bytes.ljust(32, b"0")
        elif len(key_bytes) > 32:
            key_bytes = key_bytes[:32]
        return key_bytes

    def _get_kek(self, version: int = None) -> bytes:
        """Get KEK for a specific version, falling back to current."""
        if version is not None and version in self._kek_versions:
            return self._kek_versions[version]
        return self._kek

    def generate_dek(self) -> bytes:
        """Generate a random 256-bit Data Encryption Key."""
        return os.urandom(32)

    def encrypt_dek(self, dek: bytes) -> str:
        """Encrypt a DEK with the current KEK (key wrapping).

        Returns base64-encoded JSON with version, nonce + ciphertext.
        """
        aesgcm = AESGCM(self._kek)
        nonce = os.urandom(12)
        encrypted = aesgcm.encrypt(nonce, dek, None)
        wrapped = {
            "v": self._current_version,
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(encrypted).decode(),
            "wrapped_at": datetime.utcnow().isoformat(),
        }
        return base64.b64encode(json.dumps(wrapped).encode()).decode()

    def decrypt_dek(self, wrapped_dek: str) -> bytes:
        """Decrypt a wrapped DEK using the versioned KEK.

        Reads the "v" field to select the correct key. Legacy DEKs
        without a "v" field use the current key (backward compat).
        """
        wrapped = json.loads(base64.b64decode(wrapped_dek))
        version = wrapped.get("v")  # None for legacy DEKs
        kek = self._get_kek(version)
        aesgcm = AESGCM(kek)
        nonce = base64.b64decode(wrapped["nonce"])
        ciphertext = base64.b64decode(wrapped["ciphertext"])
        return aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_data(self, data: bytes, dek: bytes) -> bytes:
        """Encrypt data using a DEK.

        Returns: nonce (12 bytes) + ciphertext (data + 16 byte tag)
        """
        aesgcm = AESGCM(dek)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext

    def decrypt_data(self, encrypted_data: bytes, dek: bytes) -> bytes:
        """Decrypt data using a DEK.

        Expects: nonce (12 bytes) + ciphertext
        """
        aesgcm = AESGCM(dek)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return aesgcm.decrypt(nonce, ciphertext, None)

    def encrypt_string(self, plaintext: str) -> str:
        """Convenience: encrypt a string (e.g., client secrets) with KEK."""
        dek = self._kek  # Use KEK directly for simple string encryption
        encrypted = self.encrypt_data(plaintext.encode("utf-8"), dek)
        return base64.b64encode(encrypted).decode()

    def decrypt_string(self, ciphertext: str) -> str:
        """Convenience: decrypt a string encrypted with encrypt_string."""
        encrypted = base64.b64decode(ciphertext)
        decrypted = self.decrypt_data(encrypted, self._kek)
        return decrypted.decode("utf-8")


encryption_service = EncryptionService()
