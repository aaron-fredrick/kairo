"""
HMAC authentication for service-to-service calls (app ↔ register).

Uses REGISTER_SYSTEM_KEY as the shared secret for registration;
per-server heartbeat secrets are issued after registration.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from typing import Mapping

HEADER_TIMESTAMP = "X-Kairo-Timestamp"
HEADER_SIGNATURE = "X-Kairo-Signature"
MAX_SKEW_SECONDS = 60


def _signing_payload(timestamp: str, method: str, path: str, body: bytes) -> bytes:
    return f"{timestamp}\n{method.upper()}\n{path}\n".encode() + body


def sign_headers(
    secret: str,
    method: str,
    path: str,
    body: bytes = b"",
    *,
    timestamp: int | None = None,
) -> dict[str, str]:
    ts = str(timestamp if timestamp is not None else int(time.time()))
    payload = _signing_payload(ts, method, path, body)
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return {HEADER_TIMESTAMP: ts, HEADER_SIGNATURE: digest}


def verify_headers(
    secret: str,
    method: str,
    path: str,
    body: bytes,
    headers: Mapping[str, str],
) -> bool:
    ts = headers.get(HEADER_TIMESTAMP) or headers.get(HEADER_TIMESTAMP.lower())
    sig = headers.get(HEADER_SIGNATURE) or headers.get(HEADER_SIGNATURE.lower())
    if not ts or not sig:
        return False
    try:
        ts_int = int(ts)
    except ValueError:
        return False
    if abs(int(time.time()) - ts_int) > MAX_SKEW_SECONDS:
        return False
    expected = sign_headers(secret, method, path, body, timestamp=ts_int)[HEADER_SIGNATURE]
    return hmac.compare_digest(expected, sig)
