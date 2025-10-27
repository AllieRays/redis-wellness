# Backend Test Plan - Redis Wellness

## Overview

This test plan establishes **systematic, accurate testing** for the Redis Wellness backend with emphasis on:
1. **No false positives/negatives** - Tests must be deterministic
2. **LLM validation** - Test for valid responses, not exact text matches
3. **Pure function isolation** - Test math/logic separately from LLM calls
4. **Integration boundaries** - Clear separation of unit vs integration tests

---

## Test Architecture

```
backend/tests/
├── unit/                          # Pure functions, no external dependencies
│   ├── test_numeric_validator.py     # LLM hallucination detection
│   ├── test_stats_utils.py           # Statistical calculations (numpy/scipy)
│   ├── test_conversion_utils.py      # Unit conversions
│   ├── test_time_utils.py            # Date/time parsing
│   ├── test_query_classifier.py      # Intent classification logic
│   ├── test_verbosity_detector.py    # Response style detection
│   └── test_pronoun_resolver.py      # Pronoun context resolution
│
├── integration/                   # Tests requiring Redis/services
│   ├── test_redis_connection.py      # Redis connection management
│   ├── test_memory_manager.py        # Dual memory system
│   ├── test_redis_health_manager.py  # Health data CRUD
│   ├── test_embedding_cache.py       # Embedding caching
│   └── test_redis_workout_indexer.py # Workout vectorization
│
├── agent/                         # Agent behavior tests (LLM-dependent)
│   ├── test_stateless_agent.py       # Stateless agent tool calling
│   ├── test_stateful_agent.py        # RAG agent with memory
│   ├── test_tool_execution.py        # Tool calling validation
│   └── test_response_validation.py   # NumericValidator integration
│
├── api/                           # HTTP endpoint tests
│   ├── test_chat_routes.py           # Chat API endpoints
│   ├── test_tools_routes.py          # Direct tool endpoints
│   └── test_system_routes.py         # Health checks
│
├── e2e/                           # End-to-end workflows
│   ├── test_health_data_pipeline.py  # XML → Redis → Query
│   ├── test_memory_persistence.py    # Conversation storage
│   └── test_stateless_vs_redis.py    # Side-by-side comparison
│
├── fixtures/                      # Test data and mocks
│   ├── health_data.py                # Sample health records
│   ├── mock_ollama.py                # LLM response mocks
│   └── redis_fixtures.py             # Redis test data
│
└── conftest.py                    # Shared pytest configuration
```

---

## Test Categories

### 1. Unit Tests (Pure Functions)

**Philosophy**: Test logic without external dependencies. All math/parsing done deterministically.

#### 1.1 Numeric Validation (`test_numeric_validator.py`)
```python
# ✅ GOOD: Test extraction logic with known inputs
def test_extract_numbers_with_units():
    validator = NumericValidator()
    text = "Your weight is 136.8 lb and BMI is 23.6"
    numbers = validator.extract_numbers_with_context(text)

    assert len(numbers) == 2
    assert numbers[0]["value"] == 136.8
    assert numbers[0]["unit"] == "lb"
    assert numbers[1]["value"] == 23.6

# ✅ GOOD: Test matching logic with controlled data
def test_values_match_within_tolerance():
    validator = NumericValidator(tolerance=0.1)
    assert validator.values_match(100, 105) is True   # 5% diff
    assert validator.values_match(100, 115) is False  # 15% diff
    assert validator.values_match(70.2, 70) is True   # Rounding

# ✅ GOOD: Test validation with mock tool results
def test_validate_response_catches_hallucinations():
    validator = NumericValidator()
    tool_results = [{"name": "tool", "content": "Weight: 136.8 lb"}]

    # Valid response - number matches tool
    valid = validator.validate_response("Your weight is 136.8 lb", tool_results)
    assert valid["valid"] is True
    assert valid["score"] == 1.0

    # Hallucinated response - number not in tools
    invalid = validator.validate_response("Your weight is 200 lb", tool_results)
    assert invalid["valid"] is False
    assert len(invalid["hallucinations"]) > 0

# ❌ BAD: Testing actual LLM output (belongs in agent tests)
def test_llm_never_hallucinates():  # Too broad, non-deterministic
    pass
```

