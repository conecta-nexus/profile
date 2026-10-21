from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

import jwt
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.consents.models import DataConsent
from apps.core.authentication import DEFAULT_JWT_AUDIENCE, DEFAULT_JWT_ISSUER

pytestmark = pytest.mark.django_db


@pytest.fixture
def keys():
    priv = Path("certs/jwt_private.pem").read_text()
    pub = Path("certs/jwt_public.pem").read_text()
    return priv, pub


def generate_test_token(
    private_key: str,
    user_id: uuid.UUID | str,
    role: str = "STUDENT",
    scope: str = "consent:write consent:read profile:student:read profile:student:write",
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": DEFAULT_JWT_ISSUER,
        "aud": [DEFAULT_JWT_AUDIENCE, "conecta-nexus-gateway"],
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=15)).timestamp()),
        "type": "access",
        "email": "testuser@ufps.edu.co",
        "role": role,
        "is_active": True,
        "scope": scope,
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


def test_consent_registration_requires_authentication():
    client = APIClient()
    response = client.post("/api/v1/profiles/consent", {"is_accepted": True}, format="json")
    assert response.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}


def test_consent_registration_requires_consent_write_scope(keys):
    priv, _ = keys
    user_id = uuid.uuid4()
    # Missing consent:write scope
    token = generate_test_token(priv, user_id=user_id, scope="profile:student:read")

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.post("/api/v1/profiles/consent", {"is_accepted": True}, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_consent_registration_success(keys):
    priv, _ = keys
    user_id = uuid.uuid4()
    token = generate_test_token(priv, user_id=user_id)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.post(
        "/api/v1/profiles/consent",
        {"is_accepted": True, "policy_version": "v1.0-2026"},
        format="json",
        HTTP_X_FORWARDED_FOR="200.21.5.14",
        HTTP_USER_AGENT="Mozilla/5.0 TestBrowser/1.0",
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.data
    assert data["user_id"] == str(user_id)
    assert data["policy_version"] == "v1.0-2026"
    assert data["is_accepted"] is True
    assert "accepted_at" in data

    # Verify DB persistence
    consent_record = DataConsent.objects.get(user_id=user_id)
    assert consent_record.ip_address == "200.21.5.14"
    assert consent_record.user_agent == "Mozilla/5.0 TestBrowser/1.0"


def test_consent_registration_rejects_false_acceptance(keys):
    priv, _ = keys
    user_id = uuid.uuid4()
    token = generate_test_token(priv, user_id=user_id)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    response = client.post(
        "/api/v1/profiles/consent",
        {"is_accepted": False},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "is_accepted" in response.data["error"]["details"]


def test_consent_status_returns_latest_record(keys):
    priv, _ = keys
    user_id = uuid.uuid4()

    # Pre-create a consent
    DataConsent.objects.create(
        user_id=user_id,
        policy_version="v1.0-2026",
        is_accepted=True,
        ip_address="192.168.1.1",
        user_agent="Agent 1",
    )

    token = generate_test_token(priv, user_id=user_id)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.get("/api/v1/profiles/consent/me")
    assert response.status_code == status.HTTP_200_OK
    assert response.data["user_id"] == str(user_id)
    assert response.data["is_accepted"] is True


def test_consent_status_not_found_when_no_record(keys):
    priv, _ = keys
    user_id = uuid.uuid4()
    token = generate_test_token(priv, user_id=user_id)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = client.get("/api/v1/profiles/consent/me")
    assert response.status_code == status.HTTP_404_NOT_FOUND
