import uuid

import pytest

from apps.companies.models import CompanyProfile
from apps.companies.serializers import (
    CompanyProfileCreateSerializer,
    CompanyProfilePrivateSerializer,
    CompanyProfilePublicSerializer,
    CompanyProfileUpdateSerializer,
)
from apps.companies.validators import (
    calculate_nit_check_digit,
    validate_colombian_nit,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def company_payload():
    """Return a valid payload for company profile registration."""
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


@pytest.fixture
def company_profile(company_payload):
    """Create a company profile used by serializer tests."""
    return CompanyProfile.objects.create(
        user_id=uuid.uuid4(),
        **company_payload,
    )


@pytest.mark.parametrize(
    ("nit_number", "expected_digit"),
    [
        ("900123456", 8),
        ("800197268", 4),
        ("860002964", 4),
    ],
)
def test_calculate_nit_check_digit(nit_number, expected_digit):
    """Calculate known Colombian NIT verification digits."""
    assert calculate_nit_check_digit(nit_number) == expected_digit


@pytest.mark.parametrize(
    "value",
    [
        "900123456-7",
        "900.123.456-8",
        "9001234568",
        "90012345-8",
        "ABCDEFGHI-1",
    ],
)
def test_validate_colombian_nit_rejects_invalid_values(value):
    """Reject malformed NIT values and incorrect verification digits."""
    with pytest.raises(Exception):
        validate_colombian_nit(value)


def test_create_serializer_accepts_valid_company(company_payload):
    """Create a profile when all company information is valid."""
    serializer = CompanyProfileCreateSerializer(data=company_payload)

    assert serializer.is_valid(), serializer.errors

    user_id = uuid.uuid4()
    company = serializer.save(user_id=user_id)

    assert company.user_id == user_id
    assert company.nit == "900123456-8"
    assert company.is_verified is True


def test_create_serializer_does_not_accept_user_id_from_payload(
    company_payload,
):
    """Prevent clients from assigning profile ownership."""
    supplied_user_id = uuid.uuid4()
    company_payload["user_id"] = str(supplied_user_id)

    serializer = CompanyProfileCreateSerializer(data=company_payload)

    assert serializer.is_valid(), serializer.errors
    assert "user_id" not in serializer.validated_data


def test_create_serializer_rejects_duplicate_nit(
    company_payload,
    company_profile,
):
    """Reject a NIT that is already registered."""
    serializer = CompanyProfileCreateSerializer(data=company_payload)

    assert not serializer.is_valid()
    assert "nit" in serializer.errors


def test_create_serializer_rejects_non_list_public_links(company_payload):
    """Require public links to be represented as a JSON list."""
    company_payload["public_links"] = "https://example.com"

    serializer = CompanyProfileCreateSerializer(data=company_payload)

    assert not serializer.is_valid()
    assert "public_links" in serializer.errors


def test_create_serializer_rejects_invalid_public_link(company_payload):
    """Reject malformed URLs inside the public links list."""
    company_payload["public_links"] = ["not-a-valid-url"]

    serializer = CompanyProfileCreateSerializer(data=company_payload)

    assert not serializer.is_valid()
    assert "public_links" in serializer.errors


def test_update_serializer_accepts_mutable_fields(company_profile):
    """Update sector, description, website, links, and contact data."""
    serializer = CompanyProfileUpdateSerializer(
        company_profile,
        data={
            "economic_sector": "Education Technology",
            "description": "Updated corporate description.",
            "website_url": "https://updated.example.com",
            "public_links": ["https://linkedin.com/company/updated"],
            "contact_name": "Updated Contact",
            "contact_email": "updated@example.com",
            "contact_phone": "+57 310 000 0000",
        },
        partial=True,
    )

    assert serializer.is_valid(), serializer.errors

    company = serializer.save()

    assert company.economic_sector == "Education Technology"
    assert company.contact_email == "updated@example.com"


def test_update_serializer_rejects_nit_changes(company_profile):
    """Protect the company NIT after profile registration."""
    serializer = CompanyProfileUpdateSerializer(
        company_profile,
        data={"nit": "901234567-7"},
        partial=True,
    )

    assert not serializer.is_valid()
    assert serializer.errors["nit"][0] == "This field is immutable."


def test_update_serializer_rejects_unsupported_fields(company_profile):
    """Reject fields outside the supported PATCH contract."""
    serializer = CompanyProfileUpdateSerializer(
        company_profile,
        data={"business_name": "Unexpected Name"},
        partial=True,
    )

    assert not serializer.is_valid()
    assert "business_name" in serializer.errors


def test_private_serializer_includes_contact_information(company_profile):
    """Expose contact information only in the private representation."""
    data = CompanyProfilePrivateSerializer(company_profile).data

    assert data["contact_name"] == company_profile.contact_name
    assert data["contact_email"] == company_profile.contact_email
    assert data["contact_phone"] == company_profile.contact_phone


def test_public_serializer_omits_contact_information(company_profile):
    """Hide direct contact information from the public representation."""
    data = CompanyProfilePublicSerializer(company_profile).data

    assert "contact_name" not in data
    assert "contact_email" not in data
    assert "contact_phone" not in data
    assert data["business_name"] == company_profile.business_name