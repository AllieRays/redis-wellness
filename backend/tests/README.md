# Redis Wellness Backend Tests

Comprehensive test suite with systematic validation and anti-hallucination strategies.

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures and pytest configuration
├── unit/                 # Pure functions (no external dependencies)
│   ├── test_numeric_validator.py
│   └── test_stats_utils.py
├── integration/          # Redis/service tests
│   └── test_redis_connection.py
├── agent/                # LLM-dependent agent tests
│   └── test_stateless_agent.py
├── api/                  # HTTP endpoint tests
│   └── test_chat_routes.py
└── fixtures/             # Test data and mocks
```

## Running Tests

### Prerequisites

1. **Redis must be running:**
   ```bash
   docker-compose up redis
   ```

2. **Ollama must be running (for agent tests):**
   ```bash
   ollama serve
   ollama pull qwen2.5:7b
   ```

3. **Install dependencies:**
   ```bash
   cd backend
   uv sync
   ```

### Run All Tests

```bash
cd backend
uv run pytest tests/ -v
```

### Run by Category

```bash
# Unit tests only (fast, no dependencies)
uv run pytest tests/unit/ -v

# Integration tests (require Redis)
uv run pytest tests/integration/ -v

# Agent tests (require Ollama + Redis)
uv run pytest tests/agent/ -v

# API tests (require full stack)
uv run pytest tests/api/ -v
```

### Run by Marker

```bash
# Unit tests marker
uv run pytest -m unit -v

# Integration tests marker
uv run pytest -m integration -v

# Agent tests marker (LLM-dependent)
uv run pytest -m agent -v

# Skip agent tests (for CI without Ollama)
uv run pytest -m "not agent" -v
```

### Run Specific Test File

```bash
uv run pytest tests/unit/test_numeric_validator.py -v
uv run pytest tests/integration/test_redis_connection.py -v
```

### Run with Coverage

```bash
# Generate coverage report
uv run pytest --cov=src --cov-report=html tests/

# View report
open htmlcov/index.html
```

### Debug Mode

```bash
# Show print statements
uv run pytest tests/ -v -s

# Show logs
uv run pytest tests/ -v --log-cli-level=INFO

# Run specific test with debugging
uv run pytest tests/unit/test_numeric_validator.py::TestNumericExtraction::test_extract_simple_number -v -s
```

## Test Philosophy

### ✅ DO:
- Test **structure** and **validity**, not exact LLM text
- Use fixtures for reusable test data
- Validate numbers match tool results (NumericValidator)
- Test edge cases and error conditions
- Clean up Redis state between tests

### ❌ DON'T:
- Assert exact LLM response text (non-deterministic)
- Test LLM "intelligence" (out of scope)
- Mix unit tests with integration tests
- Skip cleanup (Redis, sessions)
- Assume test execution order

## Test Markers

- `@pytest.mark.unit` - Pure functions, no external dependencies
- `@pytest.mark.integration` - Requires Redis
- `@pytest.mark.agent` - Requires Ollama (LLM-dependent)
- `@pytest.mark.e2e` - Full workflow tests

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run Unit Tests
  run: uv run pytest -m unit --maxfail=5

- name: Run Integration Tests
  run: uv run pytest -m integration --maxfail=5

# Skip agent tests in CI (no Ollama)
- name: Run Non-LLM Tests
  run: uv run pytest -m "not agent" --maxfail=5
```

## Fixtures

### Redis Fixtures
- `redis_client` - Session-scoped Redis client
- `clean_redis` - Function-scoped clean Redis state

### Memory Fixtures
- `memory_manager` - Memory manager instance
- `isolated_memory_session` - Auto-cleanup session

### Health Data Fixtures
- `sample_health_data` - Sample metrics
- `health_data_fixture` - Context manager to load data

### Mock LLM Fixtures
- `mock_ollama_response` - Create mock LLM responses
- `mock_tool_call` - Create mock tool calls

## Troubleshooting

### Redis Connection Issues

```bash
# Check Redis is running
docker ps | grep redis

# Test Redis connection
redis-cli ping
```

### Ollama Issues

```bash
# Check Ollama is running
curl http://localhost:11434

# Verify models
ollama list
```

### Import Errors

```bash
# Ensure proper Python path
cd backend
export PYTHONPATH=.
uv run pytest tests/
```

### Test Failures

1. Check test logs: `pytest -v --log-cli-level=DEBUG`
2. Verify Redis is clean: `redis-cli FLUSHDB`
3. Check Ollama models: `ollama pull qwen2.5:7b`

## Coverage Goals

- **Unit tests**: >90% coverage (pure functions)
- **Integration tests**: >80% coverage (data layer)
- **Agent tests**: >70% coverage (LLM behavior)
- **Overall**: >80% coverage

## Adding New Tests

1. Choose appropriate directory (unit/integration/agent/api)
2. Follow naming convention: `test_<module_name>.py`
3. Use appropriate markers: `@pytest.mark.unit`, etc.
4. Add fixtures to `conftest.py` if reusable
5. Follow validation patterns from existing tests

## Example Test Patterns

### Unit Test (Deterministic)
```python
@pytest.mark.unit
def test_calculate_stats():
    values = [1, 2, 3, 4, 5]
    stats = calculate_basic_stats(values)
    assert stats["average"] == 3.0
```

### Integration Test (Redis)
```python
@pytest.mark.integration
def test_redis_storage(clean_redis):
    clean_redis.set("key", "value")
    assert clean_redis.get("key") == b"value"
```

### Agent Test (Structural Validation)
```python
@pytest.mark.agent
@pytest.mark.asyncio
async def test_agent_response_structure(health_data_fixture):
    agent = StatelessHealthAgent()

    with health_data_fixture("test_user"):
        result = await agent.chat("What's my weight?", "test_user")

        # ✅ Test structure, not exact text
        assert "response" in result
        assert len(result["response"]) > 0
        assert result["tool_calls_made"] > 0
```

## Success Criteria

- ✅ All tests pass consistently
- ✅ No false positives/negatives
- ✅ Fast execution (<5s for unit tests)
- ✅ Clear failure messages
- ✅ >80% overall coverage
