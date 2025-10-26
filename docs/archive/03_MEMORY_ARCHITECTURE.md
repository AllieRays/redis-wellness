# Memory Architecture for AI Agents

**Teaching Goal:** Understand why agents need memory, which types work for short conversations, and how to implement them with Redis.

## The Problem: Agents Without Memory

Imagine asking a doctor:

```
You: "What was my weight last week?"
Doctor: "150 lbs"

You: "Is that good?"
Doctor: "Is what good? I don't know what you're referring to."
```

This is what happens when AI agents have no memory. Each message is processed in isolation. The agent can't answer "Is that good?" because it doesn't remember discussing weight 5 seconds ago.

**The stateless agent problem:**
- Can't answer follow-up questions ("How about last month?")
- Can't resolve pronouns ("Is **that** good?")
- Can't reference previous context ("Why did you say **that**?")
- Feels robotic and frustrating to users

## Memory Types We Implemented (and Why)

We use the **CoALA framework** (Cognitive Architecture for Language Agents) which defines 4 memory types. But we only implemented 2 - here's why:

### 1. Short-Term Memory: Conversation State (IMPLEMENTED ✅)

**What it is:** The immediate conversation history - the last 5-10 messages.

**Why it's critical:** Without this, agents can't:
- Answer follow-up questions
- Understand pronouns ("it", "that", "them")
- Maintain conversation flow

**Redis Pattern: LIST**

```python
# Store conversation as Redis LIST
# Key: user:wellness_user:session:abc123:conversation
# Structure: LPUSH (newest first)

redis_client.lpush(
    "user:wellness_user:session:abc123:conversation",
    json.dumps({
        "role": "user",
        "content": "What's my weight?",
        "timestamp": "2025-10-25T10:30:00Z"
    })
)

# Retrieve last 10 messages (most recent first)
history = redis_client.lrange(
    "user:wellness_user:session:abc123:conversation",
    0, 9  # 0-indexed, inclusive
)
```

**Why Redis LIST?**
- O(1) insertion at head (`LPUSH`)
- O(1) retrieval by range (`LRANGE`)
- Natural FIFO ordering (newest first)
- Built-in support for limiting size (`LTRIM`)

**TTL Strategy:**
```python
# Set 7-month expiration on conversation keys
ttl_seconds = 210 * 24 * 60 * 60  # ~6 months
redis_client.expire(session_key, ttl_seconds)
```

**Code Walkthrough: LangGraph Checkpointing**

We use **LangGraph's AsyncRedisSaver** instead of manual LIST management. This gives us:
- Automatic conversation persistence
- Thread-based isolation (one conversation per session)
- Built-in serialization

From `/Users/allierays/Sites/redis-wellness/backend/src/services/redis_connection.py`:

```python
async def get_checkpointer(self):
    """
    Get LangGraph checkpointer using Redis for persistence.

    Uses Redis-based storage so conversations persist across restarts.
    """
    if self._checkpointer:
        return self._checkpointer

    # Build Redis connection URL
    redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

    # Direct initialization - connection stays open for agent lifetime
    self._checkpointer = AsyncRedisSaver(redis_url=redis_url)
    await self._checkpointer.asetup()

    return self._checkpointer
```

**How the agent uses it** (`/Users/allierays/Sites/redis-wellness/backend/src/agents/stateful_rag_agent.py`):

```python
class StatefulRAGAgent:
    def __init__(self, checkpointer: BaseCheckpointSaver):
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(MemoryState)
        # Add nodes: retrieve_memory → llm → tools → store_memory
        return workflow.compile(checkpointer=self.checkpointer)

    async def chat(self, message: str, session_id: str):
        # Checkpointer automatically loads/saves conversation history
        config = {"configurable": {"thread_id": session_id}}
        final_state = await self.graph.ainvoke(input_state, config)
        return final_state
```

