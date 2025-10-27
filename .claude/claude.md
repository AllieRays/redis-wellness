# Redis Wellness - Critical Project Information

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

## Project Architecture

**We ALWAYS use Docker** - All services run in containers via `docker compose`

### Four-Layer Memory System:

The application uses **four types of memory** powered by Redis + RedisVL (CoALA framework-inspired):

1. **Short-term Memory** (LangGraph Checkpointing)
   - Stores recent conversation within current session
   - Managed by LangGraph BaseCheckpointSaver
   - Redis key pattern: `checkpoint:{session_id}:{step}`
   - Enables context awareness and pronoun resolution

2. **Episodic Memory** (User Goals & Facts)
   - Stores important user-specific facts and goals
   - Managed by `episodic_memory_manager.py` with RedisVL vector search
   - Redis key pattern: `episodic:{user_id}:goal:{timestamp}`
   - Enables cross-session goal recall
   - Uses embeddings for similarity search (1024 dimensions)
   - Retrieved autonomously via `get_my_goals` tool (LLM-triggered)

3. **Procedural Memory** (Workflow Patterns)
   - Stores successful tool-calling sequences and strategies
   - Managed by `procedural_memory_manager.py` with RedisVL
   - Redis key pattern: `procedural:pattern:{timestamp}`
   - Enables workflow optimization via past success
   - Retrieved autonomously via `get_tool_suggestions` tool (LLM-triggered)

4. **Semantic Memory** (Health Knowledge Base) - Optional
   - Stores general health facts and medical knowledge
   - Managed by `semantic_memory_manager.py` with RedisVL
   - Redis key pattern: `semantic:{category}:{fact_type}:{timestamp}`
   - Enables domain knowledge augmentation

This architecture mirrors human memory systems (CoALA framework) and dramatically improves AI conversation quality.

**Key Feature**: Memory retrieval is **autonomous** - the LLM decides when to call memory tools, not hardcoded logic.

### Key Locations:
- **Import script**: `backend/src/import_health_data.py`
- **Backend source**: `backend/src/`
- **Apple Health logic**: `backend/src/apple_health/` (parser, query tools)
- **Tests**: `backend/tests/` (unit, integration, api, llm subdirs)
- **Backend scripts**: `backend/scripts/` (health checks, validation)
- **Data**: `apple_health_export/export.xml` (mounted in Docker)
- **Documentation**: `docs/` (numbered guides + SERVICES.md)

### Docker Commands:
```bash
# Start all services
docker compose up -d

# View logs
docker compose logs backend -f

# Access Redis (from host)
docker compose exec redis redis-cli

# Run import script (from backend directory)
cd backend
uv run python -m src.import_health_data ../apple_health_export/export.xml

# Access backend container
docker compose exec backend bash
```

**IMPORTANT**: The import script runs on your HOST machine (not inside Docker), but connects to Redis inside the Docker container via port 6379.

## ⚠️ CRITICAL: Data Import Script

**Location:** `backend/src/import_health_data.py`

**THIS IS THE MAIN SCRIPT FOR IMPORTING HEALTH DATA**

**Also available as CLI command:** `uv run --directory backend import-health <path>`

### Why This Matters:
- Uses hash sets to prevent duplicate imports
- Correctly handles datetime parsing (ISO format with timezone)
- Enriches workout data with required fields (`day_of_week`, `type_cleaned`, `calories`)
- Calls `rebuild_workout_indexes.py` for proper Redis indexing
- **DO NOT create new import scripts** - this one handles all the edge cases

### Usage:
```bash
# Using Make (recommended)
make import  # Imports from apple_health_export/export.xml
make import-xml  # Prompts for custom XML path

# Using CLI command
cd backend
uv run import-health ../apple_health_export/export.xml

# Direct Python execution
cd backend
uv run python -m src.import_health_data ../apple_health_export/export.xml

# With parsed JSON (faster)
uv run import-health ../parsed_health_data.json
```

### What It Does:
1. **Parses** Apple Health XML or pre-parsed JSON
2. **Enriches** workouts with computed fields:
   - `day_of_week`: "Monday", "Tuesday", etc. (REQUIRED by tools)
   - `type_cleaned`: "Running", "Cycling" (removes HK prefix)
   - `calories`: Standardizes `totalEnergyBurned` field
3. **Stores** in Redis:
   - `user:wellness_user:health_data` - Main health data
   - `user:wellness_user:health_metric:{type}` - Metric indices (7 month TTL)
   - Triple memory system:
     - `episodic:{session_id}:history` - Conversation history
     - `semantic:{user_id}:{timestamp}` - Long-term context (RedisVL)
     - `procedural:{user_id}:goals` - User goals and preferences
