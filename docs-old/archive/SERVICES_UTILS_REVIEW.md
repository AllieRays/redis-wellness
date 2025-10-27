# Services Review: Utils Usage Analysis

**Date**: 2025-10-24
**Question**: Are we using utils everywhere we should? Is there code that should be replaced by a util?

---

## Executive Summary

✅ **Good News**: Services are mostly using utils correctly
⚠️ **Opportunities**: 3-4 patterns that could be extracted to utils

---

## Services Inventory (13 files)

1. `embedding_cache.py` - Embedding caching service
2. `embedding_service.py` - Centralized embedding generation
3. `episodic_memory_manager.py` - User events/preferences memory
4. `memory_coordinator.py` - Orchestrates all 4 memory types
5. `procedural_memory_manager.py` - Learned tool sequences
6. `redis_apple_health_manager.py` - Health data CRUD
7. `redis_chat.py` - Stateful chat service
8. `redis_connection.py` - Connection pool manager
9. `redis_workout_indexer.py` - Workout data indexing
10. `semantic_memory_manager.py` - General health knowledge
11. `short_term_memory_manager.py` - Conversation history
12. `stateless_chat.py` - Stateless chat service

---

## Current Utils Usage: ✅ GOOD

### Services ARE using utils correctly:

1. **Date/Time Handling** ✅
   - All services use `datetime.now(UTC).isoformat()` correctly
   - No manual timezone handling
   - Consistent ISO 8601 format

2. **Error Handling** ✅
   - Services use custom exceptions from `utils/exceptions.py`:
     - `HealthDataNotFoundError`
     - `ToolExecutionError`
     - `MemoryRetrievalError`
     - `InfrastructureError`
     - `LLMServiceError`

3. **Connection Management** ✅
   - All services use `RedisConnectionManager` from `redis_connection.py`
   - No raw Redis connections

---

## Opportunities for Improvement

### 1. **Extract Hash Generation Util** 🟡 OPTIONAL

**Current Pattern (Duplicated 2x):**

```python
# embedding_cache.py line 88
query_hash = hashlib.md5(query.encode("utf-8")).hexdigest()

# procedural_memory_manager.py line 68
return hashlib.md5(normalized.encode()).hexdigest()[:8]
```

**Recommendation**: Create `utils/hash_utils.py`

```python
# utils/hash_utils.py
import hashlib

def hash_text(text: str, length: int | None = None) -> str:
    """
    Generate MD5 hash of text.

    Args:
        text: Text to hash
        length: Optional length to truncate hash (e.g., 8 for short keys)

    Returns:
        Hexadecimal hash string

    Examples:
        hash_text("hello world") → "5eb63bbbe01eeed093cb22bb8f5acdc3"  # pragma: allowlist secret
        hash_text("hello world", length=8) → "5eb63bbb"
    """
    hash_value = hashlib.md5(text.encode("utf-8")).hexdigest()
    return hash_value[:length] if length else hash_value
```

**Impact**: Low priority - only 2 occurrences, pattern is simple

---

### 2. **Extract TTL Calculation Util** 🟡 OPTIONAL

**Current Pattern (Duplicated 3x):**

```python
# redis_apple_health_manager.py line 53
ttl_seconds = ttl_days * 24 * 60 * 60

# redis_workout_indexer.py line 27
self.ttl_seconds = 210 * 24 * 60 * 60

# redis_workout_indexer.py line 126
"ttl_days": self.ttl_seconds // (24 * 60 * 60)
```

**Recommendation**: Create `utils/ttl_utils.py`

```python
# utils/ttl_utils.py
SECONDS_PER_DAY = 86400  # 24 * 60 * 60

def days_to_seconds(days: int) -> int:
    """
    Convert days to seconds.

    Args:
        days: Number of days

    Returns:
        Equivalent seconds

    Examples:
        days_to_seconds(7) → 604800
        days_to_seconds(210) → 18144000  # 7 months
    """
    return days * SECONDS_PER_DAY

def seconds_to_days(seconds: int) -> int:
    """
    Convert seconds to days.

    Args:
        seconds: Number of seconds

    Returns:
        Equivalent days (rounded down)

    Examples:
        seconds_to_days(604800) → 7
        seconds_to_days(18144000) → 210  # 7 months
    """
    return seconds // SECONDS_PER_DAY
```

**Impact**: Low priority - magic number is clear enough

---

### 3. **JSON Handling** ✅ ACCEPTABLE

**Current**: 20 occurrences of `json.loads()` / `json.dumps()` in services

