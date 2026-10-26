from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)

    @field_validator("jwt_secret_key")
    @classmethod
    def require_real_secret(cls, value: str) -> str:
        if value.startswith("replace-with-"):
            raise ValueError("Generate a random JWT_SECRET_KEY before starting")
        return value

    @field_validator("database_url")
    @classmethod
    def postgres_driver(cls, value: str) -> str:
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return value.replace(prefix, "postgresql+psycopg://", 1)
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use PostgreSQL")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
