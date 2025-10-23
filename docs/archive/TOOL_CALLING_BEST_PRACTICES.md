# Tool-Calling Best Practices for Agentic Systems

**Date:** October 2025
**Context:** Redis Wellness Demo - Stateless vs Agentic RAG Chat

## Summary

This document outlines best practices for implementing LLM tool-calling in agentic systems, specifically for demos showcasing autonomous AI behavior.

---

## ✅ Current Implementation (CORRECT)

### 1. **Native LLM Tool Selection**

**What we do:**
```python
# Present ALL tools to the LLM
tools_to_use = user_tools
llm_with_tools = self.llm.bind_tools(tools_to_use)
response = await llm_with_tools.ainvoke(conversation)
```

**Why this is best practice:**
- ✅ Showcases Qwen 2.5's native function-calling capabilities
- ✅ Enables complex multi-step queries with tool chaining
- ✅ More robust than regex-based routing
- ✅ True autonomous agentic behavior for demos

### 2. **Autonomous Tool Loop**

**What we do:**
```python
for iteration in range(max_tool_calls):
    response = await llm_with_tools.ainvoke(conversation)

    if not response.tool_calls:
        break  # LLM decided it's done

    # Execute LLM's chosen tools
    for tool_call in response.tool_calls:
        result = await tool.ainvoke(tool_call["args"])
        conversation.append(ToolMessage(content=result))
```

**Why this is best practice:**
- ✅ LLM decides which tools to call
- ✅ LLM decides when to stop (no tool calls = done)
- ✅ Supports multi-step reasoning (search → aggregate → analyze)
- ✅ Demonstrates true AI autonomy

### 3. **Rich Tool Documentation**

**What we do:**
```python
@tool
def aggregate_metrics(metric_types: list[str], ...) -> dict:
    """
    🔢 CALCULATE STATISTICS - Use for mathematical aggregation.

    ⚠️ USE THIS TOOL WHEN USER ASKS FOR:
    - AVERAGE/MEAN: "average heart rate", "mean weight"
    - MIN/MAX: "minimum", "lowest", "highest"
    - TOTAL/SUM: "total steps", "sum of calories"

    ❌ DO NOT USE THIS TOOL FOR:
    - Individual data points → use search_health_records_by_metric
    - Viewing trends → use search_health_records_by_metric

    Returns: COMPUTED STATISTICS (single numbers), NOT raw data.
    """
```

**Why this is best practice:**
- ✅ Clear use cases help LLM understand tool purpose
- ✅ Negative examples prevent tool misuse
- ✅ Explicit return type clarifies expectations
- ✅ Emojis and formatting improve LLM comprehension

---

## ⚠️ Anti-Patterns to Avoid

### ❌ **Pre-LLM Tool Filtering**

**What we REMOVED:**
```python
# ❌ DON'T DO THIS (removed from codebase)
classification = self.query_classifier.classify_intent(query)
if classification["confidence"] >= 0.5:
    # Only present "recommended" tools
    tools_to_use = self._filter_tools(user_tools, classification)
```

**Why this is problematic:**
- ❌ Limits multi-step queries ("Compare Sept vs Oct" needs search + aggregate)
- ❌ Regex matching is brittle ("highest heart rate workout" triggers wrong tool)
- ❌ Hides LLM's true capabilities
- ❌ Makes system feel "rule-based" instead of "intelligent"

### ❌ **Hard-Coded Tool Routing**

**What to avoid:**
```python
# ❌ DON'T DO THIS
if "average" in query or "mean" in query:
    return aggregate_metrics(...)
elif "workout" in query:
    return search_workouts(...)
```

**Why this is problematic:**
- ❌ Cannot handle complex queries
- ❌ Keyword collisions ("What's the average workout duration?" → needs both tools)
- ❌ Undermines agentic narrative for demos

---

## 🎯 Recommended Architecture

```
User Query
    ↓
[Verbosity Detection] ← Use QueryClassifier here (UI hints only)
    ↓
Present ALL Tools to LLM
    ↓
LLM Native Tool Selection ← Qwen 2.5 decides autonomously
    ↓
Tool Execution Loop (max 8 iterations)
    ↓
[Memory Storage] ← Redis semantic memory (RAG agent only)
    ↓
Response to User
```

**Key Principles:**
1. **Lightweight verbosity detection** → Simple regex, no complex classification
2. **All tools available** → Let LLM choose based on query semantics
3. **Tool loop** → Enable multi-step reasoning
4. **Memory augmentation** → Redis context enhances tool selection

---

## 📊 Demo-Specific Benefits

### For "Stateless vs RAG" Comparison

**Without pre-filtering (current approach):**
- ✅ Shows true autonomous behavior → "Wow, it chains tools!"
- ✅ Handles unexpected queries → "It understood my complex question!"
- ✅ **Showcases Qwen 2.5** → "This is real AI function calling"
- ✅ **Redis memory as differentiator** → "Stateless can't remember context!"

