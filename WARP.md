# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Status

**🎯 NEARING COMPLETION** - This project is in **final polish phase**. Core functionality is complete and stable.

### Completed ✅
- ✅ Full stateless vs. stateful agent comparison working
- ✅ Four-layer memory architecture (short-term, episodic, procedural, semantic)
- ✅ 13 comprehensive documentation files in `/docs/`
- ✅ Complete test suite (unit, integration, API, LLM)
- ✅ Apple Health data pipeline with Redis indexing
- ✅ LangGraph checkpointing for conversation state
- ✅ 11 LangChain tools (9 health + 2 memory)
- ✅ TypeScript frontend with SSE streaming
- ✅ Full Docker deployment with health checks
- ✅ Makefile with comprehensive commands
- ✅ Pre-commit and pre-push hooks
- ✅ 100% local privacy (Ollama + Redis)

### Focus Areas for Final Polish
- 🎨 Documentation refinement (cross-references, formatting)
- 🧪 Edge case testing and validation
- 📊 Performance optimization (if needed)
- 🐛 Bug fixes from user testing
- 📝 README and doc examples verification

**Primary Goal**: Production-ready demo showcasing Redis + RedisVL for AI agent memory systems.

---

## Architecture Overview

This is a **side-by-side demo** comparing **stateless chat** vs. **agentic RAG chat** powered by Redis and RedisVL. The system demonstrates the transformative power of memory in AI conversations through:

- **Frontend**: TypeScript + Vite (port 3000)
- **Backend**: FastAPI Python (port 8000) with agentic tool-calling loops
- **Storage**: Redis Stack with RedisVL vector search (ports 6379, 8001)
- **LLM**: Qwen 2.5 7B + mxbai-embed-large via Ollama (port 11434)

The application showcases **four-layer memory architecture**: short-term (conversation checkpointing), episodic (user goals), procedural (workflow patterns), and semantic (optional health knowledge) memory.

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
- Short-term memory (LangGraph checkpointing for conversation)
- Episodic memory (user goals via vector search)
- Procedural memory (workflow patterns via vector search)
- Semantic memory (optional health knowledge base)
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
- `stateful_rag_agent.py` - Full Redis + RedisVL memory agent (LangGraph workflow)
- `__init__.py` - Agent exports

Stateless uses simple loop; stateful uses LangGraph StateGraph with checkpointing.

**Apple Health Module (`/apple_health/`)** - Complete Apple Health data processing:
- `models.py` - Pydantic models (HealthRecord, WorkoutSummary, etc.)
- `parser.py` - Secure XML parsing with validation
- `tool_models.py` - Pydantic models for tool inputs/outputs
- `query_tools/` - LangChain tools for AI queries (5 tools: 3 health + 2 memory):
  - `get_health_metrics.py` - All non-sleep, non-workout health data (heart rate, steps, weight, BMI, trends)
  - `get_sleep_analysis.py` - Sleep data with daily aggregation and efficiency metrics
  - `get_workout_data.py` - ALL workout queries (lists, patterns, progress, comparisons) - consolidated tool
  - `memory_tools.py` - Goal and procedural memory (get_my_goals, get_tool_suggestions)
- `__init__.py` - Clean module exports

**Services (`/services/`)** - Data layer and business logic:
- `redis_chat.py` - RAG chat service with triple memory system
- `stateless_chat.py` - No-memory baseline service
- `episodic_memory_manager.py` - Short-term conversation memory
- `semantic_memory_manager.py` - Long-term semantic memory (RedisVL)
- `procedural_memory_manager.py` - Goal tracking and user preferences
- `redis_connection.py` - Production-ready Redis connection management
- `redis_workout_indexer.py` - Fast Redis workout indexes (O(1) aggregations)
- `redis_apple_health_manager.py` - Redis CRUD operations for Apple Health data
- `embedding_service.py` - Embedding generation and caching