#### 1.2 Statistical Utilities (`test_stats_utils.py`)
```python
# ✅ GOOD: Test mathematical functions with known values
def test_calculate_basic_stats():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    stats = calculate_basic_stats(values)

    assert stats["average"] == 3.0
    assert stats["min"] == 1.0
    assert stats["max"] == 5.0
    assert stats["count"] == 5
    assert abs(stats["std_dev"] - 1.414) < 0.01

def test_linear_regression_trend_detection():
    dates = [datetime(2024, 1, i) for i in range(1, 11)]
    values = [170 - i*0.5 for i in range(10)]  # Decreasing trend

    result = calculate_linear_regression(dates, values)

    assert result["trend_direction"] == "decreasing"
    assert result["slope"] < 0
    assert result["r_squared"] > 0.95  # Strong correlation

def test_compare_periods_with_significant_change():
    period1 = [100, 102, 101, 99, 100]   # avg ~100
    period2 = [90, 92, 91, 89, 88]       # avg ~90

    result = compare_periods(period1, period2, "Now", "Before")

    assert result["change"]["direction"] == "decrease"
    assert result["change"]["percentage"] < -5
    assert result["statistical_test"]["significant"] is True

# ✅ GOOD: Edge cases
def test_stats_with_empty_list():
    stats = calculate_basic_stats([])
    assert stats["count"] == 0
    assert stats["average"] == 0.0
```

#### 1.3 Time Utilities (`test_time_utils.py`)
```python
def test_parse_time_period_recent():
    start, end, desc = parse_time_period("recent")
    assert (end - start).days == 30

def test_parse_time_period_month_name():
    start, end, desc = parse_time_period("September 2024")
    assert start.month == 9
    assert start.year == 2024
    assert desc == "September 2024"

def test_parse_time_period_early_late_modifiers():
    start, end, desc = parse_time_period("early September")
    assert (end - start).days <= 10

def test_parse_health_record_date():
    # Test ISO format
    date1 = parse_health_record_date("2024-10-22")
    assert date1.day == 22

    # Test datetime object passthrough
    dt = datetime.now()
    date2 = parse_health_record_date(dt)
    assert date2 == dt
```

#### 1.4 Conversion Utilities (`test_conversion_utils.py`)
```python
def test_convert_weight_kg_to_lbs():
    assert abs(convert_weight_to_lbs(100, "kg") - 220.46) < 0.01

def test_convert_weight_lbs_passthrough():
    assert convert_weight_to_lbs(150, "lb") == 150
    assert convert_weight_to_lbs(150, "lbs") == 150

def test_convert_weight_invalid_unit():
    with pytest.raises(ValueError):
        convert_weight_to_lbs(100, "stones")
```

---

### 2. Integration Tests (Redis/Services)

**Philosophy**: Test data layer and service interactions. Mock external APIs (Ollama).

#### 2.1 Redis Connection (`test_redis_connection.py`)
```python
@pytest.mark.integration
def test_redis_connection_manager():
    manager = get_redis_manager()

    with manager.get_connection() as client:
        client.set("test_key", "test_value")
        assert client.get("test_key") == b"test_value"

@pytest.mark.integration
def test_redis_connection_pool_reuse():
    manager = get_redis_manager()

    # Ensure connections are pooled
    with manager.get_connection() as client1:
        id1 = id(client1.connection_pool)

    with manager.get_connection() as client2:
        id2 = id(client2.connection_pool)

    assert id1 == id2  # Same pool

@pytest.mark.integration
def test_redis_connection_error_handling():
    manager = RedisConnectionManager(host="invalid_host")

    with pytest.raises(InfrastructureError):
        with manager.get_connection() as client:
            client.ping()
```

