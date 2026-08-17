"""Secure password hashing and verification using OWASP-compliant PBKDF2-HMAC-SHA256."""

from __future__ import annotations

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000
SALT_BYTES = 16


def hash_password(plain_password: str) -> str:
    """Hash a plain text password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    if not plain_password:
        raise ValueError("Password cannot be empty.")
    salt = secrets.token_bytes(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        ITERATIONS,
    )
    return f"{ALGORITHM}${ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored PBKDF2 hash using constant-time comparison."""
    if not plain_password or not hashed_password:
        return False
    parts = hashed_password.split("$")
    if len(parts) != 4:
        return False
    algorithm, iterations_str, salt_hex, hash_hex = parts
    if algorithm != ALGORITHM:
        return False
    try:
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
    except (ValueError, TypeError):
        return False

    computed_hash = hashlib.pbkdf2_hmac(
        "sha256",
        plain_password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(computed_hash, expected_hash)
