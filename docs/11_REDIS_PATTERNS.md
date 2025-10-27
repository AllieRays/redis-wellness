# Redis Data Structures for AI Agents

## 1. Overview

Redis powers the entire memory system with five key data structures. This doc explains **which Redis structures to use when** and **why Redis beats traditional databases** for AI workloads.

### What You'll Learn

- **[Why Redis for AI](#2-why-redis-for-ai)** - Redis vs PostgreSQL comparison
- **[Five Key Structures](#3-five-key-structures)** - STRING, LIST, HASH, ZSET, Vector
- **[Health Data Patterns](#4-health-data-patterns)** - Storing Apple Health data
- **[Memory Patterns](#5-memory-patterns)** - Checkpointing and vector search
- **[Related Documentation](#6-related-documentation)** - Implementation details

---

## 2. Why Redis for AI?

### PostgreSQL Approach (Traditional)

```sql
-- Conversation history
SELECT * FROM messages WHERE session_id = 'abc123' LIMIT 10;

-- Workout aggregations
SELECT day_of_week, COUNT(*) FROM workouts GROUP BY day_of_week;

-- Vector search
-- ❌ Needs pgvector extension, slower performance
```

**Problems**: Network round-trips, join overhead, no native vector search, multiple systems

### Redis Approach (Unified)

```python
# Conversation history - O(1)
conversation = redis.lrange("session:abc123", 0, 9)

# Workout aggregations - O(1)
day_counts = redis.hgetall("workout:days")

# Vector search - native RedisVL
results = episodic_index.search(query_vector)
```

**Benefits**: In-memory speed (50-100x faster), single data store, native vector search

---

## 3. Five Key Structures

### STRING (JSON Blob)

**Use**: Store entire health data export as JSON

```python
# 15 MB health data as single JSON
redis.set("user:wellness_user:health_data", json.dumps(health_data))
```

**Pros**: Simple, O(1) retrieval
**Cons**: No partial updates, no indexing

---

### LIST (Conversation History)

**Use**: Ordered messages with FIFO behavior

```python
# Add message
redis.lpush("session:abc", json.dumps({"role": "user", "content": "..."}))

# Get last 10
messages = redis.lrange("session:abc", 0, 9)

# Trim to 50 messages
redis.ltrim("session:abc", 0, 49)
```

**Why LIST**: O(1) insertion, range queries, automatic ordering

---

### HASH (Workout Details)

**Use**: Store structured data with multiple fields

```python
# Individual workout
redis.hset("workout:2024-10-22:Cycling:161934", mapping={
    "date": "2024-10-22",
    "type": "Cycling",
    "duration_minutes": "45.2",
    "calories": "420"
})

# Aggregations
redis.hset("workout:days", "Friday", "24")
```

**Why HASH**: O(1) field access, atomic updates

---

### ZSET (Date-Sorted Index)

**Use**: Time-series queries

```python
# Add workout with timestamp score
redis.zadd("workout:by_date", {workout_id: timestamp})

# Get workouts in date range
redis.zrangebyscore("workout:by_date", start_ts, end_ts)
```

**Why ZSET**: O(log N) range queries, sorted by timestamp

---

### Vector (RedisVL HNSW)

**Use**: Semantic search over goals/patterns

```python
# Create vector index
index = SearchIndex(schema={
    "index": {"name": "episodic_idx", "prefix": "episodic:"},
    "fields": [
        {"name": "embedding", "type": "vector",
         "attrs": {"dims": 1024, "algorithm": "hnsw"}}
    ]
})

# Store with embedding
redis.hset("episodic:goal:123", mapping={
    "text": "Weight goal is 125 lbs",
    "embedding": embedding_bytes
})

# Vector search
results = index.search(query_vector, top_k=3)
```

**Why HNSW**: Fast approximate nearest neighbor search, O(log N) complexity

---

## 4. Health Data Patterns

### Workout Storage

```python
# Individual workout (HASH)
workout:wellness_user:2024-10-17:Cycling:161934 → HASH

# Aggregations (HASH)
workout:wellness_user:days → {"Friday": "24", "Monday": "18"}

# Date index (ZSET)
workout:wellness_user:by_date → ZSET sorted by timestamp
```

### Sleep Storage

```python
# Daily sleep summary (HASH)
sleep:wellness_user:2024-10-17 → {
    "total_hours": "7.2",
    "efficiency": "0.92"
}
```

---

## 5. Memory Patterns

### Short-Term (LangGraph Checkpointing)

```python
# Automatic via AsyncRedisSaver
langgraph:checkpoint:{session_id}:{step} → Serialized state
```

### Episodic (RedisVL Vector)

```python
# Goal with vector embedding
episodic:wellness_user:goal:1729962000 → {
    "text": "Weight goal 125 lbs",
    "embedding": <bytes>,
    "metadata": {...}
}
```

### Procedural (RedisVL Vector)

```python
# Workflow pattern with embedding
procedural:pattern:1729962000 → {
    "query": "compare activity",
    "tools_used": ["get_workout_data"],
    "embedding": <bytes>
}
```

---

## 6. Related Documentation

- **[10_MEMORY_ARCHITECTURE.md](10_MEMORY_ARCHITECTURE.md)** - Memory types
- **[12_LANGGRAPH_CHECKPOINTING.md](12_LANGGRAPH_CHECKPOINTING.md)** - Checkpointing deep dive
- **[04_STATEFUL_AGENT.md](04_STATEFUL_AGENT.md)** - How agent uses Redis
- **[07_APPLE_HEALTH_PIPELINE.md](07_APPLE_HEALTH_PIPELINE.md)** - Data import patterns

---

**Key takeaway:** Redis provides five data structures (STRING, LIST, HASH, ZSET, Vector) that together enable fast health data storage, conversation history, and semantic memory search - all in one in-memory system.
