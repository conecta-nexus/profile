from http import HTTPStatus
from typing import Any

from django.http import JsonResponse
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def _error_payload(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> dict[str, Any]:
    return {
        "error": {
            "status": status_code,
            "code": code,
            "message": message,
            "details": details,
        }
    }


def _error_code(exception: Exception, status_code: int) -> str:
    if isinstance(exception, ValidationError):
        return "validation_error"

    if isinstance(exception, APIException):
        return str(exception.default_code)

    return f"http_{status_code}"


def _error_message(
    exception: Exception,
    response_data: Any,
    status_code: int,
) -> str:
    if isinstance(exception, ValidationError):
        return "Request validation failed."

    if isinstance(response_data, dict) and "detail" in response_data:
        return str(response_data["detail"])

    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Request failed."


def api_exception_handler(exception: Exception, context: dict) -> Response:
    response = drf_exception_handler(exception, context)

    if response is None:
        return Response(
            _error_payload(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "internal_server_error",
                "An unexpected error occurred.",
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    original_data = response.data
    response.data = _error_payload(
        response.status_code,
        _error_code(exception, response.status_code),
        _error_message(exception, original_data, response.status_code),
        original_data,
    )
    return response


def bad_request(_request, _exception) -> JsonResponse:
    return JsonResponse(
        _error_payload(
            status.HTTP_400_BAD_REQUEST,
            "bad_request",
            "The request could not be processed.",
        ),
        status=status.HTTP_400_BAD_REQUEST,
    )


def permission_denied(_request, _exception) -> JsonResponse:
    return JsonResponse(
        _error_payload(
            status.HTTP_403_FORBIDDEN,
            "permission_denied",
            "You do not have permission to perform this action.",
        ),
        status=status.HTTP_403_FORBIDDEN,
    )


def not_found(_request, _exception) -> JsonResponse:
    return JsonResponse(
        _error_payload(
            status.HTTP_404_NOT_FOUND,
            "not_found",
            "The requested resource was not found.",
        ),
        status=status.HTTP_404_NOT_FOUND,
    )


def server_error(_request) -> JsonResponse:
    return JsonResponse(
        _error_payload(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_server_error",
            "An unexpected error occurred.",
        ),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )