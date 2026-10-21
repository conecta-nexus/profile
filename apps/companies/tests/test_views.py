import uuid

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.companies.models import CompanyProfile
from apps.consents.models import DataConsent
from apps.core.authentication import StatelessJWTUser

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


def company_payload() -> dict:
    """Return a valid initial company profile payload."""
    return {
        "nit": "900123456-8",
        "business_name": "Conecta Nexus S.A.S.",
        "economic_sector": "Technology",
        "description": "Software solutions for university communities.",
        "website_url": "https://conectanexus.example.com",
        "public_links": [
            "https://www.linkedin.com/company/conecta-nexus",
        ],
        "contact_name": "Corporate Contact",
        "contact_email": "contact@conectanexus.example.com",
        "contact_phone": "+57 300 123 4567",
    }


def create_company_profile(user_id=None) -> CompanyProfile:
    """Persist a company profile for read and update tests."""
    user_id = user_id or uuid.uuid4()
    return CompanyProfile.objects.create(user_id=user_id, **company_payload())


def test_company_profile_endpoints_require_authentication():
    response = APIClient().get(reverse("companies:profile-me"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_company_can_create_own_profile_with_consent():
    client, user_id = make_client(
        "COMPANY",
        ["profile:company:write"],
    )
    grant_consent(user_id)

    response = client.post(
        reverse("companies:profile-me"),
        company_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["user_id"] == str(user_id)
    assert response.data["contact_email"] == company_payload()["contact_email"]
    assert CompanyProfile.objects.filter(user_id=user_id).exists()


def test_company_create_requires_accepted_consent():
    client, _ = make_client("COMPANY", ["profile:company:write"])

    response = client.post(
        reverse("companies:profile-me"),
        company_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["error"]["code"] == "CONSENT_REQUIRED"


def test_company_create_requires_company_role():
    client, user_id = make_client("STUDENT", ["profile:company:write"])
    grant_consent(user_id)

    response = client.post(
        reverse("companies:profile-me"),
        company_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_company_create_requires_write_scope():
    client, user_id = make_client("COMPANY", ["profile:company:read"])
    grant_consent(user_id)

    response = client.post(
        reverse("companies:profile-me"),
        company_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_company_cannot_create_duplicate_profile():
    client, user_id = make_client("COMPANY", ["profile:company:write"])
    grant_consent(user_id)
    create_company_profile(user_id)

    response = client.post(
        reverse("companies:profile-me"),
        company_payload(),
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "profile" in response.data["error"]["details"]


def test_company_can_retrieve_own_private_profile():
    client, user_id = make_client("COMPANY", ["profile:company:read"])
    profile = create_company_profile(user_id)

    response = client.get(reverse("companies:profile-me"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(profile.id)
    assert response.data["contact_name"] == profile.contact_name
    assert response.data["contact_email"] == profile.contact_email
    assert response.data["contact_phone"] == profile.contact_phone


def test_company_can_patch_mutable_fields_with_consent():
    client, user_id = make_client("COMPANY", ["profile:company:write"])
    grant_consent(user_id)
    profile = create_company_profile(user_id)

    response = client.patch(
        reverse("companies:profile-me"),
        {
            "economic_sector": "Education Technology",
            "description": "Updated corporate description.",
            "website_url": "https://updated.example.com",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    profile.refresh_from_db()
    assert profile.economic_sector == "Education Technology"
    assert profile.description == "Updated corporate description."


def test_company_patch_rejects_immutable_nit():
    client, user_id = make_client("COMPANY", ["profile:company:write"])
    grant_consent(user_id)
    profile = create_company_profile(user_id)

    response = client.patch(
        reverse("companies:profile-me"),
        {"nit": "800197268-4"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    profile.refresh_from_db()
    assert profile.nit == "900123456-8"


def test_company_patch_requires_accepted_consent():
    client, user_id = make_client("COMPANY", ["profile:company:write"])
    create_company_profile(user_id)

    response = client.patch(
        reverse("companies:profile-me"),
        {"description": "This update must be rejected."},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.data["error"]["code"] == "CONSENT_REQUIRED"


def test_student_can_retrieve_restricted_public_company_profile():
    profile = create_company_profile()
    client, _ = make_client(
        "STUDENT",
        ["profile:company:read_public"],
    )

    response = client.get(
        reverse(
            "companies:profile-public",
            kwargs={"user_id": profile.user_id},
        )
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["business_name"] == profile.business_name
    assert "contact_name" not in response.data
    assert "contact_email" not in response.data
    assert "contact_phone" not in response.data


def test_public_company_profile_requires_student_role():
    profile = create_company_profile()
    client, _ = make_client(
        "COMPANY",
        ["profile:company:read_public"],
    )

    response = client.get(
        reverse(
            "companies:profile-public",
            kwargs={"user_id": profile.user_id},
        )
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_public_company_profile_requires_read_public_scope():
    profile = create_company_profile()
    client, _ = make_client("STUDENT", ["profile:company:read"])

    response = client.get(
        reverse(
            "companies:profile-public",
            kwargs={"user_id": profile.user_id},
        )
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


def test_public_company_profile_returns_not_found():
    client, _ = make_client(
        "STUDENT",
        ["profile:company:read_public"],
    )

    response = client.get(
        reverse(
            "companies:profile-public",
            kwargs={"user_id": uuid.uuid4()},
        )
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
