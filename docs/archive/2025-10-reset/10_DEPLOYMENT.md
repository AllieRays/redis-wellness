# Deployment

This document covers deployment strategies, Docker configuration, environment setup, and production considerations for Redis Wellness.

## Table of Contents
- [Quick Start](#quick-start)
- [Docker Architecture](#docker-architecture)
- [Environment Configuration](#environment-configuration)
- [Production Deployment](#production-deployment)
- [Monitoring & Maintenance](#monitoring--maintenance)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Local Development

**Prerequisites**:
- Docker & Docker Compose
- Ollama running on host (`ollama serve`)
- Required models pulled (`ollama pull qwen2.5:7b` + `mxbai-embed-large`)

**Start Application**:
```bash
# Quick start script
chmod +x start.sh
./start.sh

# Manual start
docker-compose up --build

# Detached mode
docker-compose up -d --build
```

**Access Points**:
- Frontend UI: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- RedisInsight: http://localhost:8001

---

## Docker Architecture

### Service Overview

```
┌──────────────────────────────────────────────────────────┐
│                     Docker Network                        │
│                   (wellness-network)                      │
│                                                            │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────┐ │
│  │   Frontend   │───▶│   Backend    │───▶│   Redis    │ │
│  │ TypeScript   │    │   FastAPI    │    │   Stack    │ │
│  │    :3000     │    │    :8000     │    │    :6379   │ │
│  └──────────────┘    └──────┬───────┘    │    :8001   │ │
│                              │            └────────────┘ │
│                              ▼                            │
│                     Ollama (Host)                         │
│                    :11434 (via host.docker.internal)      │
└──────────────────────────────────────────────────────────┘
```

### Services

**1. Redis Stack** (`redis-wellness`)
- **Image**: `redis/redis-stack:7.4.0-v1`
- **Ports**:
  - `6379` - Redis server
  - `8001` - RedisInsight UI
- **Volume**: `redis-data` for persistence
- **Health Check**: Redis PING every 5s
- **Persistence**: Saves every 60s if 1000+ keys changed

**2. Backend** (`redis-wellness-backend`)
- **Build**: `backend/Dockerfile`
- **Port**: `8000` - FastAPI server
- **Dependencies**: Redis (healthy), Ollama (host)
- **Host Access**: `host.docker.internal` for Ollama connection

**3. Frontend** (`redis-wellness-frontend`)
- **Build**: `frontend/Dockerfile`
- **Port**: `3000` - Vite dev server
- **Dependencies**: Backend

### Network Configuration

**Bridge Network** (`wellness-network`):
- Containers communicate via service names (DNS)
- Backend connects to Redis via `redis:6379`
- Frontend connects to backend via `backend:8000`
- Backend connects to host Ollama via `host.docker.internal:11434`

---

## Environment Configuration

### Backend Environment Variables

**Required**:
```bash
# Redis Configuration
REDIS_HOST=redis                      # Docker: "redis", Local: "localhost"
REDIS_PORT=6379
REDIS_DB=0

# Ollama Configuration
OLLAMA_HOST=http://host.docker.internal:11434   # Docker
OLLAMA_MODEL=qwen2.5:7b
EMBEDDING_MODEL=mxbai-embed-large

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
```

**Optional** (with defaults):
```bash
# TTL Configuration (7 months)
REDIS_SESSION_TTL_SECONDS=18144000         # 7 months
REDIS_HEALTH_DATA_TTL_SECONDS=18144000     # 7 months
REDIS_DEFAULT_TTL_DAYS=210                 # 7 months in days

# Token Management
MAX_CONTEXT_TOKENS=24000                    # 75% of 32k context window
TOKEN_USAGE_THRESHOLD=0.8                   # Trim at 80% capacity
MIN_MESSAGES_TO_KEEP=2                      # Keep 2+ recent messages

# User Context (Optional - for personalized responses)
USER_HEALTH_CONTEXT="Athletic 30yo, running focus, minor knee injury history"
```

### Docker Compose Configuration

**docker-compose.yml**:
```yaml
services:
  redis:
    image: redis/redis-stack:7.4.0-v1
    ports:
      - "6379:6379"
      - "8001:8001"
    volumes:
      - redis-data:/data
    environment:
      - REDIS_ARGS=--save 60 1000
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - OLLAMA_HOST=http://host.docker.internal:11434
      - APP_HOST=0.0.0.0
      - APP_PORT=8000
    depends_on:
      redis:
        condition: service_healthy
    extra_hosts:
      - "host.docker.internal:host-gateway"

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  redis-data:
```

### Local Development (.env)

Create `.env` in backend directory:
```bash
# .env (backend/.env)
REDIS_HOST=localhost
REDIS_PORT=6379
OLLAMA_HOST=http://localhost:11434

# Optional: User context for personalized responses
USER_HEALTH_CONTEXT="30yo runner, training for marathon, previous knee injury"
```

**Security Note**: Never commit `.env` files. Already in `.gitignore`.

---

## Production Deployment

### Production Considerations

**1. Security**:
- [ ] Use secrets management (HashiCorp Vault, AWS Secrets Manager)
- [ ] Enable Redis AUTH (password protection)
- [ ] Use HTTPS/TLS for all connections
- [ ] Implement API rate limiting
- [ ] Enable CORS only for trusted origins

**2. Scalability**:
- [ ] Horizontal scaling: Multiple backend replicas
- [ ] Redis clustering for high availability
- [ ] Load balancer in front of backends
- [ ] Separate read/write Redis instances (optional)

**3. Monitoring**:
- [ ] Application metrics (Prometheus + Grafana)
- [ ] Redis monitoring (RedisInsight or Prometheus exporter)
- [ ] Log aggregation (ELK stack or CloudWatch)
- [ ] Health check endpoints (`/health`, `/api/health/check`)

**4. Data Persistence**:
- [ ] Redis persistence enabled (RDB + AOF)
- [ ] Regular backups of Redis data
- [ ] Volume snapshots in production

### Production Docker Compose

**docker-compose.prod.yml**:
```yaml
version: "3.8"

services:
  redis:
    image: redis/redis-stack:7.4.0-v1
    container_name: redis-wellness-prod
    ports:
      - "6379:6379"
    volumes:
      - redis-data-prod:/data
    environment:
      - REDIS_ARGS=--save 300 10 --requirepass ${REDIS_PASSWORD}
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped
    networks:
      - wellness-network-prod

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    container_name: redis-wellness-backend-prod
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - OLLAMA_HOST=${OLLAMA_HOST}
      - APP_HOST=0.0.0.0
      - APP_PORT=8000
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - wellness-network-prod
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    container_name: redis-wellness-frontend-prod
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - wellness-network-prod

networks:
  wellness-network-prod:
    driver: bridge

volumes:
  redis-data-prod:
    driver: local
```

### Health Checks

**Application Health Endpoints**:
- **`GET /health`** - Comprehensive dependency checks
- **`GET /api/health/check`** - Simple Redis + Ollama check

**Response Example**:
```json
{
  "status": "healthy",
  "api": "healthy",
  "timestamp": 1729756800.5,
  "dependencies": {
    "redis": {
      "status": "healthy",
      "host": "redis",
      "port": 6379
    },
    "ollama": {
      "status": "healthy",
      "url": "http://host.docker.internal:11434",
      "models_required": ["qwen2.5:7b", "mxbai-embed-large"],
      "models_available": ["qwen2.5:7b", "mxbai-embed-large"],
      "models_missing": []
    }
  }
}
```

### Kubernetes Deployment (Optional)

**Deployment YAML** (example):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-wellness-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: redis-wellness-backend
  template:
    metadata:
      labels:
        app: redis-wellness-backend
    spec:
      containers:
      - name: backend
        image: redis-wellness-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_HOST
          value: "redis-service"
        - name: OLLAMA_HOST
          value: "http://ollama-service:11434"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

---

## Monitoring & Maintenance

### Application Logs

**View Logs**:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f redis

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Redis Monitoring

**RedisInsight UI**:
- Access: http://localhost:8001
- View keys, memory usage, commands
- Run Redis CLI commands
- Monitor slow queries

**Redis CLI**:
```bash
# Enter Redis container
docker exec -it redis-wellness redis-cli

# Check memory
INFO memory

# Key statistics
DBSIZE
INFO keyspace

# Monitor commands in real-time
MONITOR
```

### Performance Metrics

**Key Metrics to Monitor**:
- **Redis memory usage**: Should stay under 1GB for normal usage
- **API response times**: `response_time_ms` in chat responses
- **Token usage**: Monitor via `/api/chat/tokens/{session_id}`
- **Cache hit rate**: Check `/api/cache/embedding/stats`

### Backup & Restore

**Manual Redis Backup**:
```bash
# Trigger snapshot
docker exec redis-wellness redis-cli SAVE

# Copy backup file
docker cp redis-wellness:/data/dump.rdb ./backup/dump-$(date +%Y%m%d).rdb
```

**Restore from Backup**:
```bash
# Stop services
docker-compose down

# Replace dump file
docker cp ./backup/dump-20251024.rdb redis-wellness:/data/dump.rdb

# Restart
docker-compose up -d
```

---

## Troubleshooting

### Common Issues

**1. Backend can't connect to Redis**
```bash
# Check Redis is healthy
docker-compose ps
docker-compose logs redis

# Verify network
docker network inspect wellness-network

# Check Redis connectivity from backend
docker exec redis-wellness-backend ping redis
```

**2. Backend can't reach Ollama**
```bash
# Verify Ollama is running on host
curl http://localhost:11434

# Check host.docker.internal works
docker exec redis-wellness-backend curl http://host.docker.internal:11434

# Check models are pulled
ollama list
```

**3. Port conflicts**
```bash
# Check what's using port 3000/8000/6379
lsof -i :3000
lsof -i :8000
lsof -i :6379

# Kill process or change ports in docker-compose.yml
```

**4. Redis out of memory**
```bash
# Check memory usage
docker exec redis-wellness redis-cli INFO memory

# Clear specific keys
docker exec redis-wellness redis-cli FLUSHDB

# Restart with fresh state
docker-compose down -v
docker-compose up -d
```

### Service Restart

```bash
# Restart single service
docker-compose restart backend

# Rebuild after code changes
docker-compose up -d --build backend

# Full reset (removes volumes)
docker-compose down -v
docker-compose up -d --build
```

### Debug Mode

**Enable Debug Logging**:
```python
# backend/src/logging_config.py
import logging

# Set to DEBUG level
logging.basicConfig(level=logging.DEBUG)
```

**Check Container Logs**:
```bash
# Follow all logs
docker-compose logs -f

# Filter for errors
docker-compose logs backend 2>&1 | grep -i error
```

---

## Related Documentation

- [11_CONFIGURATION.md](11_CONFIGURATION.md) - Complete configuration reference
- [06_DEVELOPMENT.md](06_DEVELOPMENT.md) - Development workflow and local setup
- [13_FAQ.md](13_FAQ.md) - Common questions and troubleshooting

---

**Last Updated**: October 2025 (Phase 3 improvements)
