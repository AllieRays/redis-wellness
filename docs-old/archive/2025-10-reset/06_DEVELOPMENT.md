# Development Guide

**Last Updated**: October 24, 2024

## Development Workflow

### Prerequisites

1. **Docker & Docker Compose** (required)
2. **Ollama** (required - runs on host)
3. **Python 3.11+** (for local development)
4. **Node.js 18+** (for frontend development)
5. **uv** (Python dependency manager - recommended)

### Quick Setup

```bash
# 1. Clone repository
git clone https://github.com/your-org/redis-wellness.git
cd redis-wellness

# 2. Start Ollama (in separate terminal)
ollama serve

# 3. Pull required models
ollama pull qwen2.5:7b
ollama pull mxbai-embed-large

# 4. Start all services
chmod +x start.sh
./start.sh

# 5. Verify everything works
curl http://localhost:8000/health
```

---

## Local Development (Without Docker)

### Backend Development

```bash
cd backend

# Install dependencies with uv
uv sync

# Start Redis locally (or use Docker)
redis-server

# Run backend
uv run python -m backend.src.main

# Access at http://localhost:8000
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (hot reload)
npm run dev

# Access at http://localhost:3000
```

---

## Code Standards

### Python Style Guide

**Formatter**: Ruff (replaces Black + isort)

**Key Rules**:
- Line length: 88 characters
- Imports: Sorted automatically by Ruff
- Strings: Double quotes preferred
- Type hints: Required for all public functions

**Configuration**: `backend/pyproject.toml`

```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]  # Line too long (handled by formatter)
```

### TypeScript Style Guide

**Formatter**: Prettier
**Linter**: ESLint

**Key Rules**:
- Semicolons: Required
- Quotes: Double quotes
- Trailing commas: ES5
- Tab width: 2 spaces

**Configuration**: `frontend/.prettierrc`, `frontend/.eslintrc.json`

---

## Type Hints

### Required Type Hints

**ALL public functions must have type hints**:

```python
# ✅ CORRECT
async def process_query(
    user_id: str,
    message: str,
    session_id: str = "default"
) -> dict[str, Any]:
    """Process user query with memory."""
    ...

# ❌ WRONG - Missing type hints
async def process_query(user_id, message, session_id="default"):
    ...
```

### Modern Python Syntax

Use Python 3.11+ union types:

```python
# ✅ CORRECT (Python 3.11+)
def get_data() -> dict[str, Any] | None:
    ...

# ❌ OLD STYLE (avoid)
from typing import Optional, Dict, Any
def get_data() -> Optional[Dict[str, Any]]:
    ...
```

### Type Hint Coverage Target

**Goal**: 95%+ coverage

**Check coverage**:
```bash
cd backend
uv run python -c "
from pathlib import Path
import ast

total = 0
typed = 0

for file in Path('src').rglob('*.py'):
    with open(file) as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            total += 1
            if node.returns is not None:
                typed += 1

print(f'Type hint coverage: {typed/total*100:.1f}% ({typed}/{total})')
"
```

---

## Docstring Style

### Google Style (Required)

**ALL public functions must have docstrings**:

```python
async def aggregate_metrics(
    user_id: str,
    metric_type: str,
    start_date: str,
    end_date: str,
    aggregation: str = "average"
) -> dict[str, Any]:
    """
    Aggregate health metrics over a date range.

    Calculates statistics (average, sum, min, max) for a specific
    health metric type within the specified date range.

    Args:
        user_id: User identifier
        metric_type: Type of metric (e.g., "HeartRate", "StepCount")
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)
        aggregation: Aggregation type (average, sum, min, max)

    Returns:
        Dict containing:
            - value: Aggregated value
            - unit: Metric unit
            - count: Number of records
            - date_range: Start and end dates

    Raises:
        ValueError: If date format is invalid
        MemoryRetrievalError: If data retrieval fails

    Example:
        >>> result = await aggregate_metrics(
        ...     user_id="user123",
        ...     metric_type="HeartRate",
        ...     start_date="2024-10-01",
        ...     end_date="2024-10-07",
        ...     aggregation="average"
        ... )
        >>> print(result["value"])
        87.5
    """
    ...
```