**Utils (`/utils/`)** - Pure utilities and helpers:
- `agent_helpers.py` - Shared agent utilities (LLM, prompts, message handling)
- `numeric_validator.py` - LLM hallucination detection and validation
- `workout_fetchers.py` - Workout data fetching from Redis indexes
- `metric_aggregators.py` - Health metric aggregation utilities
- `base.py` - Base classes, decorators, and error handling
- `stats_utils.py` - Statistical calculation utilities
- `time_utils.py` - Time parsing and date utilities
- `health_analytics.py` - Health trend analysis functions
- `api_errors.py` - API error handling
- `conversation_fact_extractor.py` - Extract facts from conversations for semantic memory
- `conversion_utils.py` - Unit conversion utilities
- `date_validator.py` - Date validation logic
- `exceptions.py` - Custom exception classes
- `intent_router.py` - Route user intents to appropriate tools
- `metric_classifier.py` - Classify health metrics
- `pronoun_resolver.py` - Resolve pronouns in user queries
- `redis_keys.py` - Centralized Redis key management
- `token_manager.py` - Token counting and management
- `user_config.py` - User configuration management
- `verbosity_detector.py` - Detect user preference for verbose/concise responses

**Frontend Structure (`/frontend/src/`)**:

- `main.ts` - Chat UI with side-by-side comparison
- `api.ts` - Backend API client with TypeScript
- `types.ts` - TypeScript interfaces for API communication
- `constants.ts` - Frontend constants and configuration
- `stats.ts` - Memory statistics tracking and display
- `streaming.ts` - Server-sent events (SSE) streaming handler
- `style.css` - Modern chat UI styling
- `utils/` - Frontend utilities:
  - `sanitizer.ts` - XSS protection and HTML sanitization
  - `ui.ts` - UI helper functions

**Documentation (`/docs/`)** - 13 comprehensive guides:

- `01_PREREQUISITES.md` - Complete setup guide (Docker, Ollama, Apple Health)
- `02_QUICKSTART.md` - Get running in under 5 minutes
- `03_STATELESS_AGENT.md` - Simple tool loop without memory
- `04_STATEFUL_AGENT.md` - LangGraph agent with four-layer memory
- `05_STATELESS_VS_STATEFUL_COMPARISON.md` - Side-by-side comparison
- `06_AGENTIC_RAG.md` - Autonomous RAG architecture and workflow
- `07_HOW_TO_IMPORT_APPLE_HEALTH_DATA.md` - Data pipeline and import
- `08_QWEN_BEST_PRACTICES.md` - Tool calling optimization for Qwen 2.5
- `09_EXAMPLE_QUERIES.md` - Curated example queries
- `10_MEMORY_ARCHITECTURE.md` - Four-layer memory system deep dive
- `11_REDIS_PATTERNS.md` - Redis patterns for AI agents
- `12_LANGGRAPH_CHECKPOINTING.md` - Conversation state management
- `13_TOOLS_SERVICES_UTILS_REFERENCE.md` - Complete backend reference

## Development Commands

### Quick Start with Make

**Use the Makefile for common tasks:**

```bash
# Show all available commands
make help

# Setup & Installation
make install          # Install all dependencies
make dev              # Start development servers
make health           # Check all services (Redis, API, Ollama)

# Data Management
make import           # Import Apple Health data from apple_health_export/export.xml
make import-xml       # Import from specific XML file (prompts for path)
make verify           # Verify data is loaded and indexed
make stats            # Show health data types and statistics

# Testing & Quality
make test             # Run all tests
make test-unit        # Run unit tests only
make test-e2e         # Run E2E tests
make lint             # Run code linting

# Redis Operations
make redis-start      # Start Redis container
make redis-stop       # Stop Redis container
make redis-clean      # Clean Redis data (FLUSHALL - prompts for confirmation)
make redis-keys       # Show Redis keys (first 20 + total count)
make clear-session    # Clear chat session (keeps health data)

# Quick Commands
make fresh-start      # Clean + Import + Dev (full reset)
make demo             # Prepare for demo (import + verify)
make clean            # Clean all build artifacts
```

