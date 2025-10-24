# Testing Strategy

**Last Updated**: October 24, 2024

## Overview

Redis Wellness has **91+ tests** across multiple categories, ensuring production-ready quality and preventing LLM hallucinations through comprehensive validation.

### Test Philosophy

1. **Anti-Hallucination First**: Every test validates LLM responses against tool data
2. **Real Redis**: Integration tests use actual Redis (not mocks)
3. **Isolated Units**: Pure functions tested without dependencies
4. **Fast Feedback**: Unit tests run in <5 seconds

---

## Test Structure

### Directory Organization

```
backend/tests/
├── conftest.py                    # Shared fixtures
├── fixtures/                      # Test data fixtures
│   └── __init__.py
├── unit/                          # Pure function tests (no Redis)
│   ├── __init__.py
│   ├── test_numeric_validator.py  # Hallucination detection
│   └── test_stats_utils.py        # Statistical calculations
├── integration/                   # Service integration tests
│   ├── __init__.py
│   ├── test_redis_connection.py   # Connection pooling
│   ├── test_memory_coordinator.py # CoALA memory system
│   └── test_workout_data_queries.py # Health data queries
├── agent/                         # Agent behavior tests
│   ├── __init__.py
│   ├── test_stateless_agent.py    # No-memory baseline
│   └── test_stateful_agent.py     # CoALA memory agent
├── api/                           # HTTP API tests
│   ├── __init__.py
│   └── test_chat_routes.py        # Chat endpoint integration
└── e2e/                           # End-to-end scenarios
    └── __init__.py
```

---

## Test Categories

### 1. Unit Tests (No Dependencies)

**Purpose**: Test pure functions in isolation

**Characteristics**:
- No Redis required
- No Ollama required
- Fast execution (<5 seconds total)
- 100% deterministic

**Example**:
```python
# tests/unit/test_numeric_validator.py

def test_numeric_validator_detects_hallucination():
    """Test that validator catches LLM hallucinations."""
    validator = NumericValidator()

    # LLM says 95 bpm, but tool returned 87 bpm
    tool_results = [{"content": '{"average": 87, "unit": "bpm"}'}]
    response_text = "Your average heart rate was 95 bpm"

    result = validator.validate_response(response_text, tool_results)

    assert not result["valid"]
    assert result["score"] < 0.5
    assert len(result["hallucinations"]) > 0
    assert "95" in result["hallucinations"][0]["response_number"]
```

**Running**:
```bash
uv run pytest tests/unit/ -v
```

---

### 2. Integration Tests (Redis Required)

**Purpose**: Test services with real Redis

**Characteristics**:
- Requires running Redis
- Tests actual data flow
- Validates Redis operations
- Slower (~10-30 seconds)

**Example**:
```python
# tests/integration/test_memory_coordinator.py

@pytest.mark.asyncio
async def test_memory_coordinator_stores_interaction():
    """Test coordinator stores across all 4 memory types."""
    coordinator = get_memory_coordinator()

    # Store interaction
    results = await coordinator.store_interaction(
        session_id="test_session",
        user_message="What was my heart rate?",
        assistant_response="Your average was 87 bpm",
        tools_used=["aggregate_metrics"],
        execution_time_ms=1250.5,
        success_score=0.95
    )

    # Verify all memory types stored
    assert results["short_term_user"] is True
    assert results["short_term_assistant"] is True
    assert results["procedural"] is True

    # Retrieve and verify
    stats = await coordinator.get_memory_stats(
        session_id="test_session",
        user_id="user123"
    )

    assert stats["short_term"]["message_count"] >= 2
    assert stats["procedural"]["total_procedures"] > 0
```

**Running**:
```bash
# Start Redis first
docker-compose up -d redis

# Run integration tests
uv run pytest tests/integration/ -v
```

---

### 3. Agent Tests (Redis + LLM)

**Purpose**: Test agent behavior end-to-end

