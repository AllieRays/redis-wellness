# Autonomous Agents: Advanced Patterns

## 1. Overview

**Autonomous agents** make decisions independently without hardcoded logic. This doc covers advanced patterns: tool chaining, intent routing, workflow optimization, and error handling.

### What You'll Learn

- **[What Makes an Agent Autonomous](#2-what-makes-an-agent-autonomous)** - Decision-making without rules
- **[Intent Routing](#3-intent-routing)** - Fast path for simple queries
- **[Tool Chaining Strategies](#4-tool-chaining-strategies)** - Multi-step workflows
- **[Workflow Optimization](#5-workflow-optimization)** - Performance patterns
- **[Related Documentation](#6-related-documentation)** - Implementation guides

---

## 2. What Makes an Agent Autonomous?

### Hardcoded (Not Autonomous)

```python
# ❌ Every decision is predetermined
if "goal" in query:
    return set_goal(query)
elif "workout" in query and "compare" in query:
    data1 = get_workouts("this month")
    data2 = get_workouts("last month")
    return compare(data1, data2)
# ...hundreds of if/else branches
```

**Problems**: Brittle, doesn't scale, can't adapt

### Autonomous (Decision-Making)

```python
# ✅ LLM decides everything
llm_with_tools = llm.bind_tools(all_tools)
response = await llm_with_tools.ainvoke(query)

# LLM autonomously:
# 1. Analyzes query
# 2. Selects tools
# 3. Chains multiple tools if needed
# 4. Decides when to stop
```

**Benefits**: Adaptive, handles variations, learns patterns

---

## 3. Intent Routing

**Pattern**: Pre-LLM routing for simple, deterministic queries

### When to Use Intent Routing

✅ **Use for**: Simple CRUD operations with clear patterns
- "My goal is X" → Direct Redis HSET
- "What are my goals?" → Direct Redis HGET
- "Delete my goals" → Direct Redis DEL

❌ **Don't use for**: Complex queries needing LLM reasoning

### Implementation

```python
# From: backend/src/utils/intent_bypass_handler.py

async def handle_intent_bypass(message: str, user_id: str):
    # Pattern matching for goals
    if re.search(r'\bgoal\b.*\bis\b', message, re.IGNORECASE):
        return await set_goal(user_id, message)  # <100ms

    if re.search(r'what.*goals', message, re.IGNORECASE):
        return await get_goals(user_id)  # <100ms

    # No match → continue to LLM
    return None
```

### Benefits

- **Fast**: <100ms (no LLM call)
- **Zero tokens**: No API cost
- **Predictable**: Deterministic results

---

## 4. Tool Chaining Strategies

### Simple Chain (Single Goal)

**Query**: "Am I on track for my weight goal?"

```python
# LLM autonomously chains 2 tools:
1. get_my_goals(query="weight goal")
   → Returns: {"goal": "125 lbs"}

2. get_health_metrics(metric="BodyMass")
   → Returns: {"latest": 136.8}

3. Synthesizes answer
```

**Pattern**: Information dependency - Tool 2 needs Tool 1's result

---

### Parallel Execution (Independent Tools)

**Query**: "Show my workouts and sleep patterns this week"

```python
# LLM calls 2 independent tools:
results = await asyncio.gather(
    get_workout_data(days=7),
    get_sleep_analysis(days=7)
)
```

**Pattern**: No dependencies - execute in parallel

---

### Iterative Refinement

**Query**: "Compare my activity this month vs last month"

```python
# LLM iteratively gathers data:
1. get_workout_data(period="this month")
   → Sees need for comparison baseline

2. get_workout_data(period="last month")
   → Sees both periods available

3. Performs comparison
```

**Pattern**: LLM realizes it needs more data after seeing initial results

---

## 5. Workflow Optimization

### Pattern Learning (Procedural Memory)

**First Time**:
```python
Query: "Compare workouts"
→ LLM figures out tools (2.8s)
→ Stores pattern with success_score=0.95
```

**Subsequent Times**:
```python
Query: "Compare workouts"
→ LLM calls get_tool_suggestions
→ Retrieves stored pattern (1.9s, 32% faster)
```

### Early Stopping

**Pattern**: Stop when you have enough information

```python
# Don't call more tools if answer is complete
if response.tool_calls:
    execute_tools(response.tool_calls)
else:
    return response.content  # LLM says "done"
```

### Max Iterations

**Pattern**: Prevent infinite loops

```python
# Stateless: MAX_TOOL_ITERATIONS = 8
# Stateful: LANGGRAPH_RECURSION_LIMIT = 50

for iteration in range(MAX_ITERATIONS):
    if no_tool_calls:
        break
```

---

## 6. Related Documentation

- **[06_AGENTIC_RAG.md](06_AGENTIC_RAG.md)** - Autonomous tool calling basics
- **[04_STATEFUL_AGENT.md](04_STATEFUL_AGENT.md)** - LangGraph autonomous workflow
- **[08_QWEN_BEST_PRACTICES.md](08_QWEN_BEST_PRACTICES.md)** - Optimizing tool selection
- **[10_MEMORY_ARCHITECTURE.md](10_MEMORY_ARCHITECTURE.md)** - Procedural memory patterns
- **[09_EXAMPLE_QUERIES.md](09_EXAMPLE_QUERIES.md)** - See autonomous agents in action

---

**Key takeaway:** Autonomous agents make independent decisions using LLM reasoning, intent routing for fast paths, tool chaining for complex queries, and procedural memory for workflow optimization - creating adaptive AI systems that improve over time.
