"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    app_host: str = "0.0.0.0"
    app_port: int = 8000

    redis_url: str = "redis://redis:6379"
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    # TTL Configuration (7 months = ~18,144,000 seconds)
    redis_session_ttl_seconds: int = 18144000  # 7 months
    redis_health_data_ttl_seconds: int = 18144000  # 7 months
    redis_default_ttl_days: int = 210  # 7 months in days

    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:7b"
    embedding_model: str = "mxbai-embed-large"

    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = ""
        extra = "allow"  # Allow extra fields from .env


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
