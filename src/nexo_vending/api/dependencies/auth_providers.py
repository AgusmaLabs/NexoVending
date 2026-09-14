"""Composition-root auth providers (Platform JwtService + AuthenticationProvider).

GoogleOAuthProvider is INTERNAL to Platform and may only be imported here.
"""

from __future__ import annotations

from nexo_platform.identity import AuthenticationProvider, JwtService

from nexo_vending.config import Settings


def build_jwt_service(settings: Settings) -> JwtService:
    algorithm = str(settings.jwt_algorithm).strip().upper() or "HS256"
    if algorithm == "RS256":
        return JwtService(
            algorithm="RS256",
            issuer=settings.jwt_issuer,
            private_key=settings.jwt_private_key,
            public_key=settings.jwt_public_key,
            key_id=settings.jwt_key_id,
        )
    return JwtService(
        secret=settings.jwt_secret,
        algorithm="HS256",
        issuer=settings.jwt_issuer,
    )


def build_authentication_provider(settings: Settings) -> AuthenticationProvider | None:
    """Wire Platform Google adapter when OIDC settings are present."""
    client_id = (settings.google_client_id or "").strip()
    client_secret = (settings.google_client_secret or "").strip()
    redirect_uri = (settings.google_redirect_uri or "").strip()
    if not client_id or not client_secret or not redirect_uri:
        return None

    from nexo_platform.identity.infrastructure.oauth.google import (  # noqa: PLC0415
        GoogleOAuthProvider,
        GoogleOAuthSettings,
    )

    google_settings = GoogleOAuthSettings(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )
    return GoogleOAuthProvider(google_settings)
