"""Application configuration (12-factor).

All settings are read from environment variables with sensible defaults that
make the app runnable in *native dev mode* with zero external services
(SQLite + Celery eager). In production (Docker / Railway / Render) every value
is supplied via the environment or a mounted `.env`.
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── App ────────────────────────────────────────────────────────────
    app_name: str = "NeuroPlant AI"
    app_version: str = "0.1.0"
    environment: str = "development"  # development | staging | production
    debug: bool = False
    api_prefix: str = "/api/v1"

    # ── CORS ────────────────────────────────────────────────────────────
    allowed_origins: str = "http://localhost:5173,http://localhost:4173,http://localhost:8080"

    # ── Database ────────────────────────────────────────────────────────
    # Native dev falls back to SQLite (aiosqlite). Production always Postgres.
    database_url: str = "sqlite+aiosqlite:///./neuroplant.db"
    db_echo: bool = False

    # ── Redis / Celery ──────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    # Native dev runs tasks inline (no broker required) until Redis is present.
    celery_task_always_eager: bool = True

    # ── Auth ────────────────────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 14
    jwt_secret: str = Field(default="dev-secret-change-me-in-production")
    jwt_refresh_secret: str = Field(default="dev-refresh-secret-change-me-in-production")

    # ── Rate limiting ───────────────────────────────────────────────────
    rate_limit_enabled: bool = False  # degraded in native dev; enabled in prod

    # ── AI serving ──────────────────────────────────────────────────────
    # Path to the trained disease-model artifact (.keras). When the path is
    # missing the detection service falls back to the deterministic rule
    # baseline (provider="baseline").
    disease_model_path: str = "models/disease"
    disease_model_version: str = "baseline-v1"

    # ── Storage (S3 / R2 / MinIO) ───────────────────────────────────────
    storage_provider: str = "local"  # local | s3
    s3_endpoint_url: str | None = None
    s3_bucket: str = "neuroplant"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_public_base_url: str | None = None

    # ── External providers (optional at runtime — graceful degrade) ─────
    google_project_id: str | None = None
    google_credentials_json: str | None = None
    openweather_api_key: str | None = None
    razorpay_key_id: str | None = None
    razorpay_key_secret: str | None = None
    razorpay_webhook_secret: str | None = None
    llm_api_key: str | None = None
    llm_provider: str = "anthropic"  # anthropic | openai | google

    @field_validator("allowed_origins")
    @classmethod
    def _split_origins(cls, v: str) -> list[str]:
        return [o.strip() for o in v.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def uses_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    return Settings()
