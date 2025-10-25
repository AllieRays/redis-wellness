# Configuration

Complete reference for all configuration options in Redis Wellness.

## Table of Contents
- [Overview](#overview)
- [Environment Variables](#environment-variables)
- [Redis Configuration](#redis-configuration)
- [Ollama Configuration](#ollama-configuration)
- [Memory & Token Management](#memory--token-management)
- [Application Settings](#application-settings)
- [Configuration Files](#configuration-files)

---

## Overview

Redis Wellness uses environment variables for configuration with sensible defaults. Configuration is managed through:

1. **Environment variables** - Primary configuration method
2. **`.env` files** - Local development overrides
3. **`config.py`** - Default values and validation
4. **`docker-compose.yml`** - Container environment

**Configuration Loading Order** (highest priority first):
1. Environment variables
2. `.env` file in backend directory
3. Defaults in `backend/src/config.py`

---

## Environment Variables

### Required Variables

**Redis Connection**:
```bash
REDIS_HOST=redis              # Redis hostname (Docker: "redis", Local: "localhost")
REDIS_PORT=6379               # Redis port
REDIS_DB=0                    # Redis database number
```

**Ollama Connection**:
```bash
OLLAMA_HOST=http://host.docker.internal:11434   # Ollama API URL
OLLAMA_MODEL=qwen2.5:7b                         # Main LLM model
EMBEDDING_MODEL=mxbai-embed-large               # Embedding model
```

**Application**:
```bash
APP_HOST=0.0.0.0              # FastAPI host (0.0.0.0 for Docker, 127.0.0.1 for local)
APP_PORT=8000                 # FastAPI port
```

### Optional Variables

**TTL Configuration** (defaults to 7 months):
```bash
REDIS_SESSION_TTL_SECONDS=18144000         # 7 months = 210 days * 24h * 60m * 60s
REDIS_HEALTH_DATA_TTL_SECONDS=18144000     # Health data cache TTL
REDIS_DEFAULT_TTL_DAYS=210                 # Default TTL in days
```

**Context Window Management**:
```bash
MAX_CONTEXT_TOKENS=24000                    # Max tokens in context (75% of 32k)
TOKEN_USAGE_THRESHOLD=0.8                   # Trigger trimming at 80%
MIN_MESSAGES_TO_KEEP=2                      # Always keep 2+ recent messages
```

**User Health Context** (optional):
```bash
USER_HEALTH_CONTEXT="30yo runner, training for marathon, previous knee injury"
```

---

## Redis Configuration

### Connection Settings

**Redis URL** (alternative to host/port):
```bash
REDIS_URL=redis://localhost:6379/0
```

**Connection Parameters**:
```python
# backend/src/config.py
redis_host: str = "localhost"
redis_port: int = 6379
redis_db: int = 0
```

### Key Patterns

Redis Wellness uses structured key patterns for organization:

**Conversation History** (short-term memory):
```
conversation:{user_id}:{session_id}
TTL: 7 months (18,144,000 seconds)
Type: LIST
```

**Semantic Memory** (long-term):
```
memory:{user_id}:{timestamp}
TTL: 7 months
Type: HASH with vector embeddings
```

**Health Data**:
```
health:{metric_type}:{date}
TTL: 7 months
Type: HASH
```

**Embedding Cache**:
```
embedding_cache:{text_hash}
TTL: 7 days
Type: STRING (JSON)
```

### Redis Persistence

**RDB Snapshots** (configured in `docker-compose.yml`):
```yaml
environment:
  - REDIS_ARGS=--save 60 1000
```
- Saves snapshot every 60 seconds if 1000+ keys changed

**Production Recommendations**:
- Enable both RDB (snapshots) and AOF (append-only file)
- Configure regular backups
- Monitor memory usage (target < 1GB for demo)

---

## Ollama Configuration

### Model Requirements

**Main LLM**: Qwen 2.5 7B
```bash
# Pull model
ollama pull qwen2.5:7b

# Verify
ollama list | grep qwen2.5
```

**Embedding Model**: mxbai-embed-large
```bash
# Pull model
ollama pull mxbai-embed-large

# Verify
ollama list | grep mxbai
```

### Connection Settings

**Docker Environment**:
```bash
OLLAMA_HOST=http://host.docker.internal:11434
```

**Local Development**:
```bash
OLLAMA_HOST=http://localhost:11434
```

### Model Parameters

**Context Window**:
- Qwen 2.5 7B: ~32,000 tokens effective
- Configured max: 24,000 tokens (75% buffer)

**Embedding Dimensions**:
- mxbai-embed-large: 1024 dimensions

**Performance**:
- Generation speed: ~10-30 tokens/second (depends on hardware)
- Embedding generation: ~100ms per text chunk

---

## Memory & Token Management

### Context Window Management

**Settings**:
```python
# backend/src/config.py
max_context_tokens: int = 24000              # 75% of 32k context
token_usage_threshold: float = 0.8           # Trim at 80% capacity
min_messages_to_keep: int = 2                # Always keep 2+ messages
```

**Automatic Trimming**:
- Triggers when context exceeds `max_context_tokens * token_usage_threshold`
- Removes oldest messages first
- Always keeps minimum `min_messages_to_keep` messages
- Logs trimming operations

**Token Counting**:
```bash
# Check token usage for a session
curl http://localhost:8000/api/chat/tokens/demo?limit=10
```

### Memory TTL Strategy

**Why 7 Months?**
- Balances memory with utility
- Covers long-term health tracking
- Prevents unbounded Redis growth

**Customization**:
```bash
# Shorter TTL (30 days)
REDIS_SESSION_TTL_SECONDS=2592000
REDIS_HEALTH_DATA_TTL_SECONDS=2592000

# Longer TTL (1 year)
REDIS_SESSION_TTL_SECONDS=31536000
REDIS_HEALTH_DATA_TTL_SECONDS=31536000
```

### Embedding Cache

**Purpose**: Caches Ollama embedding generation to improve performance

**Settings**:
```python
# Configured in backend/src/services/embedding_cache.py
TTL: 7 days
Max cache size: Unlimited (relies on TTL for cleanup)
```

**Monitoring**:
```bash
# Check cache performance
curl http://localhost:8000/api/cache/embedding/stats
```

**Expected Performance**:
- Cache hit rate: 30-50% with repeated queries
- Time saved per hit: ~100ms
- Memory cost: ~4KB per cached embedding

---

## Application Settings

### FastAPI Configuration

**Host & Port**:
```bash
APP_HOST=0.0.0.0              # Bind to all interfaces
APP_PORT=8000                 # Default HTTP port
```

**CORS Configuration** (`backend/src/main.py`):
```python
allow_origins=[
    "http://localhost:3000",
    "http://frontend:3000",
    "http://127.0.0.1:3000",
]
allow_credentials=True
allow_methods=["*"]
allow_headers=["*"]
```

**Production CORS**:
```python
# Restrict to production domain
allow_origins=["https://yourdomain.com"]
```

### Logging Configuration

**Log Levels** (`backend/src/logging_config.py`):
```python
# Default: INFO level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**Change Log Level**:
```bash
# Debug mode
export LOG_LEVEL=DEBUG

# Error only
export LOG_LEVEL=ERROR
```

### User Health Context

**Purpose**: Optional personal context for AI responses

**Configuration**:
```bash
USER_HEALTH_CONTEXT="30yo male, recreational runner, training for half-marathon. Previous right knee meniscus injury (2023), now recovered."
```

**Privacy**:
- Stored only in `.env` file (never committed to git)
- Used for contextual responses
- Never logged or exposed in API responses
- Completely optional

---

## Configuration Files

### backend/src/config.py

**Full Configuration Class**:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings with validation."""

    # Application
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    # TTL Configuration
    redis_session_ttl_seconds: int = 18144000      # 7 months
    redis_health_data_ttl_seconds: int = 18144000  # 7 months
    redis_default_ttl_days: int = 210              # 7 months

    # Ollama
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:7b"
    embedding_model: str = "mxbai-embed-large"

    # User Context
    user_health_context: str = ""

    # Token Management
    max_context_tokens: int = 24000
    token_usage_threshold: float = 0.8
    min_messages_to_keep: int = 2

    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = ""
        extra = "allow"
```

### docker-compose.yml

**Environment Variables**:
```yaml
services:
  backend:
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - OLLAMA_HOST=http://host.docker.internal:11434
      - APP_HOST=0.0.0.0
      - APP_PORT=8000
      - REDIS_SESSION_TTL_SECONDS=18144000
      - REDIS_HEALTH_DATA_TTL_SECONDS=18144000
      - REDIS_DEFAULT_TTL_DAYS=210
```

### backend/.env (Example)

**Create for local development**:
```bash
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
EMBEDDING_MODEL=mxbai-embed-large

# Application
APP_HOST=127.0.0.1
APP_PORT=8000

# Optional: User Health Context
USER_HEALTH_CONTEXT="30yo runner, marathon training, previous knee injury"

# Optional: Custom TTL (30 days example)
# REDIS_SESSION_TTL_SECONDS=2592000
# REDIS_HEALTH_DATA_TTL_SECONDS=2592000
```

**⚠️ Security**: Never commit `.env` files! Already in `.gitignore`.

---

## Configuration Best Practices

### Development

✅ **Do**:
- Use `.env` file for local overrides
- Set `REDIS_HOST=localhost` for local Redis
- Set `OLLAMA_HOST=http://localhost:11434` for local Ollama
- Keep TTLs short for testing (e.g., 1 hour)

❌ **Don't**:
- Commit `.env` files
- Hardcode secrets in code
- Use production credentials locally

### Production

✅ **Do**:
- Use environment variables (not `.env` files)
- Enable Redis AUTH with password
- Use secrets management (Vault, AWS Secrets Manager)
- Set appropriate CORS origins
- Enable rate limiting
- Monitor memory usage
- Configure log rotation

❌ **Don't**:
- Expose Redis to public internet without AUTH
- Use default passwords
- Allow `allow_origins=["*"]` in CORS
- Ignore memory limits

---

## Configuration Validation

**Check Current Configuration**:
```bash
# Start application and check health endpoint
curl http://localhost:8000/health

# Response shows configuration status
{
  "status": "healthy",
  "dependencies": {
    "redis": {"status": "healthy", "host": "localhost", "port": 6379},
    "ollama": {
      "status": "healthy",
      "models_available": ["qwen2.5:7b", "mxbai-embed-large"]
    }
  }
}
```

**Common Issues**:
1. **Redis connection failed** → Check `REDIS_HOST` and `REDIS_PORT`
2. **Ollama unavailable** → Verify `OLLAMA_HOST` and `ollama serve` running
3. **Models missing** → Run `ollama pull qwen2.5:7b` and `ollama pull mxbai-embed-large`

---

## Related Documentation

- [10_DEPLOYMENT.md](10_DEPLOYMENT.md) - Deployment strategies and Docker setup
- [06_DEVELOPMENT.md](06_DEVELOPMENT.md) - Development workflow and local setup
- [13_FAQ.md](13_FAQ.md) - Common configuration questions

---

**Last Updated**: October 2025 (Phase 3 improvements)