**With pre-filtering (old approach):**
- ❌ Users think it's "keyword matching" → "Just hard-coded rules?"
- ❌ Complex queries fail → "Why can't it compare periods?"
- ❌ Undermines "agentic" narrative

---

## 🔧 Implementation Guidelines

### Tool Design Checklist

When creating new tools:

1. **Clear Purpose Statement**
   ```python
   """
   USE THIS TOOL WHEN: [specific use cases with examples]
   DO NOT USE FOR: [anti-patterns with alternatives]
   """
   ```

2. **Typed Arguments**
   ```python
   def search_health_records(
       metric_types: list[str],  # Type hints help LLM
       time_period: str = "recent",  # Defaults provide guidance
   ) -> dict[str, Any]:
   ```

3. **Return Format Documentation**
   ```python
   """
   Returns:
       Dict with:
       - results: List of matching records
       - total_found: Integer count
       - time_range: Human-readable period
   """
   ```

4. **Example Usage**
   ```python
   """
   Example:
       Query: "What was my average heart rate last week?"
       → aggregate_metrics(
           metric_types=["HeartRate"],
           time_period="last week",
           aggregations=["average"]
       )
       Returns: {"average": "72.5 bpm", "sample_size": 1250}
   """
   ```

### Agent Configuration

```python
class StatefulRAGAgent:
    def __init__(self, memory_manager):
        self.llm = create_health_llm()  # Qwen 2.5 with low temp (0.05)

    async def chat(self, message: str, ..., max_tool_calls: int = 8):
        # 1. Get all tools (no filtering)
        user_tools = create_user_bound_tools(user_id)

        # 2. Detect verbosity (simple regex - for response style only)
        verbosity = detect_verbosity(message)

        # 3. Present ALL tools to LLM
        llm_with_tools = self.llm.bind_tools(user_tools)

        # 4. Autonomous tool loop
        for iteration in range(max_tool_calls):
            response = await llm_with_tools.ainvoke(conversation)
            if not response.tool_calls:
                break
            # Execute chosen tools...
```

---

## 🧪 Testing Tool Selection

### Validation Queries

Test with queries that require:

1. **Single Tool**
   - "What's my current weight?" → search_health_records

2. **Multiple Tools (Same Call)**
   - "Show me weight, BMI, and heart rate" → search_health_records with multiple metrics

3. **Tool Chaining (Sequential)**
   - "What was my average heart rate last week?" → search_health_records → aggregate_metrics

4. **Complex Multi-Step**
   - "Compare my September vs October activity" →
     - search_health_records (September)
     - aggregate_metrics (September)
     - search_health_records (October)
     - aggregate_metrics (October)
     - Final synthesis

5. **Ambiguous Keywords**
   - "Show me my highest heart rate workouts" → Should use search_workouts (NOT aggregate_metrics)
   - "What day do I usually work out?" → search_workouts + pattern analysis

---

## 📚 References

- **LangChain Tool Binding**: https://python.langchain.com/docs/how_to/tool_calling/
- **Qwen 2.5 Function Calling**: https://qwenlm.github.io/blog/qwen2.5/
- **Redis Wellness Demo**: `/docs/INTELLIGENT_HEALTH_TOOLS_PLAN.md`

---

## 🔄 Migration Notes

### Changes Made (October 2025)

**Removed:**
- `_filter_tools()` method from `StatefulRAGAgent`
- Tool pre-filtering based on query classification confidence
- `QueryClassifier` class (replaced with lightweight `detect_verbosity()`)
- `_extract_current_query()` helper method (no longer needed)

**Added:**
- `verbosity_detector.py` - Lightweight verbosity detection (~90 lines vs 300+)
- Simple `detect_verbosity()` function using regex patterns

**Rationale:**
Initial implementation included pre-filtering to "help" the LLM by reducing decision space. Testing revealed this was counterproductive - Qwen 2.5's native tool selection is more robust and enables complex multi-step queries that pre-filtering breaks.

---

## ✅ Review Checklist

Before deploying agentic systems:

- [ ] LLM has access to ALL relevant tools (no pre-filtering)
- [ ] Tool docstrings include clear use cases and anti-patterns
- [ ] Tool loop allows sufficient iterations (8+ for complex queries)
- [ ] Query classification used only for UI hints, not tool restriction
- [ ] Multi-step queries tested (search → aggregate → compare)
- [ ] Error handling doesn't bypass autonomous decision-making
- [ ] Logging shows LLM's tool choices (for demo transparency)
- [ ] Memory augmentation doesn't force specific tool usage

---

**Conclusion:**

The best agentic systems trust the LLM's trained capabilities. Pre-filtering tools or hard-coding routing undermines autonomy and limits functionality. For demos showcasing "intelligence," let the AI be intelligent - native tool selection with rich documentation is the winning pattern.
