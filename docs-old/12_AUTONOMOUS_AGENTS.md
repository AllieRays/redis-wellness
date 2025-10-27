# Autonomous Tool Calling and Agentic Patterns

**Teaching Goal:** Understand how AI agents autonomously select and chain tools, why we chose Qwen 2.5 7B, and how LangGraph orchestrates the workflow.

## What is Autonomous Tool Calling?

Imagine you have a toolbox with 9 different tools. You ask: **"Am I getting more active?"**

**Hardcoded approach (bad):**
```python
if "active" in query:
    tool = "search_workouts"
elif "weight" in query:
    tool = "search_health_records"
# ...hundreds of if/else branches
```

**Problems:**
- Can't handle variations ("more fit", "working out more", "exercising more")
- Can't chain multiple tools ("compare activity this month vs last month" needs 2+ tool calls)
- Breaks with complex queries
- Requires manual updates for every new question type

**Autonomous approach (good):**
```python
# LLM decides which tools to call based on the question
llm_with_tools = llm.bind_tools([
    search_workouts,
    search_health_records,
    compare_periods,
    # ...all 9 tools
])

response = await llm_with_tools.ainvoke(user_query)
# LLM autonomously calls: compare_periods("this month", "last month")
# Then: search_workouts for each period
# Then: synthesizes answer from results
```

**Benefits:**
- Handles natural language variations automatically
- Chains tools as needed (multi-step reasoning)
- Adapts to new question patterns without code changes
- Learns from procedural memory (tool patterns that worked before)

## Why Qwen 2.5 7B?

We evaluated several models for autonomous tool calling:

| Model | Size | Tool Calling | Speed | Privacy |
|-------|------|--------------|-------|---------|
| **Qwen 2.5 7B** | 4.7 GB | ✅ Excellent | ⚡ Fast | 🔒 Local |
| Llama 3.1 8B | 4.9 GB | ⚠️ Okay | ⚡ Fast | 🔒 Local |
| GPT-4 | Cloud | ✅ Excellent | 🐌 Slow | ❌ Cloud |
| Mistral 7B | 4.1 GB | ❌ Poor | ⚡ Fast | 🔒 Local |

**Why Qwen 2.5 7B won:**

1. **Native function calling support** - Trained specifically for tool use
2. **Strong JSON formatting** - Consistently returns valid tool arguments
3. **Reasonable size** - Runs on most laptops (M1/M2 Mac, modern PCs)
4. **Ollama support** - One-command install (`ollama pull qwen2.5:7b`)
5. **Privacy-first** - Runs 100% locally, health data never leaves your machine

**From the model card:**
> "Qwen2.5 is optimized for function calling and agent workflows, with improved JSON structure prediction and multi-step reasoning capabilities."

**Real-world example:**
```
User: "What day do I consistently push my heart rate when I work out?"

Qwen 2.5 7B autonomously:
1. Calls search_workouts_and_activity(days_back=30)
2. Calls analyze_workout_intensity_by_day()
3. Synthesizes: "You consistently push your heart rate on Fridays and Mondays"

Mistral 7B would need 3+ tries to get the tool calls right.
```

## The 9 Health Tools

Our agent has 9 specialized tools. Each is a **LangChain tool** that the LLM can call autonomously.

### Tool Catalog

From `/Users/allierays/Sites/redis-wellness/backend/src/apple_health/query_tools/__init__.py`:

```python
def create_user_bound_tools(user_id: str) -> list[BaseTool]:
    """
    Create 9 health tools bound to a specific user.

    Tools are automatically available to the LLM for autonomous calling.
    """
    return [
        # 1. Search health metrics (weight, BMI, heart rate, steps)
        create_search_health_records_tool(user_id),

        # 2. Search workouts with heart rate zone analysis
        create_search_workouts_tool(user_id),

        # 3. Calculate statistics (avg, min, max, sum, count)
        create_aggregate_metrics_tool(user_id),

        # 4. Weight trend analysis with linear regression
        create_weight_trends_tool(user_id),

        # 5. Period-over-period comparison (single metric)
        create_compare_periods_tool(user_id),

        # 6. Comprehensive activity comparison (multi-metric)
        create_compare_activity_tool(user_id),

        # 7. Workout schedule pattern analysis
        create_workout_schedule_tool(user_id),

        # 8. Workout intensity analysis by day of week
        create_intensity_analysis_tool(user_id),

        # 9. Progress tracking between time periods
        create_progress_tracking_tool(user_id),
    ]
```

### Tool Examples with Autonomous Selection

#### Example 1: Simple Fact Lookup

**User:** "What's my current weight?"

**LLM reasoning:** This is a factual metric query → use `search_health_records_by_metric`

