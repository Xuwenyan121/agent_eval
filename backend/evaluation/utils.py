"""Utility functions for the evaluation package."""

import os
from cryptography.fernet import Fernet


def _get_fernet_key() -> bytes:
    """Get or generate Fernet encryption key."""
    key = os.getenv("FERNET_KEY")
    if key:
        return key.encode()
    # Dev-only: generate a deterministic key (NOT for production)
    return Fernet.generate_key()


def encrypt_key(plain_text: str) -> str:
    """Encrypt an API key for storage."""
    f = Fernet(_get_fernet_key())
    return f.encrypt(plain_text.encode()).decode()


def decrypt_key(encrypted_text: str) -> str:
    """Decrypt a stored API key."""
    f = Fernet(_get_fernet_key())
    return f.decrypt(encrypted_text.encode()).decode()
