# Testing Guide

**Last Updated**: October 2025

## Status: ✅ REAL Tests Implemented

New test suite built from scratch with **REAL TESTS - NO MOCKS**.

## Quick Start

```bash
cd backend

# Run fast unit tests (50 tests, ~0.3s)
uv run pytest tests/unit/ -q

# Run all tests except expensive LLM tests
uv run pytest tests/ -m "not llm" -v

# Run everything (requires Redis + Ollama)
docker-compose up -d
uv run pytest tests/ -v
```

## Test Structure

```
backend/tests/
├── conftest.py           # Fixtures (Redis, LLM, test data)
├── unit/                 # Fast, no dependencies (50 tests)
│   ├── test_numeric_validator.py
│   ├── test_stats_utils.py
│   └── test_time_utils.py
├── integration/          # Require Redis
│   └── test_redis_services.py
├── api/                  # Require FastAPI backend
│   └── test_chat_endpoints.py
└── llm/                  # Expensive, require Ollama
    └── test_agents.py
```

## Running Tests

### Unit Tests (Fast, No Dependencies)

```bash
# All unit tests
uv run pytest tests/unit/ -v

# Specific test file
uv run pytest tests/unit/test_numeric_validator.py -v

# Specific test class
uv run pytest tests/unit/test_numeric_validator.py::TestNumericValidatorExtraction -v

# Quick smoke test
uv run pytest tests/unit/ -q
```

**50 tests, ~0.3 seconds**

### Integration Tests (Require Redis)

```bash
# Start Redis
docker-compose up -d redis

# Run integration tests
uv run pytest tests/integration/ -v
```

### API Tests (Require Backend)

```bash
# Start full stack
docker-compose up -d

# Run API tests
uv run pytest tests/api/ -v
```

### LLM Tests (Expensive, Require Ollama)

```bash
# Start Ollama
ollama serve

# Ensure models are pulled
ollama pull qwen2.5:7b
ollama pull mxbai-embed-large

# Run LLM tests (SLOW - ~30s per test)
uv run pytest tests/llm/ -v
```

⚠️ **Warning**: LLM tests are expensive and slow. Run sparingly.

### Using Test Markers

```bash
# Only unit tests (fast)
uv run pytest -m unit -v

# Only integration tests (need Redis)
uv run pytest -m integration -v

# Skip expensive LLM tests (recommended for CI)
uv run pytest -m "not llm" -v

# Only API tests
uv run pytest -m api -v
```

## Test Coverage

### ✅ Covered

**Unit Tests (50 tests)**
- `NumericValidator`: Hallucination detection (19 tests)
  - Number extraction with units
  - Value matching with tolerance
  - Hallucination detection
  - Correction functionality
- `stats_utils`: Statistical calculations (21 tests)
  - Basic stats (mean, std, min, max)
  - Linear regression
  - Moving averages
  - Correlation
  - Period comparisons
- `time_utils`: DateTime parsing (10 tests)
  - UTC timestamp generation
  - ISO 8601 parsing
  - Natural language time periods

**Integration Tests**
- Redis connection management
- Basic Redis operations (set/get, JSON, TTL)

**API Tests**
- Stateless chat endpoint
- Redis RAG chat endpoint
- Conversation history
- Health check

**LLM Tests (Expensive)**
- Stateless agent basic responses
- Stateful agent with memory
- Response quality validation

### ⏳ Not Yet Covered

- Apple Health XML parsing
- Memory coordinator workflows
- Tool calling validation
- Workout data indexing
- Embedding service

Add tests incrementally as critical paths emerge.

## Test Philosophy

### NO MOCKS - Use Real Services

All tests interact with real services:

- **Redis tests** → Real Redis (via docker-compose)
- **API tests** → Real FastAPI (TestClient)
- **LLM tests** → Real Ollama/Qwen
- **Unit tests** → Real numpy/scipy calculations

### Why No Mocks?

