from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from nexo_vending.versioning import API_PREFIX


class Settings(BaseSettings):
    """Vending-specific runtime configuration.

    Platform concerns stay in nexo-platform; this settings object only covers
    the vending product process.
    """

    app_name: str = "nexo-vending"
    app_env: str = "dev"
    database_url: str = "postgresql+psycopg://vending:vending@localhost:5432/vending"
    api_prefix: str = API_PREFIX
    log_level: str = "INFO"

    # Session JWT (Platform JwtService) — prefer RS256 in production.
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "nexo"
    jwt_secret: str | None = "dev-only-change-me"
    jwt_private_key: str | None = None
    jwt_public_key: str | None = None
    jwt_key_id: str | None = None
    jwt_expires_in: int = 3600

    # Google OIDC (composition-root only; wires Platform GoogleOAuthProvider).
    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