### Docstring Elements

**Required**:
- Short description (one line)
- Args section (all parameters)
- Returns section (return value)

**Optional but recommended**:
- Longer description (if needed)
- Raises section (exceptions)
- Example section (for complex functions)

---

## Logging Standards

### Log Levels

**Use appropriate log levels**:

| Level | When to Use | Example |
|-------|------------|---------|
| **DEBUG** | Development details | `logger.debug(f"Query embedding: {len(embedding)} dims")` |
| **INFO** | Normal operations | `logger.info("Memory coordinator initialized")` |
| **WARNING** | Recoverable issues | `logger.warning(f"Cache miss: {query[:50]}...")` |
| **ERROR** | Failures | `logger.error(f"Redis connection failed: {e}")` |

### Logging Pattern

```python
import logging

logger = logging.getLogger(__name__)

# ✅ CORRECT - Structured logging
logger.info(
    f"Memory retrieval completed: "
    f"episodic={episodic_hits}, "
    f"semantic={semantic_hits}, "
    f"duration={duration_ms}ms"
)

# ✅ CORRECT - Include context
logger.error(
    f"Tool execution failed: {tool_name}",
    exc_info=True,  # Include stack trace
    extra={
        "user_id": user_id,
        "session_id": session_id,
        "tool_args": tool_args
    }
)

# ❌ WRONG - Inconsistent levels
logger.info(f"ERROR: Redis connection failed")  # Should be logger.error()

# ❌ WRONG - Missing context
logger.error("Failed")  # Too vague
```

### Correlation IDs

**Include user_id and session_id in all logs**:

```python
logger.info(
    f"Processing query for user={user_id}, session={session_id}: {message[:50]}..."
)
```

---

## Error Handling

### Exception Hierarchy

```python
# Custom exceptions (utils/exceptions.py)
class BaseApplicationError(Exception):
    """Base for all application errors."""
    pass

class ValidationError(BaseApplicationError):
    """Input validation failed."""
    pass

class MemoryRetrievalError(BaseApplicationError):
    """Memory operation failed."""
    def __init__(self, memory_type: str, reason: str):
        self.memory_type = memory_type
        self.reason = reason
        super().__init__(f"{memory_type}: {reason}")

class LLMServiceError(BaseApplicationError):
    """LLM service unavailable."""
    pass

class InfrastructureError(BaseApplicationError):
    """Infrastructure failure (Redis, etc.)."""
    pass
```

### Error Handling Pattern

```python
# ✅ CORRECT - Specific exception handling
try:
    result = await memory_coordinator.retrieve_all_context(...)
except MemoryRetrievalError as e:
    logger.error(f"Memory retrieval failed: {e.memory_type} - {e.reason}")
    # Graceful degradation: proceed without memory
    result = default_context()
except LLMServiceError as e:
    logger.error(f"LLM unavailable: {e.reason}")
    # Critical failure: cannot proceed
    raise HTTPException(status_code=503, detail="LLM service unavailable")

# ✅ CORRECT - Always log with context
logger.error(
    f"Error processing query",
    exc_info=True,
    extra={"user_id": user_id, "session_id": session_id}
)

# ❌ WRONG - Bare except
try:
    result = await process()
except:  # Too broad!
    pass
```

### API Error Responses

**Consistent error format**:

```python
from fastapi import HTTPException

# Return structured errors
{
    "error": "Memory retrieval failed",
    "error_type": "MemoryRetrievalError",
    "details": {
        "memory_type": "episodic",
        "reason": "Redis connection timeout"
    }
}
```

---

## Testing

### Running Tests

```bash
cd backend

# All tests
uv run pytest

# Unit tests only
uv run pytest tests/unit/

# Integration tests
uv run pytest tests/ -k "not unit"

# With coverage
uv run pytest --cov=src --cov-report=html

# Specific file
uv run pytest tests/unit/test_numeric_validator.py

# Verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x
```

