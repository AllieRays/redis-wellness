# Architecture Overview

**Last Updated**: October 24, 2024

## System Design

Redis Wellness is a **side-by-side demo** comparing stateless chat vs. agentic RAG chat, built with clean architecture principles and production-ready patterns.

### Core Principle: Show, Don't Tell

The entire application is designed to **demonstrate** the transformative power of memory in AI conversations through live comparison:

- **Left side**: Stateless agent (NO memory) - forgets everything
- **Right side**: Stateful RAG agent (WITH CoALA memory) - remembers context

### Architecture Goals

1. **Demo-Focused**: Easy to understand and present
2. **Production-Ready**: Real patterns, not toy examples
3. **Privacy-First**: 100% local processing (no cloud APIs)
4. **Maintainable**: Clean separation of concerns
5. **Testable**: 91+ tests with validation strategies

---

## System Architecture Diagram

```
                           Docker Network
┌──────────────────────────────────────────────────────────┐
│                                                           │
│  Frontend (TS+Vite) ────→ Backend (FastAPI) ───→ Redis   │
│       :3000                    :8000             :6379    │
│                                  ↓                        │
│                      Agentic Tool Loop (simple)           │
│                              ↓                            │
│                           Ollama (Host)                   │
│                              :11434                       │
└───────────────────────────────────────────────────────────┘

Redis/RedisVL stores:
- Short-term memory (conversation history)
- Long-term memory (semantic vector search)
- Health data cache (7-month TTL)
```

---

## Component Architecture

### Layered Architecture (Clean Architecture)

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                   │
│  chat_routes.py, system_routes.py, health_routes.py    │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   Agent Layer                            │
│  stateless_agent.py, stateful_rag_agent.py             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  Service Layer                           │
│  redis_chat.py, memory_coordinator.py,                  │
│  episodic/procedural/semantic/short_term managers       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Data Layer (Redis + Tools)                  │
│  Redis Stack, RedisVL, Apple Health query tools         │
└─────────────────────────────────────────────────────────┘
```

### Component Responsibilities

#### API Layer (`/api/`)
**Purpose**: HTTP request/response handling

- `chat_routes.py`: Chat endpoints (stateless, redis, streaming)
- `system_routes.py`: Router aggregation and health checks
- `health_routes.py`: Health data upload and management

**Key Pattern**: Thin controllers - minimal logic, delegate to services

#### Agent Layer (`/agents/`)
**Purpose**: AI agent implementations for demo comparison

- `stateless_agent.py`: Baseline agent with NO memory
- `stateful_rag_agent.py`: Full CoALA memory agent

**Key Pattern**: Simple tool-calling loop (no framework overhead)

#### Service Layer (`/services/`)
**Purpose**: Business logic and data operations

**Chat Services**:
- `stateless_chat.py`: No-memory chat service
- `redis_chat.py`: RAG chat with full memory

**Memory Services** (CoALA Framework):
- `memory_coordinator.py`: Orchestrates all 4 memory types
- `episodic_memory_manager.py`: User preferences, goals, events
- `procedural_memory_manager.py`: Learned tool sequences
- `semantic_memory_manager.py`: General health knowledge
- `short_term_memory_manager.py`: Conversation history

**Infrastructure**:
- `redis_connection.py`: Connection pooling + circuit breaker
- `embedding_service.py`: Centralized embedding generation
- `embedding_cache.py`: Redis-backed embedding cache

#### Utility Layer (`/utils/`)
**Purpose**: Pure functions and helpers (no I/O)

- `agent_helpers.py`: Shared agent utilities (LLM creation, prompts)
- `numeric_validator.py`: LLM hallucination detection
- `redis_keys.py`: Centralized Redis key generation
- `user_config.py`: Single-user configuration
- `exceptions.py`: Custom exception hierarchy

#### Tools Layer (`/apple_health/query_tools/`)
**Purpose**: LangChain tools for AI agent tool calling

9 specialized tools:
- `search_health_records.py`: Query health metrics
- `search_workouts.py`: Find workouts by type/date
- `aggregate_metrics.py`: Calculate averages, totals
- `compare_periods.py`: Compare time periods
- `trend_analysis.py`: Analyze trends over time
- `progress_tracking.py`: Track goal progress
- `workout_patterns.py`: Identify patterns
- `health_insights.py`: Generate insights
- `identify_anomalies.py`: Detect unusual data

---

## Key Design Patterns

### 1. Simple Tool-Calling Loop (No LangGraph)

**Why?**
- Redis already handles persistence
- Queries complete in one turn (3-15 seconds)
- Simpler to debug and maintain
- Same agentic behavior

**Implementation**:
```python
# Both agents use this pattern
for iteration in range(max_tool_calls):
    response = await llm_with_tools.ainvoke(conversation)

    if not response.tool_calls:
        break  # Agent is done

    # Execute tools
    for tool_call in response.tool_calls:
        result = await tool.ainvoke(tool_call["args"])
        conversation.append(ToolMessage(content=result))