**Key insight:** We don't manually manage conversation history. LangGraph's checkpointer handles:
- Loading previous messages when the graph starts
- Saving new messages after each turn
- Thread isolation (sessions don't interfere)

### 2. Procedural Memory: Learned Tool Patterns (IMPLEMENTED ✅)

**What it is:** Memory of **how** to accomplish tasks. "When users ask about weight trends, use these 3 tools in this order."

**Why it's valuable:** Agents learn from experience:
- "Last time I answered this question, I used tools X, Y, Z - that worked well"
- "For weight analysis queries, I typically need search + aggregate + trends tools"
- Improves tool selection accuracy over time

**Redis Pattern: RedisVL HNSW Vector Index**

```python
# Schema for procedural memory
schema = {
    "index": {
        "name": "procedural_memory_idx",
        "prefix": "procedural:",
    },
    "fields": [
        {"name": "query_type", "type": "tag"},  # "weight_analysis", "workout_analysis"
        {"name": "query_description", "type": "text"},
        {"name": "tools_used", "type": "text"},  # JSON list
        {"name": "success_score", "type": "numeric"},
        {"name": "execution_time_ms", "type": "numeric"},
        {
            "name": "embedding",
            "type": "vector",
            "attrs": {
                "dims": 1024,  # mxbai-embed-large
                "distance_metric": "cosine",
                "algorithm": "hnsw",  # Hierarchical Navigable Small World
            }
        }
    ]
}
```

**How it works:**

1. **Store successful workflows** (after agent completes a task):
```python
async def store_pattern(
    query: str,
    tools_used: list[str],
    success_score: float,
    execution_time_ms: int
):
    # Generate embedding for semantic search
    query_description = f"{query_type}: {query}"
    embedding = await embedding_service.generate_embedding(query_description)

    # Store pattern with embedding
    pattern_data = {
        "query_type": "weight_analysis",
        "query_description": "Analyze my weight trends over time",
        "tools_used": json.dumps([
            "search_health_records_by_metric",
            "aggregate_metrics",
            "calculate_weight_trends_tool"
        ]),
        "success_score": 0.95,
        "execution_time_ms": 1250,
        "embedding": np.array(embedding, dtype=np.float32).tobytes()
    }

    redis_client.hset(pattern_key, mapping=pattern_data)
```

2. **Retrieve similar patterns** (when new query arrives):
```python
async def retrieve_patterns(query: str, top_k: int = 3):
    # Generate embedding for incoming query
    query_embedding = await embedding_service.generate_embedding(query)

    # Vector search for similar past workflows
    vector_query = VectorQuery(
        vector=query_embedding,
        vector_field_name="embedding",
        num_results=top_k,
        return_fields=["query_type", "tools_used", "success_score"]
    )

    results = procedural_index.query(vector_query)

    # Extract tool sequences from top matches
    patterns = []
    for result in results:
        patterns.append({
            "tools_used": json.loads(result["tools_used"]),
            "success_score": float(result["success_score"])
        })

    return patterns
```

3. **Create execution plan** (suggest tools to LLM):
```python
def plan_tool_sequence(query: str, past_patterns: list[dict]) -> dict:
    if past_patterns:
        # Use most successful pattern
        best_pattern = max(past_patterns, key=lambda p: p["success_score"])
        return {
            "suggested_tools": best_pattern["tools_used"],
            "reasoning": f"Based on previous successful workflow",
            "confidence": best_pattern["success_score"]
        }

    # Fallback to defaults
    return {
        "suggested_tools": ["search_health_records_by_metric"],
        "confidence": 0.3
    }
```

**Code Walkthrough:** `/Users/allierays/Sites/redis-wellness/backend/src/services/procedural_memory_manager.py`

The manager has 3 main responsibilities:

```python
class ProceduralMemoryManager:
    """Stores and retrieves successful tool-calling patterns."""

    async def store_pattern(self, query, tools_used, success_score, execution_time_ms):
        """Store a successful workflow after agent completes task."""
        # Only store if success_score >= 0.7
        # Generate embedding, save to Redis with 7-month TTL

    async def retrieve_patterns(self, query, top_k=3):
        """Find similar successful patterns via vector search."""
        # Generate query embedding
        # Search procedural_memory_idx
        # Return top-k most similar patterns

    def evaluate_workflow(self, tools_used, tool_results, response_generated, execution_time_ms):
        """Evaluate if workflow was successful and should be stored."""
        # Check: tools were called, no errors, response generated, fast execution
        # Return success_score (0.0 to 1.0)
```

**Why HNSW for procedural memory?**
- **Fast semantic search:** Find "similar enough" queries in O(log N)
- **Handles typos/variations:** "weight trend" matches "analyze weight pattern"
- **Learns from experience:** More successful patterns = better future performance

### 3. Episodic Memory: NOT IMPLEMENTED (Too Sparse ❌)

**What it would be:** Specific past events. "User mentioned their weight goal is 125 lbs on October 10th."

**Why we DON'T use it:** For short-lived health conversations, episodic memory is too sparse:
- Most conversations are 3-5 messages (weight check, workout query)
- Not enough "episodes" to make semantic search useful
- Better handled by short-term memory (conversation history)

**When you WOULD use it:** Long-term applications where users return over months:
- "User injured their knee in March 2024"
- "User set a marathon goal in January"
- "User mentioned they're vegetarian"

For this demo, we focus on **immediate conversations**, not long-term user profiles.

### 4. Semantic Memory: Tool Data (Special Case ✅)

**What it is:** Factual knowledge - in our case, the health data itself.

**Implementation:** We don't store this as "memory" - it's the **source data** the tools query.

```python
# Health data stored as Redis STRING (JSON blob)
# Key: user:wellness_user:health_data
{
    "metrics_summary": {
        "BodyMass": {"latest_value": 70, "unit": "kg", "count": 245}
    },
    "metrics_records": {
        "BodyMass": [
            {"date": "2024-10-22", "value": 70.2, "unit": "kg"},
            {"date": "2024-10-21", "value": 70.0, "unit": "kg"}
        ]
    }
}
```

**Why not RedisVL for health data?**
- Health metrics are **structured and time-series** (better suited for Redis HASH/ZSET)
- We need exact matches, not semantic search ("weight on Oct 22" = exact date lookup)
- Workout data uses specialized indexes (see `05_REDIS_PATTERNS.md`)

## What Doesn't Work: Lessons Learned

### ❌ Over-Engineering Memory

**What we tried:** Full CoALA implementation with all 4 memory types.

**What we learned:**
- **Episodic memory was empty** - not enough conversation history to populate
- **Semantic memory was redundant** - health data is already the "semantic" layer
- **Added complexity without value** - more code to maintain, minimal benefit

**The fix:** Simplified to 2 memory types that actually matter for short conversations.

### ❌ Storing Everything

**What we tried:** Store every single message exchange in semantic memory.

**What we learned:**
- Vector search doesn't help for "show me our last conversation" (use LIST for that)
- Embeddings are expensive (compute + storage)
- Most queries need **exact** history, not "similar" conversations

**The fix:** Use checkpointing (LIST) for exact history, vector search only for learned patterns.

### ❌ Complex TTL Strategies

**What we tried:** Different TTLs for different memory types, sliding windows, manual cleanup.

**What we learned:**
- Simple is better: 7 months for everything
- Redis handles TTL expiration automatically
- Over-optimization wastes development time

**The fix:** One TTL constant, applied consistently.

## Memory Architecture Diagram

```
User Query: "What's my weight?"
        ↓
┌───────────────────────────────────────────────────────┐
│ 1. RETRIEVE SHORT-TERM MEMORY (Checkpointer)         │
│    - Load last 10 messages from Redis                │
│    - Inject into LLM context                          │
└───────────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────────┐
│ 2. RETRIEVE PROCEDURAL MEMORY (Optional)              │
│    - Generate query embedding                         │
│    - Search for similar past workflows                │
│    - Suggest tool sequence to LLM                     │
└───────────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────────┐
│ 3. LLM PROCESSES (with both memories)                 │
│    - Sees conversation history                        │
│    - Sees suggested tools (if available)              │
│    - Decides which tools to call                      │
└───────────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────────┐
│ 4. TOOLS EXECUTE (Semantic data access)               │
│    - Query health data from Redis                     │
│    - Return structured results                        │
└───────────────────────────────────────────────────────┘
        ↓
┌───────────────────────────────────────────────────────┐
│ 5. STORE MEMORIES                                     │
│    - Checkpointer saves new messages (automatic)      │
│    - Procedural memory evaluates workflow success     │
│    - If successful, store pattern for future use      │
└───────────────────────────────────────────────────────┘
```

## Key Takeaways

1. **Short-term memory is non-negotiable** - Without conversation history, agents feel broken
2. **Procedural memory improves over time** - Agents learn which tools work best for which queries
3. **Episodic memory needs scale** - Only valuable with months/years of user history
4. **Semantic memory ≠ vector search** - Structured data often needs exact lookups
5. **Simple TTL wins** - 7 months for everything, let Redis handle expiration

## Next Steps

- **04_AUTONOMOUS_AGENTS.md** - How agents select and chain tools autonomously
- **05_REDIS_PATTERNS.md** - Deep dive into Redis data structures for AI workloads
- **06_ARCHITECTURE_DECISIONS.md** - Why we chose Redis, LangGraph, Qwen, and Ollama
