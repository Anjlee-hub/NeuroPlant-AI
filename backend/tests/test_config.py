"""Environment-specific settings and CORS validation tests."""

import pytest
from app.core.config import Settings
from pydantic import ValidationError


def test_cors_origins_are_parsed_for_middleware():
    settings = Settings(
        environment="test",
        allowed_origins="https://farmer.example, https://admin.example",
    )
    assert settings.cors_allowed_origins == [
        "https://farmer.example",
        "https://admin.example",
    ]


def test_production_settings_reject_development_defaults():
    with pytest.raises(ValidationError, match="Invalid production configuration"):
        Settings(
            environment="production",
            database_url="sqlite+aiosqlite:///./neuroplant.db",
            allowed_origins="http://localhost:5173",
        )


def test_production_settings_accept_explicit_secure_dependencies():
    settings = Settings(
        environment="production",
        debug=False,
        database_url="postgresql+asyncpg://app:password@db.example/neuroplant",
        redis_url="rediss://cache.example:6379/0",
        celery_broker_url="rediss://cache.example:6379/1",
        celery_result_backend="rediss://cache.example:6379/2",
        celery_task_always_eager=False,
        rate_limit_enabled=True,
        storage_provider="s3",
        jwt_secret="a" * 40,
        jwt_refresh_secret="b" * 40,
        allowed_origins="https://app.example",
    )
    assert settings.is_production
    assert settings.cors_allowed_origins == ["https://app.example"]


def test_production_settings_reject_local_or_incomplete_service_urls():
    with pytest.raises(ValidationError, match="DATABASE_URL must include remote"):
        Settings(
            environment="production",
            database_url="postgresql+asyncpg://user@localhost/neuroplant",
            redis_url="redis://localhost:6379/0",
            celery_broker_url="redis://localhost:6379/0",
            celery_result_backend="redis://localhost:6379/0",
            celery_task_always_eager=False,
            rate_limit_enabled=True,
            storage_provider="s3",
            jwt_secret="a" * 40,
            jwt_refresh_secret="b" * 40,
            allowed_origins="https://app.example",
        )


def test_production_settings_reject_local_redis_with_valid_database_url():
    with pytest.raises(ValidationError, match="REDIS_URL must use a remote Redis URL"):
        Settings(
            environment="production",
            database_url="postgresql+asyncpg://user:pass@db.example/neuroplant",
            redis_url="redis://localhost:6379/0",
            celery_broker_url="rediss://cache.example:6379/1",
            celery_result_backend="rediss://cache.example:6379/2",
            celery_task_always_eager=False,
            rate_limit_enabled=True,
            storage_provider="s3",
            jwt_secret="a" * 40,
            jwt_refresh_secret="b" * 40,
            allowed_origins="https://app.example",
        )
