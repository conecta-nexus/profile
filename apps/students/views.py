from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.consents.permissions import HasAcceptedConsent
from apps.core.permissions import (
    HasScope,
    IsAuthenticatedStateless,
    IsCompany,
    IsStudent,
)
from apps.students.models import StudentProfile
from apps.students.serializers import (
    StudentProfileCreateSerializer,
    StudentProfilePrivateSerializer,
    StudentProfilePublicSerializer,
    StudentProfileUpdateSerializer,
)


class StudentProfileMeView(APIView):
    """Create, retrieve, or update the authenticated student's profile."""

    def get_permissions(self):
        """Apply read or consent-protected write permissions by HTTP method."""
        if self.request.method == "GET":
            permission_classes = (
                IsAuthenticatedStateless,
                IsStudent,
                HasScope("profile:student:read"),
            )
        else:
            permission_classes = (
                IsAuthenticatedStateless,
                IsStudent,
                HasScope("profile:student:write"),
                HasAcceptedConsent,
            )

        return [permission() for permission in permission_classes]

    def post(self, request) -> Response:
        """Create the initial profile owned by the authenticated student."""
        if StudentProfile.objects.filter(user_id=request.user.id).exists():
            raise ValidationError(
                {"profile": ["A student profile already exists for this user."]}
            )

        serializer = StudentProfileCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(user_id=request.user.id)

        return Response(
            StudentProfilePrivateSerializer(profile).data,
            status=status.HTTP_201_CREATED,
        )

    def get(self, request) -> Response:
        """Return the authenticated student's complete private profile."""
        profile = get_object_or_404(StudentProfile, user_id=request.user.id)
        return Response(
            StudentProfilePrivateSerializer(profile).data,
            status=status.HTTP_200_OK,
        )

    def patch(self, request) -> Response:
        """Partially update fields that remain mutable after registration."""
        profile = get_object_or_404(StudentProfile, user_id=request.user.id)
        serializer = StudentProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()

        return Response(
            StudentProfilePrivateSerializer(profile).data,
            status=status.HTTP_200_OK,
        )


class StudentProfilePublicView(APIView):
    """Expose a restricted student profile to authorized company users."""

    permission_classes = (
        IsAuthenticatedStateless,
        IsCompany,
        HasScope("profile:student:read_public"),
    )

    def get(self, request, user_id) -> Response:
        """Return academic information without direct contact fields."""
        profile = get_object_or_404(StudentProfile, user_id=user_id)
        return Response(
            StudentProfilePublicSerializer(profile).data,
            status=status.HTTP_200_OK,
        )
