import pytest
from app_backend.models.user import User, UserRole
from app_backend.api.dm import check_dm_permission

def test_admin_can_dm_anyone():
    admin = User(role=UserRole.ADMIN.value)
    normal = User(role=UserRole.NORMAL.value)
    mod = User(role=UserRole.MODERATOR.value)
    assert check_dm_permission(admin, normal) is True
    assert check_dm_permission(admin, mod) is True
    assert check_dm_permission(admin, admin) is True

def test_mod_can_dm_anyone():
    mod = User(role=UserRole.MODERATOR.value)
    normal = User(role=UserRole.NORMAL.value)
    admin = User(role=UserRole.ADMIN.value)
    assert check_dm_permission(mod, normal) is True
    assert check_dm_permission(mod, admin) is True
    assert check_dm_permission(mod, mod) is True

def test_normal_can_dm_normal():
    normal1 = User(role=UserRole.NORMAL.value)
    normal2 = User(role=UserRole.NORMAL.value)
    assert check_dm_permission(normal1, normal2) is True

def test_normal_can_dm_mod():
    normal = User(role=UserRole.NORMAL.value)
    mod = User(role=UserRole.MODERATOR.value)
    assert check_dm_permission(normal, mod) is True

def test_normal_cannot_dm_admin():
    normal = User(role=UserRole.NORMAL.value)
    admin = User(role=UserRole.ADMIN.value)
    assert check_dm_permission(normal, admin) is False
