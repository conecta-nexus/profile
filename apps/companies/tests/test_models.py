import uuid

import pytest
from django.contrib import admin
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.companies.models import CompanyProfile


pytestmark = pytest.mark.django_db


def create_company_profile(**overrides):
    """Create a company profile with unique test data."""
    unique_value = uuid.uuid4().hex[:12]

    values = {
        "user_id": uuid.uuid4(),
        "nit": f"NIT-{unique_value}",
        "business_name": f"Nexus Company {unique_value}",
        "economic_sector": "Technology",
        "description": "Software development and technology services.",
        "contact_name": "Corporate Representative",
        "contact_email": f"{unique_value}@example.com",
        "contact_phone": "3001234567",
    }
    values.update(overrides)

    return CompanyProfile.objects.create(**values)


def test_company_profile_uses_expected_defaults():
    """Verify defaults, optional fields, and UTC timestamps."""
    profile = create_company_profile()

    assert profile.website_url is None
    assert profile.public_links == []
    assert profile.is_verified is True
    assert timezone.is_aware(profile.created_at)
    assert timezone.is_aware(profile.updated_at)


def test_company_profile_uses_expected_table_name():
    """Verify the table name required by the data contract."""
    assert CompanyProfile._meta.db_table == "company_profiles"


def test_company_profile_string_representation():
    """Return readable company identification."""
    profile = create_company_profile(
        business_name="Conecta Nexus SAS",
        nit="900123456-7",
    )

    assert str(profile) == "Conecta Nexus SAS (900123456-7)"


def test_company_user_id_must_be_unique():
    """Prevent multiple profiles for the same company user."""
    existing_profile = create_company_profile()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_company_profile(user_id=existing_profile.user_id)


def test_company_nit_must_be_unique():
    """Prevent multiple company profiles from sharing a NIT."""
    existing_profile = create_company_profile()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_company_profile(nit=existing_profile.nit)


def test_company_profile_is_registered_in_admin():
    """Expose company profiles through Django Admin."""
    assert admin.site.is_registered(CompanyProfile)