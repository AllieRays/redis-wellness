# Stateless vs Stateful Agent Comparison

## 1. Overview

Both agents use the same LLM (Qwen 2.5 7B) and same health tools. The only difference is memory.

This doc compares what each agent can do.

### What You'll Learn

- **[Architecture Comparison](#2-architecture-comparison)** - Side-by-side system diagrams
- **[Feature Comparison](#3-feature-comparison)** - What each agent can and cannot do
- **[Tool Comparison](#4-tool-comparison)** - 3 vs 5 tools explained
- **[Performance Comparison](#5-performance-comparison)** - Speed, memory, capabilities
- **[Related Documentation](#6-related-documentation)** - Deep dives into each agent

---

## 2. Architecture Comparison

### Stateless Agent (No Memory)

```mermaid
flowchart TB
    UI["User Interface"]
    Router["Intent Router<br/>(Pre-LLM)<br/>Pattern matching"]

    Simple["Redis<br/>(Simple Queries)"]
    SimpleLoop["Simple Tool Loop<br/>• Qwen 2.5 7B LLM<br/>• Tool calling<br/>• Response synthesis"]

    Tools["Health Tools<br/>(3 tools)"]
    RedisData["Redis Health Data Store"]
    Response["Response to User"]
    Forget["❌ FORGET EVERYTHING"]

    UI --> Router
    Router -->|"Simple"| Simple
    Router -->|"Complex"| SimpleLoop
    Simple --> RedisData
    SimpleLoop --> Tools
    Tools --> RedisData
    RedisData --> Response
    Response --> UI
    Response --> Forget

    style UI fill:#fff,stroke:#6c757d,stroke-width:2px,color:#000
    style Router fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style Simple fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style SimpleLoop fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style Tools fill:#fff,stroke:#333,stroke-width:2px,color:#000
    style RedisData fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Response fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style Forget fill:#fff,stroke:#dc3545,stroke-width:2px,color:#dc3545,stroke-dasharray: 5 5
```

### Stateful Agent (With Memory)

```mermaid
flowchart TB
    UI["User Interface"]
    Router["Intent Router<br/>(Pre-LLM)<br/>Pattern matching"]
    Simple["Redis<br/>(Simple Queries)"]
    Load["1. Load Checkpoint<br/>(conversation history)"]
    LLM["2. Qwen 2.5 7B LLM<br/>(sees history + decides tools)"]
    ToolDecision{"3. More tools?"}
    Tools["4. Execute Tools<br/>(5 total: 3 health + 2 memory)"]
    Reflect["5. Reflect<br/>(evaluate success)"]
    StoreEpi["6. Store Episodic<br/>(goals)"]
    StoreProc["7. Store Procedural<br/>(patterns)"]
    SaveCheck["8. Save Checkpoint<br/>(conversation)"]
    RedisVL["RedisVL<br/>Episodic + Procedural<br/>Vector Search"]
    RedisData["Redis Health Data Store"]
    Response["Response to User"]

    UI --> Router
    Router -->|"Fast path"| Simple
    Router -->|"Complex path<br/>(LangGraph)"| Load
    Simple --> Response
    Load --> LLM
    LLM --> ToolDecision
    ToolDecision -->|Yes| Tools
    ToolDecision -->|No| Reflect
    Tools --> LLM
    Reflect --> StoreEpi
    StoreEpi --> StoreProc
    StoreProc --> SaveCheck
    Tools <--> RedisVL
    Tools <--> RedisData
    SaveCheck --> Response
    Response --> UI

    style UI fill:#fff,stroke:#6c757d,stroke-width:2px,color:#000
    style Router fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style Simple fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Load fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style LLM fill:#fff,stroke:#333,stroke-width:2px,color:#000
    style ToolDecision fill:#fff,stroke:#333,stroke-width:2px,color:#000
    style Tools fill:#fff,stroke:#333,stroke-width:2px,color:#000
    style Reflect fill:#fff,stroke:#333,stroke-width:2px,color:#000
    style StoreEpi fill:#fff,stroke:#28a745,stroke-width:2px,color:#28a745
    style StoreProc fill:#fff,stroke:#28a745,stroke-width:2px,color:#28a745
    style SaveCheck fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style RedisVL fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style RedisData fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Response fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
```

### Key Differences

| Component | Stateless | Stateful |
|-----------|-----------|----------|
| **Orchestration** | Simple loop | LangGraph StateGraph |
| **Conversation History** | ❌ None | ✅ Redis checkpointing |
| **Tools** | 3 (health only) | 5 (health + memory) |
| **Vector Search** | ❌ None | ✅ RedisVL HNSW |
| **Memory Storage** | ❌ None | ✅ Episodic + Procedural |
| **Context Awareness** | ❌ None | ✅ Full conversation |

---

## 3. Feature Comparison

### What Both Agents Can Do ✅

| Feature | Stateless | Stateful |
|---------|-----------|----------|
| **Single-turn queries** | ✅ | ✅ |
| **Health data retrieval** | ✅ | ✅ |
| **Tool calling** | ✅ | ✅ |
| **Multi-step tool chains** | ✅ | ✅ |
| **Compound queries in one turn** | ✅ | ✅ |

**Example**: "What was my heart rate yesterday?" - Both answer correctly.

### What Only Stateful Can Do ✅

| Feature | Stateless | Stateful |
|---------|-----------|----------|
| **Follow-up questions** | ❌ | ✅ |
| **Pronoun resolution** | ❌ | ✅ |
| **Multi-turn reasoning** | ❌ | ✅ |
| **Goal awareness** | ❌ | ✅ |
| **Pattern learning** | ❌ | ✅ |
| **Cross-session memory** | ❌ | ✅ |

### Real Examples

#### Follow-Up Questions

**Query**: "Tell me about my recent workouts" → "What's the most common type?"

| Agent | Response to Follow-Up |
|-------|----------------------|
| **Stateless** | ❌ "What are you referring to? Please provide context." |
| **Stateful** | ✅ "Traditional Strength Training (40 workouts, 26% of total)" |

**Memory Used**: Short-term checkpointing

---

#### Pronoun Resolution

**Query**: "When was my last workout?" → "How long was it?"

| Agent | Response to "it" |
|-------|------------------|
| **Stateless** | ❌ "How long was what? Please specify." |
| **Stateful** | ✅ "45 minutes" |

**Memory Used**: Short-term checkpointing

---

#### Goal Awareness

**Query**: "Am I on track for my weight goal?"

| Agent | Response |
|-------|----------|
| **Stateless** | ❌ "I don't have information about your goals. What's your target?" |
| **Stateful** | ✅ "Your goal is 125 lbs by December. Current: 136.8 lbs. You've lost 8.2 lbs - great progress!" |

**Memory Used**: Episodic memory (RedisVL vector search)

---

#### Pattern Learning

**Query 1**: "Compare my activity this month vs last month" (first time)

| Agent | Performance |
|-------|-------------|
| **Stateless** | 2.8s (figures out tools) |
| **Stateful** | 2.8s (learns pattern) |

**Query 2**: Same question asked again

| Agent | Performance |
|-------|-------------|
| **Stateless** | 2.8s (figures out again) |
| **Stateful** | 1.9s (retrieves pattern - 32% faster) |

**Memory Used**: Procedural memory (workflow patterns)

---

## 4. Tool Comparison

### Tools Available to Each Agent

#### Stateless Agent: 3 Health Tools (No Memory)

| Tool | Purpose | Code Location |
|------|---------|---------------|
| `get_health_metrics` | Heart rate, steps, weight, BMI | `apple_health/query_tools/get_health_metrics.py` |
| `get_sleep_analysis` | Sleep data and efficiency | `apple_health/query_tools/get_sleep_analysis.py` |
| `get_workout_data` | Workout lists, patterns, progress | `apple_health/query_tools/get_workout_data.py` |

**Key Point**: NO memory tools - this agent cannot access goals or learned patterns.

---

#### Stateful Agent: 5 Tools (3 Health + 2 Memory)

| Tool | Purpose | Code Location |
|------|---------|---------------|
| `get_health_metrics` | Heart rate, steps, weight, BMI | `apple_health/query_tools/get_health_metrics.py` |
| `get_sleep_analysis` | Sleep data and efficiency | `apple_health/query_tools/get_sleep_analysis.py` |
| `get_workout_data` | Workout lists, patterns, progress | `apple_health/query_tools/get_workout_data.py` |
| **`get_my_goals`** 🆕 | Retrieve user goals (vector search) | `apple_health/query_tools/memory_tools.py` |
| **`get_tool_suggestions`** 🆕 | Retrieve learned patterns (vector search) | `apple_health/query_tools/memory_tools.py` |

**Key Point**: Same 3 health tools PLUS 2 memory tools for autonomous memory retrieval.

### The One-Line Difference

This single parameter controls whether an agent has memory:

```python path=/Users/allierays/Sites/redis-wellness/backend/src/apple_health/query_tools/__init__.py start=43
def create_user_bound_tools(
    user_id: str,
    conversation_history=None,
    include_memory_tools: bool = True,
) -> list[BaseTool]:
    """
    Create tool instances bound to the single application user.
    
    Tool Set (Health - always included):
        1. get_health_metrics - All non-sleep, non-workout health data
        2. get_sleep_analysis - Sleep data with daily aggregation
        3. get_workout_data - ALL workout queries (lists, patterns, progress)
    
    Tool Set (Memory - optional):
        4. get_my_goals - Retrieve user goals and preferences
        5. get_tool_suggestions - Retrieve learned tool-calling patterns
    """
    # Create health tools (always included)
    tools = [
        create_get_health_metrics_tool(user_id),
        create_get_sleep_analysis_tool(user_id),
        create_get_workout_data_tool(user_id),
    ]

    # Add memory retrieval tools (for autonomous memory access)
    # Stateless agent sets include_memory_tools=False for baseline comparison
    if include_memory_tools:
        memory_tools = create_memory_tools()
        tools.extend(memory_tools)
    
    return tools
```

**Usage:**

```python path=null start=null
# Stateless agent (NO memory)
tools = create_user_bound_tools(user_id, include_memory_tools=False)

# Stateful agent (WITH memory)
tools = create_user_bound_tools(user_id, include_memory_tools=True)
```

**That's it.** Same LLM, same health tools - only memory tools differ.

---

## 5. Capability Comparison

### What Each Agent Can Actually Do

| Capability | Stateless | Stateful | Impact |
|------------|-----------|----------|--------|
| **Single-turn queries** | ✅ Full | ✅ Full | Both handle factual queries equally well |
| **Follow-up questions** | ❌ Fails | ✅ Works | Stateful remembers conversation context |
| **Goal awareness** | ❌ No memory | ✅ Cross-session recall | Stateful retrieves stored goals via vector search |
| **Pattern learning** | ❌ Repeats work | ✅ Learns shortcuts | Stateful gets faster on similar queries |
| **Multi-turn reasoning** | ❌ No context | ✅ Full context | Stateful chains thoughts across messages |

### Memory Storage

| Memory Type | Stateless | Stateful |
|-------------|-----------|----------|
| **Conversation history** | None | Up to 100 messages (LangGraph checkpointing) |
| **Goals stored** | None | RedisVL vector index (1024-dim embeddings) |
| **Learned patterns** | None | RedisVL vector index (successful workflows) |
| **Persistence** | None | 7-month TTL (conversation + goals + patterns) |

### Token Usage Trade-offs

| Query Type | Stateless | Stateful | Why the Difference? |
|------------|-----------|----------|--------------------|
| **Simple query** | ~150 tokens | ~150 tokens | Same - no memory needed |
| **Follow-up** | ~150 tokens | ~400 tokens | +250 tokens for conversation history |
| **Goal query** | ❌ Fails | ~600 tokens | +450 tokens for vector search results |

**Trade-off**: Stateful uses 2-4x more tokens for context-dependent queries, but provides intelligent, context-aware responses. Stateless uses fewer tokens but cannot handle follow-ups or remember goals.

---

## 6. When to Use Each Agent

### Use Stateless Agent When:

- ✅ Building a simple Q&A system
- ✅ No need for conversation context
- ✅ Minimizing token usage is critical
- ✅ Establishing baseline metrics for comparison
- ✅ Users ask independent, single-turn questions

### Use Stateful Agent When:

- ✅ Users have multi-turn conversations
- ✅ Need to remember user goals and preferences
- ✅ Want to learn from past interactions
- ✅ Building a personalized health assistant
- ✅ Users ask follow-up questions like "What about yesterday?"

**Key Decision**: If users say "it", "that", or "those" and expect the agent to understand, you need the stateful agent.

---

## 7. Related Documentation

- **[03_STATELESS_AGENT.md](03_STATELESS_AGENT.md)** - Detailed stateless agent architecture
- **[04_STATEFUL_AGENT.md](04_STATEFUL_AGENT.md)** - Detailed stateful agent architecture
- **[10_MEMORY_ARCHITECTURE.md](10_MEMORY_ARCHITECTURE.md)** - Four-layer memory system deep dive
- **[09_EXAMPLE_QUERIES.md](09_EXAMPLE_QUERIES.md)** - Try these queries in the demo
- **[02_QUICKSTART.md](02_QUICKSTART.md)** - Run the demo to see the difference

---

**Key takeaway:** Both agents use the same LLM and tools, but Redis memory transforms the stateful agent from isolated Q&A into intelligent conversation with context awareness, goal recall, and pattern learning - proving memory is essential for AI intelligence.
