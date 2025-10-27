# Stateless Agent Architecture

## Overview

The stateless agent is the **baseline** for our comparison. It has **no memory** between requests - each query is processed independently with zero awareness of previous interactions.

**Key Point**: This demonstrates what AI agents are like WITHOUT memory systems.

### What You'll Learn

- What "stateless" means in AI agents
- How the simple tool-calling loop works
- Which tools are available (3 health tools only)
- Why it fails at follow-up questions
- Real code examples from the codebase

---

## What is Stateless?

**Stateless = Zero Memory**

Every request:
1. Receives only the current user message
2. Processes it in isolation
3. Returns a response
4. **Forgets everything**

The next request has zero knowledge of what came before.

### Example: Where Stateless Fails

```
User: "What was my heart rate yesterday?"
Agent: "Your average heart rate yesterday was 72 bpm."

User: "Is that good?"
Agent: ❌ "I need more information. What value are you referring to?"
```

The agent doesn't remember "that" refers to "72 bpm" from 5 seconds ago.

---

## Architecture

### Components

```
User Query
    ↓
Intent Router (pattern matching for goals)
    ↓
Qwen 2.5 7B LLM + 3 Health Tools
    ↓
Simple Tool Loop (up to 8 iterations)
    ↓
Redis (health data only - read-only)
    ↓
Response → FORGET EVERYTHING
```

### What's Included

✅ **Qwen 2.5 7B** - Function-calling LLM via Ollama
✅ **Simple Tool Loop** - Up to 8 iterations
✅ **Intent Router** - Fast path for goal CRUD (<100ms)
✅ **3 Health Tools**:
   - `get_health_metrics` - Heart rate, steps, weight, BMI
   - `get_sleep_analysis` - Sleep data and efficiency
   - `get_workout_data` - Workout lists, patterns, comparisons

### What's Deliberately Excluded (For Comparison)

❌ **NO conversation history** - Forgets previous messages
❌ **NO LangGraph** - No StateGraph, no checkpointing
❌ **NO RedisVL** - No vector search
❌ **NO memory tools** - `get_my_goals`, `get_tool_suggestions` not available
❌ **NO semantic memory** - No long-term knowledge base

---

## How It Works

### Simple Tool Loop

```python
# From: backend/src/agents/stateless_agent.py

async def chat(message: str, user_id: str):
    # NO conversation history loaded

    # Intent router: fast path for goals
    if is_goal_query(message):
        return handle_goal_query(message)  # <100ms, no LLM

    # Create tools (health only - NO memory)
    tools = create_user_bound_tools(
        user_id,
        include_memory_tools=False  # Stateless baseline
    )

    # Simple loop (max 8 iterations)
    conversation = [SystemMessage(...), HumanMessage(message)]

    for iteration in range(8):
        # Call LLM with tools
        llm_with_tools = llm.bind_tools(tools)
        response = await llm_with_tools.ainvoke(conversation)

        # Execute tools if LLM requested them
        if response.tool_calls:
            tool_results = execute_tools(response.tool_calls)
            conversation.append(tool_results)
        else:
            # LLM finished
            return response.content

    # NO memory stored after response
```

### Real Example: Heart Rate Query

**User**: "What was my average heart rate last week?"

**Step 1**: LLM decides to call tool
```python
{
    "tool_calls": [{
        "name": "get_health_metrics",
        "args": {"metric": "HeartRate", "days": 7}
    }]
}
```

**Step 2**: Tool retrieves from Redis
```python
# Tool reads health data (Redis hash)
result = {"average": 72, "unit": "bpm", "days": 7}
```

**Step 3**: LLM synthesizes response
> "Your average heart rate last week was 72 bpm."

**Step 4**: ❌ **Forgets everything** - no storage

---

## Tool Calling

### 3 Health Tools (All Agents Have These)

| Tool | Purpose | Redis Keys |
|------|---------|------------|
| `get_health_metrics` | All non-sleep, non-workout metrics<br/>(heart rate, steps, weight, BMI) | `health:*` hashes |
| `get_sleep_analysis` | Sleep data with daily aggregation | `sleep:*` hashes |
| `get_workout_data` | ALL workout queries<br/>(lists, patterns, progress) | `workout:*` hashes |

**Code Location**: `backend/src/apple_health/query_tools/`

### How LLM Chooses Tools

Qwen 2.5 7B reads tool docstrings and autonomously decides which to call:

