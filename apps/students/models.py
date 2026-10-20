import uuid

from django.db import models
from django.db.models import Q


class StudentProfile(models.Model):
    """Store the academic profile owned by a student user."""

    # Keep only the auth user UUID to preserve database-per-service isolation.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(unique=True)

    full_name = models.CharField(max_length=150)
    student_code = models.CharField(max_length=15, unique=True)
    academic_program = models.CharField(
        max_length=120,
        default="Ingeniería de Sistemas",
    )
    current_semester = models.PositiveSmallIntegerField()

    # Django stores JSONField as JSONB when PostgreSQL is used.
    completed_courses = models.JSONField(default=list, blank=True)
    technical_skills = models.JSONField(default=list, blank=True)
    interest_areas = models.JSONField(default=list, blank=True)

    bio = models.TextField(null=True, blank=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=25, null=True, blank=True)

    is_profile_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "student_profiles"
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    current_semester__gte=6,
                    current_semester__lte=10,
                ),
                name="student_semester_between_6_and_10",
            ),
        ]

    def __str__(self):
        """Return a readable representation of the student profile."""
        return f"{self.full_name} ({self.student_code})"