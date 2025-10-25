# Backend Services Architecture

This document explains the 11 backend services that power the Redis Wellness demo.

## Service Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Chat Layer                            │
├──────────────────────┬──────────────────────────────────────┤
│  stateless_chat.py   │  redis_chat.py                       │
│  (No Memory)         │  (Memory Coordinator)                │
└──────────────────────┴──────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Memory Coordinator                         │
│               memory_coordinator.py                          │
├──────────────────────┬────────────────┬─────────────────────┤
│  Short-term Memory   │  Procedural    │  Semantic Memory    │
│  (Conversation)      │  (Patterns)    │  (Long-term)        │
└──────────────────────┴────────────────┴─────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Redis Layer                               │
├──────────────────────┬──────────────────────────────────────┤
│  redis_connection.py │  redis_apple_health_manager.py       │
│  (Core Connection)   │  redis_workout_indexer.py            │
└──────────────────────┴──────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Support Services                           │
│               embedding_service.py                           │
└─────────────────────────────────────────────────────────────┘
```

## 1. Chat Services (User-Facing)

### stateless_chat.py
**Purpose:** Stateless chat agent with no memory between messages.

**What it does:**
- Receives user messages
- Calls LLM directly with no conversation history
- Has access to all 9 health tools
- Returns responses without context awareness

**Use case:** Demonstrates what AI agents are like WITHOUT memory.

**Key methods:**
- `stream_chat()` - Streams responses to the user

**Dependencies:**
- Ollama LLM only (no Redis)

---

### redis_chat.py
**Purpose:** Stateful chat agent with Redis-powered memory.

**What it does:**
- Stores conversation history in Redis LIST
- Retrieves relevant context from procedural memory
- Coordinates with memory managers for context-aware responses
- Manages conversation sessions

**Use case:** Demonstrates intelligent agents WITH memory.

**Key methods:**
- `stream_chat()` - Streams responses with memory context
- `clear_session()` - Resets conversation history

**Dependencies:**
- Redis (via memory managers)
- Ollama LLM
- Memory coordinator (short-term + procedural memory)

---

## 2. Memory Services (Intelligence Layer)

### memory_coordinator.py
**Purpose:** Orchestrates all memory types for the stateful agent.

**What it does:**
- Coordinates 4 memory types: short-term, procedural, semantic, episodic
- Retrieves relevant memories before LLM calls
- Stores new memories after LLM responses
- Provides unified memory interface to chat layer

**Memory types managed:**
- **Short-term:** Recent conversation turns (Redis LIST)
- **Procedural:** Learned query→tool patterns (RedisVL Vector Index)
- **Semantic:** Long-term facts (RedisVL Vector Index) - currently minimal usage
- **Episodic:** Significant events (Redis HASH) - currently minimal usage

**Key methods:**
- `retrieve_memories()` - Fetches relevant context for a query
- `store_memories()` - Saves new memories after agent response
- `get_memory_stats()` - Returns memory usage statistics

**Dependencies:**
- All 4 memory manager services
- Redis connection service

---

### short_term_memory_manager.py
**Purpose:** Manages recent conversation history (last 10 turns).

**What it does:**
- Stores conversation in Redis LIST (FIFO queue)
- Retrieves last N conversation turns for context
- Automatically trims old messages to prevent context overflow
- Provides "working memory" for the agent

**Redis pattern:** LIST (conversation_history:{session_id})

**Key methods:**
- `get_recent_memory()` - Retrieves last 10 turns
- `store_user_message()` - Adds user message to history
- `store_assistant_message()` - Adds assistant message to history
- `clear_memory()` - Resets conversation

**Why it matters:** Without this, the agent forgets what you just said.

---

### procedural_memory_manager.py
**Purpose:** Learns which tools work for which queries over time.

**What it does:**
- Stores query→tool patterns as embeddings in RedisVL Vector Index
- Suggests relevant tools based on semantic similarity to past queries
- Records successful tool calls for future pattern matching
- Improves agent efficiency by learning from experience

**Redis pattern:** RedisVL HNSW Vector Index (procedural_memory_{session_id})

**Key methods:**
- `suggest_procedure()` - Returns tools that worked for similar queries
- `record_procedure()` - Saves a new query→tool pattern
- `get_procedure_stats()` - Returns learning statistics
- `clear_procedures()` - Resets procedural memory

**Why it matters:** Agent learns "when I see query X, tool Y usually works."

**Example:**
```
Query: "How many workouts do I have?"
→ Suggests: search_workouts tool (learned from past success)
```

---

### semantic_memory_manager.py
**Purpose:** Long-term memory for facts and knowledge.

**What it does:**
- Stores important facts extracted from conversations
- Uses RedisVL Vector Index for semantic search
- Retrieves relevant facts when similar topics arise
- Designed for multi-session memory (future enhancement)

**Redis pattern:** RedisVL HNSW Vector Index (semantic_memory_{session_id})

**Key methods:**
- `retrieve_semantic_memories()` - Finds relevant facts by similarity
- `store_semantic_memory()` - Saves a new fact
- `clear_semantic_memories()` - Resets long-term memory

**Current usage:** Minimal (short conversations don't accumulate much)

**Future potential:** Multi-session memory ("Remember last week we discussed...")

---

### episodic_memory_manager.py
**Purpose:** Stores significant events and milestones.

**What it does:**
- Records important conversation events (first question, tool failures, etc.)
- Provides context about conversation flow
- Helps agent understand conversation history beyond raw messages
- Designed for richer context (future enhancement)

**Redis pattern:** HASH (episodic_memory:{session_id}:{event_id})

**Key methods:**
- `retrieve_episodic_memories()` - Fetches significant events
- `store_episodic_event()` - Records a new event
- `clear_episodic_memories()` - Resets event history

**Event types:**
- FIRST_QUESTION - Start of conversation
- TOOL_CALL - Tools used
- ERROR - Problems encountered
- MILESTONE - Significant moments

**Current usage:** Minimal (basic event tracking)

**Future potential:** Richer conversation context ("You've asked about workouts 3 times")

---

## 3. Redis Services (Data Layer)

### redis_connection.py
**Purpose:** Manages Redis connection lifecycle and singleton pattern.

**What it does:**
- Creates and maintains Redis client connection
- Implements singleton pattern (one connection per application)
- Handles connection errors gracefully
- Provides health checks

**Key methods:**
- `get_redis_manager()` - Returns singleton Redis client
- `get_redis_client()` - Returns raw Redis connection
- `health_check()` - Verifies Redis is reachable
- `close()` - Cleanly closes connection

**Why singleton matters:** Prevents connection pool exhaustion.

---

### redis_apple_health_manager.py
**Purpose:** Manages health records and metrics data in Redis.

**What it does:**
- Stores Apple Health records in Redis HASH
- Provides CRUD operations for health records
- Retrieves heart rate, steps, sleep, and other metrics
- Supports date range queries

**Redis patterns:**
- HASH: `health_record:{record_id}` - Individual records
- SET: `user:{user_id}:health_records` - User's record IDs
- SORTED SET: `health_records:by_date` - Date-based lookups

**Key methods:**
- `store_health_record()` - Saves a new health record
- `get_health_records_by_type()` - Fetches specific metric type
- `get_health_records_in_range()` - Date range queries
- `get_latest_metric()` - Most recent value for a metric

**Use case:** Powers the 6 health metric tools (heart rate, steps, etc.)

---

### redis_workout_indexer.py
**Purpose:** Indexes workout data for fast semantic search.

**What it does:**
- Creates RedisVL HNSW Vector Index for workout search
- Generates embeddings for workout metadata
- Supports semantic queries ("cycling workouts last week")
- Optimized for fast retrieval (50-100x faster than scanning)

**Redis pattern:** RedisVL HNSW Vector Index (workout_index)

**Key methods:**
- `create_index()` - Builds vector index from workout data
- `semantic_search()` - Finds workouts by similarity
- `get_workout_by_id()` - Direct workout lookup
- `delete_index()` - Removes index

**Why it matters:** Enables natural language workout queries.

**Performance:**
- Vector search: ~10-50ms
- Naive scanning: 500-5000ms

---

## 4. Support Services

### embedding_service.py
**Purpose:** Generates text embeddings for semantic search.

**What it does:**
- Converts text to vector embeddings using Ollama
- Supports `mxbai-embed-large` model (1024 dimensions)
- Caches embeddings to reduce computation
- Used by all vector-based memory services

**Key methods:**
- `get_embedding()` - Generates embedding for a text string

**Dependencies:**
- Ollama (mxbai-embed-large model)

**Why it matters:** All semantic/vector search depends on embeddings.

---

## Service Dependency Graph

```
stateless_chat.py
    └── Ollama LLM (no Redis)

