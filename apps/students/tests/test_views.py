import uuid

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.consents.models import DataConsent
from apps.core.authentication import StatelessJWTUser
from apps.students.models import StudentProfile

pytestmark = pytest.mark.django_db


def make_client(role: str, scopes: list[str], user_id=None):
    """Create an API client authenticated with a stateless JWT principal."""
    user_id = user_id or uuid.uuid4()
    user = StatelessJWTUser(
        {
            "sub": str(user_id),
            "role": role,
            "scope": " ".join(scopes),
        }
    )
    client = APIClient()
    client.force_authenticate(user=user, token=user.payload)
    return client, user_id


def grant_consent(user_id) -> DataConsent:
    """Persist accepted consent for a test user."""
    return DataConsent.objects.create(
        user_id=user_id,
        policy_version="v1.0-2026",
        is_accepted=True,
        ip_address="127.0.0.1",
        user_agent="pytest-client",
    )


def student_payload() -> dict:
    """Return a valid initial student profile payload."""
    return {
        "full_name": "Ana Torres",
        "student_code": "1152375",
        "academic_program": "Ingeniería de Sistemas",
        "current_semester": 8,
        "completed_courses": ["Databases", "Software Engineering"],
        "technical_skills": ["Python", "PostgreSQL"],
        "interest_areas": ["Backend Development"],
        "bio": "Student interested in distributed systems.",
        "contact_email": "ana@ufps.edu.co",
        "contact_phone": "+57 300 123 4567",
    }


def create_student_profile(user_id=None) -> StudentProfile:
    """Persist a student profile for read and update tests."""
    user_id = user_id or uuid.uuid4()
    return StudentProfile.objects.create(user_id=user_id, **student_payload())


def test_student_profile_endpoints_require_authentication():
    response = APIClient().get(reverse("students:profile-me"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_student_can_create_own_profile_with_consent():
    client, user_id = make_client(
        "STUDENT",
        ["profile:student:write"],
    )
    grant_consent(user_id)

    response = client.post(
        reverse("students:profile-me"),
        student_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["user_id"] == str(user_id)
    assert response.data["contact_email"] == "ana@ufps.edu.co"
    assert StudentProfile.objects.filter(user_id=user_id).exists()


def test_student_create_requires_accepted_consent():
    client, _ = make_client("STUDENT", ["profile:student:write"])

    response = client.post(
        reverse("students:profile-me"),
        student_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["error"]["code"] == "CONSENT_REQUIRED"


def test_student_create_requires_student_role():
    client, user_id = make_client("COMPANY", ["profile:student:write"])
    grant_consent(user_id)

    response = client.post(
        reverse("students:profile-me"),
        student_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_student_create_requires_write_scope():
    client, user_id = make_client("STUDENT", ["profile:student:read"])
    grant_consent(user_id)

    response = client.post(
        reverse("students:profile-me"),
        student_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_student_cannot_create_duplicate_profile():
    client, user_id = make_client("STUDENT", ["profile:student:write"])
    grant_consent(user_id)
    create_student_profile(user_id)

    response = client.post(
        reverse("students:profile-me"),
        student_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "profile" in response.data["error"]["details"]


def test_student_can_retrieve_own_private_profile():
    client, user_id = make_client("STUDENT", ["profile:student:read"])
    profile = create_student_profile(user_id)

    response = client.get(reverse("students:profile-me"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(profile.id)
    assert response.data["contact_email"] == profile.contact_email
    assert response.data["contact_phone"] == profile.contact_phone


def test_student_can_patch_mutable_fields_with_consent():
    client, user_id = make_client("STUDENT", ["profile:student:write"])
    grant_consent(user_id)
    profile = create_student_profile(user_id)

    response = client.patch(
        reverse("students:profile-me"),
        {
            "technical_skills": ["Python", "Django"],
            "completed_courses": ["Databases"],
            "bio": "Updated academic biography.",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    profile.refresh_from_db()
    assert profile.technical_skills == ["Python", "Django"]
    assert profile.bio == "Updated academic biography."


def test_student_patch_rejects_immutable_student_code():
    client, user_id = make_client("STUDENT", ["profile:student:write"])
    grant_consent(user_id)
    profile = create_student_profile(user_id)

    response = client.patch(
        reverse("students:profile-me"),
        {"student_code": "9999999"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    profile.refresh_from_db()
    assert profile.student_code == "1152375"


def test_student_patch_requires_accepted_consent():
    client, user_id = make_client("STUDENT", ["profile:student:write"])
    create_student_profile(user_id)

    response = client.patch(
        reverse("students:profile-me"),
        {"bio": "This update must be rejected."},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["error"]["code"] == "CONSENT_REQUIRED"


def test_company_can_retrieve_restricted_public_student_profile():
    profile = create_student_profile()
    client, _ = make_client(
        "COMPANY",
        ["profile:student:read_public"],
    )

    response = client.get(
        reverse(
            "students:profile-public",
            kwargs={"user_id": profile.user_id},
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["full_name"] == profile.full_name
    assert "contact_email" not in response.data
    assert "contact_phone" not in response.data


def test_public_student_profile_requires_company_role():
    profile = create_student_profile()
    client, _ = make_client(
        "STUDENT",
        ["profile:student:read_public"],
    )

    response = client.get(
        reverse(
            "students:profile-public",
            kwargs={"user_id": profile.user_id},
        )
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_public_student_profile_requires_read_public_scope():
    profile = create_student_profile()
    client, _ = make_client("COMPANY", ["profile:student:read"])

    response = client.get(
        reverse(
            "students:profile-public",
            kwargs={"user_id": profile.user_id},
        )
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_public_student_profile_returns_not_found():
    client, _ = make_client(
        "COMPANY",
        ["profile:student:read_public"],
    )

    response = client.get(
        reverse(
            "students:profile-public",
            kwargs={"user_id": uuid.uuid4()},
        )
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
