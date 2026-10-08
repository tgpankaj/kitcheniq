"""
KitchenIQ — Encryption Utility
Encrypts/decrypts integration tokens using Fernet.
"""
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()


def _get_fernet():
    key = os.getenv("TOKEN_ENCRYPTION_KEY")
    if not key:
        raise ValueError("TOKEN_ENCRYPTION_KEY not set in .env")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext):
    """Encrypt a string. Returns base64 string."""
    if plaintext is None:
        return None
    f = _get_fernet()
    return f.encrypt(str(plaintext).encode()).decode()


def decrypt(ciphertext):
    """Decrypt a Fernet token. Returns original string."""
    if ciphertext is None:
        return None
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception as e:
        print(f"[encryption] decrypt failed: {e}")
        return None