1. **False positives**: Mocks can pass even when real code breaks
2. **Integration validation**: Real services catch interface issues
3. **Confidence**: Tests validate actual behavior
4. **Maintenance**: No mock drift when implementation changes

### When to Add Tests

Add tests when:
- **Critical path identified**: Feature used in production
- **Bug found**: Regression test prevents recurrence
- **Complex logic**: Algorithm needs validation
- **API contract**: External interface needs stability

## Test Examples

### Unit Test Example

```python
@pytest.mark.unit
def test_hallucination_detection():
    """Test detecting hallucinated numbers."""
    validator = NumericValidator()

    tool_results = [{"content": "Weight: 70 kg"}]
    response = "Your weight is 80 kg"  # Hallucinated!

    result = validator.validate_response(response, tool_results)

    assert result["valid"] is False
    assert len(result["hallucinations"]) == 1
```

### Integration Test Example

```python
@pytest.mark.integration
def test_redis_operations(clean_redis):
    """Test real Redis set/get."""
    clean_redis.set("test_key", "test_value")

    result = clean_redis.get("test_key")

    assert result == b"test_value"
```

### LLM Test Example

```python
@pytest.mark.llm
@pytest.mark.asyncio
async def test_agent_response(stateless_agent):
    """Test real LLM generates response."""
    result = await stateless_agent.chat(
        message="Hello",
        user_id="test",
        session_id="test"
    )

    assert result["response"]
    assert len(result["response"]) > 0
```

## CI/CD Integration

### Pre-commit (Fast)

Pre-commit hooks run linting only:
```bash
# Automatically runs on git commit
ruff check --fix src tests
ruff format src tests
```

### Pre-push (Comprehensive)

Pre-push hooks run quality checks:
```bash
# Automatically runs on git push
# - Backend: ruff check + format
# - Frontend: typecheck + lint + ts-prune
# - Docker: build verification
```

### CI Pipeline (Recommended)

```yaml
# Example GitHub Actions workflow
- name: Run unit tests
  run: uv run pytest tests/unit/ -v

- name: Run integration tests
  run: |
    docker-compose up -d redis
    uv run pytest tests/integration/ -v

- name: Skip LLM tests in CI
  run: uv run pytest -m "not llm" -v
```

## Troubleshooting

### Redis Connection Failed

```
Error: Redis connection failed. Is docker-compose running?
```

**Fix**: Start Redis
```bash
docker-compose up -d redis
```

### Ollama Not Available

```
Ollama not available. Is ollama running?
```

**Fix**: Start Ollama
```bash
ollama serve
ollama pull qwen2.5:7b
```

### Import Errors

```
ModuleNotFoundError: No module named 'src'
```

**Fix**: Run from backend directory
```bash
cd backend
uv run pytest tests/
```

### Slow Tests

LLM tests are intentionally slow (~30s each). Skip them:
```bash
uv run pytest -m "not llm" -v
```

## Development Workflow

### Adding New Tests

1. **Choose test type** (unit/integration/api/llm)
2. **Create test file** in appropriate directory
3. **Mark with pytest.mark** (@pytest.mark.unit, etc.)
4. **Use real services** (no mocks)
5. **Run tests** to verify
6. **Update this doc** if adding new patterns

### Example: Adding a New Unit Test

```python
# backend/tests/unit/test_my_feature.py

import pytest
from src.utils.my_feature import my_function

@pytest.mark.unit
class TestMyFeature:
    """Test my new feature."""

    def test_basic_case(self):
        """Test basic functionality."""
        result = my_function(input_data)

        assert result == expected_output
```

Run it:
```bash
uv run pytest tests/unit/test_my_feature.py -v
```

## Summary

- **50 unit tests** pass in ~0.3s (no dependencies)
- **Integration tests** use real Redis
- **API tests** use real FastAPI
- **LLM tests** use real Ollama/Qwen (expensive)
- **NO MOCKS** - All tests validate actual behavior
- **Quality maintained** through: tests + linting + pre-commit + pre-push hooks

For questions or issues, see the test files themselves - they're well-documented with examples.
