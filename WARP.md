# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Architecture Overview

This is a **side-by-side demo** comparing **stateless chat** vs. **agentic RAG chat** powered by Redis and RedisVL. The system demonstrates the transformative power of memory in AI conversations through:

- **Frontend**: TypeScript + Vite (port 3000)
- **Backend**: FastAPI Python (port 8000) with LangGraph agentic workflows
- **Storage**: Redis Stack with RedisVL vector search (ports 6379, 8001)
- **LLM**: Qwen 2.5 7B + mxbai-embed-large via Ollama (port 11434)

The application showcases **dual memory systems**: short-term conversation history and long-term semantic memory with vector search.

```
                           Docker Network
┌──────────────────────────────────────────────────────────┐
│                                                           │
│  Frontend (TS+Vite) ────→ Backend (FastAPI) ───→ Redis   │
│       :3000                    :8000             :6379    │
│                                  ↓                        │
│                         LangGraph Agent                   │
│                              ↓                            │
│                           Ollama (Host)                   │
│                              :11434                       │
└───────────────────────────────────────────────────────────┘

Redis/RedisVL stores:
- Short-term memory (conversation history)
- Long-term memory (semantic vector search)
- Health data cache (7-month TTL)
```

## Key Components

**Backend Structure (`/backend/src/`)**:

- `main.py` - FastAPI application with CORS middleware
- `api/chat_routes.py` - Core chat endpoints (stateless vs. Redis comparison)
- `api/agent_routes.py` - Direct tool endpoints for testing
- `agents/health_rag_agent.py` - LangGraph agentic workflow
- `agents/query_classifier.py` - Intelligent tool routing layer
- `agents/memory_manager.py` - RedisVL dual memory system
- `agents/tool_wrappers.py` - Health data tools integration
- `services/redis_chat.py` - RAG chat service with memory
- `services/stateless_chat.py` - No-memory baseline service
- `parsers/apple_health_parser.py` - Apple Health XML parsing
- `tools/` - Health insights, math, and performance tools

**Frontend Structure (`/frontend/src/`)**:

- `main.ts` - Chat UI with side-by-side comparison
- `api.ts` - Backend API client with TypeScript
- `types.ts` - TypeScript interfaces for API communication
- `style.css` - Modern chat UI styling

**Documentation (`/docs/`)**:

- `QWEN_TOOL_CALLING_IMPLEMENTATION_PLAN.md` - LangGraph + Qwen implementation
- `INTELLIGENT_HEALTH_TOOLS_PLAN.md` - Agentic health tools design
- `RAG_IMPLEMENTATION.md` - RedisVL memory architecture
- `linting.md` - Code quality and pre-commit setup

## Development Commands

### Environment Setup

```bash
# Quick start (recommended)
chmod +x start.sh
./start.sh

# Manual start
docker-compose up --build
```

### Prerequisites Check

```bash
# Verify Docker is running
docker info

# Check if Ollama is running
curl http://localhost:11434

# Install and start Ollama if needed
brew install ollama  # macOS
ollama serve

# Pull required models
ollama pull qwen2.5:7b              # Main LLM (4.7 GB)
ollama pull mxbai-embed-large       # Embeddings (669 MB)
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
# Backend uses uv for dependency management
uv sync                              # Install dependencies
uv run python -m backend.src.main   # Run development server

# API documentation available at:
# http://localhost:8000/docs (Swagger)
# http://localhost:8000/redoc (ReDoc)
```

### Testing

```bash
# Run all tests
uv run pytest tests/

# Test specific components
uv run pytest tests/unit/test_redis_chat_rag.py
uv run pytest tests/unit/test_health_parsing.py
uv run pytest tests/test_redis_chat_api.py

# Health check endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/chat/demo/info
```

### Code Quality

```bash
# Run all linting and formatting
./lint.sh

# Backend linting (Ruff + Black)
cd backend
uv run ruff check --fix src ../tests
uv run ruff format src ../tests

# Frontend linting (ESLint + Prettier)
cd frontend
npm run typecheck
npm run lint
npm run format
```

### Health Data Integration

```bash
# Upload Apple Health export
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@export.xml"
```

## Development Notes

### Redis Usage

Redis stores dual memory system and health data:

```python
# Short-term memory (conversation history)
conversation:{session_id} → [msg1, msg2, msg3...]
TTL: 7 months

# Long-term memory (semantic search with RedisVL)
memory:{user_id}:{timestamp} → {
    "text": "User's BMI goal is 22",
    "embedding": [0.234, -0.123, ...],  # 1024 dimensions
    "metadata": {...}
}

# Health data cache
health:{metric_type}:{date} → {value, unit, source}
TTL: 7 months
```

### API Structure

**Core Demo Endpoints:**
- `/api/chat/stateless` - Stateless chat (no memory)
- `/api/chat/redis` - RAG chat with full memory
- `/api/chat/demo/info` - Demo comparison documentation

**Memory Management:**
- `/api/chat/history/{session_id}` - View conversation history
- `/api/chat/memory/{session_id}` - Memory statistics
- `/api/chat/session/{session_id}` - Clear session (DELETE)

**Health Data:**
- `/api/health/upload` - Upload Apple Health XML
- `/api/agent/search-health` - Direct health tool access
- `/api/agent/aggregate-metrics` - Health data aggregation
- `/api/agent/search-workouts` - Workout data retrieval

### Docker Network

Services communicate via `wellness-network` bridge network. Backend connects to host Ollama using `host.docker.internal`.

### LangGraph Agentic System

Key features of the agentic workflow:

- **Query Classification**: Intelligent tool routing layer
- **3 Specialized Tools**: Health data retrieval, aggregation, workouts
- **Dual Memory**: Short-term + long-term semantic memory
- **Tool Calling**: Qwen 2.5 7B optimized for function calling
- **State Management**: LangGraph handles multi-step workflows

### TypeScript Frontend

Modern vanilla TypeScript with Vite featuring:

- Side-by-side chat comparison UI
- Real-time health status monitoring
- Session management with memory statistics
- Tool call visualization
- XSS protection with proper HTML escaping

### Privacy Architecture

- All data stays local (Redis + Ollama)
- No external API calls
- Health data never leaves your machine
- Self-contained Docker environment

### Development Dependencies

- **Docker & Docker Compose** - Container orchestration
- **Ollama** - Local LLM inference (Qwen 2.5 7B + embeddings)
- **uv** - Fast Python dependency management
- **Node.js** - Frontend build tools (TypeScript + Vite)
- **Redis Stack** - In-memory database with vector search

## Access Points

- **Frontend Demo UI**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **RedisInsight**: http://localhost:8001
- **Health Check**: http://localhost:8000/health
- **Demo Info**: http://localhost:8000/api/chat/demo/info

## Demo Usage

### Try the Memory Comparison

**Stateless Chat** (forgets context):
```bash
curl -X POST http://localhost:8000/api/chat/stateless \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my average heart rate last week?"}'
  
# Follow-up fails: "Is that good?" → "What are you referring to?"
```

**Redis RAG Chat** (remembers context):
```bash
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my average heart rate last week?", "session_id": "demo"}'
  
# Follow-up works: "Is that good?" → "87 bpm is within normal range..."
```

### Load Health Data

```bash
# Upload Apple Health export
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@export.xml"
```

The application demonstrates how Redis + RedisVL transforms stateless chat into context-aware, memory-powered health insights using **100% local processing**.
