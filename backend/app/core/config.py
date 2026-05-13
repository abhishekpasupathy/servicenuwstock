from functools import lru_cache

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NOW Intelligence API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    backend_cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000"
    )
    sqlite_path: str = "./data/now_intelligence.sqlite"
    cache_ttl_seconds: int = 300
    market_cache_ttl_seconds: int = 1800
    market_fallback_cache_ttl_seconds: int = 600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.backend_cors_origins.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.app_env.lower() == "production":
            invalid_origins = {
                "*",
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            }
            if not self.cors_origins or invalid_origins.intersection(self.cors_origins):
                raise ValueError(
                    "Production BACKEND_CORS_ORIGINS must contain only deployed frontend origins."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