### Environment Setup (Manual)

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

**All tests organized in `/backend/tests/`:**

```bash
# Run all backend tests
cd backend
uv run pytest tests/

# Unit tests (no external dependencies)
uv run pytest tests/unit/
# - test_numeric_validator.py - Validation logic
# - test_health_analytics.py - Health analytics functions
# - test_intent_router.py - Intent routing logic
# - test_metric_aggregators.py - Metric aggregation
# - test_stats_utils.py - Statistical utilities
# - test_time_utils.py - Time parsing utilities
# - test_consolidated_tools.py - Tool function tests

# Integration tests (require Redis/services)
uv run pytest tests/integration/
# - test_episodic_memory.py - Short-term memory
# - test_procedural_memory.py - Goal and preference tracking
# - test_health_tools.py - Apple Health tool integration
# - test_redis_services.py - Redis service layer

# API tests (require running backend)
uv run pytest tests/api/
# - test_chat_endpoints.py - Chat endpoint integration

# LLM tests (require Ollama)
uv run pytest tests/llm/
# - test_agents.py - Full agent workflow tests

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

# Pre-push hooks (run automatically on push - prevents CI failures)
# Runs: backend ruff/tests, frontend typecheck/lint/ts-prune, Docker build
git push  # Triggers comprehensive checks
# To bypass (NOT RECOMMENDED): git push --no-verify
```

### Health Data Integration

```bash
# Import Apple Health data (recommended - uses Make)
make import

# Or import from specific XML file
make import-xml

# Verify data was imported successfully
make verify

# Show statistics about imported data
make stats

# Manual import (if not using Make)
uv run --directory backend import-health apple_health_export/export.xml
```

## Debugging Best Practices

### Critical Debugging Checklist

When debugging issues where data isn't flowing correctly between backend and frontend:

**1. Verify API Contract Matching First**

Before diving into complex debugging, check field name consistency:

```bash
# Check TypeScript interfaces
grep -r "interface.*Stats" frontend/src/types.ts

# Check backend response structure
grep -r "memory_stats" backend/src/agents/
grep -r "memory_stats" backend/src/services/

# Common mismatch: semantic_retrieval vs semantic_hits
```

**Field name mismatches are silent killers** - they don't throw errors, data just disappears.

**2. Docker Development Workflow**

The Dockerfile uses `COPY` (not volume mounts), so:

```bash
# After ANY code change in backend/src/, you MUST rebuild:
docker compose build backend
docker compose up -d backend

# Verify the change took effect:
docker compose logs backend --tail 50

# Quick fix without rebuild (for emergencies):
docker cp /path/to/file.py redis-wellness-backend:/app/src/path/to/file.py
docker compose restart backend
```

**3. Add Logging Early**

Add comprehensive logging BEFORE starting multi-hour debugging sessions:

```python
# In backend code, add explicit logging for data flow
logger.info(f"💾 Memory stats: semantic_hits={hits}, goals_stored={goals}")
logger.info(f"📊 Final state: {len(messages)} messages")
logger.info(f"✅ Retrieved episodic context: {context is not None}")
```

```typescript
// In frontend code, log what you receive
console.log('📥 Received memory_stats:', data.memory_stats);
console.log('📊 Stats object keys:', Object.keys(data.memory_stats || {}));
```

**4. Test the Full Stack in Order**

Debug systematically from backend to frontend:

```bash
# Step 1: Verify data exists in Redis
redis-cli
> KEYS episodic:*
> HGETALL episodic:user123:1234567890

# Step 2: Check backend calculates correctly
docker compose logs backend | grep "Memory stats"

# Step 3: Check backend returns correctly
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "session_id": "debug"}' | jq '.memory_stats'

# Step 4: Check frontend receives correctly
# Open browser DevTools → Network → Find request → Check Response tab
```