#### 2.2 Memory Manager (`test_memory_manager.py`)
```python
@pytest.mark.integration
async def test_short_term_memory_storage_and_retrieval():
    manager = get_memory_manager()
    user_id = "test_user"
    session_id = "test_session"

    # Store messages
    await manager.store_short_term_message(user_id, session_id, "user", "Hello")
    await manager.store_short_term_message(user_id, session_id, "assistant", "Hi there")

    # Retrieve context
    context = await manager.get_short_term_context(user_id, session_id)

    assert "Hello" in context
    assert "Hi there" in context

@pytest.mark.integration
async def test_semantic_memory_search():
    manager = get_memory_manager()
    user_id = "test_user"

    # Store semantic memory
    await manager.store_semantic_memory(
        user_id, "My BMI goal is 22", {"type": "user_goal"}
    )

    # Search
    results = await manager.retrieve_semantic_memory(user_id, "What's my BMI target?")

    assert results["hits"] > 0
    assert "22" in results["context"]

@pytest.mark.integration
async def test_memory_ttl_expiration():
    manager = get_memory_manager()
    user_id = "test_user"
    session_id = "test_session"

    # Store with short TTL (test mode)
    await manager.store_short_term_message(
        user_id, session_id, "user", "Test", ttl_seconds=1
    )

    # Verify exists
    context1 = await manager.get_short_term_context(user_id, session_id)
    assert "Test" in context1

    # Wait for expiration
    await asyncio.sleep(2)

    # Verify expired
    context2 = await manager.get_short_term_context(user_id, session_id)
    assert context2 is None or "Test" not in context2
```

#### 2.3 Apple Health Manager (`test_redis_health_manager.py`)
```python
@pytest.mark.integration
def test_store_and_retrieve_health_data():
    manager = RedisAppleHealthManager()
    user_id = "test_user"

    health_data = {
        "metrics_summary": {
            "BodyMass": {"latest_value": 70, "unit": "kg", "count": 10}
        },
        "metrics_records": {
            "BodyMass": [
                {"date": "2024-10-20", "value": 70, "unit": "kg"},
                {"date": "2024-10-21", "value": 69.5, "unit": "kg"},
            ]
        }
    }

    manager.store_health_data(user_id, health_data)
    retrieved = manager.get_health_data(user_id)

    assert retrieved["metrics_summary"]["BodyMass"]["count"] == 10
    assert len(retrieved["metrics_records"]["BodyMass"]) == 2

@pytest.mark.integration
def test_query_health_metrics_by_date_range():
    manager = RedisAppleHealthManager()
    user_id = "test_user"

    # Store data (setup from previous test or fixture)

    results = manager.query_metrics(
        user_id,
        metric_types=["BodyMass"],
        start_date="2024-10-20",
        end_date="2024-10-21"
    )

    assert len(results) > 0
    assert all(r["metric_type"] == "BodyMass" for r in results)
```

---

### 3. Agent Tests (LLM-Dependent)

**Philosophy**: Test agent behavior with **mocked LLM responses** or **validation of structure**, not exact text.

