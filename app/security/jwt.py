"""Standard RFC 7519 HS256 JSON Web Token encoding and decoding."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from uuid import UUID


def _base64url_encode(data: bytes) -> str:
    """Encode bytes to base64url string without trailing padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data_str: str) -> bytes:
    """Decode base64url string with appropriate padding."""
    padding = 4 - (len(data_str) % 4)
    if padding != 4:
        data_str += "=" * padding
    return base64.urlsafe_b64decode(data_str.encode("ascii"))


def create_access_token(
    user_id: UUID,
    secret_key: str,
    expires_delta: timedelta | None = None,
    algorithm: str = "HS256",
) -> str:
    """Create a signed HS256 JWT token for the authenticated user ID."""
    if algorithm != "HS256":
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    if not secret_key:
        raise ValueError("JWT secret key must not be empty.")

    now = int(datetime.now(timezone.utc).timestamp())
    exp = now + (int(expires_delta.total_seconds()) if expires_delta else 1440 * 60)

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": exp,
    }

    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(
    token: str,
    secret_key: str,
    algorithm: str = "HS256",
) -> UUID | None:
    """Decode and verify an HS256 JWT token, returning the user_id UUID or None if invalid."""
    if algorithm != "HS256" or not secret_key or not token:
        return None

    parts = token.strip().split(".")
    if len(parts) != 3:
        return None

    header_b64, payload_b64, signature_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    try:
        expected_sig = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        provided_sig = _base64url_decode(signature_b64)
        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        header = json.loads(_base64url_decode(header_b64).decode("utf-8"))
        if header.get("alg") != "HS256" or header.get("typ") != "JWT":
            return None

        payload = json.loads(_base64url_decode(payload_b64).decode("utf-8"))
        exp = payload.get("exp")
        if exp is None or int(exp) < int(datetime.now(timezone.utc).timestamp()):
            return None

        sub = payload.get("sub")
        if not sub:
            return None
        return UUID(str(sub))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None
