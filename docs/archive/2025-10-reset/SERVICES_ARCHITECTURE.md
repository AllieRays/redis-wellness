# Services Architecture

This document provides a comprehensive overview of all backend services in the Redis Wellness application, organized by functional category.

## Overview

The services layer implements the core business logic and data operations for the Redis-powered wellness demo. The architecture follows clean separation of concerns with specialized services for memory management (CoALA framework), data storage, chat processing, and infrastructure.

**Total Services:** 13 files, ~3,710 lines of code

---

## Services by Category

### Memory System (CoALA Framework)

The application implements the [Redis CoALA framework](https://redis.io/blog/redis-ai-agent-memory-guide/) with four distinct memory types:

| Service | Purpose | Key Functions | Redis Usage | LOC |
|---------|---------|---------------|-------------|-----|
| **`episodic_memory_manager.py`** | Stores user preferences, goals, and health events (personal diary) | `store_memory()`, `retrieve_memories()`, `clear_all_memories()` | RedisVL vector index<br>`episodic:{user_id}:{event_type}:{timestamp}` | 417 |
| **`procedural_memory_manager.py`** | Learns tool sequences and execution patterns (how-to knowledge) | `record_execution()`, `get_optimal_sequence()`, `get_tool_history()` | Redis Hash (O(1) lookup)<br>`procedure:{user_id}:{query_hash}` | 414 |
| **`semantic_memory_manager.py`** | Stores general health knowledge and facts (knowledge base) | `store_knowledge()`, `retrieve_knowledge()`, `clear_all_knowledge()` | RedisVL vector index<br>`semantic:{category}:{fact_type}:{timestamp}` | 405 |
| **`short_term_memory_manager.py`** | Conversation history with token-aware trimming | `store_short_term_message()`, `get_short_term_context_token_aware()`, `clear_session()` | Redis List + RedisVL<br>`conversation:{session_id}` | 462 |
| **`memory_coordinator.py`** | Orchestrates all 4 memory types with unified interface | `get_full_context()`, `store_interaction()`, `clear_all_memories()` | Delegates to specialized managers | 420 |

**Memory Architecture Decisions:**

- **Episodic Memory**: Uses RedisVL vector search for semantic retrieval of personal events (e.g., "user prefers morning workouts")
- **Procedural Memory**: Uses Redis Hash for O(1) lookup of learned tool sequences (e.g., "for BMI queries, use these 3 tools in order")
- **Semantic Memory**: Uses RedisVL vector search for general knowledge (e.g., "normal resting heart rate is 60-100 bpm")
- **Short-Term Memory**: Uses Redis List for FIFO conversation history with token-aware trimming

**Total Memory Services:** 5 files, 2,118 lines (57% of services layer)

---

### Embedding System

| Service | Purpose | Key Functions | Redis Usage | LOC |
|---------|---------|---------------|-------------|-----|
| **`embedding_service.py`** | Centralized embedding generation using Ollama mxbai-embed-large (1024 dimensions) | `generate_embedding()`, `generate_batch()`, `_call_ollama_api()` | None (pure generation service) | 167 |
| **`embedding_cache.py`** | Caches embeddings to avoid expensive recomputation (~200ms → <1ms) | `get()`, `set()`, `get_or_generate()` | TTL-based cache (1 hour)<br>`embedding_cache:{query_hash}` | 217 |

**Performance Impact:**
- Without cache: ~200ms per embedding (Ollama inference)
- With cache hit: <1ms (Redis GET)
- Typical hit rate: 30-50% in production

**Total Embedding Services:** 2 files, 384 lines (10% of services layer)

---

### Data Layer

| Service | Purpose | Key Functions | Redis Usage | LOC |
|---------|---------|---------------|-------------|-----|
| **`redis_apple_health_manager.py`** | CRUD operations for Apple Health data storage and retrieval | `store_health_data()`, `query_health_metrics()`, `get_conversation_context()` | Main data (permanent) + indices (7-month TTL)<br>`health:user:{user_id}:data`<br>`health:user:{user_id}:metric:{type}` | 362 |
| **`redis_workout_indexer.py`** | Fast O(1) workout aggregations using Redis data structures | `index_workouts()`, `get_workout_count_by_day()`, `get_workouts_in_date_range()` | Hash (day counts) + Sorted Set (time-range)<br>`user:{user_id}:workout:days`<br>`user:{user_id}:workout:by_date` | 200+ |

**Data Architecture:**
- **Apple Health Data**: Stored permanently with temporary lookup indices (7-month TTL)
- **Workout Indexes**: Hash for O(1) day-of-week counts, Sorted Set for O(log N) date-range queries
- **Performance**: 50-100x speedup over JSON parsing for common queries

**Total Data Services:** 2 files, ~562 lines (15% of services layer)

---

### Chat Services

| Service | Purpose | Key Functions | Redis Usage | LOC |
|---------|---------|---------------|-------------|-----|
| **`redis_chat.py`** | RAG chat service with full memory, tool calling, and pronoun resolution | `chat()`, `get_conversation_history()`, `store_message()` | Uses all memory managers + stores conversation | 200+ |
| **`stateless_chat.py`** | Baseline chat with NO memory for demo comparison | `chat()`, `chat_stream()` | None (completely stateless) | 68 |

**Chat Architecture:**
- **Redis RAG Chat**: Full CoALA memory system + tool calling + pronoun resolution
- **Stateless Chat**: Pure agent + tools only (no memory, no history, no state)
- **Purpose**: Side-by-side demo comparing stateless vs memory-powered conversations

**Total Chat Services:** 2 files, ~268 lines (7% of services layer)

---

### Infrastructure

| Service | Purpose | Key Functions | Redis Usage | LOC |
|---------|---------|---------------|-------------|-----|
| **`redis_connection.py`** | Production-ready Redis connection pooling with circuit breaker pattern | `get_connection()`, `is_healthy()`, `get_pool_info()` | Connection pool management (max 20 connections) | 194 |

**Infrastructure Features:**
- Connection pooling for performance (max 20 connections, configurable)
- Circuit breaker for resilience (5 failures → OPEN for 30s)
- Automatic retry logic with timeout handling
- Health monitoring and pool statistics

**Total Infrastructure Services:** 1 file, 194 lines (5% of services layer)

---

## Service Dependencies

### Memory System Dependencies

```
memory_coordinator.py
├── episodic_memory_manager.py
│   ├── embedding_service.py
│   └── redis_connection.py
├── procedural_memory_manager.py
│   └── redis_connection.py
├── semantic_memory_manager.py
│   ├── embedding_service.py
│   └── redis_connection.py
└── short_term_memory_manager.py
    ├── embedding_service.py
    └── redis_connection.py
```

### Chat System Dependencies

```
redis_chat.py
├── short_term_memory_manager.py (legacy import)
├── redis_connection.py
├── stateful_rag_agent (agents/)
└── pronoun_resolver (utils/)

stateless_chat.py
└── stateless_health_agent (agents/)
```

### Data Layer Dependencies

```
redis_apple_health_manager.py
└── redis_connection.py

redis_workout_indexer.py
└── redis_connection.py
```

---

## Key Design Patterns

### 1. Connection Management Pattern

All services use `RedisConnectionManager` for consistent connection handling:

```python
from .redis_connection import get_redis_manager

class MyService:
    def __init__(self):
        self.redis_manager = get_redis_manager()

    def my_operation(self):
        with self.redis_manager.get_connection() as client:
            # Redis operations here
            client.set("key", "value")
```

**Benefits:**
- Connection pooling (shared across all services)
- Circuit breaker protection
- Automatic retry logic
- Consistent error handling

### 2. Single-User Mode Pattern

All memory managers enforce single-user mode using `utils.user_config.get_user_id()`:

```python
from ..utils.user_config import get_user_id

class MemoryManager:
    def store_data(self, session_id: str):
        user_id = get_user_id()  # Always returns "wellness_user"
        # Store with user_id
```

**Benefits:**
- Simplified architecture (no multi-tenant complexity)
- Clear demo focus (personal wellness data)
- Consistent user identifier across all services

### 3. UTC Datetime Pattern

All services use UTC datetime for consistency:

```python
from datetime import UTC, datetime

timestamp = datetime.now(UTC)
```

**Benefits:**
- No timezone ambiguity
- Consistent sorting and comparison
- International compatibility

### 4. Error Handling Pattern

All services use graceful degradation with structured logging:

```python
try:
    # Operation
    logger.info("Success")
    return True
except redis.RedisError as e:
    logger.error(f"Redis operation failed: {e}")
    return False
```

**Benefits:**
- Services don't crash on Redis failures
- Detailed error logging for debugging
- Predictable return types (bool, dict, or None)

---

## Redis Key Patterns

### Memory Keys

| Memory Type | Key Pattern | Example | TTL |
|-------------|-------------|---------|-----|
| Episodic | `episodic:{user_id}:{event_type}:{timestamp}` | `episodic:wellness_user:preference:1729728000` | 7 months |
| Procedural | `procedure:{user_id}:{query_hash}` | `procedure:wellness_user:a1b2c3d4` | Permanent |
| Semantic | `semantic:{category}:{fact_type}:{timestamp}` | `semantic:health:heart_rate:1729728000` | 7 months |
| Short-Term | `conversation:{session_id}` | `conversation:default` | 7 months |

### Data Keys

| Data Type | Key Pattern | Example | TTL |
|-----------|-------------|---------|-----|
| Health Data | `health:user:{user_id}:data` | `health:user:wellness_user:data` | Permanent |
| Health Metrics | `health:user:{user_id}:metric:{type}` | `health:user:wellness_user:metric:BodyMassIndex` | 7 months |
| Workout Days | `user:{user_id}:workout:days` | `user:wellness_user:workout:days` | 7 months |
| Workout Range | `user:{user_id}:workout:by_date` | `user:wellness_user:workout:by_date` | 7 months |

### Cache Keys

| Cache Type | Key Pattern | Example | TTL |
|------------|-------------|---------|-----|
| Embeddings | `embedding_cache:{query_hash}` | `embedding_cache:a1b2c3d4e5f6` | 1 hour |

---

## Performance Characteristics

### Memory Operations

| Operation | Time Complexity | Typical Latency |
|-----------|----------------|-----------------|
| Store episodic memory | O(1) | ~5-10ms |
| Retrieve episodic memories (vector search) | O(log N) | ~15-30ms |
| Store procedural pattern | O(1) | ~1-2ms |
| Get procedural sequence | O(1) | ~1-2ms |
| Store semantic knowledge | O(1) | ~5-10ms |
| Retrieve semantic knowledge (vector search) | O(log N) | ~15-30ms |
| Store short-term message | O(1) | ~1-2ms |
| Get conversation history | O(N) | ~5-10ms |

### Data Operations

| Operation | Time Complexity | Typical Latency |
|-----------|----------------|-----------------|
| Store health data | O(1) | ~5-10ms |
| Query health metric | O(1) | ~1-2ms |
| Index workouts (bulk) | O(N) | ~50-100ms (1000 workouts) |
| Get workout count by day | O(1) | ~1-2ms |
| Get workouts in date range | O(log N) | ~5-10ms |

### Embedding Operations

| Operation | Time Complexity | Typical Latency |
|-----------|----------------|-----------------|
| Generate embedding (cold) | N/A | ~200ms (Ollama) |
| Get cached embedding | O(1) | <1ms |
| Cache hit rate | N/A | 30-50% |

---

## Testing Strategy

### Unit Tests

Location: `/backend/tests/unit/`

- `test_numeric_validator.py` - Validation logic
- `test_math_tools.py` - Mathematical functions
- `test_stateless_isolation.py` - Pure function tests

### Integration Tests

Location: `/backend/tests/`

- `test_redis_chat_rag.py` - RAG memory system
- `test_redis_chat_api.py` - HTTP API integration
- Memory manager tests (episodic, procedural, semantic, short-term)
- Workout indexer tests

### Running Tests

```bash
# All tests
cd backend
uv run pytest tests/

# Unit tests only (no external dependencies)
uv run pytest tests/unit/

# Integration tests (require Redis)
uv run pytest tests/ -k "not unit"
```

---

## Standards Compliance

All services follow these standards:

- ✅ **UTC datetime**: `datetime.now(UTC)`
- ✅ **Single-user mode**: `utils.user_config.get_user_id()`
- ✅ **Error handling**: Graceful degradation with logging
- ✅ **Connection management**: `RedisConnectionManager`
- ✅ **Semantic naming**: Clear, descriptive file names
- ✅ **Type hints**: Full type annotation coverage
- ✅ **Docstrings**: Comprehensive documentation

---

## Migration Notes

### Backward Compatibility

The refactoring maintains backward compatibility through aliases:

```python
# Old import (still works with deprecation warning)
from .short_term_memory_manager import get_memory_manager, MemoryManager

# New import (recommended)
from .short_term_memory_manager import get_short_term_memory_manager, ShortTermMemoryManager
```

### Breaking Changes

None. All existing code continues to work with deprecation warnings.

---

## Future Enhancements

### Planned Improvements

1. **Multi-user support**: Extend single-user pattern to multi-tenant architecture
2. **Embedding model upgrades**: Support for larger/better embedding models
3. **Memory pruning**: Automatic cleanup of low-relevance memories
4. **Cache warming**: Pre-populate embedding cache with common queries
5. **Metrics dashboard**: Real-time monitoring of memory system performance

### Architecture Evolution

The current architecture provides a solid foundation for these enhancements without requiring major refactoring. The modular design allows independent evolution of each service.

---

## Related Documentation

- [Memory Architecture Delta](/docs/MEMORY_ARCHITECTURE_DELTA.md) - Gap analysis vs Redis CoALA guide
- [Memory Architecture Implementation](/docs/MEMORY_ARCHITECTURE_IMPLEMENTATION_SUMMARY.md) - Implementation details
- [Duplication Removal](/docs/DUPLICATION_REMOVAL_COMPLETE.md) - Code cleanup summary
- [Services Review](/docs/SERVICES_REVIEW_SEMANTIC_NAMING.md) - Original duplication analysis
- [RAG Implementation](/docs/RAG_IMPLEMENTATION.md) - RedisVL memory architecture

---

**Last Updated:** October 24, 2025
**Version:** 1.0.0
**Refactoring Status:** Complete
