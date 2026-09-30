"""Minimal signed bearer tokens and explicit token-budget accounting."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def issue_token(subject: str, secret: str, ttl_seconds: int = 86400) -> str:
    if not secret:
        raise ValueError("SOURCEMAP_JWT_SECRET must be configured before issuing tokens")
    payload = _b64(json.dumps({"sub": subject, "exp": int(time.time()) + ttl_seconds, "jti": secrets.token_hex(8)}, separators=(",", ":")).encode())
    signature = _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{signature}"


def verify_token(token: str, secret: str) -> dict:
    if not secret:
        raise ValueError("SOURCEMAP_JWT_SECRET is not configured")
    try:
        payload, signature = token.split(".", 1)
        expected = _b64(hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("Invalid bearer token")
        raw = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
        claims = json.loads(raw)
        if not claims.get("sub") or int(claims.get("exp", 0)) <= int(time.time()):
            raise ValueError("Expired bearer token")
        return claims
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid bearer token") from exc


def token_estimate(text: str) -> int:
    """Conservative fallback estimate when a provider tokenizer is unavailable."""
    return max(1, (len(text) + 3) // 4)