4. **Indexes** workouts automatically during import for fast queries

### Important Fields:
- **startDate**: ISO format (`2024-10-15T10:30:00Z`) - DO NOT change format
- **day_of_week**: Must be full day name ("Monday", not "Mon")
- **Hash sets**: Prevents re-importing same data

## Data Flow

```
Apple Health Export (export.xml)
         ↓
  import_health_data.py
         ↓
      Redis
         ↓
   Agent Tools
         ↓
     Frontend
```

## Testing

### Test Structure:
`backend/tests/` - Organized by type

#### Available Test Suites:

**Unit Tests** (`tests/unit/`) - No external dependencies:
- `test_numeric_validator.py` - Validation logic
- `test_health_analytics.py` - Health analytics functions
- `test_intent_router.py` - Intent routing
- `test_metric_aggregators.py` - Metric aggregation
- `test_stats_utils.py` - Statistical utilities
- `test_time_utils.py` - Time parsing
- `test_consolidated_tools.py` - Tool functions

**Integration Tests** (`tests/integration/`) - Require Redis:
- `test_episodic_memory.py` - Short-term conversation memory
- `test_procedural_memory.py` - Goal and preference tracking
- `test_health_tools.py` - Apple Health tool integration
- `test_redis_services.py` - Redis service layer

**API Tests** (`tests/api/`) - Require running backend:
- `test_chat_endpoints.py` - Chat endpoint integration

**LLM Tests** (`tests/llm/`) - Require Ollama:
- `test_agents.py` - Full agent workflow tests

#### Run Tests:
```bash
cd backend

# All tests
uv run pytest tests/

# Unit tests only (fast)
uv run pytest tests/unit/

# Integration tests (need Redis)
uv run pytest tests/integration/

# API tests (need running backend)
uv run pytest tests/api/

# LLM tests (need Ollama)
uv run pytest tests/llm/

# Or use Make
make test          # All tests
make test-unit     # Unit tests only
```

## Key Constraints

### DO NOT (Core Features - Stable):
- ❌ Create new import scripts
- ❌ Change datetime formats
- ❌ Remove hash set deduplication
- ❌ Skip workout enrichment step
- ❌ Modify Redis key structure without updating `utils/redis_keys.py`
- ❌ Refactor agent logic (stateless/stateful) - tested and stable
- ❌ Change Redis data structures - optimized and working
- ❌ Modify LangGraph workflow - validated against test suite
- ❌ Alter tool calling system - Qwen-optimized
- ❌ Remove privacy features - 100% local is core selling point

### DO (Focus Areas):
- ✅ Use `import_health_data.py` for ALL imports
- ✅ Improve documentation clarity and examples
- ✅ Add test coverage for edge cases
- ✅ Enhance error messages and user feedback
- ✅ Fix bugs from user testing
- ✅ Verify code examples in docs work
- ✅ Run `make lint && make test` before commits

## Data Location

### In Docker Container (backend):
- **XML Export**: `/apple_health_export/export.xml` (87MB)
- **Parsed JSON**: `/parsed_health_data.json` (if pre-parsed)

### In Redis Container:
Access via: `docker compose exec redis redis-cli`

**Health Data:**
- **Main data**: `user:wellness_user:health_data`
- **Metrics**: `user:wellness_user:health_metric:{MetricType}` (7-month TTL)
- **Workout indexes**: Auto-indexed during import

**Four-Layer Memory System:**
- **Short-term**: `checkpoint:{session_id}:{step}` - LangGraph checkpointing (conversation history)
- **Episodic**: `episodic:{user_id}:goal:{timestamp}` - User goals and facts with embeddings
- **Procedural**: `procedural:pattern:{timestamp}` - Workflow patterns with embeddings
- **Semantic**: `semantic:{category}:{fact_type}:{timestamp}` - Health knowledge (optional)

### Apple Health Module Structure

```
backend/src/apple_health/
├── parser.py                      # XML parsing (AppleHealthParser)
├── models.py                      # Data models (HealthRecord, WorkoutSummary)
├── tool_models.py                 # Pydantic models for tool inputs/outputs
└── query_tools/                   # LangChain tools for agents (5 tools: 3 health + 2 memory)
    ├── __init__.py               # Tool registration
    ├── get_health_metrics.py     # All non-sleep, non-workout health data (heart rate, steps, weight, BMI, trends)
    ├── get_sleep_analysis.py     # Sleep data with daily aggregation and efficiency metrics
    ├── get_workout_data.py       # ALL workout queries (lists, patterns, progress, comparisons) - consolidated tool
    └── memory_tools.py           # Goal and procedural memory (get_my_goals, get_tool_suggestions)
```