```python
# LLM autonomously generates this tool call
{
    "name": "search_health_records_by_metric",
    "args": {
        "metric_types": ["BodyMass"],
        "time_period": "recent"
    }
}

# Tool returns
{
    "results": [
        {"date": "2024-10-22", "value": "136.8 lb"}
    ]
}

# LLM synthesizes response
"Your current weight is 136.8 lb (as of October 22)"
```

#### Example 2: Multi-Tool Chaining

**User:** "Compare my workout frequency this month vs last month"

**LLM reasoning:** Need to compare periods → use `compare_activity_periods_tool`

```python
# LLM autonomously generates this tool call
{
    "name": "compare_activity_periods_tool",
    "args": {
        "period1_description": "this month",
        "period2_description": "last month"
    }
}

# Tool internally chains multiple operations:
# 1. Parse time periods → date ranges
# 2. Query workouts for period 1
# 3. Query workouts for period 2
# 4. Calculate statistics for both
# 5. Return comparison

# Returns
{
    "period1": {
        "workouts": 12,
        "total_calories": 2847,
        "avg_duration": 45
    },
    "period2": {
        "workouts": 8,
        "total_calories": 1932,
        "avg_duration": 42
    },
    "change": {
        "workouts": "+50%",
        "calories": "+47%"
    }
}

# LLM synthesizes
"You've worked out 50% more this month (12 workouts vs 8). You burned 915 more calories
this month compared to last month."
```

#### Example 3: Complex Multi-Step Query

**User:** "What day do I consistently push my heart rate when I work out?"

**LLM reasoning:** Need workout patterns + intensity analysis → chain 2 tools

```python
# Step 1: Get recent workouts with heart rate data
{
    "name": "search_workouts_and_activity",
    "args": {
        "days_back": 30
    }
}

# Returns workouts with heart rate zones
{
    "workouts": [
        {"day_of_week": "Friday", "max_hr": 168, "avg_hr": 145},
        {"day_of_week": "Monday", "max_hr": 172, "avg_hr": 150},
        # ...more workouts
    ]
}

# Step 2: Analyze intensity by day
{
    "name": "analyze_workout_intensity_by_day",
    "args": {}
}

# Returns aggregated intensity by day of week
{
    "Friday": {"avg_max_hr": 170, "count": 8},
    "Monday": {"avg_max_hr": 165, "count": 6},
    "Wednesday": {"avg_max_hr": 155, "count": 4}
}

# LLM synthesizes
"You consistently push your heart rate on Fridays and Mondays. On Fridays, your average
max heart rate is 170 bpm across 8 workouts."
```

## How the LLM Selects Tools Autonomously

### 1. Tool Binding (Setup Phase)

From `/Users/allierays/Sites/redis-wellness/backend/src/agents/stateful_rag_agent.py`:

```python
async def _llm_node(self, state: MemoryState) -> dict:
    """Call LLM with tools and context."""

    # Create all 9 tools bound to this user
    tools = create_user_bound_tools(state["user_id"])

    # Bind tools to LLM (makes them available for calling)
    llm_with_tools = self.llm.bind_tools(tools)

    # Build system prompt with instructions
    system_prompt = build_base_system_prompt()

    # Call LLM with tools and conversation history
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await llm_with_tools.ainvoke(messages)

    return {"messages": [response]}
```

### 2. System Prompt (Guidance)

From `/Users/allierays/Sites/redis-wellness/backend/src/utils/agent_helpers.py`:

```python
def build_base_system_prompt() -> str:
    """Build system prompt that teaches the LLM how to use tools."""
    return """You are a health AI assistant with access to the user's Apple Health data.

You have tools to search health records, query workouts, aggregate metrics, and compare time periods.

⚠️ TOOL-FIRST POLICY:
- For factual questions about workouts/health data → ALWAYS call tools (source of truth)
- NEVER answer workout/metric questions without tool data
- Always verify data through tools before responding

CRITICAL - TOOL USAGE EXAMPLES:
- For "last workout" or "when did I work out" queries → Use search_workouts_and_activity with days_back=30
- For "what is my weight/heart rate/steps" → Use search_health_records with appropriate metric_type
- For "recent workouts" → Use search_workouts_and_activity with days_back=30
- NEVER make up workout data (times, dates, calories, heart rates, etc.)

Key guidelines:
- Answer directly and concisely - get to the point in 1-2 sentences
- Only report data that tools actually return
- Quote returned data exactly (dates, times, numbers)
"""
```

