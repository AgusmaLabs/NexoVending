from nexo_vending.config import Settings, get_settings


def test_settings_defaults_are_vending_specific(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("API_PREFIX", raising=False)
    settings = Settings(_env_file=None)
    assert settings.app_name == "nexo-vending"
    assert "vending" in settings.database_url
    assert settings.api_prefix == ""


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b
    get_settings.cache_clear()
