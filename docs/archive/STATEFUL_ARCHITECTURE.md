# Stateful Architecture: LangGraph + Redis/RedisVL

## Overview

The stateful RAG agent uses a **dual-layer state persistence architecture**:

1. **LangGraph Checkpointer**: Workflow state persistence (agent reasoning, tool calls)
2. **Redis + RedisVL**: Memory system (conversation history, semantic search)

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Stateful RAG Agent                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  LangGraph Workflow (with MemorySaver)             │    │
│  │  • Multi-turn reasoning state                       │    │
│  │  • Tool execution history                           │    │
│  │  • Conditional routing decisions                    │    │
│  │  • Thread-based state (thread_id = session_id)     │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↕                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Redis/RedisVL Memory System                        │    │
│  │  • Short-term: Conversation history (Redis LIST)    │    │
│  │  • Long-term: Semantic memory (RedisVL HNSW)       │    │
│  │  • 7-month TTL for automatic cleanup                │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Layer 1: LangGraph Checkpointer

### Purpose
Persist **workflow execution state** across invocations within a conversation thread.

### Implementation
```python
from langgraph.checkpoint.memory import MemorySaver

# Initialize checkpointer
self.checkpointer = MemorySaver()

# Compile workflow with checkpointer
self.app = workflow.compile(checkpointer=self.checkpointer)

# Invoke with thread_id for state persistence
config = {"configurable": {"thread_id": session_id}}
final_state = await self.app.ainvoke(initial_state, config=config)
```

### What It Stores
- **Agent reasoning state**: Current position in agent-tools loop
- **Tool call history**: Which tools were called, what they returned
- **Conditional routing decisions**: Whether to continue or end workflow
- **Message accumulation**: `add_messages` reducer maintains conversation flow

### Benefits
- ✅ **Automatic state recovery**: Resume multi-turn workflows seamlessly
- ✅ **Tool call deduplication**: Avoid re-calling tools in same thread
- ✅ **Workflow debugging**: Inspect state at any checkpoint
- ✅ **Thread isolation**: Each session_id gets independent state

### Limitations
- ⚠️ **In-memory only**: State lost on process restart (MemorySaver limitation)
- ⚠️ **Not cross-session**: Each thread is independent

## Layer 2: Redis + RedisVL Memory

### Purpose
Persist **conversation content and semantic insights** for long-term retrieval.

### Implementation

#### Short-term Memory (Redis LIST)
```python
# Store message
redis_client.lpush(f"health_chat_session:{session_id}", json.dumps(message_data))
redis_client.expire(session_key, 7_months_in_seconds)

# Retrieve recent context
messages = redis_client.lrange(session_key, 0, 9)  # Last 10 messages
```

#### Long-term Memory (RedisVL Vector Search)
```python
# Initialize semantic index (HNSW)
schema = IndexSchema.from_dict({
    "index": {"name": "semantic_memory_idx", "prefix": "memory:semantic:"},
    "fields": [
        {"name": "user_id", "type": "tag"},
        {"name": "embedding", "type": "vector", "attrs": {
            "dims": 1024,  # mxbai-embed-large
            "distance_metric": "cosine",
            "algorithm": "hnsw"
        }}
    ]
})

# Store semantic memory
embedding = await generate_embedding(combined_text)
redis_client.hset(memory_key, mapping={
    "user_message": user_message,
    "assistant_response": assistant_response,
    "embedding": np.array(embedding).tobytes()
})

# Semantic search
vector_query = VectorQuery(
    vector=query_embedding,
    vector_field_name="embedding",
    num_results=3
)
results = semantic_index.query(vector_query)
```

### What It Stores
- **Short-term (Redis LIST)**:
  - Last 10 conversation messages (chronological)
  - Role, content, timestamp for each message
  - Fast retrieval for recent context

- **Long-term (RedisVL HNSW)**:
  - Semantic embeddings of Q&A pairs
  - Vector search across all conversations
  - User-scoped memory (filtered by user_id)

### Benefits
- ✅ **Persistent across restarts**: Survives process/container restarts
- ✅ **Cross-session insights**: "What were my fitness goals?" works months later
- ✅ **Semantic retrieval**: Find relevant past conversations by meaning
- ✅ **Automatic cleanup**: 7-month TTL prevents unbounded growth

## How They Work Together

### Single-Turn Query Flow
```
User: "What was my average heart rate last week?"

1. LangGraph Checkpointer:
   └─ Load thread state (empty for first message)

2. Redis Memory:
   ├─ Short-term: Fetch last 10 messages (context)
   └─ Long-term: Semantic search for "heart rate" insights

3. Agent Node:
   └─ Inject memory into system prompt
   └─ LLM generates response with tool calls

4. Tool Node:
   └─ Execute query_health_metrics tool

5. Agent Node:
   └─ LLM formats final response

6. Storage:
   ├─ LangGraph: Save workflow state (tool results, messages)
   └─ Redis: Store Q&A in both short + long-term memory
```

