# Stateful Agent Architecture

## 1. Overview

The stateful agent demonstrates how **Redis + RedisVL + LangGraph** transform a stateless baseline into an intelligent, context-aware AI system. This is the agent WITH memory.

**Key Point**: This shows what AI agents are capable of when they have memory systems.

### What You'll Learn

- **[Four-Layer Memory System](#2-four-layer-memory-system)** - Short-term, episodic, procedural, semantic memory
- **[Architecture Components](#3-architecture-components)** - LangGraph, Redis, RedisVL, and tools
- **[How It Works](#4-how-it-works)** - Autonomous memory retrieval via tools
- **[Memory Retrieval & Storage](#5-memory-retrieval--storage)** - When and how memory is used
- **[Related Documentation](#6-related-documentation)** - Links to deeper dives

---

## 2. Four-Layer Memory System

The stateful agent uses **four types of memory** inspired by the CoALA (Cognitive Architecture for Language Agents) framework:

### 1️⃣ Short-Term Memory (LangGraph Checkpointing)

**What**: Recent conversation within current session
**Managed by**: LangGraph `AsyncRedisSaver`
**Storage**: Redis checkpoints (`langgraph:checkpoint:*`)
**Enables**: Context awareness, pronoun resolution, follow-up questions

```python
# Conversation history automatically loaded
messages = [
    HumanMessage("What was my heart rate?"),
    AIMessage("72 bpm average"),
    HumanMessage("Is that good?")  # LLM understands context
]
```

### 2️⃣ Episodic Memory (User Goals & Facts)

**What**: Important user-specific facts and goals
**Managed by**: `episodic_memory_manager.py`
**Storage**: RedisVL HNSW vector index (`episodic:*`)
**Retrieved via**: `get_my_goals` tool (LLM-triggered)
**Enables**: Cross-session goal recall

```python
# Stored with vector embeddings
{
    "user_id": "wellness_user",
    "goal": "Weight goal is 125 lbs by December",
    "embedding": <1024-dim vector>,
    "timestamp": 1729962000
}
```

### 3️⃣ Procedural Memory (Workflow Patterns)

**What**: Successful tool-calling sequences and strategies
**Managed by**: `procedural_memory_manager.py`
**Storage**: RedisVL HNSW vector index (`procedural:*`)
**Retrieved via**: `get_tool_suggestions` tool (LLM-triggered)
**Enables**: Workflow optimization via past success

```python
# After successful workflow
{
    "query": "Compare activity this month vs last",
    "tools_used": ["get_workout_data", "get_health_metrics"],
    "success_score": 0.95,
    "embedding": <1024-dim vector>
}
```

### 4️⃣ Semantic Memory (Health Knowledge Base) - Optional

**What**: General health facts and medical knowledge
**Managed by**: `semantic_memory_manager.py`
**Storage**: RedisVL HNSW vector index (`semantic:*`)
**Enables**: Domain knowledge augmentation

---

## 3. Architecture Components

### Full System Diagram

```
User Query
    ↓
Intent Router (pattern matching for fast path)
    ↓
LangGraph StateGraph Workflow
    ↓
┌─────────────────────────────────────┐
│ 1. Load Checkpointer (short-term)  │ ← Redis
│ 2. LLM + 5 Tools (3 health + 2 mem)│ ← Qwen 2.5 7B
│ 3. Execute tools (autonomous)       │ ← Health data + memory
│ 4. Loop (up to recursion limit)     │
│ 5. Reflect on workflow success      │
│ 6. Store episodic memory            │ → RedisVL
│ 7. Store procedural patterns        │ → RedisVL
└─────────────────────────────────────┘
    ↓
Response + Memory Stored
```

### Key Technologies

| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM** | Qwen 2.5 7B via Ollama | Function-calling, autonomous tool selection |
| **Orchestration** | LangGraph StateGraph | Workflow management with recursion |
| **Short-term Memory** | Redis + LangGraph checkpointing | Conversation history (7-month TTL) |
| **Episodic/Procedural** | RedisVL HNSW vector index | Semantic search over goals/patterns |
| **Embeddings** | mxbai-embed-large | 1024-dim vectors for similarity search |
| **Health Data** | Redis hashes + JSON | O(1) lookups for metrics/workouts |

---

## 4. How It Works

### LangGraph Workflow

The stateful agent uses **LangGraph's StateGraph** to orchestrate the workflow:

```python
# From: backend/src/agents/stateful_rag_agent.py

class StatefulRAGAgent:
    def __init__(self, checkpointer, episodic_memory, procedural_memory):
        self.llm = create_health_llm()
        self.checkpointer = checkpointer  # AsyncRedisSaver
        self.episodic = episodic_memory
        self.procedural = procedural_memory
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(MemoryState)

        # Core nodes
        workflow.add_node("llm", self._llm_node)
        workflow.add_node("tools", self._tool_node)

        # Memory storage nodes
        workflow.add_node("reflect", self._reflect_node)
        workflow.add_node("store_episodic", self._store_episodic_node)
        workflow.add_node("store_procedural", self._store_procedural_node)

        # Flow: llm → tools → llm (loop) → reflect → store
        workflow.set_entry_point("llm")
        workflow.add_conditional_edges(
            "llm",
            self._should_continue,
            {"tools": "tools", "end": "reflect"}
        )
        workflow.add_edge("tools", "llm")
        workflow.add_edge("reflect", "store_episodic")
        workflow.add_edge("store_episodic", "store_procedural")
        workflow.add_edge("store_procedural", END)

        return workflow.compile(checkpointer=self.checkpointer)
```

### Autonomous Memory Retrieval

**Key Innovation**: Memory retrieval is **tool-based**, not automatic injection.

The LLM decides when to call memory tools:

```python
# 5 tools available to LLM:

# Health tools (same as stateless)
1. get_health_metrics
2. get_sleep_analysis
3. get_workout_data

# Memory tools (ONLY in stateful)
4. get_my_goals         # Retrieves episodic memory via vector search
5. get_tool_suggestions # Retrieves procedural patterns via vector search
```

**Example: Goal-Based Query**

```
User: "Am I on track for my weight goal?"

LLM reasoning:
1. User mentions "goal" → autonomously calls get_my_goals tool
2. get_my_goals performs RedisVL vector search
3. Returns: {"goal": "125 lbs by December", "metric": "weight"}
4. LLM then calls get_health_metrics for current weight
5. LLM synthesizes comparison: "Your goal is 125 lbs. Current: 136.8 lbs..."
```

---

## 5. Memory Retrieval & Storage

### When Memory is Retrieved (Autonomous)

**LLM decides** when to call memory tools based on query:

| Query Pattern | Tool Called | Memory Type |
|---------------|-------------|-------------|
| "my goal", "target", "on track" | `get_my_goals` | Episodic |
| Similar to past successful queries | `get_tool_suggestions` | Procedural |
| Follow-up questions | *(automatic - checkpointer)* | Short-term |

### When Memory is Stored (Automatic)

**After every response**, the agent automatically stores:

**Episodic Memory** (if conversation contains goals/facts):
```python
async def _store_episodic_node(self, state):
    # Extract facts from conversation
    facts = extract_facts_from_conversation(state["messages"])

    # Store each fact with embedding
    for fact in facts:
        embedding = generate_embedding(fact)
        await self.episodic.store_memory(
            user_id=state["user_id"],
            text=fact,
            embedding=embedding
        )
```

**Procedural Memory** (if workflow was successful):
```python
async def _store_procedural_node(self, state):
    # Evaluate workflow success
    if success_score >= 0.7:
        pattern = {
            "query": user_query,
            "tools_used": tools_used,
            "success_score": success_score,
            "execution_time_ms": duration
        }

        embedding = generate_embedding(pattern["query"])
        await self.procedural.store_pattern(pattern, embedding)
```

### Redis Keys Used

```bash
# Short-term (LangGraph checkpointing)
langgraph:checkpoint:{session_id}:*

# Episodic (goals and facts)
episodic:wellness_user:goal:1729962000

# Procedural (workflow patterns)
procedural:pattern:1729962000

# Health data (read by tools)
health:wellness_user:*
workout:wellness_user:*
sleep:wellness_user:*
```

---

## 6. Related Documentation

- **[STATELESS_AGENT.md](STATELESS_AGENT.md)** - Baseline agent without memory
- **[STATELESS_VS_STATEFUL_COMPARISON.md](STATELESS_VS_STATEFUL_COMPARISON.md)** - Side-by-side comparison
- **[MEMORY_ARCHITECTURE.md](MEMORY_ARCHITECTURE.md)** - Deep dive into memory systems
- **[LANGGRAPH_CHECKPOINTING.md](LANGGRAPH_CHECKPOINTING.md)** - LangGraph state management
- **[REDIS_PATTERNS.md](REDIS_PATTERNS.md)** - Redis data structures for AI
- **[EXAMPLE_QUERIES.md](EXAMPLE_QUERIES.md)** - Try queries to see memory in action

---

**Key takeaway:** Redis + LangGraph transforms stateless chat into an intelligent agent that remembers conversations (checkpointing), recalls goals (episodic memory), learns patterns (procedural memory), and autonomously retrieves context via tools when needed.
