"""JWT access-token helpers for device sessions at the edge.

Uses HS256 with the standard library only so the edge can issue short-lived
Bearer tokens after a successful ``device_id`` + ``mac_address`` sign-in without
adding extra dependencies.
"""
import base64
import hashlib
import hmac
import json
import time
from typing import Any


class TokenService:
    """Creates and validates edge-issued JWT access tokens."""

    @staticmethod
    def _b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64url_decode(data: str) -> bytes:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)

    @classmethod
    def create_access_token(cls, device_id: str, secret: str, ttl_seconds: int) -> tuple[str, int]:
        """Build a signed JWT for the authenticated device."""
        now = int(time.time())
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "device_id": device_id,
            "iat": now,
            "exp": now + ttl_seconds,
        }
        encoded_header = cls._b64url_encode(json.dumps(header, separators=(",", ":")).encode())
        encoded_payload = cls._b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{encoded_header}.{encoded_payload}".encode()
        signature = cls._b64url_encode(
            hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        )
        return f"{encoded_header}.{encoded_payload}.{signature}", ttl_seconds

    @classmethod
    def decode_access_token(cls, token: str, secret: str) -> str | None:
        """Return ``device_id`` when the token is valid; otherwise ``None``."""
        try:
            encoded_header, encoded_payload, encoded_signature = token.split(".", 2)
        except ValueError:
            return None

        signing_input = f"{encoded_header}.{encoded_payload}".encode()
        expected_signature = cls._b64url_encode(
            hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        )
        if not hmac.compare_digest(expected_signature, encoded_signature):
            return None

        try:
            payload: dict[str, Any] = json.loads(cls._b64url_decode(encoded_payload))
        except (json.JSONDecodeError, ValueError):
            return None

        device_id = payload.get("device_id")
        exp = payload.get("exp")
        if not device_id or not isinstance(exp, int) or exp < int(time.time()):
            return None

        return str(device_id)