### Multi-Turn Follow-Up Flow
```
User: "Is that good for my age?"

1. LangGraph Checkpointer:
   └─ Resume thread state (knows "87 bpm" from previous tool call)

2. Redis Memory:
   ├─ Short-term: "User: What was my average heart rate?"
   │              "Assistant: Your average heart rate was 87 bpm..."
   └─ Long-term: Previous health insights

3. Agent Node:
   └─ Understands "that" = 87 bpm (from thread state + short-term memory)
   └─ No need to re-query data

4. Final Response:
   └─ "87 bpm is within the normal range for adults..."
```

## Why Both Layers?

| Feature | LangGraph Checkpointer | Redis/RedisVL |
|---------|------------------------|---------------|
| **Purpose** | Workflow state | Conversation memory |
| **Scope** | Single conversation thread | Cross-session insights |
| **Persistence** | In-memory (process lifetime) | Disk (7 months) |
| **Best For** | Multi-turn reasoning | Semantic retrieval |
| **State Type** | Agent/tool execution state | User messages + responses |
| **Search** | ❌ No search | ✅ Vector search |

### Complementary Strengths

1. **LangGraph**: Tracks what the agent is *doing* (tool calls, routing)
2. **Redis**: Tracks what the agent *knows* (conversation history, insights)

### Example: Why You Need Both

**Scenario**: User asks "What's my BMI?" then "How does it compare to last month?"

**LangGraph Checkpointer**:
- Remembers tool call results from current conversation
- Knows BMI tool was already called (no re-execution)
- Maintains agent reasoning state

**Redis Memory**:
- Short-term: "User asked about BMI, got 24.5"
- Long-term: Finds similar BMI questions from last month via semantic search
- Provides historical context: "Last month your BMI was 25.1"

## Configuration

### LangGraph Thread Management
```python
# Use session_id as thread_id for natural grouping
config = {"configurable": {"thread_id": session_id}}
final_state = await self.app.ainvoke(initial_state, config=config)
```

### Redis Memory TTL
```python
# 7-month TTL for health data retention
memory_ttl = 7 * 30 * 24 * 60 * 60  # seconds
redis_client.expire(key, memory_ttl)
```

### RedisVL Vector Index
```python
# HNSW parameters
{
    "dims": 1024,              # mxbai-embed-large dimension
    "distance_metric": "cosine",
    "algorithm": "hnsw",       # Fast approximate search
    "datatype": "float32"
}
```

## Production Considerations

### Current Limitations

1. **MemorySaver is in-memory**: LangGraph state lost on restart
2. **No Redis-based checkpointer**: Future enhancement opportunity

### Future Enhancements

**Option 1: Redis-based LangGraph Checkpointer**
```python
# Custom Redis checkpointer (not implemented yet)
from langgraph.checkpoint.redis import RedisCheckpointer

checkpointer = RedisCheckpointer(
    redis_client=redis_client,
    ttl=7 * 30 * 24 * 60 * 60
)
```

**Option 2: Keep Dual System**
- LangGraph for transient workflow state (MemorySaver is fine)
- Redis for persistent memory (already production-ready)

### Recommended: Keep Current Architecture

The dual-layer system is **production-ready** because:

1. ✅ **Workflow state is ephemeral by nature**: Multi-turn tool loops complete quickly
2. ✅ **Memory is persistent where it matters**: Redis stores all important data
3. ✅ **Graceful degradation**: Process restart loses workflow state but keeps all memory
4. ✅ **Performance**: In-memory checkpointer is faster than Redis for transient state

## Testing State Persistence

### Test LangGraph Checkpointer
```bash
# Multi-turn conversation in same thread
curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "What was my heart rate?", "session_id": "test123"}'

curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "Is that good?", "session_id": "test123"}'
# Should understand "that" refers to heart rate from previous turn
```

### Test Redis Memory
```bash
# Different sessions, semantic search
curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "My fitness goal is to run 5K", "session_id": "session1"}'

# Later, different session
curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "What are my fitness goals?", "session_id": "session2"}'
# Should retrieve semantic memory from session1
```

## Summary

The stateful RAG agent achieves **true statefulness** through:

1. **LangGraph MemorySaver**: Workflow state persistence within conversation threads
2. **Redis + RedisVL**: Dual memory system (short-term + long-term semantic search)

This architecture provides:
- ✅ Multi-turn reasoning with context awareness
- ✅ Cross-session semantic insights
- ✅ Automatic state cleanup (7-month TTL)
- ✅ Production-ready persistence
- ✅ Graceful degradation on process restart

The agent is now **genuinely stateful** at both the workflow and memory levels.
