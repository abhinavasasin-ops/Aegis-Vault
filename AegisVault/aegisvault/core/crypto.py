"""Cryptographic primitives for AegisVault.

- Password hashing: SHA-256(salt || password) for VERIFICATION only.
- Key derivation:   PBKDF2-HMAC-SHA256, 200k iterations.
- Encryption:       AES-256-GCM, random 12-byte nonce per item.
"""
from __future__ import annotations
import hashlib
from typing import Tuple
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes

from ..config import PBKDF2_ITERS, KEY_LEN, SALT_LEN, GCM_IV_LEN


# --- Password verification hashing -----------------------------------------

def new_salt(n: int = SALT_LEN) -> bytes:
    return get_random_bytes(n)


def hash_password(password: str, salt: bytes) -> str:
    h = hashlib.sha256()
    h.update(salt)
    h.update(password.encode("utf-8"))
    return h.hexdigest()


def verify_password(password: str, salt: bytes, expected_hex: str) -> bool:
    import hmac
    return hmac.compare_digest(hash_password(password, salt), expected_hex)


# --- Key derivation ---------------------------------------------------------

def derive_key(password: str, kdf_salt: bytes) -> bytes:
    return PBKDF2(
        password.encode("utf-8"),
        kdf_salt,
        dkLen=KEY_LEN,
        count=PBKDF2_ITERS,
        hmac_hash_module=SHA256,
    )


# --- AES-256-GCM ------------------------------------------------------------

def encrypt(key: bytes, plaintext: bytes) -> Tuple[bytes, bytes]:
    """Returns (iv, ciphertext_with_tag). Tag is appended (last 16 bytes)."""
    iv = get_random_bytes(GCM_IV_LEN)
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    ct, tag = cipher.encrypt_and_digest(plaintext)
    return iv, ct + tag


def decrypt(key: bytes, iv: bytes, blob: bytes) -> bytes:
    ct, tag = blob[:-16], blob[-16:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    return cipher.decrypt_and_verify(ct, tag)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()