**Key insight:** The system prompt teaches the LLM:
1. **When** to use tools (always for factual queries)
2. **Which** tools for which questions
3. **How** to use tool results (quote exactly, don't make up data)

### 3. Tool Execution (Runtime)

When the LLM decides to call a tool:

```python
async def _tool_node(self, state: MemoryState) -> dict:
    """Execute tools that LLM requested."""
    last_msg = state["messages"][-1]
    tool_calls = getattr(last_msg, "tool_calls", [])

    # LLM might call multiple tools in one turn
    logger.info(f"🔧 Executing {len(tool_calls)} tools")

    tools = create_user_bound_tools(state["user_id"])
    tool_messages = []

    for tool_call in tool_calls:
        tool_name = tool_call.get("name")
        logger.info(f"   → {tool_name}")

        # Find the tool and execute it
        for tool in tools:
            if tool.name == tool_name:
                result = await tool.ainvoke(tool_call["args"])
                tool_messages.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call.get("id", ""),
                        name=tool_name,
                    )
                )
                break

    return {"messages": tool_messages}
```

### 4. Tool Results → LLM → Response

After tools execute, results go back to the LLM:

```
LLM: "I'll call search_health_records_by_metric"
  ↓
Tool: Returns {"results": [{"date": "2024-10-22", "value": "136.8 lb"}]}
  ↓
LLM: "Based on the tool result, I'll respond: 'Your weight is 136.8 lb as of October 22'"
```

## Tool Chaining for Multi-Step Queries

Some queries require multiple tool calls in sequence. The LLM orchestrates this autonomously.

### Example: "Am I getting more active?"

**Step 1: LLM analyzes query**
- "more active" suggests comparison over time
- Need activity metrics from two periods

**Step 2: LLM calls comparison tool**
```python
{
    "name": "compare_activity_periods_tool",
    "args": {
        "period1_description": "last 30 days",
        "period2_description": "30 to 60 days ago"
    }
}
```

**Step 3: Tool returns comparison**
```json
{
    "period1": {"steps": 315000, "workouts": 12},
    "period2": {"steps": 285000, "workouts": 10},
    "change": {"steps": "+10.5%", "workouts": "+20%"}
}
```

**Step 4: LLM synthesizes answer**
```
"Yes, you're getting more active. Your step count increased by 10.5%
and you're working out 20% more often compared to the previous month."
```

**No manual tool chaining code needed** - the LLM decides what to call and when.

## How Procedural Memory Helps Tool Selection

Procedural memory learns which tool sequences work well for which queries.

### Without Procedural Memory

**User:** "Show my weight trend over time"

**LLM:** (tries different approaches)
- First time: Calls `search_health_records` → gets raw data, no trend analysis
- Second attempt: Calls `aggregate_metrics` → gets average, but no trend
- Third attempt: Calls `calculate_weight_trends_tool` → ✅ Success!

### With Procedural Memory

**User:** "Show my weight trend over time"

**Agent workflow:**

1. **Retrieve procedural patterns:**
```python
# Generate query embedding
embedding = generate_embedding("Show my weight trend over time")

# Search for similar past queries
patterns = procedural_memory.retrieve_patterns(embedding, top_k=3)

# Returns:
[
    {
        "query": "Analyze my weight trends",
        "tools_used": [
            "search_health_records_by_metric",
            "calculate_weight_trends_tool"
        ],
        "success_score": 0.95
    }
]
```

2. **Inject plan into LLM context:**
```python
system_prompt += f"""
📋 SUGGESTED TOOL SEQUENCE (from past successful workflows):
- search_health_records_by_metric (get weight data)
- calculate_weight_trends_tool (analyze trend)
Confidence: 95%
"""
```

3. **LLM follows the plan** (because it worked before):
```python
# LLM calls tools in suggested order
tool_calls = [
    {"name": "search_health_records_by_metric", "args": {"metric_types": ["BodyMass"]}},
    {"name": "calculate_weight_trends_tool", "args": {}}
]
```

**Result:** Correct tools on first try, faster response, better UX.

## LangGraph Orchestration: State Machine Approach

LangGraph orchestrates the autonomous tool-calling workflow as a **state machine**.

### Why State Machine vs Simple Loop?

**Simple loop (bad):**
```python
while True:
    response = llm(user_query)
    if response.has_tool_calls():
        results = execute_tools(response.tool_calls)
        # What if we need to store memories?
        # What if we need to validate results?
        # Hard to extend!
    else:
        break
```

**State machine (good):**
```python
graph = StateGraph(MemoryState)

# Define nodes (stages)
graph.add_node("retrieve_memory", retrieve_memory_node)
graph.add_node("llm", llm_node)
graph.add_node("tools", tool_node)
graph.add_node("store_memory", store_memory_node)

# Define flow
graph.set_entry_point("retrieve_memory")
graph.add_edge("retrieve_memory", "llm")
graph.add_conditional_edges("llm", should_continue, {
    "tools": "tools",
    "end": "store_memory"
})
graph.add_edge("tools", "llm")  # Loop back for multi-turn
graph.add_edge("store_memory", END)
```

**Benefits:**
- **Explicit stages:** Retrieve memory → LLM → Tools → Store memory
- **Easy to extend:** Add validation, refinement, or new memory types
- **Debuggable:** See exactly which stage failed
- **Checkpointing:** Save state at each step (conversation history)

### Code Walkthrough: StatefulRAGAgent Graph

From `/Users/allierays/Sites/redis-wellness/backend/src/agents/stateful_rag_agent.py`:

```python
def _build_graph(self):
    """Build LangGraph state machine with episodic AND procedural memory."""
    workflow = StateGraph(MemoryState)

    # Add nodes (stages)
    workflow.add_node("retrieve_episodic", self._retrieve_episodic_node)
    workflow.add_node("retrieve_procedural", self._retrieve_procedural_node)
    workflow.add_node("llm", self._llm_node)
    workflow.add_node("tools", self._tool_node)
    workflow.add_node("reflect", self._reflect_node)
    workflow.add_node("store_episodic", self._store_episodic_node)
    workflow.add_node("store_procedural", self._store_procedural_node)

    # Build flow: retrieve → llm → tools → reflect → store → END
    workflow.set_entry_point("retrieve_episodic")
    workflow.add_edge("retrieve_episodic", "retrieve_procedural")
    workflow.add_edge("retrieve_procedural", "llm")
    workflow.add_conditional_edges("llm", self._should_continue, {
        "tools": "tools",
        "end": "reflect"
    })
    workflow.add_edge("tools", "llm")  # Loop back for tool chaining
    workflow.add_edge("reflect", "store_episodic")
    workflow.add_edge("store_episodic", "store_procedural")
    workflow.add_edge("store_procedural", END)

    return workflow.compile(checkpointer=self.checkpointer)
```

### State Machine Flow

```
User Query: "Compare my workouts this week vs last week"
        ↓
┌─────────────────────────────────────────┐
│ 1. retrieve_episodic                    │
│    Load past goals/preferences (if any) │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ 2. retrieve_procedural                  │
│    Find similar past workflows          │
│    Suggest tool sequence to LLM         │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ 3. llm                                  │
│    LLM decides: call compare_activity   │
│    Returns tool_calls in response       │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ 4. should_continue (conditional)        │
│    Has tool_calls? → Go to "tools"      │
│    No tool_calls? → Go to "reflect"     │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ 5. tools                                │
│    Execute compare_activity_periods     │
│    Return results to state              │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ 6. llm (again)                          │
│    LLM sees tool results                │
│    Generates final response             │
│    No more tool_calls → proceed         │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ 7. reflect                              │
│    Evaluate workflow success            │
│    Calculate success_score              │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ 8. store_episodic                       │
│    Extract facts (goals, preferences)   │
│    Store in episodic memory if found    │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ 9. store_procedural                     │
│    If successful (score >= 0.7):        │
│    Store workflow pattern for future    │
└─────────────────────────────────────────┘
        ↓
      END
```

### Conditional Edges: Tool Looping

The `should_continue` function enables tool chaining:

```python
def _should_continue(self, state: MemoryState) -> str:
    """Check if we need to call more tools."""
    last_msg = state["messages"][-1]
    has_tool_calls = hasattr(last_msg, "tool_calls") and last_msg.tool_calls

    return "tools" if has_tool_calls else "end"
```

**Example: Multi-turn tool loop**
```
Turn 1: LLM → "I'll call search_workouts" → goes to tools
Turn 2: tools → executes, returns to LLM → LLM → "Now I'll call aggregate_metrics" → goes to tools
Turn 3: tools → executes, returns to LLM → LLM → "Here's the answer" (no tool_calls) → goes to end
```

## Key Takeaways

1. **Autonomous tool calling > hardcoded logic** - LLMs handle natural language variations automatically
2. **Qwen 2.5 7B excels at function calling** - Native support, strong JSON formatting, local privacy
3. **9 health tools cover common queries** - Search, aggregate, compare, analyze - autonomous selection
4. **Tool chaining is automatic** - LLM orchestrates multi-step workflows without manual coding
5. **Procedural memory accelerates learning** - Agents get better at tool selection over time
6. **LangGraph provides structure** - State machine approach is debuggable and extensible

## Next Steps

- **05_REDIS_PATTERNS.md** - Deep dive into Redis data structures for AI workloads
- **06_ARCHITECTURE_DECISIONS.md** - Why we chose Redis, LangGraph, Qwen, and Ollama
- **08_EXTENDING.md** - Add new tools and teach your agent new capabilities