```

**See**: `docs/WHY_NO_LANGGRAPH.md` for detailed comparison

---

### 2. CoALA Memory Framework

**What**: 4-memory cognitive architecture for AI agents

**Implementation**: Redis + RedisVL

| Memory Type | Data Structure | Use Case |
|------------|----------------|----------|
| Episodic | RedisVL HNSW | User preferences, goals |
| Procedural | Redis Hash | Learned tool patterns |
| Semantic | RedisVL HNSW | General health knowledge |
| Short-Term | Redis List | Conversation history |

**See**: `docs/04_MEMORY_SYSTEM.md` for complete documentation

---

### 3. Tool-First Policy

**Rule**: For factual data queries, ALWAYS call tools first (never answer from memory)

**Why?**
- Memory can become stale
- Tools provide current, accurate data
- Memory is for USER CONTEXT, not factual data

**Implementation**:
```python
def _is_factual_data_query(self, message: str) -> bool:
    """Detect if query asks for factual data."""
    factual_keywords = [
        "how many", "what day", "when did i",
        "average", "total", "count", "workouts"
    ]
    return any(keyword in message.lower() for keyword in factual_keywords)

# Skip semantic memory for factual queries
skip_long_term = self._is_factual_data_query(message)
```

---

### 4. Circuit Breaker Pattern (Redis)

**What**: Automatically stop calling Redis when it's failing

**Implementation** (`redis_connection.py`):
```python
class RedisCircuitBreaker:
    def can_execute(self) -> bool:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True
```

**States**:
- **CLOSED**: Normal operation
- **OPEN**: Failing, reject requests (after 5 failures)
- **HALF_OPEN**: Testing if recovered (after 30 seconds)

---

### 5. Connection Pooling

**What**: Reuse Redis connections for performance

**Implementation**:
```python
pool = ConnectionPool(
    max_connections=20,
    retry_on_timeout=True,
    socket_connect_timeout=5,
    health_check_interval=30
)
```

**Benefits**:
- Reduced connection overhead
- Better performance under load
- Automatic health checking

---

### 6. Embedding Cache

**What**: Cache embeddings in Redis to avoid expensive regeneration

**Performance**:
- Without cache: ~200ms per embedding (Ollama inference)
- With cache hit: <1ms (Redis GET)
- Typical hit rate: 30-50%

**Implementation**: `embedding_cache.py`

---

### 7. Numeric Validation

**What**: Detect LLM hallucinations by validating numbers in responses

**Strategy**:
1. Extract all numbers from LLM response
2. Extract all numbers from tool results
3. Check if response numbers match tool data
4. Calculate validation score (0-100%)

**Implementation**: `numeric_validator.py`

---

## Technology Choices

### Why These Technologies?

| Technology | Purpose | Why This Choice? |
|-----------|---------|------------------|
| **FastAPI** | Backend API | Async support, auto docs, modern Python |
| **Redis Stack** | Memory storage | Fast, versatile, production-proven |
| **RedisVL** | Vector search | Native Redis integration, HNSW index |
| **Ollama** | LLM inference | 100% local, no API keys, privacy |
| **Qwen 2.5 7B** | Main LLM | Optimized for tool calling, 4.7 GB |
| **mxbai-embed-large** | Embeddings | 1024 dims, good quality, 669 MB |
| **TypeScript** | Frontend | Type safety, modern tooling |
| **Vite** | Frontend build | Fast HMR, modern dev experience |
| **Docker** | Deployment | Consistent environments, easy setup |

---

### Why Qwen 2.5 7B?

**Compared to alternatives**:

| Model | Size | Tool Calling | Speed | Local? |
|-------|------|-------------|-------|--------|
| Qwen 2.5 7B | 4.7 GB | ⭐⭐⭐⭐⭐ | Fast | ✅ |
| Llama 3.1 8B | 4.7 GB | ⭐⭐⭐ | Fast | ✅ |
| GPT-4 | N/A | ⭐⭐⭐⭐⭐ | Fast | ❌ Cloud |
| Llama 3.1 70B | 40 GB | ⭐⭐⭐⭐ | Slow | ✅ |

**Winner**: Qwen 2.5 7B - Best tool calling performance at reasonable size

---

### Why Not LangGraph?

**Short Answer**: Redis already does what LangGraph does (persistence), and our queries are simple (complete in one turn).

**Detailed Analysis**: `docs/WHY_NO_LANGGRAPH.md`

**Key Points**:
1. Redis handles state persistence (no need for checkpointers)
2. No multi-hour workflows (queries complete in 3-15 seconds)
3. Simpler code (just a Python loop)
4. Same agentic behavior (LLM chooses tools autonomously)

---

## Single-User Mode

### Why Single-User?

This is a **demo application** focused on showing memory capabilities, not a multi-tenant production app.

### Implementation

All services accept `user_id` parameter but use a configured single user:

```python
# utils/user_config.py
def get_user_id() -> str:
    """Get the single configured user ID."""
    return "user123"  # Hardcoded for demo
