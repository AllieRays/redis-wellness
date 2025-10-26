# Redis Wellness - Critical Project Information

## Project Architecture

**We ALWAYS use Docker** - All services run in containers via `docker compose`

### Triple Memory System:

The application uses **three types of memory** powered by Redis + RedisVL:

1. **Episodic Memory** (Short-term)
   - Stores conversation history within a session
   - Managed by `episodic_memory_manager.py`
   - Redis key pattern: `episodic:{session_id}:history`
   - Enables context awareness within a conversation

2. **Semantic Memory** (Long-term)
   - Stores important facts extracted from conversations
   - Managed by `semantic_memory_manager.py` with RedisVL vector search
   - Redis key pattern: `semantic:{user_id}:{timestamp}`
   - Enables recall of past information across sessions
   - Uses embeddings for similarity search (1024 dimensions)

3. **Procedural Memory** (Goals & Preferences)
   - Stores user goals, preferences, and configuration
   - Managed by `procedural_memory_manager.py`
   - Redis key pattern: `procedural:{user_id}:goals`
   - Enables personalized responses based on user objectives

This architecture mirrors human memory systems and dramatically improves AI conversation quality.

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

### DO NOT:
- ❌ Create new import scripts
- ❌ Change datetime formats
- ❌ Remove hash set deduplication
- ❌ Skip workout enrichment step
- ❌ Modify Redis key structure without updating `utils/redis_keys.py`

### DO:
- ✅ Use `import_health_data.py` for ALL imports
- ✅ Test with `test_data_validation.sh` after importing
- ✅ Run hallucination tests to verify agent accuracy
- ✅ Check `rebuild_workout_indexes.py` for workout indexing

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

**Triple Memory System:**
- **Episodic**: `episodic:{session_id}:history` - Conversation history
- **Semantic**: `semantic:{user_id}:{timestamp}` - Long-term facts with embeddings
- **Procedural**: `procedural:{user_id}:goals` - User goals and preferences

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

## Related Scripts & Services

**Backend Scripts** (`backend/scripts/`):
- `startup_health_check.py` - Validates data on backend startup
- `populate_semantic_memory.py` - Populates semantic memory from conversations
- `validate_imports.py` - Validates imported health data
- `verify_redis_checkpointer.py` - Verifies Redis persistence

**Core Services** (`backend/src/services/`):
- `redis_chat.py` - RAG chat service with triple memory
- `stateless_chat.py` - Baseline no-memory service
- `episodic_memory_manager.py` - Conversation history
- `semantic_memory_manager.py` - Long-term context (RedisVL)
- `procedural_memory_manager.py` - Goals and preferences
- `redis_workout_indexer.py` - Workout indexing
- `redis_apple_health_manager.py` - Health data CRUD
- `embedding_service.py` - Embedding generation

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
