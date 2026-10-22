from unittest.mock import MagicMock
import uuid

import pytest

from apps.core.authentication import StatelessJWTUser
from apps.core.permissions import (
    HasRequiredScopes,
    HasScope,
    IsAdmin,
    IsAuthenticatedStateless,
    IsCompany,
    IsStudent,
)


def make_mock_user(role="STUDENT", scopes=None, is_auth=True):
    user = MagicMock()
    user.is_authenticated = is_auth
    user.id = uuid.uuid4() if is_auth else None
    user.role = role
    user.scopes = scopes or []
    user.has_scope = lambda s: s in user.scopes
    user.has_all_scopes = lambda *sc: all(s in user.scopes for s in sc)
    return user


def test_is_authenticated_stateless():
    perm = IsAuthenticatedStateless()
    req = MagicMock(user=make_mock_user(is_auth=True))
    assert perm.has_permission(req, None) is True

    req_anon = MagicMock(user=make_mock_user(is_auth=False))
    assert perm.has_permission(req_anon, None) is False


def test_role_permissions():
    student_user = make_mock_user(role="STUDENT")
    company_user = make_mock_user(role="COMPANY")
    admin_user = make_mock_user(role="ADMIN")

    is_student = IsStudent()
    is_company = IsCompany()
    is_admin = IsAdmin()

    assert is_student.has_permission(MagicMock(user=student_user), None) is True
    assert is_student.has_permission(MagicMock(user=company_user), None) is False

    assert is_company.has_permission(MagicMock(user=company_user), None) is True
    assert is_company.has_permission(MagicMock(user=student_user), None) is False

    assert is_admin.has_permission(MagicMock(user=admin_user), None) is True
    assert is_admin.has_permission(MagicMock(user=student_user), None) is False


def test_has_scope_permission():
    user = make_mock_user(scopes=["consent:write", "profile:student:write"])
    req = MagicMock(user=user)

    perm_write = HasScope("consent:write")()
    perm_read = HasScope("consent:read")()

    assert perm_write.has_permission(req, None) is True
    assert perm_read.has_permission(req, None) is False


def test_has_required_scopes_permission():
    user = make_mock_user(scopes=["profile:read", "profile:write"])
    req = MagicMock(user=user)
    view = MagicMock(required_scopes=["profile:read", "profile:write"])

    perm = HasRequiredScopes()
    assert perm.has_permission(req, view) is True

    view_extra = MagicMock(required_scopes=["profile:read", "profile:admin"])
    assert perm.has_permission(req, view_extra) is False
