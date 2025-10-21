# Tests Directory

This directory contains all tests for the Redis Wellness demo project.

## Directory Structure

```
tests/
├── README.md                    # This file
├── test_redis_chat_api.py       # Integration tests for Redis chat API
├── test_with_data.py            # Integration tests with loaded data
└── unit/                        # Unit tests (require backend dependencies)
    ├── test_api.py
    ├── test_health_parsing.py
    ├── test_insights.py
    ├── test_math_tools.py
    ├── test_parsing_direct.py
    ├── test_redis_chat_rag.py
    ├── test_redis_data.py
    ├── test_stateless_isolation.py
    └── test_tool_loading.py
```

## Test Types

### Integration Tests (Recommended)
**Location**: `/tests/*.py` (root level)

These tests verify the backend API endpoints by making HTTP requests to the running service. They do NOT require backend dependencies installed locally.

- **`test_redis_chat_api.py`** - Redis chat API with RAG and semantic memory
  - Exercise query with tool calling
  - Follow-up questions with conversation history
  - Memory statistics verification
  - Session management

- **`test_with_data.py`** - Tests requiring loaded health data
  - Exercise queries with actual health records
  - Data retrieval and aggregation
  - Populates Redis with test data

**Run these tests**: `python3 -m pytest tests/ --ignore=tests/unit`

### Unit Tests (Require Docker)
**Location**: `/tests/unit/*.py`

These tests import backend code directly and require all backend dependencies (LangGraph, RedisVL, etc.) to be installed. They are best run inside the Docker container.

- **`test_api.py`** - FastAPI endpoint tests
- **`test_health_parsing.py`** - Apple Health XML parsing
- **`test_insights.py`** - Health insight generation
- **`test_parsing_direct.py`** - Direct parsing logic
- **`test_redis_data.py`** - Redis data operations
- **`test_stateless_isolation.py`** - Stateless chat verification
- **`test_redis_chat_rag.py`** - RAG agent tests
- **`test_math_tools.py`** - Math utility tests
- **`test_tool_loading.py`** - Verify agent tools are loaded

**Run these tests**: See "Running Unit Tests in Docker" below

## Prerequisites

### Running Backend Services
All integration tests require the backend services to be running:

```bash
# Start all services
./start.sh

# Or manually
docker-compose up --build
```

Verify services are healthy:
```bash
curl http://localhost:8000/api/health/check
```

### Required Services
- **Backend API**: http://localhost:8000
- **Redis**: localhost:6379
- **Ollama**: localhost:11434
  - Model: `qwen2.5:7b`
  - Embeddings: `mxbai-embed-large`

### Load Health Data (Optional)
Some tests work better with real health data loaded:

```bash
# Use utility scripts in /scripts directory
python3 scripts/load_health_data.py

# Or via API
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@export.xml"
```

## Running Tests

### Run Integration Tests (Recommended)
```bash
# From project root - run only integration tests
python3 -m pytest tests/ --ignore=tests/unit

# With verbose output
python3 -m pytest tests/ --ignore=tests/unit -v

# With print statements
python3 -m pytest tests/ --ignore=tests/unit -s
```

### Run Specific Test File
```bash
python3 -m pytest tests/test_redis_chat_api.py

# Run specific test function
python3 -m pytest tests/test_redis_chat_api.py::test_redis_chat_exercise_query
```

### Run by Pattern
```bash
# Run all tests with "redis" in the name
python3 -m pytest tests/ --ignore=tests/unit -k redis

# Run all tests with "chat" in the name
python3 -m pytest tests/ --ignore=tests/unit -k chat
```

### Running Unit Tests in Docker
Unit tests require backend dependencies and should be run inside the Docker container:

```bash
# Enter the backend container
docker-compose exec backend bash

# Inside container, run unit tests
cd /app
pytest tests/unit/ -v

# Or run specific unit test
pytest tests/unit/test_health_parsing.py -v
```

**Note**: Unit tests may have import errors or configuration issues when run outside Docker. Use integration tests for CI/CD and local development.

## Expected Output

### Successful Integration Test Run
```
======================== test session starts =========================
collected 4 items

tests/test_redis_chat_api.py ...                               [ 75%]
tests/test_with_data.py .                                      [100%]

======================== 4 passed in 8.92s ==========================
```

### Common Test Output
Tests include detailed logging:
```
================================================================================
TEST: Redis Chat Exercise Query via API
================================================================================
Session ID: test_session_a1b2c3d4_1234567890
Base URL: http://localhost:8000

[1/5] Checking backend health...
✓ Backend healthy: Redis=True, Ollama=True

[2/5] Sending exercise query...
Response status: 200

[3/5] Verifying response structure...
✓ Has field: response
✓ Has field: session_id
✓ Has field: tools_used
✓ Has field: tool_calls_made
✓ Has field: memory_stats

[4/5] Verifying tool usage...
Tools called: 1
Tool names: ['search_workouts_and_activity']
✓ Uses exercise-related tools

[5/5] Verifying response quality...

Query: when was the last time I exercised
Response: Based on your health records, your last exercise session was...

Memory stats: {
  "short_term_available": false,
  "semantic_hits": 0,
  "long_term_available": false
}

================================================================================
✓ TEST PASSED: Redis Chat Exercise Query
================================================================================
```