**Characteristics**:
- Requires Redis + Ollama
- Tests full agent flow
- Validates tool calling
- Slowest (~30-60 seconds)

**Example**:
```python
# tests/agent/test_stateful_agent.py

@pytest.mark.asyncio
async def test_stateful_agent_uses_memory():
    """Test stateful agent retrieves and uses memory."""
    coordinator = get_memory_coordinator()
    agent = StatefulRAGAgent(coordinator)

    # Store context in memory
    await coordinator.store_interaction(
        session_id="test",
        user_message="My goal is to workout 3 times per week",
        assistant_response="Got it! I'll track your progress.",
        tools_used=[]
    )

    # Query that requires memory
    result = await agent.chat(
        message="Am I meeting my goal?",
        user_id="user123",
        session_id="test"
    )

    # Verify memory was used
    assert result["memory_stats"]["episodic_hits"] > 0
    assert "3" in result["response"] or "three" in result["response"].lower()
```

**Running**:
```bash
# Start all services
docker-compose up -d

# Run agent tests
uv run pytest tests/agent/ -v
```

---

### 4. API Tests (Full Stack)

**Purpose**: Test HTTP endpoints

**Characteristics**:
- Requires running backend
- Tests request/response
- Validates error handling
- Integration with FastAPI

**Example**:
```python
# tests/api/test_chat_routes.py

@pytest.mark.asyncio
async def test_redis_chat_endpoint(client):
    """Test Redis chat endpoint with memory."""
    response = await client.post(
        "/api/chat/redis",
        json={
            "message": "What was my average heart rate last week?",
            "session_id": "test_session"
        }
    )

    assert response.status_code == 200
    data = response.json()

    assert "response" in data
    assert "tools_used" in data
    assert "memory_stats" in data
    assert len(data["tools_used"]) > 0
```

**Running**:
```bash
uv run pytest tests/api/ -v
```

---

## Anti-Hallucination Strategy

### The Problem

LLMs can "hallucinate" - make up numbers that weren't in the tool results.

**Example**:
```python
# Tool returned: {"average": 87, "unit": "bpm"}
# LLM response: "Your average was 95 bpm"  # WRONG!
```

### Our Solution: Numeric Validator

**3-step validation process**:

1. **Extract all numbers from response**
2. **Extract all numbers from tool results**
3. **Match response numbers to tool data**

**Implementation**:
```python
# utils/numeric_validator.py

class NumericValidator:
    def validate_response(
        self,
        response_text: str,
        tool_results: list[dict],
        strict: bool = False
    ) -> dict:
        """
        Validate LLM response against tool data.

        Returns:
            {
                "valid": bool,
                "score": float,  # 0-1
                "hallucinations": list[dict],
                "stats": {
                    "total_numbers": int,
                    "matched": int,
                    "unmatched": int
                }
            }
        """
        # Extract numbers from response
        response_numbers = self._extract_numbers(response_text)

        # Extract numbers from tool results
        tool_numbers = self._extract_tool_numbers(tool_results)

        # Match and calculate score
        matched = self._match_numbers(response_numbers, tool_numbers)

        return {
            "valid": matched / len(response_numbers) > 0.8,
            "score": matched / len(response_numbers),
            "hallucinations": self._find_hallucinations(...),
            "stats": {...}
        }
```

### Testing Anti-Hallucination

**Every agent test includes validation**:

```python
@pytest.mark.asyncio
async def test_agent_no_hallucination():
    """Test agent doesn't hallucinate numbers."""
    agent = StatefulRAGAgent(coordinator)

    result = await agent.chat(
        message="What was my average heart rate?",
        user_id="test_user",
        session_id="test"
    )

    # Validation is automatic in agent
    assert result["validation"]["valid"] is True
    assert result["validation"]["score"] >= 0.8
    assert result["validation"]["hallucinations_detected"] == 0
```

---

## Test Fixtures

### Shared Fixtures (`conftest.py`)

