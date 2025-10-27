# Memory System - CoALA Framework

**Last Updated**: October 24, 2024

## Overview

Redis Wellness implements the **CoALA (Cognitive Architectures for Language Agents)** framework using Redis and RedisVL for a production-grade AI agent memory system.

This document explains how the 4-memory-type system works, its Redis implementation, and performance characteristics.

### What is CoALA?

CoALA is a cognitive architecture framework that gives AI agents human-like memory capabilities through four distinct memory types. Based on the paper: https://arxiv.org/pdf/2309.02427

### Redis Implementation

- **Redis Stack** for persistence and data structures
- **RedisVL** for vector search (episodic & semantic memories)
- **Redis Hash** for O(1) procedural lookup
- **Redis List** for conversation history

## Four Memory Types

### 1. Episodic Memory 🎯

**Purpose**: User-specific events, preferences, goals, and personal experiences

**Think of it as**: The agent's personal diary of interactions with YOU

**Examples**:
- "User prefers morning workouts"
- "User's BMI goal is 22"
- "User mentioned knee pain on 2024-10-15"
- "User frequently asks about heart rate zones"

**Redis Implementation**:
```python
# Storage: RedisVL vector index with semantic search
Index: episodic_memory_index
Prefix: episodic:{user_id}:{event_type}:{timestamp}

# Example keys:
episodic:user123:preference:1729756800
episodic:user123:goal:1729843200
episodic:user123:health_event:1729929600

# Fields stored:
{
    "user_id": "user123",
    "event_type": "preference",  # preference, goal, health_event, interaction, milestone
    "timestamp": 1729756800,
    "description": "User prefers morning workouts",
    "context": "Mentioned during conversation about scheduling",
    "metadata": {...},
    "embedding": [0.234, -0.123, ...]  # 1024-dim vector
}
```

**Performance**:
- **Write**: O(log N) - RedisVL HNSW index insertion
- **Search**: O(log N) - Vector similarity search
- **Retrieval**: 10-50ms for top-k results

**Code Location**: `backend/src/services/episodic_memory_manager.py`

---

### 2. Procedural Memory 🔧

**Purpose**: Learned tool sequences and execution patterns (how-to knowledge)

**Think of it as**: The agent's learned skills and best practices

**Examples**:
- "For 'weekly summary' queries → call `aggregate_metrics` then `compare_periods`"
- "When user asks 'am I improving?' → use `trend_analysis` + `progress_tracking`"
- "Workout frequency questions require `search_workouts` then `aggregate_metrics`"

**Redis Implementation**:
```python
# Storage: Redis Hash for O(1) lookup
Key: procedure:{user_id}:{query_hash}

# Example keys:
procedure:user123:a1b2c3d4
procedure:user123:e5f6g7h8

# Fields stored:
{
    "user_id": "user123",
    "query_pattern": "What was my average heart rate last week?",
    "tool_sequence": ["aggregate_metrics", "compare_periods"],
    "execution_count": 12,
    "avg_execution_time_ms": 1250.5,
    "avg_success_score": 0.95,
    "created_at": "2024-10-24T12:00:00Z",
    "last_used": "2024-10-24T14:30:00Z"
}
```

**Learning Algorithm**:
```python
# Confidence increases with:
# 1. Execution count (more uses = more confident)
# 2. Success score (better results = more confident)
confidence = min(avg_success_score * (1 + execution_count / 10), 1.0)

# Recommend if confidence >= 0.7
recommended = confidence >= 0.7
```

**Performance**:
- **Write**: O(1) - Redis Hash set
- **Lookup**: O(1) - Redis Hash get
- **Retrieval**: <1ms average

**Code Location**: `backend/src/services/procedural_memory_manager.py`

---

### 3. Semantic Memory 📚

**Purpose**: General health knowledge and facts (impersonal knowledge base)

**Think of it as**: The agent's encyclopedia of health information

**Examples**:
- "Normal resting heart rate is 60-100 bpm"
- "VO2 max is a measure of cardiovascular fitness"
- "BMI is calculated as weight(kg) / height(m)²"
- "Higher VO2 max correlates with better endurance"

**Redis Implementation**:
```python
# Storage: RedisVL vector index for semantic search
Index: semantic_knowledge_index
Prefix: semantic:{category}:{fact_type}:{timestamp}

# Example keys:
semantic:cardio:guideline:1729756800
semantic:metrics:definition:1729843200
semantic:nutrition:relationship:1729929600

# Fields stored:
{
    "fact_type": "guideline",  # definition, relationship, guideline, general
    "category": "cardio",      # cardio, nutrition, metrics, general
    "timestamp": 1729756800,
    "fact": "Normal resting heart rate is 60-100 bpm",
    "context": "Standard medical guideline for adults",
    "source": "medical_literature",
    "metadata": {...},
    "embedding": [0.123, 0.456, ...]  # 1024-dim vector
}
```

**Performance**:
- **Write**: O(log N) - RedisVL HNSW index insertion
- **Search**: O(log N) - Vector similarity search
- **Retrieval**: 10-50ms for top-k results

