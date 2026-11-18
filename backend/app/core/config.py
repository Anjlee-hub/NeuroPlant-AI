"""Application configuration (12-factor).

All settings are read from environment variables with sensible defaults that
make the app runnable in *native dev mode* with zero external services
(SQLite + Celery eager). In production (Docker / Railway / Render) every value
is supplied via the environment or a mounted `.env`.
"""

from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
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
    # Per-user scan-upload quota (token-bucket refill, in-process until Redis).
    rate_limit_scan_per_minute: int = 10
    # Per-user offline-sync quota — a separate budget from live uploads.
    rate_limit_scan_sync_per_minute: int = 10
    # Per-user marketplace-message quota (M4 Task 5) — bounds chat spam.
    rate_limit_messages_per_minute: int = 30

    # ── Scan uploads ─────────────────────────────────────────────────────
    scan_max_images: int = 5  # max images per POST /scans
    scan_inference_timeout_seconds: float = 30.0  # hard ceiling on one predict
    scan_sync_max_items: int = 50  # max scans per POST /scans/sync batch

    # ── AI serving ──────────────────────────────────────────────────────
    # Path to the trained disease-model artifact (.keras). When the path is
    # missing the detection service falls back to the deterministic rule
    # baseline (provider="baseline").
    disease_model_path: str = "models/disease"
    disease_model_version: str = "baseline-v1"

    # ── Image preprocessing (OpenCV pipeline) ───────────────────────────
    # Upload ceiling; dimension guards (decompression-bomb protection);
    # model input size; re-encode quality for stored/augmented images.
    preprocess_max_bytes: int = 15 * 1024 * 1024
    preprocess_max_dimension: int = 8000
    preprocess_min_dimension: int = 16
    preprocess_target_size: int = 224
    preprocess_jpeg_quality: int = 92

    # ── Storage (S3 / R2 / MinIO) ───────────────────────────────────────
    storage_provider: str = "local"  # local | s3
    # Where the local provider keeps user media (relative to the run dir).
    storage_local_dir: str = "storage"
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
    llm_model: str = "claude-sonnet-5"  # used by LLMConversationProvider (M3.1)

    # ── Weather (M5 Task 1) ─────────────────────────────────────────────
    # Provider: "mock" (deterministic offline source — the native-dev default
    # that needs no API key) or "openweather" (live source). When the live
    # source fails and fallback is enabled, WeatherService degrades to the mock
    # provider and marks the response ``is_fallback`` instead of erroring.
    weather_provider: str = "mock"
    weather_timeout_seconds: float = 5.0
    weather_fallback_enabled: bool = True

    @field_validator("allowed_origins")
    @classmethod
    def _split_origins(cls, v: str) -> str:
        origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        if not origins:
            raise ValueError("at least one allowed origin is required")
        return ",".join(origins)

    @model_validator(mode="after")
    def _validate_environment_configuration(self) -> "Settings":
        if self.environment not in {"development", "staging", "production", "test"}:
            raise ValueError("environment must be development, staging, production, or test")
        if not self.is_production:
            return self

        errors: list[str] = []
        if not self.uses_postgres:
            errors.append("DATABASE_URL must use PostgreSQL")
        else:
            try:
                database_url = urlsplit(self.database_url)
            except ValueError:
                database_url = None
            if (
                database_url is None
                or not database_url.hostname
                or not database_url.username
                or not database_url.password
                or database_url.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
            ):
                errors.append("DATABASE_URL must include remote PostgreSQL host and credentials")
        for setting_name, redis_url in (
            ("REDIS_URL", self.redis_url),
            ("CELERY_BROKER_URL", self.celery_broker_url),
            ("CELERY_RESULT_BACKEND", self.celery_result_backend),
        ):
            try:
                parsed_redis_url = urlsplit(redis_url)
            except ValueError:
                parsed_redis_url = None
            if (
                parsed_redis_url is None
                or parsed_redis_url.scheme not in {"redis", "rediss"}
                or not parsed_redis_url.hostname
                or parsed_redis_url.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
            ):
                errors.append(f"{setting_name} must use a remote Redis URL")
        if self.debug:
            errors.append("DEBUG must be false")
        if self.celery_task_always_eager:
            errors.append("CELERY_TASK_ALWAYS_EAGER must be false")
        if not self.rate_limit_enabled:
            errors.append("RATE_LIMIT_ENABLED must be true")
        if self.storage_provider != "s3":
            errors.append("STORAGE_PROVIDER must be s3")
        if len(self.jwt_secret) < 32 or self.jwt_secret.startswith("dev-"):
            errors.append("JWT_SECRET must be a non-default secret of at least 32 characters")
        if (
            len(self.jwt_refresh_secret) < 32
            or self.jwt_refresh_secret.startswith("dev-")
            or self.jwt_refresh_secret == self.jwt_secret
        ):
            errors.append(
                "JWT_REFRESH_SECRET must be distinct, non-default, and at least 32 characters"
            )
        origins = self.cors_allowed_origins
        if not origins or any("localhost" in origin or "127.0.0.1" in origin for origin in origins):
            errors.append("ALLOWED_ORIGINS must contain production origins, not localhost")
        if errors:
            raise ValueError("Invalid production configuration: " + "; ".join(errors))
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_allowed_origins(self) -> list[str]:
        """CORS middleware origins parsed from the comma-separated setting."""
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def uses_postgres(self) -> bool:
        return self.database_url.startswith("postgresql")


@lru_cache
def get_settings() -> Settings:
    return Settings()
