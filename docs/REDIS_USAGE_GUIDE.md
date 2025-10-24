# Redis Usage Guide: Complete Reference

**Purpose**: Document every way we use Redis in this application
**Last Updated**: October 2024

---

## Table of Contents

1. [Redis Data Structures Used](#redis-data-structures-used)
2. [CoALA Memory System](#coala-memory-system)
3. [Health Data Storage](#health-data-storage)
4. [Workout Indexing](#workout-indexing)
5. [Caching Layer](#caching-layer)
6. [Key Patterns](#key-patterns)
7. [TTL Strategy](#ttl-strategy)
8. [Real Examples](#real-examples)

---

## Redis Data Structures Used

We leverage 5 different Redis data structures for optimal performance:

| Data Structure | Use Case | Performance | Example |
|---------------|----------|-------------|---------|
| **STRING** | Simple key-value storage | O(1) | Health data JSON |
| **LIST** | Conversation history | O(1) prepend/access | Chat messages |
| **HASH** | Complex objects | O(1) field access | Workout details, procedural memory |
| **SORTED SET** | Time-ordered data | O(log N) range queries | Workouts by date |
| **VECTOR (RedisVL)** | Semantic search | O(log N) similarity | Episodic/semantic memory |

---

## CoALA Memory System

Our implementation of the CoALA (Cognitive Architecture for Language Agents) framework using Redis.

### 1. Short-Term Memory (Conversation History)

**Data Structure**: Redis LIST
**File**: `backend/src/services/short_term_memory_manager.py`
**TTL**: 7 months (18,144,000 seconds)

#### Key Pattern
```
health_chat_session:{session_id}
```

#### Storage Example
```python
# Store a message
await memory_manager.store_short_term_message(
    user_id=get_user_id(),
    session_id="demo",
    role="user",
    content="What was my heart rate last week?"
)

# Redis command executed:
# LPUSH health_chat_session:demo '{"id": "uuid", "role": "user", "content": "...", "timestamp": "2024-10-24T..."}'
# EXPIRE health_chat_session:demo 18144000
```

#### Retrieval Example
```python
# Get last 10 messages
messages = await memory_manager.get_short_term_context(
    user_id=get_user_id(),
    session_id="demo",
    limit=10
)

# Redis command executed:
# LRANGE health_chat_session:demo 0 9
```

#### Redis Data
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "role": "user",
    "content": "What was my heart rate last week?",
    "timestamp": "2024-10-24T15:30:00Z"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "role": "assistant",
    "content": "Your average heart rate last week was 72 bpm.",
    "timestamp": "2024-10-24T15:30:15Z"
  }
]
```

---

### 2. Episodic Memory (User Preferences & Goals)

**Data Structure**: RedisVL Vector Search (HASH + VECTOR INDEX)
**File**: `backend/src/services/episodic_memory_manager.py`
**TTL**: 7 months

#### Key Pattern
```
episodic:{user_id}:{event_type}:{timestamp}
```

#### Vector Index Schema
```python
{
    "index": {
        "name": "episodic_memory_idx",
        "prefix": "episodic:",
        "storage_type": "hash"
    },
    "fields": [
        {"name": "user_id", "type": "tag"},
        {"name": "event_type", "type": "tag"},  # preference, goal, health_event, etc.
        {"name": "timestamp", "type": "numeric"},
        {"name": "description", "type": "text"},
        {"name": "context", "type": "text"},
        {"name": "embedding", "type": "vector", "dims": 1024}  # mxbai-embed-large
    ]
}
```

#### Storage Example
```python
# Store user preference
await episodic_manager.store_episodic_event(
    user_id=get_user_id(),
    event_type=EpisodicEventType.PREFERENCE,
    description="User prefers morning workouts",
    context="Mentioned during conversation about workout scheduling",
    metadata={"workout_time": "07:00"}
)

# Redis commands executed:
# HSET episodic:wellness_user:preference:1729774800
#   user_id "wellness_user"
#   event_type "preference"
#   timestamp 1729774800
#   description "User prefers morning workouts"
#   context "Mentioned during conversation..."
#   metadata '{"workout_time": "07:00"}'
#   embedding <1024-dim vector bytes>
# EXPIRE episodic:wellness_user:preference:1729774800 18144000
```

#### Retrieval Example (Semantic Search)
```python
# Search for user preferences
result = await episodic_manager.retrieve_episodic_memories(
    user_id=get_user_id(),
    query="What are my workout preferences?",
    event_types=[EpisodicEventType.PREFERENCE],
    top_k=5
)

# Redis commands executed:
# 1. Generate embedding for query
# 2. FT.SEARCH episodic_memory_idx
#    "@user_id:{wellness_user} @event_type:{preference}"
#    KNN 5 @embedding $vector
#    RETURN 5 description context event_type timestamp metadata
```

#### Redis Data
```json
{
  "user_id": "wellness_user",
  "event_type": "preference",
  "timestamp": 1729774800,
  "description": "User prefers morning workouts",
  "context": "Mentioned during conversation about workout scheduling",
  "metadata": "{\"workout_time\": \"07:00\"}",
  "embedding": "<binary 1024-dim float32 array>"
}
```

---

### 3. Procedural Memory (Learned Tool Sequences)

**Data Structure**: Redis HASH
**File**: `backend/src/services/procedural_memory_manager.py`
**TTL**: 7 months

#### Key Pattern
```
procedure:{user_id}:{query_hash}
```

#### Storage Example
```python
# Record successful tool sequence
await procedural_manager.record_procedure(
    user_id=get_user_id(),
    query="What was my average heart rate last week?",
    tool_sequence=["aggregate_metrics", "compare_periods"],
    execution_time_ms=1250.5,
    success_score=0.95,
    metadata={"validation_score": 0.98}
)

# Redis commands executed:
# Query hash: MD5("what was my average heart rate last week?")[:8] = "a1b2c3d4"
# HSET procedure:wellness_user:a1b2c3d4
#   user_id "wellness_user"
#   query_pattern "What was my average heart rate last week?"
#   tool_sequence '["aggregate_metrics", "compare_periods"]'
#   execution_count 1
#   avg_execution_time_ms 1250.5
#   avg_success_score 0.95
#   created_at "2024-10-24T15:30:00Z"
#   last_used "2024-10-24T15:30:00Z"
#   metadata '{"validation_score": 0.98}'
# EXPIRE procedure:wellness_user:a1b2c3d4 18144000
```

#### Update Example (Learning Over Time)
```python
# Same query asked again
await procedural_manager.record_procedure(
    user_id=get_user_id(),
    query="What was my average heart rate last week?",
    tool_sequence=["aggregate_metrics", "compare_periods"],
    execution_time_ms=1100.0,
    success_score=0.98
)

# Redis automatically updates with averaging:
# execution_count: 1 → 2
# avg_execution_time_ms: 1250.5 → 1175.25  # (1250.5 + 1100) / 2
# avg_success_score: 0.95 → 0.965  # (0.95 + 0.98) / 2
```

#### Redis Data
```json
{
  "user_id": "wellness_user",
  "query_pattern": "What was my average heart rate last week?",
  "tool_sequence": "[\"aggregate_metrics\", \"compare_periods\"]",
  "execution_count": "2",
  "avg_execution_time_ms": "1175.25",
  "avg_success_score": "0.965",
  "created_at": "2024-10-24T15:30:00Z",
  "last_used": "2024-10-24T16:45:00Z",
  "metadata": "{\"validation_score\": 0.98}"
}
```

---

### 4. Semantic Memory (General Health Knowledge)

**Data Structure**: RedisVL Vector Search (HASH + VECTOR INDEX)
**File**: `backend/src/services/semantic_memory_manager.py`
**TTL**: 7 months

#### Key Pattern
```
semantic:{category}:{fact_type}:{timestamp}
```

#### Vector Index Schema
```python
{
    "index": {
        "name": "semantic_knowledge_idx",
        "prefix": "semantic:",
        "storage_type": "hash"
    },
    "fields": [
        {"name": "fact_type", "type": "tag"},  # definition, relationship, guideline
        {"name": "category", "type": "tag"},   # cardio, nutrition, metrics, etc.
        {"name": "timestamp", "type": "numeric"},
        {"name": "fact", "type": "text"},
        {"name": "context", "type": "text"},
        {"name": "source", "type": "text"},
        {"name": "embedding", "type": "vector", "dims": 1024}
    ]
}
```

#### Storage Example
```python
# Store health knowledge
await semantic_manager.store_semantic_fact(
    fact="Normal resting heart rate is 60-100 bpm",
    fact_type="guideline",
    category="cardio",
    context="Standard medical guideline for adults",
    source="medical_literature"
)

# Redis commands executed:
# HSET semantic:cardio:guideline:1729774800
#   fact_type "guideline"
#   category "cardio"
#   timestamp 1729774800
#   fact "Normal resting heart rate is 60-100 bpm"
#   context "Standard medical guideline for adults"
#   source "medical_literature"
#   metadata '{}'
#   embedding <1024-dim vector bytes>
# EXPIRE semantic:cardio:guideline:1729774800 18144000
```

#### Redis Data
```json
{
  "fact_type": "guideline",
  "category": "cardio",
  "timestamp": 1729774800,
  "fact": "Normal resting heart rate is 60-100 bpm",
  "context": "Standard medical guideline for adults",
  "source": "medical_literature",
  "metadata": "{}",
  "embedding": "<binary 1024-dim float32 array>"
}
```

---

## Health Data Storage

### Main Health Data Collection

**Data Structure**: STRING (JSON)
**File**: `backend/src/services/redis_apple_health_manager.py`
**TTL**: None (permanent)

#### Key Pattern
```
health:user:{user_id}:data
```

#### Storage Example
```python
# Store parsed Apple Health export
storage_info = manager.store_health_data(
    user_id=get_user_id(),
    health_data={
        "record_count": 45123,
        "data_categories": ["HeartRate", "Steps", "Workouts"],
        "date_range": {"start": "2023-01-01", "end": "2024-10-24"},
        "metrics_summary": {...},
        "workouts": {...}
    },
    ttl_days=210
)

# Redis commands executed:
# SET health:user:wellness_user:data '{"record_count": 45123, ...}'
# (No EXPIRE - permanent storage)
```

#### Redis Data
```json
{
  "record_count": 45123,
  "data_categories": ["HeartRate", "Steps", "Workouts", "ActiveEnergyBurned"],
  "date_range": {
    "start": "2023-01-01",
    "end": "2024-10-24"
  },
  "metrics_summary": {
    "HeartRate": {
      "count": 12345,
      "avg": 72.5,
      "min": 52,
      "max": 165
    }
  },
  "workouts": [...]
}
```

---

### Health Metric Indexes (Fast Queries)

**Data Structure**: STRING (JSON)
**File**: `backend/src/services/redis_apple_health_manager.py`
**TTL**: 210 days (7 months)

#### Key Pattern
```
health:user:{user_id}:metric:{metric_type}
```

#### Storage Example
```python
# Automatically created during import
# For each metric type (HeartRate, Steps, etc.)

# Redis commands executed:
# SETEX health:user:wellness_user:metric:HeartRate 18144000 '{"count": 12345, "avg": 72.5, ...}'
# SETEX health:user:wellness_user:metric:Steps 18144000 '{"count": 8901, "avg": 8500, ...}'
```

#### Query Example
```python
# Fast O(1) metric lookup
result = manager.query_health_metrics(
    user_id=get_user_id(),
    metric_types=["HeartRate", "Steps"]
)

# Redis commands executed:
# GET health:user:wellness_user:metric:HeartRate
# GET health:user:wellness_user:metric:Steps
# TTL health:user:wellness_user:metric:HeartRate
# TTL health:user:wellness_user:metric:Steps
```

#### Redis Data
```json
{
  "count": 12345,
  "avg": 72.5,
  "min": 52,
  "max": 165,
  "recent_values": [72, 68, 75, 71, 69],
  "date_range": {
    "start": "2023-01-01",
    "end": "2024-10-24"
  }
}
```

---

### Health Context

**Data Structure**: STRING
**File**: `backend/src/services/redis_apple_health_manager.py`
**TTL**: None (permanent)

#### Key Pattern
```
health:user:{user_id}:context
```

#### Storage Example
```python
# Store conversation context about health data
# Redis command executed:
# SET health:user:wellness_user:context "User has consistent workout routine, tracks heart rate daily"
```

---

### Recent Health Insights

**Data Structure**: STRING (JSON)
**File**: `backend/src/services/redis_apple_health_manager.py`
**TTL**: 210 days

#### Key Pattern
```
health:user:{user_id}:recent_insights
```

#### Storage Example
```python
# Automatically created during import
# Redis command executed:
# SETEX health:user:wellness_user:recent_insights 18144000 '{"record_count": 45123, ...}'
```

#### Redis Data
```json
{
  "record_count": 45123,
  "data_categories": ["HeartRate", "Steps", "Workouts"],
  "date_range": {
    "start": "2023-01-01",
    "end": "2024-10-24"
  },
  "generated_at": "2024-10-24T15:30:00Z"
}
```

---

## Workout Indexing

Redis indexes enable **O(1)** workout aggregations without parsing JSON.

### 1. Workout Count by Day of Week

**Data Structure**: HASH
**File**: `backend/src/services/redis_workout_indexer.py`
**TTL**: 210 days

#### Key Pattern
```
user:{user_id}:workout:days
```

#### Storage Example
```python
# Index all workouts during import
indexer.index_workouts(
    user_id=get_user_id(),
    workouts=[
        {"date": "2024-10-14", "day_of_week": "Monday", "type": "Running"},
        {"date": "2024-10-16", "day_of_week": "Wednesday", "type": "Cycling"},
        {"date": "2024-10-21", "day_of_week": "Monday", "type": "Running"},
    ]
)

# Redis commands executed (using pipeline):
# HINCRBY user:wellness_user:workout:days Monday 1
# HINCRBY user:wellness_user:workout:days Wednesday 1
# HINCRBY user:wellness_user:workout:days Monday 1  # Now 2
# EXPIRE user:wellness_user:workout:days 18144000
```

#### Query Example
```python
# Instant O(1) aggregation
counts = indexer.get_workout_count_by_day(get_user_id())

# Redis command executed:
# HGETALL user:wellness_user:workout:days
```

#### Redis Data
```json
{
  "Monday": "15",
  "Tuesday": "8",
  "Wednesday": "12",
  "Thursday": "10",
  "Friday": "14",
  "Saturday": "6",
  "Sunday": "5"
}
```

---

### 2. Workout Index by Date (Range Queries)

**Data Structure**: SORTED SET
**File**: `backend/src/services/redis_workout_indexer.py`
**TTL**: 210 days

#### Key Pattern
```
user:{user_id}:workout:by_date
```

#### Storage Example
```python
# Workouts stored with timestamp as score
# Redis commands executed:
# ZADD user:wellness_user:workout:by_date
#   1697241600 "2024-10-14:Running:073000"
#   1697414400 "2024-10-16:Cycling:073000"
#   1697846400 "2024-10-21:Running:073000"
# EXPIRE user:wellness_user:workout:by_date 18144000
```

#### Range Query Example
```python
# Get workouts between dates (O(log N))
workout_ids = indexer.get_workouts_in_date_range(
    user_id=get_user_id(),
    start_timestamp=1697241600,  # Oct 14
    end_timestamp=1697846400     # Oct 21
)

# Redis command executed:
# ZRANGEBYSCORE user:wellness_user:workout:by_date 1697241600 1697846400
```

#### Redis Data
```
Score (timestamp) | Member (workout_id)
1697241600       | 2024-10-14:Running:073000
1697414400       | 2024-10-16:Cycling:073000
1697846400       | 2024-10-21:Running:073000
```

---

### 3. Individual Workout Details

**Data Structure**: HASH
**File**: `backend/src/services/redis_workout_indexer.py`
**TTL**: 210 days

#### Key Pattern
```
user:{user_id}:workout:{workout_id}
```

#### Storage Example
```python
# Each workout stored as hash
# Redis command executed:
# HSET user:wellness_user:workout:2024-10-14:Running:073000
#   date "2024-10-14"
#   startDate "2024-10-14T07:30:00Z"
#   day_of_week "Monday"
#   type "Running"
#   duration_minutes "45"
#   calories "420"
# EXPIRE user:wellness_user:workout:2024-10-14:Running:073000 18144000
```

#### Redis Data
```json
{
  "date": "2024-10-14",
  "startDate": "2024-10-14T07:30:00Z",
  "day_of_week": "Monday",
  "type": "Running",
  "duration_minutes": "45",
  "calories": "420"
}
```

---

## Caching Layer

### Embedding Cache

**Data Structure**: STRING (JSON)
**File**: `backend/src/services/embedding_cache.py`
**TTL**: 1 hour (3600 seconds)

#### Key Pattern
```
embedding_cache:{query_hash}
```

#### Storage Example
```python
# Cache expensive embedding generation
embedding = await cache.get_or_generate(
    query="What are my workout preferences?",
    generate_fn=lambda: ollama_generate_embedding(query)
)

# First call (cache miss):
# GET embedding_cache:a1b2c3d4e5f6...  # Returns None
# <Generate embedding with Ollama - ~200ms>
# SETEX embedding_cache:a1b2c3d4e5f6... 3600 '[0.234, -0.123, ...]'

# Second call (cache hit):
# GET embedding_cache:a1b2c3d4e5f6...  # Returns cached embedding <1ms
```

#### Performance Impact
```
Without cache: ~200ms per embedding (Ollama inference)
With cache hit: <1ms (Redis GET)
Hit rate: 30-50% in production
Savings: 150-200ms per cache hit
```

#### Redis Data
```json
[0.234, -0.123, 0.456, -0.789, ..., 0.321]  // 1024 floats
```

---

## Key Patterns

All Redis keys follow consistent naming conventions (centralized in `utils/redis_keys.py`):

### Pattern Summary

| Domain | Pattern | Example |
|--------|---------|---------|
| **Health Data** | `health:user:{user_id}:*` | `health:user:wellness_user:data` |
| **Workouts** | `user:{user_id}:workout:*` | `user:wellness_user:workout:days` |
| **Chat Sessions** | `health_chat_session:{session_id}` | `health_chat_session:demo` |
| **Episodic Memory** | `episodic:{user_id}:{type}:{ts}` | `episodic:wellness_user:preference:1729774800` |
| **Procedural Memory** | `procedure:{user_id}:{hash}` | `procedure:wellness_user:a1b2c3d4` |
| **Semantic Memory** | `semantic:{category}:{type}:{ts}` | `semantic:cardio:guideline:1729774800` |
| **Embedding Cache** | `embedding_cache:{hash}` | `embedding_cache:a1b2c3d4e5f6...` |

### Wildcard Patterns (for scanning)

```python
# All health data for a user
pattern = RedisKeys.health_pattern(user_id)  # "health:user:wellness_user:*"

# All workouts for a user
pattern = RedisKeys.workout_pattern(user_id)  # "user:wellness_user:workout:*"

# All semantic memory for a user
pattern = RedisKeys.semantic_pattern(user_id)  # "memory:semantic:wellness_user:*"
```

---

## TTL Strategy

Different data types have different expiration policies:

| Data Type | TTL | Reason |
|-----------|-----|--------|
| **Health Data (main)** | ♾️ Permanent | Source of truth |
| **Health Indexes** | 7 months | Rebuildable from main data |
| **Workouts** | 7 months | Rebuildable from main data |
| **All Memory Types** | 7 months | Balance: retention vs. relevance |
| **Chat Sessions** | 7 months | Privacy + cleanup |
| **Embedding Cache** | 1 hour | Frequently changing queries |

### Why 7 Months?

```python
# Configuration
TTL_DAYS = 210  # 7 months
TTL_SECONDS = 210 * 24 * 60 * 60  # 18,144,000 seconds

# Reasoning:
# - Long enough for longitudinal health tracking
# - Short enough for automatic cleanup
# - Matches typical health data relevance window
# - Privacy-friendly (auto-deletion)
```

---

## Real Examples

### Example 1: User Asks "What was my heart rate last week?"

```python
# 1. Short-term memory retrieval
# LRANGE health_chat_session:demo 0 9
# Returns: Last 10 conversation messages

# 2. Episodic memory search (semantic)
# FT.SEARCH episodic_memory_idx "@user_id:{wellness_user}" KNN 5 @embedding ...
# Returns: User's heart rate preferences/goals

# 3. Tool execution (aggregate_metrics)
# GET health:user:wellness_user:metric:HeartRate
# Returns: {"avg": 72.5, "count": 12345, ...}

# 4. Store interaction
# LPUSH health_chat_session:demo '{"role": "user", "content": "What was...", ...}'
# LPUSH health_chat_session:demo '{"role": "assistant", "content": "Your average...", ...}'

# 5. Update procedural memory
# HSET procedure:wellness_user:a1b2c3d4 execution_count 1 avg_execution_time_ms 1250.5 ...
```

---

### Example 2: Import Apple Health Data

```python
# 1. Store main health data (permanent)
# SET health:user:wellness_user:data '{"record_count": 45123, ...}'

# 2. Create metric indexes (7 month TTL)
# SETEX health:user:wellness_user:metric:HeartRate 18144000 '{"avg": 72.5, ...}'
# SETEX health:user:wellness_user:metric:Steps 18144000 '{"avg": 8500, ...}'
# ... (for each metric type)

# 3. Index workouts for fast queries
# HINCRBY user:wellness_user:workout:days Monday 1
# ZADD user:wellness_user:workout:by_date 1697241600 "2024-10-14:Running:073000"
# HSET user:wellness_user:workout:2024-10-14:Running:073000 date "2024-10-14" ...

# 4. Clear stale semantic memory (prevent outdated cache)
# DEL semantic:* (matching user-specific patterns)

# Result:
# - 1 permanent key (main data)
# - 20+ metric indexes (TTL)
# - 100+ workout details (TTL)
# - 3 workout aggregation indexes (TTL)
```

---

### Example 3: "Do I work out consistently on Mondays?"

```python
# 1. Embedding cache check
# GET embedding_cache:abc123def456...
# Result: Cache miss → Generate embedding

# 2. Check procedural memory for learned pattern
# HGETALL procedure:wellness_user:f4e5d6c7
# Result: Learned tool sequence ["search_workouts", "aggregate_metrics"]

# 3. Execute tools using Redis indexes
# HGETALL user:wellness_user:workout:days
# Result: {"Monday": "15", "Tuesday": "8", ...} ← O(1) lookup!

# 4. Store embedding for future
# SETEX embedding_cache:abc123def456... 3600 '[0.234, -0.123, ...]'

# 5. Update procedural memory (execution count++)
# HSET procedure:wellness_user:f4e5d6c7 execution_count 3 avg_execution_time_ms 850.2
```

---

## Redis Connection Management

**File**: `backend/src/services/redis_connection.py`

### Connection Pool
```python
class RedisConnectionManager:
    def __init__(self):
        self.redis_pool = redis.ConnectionPool(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            max_connections=10,
            decode_responses=True  # Auto-decode bytes to strings
        )

    @contextmanager
    def get_connection(self):
        """Get Redis connection from pool."""
        client = redis.Redis(connection_pool=self.redis_pool)
        try:
            yield client
        finally:
            client.close()  # Return to pool
```

### Usage Pattern
```python
# Always use context manager
with redis_manager.get_connection() as client:
    client.set("key", "value")
    result = client.get("key")
# Connection automatically returned to pool
```

---

## Performance Characteristics

### Operation Complexity

| Operation | Complexity | Use Case |
|-----------|-----------|----------|
| **GET/SET** | O(1) | Health data, metrics, cache |
| **LPUSH/LRANGE** | O(1) / O(N) | Chat history (N = limit) |
| **HGET/HSET** | O(1) | Workout details, procedural memory |
| **HINCRBY** | O(1) | Workout day counts |
| **ZADD/ZRANGEBYSCORE** | O(log N) | Workout date ranges |
| **Vector Search** | O(log N) | Episodic/semantic memory |

### Typical Query Times

```
GET (cache hit): <1ms
HGETALL (workout): 1-2ms
Vector search (top 5): 5-15ms
Complex multi-tool query: 3-8 seconds (mostly LLM, not Redis)
```

---

## Monitoring Redis Usage

### RedisInsight

Access at `http://localhost:8001` to visualize:
- All keys and their types
- Memory usage per key
- TTL for each key
- Vector indexes and search

### Key Inspection Commands

```bash
# Connect to Redis
docker exec -it redis-wellness-redis-1 redis-cli

# List all keys (use with caution in production)
KEYS *

# Count keys by pattern
EVAL "return #redis.call('keys', ARGV[1])" 0 "health:*"

# Inspect key type
TYPE health:user:wellness_user:data

# Get TTL
TTL health:user:wellness_user:metric:HeartRate

# Memory usage
MEMORY USAGE health:user:wellness_user:data
```

---

## Summary: Redis Usage Matrix

| Feature | Structure | File | Keys | TTL |
|---------|-----------|------|------|-----|
| **Short-term memory** | LIST | `short_term_memory_manager.py` | 1 per session | 7 months |
| **Episodic memory** | HASH+VECTOR | `episodic_memory_manager.py` | Many per user | 7 months |
| **Procedural memory** | HASH | `procedural_memory_manager.py` | 1 per query pattern | 7 months |
| **Semantic memory** | HASH+VECTOR | `semantic_memory_manager.py` | Many | 7 months |
| **Health data** | STRING | `redis_apple_health_manager.py` | 1 main | Permanent |
| **Health indexes** | STRING | `redis_apple_health_manager.py` | 1 per metric | 7 months |
| **Workout days** | HASH | `redis_workout_indexer.py` | 1 per user | 7 months |
| **Workout dates** | SORTED SET | `redis_workout_indexer.py` | 1 per user | 7 months |
| **Workout details** | HASH | `redis_workout_indexer.py` | 1 per workout | 7 months |
| **Embedding cache** | STRING | `embedding_cache.py` | 1 per query | 1 hour |

**Total Keys (typical user):**
- 1 health data (permanent)
- 20 metric indexes
- 3 workout aggregation indexes
- 100-500 individual workouts
- 10-50 episodic memories
- 5-20 procedural patterns
- 10-50 semantic facts
- 1-5 active chat sessions
- 50-200 embedding cache entries

**Estimated Total**: 200-850 keys per active user

---

## Related Documentation

- `utils/redis_keys.py` - Centralized key generation
- `services/redis_connection.py` - Connection pool management
- `docs/MEMORY_ARCHITECTURE_IMPLEMENTATION_SUMMARY.md` - CoALA framework details
- `docs/WHY_NO_LANGGRAPH.md` - Why Redis handles state (not LangGraph)

---

**Last Updated**: October 2024
**Maintainer**: Backend Team
