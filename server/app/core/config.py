"""Configuration centrale de l'application via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic import model_validator  # noqa: E402


class Settings(BaseSettings):
    """Lit la configuration depuis les variables d'environnement ou .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "production", "test"] = "development"
    app_name: str = "SUPMEAL"
    app_url: str = "http://localhost:5173"

    # Backend
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_cors_origins: str = "http://localhost:5173"

    # Securite
    secret_key: str = "dev-secret-CHANGE-ME-IN-PRODUCTION-please-use-random-64-chars"
    jwt_secret: str = "dev-jwt-secret-CHANGE-ME-IN-PRODUCTION-please-use-random-64-chars"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24h

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "supmeal"
    postgres_user: str = "supmeal"
    postgres_password: str = "supmeal"

    # Uploads
    upload_dir: str = "./uploads"
    max_upload_size_mb: int = 5

    # OAuth2 - Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/oauth/google/callback"

    # OAuth2 - GitHub
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/api/v1/auth/oauth/github/callback"

    # OAuth2 - Microsoft
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_redirect_uri: str = "http://localhost:8000/api/v1/auth/oauth/microsoft/callback"

    @model_validator(mode="after")
    def _check_secrets(self):
        if self.app_env == "production":
            for name in ("secret_key", "jwt_secret"):
                val = getattr(self, name, "")
                if not val or "CHANGE-ME" in val or len(val) < 32:
                    raise ValueError(
                        f"{name} doit etre defini (>=32 chars) en production"
                    )
        return self

    @field_validator("backend_cors_origins")
    @classmethod
    def parse_cors(cls, v: str) -> str:
        return v.strip()

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        """URL sync pour Alembic."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()