### Test Organization

```
backend/tests/
├── unit/                           # Pure function tests (no Redis)
│   ├── test_numeric_validator.py
│   ├── test_math_tools.py
│   └── test_stateless_isolation.py
├── test_redis_chat_rag.py         # Memory system integration
├── test_redis_chat_api.py         # API integration
└── test_memory_coordinator.py     # Memory orchestration
```

### Writing Tests

**Test naming convention**:

```python
# test_feature_name.py

def test_function_name_should_do_what():
    """Test that function_name does what when condition."""
    # Arrange
    input_data = {...}

    # Act
    result = function_name(input_data)

    # Assert
    assert result == expected_value
```

**See**: `docs/07_TESTING.md` for complete strategy

---

## Code Quality Tools

### Pre-commit Hooks

**Automatic code quality checks on commit**:

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

**Configuration**: `.pre-commit-config.yaml`

### Linting

```bash
# Backend (Ruff)
cd backend
uv run ruff check --fix src tests
uv run ruff format src tests

# Frontend (ESLint + Prettier)
cd frontend
npm run lint
npm run format

# Type checking (optional)
npm run typecheck
```

### Manual Quality Check

```bash
# Run all quality checks
./lint.sh

# Or manually
cd backend
uv run ruff check --fix src tests
uv run ruff format src tests

cd ../frontend
npm run typecheck
npm run lint
npm run format
```

---

## Git Workflow

### Branch Strategy

```
main           # Production-ready code
├── develop    # Integration branch
    ├── feature/memory-system
    ├── feature/tool-optimization
    └── bugfix/redis-connection
```

### Commit Messages

**Format**: Conventional Commits

```bash
# Feature
git commit -m "feat: add episodic memory manager"

# Bug fix
git commit -m "fix: resolve Redis connection timeout"

# Documentation
git commit -m "docs: update memory system documentation"

# Refactoring
git commit -m "refactor: simplify tool calling loop"

# Performance
git commit -m "perf: optimize embedding cache"

# Tests
git commit -m "test: add memory coordinator tests"
```

**Prefixes**:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `perf:` Performance improvement
- `test:` Add/update tests
- `chore:` Maintenance tasks

---

## Debugging

### Backend Debugging

```bash
# Run with debug logging
cd backend
export LOG_LEVEL=DEBUG
uv run python -m backend.src.main

# Watch logs
docker-compose logs -f backend

# Interactive debugging (IPython)
uv add --dev ipython
# Add breakpoint in code:
import IPython; IPython.embed()
```

### Frontend Debugging

```bash
# Browser DevTools
# Open: http://localhost:3000
# Press F12

# Check console for errors
# Network tab for API calls
```

### Redis Debugging

```bash
# Connect to Redis CLI
docker exec -it redis-wellness-redis-1 redis-cli

# Monitor all commands
MONITOR

# List all keys
KEYS *

# Get key value
GET health_chat_session:demo

# Flush all data (CAUTION!)
FLUSHDB
```

### Ollama Debugging

```bash
# Check Ollama status
curl http://localhost:11434

# List models
ollama list

# Check model details
ollama show qwen2.5:7b

# Watch Ollama logs
ollama serve  # In foreground with logs
```

---

## Environment Variables

### Backend Configuration

**File**: `backend/.env` (create from `.env.example`)

```bash
# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_MAX_CONNECTIONS=20

# Ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:7b
EMBEDDING_MODEL=mxbai-embed-large

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

# Memory
REDIS_SESSION_TTL_SECONDS=18144000  # 7 months
```

### Frontend Configuration

**File**: `frontend/.env` (optional)

```bash
VITE_API_URL=http://localhost:8000
```

---

## Hot Reload

### Backend Hot Reload

```bash
# Docker Compose (watches files)
docker-compose up --build

# Or local with uvicorn
cd backend
uv run uvicorn backend.src.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Hot Reload

```bash
# Vite dev server (automatic)
cd frontend
npm run dev

