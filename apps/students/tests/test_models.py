import uuid

import pytest
from django.db import IntegrityError, transaction

from apps.students.models import StudentProfile


pytestmark = pytest.mark.django_db


def create_student_profile(**overrides):
    """Create a valid student profile with optional field overrides."""
    unique_value = uuid.uuid4().hex[:12]

    values = {
        "user_id": uuid.uuid4(),
        "full_name": "Andrea Gómez",
        "student_code": unique_value,
        "current_semester": 6,
        "contact_email": f"{unique_value}@example.com",
    }
    values.update(overrides)

    return StudentProfile.objects.create(**values)


def test_student_profile_uses_expected_defaults():
    """Verify the defaults defined by the student profile contract."""
    profile = create_student_profile()

    assert profile.academic_program == "Ingeniería de Sistemas"
    assert profile.completed_courses == []
    assert profile.technical_skills == []
    assert profile.interest_areas == []
    assert profile.bio is None
    assert profile.contact_phone is None
    assert profile.is_profile_complete is False
    assert profile.created_at is not None
    assert profile.updated_at is not None


def test_student_profile_uses_expected_table_name():
    """Verify the PostgreSQL table name required by the data model."""
    assert StudentProfile._meta.db_table == "student_profiles"


@pytest.mark.parametrize("semester", [6, 10])
def test_semester_boundary_values_are_accepted(semester):
    """Accept the minimum and maximum allowed semesters."""
    profile = create_student_profile(current_semester=semester)

    assert profile.current_semester == semester


@pytest.mark.parametrize("semester", [5, 11])
def test_semester_outside_allowed_range_is_rejected(semester):
    """Reject semesters outside the database constraint."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_student_profile(current_semester=semester)


def test_user_id_must_be_unique():
    """Prevent multiple student profiles for the same auth user."""
    existing_profile = create_student_profile()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_student_profile(user_id=existing_profile.user_id)


def test_student_code_must_be_unique():
    """Prevent duplicated institutional student codes."""
    existing_profile = create_student_profile()

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            create_student_profile(student_code=existing_profile.student_code)