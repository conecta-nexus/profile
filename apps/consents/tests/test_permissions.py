from unittest.mock import MagicMock
import uuid

import pytest

from apps.consents.models import DataConsent
from apps.consents.permissions import ConsentRequired, HasAcceptedConsent
from apps.core.authentication import StatelessJWTUser

pytestmark = pytest.mark.django_db


def test_has_accepted_consent_unauthenticated():
    perm = HasAcceptedConsent()
    request = MagicMock(user=None)
    assert perm.has_permission(request, None) is False

    user_anon = MagicMock(is_authenticated=False)
    request_anon = MagicMock(user=user_anon)
    assert perm.has_permission(request_anon, None) is False


def test_has_accepted_consent_missing_raises_consent_required():
    perm = HasAcceptedConsent()
    user_id = uuid.uuid4()
    user = StatelessJWTUser({"sub": str(user_id), "role": "STUDENT"})
    request = MagicMock(user=user)

    with pytest.raises(ConsentRequired) as exc:
        perm.has_permission(request, None)

    assert exc.value.get_codes() == "CONSENT_REQUIRED"


def test_has_accepted_consent_granted_when_record_exists():
    user_id = uuid.uuid4()
    DataConsent.objects.create(
        user_id=user_id,
        policy_version="v1.0-2026",
        is_accepted=True,
        ip_address="127.0.0.1",
        user_agent="pytest-client",
    )

    user = StatelessJWTUser({"sub": str(user_id), "role": "STUDENT"})
    request = MagicMock(user=user)

    perm = HasAcceptedConsent()
    assert perm.has_permission(request, None) is True
