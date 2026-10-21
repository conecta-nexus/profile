from typing import Any

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.consents.models import DataConsent
from apps.consents.serializers import (
    DataConsentCreateSerializer,
    DataConsentStatusSerializer,
)
from apps.core.permissions import HasScope


def get_client_ip(request: Any) -> str:
    """Extract origin IP address from request headers or remote address."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
    return ip or "127.0.0.1"


class ConsentRegistrationView(APIView):
    """Register explicit Law 1581 Habeas Data user consent."""

    permission_classes = [IsAuthenticated, HasScope("consent:write")]

    def post(self, request, *args, **kwargs) -> Response:
        serializer = DataConsentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "").strip() or "Unknown"

        consent = serializer.save(
            user_id=request.user.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        response_serializer = DataConsentStatusSerializer(consent)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ConsentStatusView(APIView):
    """Retrieve the latest Law 1581 Habeas Data consent status for the authenticated user."""

    permission_classes = [IsAuthenticated, HasScope("consent:read")]

    def get(self, request, *args, **kwargs) -> Response:
        consent = (
            DataConsent.objects.filter(user_id=request.user.id)
            .order_by("-accepted_at")
            .first()
        )
        if not consent:
            raise NotFound("No consent record found for the authenticated user.")

        serializer = DataConsentStatusSerializer(consent)
        return Response(serializer.data, status=status.HTTP_200_OK)
