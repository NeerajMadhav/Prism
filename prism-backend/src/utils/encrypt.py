"""AES-256-GCM encrypt/decrypt for credentials at rest."""

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.config.settings import get_settings


def _get_key() -> bytes:
    """Decode the 64-hex-char ENCRYPTION_KEY into 32 bytes."""
    key_hex = get_settings().encryption_key
    return bytes.fromhex(key_hex)


def aes_encrypt(plaintext: str) -> str:
    """Encrypt plaintext; return nonce+ciphertext as hex."""
    key = _get_key()
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return (nonce + ciphertext).hex()


def aes_decrypt(token_hex: str) -> str:
    """Decrypt hex token produced by aes_encrypt."""
    raw = bytes.fromhex(token_hex)
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(_get_key())
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
