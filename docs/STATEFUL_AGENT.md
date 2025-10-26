# Stateful Agent Architecture

## 1. Overview

This document explains the **internal architecture of the stateful agent**: how it uses **Agentic RAG** (Retrieval-Augmented Generation with autonomous tool calling) to maintain context and intelligence.

### What You'll Learn

- **[Key Technologies](#2-key-technologies)** - LangGraph, Redis, RedisVL, and the 5 tools bound to the LLM
- **[Architecture Overview](#3-architecture-overview)** - Component layers and how they interact
- **[How It Works](#4-how-it-works)** - Workflow with intent routing, checkpointing, and vector search
- **[Why It Matters](#5-why-it-matters)** - Benefits of stateful vs. stateless agents
- **[Related Documentation](#6-related-documentation)** - Links to deeper dives on memory and Redis patterns

---

## 2. Key Technologies

- **Qwen 2.5 7B**: Function-calling LLM that reads tool docstrings and autonomously decides which tools to call
- **LangGraph**: StateGraph workflow orchestration with automatic Redis checkpointing for conversation history
- **Redis**: Stores short-term conversation history via LangGraph's AsyncRedisSaver
- **RedisVL**: Vector search for episodic memory (goals) and procedural memory (learned patterns)
- **Intent Router**: Pre-LLM pattern matching for fast deterministic operations (goal CRUD)

### 5 Tools Bound to LLM

#### Health Data Tools

1. `get_health_metrics` - Heart rate, steps, weight, BMI, etc.
2. `get_sleep_analysis` - Sleep data with daily aggregation and efficiency metrics
3. `get_workout_data` - All workout queries (lists, patterns, progress, comparisons)

#### Memory Tools

4. `get_my_goals` - Retrieve user goals and preferences (episodic memory)
5. `get_tool_suggestions` - Retrieve learned tool-calling patterns (procedural memory)

---

## 3. Architecture Overview

The stateful agent combines **intent routing**, **LangGraph workflow**, and **Redis memory layers**:

```mermaid
flowchart TB
    UI["User Interface"]
    Router["Intent Router<br/>(Pre-LLM)<br/>Pattern matching"]

    FastPath["Direct Redis Ops<br/>(Goal CRUD)"]
    ComplexPath["LangGraph StateGraph<br/>• Qwen 2.5 7B LLM<br/>• Tool calling loop<br/>• Response synthesis"]

    RedisShort["Redis<br/>Short-term<br/>Checkpointing"]
    RedisVL["RedisVL<br/>Episodic + Procedural<br/>Vector Search"]
    Tools["Health Tools<br/>(3 data tools)"]

    UI --> Router
    Router -->|"Fast path"| FastPath
    Router -->|"Complex path"| ComplexPath

    ComplexPath --> RedisShort
    ComplexPath --> RedisVL
    ComplexPath --> Tools

    style UI fill:#fff,stroke:#dc3545,stroke-width:2px,color:#000
    style Router fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style FastPath fill:#fff,stroke:#333,stroke-width:2px,color:#000
    style ComplexPath fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style RedisShort fill:#dc3545,stroke:#dc3545,stroke-width:2px,color:#fff
    style RedisVL fill:#dc3545,stroke:#dc3545,stroke-width:2px,color:#fff
    style Tools fill:#fff,stroke:#333,stroke-width:2px,color:#000
```

### Layer Responsibilities

1. **Intent Router**: Pre-LLM pattern matching for fast deterministic operations (<100ms)
2. **LangGraph**: Orchestrates LLM → tools → memory → response workflow
3. **Memory Layer**:
   - Redis checkpointing (short-term conversation history)
   - RedisVL vector search (episodic goals + procedural patterns)
4. **Tool Layer**: 5 tools for health data retrieval and memory access

---

## 4. How It Works

The stateful agent processes queries through a multi-stage workflow with intelligent tool selection and memory retrieval:

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'14px'}}}%%
flowchart TB
    Query["User Query"]
    Router{"Intent Router"}
    subgraph Simple["Simple Path"]
        GoalOp["Goal CRUD"]
        Redis1["Redis"]
    end
    subgraph Complex["Complex Path"]
        Memory["Load History"]
        LLM["Qwen 2.5 7B"]
        Decision{"Which tool?"}
        MT["Memory Tools<br/>get_my_goals<br/>get_tool_suggestions"]
        HT["Health Tools<br/>get_health_metrics<br/>get_workout_data<br/>get_sleep_analysis"]
        VectorDB["RedisVL<br/>Vector search"]
        HealthDB["Redis<br/>Health data"]
        Loop{"More data?"}
        Store["Store memories"]
    end
    Response["Response"]
    Query --> Router
    Router -->|"'Set goal...'"| GoalOp
    Router -->|"Health query"| Memory
    GoalOp --> Redis1
    Redis1 --> Response
    Memory --> LLM
    LLM --> Decision
    Decision -->|Context| MT
    Decision -->|Data| HT
    Decision -->|Done| Response
    MT --> VectorDB
    HT --> HealthDB
    VectorDB --> Loop
    HealthDB --> Loop
    Loop -->|Yes| LLM
    Loop -->|No| Store
    Store --> Response
    style Query fill:#fff,stroke:#333,stroke-width:2px
    style Router fill:#fff,stroke:#333,stroke-width:2px
    style GoalOp fill:#fff,stroke:#333,stroke-width:2px
    style Redis1 fill:#fff,stroke:#333,stroke-width:2px
    style Memory fill:#f8d7da,stroke:#dc3545,stroke-width:2px
    style LLM fill:#fff,stroke:#333,stroke-width:2px
    style Decision fill:#fff,stroke:#333,stroke-width:2px
    style MT fill:#f8d7da,stroke:#dc3545,stroke-width:2px
    style HT fill:#fff,stroke:#333,stroke-width:2px
    style VectorDB fill:#dc3545,stroke:#dc3545,stroke-width:2px,color:#fff
    style HealthDB fill:#fff,stroke:#333,stroke-width:2px
    style Loop fill:#fff,stroke:#333,stroke-width:2px
    style Store fill:#f8d7da,stroke:#dc3545,stroke-width:2px
    style Response fill:#fff,stroke:#333,stroke-width:2px
    style Simple fill:#f8f9fa,stroke:#6c757d,stroke-width:1px
    style Complex fill:#f8f9fa,stroke:#6c757d,stroke-width:1px
```

### Key Components

#### Intent Router (Fast Path)

Pattern-based routing for deterministic operations. Bypasses LLM for goal setting/retrieval.

**Example:** "My goal is to run 3x per week" → Direct Redis storage (<100ms, zero tokens)

#### LangGraph Checkpointing (Short-term Memory)

Automatically loads conversation history before each LLM call via `AsyncRedisSaver`.

**Example conversation state:**
```python
messages = [
    HumanMessage("What was my heart rate?"),
    AIMessage("72 bpm average"),
    HumanMessage("Is that good?")  # LLM understands "that" = 72 bpm
]
```

**Redis keys:** `langgraph:checkpoint:{session_id}:*` (TTL: 7 months)

#### RedisVL Vector Search (Episodic + Procedural Memory)

Goals and patterns stored with embeddings for semantic retrieval.

**Example goal storage:**
```python
episodic:user:goal:1729962000 → {
    "text": "Target heart rate is 80-85 bpm",
    "embedding": [0.234, -0.123, ...],  # 1024-dim
    "metric": "HeartRate"
}
```

**LLM retrieves via `get_my_goals` tool** when needed for context.

### Real Example: "Is that good?"

Demonstrates all three components working together:

```
User: "What was my heart rate last week?"
Agent: "87 bpm average"
User: "Is that good?"  ← Needs context + goals
```

**Step 1: LangGraph loads conversation**
```python
messages = [
    HumanMessage("What was my heart rate last week?"),
    AIMessage("87 bpm average"),
    HumanMessage("Is that good?")  # Current query
]
```

**Step 2: LLM autonomously calls `get_my_goals` tool**

Qwen reads the tool docstring and decides to retrieve goals:
```python
{"tool_calls": [{"name": "get_my_goals", "args": {"query": "heart rate goal"}}]}
```

**Step 3: RedisVL retrieves goal**
```python
goals = [{"metric": "HeartRate", "target": "80-85 bpm"}]
```

**Step 4: LLM synthesizes response**

Combines conversation context (87 bpm) + episodic memory (goal: 80-85 bpm):

> "87 bpm is slightly above your target range of 80-85 bpm."

---

## 5. Why It Matters

### Comparison: Stateless vs. Stateful

| Without Redis | With Redis + LangGraph |
|---------------|------------------------|
| ❌ Forgets conversation | ✅ Checkpointing loads conversation automatically |
| ❌ Can't answer follow-ups | ✅ Understands "that", "it", "them" references |
| ❌ Doesn't know user goals | ✅ Vector search retrieves goals semantically |
| ❌ Repeats mistakes | ✅ Learns successful tool-calling patterns |

### Four-Layer Memory Architecture

- **Short-term** (session): Conversation context for follow-ups
- **Episodic** (permanent): User goals and preferences
- **Procedural** (permanent): Learned tool-calling patterns
- **Semantic** (optional): Health knowledge base

### Performance

- Intent router: <100ms (direct Redis)
- First turn: ~2.8s (0.5s checkpoint + 2.3s LLM)
- Follow-up: ~1.9s (context preloaded)
- Memory overhead: ~170 KB per user (100 turns + 10 goals)

---

## 6. Related Documentation

- **[02_THE_DEMO.md](02_THE_DEMO.md)** - Side-by-side stateless vs. stateful comparison in the UI
- **[03_MEMORY_ARCHITECTURE.md](03_MEMORY_ARCHITECTURE.md)** - Deep dive into four-layer memory system
- **[04_AUTONOMOUS_AGENTS.md](04_AUTONOMOUS_AGENTS.md)** - Tool-calling and agentic workflow patterns
- **[05_REDIS_PATTERNS.md](05_REDIS_PATTERNS.md)** - Redis usage patterns and best practices

---

**Key takeaway:** Redis + LangGraph transforms stateless chat into context-aware AI that remembers, learns, and understands user intent through autonomous tool calling and multi-layer memory.
