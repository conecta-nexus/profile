import uuid

import pytest
from rest_framework.exceptions import ValidationError

from apps.consents.models import DataConsent
from apps.consents.serializers import (
    DataConsentCreateSerializer,
    DataConsentStatusSerializer,
)

pytestmark = pytest.mark.django_db


def test_create_serializer_accepts_valid_payload():
    data = {"is_accepted": True, "policy_version": "v1.0-2026"}
    serializer = DataConsentCreateSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["is_accepted"] is True
    assert serializer.validated_data["policy_version"] == "v1.0-2026"


def test_create_serializer_defaults_policy_version():
    data = {"is_accepted": True}
    serializer = DataConsentCreateSerializer(data=data)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["policy_version"] == "v1.0-2026"


def test_create_serializer_rejects_false_is_accepted():
    data = {"is_accepted": False}
    serializer = DataConsentCreateSerializer(data=data)
    assert not serializer.is_valid()
    assert "is_accepted" in serializer.errors


def test_create_serializer_rejects_blank_policy_version():
    data = {"is_accepted": True, "policy_version": "   "}
    serializer = DataConsentCreateSerializer(data=data)
    assert not serializer.is_valid()
    assert "policy_version" in serializer.errors


def test_status_serializer_includes_all_contract_fields():
    consent = DataConsent.objects.create(
        user_id=uuid.uuid4(),
        policy_version="v1.0-2026",
        is_accepted=True,
        ip_address="127.0.0.1",
        user_agent="pytest-agent",
    )
    serializer = DataConsentStatusSerializer(instance=consent)
    data = serializer.data

    assert data["id"] == str(consent.id)
    assert data["user_id"] == str(consent.user_id)
    assert data["policy_version"] == "v1.0-2026"
    assert data["is_accepted"] is True
    assert "accepted_at" in data
