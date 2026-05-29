"""AuthService username pool."""
from app.services.auth_service import auth_service


def test_username_pool_dimensions():
    assert auth_service.total_permutations > 0
    assert auth_service.max_users >= 1
    assert len(auth_service.adjectives) >= 1
    assert len(auth_service.nouns) >= 1
