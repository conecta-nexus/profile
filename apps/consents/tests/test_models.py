import uuid

from django.contrib import admin
from django.db import IntegrityError, transaction
import pytest

from apps.consents.models import DataConsent

pytestmark = pytest.mark.django_db


def create_data_consent(**overrides):
    """Create a valid data consent record with optional overrides."""
    values = {
        "user_id": uuid.uuid4(),
        "policy_version": "v1.0-2026",
        "is_accepted": True,
        "ip_address": "192.168.1.10",
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64)",
    }
    values.update(overrides)
    return DataConsent.objects.create(**values)


def test_data_consent_uses_expected_defaults():
    """Verify default values and auto-generated fields."""
    consent = create_data_consent()

    assert consent.policy_version == "v1.0-2026"
    assert consent.is_accepted is True
    assert consent.accepted_at is not None
    assert consent.id is not None


def test_data_consent_uses_expected_table_name():
    """Verify table name is data_consents."""
    assert DataConsent._meta.db_table == "data_consents"


def test_data_consent_is_accepted_must_be_true():
    """Ensure check constraint prevents saving is_accepted=False."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_data_consent(is_accepted=False)


def test_data_consent_user_id_is_indexed():
    """Verify that user_id field has db_index set."""
    field = DataConsent._meta.get_field("user_id")
    assert field.db_index is True


def test_data_consent_string_representation():
    """Verify readable string representation."""
    consent = create_data_consent()
    assert str(consent.user_id) in str(consent)
    assert "v1.0-2026" in str(consent)


def test_data_consent_is_registered_in_admin():
    """Ensure DataConsent is registered in Django admin."""
    assert admin.site.is_registered(DataConsent)