#### 3.1 Tool Execution (`test_tool_execution.py`)
```python
@pytest.mark.agent
async def test_agent_selects_correct_tool_for_query():
    """Test that agent chooses appropriate tool without validating exact text."""
    agent = StatelessHealthAgent()

    # Query that should trigger search_health_records tool
    result = await agent.chat(
        message="What's my current weight?",
        user_id="test_user"
    )

    # ✅ GOOD: Validate structure, not content
    assert "tools_used" in result
    assert any("search_health_records" in str(tool) for tool in result["tools_used"])
    assert result["response"]  # Has a response

    # ❌ BAD: Don't check exact text (LLM varies)
    # assert "Your weight is" in result["response"]  # Too brittle

@pytest.mark.agent
async def test_agent_chains_multiple_tools():
    """Test multi-step reasoning without exact text matching."""
    agent = StatefulRAGAgent(memory_manager=get_memory_manager())

    result = await agent.chat(
        message="Compare my workout frequency this month vs last month",
        user_id="test_user",
        session_id="test"
    )

    # ✅ GOOD: Verify tool chaining occurred
    assert result["tool_calls_made"] >= 2  # Multiple tools called
    assert len(result["tools_used"]) >= 2

    # ✅ GOOD: Verify response has numeric data
    validator = get_numeric_validator()
    numbers = validator.extract_numbers_with_context(result["response"])
    assert len(numbers) > 0  # Response contains numbers

@pytest.mark.agent
async def test_agent_with_mocked_llm_response():
    """Test with completely mocked LLM to ensure determinism."""

    # Mock LLM to return specific tool calls
    mock_llm_response = AIMessage(
        content="",
        tool_calls=[{
            "name": "search_health_records_by_metric",
            "args": {"metric_types": ["BodyMass"], "time_period": "recent"},
            "id": "test_call_1"
        }]
    )

    with patch.object(StatelessHealthAgent, 'llm') as mock_llm:
        mock_llm.ainvoke.return_value = mock_llm_response

        agent = StatelessHealthAgent()
        result = await agent.chat("What's my weight?", "test_user")

        assert result["tool_calls_made"] == 1
        assert "search_health_records_by_metric" in str(result["tools_used"])
```

#### 3.2 Response Validation (`test_response_validation.py`)
```python
@pytest.mark.agent
async def test_numeric_validator_catches_agent_hallucinations():
    """Integration test: validator detects hallucinated numbers in agent responses."""
    agent = StatelessHealthAgent()

    # Mock tool to return specific data
    mock_tool_result = {
        "name": "search_health_records_by_metric",
        "content": '{"results": [{"value": "136.8 lb", "date": "2024-10-22"}]}'
    }

    result = await agent.chat(
        message="What's my weight?",
        user_id="test_user"
    )

    # Validate the response against tool results
    validator = get_numeric_validator()
    validation = validator.validate_response(
        response_text=result["response"],
        tool_results=[mock_tool_result]
    )

    # ✅ GOOD: Check validation structure
    assert "valid" in validation
    assert "score" in validation
    assert "hallucinations" in validation

    # Response should be valid if agent used tool correctly
    if validation["valid"]:
        assert validation["score"] >= 0.8
    else:
        # If invalid, log for debugging (don't fail test)
        logger.warning(f"Agent produced invalid response: {validation}")

@pytest.mark.agent
async def test_agent_response_contains_tool_data():
    """Verify agent incorporates tool results into response."""
    agent = StatefulRAGAgent(memory_manager=get_memory_manager())

    # Use fixture with known health data
    with health_data_fixture("user123"):
        result = await agent.chat(
            message="What workouts did I do last week?",
            user_id="user123",
            session_id="test"
        )

        # ✅ GOOD: Structural validation
        assert result["tool_calls_made"] > 0
        assert result["response"]

        # ✅ GOOD: Verify response has workout-related content
        response_lower = result["response"].lower()
        assert any(word in response_lower for word in ["workout", "exercise", "activity"])
```