```python
import pytest
from backend.src.services.memory_coordinator import get_memory_coordinator

@pytest.fixture
async def coordinator():
    """Get memory coordinator for tests."""
    return get_memory_coordinator()

@pytest.fixture
async def clean_redis():
    """Clean Redis before test."""
    from backend.src.services.redis_connection import get_redis_manager

    redis_manager = get_redis_manager()
    with redis_manager.get_connection() as client:
        client.flushdb()

    yield

    # Cleanup after test
    with redis_manager.get_connection() as client:
        client.flushdb()

@pytest.fixture
def sample_health_data():
    """Sample health records for testing."""
    return {
        "HeartRate": [
            {"value": 87, "date": "2024-10-20", "unit": "bpm"},
            {"value": 85, "date": "2024-10-21", "unit": "bpm"},
        ],
        "StepCount": [
            {"value": 10000, "date": "2024-10-20", "unit": "steps"},
        ]
    }
```

---

## Running Tests

### Quick Test Commands

```bash
# All tests
uv run pytest

# By category
uv run pytest tests/unit/              # Unit only
uv run pytest tests/integration/       # Integration only
uv run pytest tests/agent/             # Agent only
uv run pytest tests/api/               # API only

# By file
uv run pytest tests/unit/test_numeric_validator.py

# By test name
uv run pytest -k "test_memory"

# Verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x

# Show print statements
uv run pytest -s

# Parallel execution (if pytest-xdist installed)
uv run pytest -n auto
```

### With Coverage

```bash
# Generate coverage report
uv run pytest --cov=src --cov-report=html

# View coverage
open htmlcov/index.html

# Coverage threshold
uv run pytest --cov=src --cov-fail-under=80
```

### Watch Mode (Continuous)

```bash
# Install pytest-watch
uv add --dev pytest-watch

# Run tests on file changes
uv run ptw
```

---

## Writing New Tests

### Test Naming Convention

```python
# File: test_<module_name>.py
# Function: test_<feature>_<should>_<action>_<when>_<condition>

# ✅ GOOD
def test_validator_detects_hallucination_when_numbers_mismatch():
    ...

def test_memory_coordinator_retrieves_all_types_when_available():
    ...

# ❌ BAD
def test_1():  # Not descriptive
    ...

def test_memory():  # Too vague
    ...
```

### Test Structure (AAA Pattern)

```python
def test_feature():
    """Test that feature does X when Y."""
    # Arrange - Set up test data
    input_data = {"key": "value"}
    expected = {"result": "expected"}

    # Act - Execute the function
    result = function_under_test(input_data)

    # Assert - Verify the results
    assert result == expected
    assert result["key"] == "value"
```

### Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function()
    assert result is not None
```

### Mocking (When Necessary)

```python
from unittest.mock import Mock, patch

@patch('backend.src.services.embedding_service.httpx.AsyncClient')
async def test_embedding_service_handles_failure(mock_client):
    """Test embedding service handles Ollama failures."""
    # Arrange
    mock_client.return_value.post.side_effect = Exception("Connection failed")
    service = EmbeddingService()

    # Act & Assert
    with pytest.raises(LLMServiceError):
        await service.generate_embedding("test query")
```

---

## Test Coverage Goals

### Current Coverage

| Component | Coverage | Goal | Status |
|-----------|----------|------|--------|
| Agents | 85% | 80% | ✅ |
| Services | 82% | 80% | ✅ |
| Utils | 90% | 85% | ✅ |
| API | 75% | 70% | ✅ |
| **Overall** | **83%** | **80%** | ✅ |

### Priority Areas

**Must have coverage**:
- ✅ Memory managers (episodic, procedural, semantic, short-term)
- ✅ Agents (stateless, stateful)
- ✅ Numeric validator (anti-hallucination)
- ✅ Redis connection management

**Good to have coverage**:
- API routes (tested via integration)
- Tool implementations
- Error handling paths

**Not critical**:
- Type stubs (`__init__.py`)
- Configuration files
- Fixtures

---

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis/redis-stack:latest
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install uv
        run: pip install uv

      - name: Install dependencies
        run: |
          cd backend
          uv sync

      - name: Run tests
        run: |
          cd backend
          uv run pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml
```