**5. TypeScript Interface Verification**

When adding new fields to API responses:

```typescript
// 1. Check the interface definition
export interface MemoryStats {
  semantic_hits: number;  // ← Must match backend exactly
  goals_stored: number;
}

// 2. Check the usage site
this.stats.semanticMemories = data.memory_stats?.semantic_hits || 0;
//                                                 ^^^^^^^^^^^^^ Field name must match

// 3. Grep for all usages to ensure consistency
// grep -r "semantic_" frontend/src/
```

**6. Streaming Response Debugging**

For streaming endpoints, ensure all data is included:

```python
# BAD - Missing memory_stats in done event
yield {"type": "done", "data": {"response": text}}

# GOOD - All fields included
yield {
    "type": "done",
    "data": {
        "response": text,
        "tools_used": tools,
        "memory_stats": result.get("memory_stats", {}),  # Don't forget!
    }
}
```

**7. Environment Variable Mismatches**

Check that docker-compose.yml uses the SAME variable names as config.py:

```yaml
# docker-compose.yml
environment:
  - OLLAMA_BASE_URL=http://host.docker.internal:11434  # Must match config.py

# backend/src/config.py
ollama_base_url: str = Field(default="http://localhost:11434")
# Variable name MUST match: OLLAMA_BASE_URL ← config expects this exact name
```

### Common Pitfall: Field Name Mismatches

**Symptom**: Backend logs show correct values, but frontend displays 0 or undefined.

**Root Cause**: Field names don't match between backend response and frontend interface.

**Example from October 2024**:
```python
# Backend was sending:
return {"memory_stats": {"semantic_retrieval": 1}}  # ❌ Wrong field name

# Frontend expected:
interface MemoryStats {
  semantic_hits: number;  # ← Looking for this field
}
```

**Fix**: Change backend to match frontend:
```python
# Backend now sends:
return {"memory_stats": {"semantic_hits": 1}}  # ✅ Correct field name
```

**Prevention**: Always grep both codebases when adding new fields:
```bash
grep -r "semantic_hits" frontend/src/
grep -r "semantic_hits" backend/src/
```

### Docker Rebuild Requirements

**When to rebuild Docker images:**

- ✅ After ANY change to `backend/src/` files
- ✅ After changes to `pyproject.toml` or `uv.lock`
- ✅ After changes to environment variables in docker-compose.yml
- ❌ NOT needed for frontend changes (volume mounted)

**Quick rebuild command:**
```bash
docker compose build backend && docker compose up -d backend && docker compose logs backend --tail 50
```

### Log Visibility Troubleshooting

**Issue**: Logs not appearing even though code is executing.

**Causes**:
1. Multiple processes running (check with `lsof -i :8000`)
2. Docker container running old code (rebuild needed)
3. Background processes hiding output
4. Wrong log level configured

**Fix**:
```bash
# Kill all instances
lsof -ti:8000 | xargs kill -9

# Check Docker logs
docker compose logs backend -f

# Check background bash processes
# Use /bashes command to see running shells
```

## Development Notes

### Project Maturity

**Status**: Near completion - focus on stability, documentation quality, and final testing.

**Recent Changes (October 2024)**:
- ✅ Documentation reorganization (13 structured docs)
- ✅ Pydantic V2 migration (deprecation warnings fixed)
- ✅ Cross-reference improvements across all docs
- ✅ Mermaid diagram enhancements for readability
- ✅ Terminology consistency ("simple queries" vs "goal CRUD")

**What NOT to Change**:
- ❌ Core agent logic (stateless/stateful) - stable and tested
- ❌ Redis data structures - optimized and working
- ❌ LangGraph workflow - validated against test suite
- ❌ Tool calling system - Qwen-optimized and reliable

**Safe to Improve**:
- ✅ Documentation clarity and examples
- ✅ Error messages and user feedback
- ✅ Test coverage for edge cases
- ✅ Performance monitoring and logging
- ✅ README and doc formatting