**Pre-populated Knowledge**:
- Default health facts loaded on initialization
- Extensible for custom health domains

**Code Location**: `backend/src/services/semantic_memory_manager.py`

---

### 4. Short-Term Memory 📝

**Purpose**: Recent conversation history (working memory)

**Think of it as**: The agent's notepad of what was just said

**Examples**:
- Last 10 messages in conversation
- Enables pronoun resolution ("it", "that", "them")
- Maintains conversation flow

**Redis Implementation**:
```python
# Storage: Redis List (FIFO queue)
Key: health_chat_session:{session_id}

# Example key:
health_chat_session:session_abc123

# Messages stored (prepended for newest-first):
[
    {
        "id": "msg-uuid-1",
        "role": "user",
        "content": "What was my average heart rate last week?",
        "timestamp": "2024-10-24T14:30:00Z"
    },
    {
        "id": "msg-uuid-2",
        "role": "assistant",
        "content": "Your average heart rate last week was 87 bpm.",
        "timestamp": "2024-10-24T14:30:05Z"
    },
    ...
]
```

**Token Management**:
- Automatic trimming to stay within LLM context window (24,000 tokens for Qwen 2.5 7B)
- Threshold: 80% of limit (19,200 tokens)
- Oldest messages trimmed first

**Performance**:
- **Write**: O(1) - Redis LPUSH
- **Read**: O(N) where N = limit (typically 10)
- **Retrieval**: <1ms for 10 messages

**Code Location**: `backend/src/services/short_term_memory_manager.py`

---

## Memory Coordinator

The **Memory Coordinator** orchestrates all 4 memory types for unified AI agent access.

**Code Location**: `backend/src/services/memory_coordinator.py`

### Key Methods

```python
# Retrieve all memory types for context
context = await coordinator.retrieve_all_context(
    session_id="session_123",
    query="What was my workout frequency last month?",
    include_episodic=True,    # User preferences/goals
    include_procedural=True,  # Learned tool patterns
    include_semantic=True,    # General health knowledge
    include_short_term=True   # Conversation history
)

# Store interaction across all memory types
await coordinator.store_interaction(
    session_id="session_123",
    user_message="What was my average heart rate?",
    assistant_response="Your average was 87 bpm...",
    tools_used=["aggregate_metrics"],
    execution_time_ms=1250.5,
    success_score=0.95
)
```

### Memory Context Structure

```python
@dataclass
class MemoryContext:
    # Short-term
    short_term: str | None = None
    short_term_messages: int = 0

    # Episodic
    episodic: str | None = None
    episodic_hits: int = 0

    # Procedural
    procedural: dict | None = None
    procedural_confidence: float = 0.0
    procedural_recommended: bool = False

    # Semantic
    semantic: str | None = None
    semantic_hits: int = 0

    # Metadata
    user_id: str = ""
    session_id: str = ""
    retrieved_at: str = ""
```

---

## Performance Characteristics

### Memory Operation Latency (Average)

| Memory Type | Write | Read | Search | Storage |
|------------|-------|------|--------|---------|
| **Episodic** | 10-20ms | N/A | 10-50ms | RedisVL HNSW |
| **Procedural** | <1ms | <1ms | <1ms | Redis Hash |
| **Semantic** | 10-20ms | N/A | 10-50ms | RedisVL HNSW |
| **Short-Term** | <1ms | <1ms | N/A | Redis List |

### Memory Size & TTL

| Memory Type | Typical Size | TTL | Cleanup |
|------------|-------------|-----|---------|
| **Episodic** | 10-100 events/user | 7 months | Automatic |
| **Procedural** | 5-20 patterns/user | 7 months | Automatic |
| **Semantic** | ~50 facts (pre-populated) | 7 months | Manual |
| **Short-Term** | Last 10 messages | 7 months | Automatic |

---

## Example Memory Flow

### Query: "What was my average heart rate last week?"

**1. Memory Retrieval** (via Memory Coordinator):

```python
# Short-term memory
short_term = "Recent conversation:
User: When did I last work out?
Assistant: 2 days ago - Running, 30 minutes"

# Episodic memory (semantic search)
episodic = "Personal context (2 memories):
1. [2024-10-20] PREFERENCE
   User prefers morning workouts
   Context: Mentioned during scheduling conversation

2. [2024-10-18] GOAL
   User's target heart rate zone is 140-160 bpm
   Context: User wants to improve cardiovascular fitness"

# Procedural memory (pattern lookup)
procedural = {
    "tool_sequence": ["aggregate_metrics"],
    "confidence": 0.85,
    "recommended": True
}

# Semantic memory (health knowledge)
semantic = "Health knowledge (1 fact):
1. [CARDIO] guideline
   Normal resting heart rate is 60-100 bpm
   Lower heart rate generally indicates better fitness"
```

**2. Agent Processing**:
- LLM receives all memory context in system prompt
- Calls `aggregate_metrics` tool (suggested by procedural memory)
- Gets result: "87 bpm average last week"

**3. Memory Storage**:
- **Short-term**: Store user message + assistant response
- **Episodic**: Store if response contains meaningful insight
- **Procedural**: Record tool sequence with success score
- **Semantic**: No update (pre-populated knowledge)