```python
# Tool docstring (LLM reads this)
def get_health_metrics(metric: str, days: int):
    """
    🔢 RETRIEVE health metrics: heart rate, steps, weight, BMI.

    USE THIS TOOL WHEN:
    - User asks about "heart rate", "steps", "weight", "BMI"
    - User wants statistics: "average", "min", "max"

    DO NOT USE for:
    - Sleep data (use get_sleep_analysis)
    - Workouts (use get_workout_data)
    """
```

LLM sees these descriptions and picks the right tool based on the query.

---

## Limitations

### What Stateless CANNOT Do

❌ **Follow-up questions**
```
"How many workouts?" → "154 workouts"
"What's the most common type?" → ❌ "What are you referring to?"
```

❌ **Pronoun resolution**
```
"When was my last workout?" → "October 17th"
"How long was it?" → ❌ "How long was what?"
```

❌ **Multi-turn reasoning**
```
Turn 1: "What was my heart rate during workouts?"
Turn 2: "How does that compare to this week?"
Turn 3: ❌ "I need context. What are you comparing?"
```

❌ **Goal awareness**
```
"Am I on track for my weight goal?" → ❌ "I don't know your goals"
```

❌ **Pattern learning**
```
Query 1: 2.8s to figure out tools
Query 2: 2.8s (same - doesn't learn)
```

### This is NOT a Limitation of Qwen

The LLM is capable. The limitation is **architectural** - no memory system.

---

## Code Examples

### Agent Initialization

```python path=/Users/allierays/Sites/redis-wellness/backend/src/agents/stateless_agent.py start=46
class StatelessHealthAgent:
    """
    Simple stateless chat with basic tool calling but NO memory.

    This is the BASELINE for demonstrating memory value.
    """

    def __init__(self) -> None:
        """Initialize stateless chat."""
        self.llm = create_health_llm()
        logger.info("StatelessHealthAgent initialized (no memory)")
```

### Tool Creation (No Memory Tools)

```python path=/Users/allierays/Sites/redis-wellness/backend/src/agents/stateless_agent.py start=173
# Create tools (health only - NO memory tools)
user_tools = create_user_bound_tools(
    user_id,
    conversation_history=messages,
    include_memory_tools=False,  # Stateless agent has NO memory
)
```

### System Prompt (No Memory Instructions)

```python path=/Users/allierays/Sites/redis-wellness/backend/src/utils/agent_helpers.py start=null
def build_base_system_prompt() -> str:
    """
    Build system prompt for health AI agent.

    NOTE: No memory retrieval instructions - stateless agent
    only has access to health tools.
    """
    return """
    You are a health AI agent with access to Apple Health data.

    Available tools:
    - get_health_metrics: Heart rate, steps, weight, BMI
    - get_sleep_analysis: Sleep data and efficiency
    - get_workout_data: Workout lists, patterns, progress

    NOTE: You have NO memory of previous conversations.
    """
```

---

## Performance

| Metric | Stateless Agent |
|--------|-----------------|
| **First query** | ~2.8s (LLM inference) |
| **Follow-up query** | ❌ Fails (no context) |
| **Pattern learning** | ❌ None (2.8s every time) |
| **Token usage** | Low (no conversation history) |
| **Memory overhead** | 0 KB |

---

## Comparison to Stateful

See [STATELESS_VS_STATEFUL_COMPARISON.md](STATELESS_VS_STATEFUL_COMPARISON.md) for side-by-side comparison.

**Key Differences**:
- Stateless: 3 tools (health only)
- Stateful: 5 tools (health + memory)
- Stateless: Simple loop
- Stateful: LangGraph workflow
- Stateless: No Redis storage
- Stateful: Checkpointing + vector search

---

## Related Documentation

- **[STATEFUL_AGENT.md](STATEFUL_AGENT.md)** - How memory transforms the agent
- **[STATELESS_VS_STATEFUL_COMPARISON.md](STATELESS_VS_STATEFUL_COMPARISON.md)** - Side-by-side comparison
- **[EXAMPLE_QUERIES.md](EXAMPLE_QUERIES.md)** - Try queries to see the difference
- **[QUICKSTART.md](QUICKSTART.md)** - Run the demo

---

**Key takeaway:** The stateless agent is intentionally memory-free to demonstrate the baseline. It works for simple, single-turn queries but fails at conversation, context, and learning - exactly what we're trying to show.