```

### Multi-User Migration Path

To convert to multi-user:

1. Add authentication (JWT tokens)
2. Extract `user_id` from auth context
3. Add user management endpoints
4. Namespace Redis keys by user (already done!)
5. Add access control checks

**All Redis keys are already namespaced** by `user_id` or `session_id`, so the data layer is multi-user ready.

---

## Data Flow

### Stateless Chat Flow

```
User Query
    ↓
API (chat_routes.py)
    ↓
StatelessHealthAgent
    ↓
Tool Selection (LLM)
    ↓
Tool Execution
    ↓
Response (forgets everything)
```

**No memory storage or retrieval**

---

### RAG Chat Flow (With Memory)

```
User Query
    ↓
API (chat_routes.py)
    ↓
RedisChatService
    ↓
Memory Retrieval (4 types)
    ├─ Short-term (last 10 messages)
    ├─ Episodic (user preferences)
    ├─ Procedural (learned patterns)
    └─ Semantic (health knowledge)
    ↓
StatefulRAGAgent (with memory context)
    ↓
Tool Selection (LLM + memory)
    ↓
Tool Execution
    ↓
Response Generation
    ↓
Memory Storage (4 types)
    ├─ Short-term (conversation)
    ├─ Episodic (if meaningful)
    ├─ Procedural (tool patterns)
    └─ Semantic (no per-interaction updates)
    ↓
Response (remembers context)
```

---

## Error Handling Strategy

### Exception Hierarchy

```python
# Custom exceptions (utils/exceptions.py)
class BaseApplicationError(Exception)
    ├─ ValidationError
    ├─ MemoryRetrievalError
    ├─ LLMServiceError
    └─ InfrastructureError
```

### Error Handling Pattern

```python
try:
    result = await service.process()
except MemoryRetrievalError as e:
    logger.error(f"Memory failed: {e.memory_type} - {e.reason}")
    # Fallback: proceed without memory
except LLMServiceError as e:
    logger.error(f"LLM failed: {e.reason}")
    raise HTTPException(status_code=503, detail="LLM unavailable")
