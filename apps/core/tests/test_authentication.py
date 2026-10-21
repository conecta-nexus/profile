from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

from django.conf import settings
from django.test import RequestFactory
import jwt
import pytest
from rest_framework.exceptions import AuthenticationFailed

from apps.core.authentication import (
    DEFAULT_JWT_AUDIENCE,
    DEFAULT_JWT_ISSUER,
    RS256JWTAuthentication,
    StatelessJWTUser,
)


@pytest.fixture
def keys(tmp_path, monkeypatch):
    from scripts.generate_keys import generate_rsa_key_pair

    priv, pub = generate_rsa_key_pair(tmp_path)
    priv_text = priv.read_text(encoding="utf-8")
    pub_text = pub.read_text(encoding="utf-8")
    monkeypatch.setenv("JWT_PUBLIC_KEY", pub_text)
    return priv_text, pub_text


def make_token(
    private_key: str,
    sub: str | None = None,
    email: str = "student@ufps.edu.co",
    role: str = "STUDENT",
    scope: str = "consent:write consent:read profile:student:read profile:student:write",
    expires_in_seconds: int = 900,
    iss: str = DEFAULT_JWT_ISSUER,
    aud: str | list[str] | None = None,
    token_type: str = "access",
    is_active: bool = True,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": iss,
        "aud": aud or [DEFAULT_JWT_AUDIENCE, "conecta-nexus-gateway"],
        "sub": sub or str(uuid.uuid4()),
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
        "type": token_type,
        "email": email,
        "role": role,
        "is_active": is_active,
        "scope": scope,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def test_stateless_jwt_user_attributes():
    user_id = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "email": "user@ufps.edu.co",
        "role": "STUDENT",
        "scope": "consent:read profile:student:read",
        "is_active": True,
    }
    user = StatelessJWTUser(payload)

    assert str(user.id) == user_id
    assert user.pk == user.id
    assert user.user_id == user.id
    assert user.email == "user@ufps.edu.co"
    assert user.role == "STUDENT"
    assert user.is_authenticated is True
    assert user.is_anonymous is False
    assert user.has_scope("consent:read") is True
    assert user.has_scope("consent:write") is False
    assert user.has_any_scope("consent:read", "other") is True
    assert user.has_any_scope("other1", "other2") is False
    assert user.has_all_scopes("consent:read", "profile:student:read") is True
    assert user.has_all_scopes("consent:read", "consent:write") is False
    assert "user@ufps.edu.co (STUDENT)" in str(user)


def test_rs256_authentication_success(keys):
    priv, _ = keys
    user_id = str(uuid.uuid4())
    token = make_token(priv, sub=user_id, role="STUDENT")

    factory = RequestFactory()
    request = factory.get("/api/v1/profiles/students/me", HTTP_AUTHORIZATION=f"Bearer {token}")

    auth = RS256JWTAuthentication()
    user, payload = auth.authenticate(request)

    assert isinstance(user, StatelessJWTUser)
    assert str(user.id) == user_id
    assert user.role == "STUDENT"
    assert payload["sub"] == user_id


def test_rs256_authentication_no_header():
    factory = RequestFactory()
    request = factory.get("/api/v1/profiles/students/me")

    auth = RS256JWTAuthentication()
    assert auth.authenticate(request) is None


def test_rs256_authentication_non_bearer_header():
    factory = RequestFactory()
    request = factory.get("/api/v1/profiles/students/me", HTTP_AUTHORIZATION="Basic dXNlcjpwYXNz")

    auth = RS256JWTAuthentication()
    assert auth.authenticate(request) is None


def test_rs256_authentication_malformed_header():
    factory = RequestFactory()
    auth = RS256JWTAuthentication()

    with pytest.raises(AuthenticationFailed) as exc:
        auth.authenticate(factory.get("/", HTTP_AUTHORIZATION="Bearer"))
    assert exc.value.get_codes() == "invalid_header"

    with pytest.raises(AuthenticationFailed) as exc:
        auth.authenticate(factory.get("/", HTTP_AUTHORIZATION="Bearer one two three"))
    assert exc.value.get_codes() == "invalid_header"


def test_rs256_authentication_expired_token(keys):
    priv, _ = keys
    token = make_token(priv, expires_in_seconds=-60)

    factory = RequestFactory()
    request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
    auth = RS256JWTAuthentication()

    with pytest.raises(AuthenticationFailed) as exc:
        auth.authenticate(request)
    assert exc.value.get_codes() == "token_expired"


def test_rs256_authentication_invalid_issuer(keys):
    priv, _ = keys
    token = make_token(priv, iss="https://evil.issuer.com")

    factory = RequestFactory()
    request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
    auth = RS256JWTAuthentication()

    with pytest.raises(AuthenticationFailed) as exc:
        auth.authenticate(request)
    assert exc.value.get_codes() == "invalid_issuer"


def test_rs256_authentication_invalid_audience(keys):
    priv, _ = keys
    token = make_token(priv, aud="untrusted-service")

    factory = RequestFactory()
    request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
    auth = RS256JWTAuthentication()

    with pytest.raises(AuthenticationFailed) as exc:
        auth.authenticate(request)
    assert exc.value.get_codes() == "invalid_audience"


def test_rs256_authentication_invalid_token_type(keys):
    priv, _ = keys
    token = make_token(priv, token_type="refresh")

    factory = RequestFactory()
    request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
    auth = RS256JWTAuthentication()

    with pytest.raises(AuthenticationFailed) as exc:
        auth.authenticate(request)
    assert exc.value.get_codes() == "invalid_token_type"


def test_rs256_authentication_inactive_user(keys):
    priv, _ = keys
    token = make_token(priv, is_active=False)

    factory = RequestFactory()
    request = factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
    auth = RS256JWTAuthentication()

    with pytest.raises(AuthenticationFailed) as exc:
        auth.authenticate(request)
    assert exc.value.get_codes() == "user_inactive"