### Project Structure (Updated October 2024)

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
- `POST /api/chat/stateless` - Stateless chat (no memory)
- `POST /api/chat/stateless/stream` - Stateless chat with streaming (SSE)
- `POST /api/chat/stateful` - Stateful RAG chat with full memory (LangGraph)
- `POST /api/chat/stateful/stream` - Stateful chat with streaming (SSE)
- `GET /api/chat/demo/info` - Demo comparison documentation

**Memory Management:**
- `GET /api/chat/history/{session_id}` - View conversation history
- `GET /api/chat/memory/{session_id}` - Memory statistics
- `DELETE /api/chat/session/{session_id}` - Clear session

**Health Data:**
- Import via `make import` or `import_health.py` script (not HTTP endpoint)
- Data automatically indexed in Redis on import
- Semantic memory cleared on import to prevent stale data

### Docker Network

Services communicate via `wellness-network` bridge network. Backend connects to host Ollama using `host.docker.internal`.

### Agentic Tool-Calling System

Key features of the agentic workflow:

- **Tool-First Policy**: Factual queries skip semantic memory to avoid stale cache
- **5 Specialized Tools**: 3 health tools (metrics, sleep, workouts) + 2 memory tools (goals, patterns)
- **Four-Layer Memory**: Short-term (checkpointing) + Episodic (goals) + Procedural (patterns) + Semantic (optional)
- **Tool Calling**: Qwen 2.5 7B optimized for function calling
- **Simple Loop**: Up to 8 iterations for complex multi-step queries
- **Autonomous**: LLM decides which tools to call, chains them, decides when done
- **Memory Clearing**: Import script clears semantic memory to prevent stale data


### TypeScript Frontend

Modern vanilla TypeScript with Vite featuring:

- Side-by-side chat comparison UI
- Real-time health status monitoring
- Session management with memory statistics
- Tool call visualization
- XSS protection with proper HTML escaping

### Privacy Architecture (Core Feature - Do NOT Modify)

- All data stays local (Redis + Ollama)
- No external API calls
- Health data never leaves your machine
- Self-contained Docker environment

**This is a key selling point** - 100% local processing for sensitive health data.

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

**Stateful RAG Chat** (remembers context):
```bash
curl -X POST http://localhost:8000/api/chat/stateful \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my average heart rate last week?", "session_id": "demo"}'

# Follow-up works: "Is that good?" → "87 bpm is within normal range..."
```

**Streaming Chat** (tokens arrive in real-time):
```bash
# Stateless streaming
curl -X POST http://localhost:8000/api/chat/stateless/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "did I work out on October 17th?"}'

# Stateful streaming
curl -X POST http://localhost:8000/api/chat/stateful/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "did I work out on October 17th?", "session_id": "demo"}'
```

### Load Health Data

```bash
# Import Apple Health data (recommended)
make import

# Or use manual command
uv run --directory backend import-health apple_health_export/export.xml

# Verify data was imported
make verify
```

The application demonstrates how Redis + RedisVL transforms stateless chat into context-aware, memory-powered health insights using **100% local processing**.

---

## Working with This Codebase (Important Guidelines)

### Before Making Changes

1. **Check Test Suite First**
   ```bash
   make test  # Run all tests to verify current state
   ```

2. **Review Documentation**
   - If changing agent logic → Read `docs/03_STATELESS_AGENT.md` and `docs/04_STATEFUL_AGENT.md`
   - If changing memory → Read `docs/10_MEMORY_ARCHITECTURE.md`
   - If changing Redis patterns → Read `docs/11_REDIS_PATTERNS.md`
   - If changing tools → Read `docs/13_TOOLS_SERVICES_UTILS_REFERENCE.md`

3. **Understand Dependencies**
   - Frontend changes: No rebuild needed (volume mounted)
   - Backend changes: **MUST rebuild Docker** (`make build-backend`)
   - Environment variables: Update `docker-compose.yml` AND `config.py`