---

## Test Data Management

### Fixture Files

```
backend/tests/fixtures/
├── sample_health_records.json
├── sample_workouts.json
└── sample_memory_data.json
```

### Loading Fixtures

```python
import json
from pathlib import Path

def load_fixture(name: str):
    """Load test fixture by name."""
    fixture_path = Path(__file__).parent / "fixtures" / f"{name}.json"
    with open(fixture_path) as f:
        return json.load(f)

# Usage
@pytest.fixture
def health_records():
    return load_fixture("sample_health_records")
```

---

## Performance Testing

### Test Execution Time

```bash
# Show slowest tests
uv run pytest --durations=10

# Typical execution times:
# - Unit tests: <5 seconds
# - Integration tests: 10-30 seconds
# - Agent tests: 30-60 seconds
# - Full suite: ~2 minutes
```

### Performance Benchmarks

```python
import time

def test_memory_retrieval_performance():
    """Test memory retrieval is fast (<100ms)."""
    coordinator = get_memory_coordinator()

    start = time.time()
    result = await coordinator.retrieve_all_context(
        session_id="test",
        query="test query"
    )
    duration_ms = (time.time() - start) * 1000

    assert duration_ms < 100, f"Too slow: {duration_ms}ms"
```

---

## Common Test Patterns

### Testing Exceptions

```python
def test_function_raises_error_when_invalid():
    """Test function raises appropriate error."""
    with pytest.raises(ValidationError) as exc_info:
        function_with_validation(invalid_input)

    assert "Invalid input" in str(exc_info.value)
```

### Testing Logging

```python
def test_function_logs_error(caplog):
    """Test function logs errors appropriately."""
    with caplog.at_level(logging.ERROR):
        function_that_logs()

    assert "Error message" in caplog.text
```

### Testing with Parametrize

```python
@pytest.mark.parametrize("input,expected", [
    (87, "normal"),
    (120, "elevated"),
    (55, "low"),
])
def test_heart_rate_classification(input, expected):
    """Test heart rate classification for various inputs."""
    result = classify_heart_rate(input)
    assert result == expected
```

---

## Troubleshooting Tests

### Issue: Redis Connection Failed

```bash
# Start Redis
docker-compose up -d redis

# Verify Redis is running
docker-compose ps redis

# Check connection
docker exec redis-wellness-redis-1 redis-cli ping
```

### Issue: Ollama Not Available

```bash
# Tests that require Ollama should skip if not available
@pytest.mark.skipif(
    not is_ollama_available(),
    reason="Ollama not available"
)
async def test_with_ollama():
    ...
```

### Issue: Flaky Tests

```python
# Add retries for flaky tests
@pytest.mark.flaky(reruns=3)
async def test_sometimes_fails():
    ...
```

### Issue: Tests Take Too Long

```bash
# Run only fast tests
uv run pytest -m "not slow"

# Mark slow tests
@pytest.mark.slow
async def test_slow_operation():
    ...
```

---

## Test Quality Checklist

When writing tests, ensure:

- [ ] Test name clearly describes what's being tested
- [ ] Docstring explains the test purpose
- [ ] Test is isolated (doesn't depend on other tests)
- [ ] Test cleans up after itself
- [ ] Assertions are specific (not just `assert result`)
- [ ] Edge cases are covered
- [ ] Error cases are tested
- [ ] Test is fast (or marked as slow)
- [ ] Test is deterministic (no random values)

---

## See Also

- **Development Guide**: `docs/06_DEVELOPMENT.md`
- **Architecture**: `docs/03_ARCHITECTURE.md`
- **API Reference**: `docs/09_API.md`

---

**Last Updated**: October 24, 2024