# Changes reflected immediately in browser
```

---

## Common Development Tasks

### Add a New Tool

1. **Create tool file**: `backend/src/apple_health/query_tools/my_tool.py`

```python
from langchain_core.tools import tool

@tool
async def my_new_tool(user_id: str, param: str) -> dict:
    """
    Tool description for LLM.

    Args:
        user_id: User identifier
        param: Parameter description
    """
    # Implementation
    return {"result": ...}
```

2. **Export tool**: `backend/src/apple_health/query_tools/__init__.py`

```python
from .my_tool import my_new_tool

__all__ = ["my_new_tool", ...]
```

3. **Register tool**: `backend/src/apple_health/query_tools/__init__.py`

```python
def create_user_bound_tools(user_id: str) -> list[BaseTool]:
    return [
        my_new_tool,
        # ... other tools
    ]
```

4. **Test tool**:

```python
# tests/unit/test_my_tool.py
async def test_my_new_tool():
    result = await my_new_tool.ainvoke({"user_id": "test", "param": "value"})
    assert result["result"] is not None
```

---

### Add a New API Endpoint

1. **Define endpoint**: `backend/src/api/chat_routes.py`

```python
@router.post("/my-endpoint")
async def my_endpoint(request: MyRequest) -> MyResponse:
    """
    Endpoint description.

    Args:
        request: Request model

    Returns:
        Response model
    """
    # Implementation
    return MyResponse(...)
```

2. **Define models**: `backend/src/api/models.py`

```python
from pydantic import BaseModel

class MyRequest(BaseModel):
    param: str

class MyResponse(BaseModel):
    result: str
```

3. **Test endpoint**:

```bash
curl -X POST http://localhost:8000/api/my-endpoint \
  -H "Content-Type: application/json" \
  -d '{"param": "value"}'
```

---

### Add a New Memory Type

1. **Create manager**: `backend/src/services/my_memory_manager.py`

```python
class MyMemoryManager:
    def __init__(self) -> None:
        self.redis_manager = get_redis_manager()

    async def store(self, key: str, value: str) -> bool:
        ...

    async def retrieve(self, key: str) -> str | None:
        ...
```

2. **Integrate with coordinator**: `backend/src/services/memory_coordinator.py`

```python
from .my_memory_manager import get_my_memory_manager

class MemoryCoordinator:
    def __init__(self) -> None:
        self.my_memory = get_my_memory_manager()
        ...
```

---

## Troubleshooting

### Issue: Port Already in Use

```bash
# Find process using port
lsof -ti:8000  # Backend
lsof -ti:3000  # Frontend
lsof -ti:6379  # Redis

# Kill process
lsof -ti:8000 | xargs kill -9
```

### Issue: Redis Connection Failed

```bash
# Check Redis is running
docker-compose ps redis

# Restart Redis
docker-compose restart redis

# Check logs
docker-compose logs redis
```

### Issue: Ollama Not Responding

```bash
# Check Ollama is running
ps aux | grep ollama

# Start Ollama
ollama serve

# Verify connection
curl http://localhost:11434
```

### Issue: Module Not Found

```bash
# Backend
cd backend
uv sync  # Reinstall dependencies

# Frontend
cd frontend
npm install  # Reinstall dependencies
```

---

## Performance Profiling

### Profile Backend

```bash
# Install profiler
uv add --dev py-spy

# Profile running process
py-spy record -o profile.svg --pid $(pgrep -f "uvicorn")

# View profile.svg in browser
```

### Profile Redis

```bash
# Monitor commands
docker exec -it redis-wellness-redis-1 redis-cli MONITOR

# Slow log
docker exec -it redis-wellness-redis-1 redis-cli SLOWLOG GET 10
```

---

## See Also

- **Testing Guide**: `docs/07_TESTING.md`
- **API Reference**: `docs/09_API.md`
- **Architecture**: `docs/03_ARCHITECTURE.md`
- **Code Quality**: `docs/08_CODE_QUALITY.md`

---

**Last Updated**: October 24, 2024
