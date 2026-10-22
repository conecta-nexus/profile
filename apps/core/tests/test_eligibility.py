from types import SimpleNamespace
from unittest.mock import patch
import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.consents.models import DataConsent
from apps.core.authentication import StatelessJWTUser
from apps.students.models import StudentProfile

pytestmark = pytest.mark.django_db


def eligibility_url(user_id: uuid.UUID | str) -> str:
    """Build the internal eligibility endpoint URL."""
    return f"/api/v1/profiles/internal/{user_id}/eligibility"


def authenticated_client(
    *,
    role: str = "SERVICE",
    scopes: tuple[str, ...] = ("profile:read_internal",),
) -> APIClient:
    """Create a client with the stateless principal expected by Profile."""
    payload = {
        "sub": str(uuid.uuid4()),
        "role": role,
        "scope": " ".join(scopes),
        "is_active": True,
    }
    user = StatelessJWTUser(payload)
    client = APIClient()
    client.force_authenticate(user=user, token=payload)
    return client


def create_student(
    user_id: uuid.UUID,
    *,
    semester: int = 7,
    email: str = "student@ufps.edu.co",
    phone: str | None = "3001234567",
) -> StudentProfile:
    """Persist a valid student profile for endpoint tests."""
    return StudentProfile.objects.create(
        user_id=user_id,
        full_name="Carlos Estudiante",
        student_code=uuid.uuid4().hex[:10],
        academic_program="Ingeniería de Sistemas",
        current_semester=semester,
        contact_email=email,
        contact_phone=phone,
    )


def grant_consent(user_id: uuid.UUID) -> DataConsent:
    """Persist the accepted consent required for eligibility."""
    return DataConsent.objects.create(
        user_id=user_id,
        policy_version="v1.0-2026",
        is_accepted=True,
        ip_address="127.0.0.1",
        user_agent="pytest-client",
    )


def test_eligibility_requires_authentication():
    response = APIClient().get(eligibility_url(uuid.uuid4()))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_eligibility_rejects_caller_without_internal_scope():
    client = authenticated_client(
        role="STUDENT",
        scopes=("profile:student:read",),
    )

    response = client.get(eligibility_url(uuid.uuid4()))

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_eligibility_rejects_invalid_user_id():
    client = authenticated_client()

    response = client.get(eligibility_url("not-a-valid-uuid"))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "user_id" in response.data["error"]["details"]


def test_eligibility_returns_not_found_for_unknown_student():
    client = authenticated_client()

    response = client.get(eligibility_url(uuid.uuid4()))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.parametrize("semester", [6, 10])
def test_eligibility_accepts_semester_boundaries(semester):
    student_id = uuid.uuid4()
    create_student(
        student_id,
        semester=semester,
        email="carlos@ufps.edu.co",
        phone="3109876543",
    )
    grant_consent(student_id)
    client = authenticated_client()

    response = client.get(eligibility_url(student_id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "user_id": str(student_id),
        "is_eligible": True,
        "current_semester": semester,
        "has_consent": True,
        "contact_info": {
            "email": "carlos@ufps.edu.co",
            "phone": "3109876543",
        },
    }


def test_eligibility_is_false_without_consent():
    student_id = uuid.uuid4()
    create_student(student_id, semester=8, phone=None)
    client = authenticated_client()

    response = client.get(eligibility_url(student_id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_eligible"] is False
    assert response.data["current_semester"] == 8
    assert response.data["has_consent"] is False


@pytest.mark.parametrize("semester", [5, 11])
def test_eligibility_is_false_outside_semester_range(semester):
    """Exercise the endpoint branch without weakening the database constraint."""
    student_id = uuid.uuid4()
    grant_consent(student_id)
    student = SimpleNamespace(
        current_semester=semester,
        contact_email="student@ufps.edu.co",
        contact_phone="3001234567",
    )
    client = authenticated_client()

    with patch("apps.core.views.StudentProfile.objects.filter") as student_filter:
        student_filter.return_value.first.return_value = student
        response = client.get(eligibility_url(student_id))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_eligible"] is False
    assert response.data["current_semester"] == semester
    assert response.data["has_consent"] is True


def test_eligibility_allows_admin_without_internal_scope():
    student_id = uuid.uuid4()
    create_student(student_id, semester=6)
    client = authenticated_client(role="ADMIN", scopes=())

    response = client.get(eligibility_url(student_id))

    assert response.status_code == status.HTTP_200_OK