```

### API Error Responses

All errors return consistent format:
```json
{
    "error": "Error message",
    "error_type": "MemoryRetrievalError",
    "details": {...}
}
```

---

## Performance Considerations

### Memory Retrieval Latency

| Operation | Avg Latency | Data Structure |
|-----------|------------|----------------|
| Short-term (10 msgs) | <1ms | Redis List |
| Procedural lookup | <1ms | Redis Hash (O(1)) |
| Episodic search | 10-50ms | RedisVL HNSW |
| Semantic search | 10-50ms | RedisVL HNSW |
| **Total** | **~50ms** | All 4 types |

### LLM Inference Latency

| Model | Avg Response Time | Tokens/sec |
|-------|------------------|------------|
| Qwen 2.5 7B | 3-8 seconds | ~25-30 |
| Tool calls | +500ms per tool | - |
| Total query | 3-15 seconds | - |

**Note**: First request takes longer (model loading into memory)

### Optimization Strategies

1. **Embedding Cache**: 30-50% hit rate saves ~200ms per cache hit
2. **Connection Pooling**: Reduces Redis connection overhead
3. **Async/Await**: Non-blocking I/O throughout
4. **Simple Loop**: Minimal framework overhead

---

## Security Considerations

### Current Security (Demo Mode)

- ✅ **Local-only**: No data sent to cloud APIs
- ✅ **XSS Protection**: Frontend sanitizes HTML
- ✅ **CORS**: Restricted to localhost origins
- ✅ **Input Validation**: Pydantic models validate all inputs
- ⚠️ **No Authentication**: Single-user demo (by design)

### Production Security Additions

For production deployment, add:

1. **Authentication**: JWT tokens or OAuth
2. **Rate Limiting**: Per-user request limits
3. **Input Sanitization**: Additional validation layers
4. **HTTPS**: TLS encryption for all traffic
5. **Access Control**: Role-based permissions
6. **Audit Logging**: Track all data access

---

## Scalability

### Current Scale (Single-User Demo)

- **Concurrent Users**: 1 (by design)
- **Redis Memory**: ~50 MB typical
- **Request Rate**: 1-2 requests/minute (human speed)

### Multi-User Scale Estimates

**With current architecture** (no changes needed):

| Users | Redis Memory | Request Rate | Notes |
|-------|-------------|--------------|-------|
| 10 | 500 MB | 20/min | Easy |
| 100 | 5 GB | 200/min | No changes needed |
| 1,000 | 50 GB | 2,000/min | Redis cluster recommended |
| 10,000 | 500 GB | 20,000/min | Redis cluster + load balancer |

**Bottleneck**: Ollama is single-threaded (one request at a time)

**Solution**: Run multiple Ollama instances with load balancer

---

## Monitoring & Observability

### Current Logging

- **Structured Logging**: JSON format with timestamps
- **Log Levels**: INFO for normal ops, ERROR for failures
- **Correlation**: All logs include `user_id` and `session_id`

### Health Checks

```bash
# Comprehensive health check
curl http://localhost:8000/health

# Returns:
{
    "status": "healthy",
    "timestamp": 1729756800,
    "dependencies": {
        "redis": {"status": "healthy", ...},
        "ollama": {"status": "healthy", "models_available": [...]}
    }
}
```

### Metrics to Monitor (Production)

1. **Redis**:
   - Memory usage
   - Connection pool utilization
   - Circuit breaker state

2. **LLM**:
   - Response latency (p50, p95, p99)
   - Tool calls per query
   - Validation scores

3. **Memory System**:
   - Cache hit rates (embedding, memory)
   - Memory retrieval latency
   - Storage success rates

---

## Testing Strategy

### Test Coverage

- **91+ tests** across unit and integration
- **Categories**: Unit, integration, validation, memory
- **Anti-Hallucination**: Numeric validation in all tests

### Test Structure

```
backend/tests/
├── unit/                      # Pure function tests
│   ├── test_numeric_validator.py
│   ├── test_math_tools.py
│   └── test_stateless_isolation.py
├── test_redis_chat_rag.py    # Memory system integration
├── test_redis_chat_api.py    # API integration
└── test_memory_coordinator.py # Memory orchestration
```

**See**: `docs/07_TESTING.md` for complete strategy

---

## Deployment

### Development

```bash
# Quick start
./start.sh

# Or manual
docker-compose up --build
```

### Production Considerations

**Infrastructure**:
- Redis: Managed Redis (AWS ElastiCache, Redis Cloud)
- Backend: Container orchestration (Kubernetes, ECS)
- Frontend: CDN (Cloudflare, CloudFront)
- LLM: Dedicated GPU instances for Ollama

**Configuration**:
- Environment variables for all settings
- Secrets management (AWS Secrets Manager, Vault)
- Health checks for all services
- Auto-scaling based on load

---

## Future Enhancements

### Possible Extensions

1. **Multi-User Support**: Add authentication and user management
2. **Additional Data Sources**: Fitbit, Garmin, Oura integration
3. **Advanced Analytics**: Machine learning for health predictions
4. **Voice Interface**: Speech-to-text for hands-free interaction
5. **Mobile App**: React Native or Flutter companion app
6. **Scheduled Reports**: Daily/weekly health summaries via email

### Architecture Implications

All extensions can be added without major refactoring thanks to:
- Clean separation of concerns
- Service layer abstractions
- Pluggable data sources
- Extensible memory system

---

## See Also

- **Memory System**: `docs/04_MEMORY_SYSTEM.md`
- **Agent Comparison**: `docs/05_AGENT_COMPARISON.md`
- **Testing Strategy**: `docs/07_TESTING.md`
- **API Reference**: `docs/09_API.md`
- **Why No LangGraph**: `docs/WHY_NO_LANGGRAPH.md`

---

**Last Updated**: October 24, 2024
**Maintainer**: [Your Name]