**Analysis**: This is fine because:
- JSON operations are straightforward
- Services need to serialize/deserialize data structures
- No complex transformations needed
- Standard library usage is appropriate

**Verdict**: ✅ No util needed

---

### 4. **Error Handling Patterns** 🟢 GOOD CANDIDATE

**Current Pattern (Duplicated ~30x):**

```python
try:
    # operation
except Exception as e:
    logger.error(f"Operation failed: {e}")
    return None
```

**Problem**: Inconsistent error handling:
- Some return `None`
- Some return `False`
- Some return `{"error": str(e)}`
- Some raise exceptions

**Recommendation**: Create `utils/error_handler.py`

```python
# utils/error_handler.py
import logging
from typing import Any, Callable, TypeVar

T = TypeVar('T')

def safe_execute(
    operation: Callable[[], T],
    default: T,
    error_message: str,
    logger: logging.Logger
) -> T:
    """
    Safely execute operation with consistent error handling.

    Args:
        operation: Function to execute
        default: Value to return on error
        error_message: Error message prefix
        logger: Logger instance

    Returns:
        Operation result or default on error

    Examples:
        result = safe_execute(
            operation=lambda: redis_client.get(key),
            default=None,
            error_message="Redis GET failed",
            logger=logger
        )
    """
    try:
        return operation()
    except Exception as e:
        logger.error(f"{error_message}: {e}", exc_info=True)
        return default
```

**Impact**: Medium priority - would standardize error handling

---

### 5. **Redis Key Generation** 🟢 STRONG CANDIDATE

**Current Pattern (Duplicated 15+ times across services):**

```python
# Different key patterns across services
f"health:user:{user_id}:data"
f"health:user:{user_id}:metric:{metric_type}"
f"embedding_cache:{query_hash}"
f"procedure:{user_id}:{query_hash}"
f"episodic:{user_id}:{timestamp}"
f"semantic:{category}:{timestamp}"
f"health_chat_session:{session_id}"
f"memory:semantic:{user_id}:*"
```

**Problem**: Key format scattered across services, no centralization

**Recommendation**: Create `utils/redis_keys.py`

```python
# utils/redis_keys.py
class RedisKeys:
    """Centralized Redis key generation."""

    # Health Data Keys
    @staticmethod
    def health_data(user_id: str) -> str:
        """Main health data key."""
        return f"health:user:{user_id}:data"

    @staticmethod
    def health_metric(user_id: str, metric_type: str) -> str:
        """Health metric index key."""
        return f"health:user:{user_id}:metric:{metric_type}"

    # Memory Keys
    @staticmethod
    def chat_session(session_id: str) -> str:
        """Chat session history key."""
        return f"health_chat_session:{session_id}"

    @staticmethod
    def episodic_memory(user_id: str, timestamp: int) -> str:
        """Episodic memory key."""
        return f"episodic:{user_id}:{timestamp}"

    @staticmethod
    def procedural_memory(user_id: str, query_hash: str) -> str:
        """Procedural memory key."""
        return f"procedure:{user_id}:{query_hash}"

    @staticmethod
    def semantic_memory(category: str, timestamp: int) -> str:
        """Semantic memory key."""
        return f"semantic:{category}:{timestamp}"

    # Cache Keys
    @staticmethod
    def embedding_cache(query_hash: str) -> str:
        """Embedding cache key."""
        return f"embedding_cache:{query_hash}"

    # Pattern Keys (for scanning)
    @staticmethod
    def all_user_health(user_id: str) -> str:
        """Pattern for all user health keys."""
        return f"health:user:{user_id}:*"

    @staticmethod
    def all_semantic_for_user(user_id: str) -> str:
        """Pattern for all semantic memory keys for user."""
        return f"memory:semantic:{user_id}:*"
```

**Benefits:**
- Centralized key management
- Easy to update key formats
- Self-documenting key structure
- Prevents typos in key names
- Easy to grep for key usage

**Impact**: High priority - improves maintainability significantly

---

## Detailed Service-by-Service Analysis

### ✅ Excellent Utils Usage

**1. `redis_chat.py`**
- Uses `pronoun_resolver` util
- Uses exception utils correctly
- Clean separation of concerns

**2. `embedding_service.py`**
- Uses custom exceptions properly
- Clean error handling
- Good separation from cache

**3. `memory_coordinator.py`**
- Uses exception utils
- Uses all memory managers
- Good orchestration pattern

---

### 🟡 Could Use More Utils

**4. `embedding_cache.py`**
- Hash generation (could use hash util)
- Otherwise clean

