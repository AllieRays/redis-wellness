# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Architecture Overview

This is a **side-by-side demo** comparing **stateless chat** vs. **agentic RAG chat** powered by Redis and RedisVL. The system demonstrates the transformative power of memory in AI conversations through:

- **Frontend**: TypeScript + Vite (port 3000)
- **Backend**: FastAPI Python (port 8000) with agentic tool-calling loops
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
│                      Agentic Tool Loop (simple)           │
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

**Backend Structure (`/backend/src/`)** - Clean Architecture:

**Core Application:**
- `main.py` - FastAPI application with CORS middleware
- `config.py` - Application configuration and settings

**API Layer (`/api/`):**
- `chat_routes.py` - Core chat endpoints (stateless vs. Redis comparison)
- `system_routes.py` - Main router aggregation and system health

**AI Agents (`/agents/`)** - Two agents for demo comparison:
- `stateless_agent.py` - Baseline agent with NO memory (simple tool loop)
- `stateful_rag_agent.py` - Full Redis + RedisVL memory agent (simple tool loop)
- `__init__.py` - Agent exports

Both agents use the same simple tool-calling loop pattern for maintainability.

**Apple Health Module (`/apple_health/`)** - Complete Apple Health data processing:
- `models.py` - Pydantic models (HealthRecord, WorkoutSummary, etc.)
- `parser.py` - Secure XML parsing with validation
- `query_tools/` - LangChain tools for AI queries (9 tools: search, aggregate, workouts, patterns, trends)
- `__init__.py` - Clean module exports

**Services (`/services/`)** - Data layer and business logic:
- `redis_chat.py` - RAG chat service with dual memory
- `stateless_chat.py` - No-memory baseline service
- `memory_manager.py` - RedisVL dual memory system (short + long-term)
- `redis_connection.py` - Production-ready Redis connection management
- `redis_workout_indexer.py` - Fast Redis workout indexes (O(1) aggregations)
- `redis_apple_health_manager.py` - Redis CRUD operations for Apple Health data
- `embedding_cache.py` - Embedding cache for performance

**Utils (`/utils/`)** - Pure utilities and helpers:
- `agent_helpers.py` - Shared agent utilities (LLM, prompts, message handling)
- `numeric_validator.py` - LLM hallucination detection and validation
- `workout_fetchers.py` - Workout data fetching from Redis indexes
- `metric_aggregators.py` - Health metric aggregation utilities
- `base.py` - Base classes, decorators, and error handling
- `stats_utils.py` - Statistical calculation utilities
- `time_utils.py` - Time parsing and date utilities
- `health_analytics.py` - Health trend analysis functions

**Frontend Structure (`/frontend/src/`)**:

- `main.ts` - Chat UI with side-by-side comparison
- `api.ts` - Backend API client with TypeScript
- `types.ts` - TypeScript interfaces for API communication
- `style.css` - Modern chat UI styling

**Documentation (`/docs/`)**:

- `HEALTH_DATA_PIPELINE.md` - Apple Health XML → Redis pipeline
- `REORGANIZATION_SUMMARY.md` - Project structure cleanup (Oct 2025)
- `LANGGRAPH_REMOVAL_PLAN.md` - Why we removed LangGraph and use simple loops
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

**All tests moved to `/backend/tests/` for proper monorepo structure:**

```bash
# Run all backend tests
cd backend
uv run pytest tests/

# Unit tests (no external dependencies)
uv run pytest tests/unit/

# Integration tests (require Redis/services)
uv run pytest tests/ -k "not unit"

# Specific test categories
uv run pytest tests/unit/test_numeric_validator.py  # Validation logic
uv run pytest tests/unit/test_math_tools.py         # Mathematical functions
uv run pytest tests/unit/test_stateless_isolation.py # Pure function tests
uv run pytest tests/test_redis_chat_rag.py          # RAG memory system
uv run pytest tests/test_redis_chat_api.py          # HTTP API integration

# Health check endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/chat/demo/info
```

### Code Quality

```bash
# Run all linting and formatting
./lint.sh

# Backend linting (Ruff + Black) - Updated paths
cd backend
uv run ruff check --fix src tests  # Tests now in backend/tests
uv run ruff format src tests

# Frontend linting (ESLint + Prettier)
cd frontend
npm run typecheck
npm run lint
npm run format

# Pre-commit hooks (run automatically on commit)
git commit -m "your message"  # Triggers all quality checks
```

### Health Data Integration

```bash
# Upload Apple Health export
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@export.xml"
```

## Development Notes

### Project Structure (Updated October 2025)

**Consolidated Apple Health module** for clarity and maintainability:

- **`/apple_health/`**: All Apple Health data processing (models, parser, tools, queries)
- **`/agents/`**: AI agents (simple tool-calling loops)
- **`/services/`**: Data layer services (Redis, memory, vectorization)
- **`/utils/`**: Pure utilities and helpers (math, validation, classification)
- **`/api/`**: HTTP endpoints and request/response models
- **`/backend/tests/`**: All tests in proper monorepo structure

This structure ensures clear boundaries between:
- Apple Health processing (apple_health)
- AI logic (agents with simple loops)
- Data operations (services)
- Pure functions (utils)
- LLM-callable tools (query_tools)

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
- Import via `import_health.py` script (not HTTP endpoint)
- Data automatically indexed in Redis on import
- Semantic memory cleared on import to prevent stale data

### Docker Network

Services communicate via `wellness-network` bridge network. Backend connects to host Ollama using `host.docker.internal`.

### Agentic Tool-Calling System

Key features of the agentic workflow:

- **Tool-First Policy**: Factual queries skip semantic memory to avoid stale cache
- **9 Specialized Tools**: Health records, workouts, patterns, comparisons, trends, progress
- **Dual Memory**: Short-term conversation + long-term context (Redis + RedisVL)
- **Tool Calling**: Qwen 2.5 7B optimized for function calling
- **Simple Loop**: Up to 8 iterations for complex multi-step queries
- **Autonomous**: LLM decides which tools to call, chains them, decides when done
- **Memory Clearing**: Import script clears semantic memory to prevent stale data

**Why Simple Loop, Not LangGraph?**
- Redis already handles persistence (no need for checkpointers)
- Queries complete in one turn (~3-15 seconds)
- Simpler to debug and maintain
- Same agentic behavior: autonomous tool selection, chaining, and decision-making
- See `/docs/LANGGRAPH_REMOVAL_PLAN.md` for full analysis

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