### Code Quality Requirements

**All changes must pass**:
```bash
make lint       # Ruff + Black + ESLint
make test       # Full test suite
make typecheck  # TypeScript validation
```

**Pre-commit hooks** run automatically - DO NOT bypass with `--no-verify`.

**Pre-push hooks** prevent CI failures - includes backend tests + Docker build.

### Making Documentation Changes

**Documentation is a priority** - this is a demo project meant to teach.

**When updating docs**:
- ✅ Keep examples realistic and testable
- ✅ Maintain consistent terminology (check other docs)
- ✅ Update cross-references if file names change
- ✅ Verify code examples actually work
- ✅ Keep formatting consistent across all 13 docs

**Doc structure is stabilized** - major reorganization is NOT needed.

### Testing Philosophy

**Test pyramid** (in `/backend/tests/`):
- **Unit tests**: Fast, no dependencies (validators, aggregators, analytics)
- **Integration tests**: Redis-dependent (memory managers, services)
- **API tests**: Running backend required (endpoints)
- **LLM tests**: Ollama required (full agent workflows)

**Run targeted tests**:
```bash
uv run pytest tests/unit/              # Fast, no setup
uv run pytest tests/integration/       # Requires Redis
uv run pytest tests/llm/               # Requires Ollama
uv run pytest tests/ -k test_name      # Specific test
```

### Common Workflows

**Adding a new feature**:
1. Write tests first (`tests/unit/` or `tests/integration/`)
2. Implement feature in appropriate module
3. Update relevant documentation in `/docs/`
4. Run `make lint && make test`
5. Rebuild Docker if backend changed
6. Manually test in UI at http://localhost:3000

**Fixing a bug**:
1. Add regression test that reproduces bug
2. Fix bug in source code
3. Verify test passes
4. Check if docs need clarification
5. Run full test suite

**Improving docs**:
1. Make changes in `/docs/`
2. Verify cross-references still work
3. Check formatting consistency
4. Test any code examples locally
5. Commit (no rebuild needed)

### Known Gotchas

**Field name mismatches** (silent killer):
- Frontend TypeScript interfaces MUST match backend response keys exactly
- Example: `semantic_hits` vs `semantic_retrieval` causes silent data loss
- Always grep both codebases when adding new fields

**Docker rebuild requirements**:
- Backend uses `COPY` (not volumes) - rebuild after ANY `/backend/src/` change
- Quick check: `docker compose logs backend --tail 50`
- Bypass for emergencies: `docker cp file.py redis-wellness-backend:/app/src/path/to/file.py`

**Streaming responses**:
- SSE endpoints must yield ALL fields in "done" event
- Missing fields in final event causes frontend to show 0/undefined
- Check both `stateless_chat.py` and `stateful_rag_agent.py`

**Environment variables**:
- Variable names in `docker-compose.yml` must match `config.py` Field names
- Example: `OLLAMA_BASE_URL` not `OLLAMA_URL`

### Project Philosophy

**This is a teaching demo** - code clarity matters more than extreme optimization.

**Priorities** (in order):
1. **Correctness** - Feature works reliably
2. **Documentation** - Users understand how it works
3. **Privacy** - Data stays local (non-negotiable)
4. **Simplicity** - Clear, maintainable code
5. **Performance** - Fast enough for demo purposes

**Not priorities**:
- Production-scale performance (this is a demo)
- Supporting multiple LLM providers (Ollama is sufficient)
- Cloud deployment (local-first is the feature)
- Complex optimization (simplicity > speed)

### Final Notes

**This project is nearly done** - resist the urge to refactor working code.

**Focus on**:
- Bug fixes from user testing
- Documentation improvements
- Edge case handling
- Error message clarity

**Avoid**:
- Major architectural changes
- Unnecessary abstraction
- Feature creep
- Over-engineering

**Goal**: Ship a polished, educational demo that showcases Redis + RedisVL for AI agent memory.
