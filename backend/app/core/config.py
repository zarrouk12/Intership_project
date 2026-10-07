"""Configuration centrale de l'application (Pydantic Settings v2)."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    PROJECT_NAME: str = "Medicacom AOI Transformation"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+psycopg2://odoo:odoo@localhost:5432/medicacom"

    SECRET_KEY: str = "dev-secret-key-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    # Chaine separee par des virgules : evite tout decodage JSON implicite du .env
    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    FIRST_SUPERUSER_EMAIL: str = "admin@medicacom.com"
    FIRST_SUPERUSER_PASSWORD: str = "medicacom2026"

    # development | production. En production, l'aide aux comptes de demonstration
    # disparait de l'API : aucune liste de comptes ne peut fuiter par l'interface.
    ENVIRONMENT: str = "development"
    # Mot de passe commun aux comptes du seed, publie par l'aide de developpement.
    # Laisser vide pour ne jamais l'exposer, meme en developpement.
    DEMO_PASSWORD: str = ""

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in {"development", "dev", "local"}

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
