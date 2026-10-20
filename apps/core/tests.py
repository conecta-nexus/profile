import json

from django.conf import settings
from django.core.checks import run_checks
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.renderers import JSONRenderer

from apps.core.exceptions import (
    api_exception_handler,
    bad_request,
    not_found,
    permission_denied,
    server_error,
)
from apps.core.urls import urlpatterns as profile_urlpatterns
from config.urls import urlpatterns as root_urlpatterns


# Render DRF and Django responses into comparable JSON dictionaries.
def response_json(response) -> dict:
    if hasattr(response, "data"):
        content = JSONRenderer().render(response.data)
    else:
        content = response.content

    return json.loads(content)


# Verify that every module required by the profile service is registered.
def test_required_apps_are_registered():
    expected_apps = {
        "rest_framework",
        "apps.core.apps.CoreConfig",
        "apps.consents.apps.ConsentsConfig",
        "apps.students.apps.StudentsConfig",
        "apps.companies.apps.CompaniesConfig",
    }

    assert expected_apps.issubset(set(settings.INSTALLED_APPS))


# Verify that Django targets the database defined by the task.
def test_database_targets_profiles_postgresql_database():
    """Verify the PostgreSQL engine and profiles database name."""
    database = settings.DATABASES["default"]

    assert database["ENGINE"] == "django.db.backends.postgresql"

    # Django prefixes the configured name while the test database is active.
    assert database["NAME"] in {"db_profiles", "test_db_profiles"}


# Verify the global renderer, parser, and exception handler.
def test_drf_global_settings():
    drf_settings = settings.REST_FRAMEWORK

    assert drf_settings["DEFAULT_RENDERER_CLASSES"] == [
        "rest_framework.renderers.JSONRenderer"
    ]
    assert drf_settings["DEFAULT_PARSER_CLASSES"] == [
        "rest_framework.parsers.JSONParser"
    ]
    assert (
        drf_settings["EXCEPTION_HANDLER"]
        == "apps.core.exceptions.api_exception_handler"
    )


# Verify the root path and each internal module route.
def test_profile_routes_are_registered():
    root_routes = {str(pattern.pattern) for pattern in root_urlpatterns}
    profile_routes = {
        str(pattern.pattern) for pattern in profile_urlpatterns
    }

    assert "api/v1/profiles/" in root_routes
    assert {
        "consents/",
        "students/",
        "companies/",
    }.issubset(profile_routes)


# Verify the standard validation error contract.
def test_validation_error_uses_standard_structure():
    response = api_exception_handler(
        ValidationError(
            {"student_code": ["This field is required."]}
        ),
        {},
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response_json(response) == {
        "error": {
            "status": 400,
            "code": "validation_error",
            "message": "Request validation failed.",
            "details": {
                "student_code": ["This field is required."]
            },
        }
    }


# Verify that DRF not-found errors preserve the standard contract.
def test_not_found_error_uses_standard_structure():
    response = api_exception_handler(NotFound(), {})
    payload = response_json(response)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert payload["error"]["status"] == 404
    assert payload["error"]["code"] == "not_found"


# Prevent unexpected exceptions from exposing internal information.
def test_unhandled_exception_is_returned_as_json():
    response = api_exception_handler(RuntimeError("Unexpected failure"), {})

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response_json(response) == {
        "error": {
            "status": 500,
            "code": "internal_server_error",
            "message": "An unexpected error occurred.",
            "details": None,
        }
    }


# Verify that Django-level errors use the same API contract.
def test_django_error_handlers_use_standard_structure():
    responses = [
        (bad_request(None, None), 400, "bad_request"),
        (permission_denied(None, None), 403, "permission_denied"),
        (not_found(None, None), 404, "not_found"),
        (server_error(None), 500, "internal_server_error"),
    ]

    for response, expected_status, expected_code in responses:
        assert response.status_code == expected_status
        assert response_json(response)["error"]["code"] == expected_code


# Ensure that Django reports no configuration warnings or errors.
def test_django_system_checks_pass():
    assert run_checks() == []