**5. `procedural_memory_manager.py`**
- Hash generation (could use hash util)
- Otherwise clean

**6. `redis_apple_health_manager.py`**
- TTL calculations (could use ttl util)
- Redis key patterns (could use redis_keys util)
- Otherwise clean

**7. `redis_workout_indexer.py`**
- TTL calculations (could use ttl util)
- Redis key patterns (could use redis_keys util)
- Otherwise clean

---

### ✅ Service-Specific Logic (Correct)

**8. `redis_connection.py`**
- Connection pooling is service logic
- ✅ Correctly NOT a util (manages state)

**9. `episodic_memory_manager.py`**
- Redis operations are service logic
- Uses datetime utils correctly
- ✅ Appropriate as service

**10. `semantic_memory_manager.py`**
- Vector search is service logic
- Uses RedisVL correctly
- ✅ Appropriate as service

---

## Recommendations Priority

### 🔴 High Priority (Do It)

**1. Create `utils/redis_keys.py`** - **RECOMMENDED**
- **Benefit**: Centralized key management, easier refactoring
- **Effort**: 1-2 hours
- **Impact**: Affects 8+ service files
- **Risk**: Low (easy to test)

### 🟡 Medium Priority (Consider)

**2. Standardize Error Handling** - **CONSIDER**
- **Benefit**: Consistent error behavior
- **Effort**: 3-4 hours
- **Impact**: All services
- **Risk**: Medium (behavior changes)

### 🟢 Low Priority (Nice to Have)

**3. Create `utils/hash_utils.py`** - **OPTIONAL**
- **Benefit**: Minor DRY improvement
- **Effort**: 30 minutes
- **Impact**: 2 files only
- **Risk**: None

**4. Create `utils/ttl_utils.py`** - **OPTIONAL**
- **Benefit**: Clearer intent
- **Effort**: 30 minutes
- **Impact**: 3 files only
- **Risk**: None

---

## What's Already Good ✅

### Services ARE Using Utils Correctly For:

1. ✅ **Date/Time** - `datetime.now(UTC).isoformat()`
2. ✅ **Exceptions** - Custom exceptions from utils
3. ✅ **User Config** - Single-user utilities
4. ✅ **Token Management** - Token manager util
5. ✅ **Validation** - Numeric validator in agents
6. ✅ **Time Parsing** - `parse_time_period()` from utils

### No Utils Needed For:

1. ✅ **JSON Operations** - Standard library is fine
2. ✅ **Redis Operations** - Service-specific logic
3. ✅ **Connection Pooling** - Service-specific state
4. ✅ **Memory Management** - Service-specific logic

---

## Action Plan

### If You Want To Improve (Optional):

```bash
# 1. Create Redis keys util (RECOMMENDED)
cat > backend/src/utils/redis_keys.py << 'EOF'
# Content from recommendation above
EOF

# 2. Update services to use RedisKeys class
# Example: redis_apple_health_manager.py
- main_key = f"health:user:{user_id}:data"
+ main_key = RedisKeys.health_data(user_id)

# 3. Test thoroughly
cd backend && uv run pytest tests/

# 4. Commit
git add backend/src/utils/redis_keys.py
git commit -m "feat: centralize Redis key generation in utils"
```

---

## Final Verdict

✅ **Services are using utils correctly for the most part**

**Current State**: Good (7/10)
- Datetime handling: Excellent
- Exception handling: Good
- Utils usage: Mostly correct

**Potential State with Improvements**: Excellent (9/10)
- Add `redis_keys.py` util
- Standardize error handling
- Centralize key management

**No Major Issues Found** - This is clean, well-organized code that follows good patterns.

The suggested improvements are **optimizations**, not **fixes for problems**.

---

## Summary Table

| Pattern | Current State | Should Use Util? | Priority |
|---------|--------------|------------------|----------|
| Datetime handling | ✅ Correct | Already good | - |
| Exception handling | ✅ Good | Already using | - |
| JSON operations | ✅ Acceptable | No util needed | - |
| Redis connections | ✅ Good | Using manager | - |
| Hash generation | 🟡 Duplicated | Optional util | Low |
| TTL calculations | 🟡 Duplicated | Optional util | Low |
| Redis key patterns | 🟠 Scattered | **Yes, create util** | **High** |
| Error handling patterns | 🟡 Inconsistent | Consider util | Medium |

---

**Conclusion**: Your services are well-written. The only **strong recommendation** is to create `redis_keys.py` for centralized key management. Everything else is optional polish.