## Test Details

### `test_redis_chat_api.py`

**Purpose**: Verify Redis chat with RAG and tool calling

**Test Functions**:
1. `test_redis_chat_exercise_query()`
   - Sends: "when was the last time I exercised"
   - Verifies: Tool calling works (agent calls search_workouts_and_activity)
   - Checks: Response contains actual data from Redis health records
   - Validates: Tool usage metadata and memory statistics

2. `test_redis_chat_follow_up_with_memory()`
   - First query: "what is my latest weight"
   - Follow-up: "is that good?"
   - Verifies: Agent understands context from conversation history
   - Note: Semantic memory is currently disabled, but message history works

3. `test_conversation_history()`
   - Verifies: Conversation history is properly stored in Redis
   - Checks: Message structure (role, content fields)
   - Validates: Session persistence

**Expected Behavior**:
- All tool calls should complete successfully
- Responses should reference actual health data
- Follow-up questions should maintain context
- Memory stats show conversation history (semantic memory disabled)

### `test_with_data.py`

**Purpose**: Test queries that require actual health data

**Requirements**:
- Health data must be loaded via `/scripts/load_health_data.py`
- Or use sample data endpoint

### `test_stateless_isolation.py`

**Purpose**: Verify stateless chat has no memory

**Expected Behavior**:
- Stateless chat should NOT remember previous messages
- Each request is independent
- No session persistence

## Current Implementation Notes

### Semantic Memory Status
**Currently Disabled** - The semantic memory system (long-term memory with vector search) is commented out in the agent implementation.

**What still works**:
- Conversation history (message-based context)
- Short-term context through LangGraph state
- Tool calling and RAG

**Tests reflect this**:
- `memory_stats.short_term_available` will be `false`
- `memory_stats.semantic_hits` will be `0`
- Context understanding works through conversation history

### Tool Calling
The agent uses QueryClassifier to route queries to appropriate tools:
- **Aggregation queries** → `aggregate_metrics`
- **Retrieval queries** → `search_health_records_by_metric`
- **Workout queries** → `search_workouts_and_activity`

Tests verify the correct tool is selected based on query intent.

## Troubleshooting

### Backend Not Running
```
Error: Connection refused on http://localhost:8000
```
**Fix**: Start backend services with `./start.sh`

### Ollama Not Responding
```
Error: Ollama not available at http://localhost:11434
```
**Fix**:
```bash
# Start Ollama
ollama serve

# Verify models are installed
ollama list
ollama pull qwen2.5:7b
ollama pull mxbai-embed-large
```

### Redis Connection Failed
```
Error: Redis connection failed
```
**Fix**:
```bash
# Check Redis is running
docker ps | grep redis

# Restart services
docker-compose restart redis
```

### Test Timeouts
Some queries can take 30-60 seconds due to:
- LLM inference time
- Tool execution
- Vector search (if enabled)

**Current timeout**: 60 seconds per request

### No Health Data
```
Response: "I don't have any health records available"
```
**Fix**: Load health data first:
```bash
python3 scripts/load_health_data.py
```

## Adding New Tests

### Template for Integration Tests
```python
def test_new_feature():
    """Test description."""
    base_url = "http://localhost:8000"
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"

    try:
        # Make API request
        response = requests.post(
            f"{base_url}/api/chat/redis",
            json={"message": "test query", "session_id": session_id},
            timeout=60
        )

        # Verify response
        assert response.status_code == 200
        result = response.json()
        assert "response" in result

    finally:
        # Cleanup
        requests.delete(f"{base_url}/api/chat/session/{session_id}")
```

### Best Practices
- Use unique session IDs with timestamps
- Always cleanup sessions in `finally` block
- Set appropriate timeouts (60s for LLM queries)
- Verify both response structure AND content
- Check tool usage metadata for debugging

## CI/CD Integration

To run tests in CI/CD:

```yaml
# Example GitHub Actions
- name: Start services
  run: docker-compose up -d

- name: Wait for health
  run: |
    timeout 60 bash -c 'until curl -f http://localhost:8000/api/health/check; do sleep 2; done'

- name: Run integration tests
  run: python3 -m pytest tests/ --ignore=tests/unit -v

- name: Run unit tests (in Docker)
  run: docker-compose exec -T backend pytest tests/unit/ -v
```

## Test Coverage

Current coverage focuses on:
- HTTP API endpoints
- Tool calling accuracy
- Memory/context handling
- Session management
- Health data parsing

**Not yet covered**:
- Performance/load testing
- Error handling edge cases
- Concurrent session handling
- Vector search accuracy (semantic memory disabled)

---

**Last Updated**: 2025-10-20
**Status**: All integration tests passing (4/4)

## Summary

- **Integration tests**: 4 tests, all passing, no warnings
- **Unit tests**: 9 tests, require Docker to run
- **Recommended**: Use integration tests for development and CI/CD
- **Test organization**: Integration tests in `/tests`, unit tests in `/tests/unit`
