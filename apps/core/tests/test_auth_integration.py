from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

import jwt
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.authentication import (
    DEFAULT_JWT_AUDIENCE,
    DEFAULT_JWT_ISSUER,
    RS256JWTAuthentication,
)

pytestmark = pytest.mark.django_db


def test_auth_microservice_token_verification():
    """Verify that tokens signed by the auth microservice private key are verified in profile."""
    auth_private_key_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "auth" / "certs" / "jwt_private.pem"
    if not auth_private_key_path.exists():
        pytest.skip("Auth microservice private key not found at ../auth/certs/jwt_private.pem")

    priv_pem = auth_private_key_path.read_text(encoding="utf-8")
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Token payload matches exactly what auth create_access_token produces
    payload = {
        "iss": DEFAULT_JWT_ISSUER,
        "aud": [DEFAULT_JWT_AUDIENCE, "conecta-nexus-gateway"],
        "sub": user_id,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "type": "access",
        "email": "1152375@ufps.edu.co",
        "role": "STUDENT",
        "is_active": True,
        "scope": "consent:write consent:read profile:student:read profile:student:write profile:company:read_public challenge:read application:create application:read_own",
    }
    token = jwt.encode(payload, priv_pem, algorithm="RS256")

    # 1. Test Authentication backend
    from django.test import RequestFactory

    rf = RequestFactory()
    req = rf.get("/api/v1/profiles/consent/me", HTTP_AUTHORIZATION=f"Bearer {token}")

    auth = RS256JWTAuthentication()
    user, decoded = auth.authenticate(req)

    assert user is not None
    assert str(user.id) == user_id
    assert user.email == "1152375@ufps.edu.co"
    assert user.role == "STUDENT"
    assert user.has_scope("consent:write") is True
    assert user.has_scope("consent:read") is True

    # 2. Test Consent endpoints using APIClient
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # Register consent
    post_res = client.post(
        "/api/v1/profiles/consent",
        {"is_accepted": True, "policy_version": "v1.0-2026"},
        format="json",
        HTTP_X_FORWARDED_FOR="190.158.12.34",
        HTTP_USER_AGENT="ConectaNexusTest/1.0",
    )
    assert post_res.status_code == status.HTTP_201_CREATED
    assert post_res.data["user_id"] == user_id

    # Retrieve consent
    get_res = client.get("/api/v1/profiles/consent/me")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.data["user_id"] == user_id
    assert get_res.data["is_accepted"] is True
