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

    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.1"

    class Config:
        env_file = ".env"


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
