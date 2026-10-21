from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

import jwt
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.consents.models import DataConsent
from apps.core.authentication import DEFAULT_JWT_AUDIENCE, DEFAULT_JWT_ISSUER
from apps.students.models import StudentProfile

pytestmark = pytest.mark.django_db


def make_token(
    user_id: uuid.UUID | str,
    role: str = "ADMIN",
    scope: str = "profile:read_internal profile:read_all",
) -> str:
    priv_pem = Path("certs/jwt_private.pem").read_text(encoding="utf-8")
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
        "email": "service@conectanexus.internal",
        "role": role,
        "is_active": True,
        "scope": scope,
    }
    return jwt.encode(payload, priv_pem, algorithm="RS256")


def create_student(user_id, semester=7, email="student@ufps.edu.co", phone="3001234567"):
    return StudentProfile.objects.create(
        user_id=user_id,
        full_name="Carlos Estudiante",
        student_code=uuid.uuid4().hex[:10],
        academic_program="Ingeniería de Sistemas",
        current_semester=semester,
        contact_email=email,
        contact_phone=phone,
    )


def test_eligibility_requires_authentication():
    client = APIClient()
    user_id = uuid.uuid4()
    res = client.get(f"/api/v1/profiles/internal/{user_id}/eligibility")
    assert res.status_code in {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN}


def test_eligibility_rejects_unauthorized_scope():
    caller_id = uuid.uuid4()
    # Student role without profile:read_internal
    token = make_token(caller_id, role="STUDENT", scope="profile:student:read")

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    user_id = uuid.uuid4()
    res = client.get(f"/api/v1/profiles/internal/{user_id}/eligibility")
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_eligibility_rejects_invalid_uuid():
    token = make_token(uuid.uuid4(), role="ADMIN")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    res = client.get("/api/v1/profiles/internal/not-a-valid-uuid/eligibility")
    assert res.status_code == status.HTTP_400_BAD_REQUEST


def test_eligibility_not_found_when_student_does_not_exist():
    token = make_token(uuid.uuid4(), role="ADMIN")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    non_existent_user = uuid.uuid4()
    res = client.get(f"/api/v1/profiles/internal/{non_existent_user}/eligibility")
    assert res.status_code == status.HTTP_404_NOT_FOUND


def test_eligibility_success_eligible_student():
    student_id = uuid.uuid4()
    create_student(student_id, semester=7, email="carlos@ufps.edu.co", phone="3109876543")

    DataConsent.objects.create(
        user_id=student_id,
        policy_version="v1.0-2026",
        is_accepted=True,
        ip_address="127.0.0.1",
        user_agent="Agent",
    )

    token = make_token(uuid.uuid4(), role="SERVICE", scope="profile:read_internal")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    res = client.get(f"/api/v1/profiles/internal/{student_id}/eligibility")
    assert res.status_code == status.HTTP_200_OK

    data = res.data
    assert data["user_id"] == str(student_id)
    assert data["is_eligible"] is True
    assert data["current_semester"] == 7
    assert data["has_consent"] is True
    assert data["contact_info"] == {
        "email": "carlos@ufps.edu.co",
        "phone": "3109876543",
    }


def test_eligibility_ineligible_when_consent_missing():
    student_id = uuid.uuid4()
    create_student(student_id, semester=8, email="carlos@ufps.edu.co", phone=None)

    # No DataConsent created for student_id

    token = make_token(uuid.uuid4(), role="ADMIN")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    res = client.get(f"/api/v1/profiles/internal/{student_id}/eligibility")
    assert res.status_code == status.HTTP_200_OK

    data = res.data
    assert data["user_id"] == str(student_id)
    assert data["is_eligible"] is False
    assert data["has_consent"] is False
    assert data["current_semester"] == 8
    assert data["contact_info"]["email"] == "carlos@ufps.edu.co"


def test_eligibility_allowed_with_admin_role_without_scope():
    student_id = uuid.uuid4()
    create_student(student_id, semester=6)

    token = make_token(uuid.uuid4(), role="ADMIN", scope="")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    res = client.get(f"/api/v1/profiles/internal/{student_id}/eligibility")
    assert res.status_code == status.HTTP_200_OK
