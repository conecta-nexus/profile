import uuid

import pytest

from apps.students.models import StudentProfile
from apps.students.serializers import (
    StudentProfileCreateSerializer,
    StudentProfilePrivateSerializer,
    StudentProfilePublicSerializer,
    StudentProfileUpdateSerializer,
)


pytestmark = pytest.mark.django_db


def valid_student_data(**overrides):
    """Return valid data for an initial student profile."""
    unique_value = uuid.uuid4().hex[:12]

    values = {
        "full_name": "Andrea Gómez",
        "student_code": unique_value,
        "academic_program": "Ingeniería de Sistemas",
        "current_semester": 6,
        "completed_courses": ["Programming I"],
        "technical_skills": ["Python"],
        "interest_areas": ["Backend development"],
        "bio": "Systems engineering student.",
        "contact_email": f"{unique_value}@example.com",
        "contact_phone": "3001234567",
    }
    values.update(overrides)

    return values


def create_student_profile(**overrides):
    """Create a persisted student profile for serializer tests."""
    values = valid_student_data(**overrides)
    values["user_id"] = values.get("user_id", uuid.uuid4())

    return StudentProfile.objects.create(**values)


@pytest.mark.parametrize("semester", [6, 10])
def test_create_serializer_accepts_semester_boundaries(semester):
    """Accept the minimum and maximum semesters."""
    serializer = StudentProfileCreateSerializer(
        data=valid_student_data(current_semester=semester)
    )

    assert serializer.is_valid(), serializer.errors

    profile = serializer.save(user_id=uuid.uuid4())

    assert profile.current_semester == semester


@pytest.mark.parametrize("semester", [5, 11])
def test_create_serializer_rejects_invalid_semester(semester):
    """Reject semesters outside the supported academic range."""
    serializer = StudentProfileCreateSerializer(
        data=valid_student_data(current_semester=semester)
    )

    assert serializer.is_valid() is False
    assert "current_semester" in serializer.errors


def test_create_serializer_does_not_accept_user_id_from_payload():
    """Prevent clients from assigning profile ownership."""
    requested_user_id = uuid.uuid4()
    authenticated_user_id = uuid.uuid4()
    data = valid_student_data(user_id=requested_user_id)

    serializer = StudentProfileCreateSerializer(data=data)

    assert serializer.is_valid(), serializer.errors

    profile = serializer.save(user_id=authenticated_user_id)

    assert profile.user_id == authenticated_user_id
    assert profile.user_id != requested_user_id


@pytest.mark.parametrize(
    "field_name,new_value",
    [
        ("student_code", "NEW-CODE"),
        ("academic_program", "Software Engineering"),
    ],
)
def test_update_serializer_rejects_immutable_fields(field_name, new_value):
    """Reject attempts to modify immutable academic identifiers."""
    profile = create_student_profile()
    serializer = StudentProfileUpdateSerializer(
        profile,
        data={field_name: new_value},
        partial=True,
    )

    assert serializer.is_valid() is False
    assert field_name in serializer.errors


def test_update_serializer_accepts_supported_fields():
    """Update academic information without changing immutable fields."""
    profile = create_student_profile()
    original_student_code = profile.student_code
    original_academic_program = profile.academic_program

    serializer = StudentProfileUpdateSerializer(
        profile,
        data={
            "current_semester": 8,
            "completed_courses": ["Programming I", "Databases"],
            "technical_skills": ["Python", "Django"],
            "interest_areas": ["Backend development", "Cloud computing"],
            "bio": "Updated academic profile.",
        },
        partial=True,
    )

    assert serializer.is_valid(), serializer.errors

    updated_profile = serializer.save()

    assert updated_profile.current_semester == 8
    assert updated_profile.technical_skills == ["Python", "Django"]
    assert updated_profile.student_code == original_student_code
    assert updated_profile.academic_program == original_academic_program


def test_update_serializer_rejects_unsupported_fields():
    """Reject fields that are not part of the partial update contract."""
    profile = create_student_profile()
    serializer = StudentProfileUpdateSerializer(
        profile,
        data={"contact_email": "new-address@example.com"},
        partial=True,
    )

    assert serializer.is_valid() is False
    assert "contact_email" in serializer.errors


def test_private_serializer_includes_contact_information():
    """Expose contact information only in the owner's representation."""
    profile = create_student_profile()

    data = StudentProfilePrivateSerializer(profile).data

    assert data["contact_email"] == profile.contact_email
    assert data["contact_phone"] == profile.contact_phone


def test_public_serializer_omits_contact_information():
    """Prevent direct contact details from appearing publicly."""
    profile = create_student_profile()

    data = StudentProfilePublicSerializer(profile).data

    assert "contact_email" not in data
    assert "contact_phone" not in data
    assert data["user_id"] == str(profile.user_id)

@pytest.mark.parametrize(
    "field_name",
    [
        "completed_courses",
        "technical_skills",
        "interest_areas",
    ],
)
def test_create_serializer_rejects_non_list_academic_fields(field_name):
    """Reject non-array values for documented JSONB list fields."""
    data = valid_student_data()
    data[field_name] = {"unexpected": "object"}

    serializer = StudentProfileCreateSerializer(data=data)

    assert serializer.is_valid() is False
    assert field_name in serializer.errors


@pytest.mark.parametrize(
    "field_name",
    [
        "completed_courses",
        "technical_skills",
        "interest_areas",
    ],
)
def test_update_serializer_rejects_non_list_academic_fields(field_name):
    """Preserve the JSON array structure during partial updates."""
    profile = create_student_profile()
    serializer = StudentProfileUpdateSerializer(
        profile,
        data={field_name: "not-a-list"},
        partial=True,
    )

    assert serializer.is_valid() is False
    assert field_name in serializer.errors