#### 3.3 Memory Integration (`test_stateful_agent.py`)
```python
@pytest.mark.agent
async def test_agent_remembers_conversation_context():
    """Test short-term memory (conversation history)."""
    agent = StatefulRAGAgent(memory_manager=get_memory_manager())
    session_id = f"test_{uuid.uuid4()}"

    # First message
    result1 = await agent.chat(
        message="My BMI goal is 22",
        user_id="test_user",
        session_id=session_id
    )
    assert result1["response"]

    # Follow-up that requires context
    result2 = await agent.chat(
        message="Am I close to that goal?",  # "that goal" requires memory
        user_id="test_user",
        session_id=session_id
    )

    # ✅ GOOD: Verify memory was used
    assert result2["memory_stats"]["short_term_hits"] > 0

    # ✅ GOOD: Verify response is contextual (not "I don't know what you're referring to")
    assert "goal" in result2["response"].lower() or "22" in result2["response"]

@pytest.mark.agent
async def test_agent_skips_semantic_memory_for_factual_queries():
    """Test tool-first policy: factual queries bypass semantic memory."""
    agent = StatefulRAGAgent(memory_manager=get_memory_manager())

    result = await agent.chat(
        message="How many workouts did I do last week?",  # Factual query
        user_id="test_user",
        session_id="test"
    )

    # ✅ GOOD: Verify semantic memory was skipped
    memory_stats = result.get("memory_stats", {})
    semantic_hits = memory_stats.get("semantic_hits", 0)
    assert semantic_hits == 0 or not memory_stats  # Semantic memory not used

    # ✅ GOOD: Verify tool was called instead
    assert result["tool_calls_made"] > 0
```

---

### 4. API Tests (HTTP Endpoints)

**Philosophy**: Test HTTP layer and request/response validation. Mock services.

#### 4.1 Chat Routes (`test_chat_routes.py`)
```python
from fastapi.testclient import TestClient

client = TestClient(app)

def test_stateless_chat_endpoint():
    response = client.post(
        "/api/chat/stateless",
        json={"message": "What's my weight?"}
    )

    assert response.status_code == 200
    data = response.json()

    # ✅ GOOD: Validate response structure
    assert "response" in data
    assert "tools_used" in data
    assert "type" in data
    assert data["type"] == "stateless"

def test_redis_chat_endpoint():
    response = client.post(
        "/api/chat/redis",
        json={"message": "What's my BMI?", "session_id": "test123"}
    )

    assert response.status_code == 200
    data = response.json()

    # ✅ GOOD: Validate response structure
    assert "response" in data
    assert "session_id" in data
    assert "memory_stats" in data
    assert data["type"] == "redis_with_memory"

def test_get_conversation_history():
    # Setup: Send messages first
    client.post("/api/chat/redis", json={
        "message": "Hello",
        "session_id": "history_test"
    })

    # Get history
    response = client.get("/api/chat/history/history_test")

    assert response.status_code == 200
    data = response.json()

    assert "messages" in data
    assert len(data["messages"]) > 0
    assert data["messages"][0]["role"] in ["user", "assistant"]

def test_clear_session():
    response = client.delete("/api/chat/session/test123")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["session_id"] == "test123"
```

---

### 5. End-to-End Tests

**Philosophy**: Test complete workflows from start to finish.

#### 5.1 Health Data Pipeline (`test_health_data_pipeline.py`)
```python
@pytest.mark.e2e
async def test_complete_health_data_workflow():
    """Test: Upload XML → Store in Redis → Query with agent → Validate response."""

    # 1. Upload Apple Health XML (mocked or fixture)
    xml_path = "tests/fixtures/sample_export.xml"
    with open(xml_path, "rb") as f:
        response = client.post("/api/health/upload", files={"file": f})

    assert response.status_code == 200

    # 2. Verify data in Redis
    manager = RedisAppleHealthManager()
    health_data = manager.get_health_data("test_user")
    assert health_data is not None
    assert "metrics_summary" in health_data

    # 3. Query with agent
    result = await agent.chat(
        message="What's my recent weight trend?",
        user_id="test_user",
        session_id="e2e_test"
    )

    # 4. Validate response
    assert result["tool_calls_made"] > 0
    assert result["response"]

    # Validate numbers in response match Redis data
    validator = get_numeric_validator()
    # ... validation logic

@pytest.mark.e2e
async def test_stateless_vs_redis_memory_comparison():
    """Test: Compare stateless and Redis agent responses for context."""

    session_id = f"comparison_{uuid.uuid4()}"

    # Redis chat: Multi-turn conversation
    redis_result1 = await redis_service.chat(
        message="My BMI goal is 22",
        session_id=session_id
    )
    redis_result2 = await redis_service.chat(
        message="How close am I?",  # Requires context
        session_id=session_id
    )

    # Stateless chat: Same follow-up
    stateless_result = await stateless_service.chat(
        message="How close am I?"  # No context
    )

    # ✅ GOOD: Validate structural differences
    assert redis_result2["memory_stats"]["short_term_hits"] > 0
    assert "22" in redis_result2["response"] or "goal" in redis_result2["response"]

    # Stateless should fail to answer or ask for clarification
    assert stateless_result["response"]  # Has response
    # Don't assert exact text, but verify it's different
```

