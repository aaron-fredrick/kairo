"""JWT and password helpers."""
from datetime import timedelta

from app_backend.auth.jwt import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = get_password_hash("secret")
    assert verify_password("secret", hashed)
    assert not verify_password("wrong", hashed)


def test_create_and_decode_token():
    token = create_access_token({"sub": "test-user", "role": "normal"})
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "test-user"


def test_decode_invalid_token():
    assert decode_access_token("not-a-jwt") is None


def test_token_with_custom_expiry():
    token = create_access_token({"sub": "u"}, expires_delta=timedelta(minutes=5))
    assert decode_access_token(token) is not None
