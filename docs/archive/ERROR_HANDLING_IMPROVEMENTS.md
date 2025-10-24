# Error Handling Improvements Plan

## Executive Summary

Your backend has **excellent error handling infrastructure** but the **new CoALA memory services** need to adopt it consistently. The core exception system is production-ready—we just need to use it everywhere.

## Priority 1: Critical Bug Fixes

### 1.1 redis_chat.py - Fix Undefined Reference (Line 221)

**File**: `backend/src/services/redis_chat.py`
**Line**: 221
**Issue**: References `self.memory_manager` (doesn't exist)

```python
# ❌ Current (broken):
return await self.memory_manager.clear_session_memory(session_id)

# ✅ Fix:
return await self.memory_coordinator.clear_session_memories(session_id)
```

## Priority 2: Adopt Structured Exceptions in Memory Services

Your new memory services use logging + return False/None instead of raising structured exceptions. This bypasses your excellent error handling system.

### 2.1 embedding_service.py

**Current pattern**:
```python
except Exception as e:
    logger.error(f"Embedding generation failed: {e}", exc_info=True)
    raise LLMServiceError(reason=f"Failed to generate embedding: {str(e)}") from e
```

**Status**: ✅ Already correct! Uses structured exceptions.

### 2.2 episodic_memory_manager.py

**Methods to fix**: `store_episodic_event`, `retrieve_episodic_memories`, `clear_episodic_memories`

**Current pattern**:
```python
except Exception as e:
    logger.error(f"Episodic memory storage failed: {e}")
    return False  # ❌ Silent failure
```

**Should be**:
```python
except Exception as e:
    logger.error(f"Episodic memory storage failed: {e}", exc_info=True)
    raise MemoryRetrievalError(
        memory_type="episodic",
        reason=str(e)
    ) from e
```

### 2.3 semantic_memory_manager.py

**Methods to fix**: `store_semantic_fact`, `retrieve_semantic_knowledge`, `populate_default_health_knowledge`, `clear_semantic_knowledge`

**Same pattern as episodic_memory_manager.py**

### 2.4 procedural_memory_manager.py

**Methods to fix**: `record_procedure`, `suggest_procedure`, `get_user_procedures`, `get_procedure_stats`, `clear_procedures`

**Same pattern as episodic_memory_manager.py**

### 2.5 memory_coordinator.py

**Methods to fix**: All methods that catch generic `Exception`

**Current pattern**:
```python
except Exception as e:
    logger.warning(f"Short-term retrieval failed: {e}")
    # Non-critical: continue without short-term
```

**Note**: Memory coordinator uses "graceful degradation" pattern (warning + continue). This is **acceptable** for non-critical retrieval but should use structured exceptions for critical operations.

**Keep graceful degradation for**:
- Short-term retrieval (line 139)
- Episodic retrieval (line 154)
- Semantic retrieval (line 169)
- Procedural retrieval (line 193)

**Use structured exceptions for**:
- Storage failures (line 242-259)
- Stats retrieval (line 427)
- Session clearing (line 451)
- User memory clearing (line 485-506)

## Priority 3: Standardize Apple Health Tool Error Responses

### 3.1 Current Inconsistency

Some tools return error dicts:
```python
return {"error": "No health data found", "records": []}
```

Others raise structured exceptions:
```python
raise HealthDataNotFoundError(user_id, metric_types=metric_types)
```

### 3.2 Recommended Approach

**For LangChain tools** (apple_health/query_tools/*), **keep dict-based errors** because:
- LangChain tools need to return serializable dicts
- LLM can read error messages from tool results
- Exceptions would break tool calling loop

**Keep current pattern**:
```python
try:
    # Tool logic
    return {"results": [...], "total": 42}
except Exception as e:
    logger.error(f"Tool failed: {e}", exc_info=True)
    return {
        "error": f"Failed to search: {str(e)}",
        "error_type": type(e).__name__,
        "results": []
    }
```

**This is correct for tools!** The agent layer will handle tool errors gracefully.

## Priority 4: API Layer Error Handling

### 4.1 chat_routes.py

**Current**: Routes don't explicitly catch `WellnessError` exceptions.

**Status**: ✅ **Actually fine!** Your `main.py` already registers global exception handlers:
```python
from utils.api_errors import setup_exception_handlers
setup_exception_handlers(app)
```

**No changes needed** - exceptions will be caught by middleware.

### 4.2 system_routes.py

**Health check endpoints**: Use basic try/except (lines 56-62, 65-76).

**Status**: ✅ **Acceptable for health checks** - they should never fail loudly.

## Implementation Checklist

### Critical (Do First)
- [ ] Fix `redis_chat.py` line 221 bug
- [ ] Test memory coordinator graceful degradation
- [ ] Add structured exceptions to episodic_memory_manager.py
- [ ] Add structured exceptions to semantic_memory_manager.py
- [ ] Add structured exceptions to procedural_memory_manager.py

### Important (Do Next)
- [ ] Review memory_coordinator.py exception strategy (graceful vs strict)
- [ ] Add integration tests for error scenarios
- [ ] Document error handling patterns in WARP.md

### Nice to Have
- [ ] Add circuit breaker for Ollama/Redis
- [ ] Add retry logic for transient failures
- [ ] Add Sentry/error tracking integration

## Code Quality Notes

### ✅ What's Already Great

1. **Three-tier exception hierarchy** (`utils/exceptions.py`)
2. **Correlation ID tracking** for debugging
3. **Automatic HTTP status code mapping**
4. **Sensitive data sanitization** (user IDs masked in logs)
5. **Structured error responses** with consistent schema
6. **Tool-level validation decorators** (`utils/base.py`)

### ⚠️ Patterns to Adopt

1. **Always use `from e` for exception chaining**:
   ```python
   raise NewException(...) from e  # ✅ Preserves stack trace
   ```

2. **Use `exc_info=True` for error logs**:
   ```python
   logger.error("Failed", exc_info=True)  # ✅ Includes traceback
   ```

3. **Sanitize user data in exceptions**:
   ```python
   from ..utils.exceptions import sanitize_user_id
   raise MemoryRetrievalError(
       details={"user_id": sanitize_user_id(user_id)}
   )
   ```

## Testing Strategy

### Unit Tests Needed
```python
# Test memory service error handling
async def test_episodic_storage_redis_failure():
    """Verify MemoryRetrievalError is raised on Redis failure."""
    with patch("redis.Redis.hset", side_effect=ConnectionError()):
        with pytest.raises(MemoryRetrievalError):
            await manager.store_episodic_event(...)

# Test API error responses
async def test_chat_endpoint_returns_503_on_redis_failure():
    """Verify proper HTTP status on infrastructure failure."""
    response = await client.post("/api/chat/redis", json={...})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "REDIS_CONNECTION_FAILED"
```

### Integration Tests Needed
```python
# Test graceful degradation
async def test_memory_coordinator_graceful_degradation():
    """Verify agent works even if episodic memory fails."""
    # Simulate episodic memory failure
    # Verify response still works (no episodic context)
    # Verify warning logged

# Test correlation ID propagation
async def test_correlation_id_in_error_chain():
    """Verify correlation ID flows through all layers."""
    response = await client.post("/api/chat/redis", json={...})
    correlation_id = response.headers["X-Correlation-ID"]
    # Verify same ID appears in all logs for this request
```

## Performance Considerations

### Current Approach
- Exceptions are expensive in Python (~1ms overhead)
- Your graceful degradation pattern is good for non-critical paths

### Recommendations
1. **Keep graceful degradation** for memory retrieval (optional features)
2. **Use strict exceptions** for critical paths (data storage, API responses)
3. **Cache common errors** (e.g., "no health data found") to avoid re-raising

## Monitoring & Observability

### Add These Metrics
```python
# In memory services
error_counter = Counter("memory_errors_total", ["memory_type", "operation"])

try:
    # Memory operation
except Exception as e:
    error_counter.labels(memory_type="episodic", operation="store").inc()
    raise
```

### Logging Best Practices
```python
# ✅ Good: Structured logging with context
logger.error(
    "Episodic memory storage failed",
    extra={
        "user_id": sanitize_user_id(user_id),
        "event_type": event_type,
        "correlation_id": correlation_id,
    },
    exc_info=True
)

# ❌ Bad: Generic error message
logger.error(f"Error: {e}")
```

## Summary

Your error handling infrastructure is **production-ready**. The main issue is that your new CoALA memory services (added recently) haven't adopted it yet. Fix the critical bug in `redis_chat.py` and update the memory services to raise structured exceptions instead of returning False/None.

Keep the dict-based error returns in LangChain tools—that's correct for tool calling.
