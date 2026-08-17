"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings required by the application infrastructure."""

    database_url: str
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=1440, ge=1)
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    transaction_agent_batch_size: int = Field(default=10, ge=1, le=100)
    transaction_agent_confidence_threshold: float = Field(default=0.85, ge=0, le=1)
    transaction_agent_max_batches_per_run: int = Field(default=10, ge=1, le=100)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings without logging sensitive values."""

    return Settings()