redis_chat.py
    ├── memory_coordinator.py
    │   ├── short_term_memory_manager.py
    │   │   └── redis_connection.py
    │   ├── procedural_memory_manager.py
    │   │   ├── redis_connection.py
    │   │   └── embedding_service.py
    │   ├── semantic_memory_manager.py
    │   │   ├── redis_connection.py
    │   │   └── embedding_service.py
    │   └── episodic_memory_manager.py
    │       └── redis_connection.py
    └── Ollama LLM

All Health Tools
    ├── redis_apple_health_manager.py
    │   └── redis_connection.py
    └── redis_workout_indexer.py
        ├── redis_connection.py
        └── embedding_service.py
```

---

## Key Design Patterns

### 1. Singleton Pattern
**Services:** `redis_connection.py`

**Why:** Prevents connection pool exhaustion. One Redis client per application.

```python
_redis_manager: Optional[RedisManager] = None

def get_redis_manager() -> RedisManager:
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager
```

### 2. Manager Pattern
**Services:** All memory managers

**Why:** Encapsulates memory operations, provides clean API, separates concerns.

Each manager has:
- `retrieve_*()` - Get memories
- `store_*()` - Save memories
- `clear_*()` - Reset memories
- `get_*_stats()` - Metrics

### 3. Coordinator Pattern
**Services:** `memory_coordinator.py`

**Why:** Orchestrates multiple memory types, provides unified interface, simplifies chat layer.

Coordinates:
- Memory retrieval (parallel)
- Memory storage (after response)
- Memory statistics (aggregated)

### 4. Streaming Pattern
**Services:** `stateless_chat.py`, `redis_chat.py`

**Why:** Real-time user feedback, better UX for long responses.

Uses Server-Sent Events (SSE) to stream:
- Token-by-token text
- Tool calls in real-time
- Memory stats after response

---

## Performance Characteristics

| Service | Latency | Scaling Factor |
|---------|---------|----------------|
| **stateless_chat** | ~2-5s | LLM inference only |
| **redis_chat** | ~3-6s | LLM + memory retrieval |
| **short_term_memory** | <10ms | Redis LIST ops |
| **procedural_memory** | ~20-50ms | Vector search (HNSW) |
| **semantic_memory** | ~20-50ms | Vector search (HNSW) |
| **episodic_memory** | <10ms | Redis HASH ops |
| **redis_apple_health** | <10ms | Redis HASH/SET ops |
| **redis_workout_indexer** | ~10-50ms | Vector search (HNSW) |
| **embedding_service** | ~100-200ms | Ollama embedding generation |

---

## Memory Usage Statistics

From the UI, you can see real-time memory stats:

- **Short-term memory** - Number of conversation turns stored
- **Procedural patterns** - Number of query→tool patterns learned
- **Token count** - Total tokens in context (including memory)
- **Token usage %** - Percentage of context window used

---

## Next Steps

- [03_MEMORY_ARCHITECTURE.md](./03_MEMORY_ARCHITECTURE.md) - Deep dive into memory patterns
- [04_AUTONOMOUS_AGENTS.md](./04_AUTONOMOUS_AGENTS.md) - How tool calling works
- [05_REDIS_PATTERNS.md](./05_REDIS_PATTERNS.md) - Redis data structure patterns
- [06_ARCHITECTURE_DECISIONS.md](./06_ARCHITECTURE_DECISIONS.md) - Why we made each choice
