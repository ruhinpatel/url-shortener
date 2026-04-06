from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/urlshortener"
    redis_url: str = "redis://localhost:6379/0"
    base_url: str = "http://localhost:8000"
    default_cache_ttl_seconds: int = 86400  # 24h
    rate_limit_shorten_per_minute: int = 100
    rate_limit_redirect_per_minute: int = 1000
    short_code_min_length: int = 3
    short_code_max_length: int = 20

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
