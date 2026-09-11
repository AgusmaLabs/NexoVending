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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
