from functools import lru_cache
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NOW Terminal API"
    api_prefix: str = "/api"
    app_env: str = "development"
    postgres_url: str = "postgresql+asyncpg://now:nowpass@localhost:5432/nowdb"
    redis_url: str = "redis://localhost:6379/0"
    alpha_vantage_key: str | None = None
    default_ticker: str = "NOW"
    sqlite_path: str = "./data/dadstock.sqlite"
    cache_ttl_seconds: int = 300
    market_cache_ttl_seconds: int = 1800
    market_fallback_cache_ttl_seconds: int = 600
    cache_quote_ttl: int = 60
    cache_ohlcv_ttl: int = 300
    cache_fundamentals_ttl: int = 21600
    backend_cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @computed_field
    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
