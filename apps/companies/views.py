from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.companies.models import CompanyProfile
from apps.companies.serializers import (
    CompanyProfileCreateSerializer,
    CompanyProfilePrivateSerializer,
    CompanyProfilePublicSerializer,
    CompanyProfileUpdateSerializer,
)
from apps.consents.permissions import HasAcceptedConsent
from apps.core.permissions import (
    HasScope,
    IsAuthenticatedStateless,
    IsCompany,
    IsStudent,
)


class CompanyProfileMeView(APIView):
    """Create, retrieve, or update the authenticated company's profile."""

    def get_permissions(self):
        """Apply read or consent-protected write permissions by HTTP method."""
        if self.request.method == "GET":
            permission_classes = (
                IsAuthenticatedStateless,
                IsCompany,
                HasScope("profile:company:read"),
            )
        else:
            permission_classes = (
                IsAuthenticatedStateless,
                IsCompany,
                HasScope("profile:company:write"),
                HasAcceptedConsent,
            )

        return [permission() for permission in permission_classes]

    def post(self, request) -> Response:
        """Create the initial profile owned by the authenticated company."""
        if CompanyProfile.objects.filter(user_id=request.user.id).exists():
            raise ValidationError(
                {"profile": ["A company profile already exists for this user."]}
            )

        serializer = CompanyProfileCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(user_id=request.user.id)

        return Response(
            CompanyProfilePrivateSerializer(profile).data,
            status=status.HTTP_201_CREATED,
        )

    def get(self, request) -> Response:
        """Return the authenticated company's complete private profile."""
        profile = get_object_or_404(CompanyProfile, user_id=request.user.id)
        return Response(
            CompanyProfilePrivateSerializer(profile).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request) -> Response:
        """Partially update fields that remain mutable after registration."""
        profile = get_object_or_404(CompanyProfile, user_id=request.user.id)
        serializer = CompanyProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()

        return Response(
            CompanyProfilePrivateSerializer(profile).data,
            status=status.HTTP_200_OK,
        )


class CompanyProfilePublicView(APIView):
    """Expose a restricted company profile to authorized student users."""

    permission_classes = (
        IsAuthenticatedStateless,
        IsStudent,
        HasScope("profile:company:read_public"),
    )

    def get(self, request, user_id) -> Response:
        """Return corporate information without direct contact fields."""
        profile = get_object_or_404(CompanyProfile, user_id=user_id)
        return Response(
            CompanyProfilePublicSerializer(profile).data,
            status=status.HTTP_200_OK,
        )
