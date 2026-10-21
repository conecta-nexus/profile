import logging
import os
from pathlib import Path
from typing import Any
import uuid

from django.conf import settings
import jwt
from rest_framework import authentication, exceptions

logger = logging.getLogger(__name__)

DEFAULT_JWT_ISSUER = "https://auth.conectanexus.ufps.edu.co"
DEFAULT_JWT_AUDIENCE = "conecta-nexus-services"


class StatelessJWTUser:
    """In-memory user object representing an authenticated entity via RS256 JWT."""

    def __init__(self, payload: dict[str, Any]):
        self.payload = payload
        raw_sub = payload.get("sub")
        try:
            self.id = uuid.UUID(str(raw_sub)) if raw_sub else None
        except (ValueError, TypeError):
            self.id = raw_sub

        self.pk = self.id
        self.user_id = self.id
        self.email: str = payload.get("email", "")
        self.role: str = payload.get("role", "")
        self.is_active: bool = bool(payload.get("is_active", True))

        scope_claim = payload.get("scope", "")
        if isinstance(scope_claim, str):
            self.scopes: list[str] = [s for s in scope_claim.split() if s]
        elif isinstance(scope_claim, (list, tuple)):
            self.scopes = [str(s) for s in scope_claim]
        else:
            self.scopes = []

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def has_any_scope(self, *scopes: str) -> bool:
        return any(scope in self.scopes for scope in scopes)

    def has_all_scopes(self, *scopes: str) -> bool:
        return all(scope in self.scopes for scope in scopes)

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"

    def __repr__(self) -> str:
        return f"<StatelessJWTUser id={self.id} role={self.role}>"


def get_jwt_public_key() -> str:
    """Retrieve the RSA public key from environment, configured path, or disk."""
    key_content = getattr(settings, "JWT_PUBLIC_KEY", None) or os.getenv("JWT_PUBLIC_KEY")
    if key_content and key_content.strip():
        return key_content.strip()

    key_path_str = getattr(settings, "JWT_PUBLIC_KEY_PATH", None) or os.getenv(
        "JWT_PUBLIC_KEY_PATH", "certs/jwt_public.pem"
    )
    key_path = Path(key_path_str)
    if not key_path.is_absolute():
        key_path = settings.BASE_DIR / key_path

    if key_path.exists() and key_path.is_file():
        return key_path.read_text(encoding="utf-8").strip()

    raise exceptions.AuthenticationFailed(
        detail="RS256 public key is not configured or could not be found.",
        code="public_key_missing",
    )


class RS256JWTAuthentication(authentication.BaseAuthentication):
    """Stateless DRF authentication backend verifying RS256 JWT tokens with public key."""

    keyword = "Bearer"

    def authenticate(self, request) -> tuple[StatelessJWTUser, dict[str, Any]] | None:
        auth_header = authentication.get_authorization_header(request).decode("utf-8")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) == 0:
            return None

        if parts[0].lower() != self.keyword.lower():
            return None

        if len(parts) == 1:
            raise exceptions.AuthenticationFailed(
                detail="Invalid Authorization header. No credentials provided.",
                code="invalid_header",
            )
        elif len(parts) > 2:
            raise exceptions.AuthenticationFailed(
                detail="Invalid Authorization header. Token string should not contain spaces.",
                code="invalid_header",
            )

        token = parts[1]
        payload = self.decode_and_validate_token(token)
        user = StatelessJWTUser(payload)
        return user, payload

    def decode_and_validate_token(self, token: str) -> dict[str, Any]:
        public_key = get_jwt_public_key()
        issuer = getattr(settings, "JWT_ISSUER", None) or os.getenv(
            "JWT_ISSUER", DEFAULT_JWT_ISSUER
        )
        audience = getattr(settings, "JWT_AUDIENCE", None) or os.getenv(
            "JWT_AUDIENCE", DEFAULT_JWT_AUDIENCE
        )

        try:
            # First decode without audience check to support tokens with multiple audiences
            # or custom audience lists
            unverified_payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_aud": False},
            )
        except jwt.PyJWTError as exc:
            raise exceptions.AuthenticationFailed(
                detail=f"Token decoding failed: {str(exc)}",
                code="invalid_token",
            ) from exc

        # Verify audience contains either our audience, or accepts list of audiences
        token_aud = unverified_payload.get("aud")
        expected_audiences = [audience, "conecta-nexus-gateway", "conecta-nexus-services"]
        valid_aud = False
        if isinstance(token_aud, str):
            valid_aud = token_aud in expected_audiences
        elif isinstance(token_aud, (list, tuple)):
            valid_aud = any(aud in expected_audiences for aud in token_aud)

        if not valid_aud:
            raise exceptions.AuthenticationFailed(
                detail="Token audience is invalid.",
                code="invalid_audience",
            )

        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                issuer=issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": False,  # Custom checked above
                    "require": ["exp", "sub", "role"],
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise exceptions.AuthenticationFailed(
                detail="Token has expired.",
                code="token_expired",
            ) from exc
        except jwt.InvalidIssuerError as exc:
            raise exceptions.AuthenticationFailed(
                detail="Token issuer is invalid.",
                code="invalid_issuer",
            ) from exc
        except jwt.PyJWTError as exc:
            raise exceptions.AuthenticationFailed(
                detail=f"Token validation failed: {str(exc)}",
                code="invalid_token",
            ) from exc

        # Validate token type (must be access token)
        token_type = payload.get("type", "access")
        if token_type != "access":
            raise exceptions.AuthenticationFailed(
                detail=f"Invalid token type: expected 'access', got '{token_type}'.",
                code="invalid_token_type",
            )

        # Validate active status
        if payload.get("is_active") is False:
            raise exceptions.AuthenticationFailed(
                detail="User account is deactivated.",
                code="user_inactive",
            )

        return payload

    def authenticate_header(self, request) -> str:
        return self.keyword
