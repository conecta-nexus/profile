from rest_framework import exceptions, permissions

from apps.consents.models import DataConsent


class ConsentRequired(exceptions.PermissionDenied):
    """Raised when an operation requires prior Habeas Data consent."""

    default_code = "CONSENT_REQUIRED"
    default_detail = (
        "Habeas Data consent (Law 1581 of 2012) is required before accessing or managing profiles."
    )


class HasAcceptedConsent(permissions.BasePermission):
    """Permission class that blocks profile actions unless explicit consent was recorded."""

    message = (
        "Habeas Data consent (Law 1581 of 2012) is required before accessing or managing profiles."
    )
    code = "CONSENT_REQUIRED"

    def has_permission(self, request, view) -> bool:
        if not request.user or not getattr(request.user, "is_authenticated", False):
            return False

        user_id = getattr(request.user, "id", None)
        if not user_id:
            return False

        has_consent = DataConsent.objects.filter(
            user_id=user_id,
            is_accepted=True,
        ).exists()

        if not has_consent:
            raise ConsentRequired()

        return True
