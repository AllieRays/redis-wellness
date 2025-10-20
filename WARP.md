# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Architecture Overview

This is a privacy-first wellness application with Redis-powered conversational memory. The system uses Docker containers with:

- **Frontend**: TypeScript + Vite (port 3000)
- **Backend**: FastAPI Python (port 8000)
- **Storage**: Redis Stack with RedisInsight (ports 6379, 8001)
- **LLM**: Ollama running on host (port 11434)

The application demonstrates how Redis provides conversational memory for AI-powered health insights using local LLMs - no external API calls.

```
Frontend (TS+Vite) ──→ Backend (FastAPI) ──→ Redis
     :3000                    :8000           :6379
                               ↓
                        Ollama (Host)
                           :11434
```

## Key Components

**Backend Structure (`/src/` and `/backend/src/`)**:

- `main.py` - FastAPI application with CORS middleware
- `api/routes.py` - API endpoint definitions (import referenced but may not exist yet)
- `config.py` - Settings configuration (imported but may not exist yet)
- `services/` - Redis and Ollama service integrations
- `models/` - Pydantic schemas for data validation
- `parsers/` - Apple Health XML parsing utilities

**Frontend Structure (`/frontend/src/`)**:

- `main.ts` - Chat UI logic and DOM manipulation
- `api.ts` - Backend API client with TypeScript
- `types.ts` - TypeScript interfaces for API communication
- `style.css` - UI styling

**Static Web UI**: `/static/index.html` - Standalone HTML UI served by FastAPI

## Development Commands

### Environment Setup

```bash
# Quick start (recommended)
./start.sh

# Manual start
docker-compose up --build
```

### Prerequisites Check

```bash
# Verify Docker is running
docker info

# Check if Ollama is running
curl -s http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve
ollama pull llama3.1
```

### Service Management

```bash
# Stop all services
docker-compose down

# Stop and clear Redis data
docker-compose down -v

# View logs
docker-compose logs -f
docker-compose logs -f backend
docker-compose logs -f frontend

# Check service status
docker-compose ps
```

### Frontend Development

```bash
cd frontend
npm run dev      # Development server
npm run build    # Build for production
npm run preview  # Preview production build
```

### Backend Development

```bash
# The backend uses uv for dependency management
uv sync          # Install dependencies
uv run python -m src.main  # Run development server

# API documentation available at:
# http://localhost:8000/docs (Swagger)
# http://localhost:8000/redoc (ReDoc)
```

### Testing

```bash
# Run tests (pytest-based)
uv run pytest tests/

# Test specific file
uv run pytest tests/test_api.py

# Health check endpoint test
curl http://localhost:8000/api/health/check
```

### Health Data Integration

```bash
# Upload Apple Health export
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@export.xml"
```

## Development Notes

### Redis Usage

Redis stores conversation history, health data cache, and session management:

```python
conversation:{session_id}:{message_id} → {role, content, timestamp}
health:{metric_type}:{date} → {value, unit, source}
```

### API Structure

- All API routes prefixed with `/api`
- Health check endpoint: `/api/health/check`
- Chat endpoint: `/api/chat`
- Health upload: `/api/health/upload`

### Docker Network

Services communicate via `wellness-network` bridge network. Backend connects to host Ollama using `host.docker.internal`.

### TypeScript Frontend

Uses vanilla TypeScript with Vite - no frameworks. Key features:

- Real-time chat interface
- Health status monitoring (Redis/Ollama connectivity)
- Session management with persistent conversation history
- XSS protection with HTML escaping

### Privacy Architecture

- All data stays local (Redis + Ollama)
- No external API calls
- Health data never leaves your machine
- Self-contained Docker environment

### Development Dependencies

- **Docker & Docker Compose** - Container orchestration
- **Ollama** - Local LLM inference (runs on host, not in container)
- **uv** - Python dependency management (faster than pip)

## Access Points

- **Frontend UI**: http://localhost:3000
- **Web UI**: http://localhost:8000/static/index.html
- **API Docs**: http://localhost:8000/docs
- **RedisInsight**: http://localhost:8001
- **Root API**: http://localhost:8000/

The application demonstrates Redis as a memory layer for stateful AI conversations, transforming simple chat into context-aware health insights.
