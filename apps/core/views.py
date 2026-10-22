import uuid

from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.consents.models import DataConsent
from apps.core.permissions import IsInternalServiceOrAdmin
from apps.students.models import StudentProfile


class InternalEligibilityView(APIView):
    """Synchronous internal endpoint consumed by inter-service clients (application microservice).

    Validates student semester eligibility (semesters 6-10), checks Law 1581 Habeas Data consent,
    and returns contact channels upon formal application acceptance (RB-05 / RF06 / RF31).
    """

    permission_classes = [IsAuthenticated, IsInternalServiceOrAdmin]

    def get(self, request, user_id, *args, **kwargs) -> Response:
        try:
            target_uuid = uuid.UUID(str(user_id))
        except (ValueError, TypeError):
            raise ValidationError({"user_id": ["Invalid UUID format."]})

        student = StudentProfile.objects.filter(user_id=target_uuid).first()
        if not student:
            raise NotFound("Student profile not found for the specified user.")

        has_consent = DataConsent.objects.filter(
            user_id=target_uuid,
            is_accepted=True,
        ).exists()

        current_semester = student.current_semester
        is_eligible = bool(has_consent and 6 <= current_semester <= 10)

        response_payload = {
            "user_id": str(target_uuid),
            "is_eligible": is_eligible,
            "current_semester": current_semester,
            "has_consent": has_consent,
            "contact_info": {
                "email": student.contact_email,
                "phone": student.contact_phone,
            },
        }

        return Response(response_payload, status=status.HTTP_200_OK)
