from collections.abc import Iterable
from typing import Any

from rest_framework.permissions import BasePermission


class IsAuthenticatedStateless(BasePermission):
    """Allows access only to authenticated stateless JWT users."""

    def has_permission(self, request: Any, view: Any) -> bool:
        return bool(
            request.user
            and getattr(request.user, "is_authenticated", False)
            and getattr(request.user, "id", None) is not None
        )


class IsStudent(BasePermission):
    """Allows access only to users with the STUDENT role."""

    message = "Only student accounts are authorized to perform this action."

    def has_permission(self, request: Any, view: Any) -> bool:
        return bool(
            request.user
            and getattr(request.user, "is_authenticated", False)
            and getattr(request.user, "role", None) == "STUDENT"
        )


class IsCompany(BasePermission):
    """Allows access only to users with the COMPANY role."""

    message = "Only corporate accounts are authorized to perform this action."

    def has_permission(self, request: Any, view: Any) -> bool:
        return bool(
            request.user
            and getattr(request.user, "is_authenticated", False)
            and getattr(request.user, "role", None) == "COMPANY"
        )


class IsAdmin(BasePermission):
    """Allows access only to users with the ADMIN role."""

    message = "Administrator privileges are required for this action."

    def has_permission(self, request: Any, view: Any) -> bool:
        return bool(
            request.user
            and getattr(request.user, "is_authenticated", False)
            and getattr(request.user, "role", None) == "ADMIN"
        )


class IsInternalServiceOrAdmin(BasePermission):
    """Allows access to internal service callers with profile:read_internal scope or ADMIN role."""

    message = "Internal service token or administrative scope required."

    def has_permission(self, request: Any, view: Any) -> bool:
        if not request.user or not getattr(request.user, "is_authenticated", False):
            return False

        if getattr(request.user, "role", None) == "ADMIN":
            return True

        has_any_scope_fn = getattr(request.user, "has_any_scope", None)
        if callable(has_any_scope_fn):
            return bool(
                has_any_scope_fn("profile:read_internal", "profile:read_all")
            )

        scopes = set(getattr(request.user, "scopes", []))
        return bool({"profile:read_internal", "profile:read_all"} & scopes)


def HasScope(required_scope: str):
    """Permission class factory requiring a specific OAuth2 scope."""

    class _HasScope(BasePermission):
        message = f"Missing required permission scope: '{required_scope}'."

        def has_permission(self, request: Any, view: Any) -> bool:
            if not request.user or not getattr(request.user, "is_authenticated", False):
                return False
            has_scope_fn = getattr(request.user, "has_scope", None)
            if callable(has_scope_fn):
                return bool(has_scope_fn(required_scope))
            return False

    _HasScope.__name__ = f"HasScope_{required_scope.replace(':', '_')}"
    return _HasScope


class HasRequiredScopes(BasePermission):
    """View-driven permission requiring all scopes listed in `view.required_scopes`."""

    def has_permission(self, request: Any, view: Any) -> bool:
        if not request.user or not getattr(request.user, "is_authenticated", False):
            return False

        required_scopes = getattr(view, "required_scopes", [])
        if not required_scopes:
            return True

        has_all_scopes_fn = getattr(request.user, "has_all_scopes", None)
        if callable(has_all_scopes_fn):
            return bool(has_all_scopes_fn(*required_scopes))

        scopes = set(getattr(request.user, "scopes", []))
        return set(required_scopes).issubset(scopes)
