from rest_framework import serializers

from apps.students.models import StudentProfile


class StringListField(serializers.ListField):
    """Accept a JSON array containing non-empty strings."""

    def __init__(self, **kwargs):
        super().__init__(
            child=serializers.CharField(allow_blank=False),
            **kwargs,
        )


class SemesterValidationMixin:
    """Provide semester validation shared by student serializers."""

    def validate_current_semester(self, value):
        """Reject semesters outside the supported academic range."""
        if not 6 <= value <= 10:
            raise serializers.ValidationError(
                "Current semester must be between 6 and 10."
            )

        return value


class StudentProfileCreateSerializer(
    SemesterValidationMixin,
    serializers.ModelSerializer,
):
    """Validate the initial student profile registration."""

    # Enforce the array structure documented for PostgreSQL JSONB fields.
    completed_courses = StringListField(required=False)
    technical_skills = StringListField(required=False)
    interest_areas = StringListField(required=False)

    class Meta:
        model = StudentProfile
        fields = (
            "id",
            "user_id",
            "full_name",
            "student_code",
            "academic_program",
            "current_semester",
            "completed_courses",
            "technical_skills",
            "interest_areas",
            "bio",
            "contact_email",
            "contact_phone",
            "is_profile_complete",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user_id",
            "is_profile_complete",
            "created_at",
            "updated_at",
        )


class StudentProfileUpdateSerializer(
    SemesterValidationMixin,
    serializers.ModelSerializer,
):
    """Validate fields supported by partial student profile updates."""

    # Keep the JSONB fields consistent with their documented list structure.
    completed_courses = StringListField(required=False)
    technical_skills = StringListField(required=False)
    interest_areas = StringListField(required=False)

    immutable_fields = frozenset(
        {
            "student_code",
            "academic_program",
        }
    )

    class Meta:
        model = StudentProfile
        fields = (
            "current_semester",
            "completed_courses",
            "technical_skills",
            "interest_areas",
            "bio",
        )

    def validate(self, attributes):
        """Reject immutable and unsupported fields instead of ignoring them."""
        submitted_fields = set(self.initial_data)
        supported_fields = set(self.fields)
        unsupported_fields = submitted_fields - supported_fields

        if unsupported_fields:
            errors = {}

            for field_name in sorted(unsupported_fields):
                if field_name in self.immutable_fields:
                    errors[field_name] = (
                        "This field is immutable and cannot be updated."
                    )
                else:
                    errors[field_name] = (
                        "This field cannot be updated through this endpoint."
                    )

            raise serializers.ValidationError(errors)

        return super().validate(attributes)


class StudentProfilePrivateSerializer(serializers.ModelSerializer):
    """Expose the complete student profile to its owner."""

    class Meta:
        model = StudentProfile
        fields = (
            "id",
            "user_id",
            "full_name",
            "student_code",
            "academic_program",
            "current_semester",
            "completed_courses",
            "technical_skills",
            "interest_areas",
            "bio",
            "contact_email",
            "contact_phone",
            "is_profile_complete",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class StudentProfilePublicSerializer(serializers.ModelSerializer):
    """Expose academic data without direct contact information."""

    class Meta:
        model = StudentProfile
        fields = (
            "id",
            "user_id",
            "full_name",
            "student_code",
            "academic_program",
            "current_semester",
            "completed_courses",
            "technical_skills",
            "interest_areas",
            "bio",
            "is_profile_complete",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields