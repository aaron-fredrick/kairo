"""HMAC service authentication."""
from shared.service_auth import sign_headers, verify_headers


def test_sign_and_verify_roundtrip():
    body = b'{"host":"app","port":8000}'
    headers = sign_headers("test-secret", "POST", "/api/v1/register", body)
    assert verify_headers("test-secret", "POST", "/api/v1/register", body, headers)


def test_reject_wrong_secret():
    headers = sign_headers("a", "GET", "/api/v1/health", b"")
    assert not verify_headers("b", "GET", "/api/v1/health", b"", headers)
