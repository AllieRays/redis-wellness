"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    app_host: str = "0.0.0.0"
    app_port: int = 8000

    redis_url: str = "redis://localhost:6379"
    redis_host: str = "localhost"  # Use localhost for local testing, override with REDIS_HOST=redis in Docker
    redis_port: int = 6379
    redis_db: int = 0

    # TTL Configuration (7 months = ~18,144,000 seconds)
    redis_session_ttl_seconds: int = 18144000  # 7 months
    redis_health_data_ttl_seconds: int = 18144000  # 7 months
    redis_default_ttl_days: int = 210  # 7 months in days

    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:7b"
    embedding_model: str = "mxbai-embed-large"

    # User health context (personal medical history, injuries, goals)
    # Set in .env file - keeps personal health data private and out of git
    user_health_context: str = ""

    # Token limits for context management
    # Qwen 2.5 7B has ~32k effective context window
    max_context_tokens: int = 24000  # Conservative limit (75% of 32k)
    token_usage_threshold: float = 0.8  # Trigger trimming at 80% of max
    min_messages_to_keep: int = 2  # Always keep at least 2 recent messages

    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = ""
        extra = "allow"  # Allow extra fields from .env


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