**Important**: Tools in `query_tools/` are what agents use to access data. The system uses **5 consolidated tools** (3 health + 2 memory) instead of many specialized tools to reduce token usage and improve LLM performance. The `get_workout_data` tool handles all workout queries through feature flags.

**Stateless vs. Stateful Agents:**
- **Stateless Agent**: Uses 9 health tools only, simple tool loop, NO memory
- **Stateful Agent**: Uses 11 tools (9 health + 2 memory), LangGraph workflow with checkpointing, four-layer memory
- **Memory is autonomous**: LLM decides when to call `get_my_goals` or `get_tool_suggestions`

## Related Scripts & Services

**Backend Scripts** (`backend/scripts/`):
- `startup_health_check.py` - Validates data on backend startup
- `populate_semantic_memory.py` - Populates semantic memory from conversations
- `validate_imports.py` - Validates imported health data
- `verify_redis_checkpointer.py` - Verifies Redis persistence

**Core Services** (`backend/src/services/`):
- `redis_chat.py` - RAG chat service with four-layer memory (stateful agent)
- `stateless_chat.py` - Baseline no-memory service (stateless agent)
- `episodic_memory_manager.py` - Episodic memory (user goals)
- `semantic_memory_manager.py` - Semantic memory (health knowledge, optional)
- `procedural_memory_manager.py` - Procedural memory (workflow patterns)
- `redis_workout_indexer.py` - Workout indexing
- `redis_apple_health_manager.py` - Health data CRUD
- `embedding_service.py` - Embedding generation
- `redis_connection.py` - Production-ready Redis connection management

## Troubleshooting

### "Agent says it doesn't have data"
1. Check if data is imported: `make verify` or `docker compose exec redis redis-cli KEYS "*health*"`
2. Verify Redis is running: `docker compose ps`
3. Check data statistics: `make stats`
4. Re-import if needed: `make import`
5. Test with curl: `curl http://localhost:8000/health`

### "Datetime format errors"
- **Solution**: Use `backend/src/import_health_data.py` - it handles all datetime edge cases
- **DO NOT** manually parse dates - use the script's proper parsing
- All dates stored in ISO format with timezone (`2024-10-15T10:30:00Z`)

### "Duplicate workout entries"
- **Cause**: Not using deduplication properly during import
- **Solution**: `import_health_data.py` handles deduplication automatically via hash tracking

### "Redis commands fail"
- **Always use Docker**: `docker compose exec redis redis-cli` (NOT `redis-cli`)
- Redis runs in container, not on host

### "Backend can't connect to Redis"
- Check both containers running: `docker compose ps`
- Check Docker network: `docker compose logs backend | grep -i redis`
- Redis host in code is `redis` (container name), not `localhost`

---

## Development Philosophy

**This is a teaching demo** - code clarity matters more than extreme optimization.

### Priorities (in order):
1. **Correctness** - Feature works reliably
2. **Documentation** - Users understand how it works
3. **Privacy** - Data stays local (non-negotiable)
4. **Simplicity** - Clear, maintainable code
5. **Performance** - Fast enough for demo purposes

### Not Priorities:
- Production-scale performance (this is a demo)
- Supporting multiple LLM providers (Ollama is sufficient)
- Cloud deployment (local-first is the feature)
- Complex optimization (simplicity > speed)

### Project Status Notes:
- **Nearly complete** - resist urge to refactor working code
- **Focus on**: Bug fixes, docs, edge cases, error messages
- **Avoid**: Major architecture changes, unnecessary abstraction, feature creep
- **Goal**: Ship a polished, educational demo

### Before Making Changes:
1. Run `make test` to verify current state
2. Review relevant docs in `/docs/` (13 comprehensive guides)
3. Understand dependencies:
   - Frontend changes: No rebuild needed (volume mounted)
   - Backend changes: **MUST rebuild Docker** (`docker compose build backend`)
   - Environment variables: Update both `docker-compose.yml` AND `config.py`

### Code Quality:
- Pre-commit hooks run automatically - DO NOT bypass
- Pre-push hooks prevent CI failures (tests + Docker build)
- All changes must pass: `make lint && make test && make typecheck`
