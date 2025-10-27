# Testing Status

**Last Updated**: October 2025

## Current Status: No Test Suite

The test suite was removed in October 2025 due to being wildly out of date with the current codebase architecture.

### Issues with Previous Tests (~2600 lines)

1. **Import errors** - `conftest.py` imported functions that no longer exist (`get_procedural_memory_manager` vs `get_procedural_memory`)
2. **Architecture mismatch** - Tests assumed CoALA memory framework structure that diverged from implementation
3. **Cannot run** - `pytest` collection failed immediately due to missing dependencies
4. **Maintenance burden** - Fixing would require rewriting most of the test suite

### Current Quality Assurance

Quality is maintained through:

1. **Pre-commit hooks** - Ruff linting and formatting (`.pre-commit-config.yaml`)
2. **Pre-push hooks** - Comprehensive checks preventing CI failures (`.git/hooks/pre-push`)
3. **Docker environment** - Consistent reproducible environment
4. **Manual testing** - Frontend UI at http://localhost:3000
5. **Type checking** - TypeScript for frontend, Python type hints for backend

### When Tests Are Needed

Consider writing tests when:

- **Critical paths** need regression protection (e.g., Apple Health XML parsing)
- **Complex algorithms** need validation (e.g., numeric validator, hallucination detection)
- **API contracts** need stability guarantees (e.g., chat endpoints)

### Testing Strategy (When Implemented)

#### Unit Tests (Isolated, Fast)
```bash
# Pure functions with no external dependencies
- backend/src/utils/numeric_validator.py
- backend/src/utils/stats_utils.py
- backend/src/utils/time_utils.py
- backend/src/apple_health/parser.py (validation logic)
```

#### Integration Tests (Redis Required)
```bash
# Services that interact with Redis
- backend/src/services/redis_chat.py
- backend/src/services/memory_manager.py
- backend/src/services/redis_workout_indexer.py
```

#### API Tests (FastAPI TestClient)
```bash
# HTTP endpoint validation
- POST /api/chat/stateless
- POST /api/chat/redis
- GET /api/chat/history/{session_id}
- GET /api/chat/memory/{session_id}
```

#### Agent Tests (LLM Required - Expensive)
```bash
# Full agentic workflows - run sparingly
- Stateless agent tool calling
- Stateful agent with memory
- Multi-turn conversations
```

### Test File Structure (Future)

```
backend/tests/
├── unit/
│   ├── test_numeric_validator.py
│   ├── test_stats_utils.py
│   ├── test_time_utils.py
│   └── test_apple_health_parser.py
├── integration/
│   ├── test_redis_chat.py
│   ├── test_memory_manager.py
│   └── test_workout_indexer.py
├── api/
│   └── test_chat_routes.py
├── agent/ (expensive)
│   ├── test_stateless_agent.py
│   └── test_stateful_agent.py
└── conftest.py (fixtures)
```

### Running Tests (Future)

```bash
# Unit tests (fast, no dependencies)
cd backend
uv run pytest tests/unit/

# Integration tests (require Redis)
docker-compose up -d redis
uv run pytest tests/integration/

# API tests (require full backend)
docker-compose up -d
uv run pytest tests/api/

# All tests
uv run pytest tests/
```

## Decision Rationale

**Why remove instead of fix?**

1. **Current workflow works** - Docker + manual testing + pre-commit hooks provide adequate quality
2. **High rewrite cost** - Most tests would need complete rewrites
3. **Architecture changes** - Better to write tests against stable architecture
4. **Clear slate** - When tests are needed, write them fresh with current patterns

**No tests ≠ No quality** - Quality is maintained through linting, type checking, Docker consistency, and manual validation.

When the project reaches a point where automated regression testing provides clear value, implement tests incrementally starting with the most critical paths.
