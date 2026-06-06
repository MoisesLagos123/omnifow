"""Configuración por variables de entorno (Pydantic Settings)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # DB
    database_url: str = Field(..., alias="DATABASE_URL")

    # JWT
    jwt_private_key_path: Path = Field(Path("./keys/jwt_private.pem"), alias="JWT_PRIVATE_KEY_PATH")
    jwt_public_key_path: Path = Field(Path("./keys/jwt_public.pem"), alias="JWT_PUBLIC_KEY_PATH")
    jwt_issuer: str = Field("mini-erp", alias="JWT_ISSUER")
    jwt_audience: str = Field("mini-erp-api", alias="JWT_AUDIENCE")
    jwt_access_ttl_seconds: int = Field(900, alias="JWT_ACCESS_TTL_SECONDS")
    jwt_refresh_ttl_seconds: int = Field(604800, alias="JWT_REFRESH_TTL_SECONDS")

    # Auth policy
    login_max_failed_attempts: int = Field(5, alias="LOGIN_MAX_FAILED_ATTEMPTS")
    login_lock_minutes: int = Field(15, alias="LOGIN_LOCK_MINUTES")

    # Inventario — control de vencimiento
    dias_alerta_vencimiento_default: int = Field(
        30, alias="DIAS_ALERTA_VENCIMIENTO_DEFAULT"
    )

    # CORS
    cors_allow_origins: str = Field("http://localhost:5173", alias="CORS_ALLOW_ORIGINS")

    # App
    app_env: str = Field("dev", alias="APP_ENV")

    # Frontend (para construir links que incluimos en emails — ej. reset
    # password). Debe coincidir con el origen donde corre el frontend.
    frontend_base_url: str = Field(
        "http://localhost:5173", alias="FRONTEND_BASE_URL"
    )

    # Reset password
    reset_password_ttl_minutes: int = Field(
        60, alias="RESET_PASSWORD_TTL_MINUTES"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
