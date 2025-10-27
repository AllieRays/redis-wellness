# Agentic RAG: Autonomous Tool Calling

## 1. Overview

**Agentic RAG** = Retrieval-Augmented Generation where the AI **autonomously decides** which tools to call and when. No hardcoded logic - the LLM makes all decisions based on query analysis.

This is the core pattern that makes both agents (stateless and stateful) intelligent at data retrieval.

### What You'll Learn

- **[What is Agentic RAG](#2-what-is-agentic-rag)** - Autonomous vs hardcoded tool calling
- **[How Qwen Chooses Tools](#3-how-qwen-chooses-tools)** - Tool docstrings and decision-making
- **[Tool Chaining](#4-tool-chaining)** - Multi-step autonomous workflows
- **[Real Examples](#5-real-examples)** - Actual queries and tool selections
- **[Related Documentation](#6-related-documentation)** - Deep dives into tools and agents

---

## 2. What is Agentic RAG?

### Traditional RAG (Hardcoded)

```python
# ❌ BAD: Hardcoded logic
if "weight" in query:
    tool = search_health_records
elif "workout" in query:
    tool = search_workouts
# ...100+ if/else statements
```

**Problems**:
- Can't handle variations ("fitness" vs "workout")
- Can't chain tools
- Breaks with complex queries
- Requires manual updates

### Agentic RAG (Autonomous)

```python
# ✅ GOOD: LLM decides
llm_with_tools = llm.bind_tools([
    get_health_metrics,
    get_sleep_analysis,
    get_workout_data,
    get_my_goals,         # Stateful only
    get_tool_suggestions  # Stateful only
])

response = await llm_with_tools.ainvoke(user_query)
# LLM autonomously picks tools based on query
```

**Benefits**:
- Handles natural language variations
- Chains multiple tools as needed
- Adapts to new patterns
- No code changes required

---

## 3. How Qwen Chooses Tools

### Tool Docstrings as Instructions

Qwen 2.5 7B reads tool docstrings to understand what each tool does:

```python
@tool
def get_health_metrics(metric: str, days: int):
    """
    🔢 RETRIEVE health metrics: heart rate, steps, weight, BMI.

    ⚠️ USE THIS TOOL WHEN USER ASKS FOR:
    - "heart rate", "pulse", "bpm"
    - "steps", "walking", "distance"
    - "weight", "mass", "lbs", "kg"
    - "BMI", "body mass index"
    - Statistics: "average", "min", "max", "total"

    ❌ DO NOT USE for:
    - Sleep data (use get_sleep_analysis)
    - Workouts (use get_workout_data)
    - Goals (use get_my_goals)  # Stateful only

    Returns health metrics with statistics.
    """
```

### Decision Process

1. **User asks**: "What was my average heart rate?"
2. **Qwen reads all tool docstrings**
3. **Qwen sees**: `get_health_metrics` mentions "heart rate" and "average"
4. **Qwen decides**: Call `get_health_metrics(metric="HeartRate", days=7)`
5. **Tool executes**: Returns `{"average": 72, "unit": "bpm"}`
6. **Qwen synthesizes**: "Your average heart rate last week was 72 bpm"

---

## 4. Tool Chaining

Agentic RAG enables **autonomous multi-step workflows**:

### Example: Goal-Based Query

**User**: "Am I on track for my weight goal?"

**Stateful Agent Workflow** (Autonomous):

```
1. LLM sees "goal" keyword
   ↓
2. Calls get_my_goals tool
   → Returns: {"goal": "125 lbs by December", "current": null}
   ↓
3. LLM realizes it needs current weight
   ↓
4. Calls get_health_metrics(metric="BodyMass")
   → Returns: {"latest": 136.8, "unit": "lb"}
   ↓
5. LLM synthesizes comparison
   → "Your goal is 125 lbs. Current: 136.8 lbs. You need to lose 11.8 lbs..."
```

**Key**: LLM autonomously decided to chain 2 tools based on information needs.

### Example: Pattern Learning

**User**: "Compare my activity this month vs last month" (asked twice)

**First Time**:
```
1. LLM figures out tools needed
2. Calls get_workout_data(period="this month")
3. Calls get_workout_data(period="last month")
4. Synthesizes comparison
5. Stores pattern in procedural memory
```

**Second Time**:
```
1. LLM calls get_tool_suggestions(query="compare activity")
2. Retrieves stored pattern: ["get_workout_data", "get_workout_data"]
3. Executes same tools (32% faster)
4. Synthesizes comparison
```

---

## 5. Real Examples

### Simple Query (Single Tool)

**Query**: "How many workouts do I have?"

**Tool Selected**: `get_workout_data`

```python
{
    "tool_calls": [{
        "name": "get_workout_data",
        "args": {"include_summary": True}
    }]
}
```

**Response**: "You have 154 workouts recorded."

---

### Complex Query (Multiple Tools)

**Query**: "Show my workout pattern and tell me if I'm improving"

**Tools Selected**: 3 tool calls

```python
[
    {"name": "get_workout_data", "args": {"include_patterns": True}},
    {"name": "get_workout_data", "args": {"include_progress": True}},
    {"name": "get_my_goals", "args": {"query": "workout frequency"}}
]
```

**Response**: "You work out most on Fridays (24 workouts). Your frequency increased 50% this month, which aligns with your goal of 3x/week."

---

### Goal Query (Memory + Health Tools)

**Query**: "Am I hitting my step goal today?"

**Tools Selected** (Stateful only):

```python
[
    {"name": "get_my_goals", "args": {"query": "steps goal"}},
    {"name": "get_health_metrics", "args": {"metric": "StepCount", "days": 1}}
]
```

**Response**: "Your goal is 10,000 steps daily. Today you have 8,432 steps (84%)."

---

## 6. Related Documentation

- **[STATELESS_AGENT.md](STATELESS_AGENT.md)** - Agentic RAG without memory
- **[STATEFUL_AGENT.md](STATEFUL_AGENT.md)** - Agentic RAG with memory
- **[QWEN_BEST_PRACTICES.md](QWEN_BEST_PRACTICES.md)** - Optimizing tool calling
- **[AUTONOMOUS_AGENTS.md](AUTONOMOUS_AGENTS.md)** - Advanced agentic patterns
- **[EXAMPLE_QUERIES.md](EXAMPLE_QUERIES.md)** - See tool selection in action

---

**Key takeaway:** Agentic RAG lets the LLM autonomously decide which tools to call based on query analysis, enabling natural language understanding, tool chaining, and adaptive workflows without hardcoded logic.