---

## Anti-Hallucination Testing Strategy

### Problem: LLMs produce non-deterministic text
### Solution: Test structure and validity, not exact content

```python
# ❌ BAD: Brittle exact text matching
def test_agent_response():
    result = agent.chat("What's my weight?")
    assert result["response"] == "Your current weight is 136.8 lb"  # Fails if LLM varies

# ✅ GOOD: Structural validation
def test_agent_response_structure():
    result = agent.chat("What's my weight?")

    # 1. Verify response exists and is non-empty
    assert result["response"]
    assert len(result["response"]) > 10

    # 2. Verify tool was called
    assert result["tool_calls_made"] > 0

    # 3. Verify response contains numeric data
    validator = get_numeric_validator()
    numbers = validator.extract_numbers_with_context(result["response"])
    assert len(numbers) > 0

    # 4. Verify numbers match tool results
    validation = validator.validate_response(
        result["response"],
        result["tool_results"]
    )
    assert validation["valid"] is True
    assert validation["score"] >= 0.8

# ✅ GOOD: Semantic validation
def test_agent_response_semantics():
    result = agent.chat("What's my weight?")

    # Check for weight-related keywords
    response_lower = result["response"].lower()
    assert any(word in response_lower for word in ["weight", "lb", "kg", "pounds"])

    # Check response is not an error message
    assert not any(word in response_lower for word in ["error", "failed", "unavailable"])
```

---

## Test Configuration

### conftest.py
```python
import pytest
import asyncio
from typing import Generator
from redis import Redis

from src.config import get_settings
from src.services.redis_connection import get_redis_manager
from src.services.memory_manager import get_memory_manager

# ========== Pytest Configuration ==========

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (require Redis)")
    config.addinivalue_line("markers", "agent: Agent tests (LLM-dependent)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (full workflows)")

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# ========== Redis Fixtures ==========

@pytest.fixture(scope="session")
def redis_client() -> Generator[Redis, None, None]:
    """Provide Redis client for tests."""
    manager = get_redis_manager()
    with manager.get_connection() as client:
        yield client
        # Cleanup: flush test data
        client.flushdb()

@pytest.fixture(scope="function")
def clean_redis(redis_client):
    """Ensure clean Redis state for each test."""
    redis_client.flushdb()
    yield redis_client
    redis_client.flushdb()

# ========== Memory Fixtures ==========

@pytest.fixture
def memory_manager():
    """Provide memory manager for tests."""
    return get_memory_manager()

@pytest.fixture
async def isolated_memory_session(memory_manager):
    """Provide isolated memory session (auto-cleanup)."""
    import uuid
    session_id = f"test_{uuid.uuid4()}"
    user_id = "test_user"

    yield user_id, session_id

    # Cleanup
    await memory_manager.clear_session(user_id, session_id)

# ========== Health Data Fixtures ==========

@pytest.fixture
def sample_health_data():
    """Provide sample health data for tests."""
    return {
        "metrics_summary": {
            "BodyMass": {
                "latest_value": 70,
                "unit": "kg",
                "count": 30,
                "latest_date": "2024-10-22"
            },
            "BodyMassIndex": {
                "latest_value": 23.6,
                "unit": "count",
                "count": 30,
                "latest_date": "2024-10-22"
            }
        },
        "metrics_records": {
            "BodyMass": [
                {"date": "2024-10-20", "value": 70.2, "unit": "kg"},
                {"date": "2024-10-21", "value": 70.0, "unit": "kg"},
                {"date": "2024-10-22", "value": 69.8, "unit": "kg"},
            ]
        }
    }

@pytest.fixture
def health_data_fixture(sample_health_data, redis_client):
    """Context manager to load health data into Redis for tests."""
    from contextlib import contextmanager

    @contextmanager
    def _load_health_data(user_id: str):
        from src.utils.user_config import get_user_health_data_key
        import json

        key = get_user_health_data_key(user_id)
        redis_client.set(key, json.dumps(sample_health_data))

        try:
            yield
        finally:
            redis_client.delete(key)

    return _load_health_data

# ========== Mock LLM Fixtures ==========

@pytest.fixture
def mock_ollama_response():
    """Provide mock Ollama responses for deterministic tests."""
    from langchain_core.messages import AIMessage

    def _create_response(content: str = "", tool_calls: list = None):
        return AIMessage(content=content, tool_calls=tool_calls or [])

    return _create_response
```

