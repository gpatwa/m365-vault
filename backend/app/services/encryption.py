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
    """Envelope encryption service using AES-256-GCM."""

    def __init__(self):
        master_key = settings.ENCRYPTION_MASTER_KEY.encode("utf-8")
        # Ensure master key is exactly 32 bytes
        if len(master_key) < 32:
            master_key = master_key.ljust(32, b"0")
        elif len(master_key) > 32:
            master_key = master_key[:32]
        self._kek = master_key

    def generate_dek(self) -> bytes:
        """Generate a random 256-bit Data Encryption Key."""
        return os.urandom(32)

    def encrypt_dek(self, dek: bytes) -> str:
        """Encrypt a DEK with the KEK (key wrapping).

        Returns base64-encoded JSON with nonce + ciphertext.
        """
        aesgcm = AESGCM(self._kek)
        nonce = os.urandom(12)
        encrypted = aesgcm.encrypt(nonce, dek, None)
        wrapped = {
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(encrypted).decode(),
            "wrapped_at": datetime.utcnow().isoformat(),
        }
        return base64.b64encode(json.dumps(wrapped).encode()).decode()

    def decrypt_dek(self, wrapped_dek: str) -> bytes:
        """Decrypt a wrapped DEK using the KEK."""
        wrapped = json.loads(base64.b64decode(wrapped_dek))
        aesgcm = AESGCM(self._kek)
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