---

## Tool-First Policy

**Important**: For factual data queries, the agent ALWAYS calls tools first, even if semantic memory has relevant information.

**Why?**
- Semantic memory can become stale
- Tools provide current, accurate data
- Memory is for USER CONTEXT, not factual data

**Example**:
```python
# Query: "What was my average heart rate last week?"

# ❌ WRONG: Answer from semantic memory
"Your average was 85 bpm"  # Might be outdated!

# ✅ CORRECT: Call aggregate_metrics tool
tools_used = ["aggregate_metrics"]
result = "87 bpm (current data from Redis indexes)"
```

---

## Redis Key Patterns

### Centralized via RedisKeys Utility

All Redis keys are generated through `backend/src/utils/redis_keys.py` to ensure consistency.

```python
from backend.src.utils.redis_keys import RedisKeys

# Episodic memory
RedisKeys.episodic_memory(user_id, event_type, timestamp)
# → episodic:{user_id}:{event_type}:{timestamp}

# Procedural memory
RedisKeys.procedural_memory(user_id, query_hash)
# → procedure:{user_id}:{query_hash}

# Semantic memory
RedisKeys.semantic_memory(category, fact_type, timestamp)
# → semantic:{category}:{fact_type}:{timestamp}

# Short-term memory
RedisKeys.chat_session(session_id)
# → health_chat_session:{session_id}

# Embedding cache
RedisKeys.embedding_cache(query_hash)
# → embedding_cache:{query_hash}
```

---

## Vector Embeddings

### Model: mxbai-embed-large (Ollama)

- **Dimensions**: 1024
- **Provider**: Ollama (local inference)
- **Performance**: ~200ms per embedding (first time), <1ms (cached)

### Embedding Cache

Embeddings are cached in Redis to avoid expensive recomputation:

```python
# Cache key
embedding_cache:{query_hash}

# TTL: 1 hour

# Cache hit rate: 30-50% in production
```

---

## Memory Statistics

Get memory statistics for monitoring:

```python
stats = await coordinator.get_memory_stats(
    session_id="session_123",
    user_id="user_abc"
)

# Returns:
{
    "short_term": {
        "message_count": 12,
        "ttl_seconds": 18144000  # 7 months
    },
    "episodic": {
        "memory_count": 23
    },
    "procedural": {
        "total_procedures": 8,
        "total_executions": 47,
        "overall_avg_score": 0.92
    },
    "semantic": {
        "note": "Pre-populated knowledge base",
        "available": True
    },
    "user_id": "user_abc",
    "session_id": "session_123"
}
```

---

## Clearing Memories

### Session-Level (Short-term only)

```python
await coordinator.clear_session_memories(session_id="session_123")
```

### User-Level (Episodic, Procedural, Semantic)

```python
await coordinator.clear_user_memories(
    clear_episodic=True,     # Clear user preferences/goals
    clear_procedural=True,   # Clear learned tool patterns
    clear_semantic=False     # Don't clear knowledge base
)
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Memory Coordinator                       │
│         (Unified interface for all memory types)            │
└──────────────┬──────────────────────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┬──────────┐
    │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼
┌─────────┐┌──────────┐┌──────────┐┌──────────┐
│Episodic ││Procedural││Semantic  ││Short-Term│
│Memory   ││Memory    ││Memory    ││Memory    │
│Manager  ││Manager   ││Manager   ││Manager   │
└────┬────┘└────┬─────┘└────┬─────┘└────┬─────┘
     │          │           │           │
     ▼          ▼           ▼           ▼
┌─────────────────────────────────────────────┐
│              Redis Stack                     │
│                                              │
│  RedisVL      Redis Hash   RedisVL    List  │
│  (HNSW)       (O(1))       (HNSW)    (FIFO) │
└─────────────────────────────────────────────┘
```

---

## Best Practices

### 1. When to Use Each Memory Type

- **Episodic**: User says "I prefer...", "My goal is...", "I mentioned..."
- **Procedural**: Track successful tool sequences (automatic)
- **Semantic**: Pre-populated health facts (no per-interaction updates)
- **Short-Term**: All messages (automatic)

### 2. Memory Retrieval Performance

- Always retrieve short-term memory (conversation context)
- Skip episodic/semantic for purely factual queries (tool-first policy)
- Use procedural suggestions to optimize tool selection

### 3. Error Handling

All memory operations use consistent error handling via `MemoryRetrievalError`:

```python
from backend.src.utils.exceptions import MemoryRetrievalError

try:
    context = await coordinator.retrieve_all_context(...)
except MemoryRetrievalError as e:
    logger.error(f"Memory retrieval failed: {e.memory_type} - {e.reason}")
    # Fallback: proceed without memory
```

---

## See Also

- **CoALA Paper**: https://arxiv.org/pdf/2309.02427
- **Redis AI Agents Guide**: https://redis.io/blog/ai-agents-memory/
- **RedisVL Documentation**: https://github.com/RedisVentures/redisvl
- **Architecture Overview**: `docs/03_ARCHITECTURE.md`
- **API Reference**: `docs/09_API.md`