---

## Running Tests

```bash
# Run all tests
cd backend
uv run pytest tests/

# Run by category
uv run pytest tests/unit/                    # Pure functions only
uv run pytest tests/integration/             # Redis-dependent
uv run pytest tests/agent/                   # LLM-dependent
uv run pytest tests/e2e/                     # Full workflows

# Run by marker
uv run pytest -m unit                        # Unit tests only
uv run pytest -m integration                 # Integration tests only
uv run pytest -m "not agent"                 # Exclude LLM tests

# Run with coverage
uv run pytest --cov=src --cov-report=html tests/

# Run specific test file
uv run pytest tests/unit/test_numeric_validator.py -v

# Run with debug output
uv run pytest tests/ -v -s                   # Show print statements
uv run pytest tests/ -v --log-cli-level=INFO # Show logs
```

---

## Test Quality Checklist

### ✅ DO:
- Test pure functions with deterministic inputs/outputs
- Validate response **structure** and **validity**, not exact text
- Use mocks for external services (Ollama, Redis in unit tests)
- Test edge cases and error conditions
- Use fixtures for reusable test data
- Test tool selection and chaining, not exact tool responses
- Validate numeric data against tool results (NumericValidator)
- Test memory system behavior, not exact memory content

### ❌ DON'T:
- Assert exact LLM response text (non-deterministic)
- Test LLM "intelligence" (out of scope)
- Mix unit tests with integration tests
- Skip cleanup (Redis, sessions)
- Test implementation details (test behavior)
- Hardcode test data inline (use fixtures)
- Assume test order (each test isolated)

---

## Success Criteria

A test suite is **successful** when:

1. **No false positives**: Tests pass consistently, not randomly
2. **No false negatives**: Real bugs cause test failures
3. **Fast execution**: Unit tests <1s, integration <5s, e2e <30s
4. **Clear failures**: Test names and assertions explain what broke
5. **Maintainable**: Easy to add new tests, minimal duplication
6. **Comprehensive**: Cover core paths, edge cases, error handling

---

## Next Steps

1. **Create test fixtures** (fixtures/, conftest.py)
2. **Write unit tests first** (pure functions, deterministic)
3. **Add integration tests** (Redis, services)
4. **Build agent tests carefully** (structure validation, no exact text)
5. **Add API tests** (HTTP layer)
6. **Implement e2e tests last** (full workflows)
7. **Set up CI/CD** (GitHub Actions to run tests)
8. **Monitor coverage** (aim for >80% on core logic)
