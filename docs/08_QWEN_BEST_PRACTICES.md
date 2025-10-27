# Qwen 2.5 Best Practices for Tool Calling

**Last Updated**: 2025-10-26
**Model**: Qwen 2.5 7B Instruct
**Framework**: LangChain + Ollama

---

## Overview

This document provides best practices for implementing reliable tool calling with Qwen 2.5 7B in production environments. These practices are based on official Qwen documentation, LangChain integration patterns, and real-world implementation experience.

---

## Core Principles

### 1. Temperature Settings

**Recommendation**: Use ultra-low temperature (≤0.15) for tool calling scenarios.

```python
llm = ChatOllama(
    model="qwen2.5:7b",
    base_url="http://localhost:11434",
    temperature=0.05,  # Ultra-low for precise tool selection
    num_predict=512,   # Limit response length for tool calls
)
```

**Rationale**: Tool selection requires accuracy and reliability. The model must confidently select the correct tool and format parameters precisely. Low temperature reduces randomness in tool selection.

### 2. Tool Description Guidelines

Write clear, distinctive tool descriptions with explicit use cases:

```python
@tool
def aggregate_metrics(
    metric_types: List[str],
    time_period: str = "recent",
    aggregations: List[str] = None
) -> Dict[str, Any]:
    """
    🔢 CALCULATE STATISTICS: Average, Min, Max, Sum, Count over health metrics.

    ⚠️ USE THIS TOOL WHEN USER ASKS FOR:
    - "average", "mean", "avg"
    - "minimum", "min", "lowest"
    - "maximum", "max", "highest"
    - "total", "sum", "count", "how many"
    - "statistics", "stats", "calculations"

    ❌ DO NOT USE for:
    - Individual data points (use search_health_records instead)
    - Viewing trends over time (use search_health_records instead)
    - Listing all values (use search_health_records instead)

    This tool performs MATHEMATICAL AGGREGATION on health data.
    Returns computed statistics, NOT raw data.

    Args:
        metric_types: Health metrics to aggregate ["HeartRate", "BodyMass", etc.]
        time_period: Natural language time ("last week", "September 2024")
        aggregations: Statistics to compute ["average", "min", "max", "sum"]

    Returns:
        Dict with computed statistics for each metric

    Example:
        Query: "What was my average heart rate last week?"
        Returns: {"average": 72.5, "min": 58, "max": 145, "unit": "bpm"}
    """
```

**Key elements**:
- Visual emoji for quick identification (🔢)
- Explicit "USE THIS TOOL WHEN" section with keywords
- Clear negative examples ("DO NOT USE for")
- Natural language examples showing query → output
- Keyword-rich descriptions that match user query patterns

### 3. System Prompt Design

Provide explicit tool selection guidance in the system prompt. See [06_AGENTIC_RAG.md](06_AGENTIC_RAG.md) for how Qwen's agentic RAG approach makes tool selection decisions:

```python
system_prompt = """
You are a health AI agent with access to tools for querying Apple Health data.

📋 TOOL SELECTION RULES:

1. For STATISTICS and CALCULATIONS:
   - Keywords: "average", "mean", "min", "max", "total", "sum", "statistics"
   - Use: aggregate_metrics tool
   - Example: "What was my average heart rate?" → aggregate_metrics

2. For RAW DATA and TRENDS:
   - Keywords: "show me", "list", "display", "view", "trend", "over time"
   - Use: search_health_records tool
   - Example: "Show me my weight values" → search_health_records

3. For WORKOUTS and EXERCISE:
   - Keywords: "workout", "exercise", "run", "training", "activity"
   - Use: search_workouts tool
   - Example: "When did I last work out?" → search_workouts

⚠️ IMPORTANT: Always use the most specific tool for the query type.
"""
```

### 4. Query Classification (Recommended for Complex Systems)

Add a pre-processing layer to classify queries before LLM invocation:

```python
class QueryClassifier:
    """Classify user queries to route to appropriate tools."""

    AGGREGATION_KEYWORDS = [
        r'\baverage\b', r'\bmean\b', r'\bavg\b',
        r'\bminimum\b', r'\bmin\b', r'\blowest\b',
        r'\bmaximum\b', r'\bmax\b', r'\bhighest\b',
        r'\btotal\b', r'\bsum\b', r'\bcount\b',
        r'\bstatistics\b', r'\bstats\b',
    ]

    def classify_intent(self, query: str) -> Dict[str, Any]:
        """
        Classify query intent and recommend tools.

        Returns:
            Dict with intent, confidence, recommended_tools, reasoning
        """
        query_lower = query.lower()

        aggregation_matches = sum(
            1 for pattern in self.AGGREGATION_KEYWORDS
            if re.search(pattern, query_lower)
        )

        if aggregation_matches > 0:
            return {
                "intent": "aggregation",
                "confidence": min(aggregation_matches / 3, 1.0),
                "recommended_tools": ["aggregate_metrics"],
                "reasoning": f"Query contains aggregation keywords (matched {aggregation_matches})"
            }

        # ... similar logic for other intents
```

**Integration**:

```python
def _agent_node(self, state: AgentState) -> Dict:
    """Agent reasoning node with query classification."""

    user_message = state["messages"][-1].content

    # Classify query intent
    classification = self.query_classifier.classify_intent(user_message)

    # Filter tools based on classification (if confident)
    if classification["confidence"] >= 0.6:
        tools_to_use = [
            tool for tool in all_tools
            if tool.name in classification["recommended_tools"]
        ]
    else:
        tools_to_use = all_tools  # Use all tools if uncertain

    llm_with_tools = self.llm.bind_tools(tools_to_use)
    response = llm_with_tools.invoke(messages)

    return {"messages": [response]}
```

**Benefits**:
- Reduces LLM's decision space (fewer tools = easier choice)
- Prevents wrong tool selection if correct tool is the only option
- Provides fallback to all tools if classification is uncertain
- Adds structured reasoning to tool selection process

### 5. Tool Library Management

**Problem**: Large tool libraries (10+ tools) can degrade performance.

**Solution**: Use tool routing to present only relevant tools. See how this is implemented in [03_STATELESS_AGENT.md](03_STATELESS_AGENT.md) and [04_STATEFUL_AGENT.md](04_STATEFUL_AGENT.md):

```python
# Instead of binding all 20 tools:
llm_with_tools = llm.bind_tools(all_tools)  # ❌ Poor performance

# Filter to relevant subset:
relevant_tools = filter_tools_by_intent(query, all_tools)
llm_with_tools = llm.bind_tools(relevant_tools)  # ✅ Better performance
```

**Our application**: Has only 5 tools (3 health + 2 memory), so routing is optional but still helpful.

### 6. Avoid ReAct-Style Templates

**Not Recommended** for Qwen 2.5:

```python
# ❌ Don't use stopword-based ReAct patterns
template = """
Thought: {reasoning}
Action: {tool_name}
Action Input: {tool_args}
"""
```

**Why**:
- Qwen 2.5 is a reasoning model that may output stopwords in thought sections
- Leads to unexpected tool call parsing failures
- Official Qwen docs recommend against this approach

**Instead**: Use native tool calling with `bind_tools()`:

```python
# ✅ Use LangChain's native tool calling
llm_with_tools = llm.bind_tools(tools)
response = llm_with_tools.invoke(messages)
```

---

## Implementation Checklist

Use this checklist when implementing tool calling with Qwen 2.5:

### Model Configuration
- [ ] Temperature set to ≤0.15 for tool calling scenarios
- [ ] `num_predict` limited to reasonable value (512-1024)
- [ ] Model capabilities confirmed: `ollama show qwen2.5:7b` shows "tools"

### Tool Design
- [ ] Tool descriptions are clear and distinctive
- [ ] Each tool has explicit "USE THIS TOOL WHEN" section
- [ ] Tool descriptions include negative examples ("DO NOT USE for")
- [ ] Tool descriptions are keyword-rich (match user query patterns)
- [ ] Tool descriptions include example queries and outputs

### System Prompt
- [ ] System prompt includes explicit tool selection rules
- [ ] Tool selection rules are structured and easy to follow
- [ ] Example queries provided for each tool
- [ ] Warnings included for common mistakes

### Query Classification (Optional)
- [ ] Classifier implemented for complex systems (5+ tools)
- [ ] Confidence threshold prevents overly aggressive filtering (≥0.6)
- [ ] Fallback to all tools if classification uncertain
- [ ] Classification reasoning logged for debugging

### Testing
- [ ] Test suite covers all tool types with representative queries
- [ ] Integration tests verify end-to-end tool selection
- [ ] Edge cases tested (ambiguous queries, multi-step queries)
- [ ] Tool selection accuracy measured (target: ≥90%)

### Monitoring
- [ ] Tool selection decisions logged with structured data
- [ ] Classification confidence tracked
- [ ] Tool call success/failure rates monitored
- [ ] User queries logged for analysis

---

## Troubleshooting

### Issue: LLM Selects Wrong Tool

**Symptoms**:
- LLM consistently chooses Tool A even when Tool B is clearly appropriate
- Tool descriptions seem clear but LLM ignores them

**Solutions**:
1. **Lower temperature** to 0.05 (increase precision)
2. **Add query classifier** to pre-filter tools
3. **Enhance tool descriptions** with more explicit keywords
4. **Strengthen system prompt** with decision tree logic

### Issue: No Tool Calls Made

**Symptoms**:
- LLM responds without calling any tools
- `response.tool_calls` is empty

**Solutions**:
1. **Check model capabilities**: `ollama show qwen2.5:7b` should show "tools"
2. **Verify LangChain version**: `langchain-ollama>=0.2.0` required
3. **Check tool binding**: Ensure `llm.bind_tools(tools)` is called
4. **Review system prompt**: May be too permissive about answering without tools

### Issue: Tool Arguments Invalid

**Symptoms**:
- Tools are called but with wrong or missing arguments
- Pydantic validation errors

**Solutions**:
1. **Add examples to tool descriptions** showing correct argument formats
2. **Use type hints and descriptions** for all tool parameters
3. **Add argument validation** with clear error messages
4. **Lower temperature** to increase precision in argument formatting

---

## Performance Optimization

### Response Time Targets
- Single tool call: < 2 seconds
- Multi-step queries: < 5 seconds
- Complex aggregations: < 3 seconds

### Optimization Strategies

1. **Limit Context Length**
   ```python
   # Keep conversation history manageable
   messages = messages[-10:]  # Last 10 messages only
   ```

2. **Use Streaming**
   ```python
   # Stream tokens as they're generated
   for chunk in llm_with_tools.stream(messages):
       yield chunk
   ```

3. **Cache Embeddings**
   ```python
   # Cache tool embeddings for semantic search
   @lru_cache(maxsize=100)
   def get_tool_embedding(tool_description: str):
       return embed_model.encode(tool_description)
   ```

4. **Parallel Tool Calls**
   ```python
   # If multiple tools needed, execute in parallel
   async def execute_tools(tool_calls):
       tasks = [execute_tool(tc) for tc in tool_calls]
       return await asyncio.gather(*tasks)
   ```

---

## Production Considerations

### Monitoring Metrics

Track these metrics in production:

- **Tool Selection Accuracy**: % of queries where correct tool was selected
- **Tool Call Success Rate**: % of tool calls that executed successfully
- **Average Response Time**: By tool type
- **Classification Confidence**: Distribution of confidence scores
- **Tool Usage Distribution**: Which tools are most/least used

### Error Handling

```python
def execute_tool_with_fallback(tool_call, fallback_tool):
    """Execute tool with fallback if primary tool fails."""
    try:
        return tool_call.execute()
    except Exception as e:
        logger.error(f"Tool {tool_call.name} failed: {e}")
        logger.info(f"Falling back to {fallback_tool.name}")
        return fallback_tool.execute()
```

### Logging Best Practices

```python
logger.info(
    "Tool Selection",
    extra={
        "query": user_message,
        "intent": classification["intent"],
        "confidence": classification["confidence"],
        "recommended_tools": classification["recommended_tools"],
        "tools_presented": [t.name for t in tools],
        "tools_called": [tc.name for tc in response.tool_calls],
        "selection_correct": (
            response.tool_calls[0].name in classification["recommended_tools"]
        ),
    }
)
```

---

## References

### Official Documentation
- [Qwen Function Calling](https://qwen.readthedocs.io/en/latest/framework/function_call.html)
- [Qwen Ollama Integration](https://qwen.readthedocs.io/en/latest/run_locally/ollama.html)
- [LangChain Tool Calling](https://python.langchain.com/docs/concepts/tool_calling/)
- [ChatOllama API](https://python.langchain.com/api_reference/ollama/chat_models/langchain_ollama.chat_models.ChatOllama.html)

### Additional Resources
- [Ollama Tool Calling Blog](https://ollama.com/blog/streaming-tool)
- [Qwen Model Library](https://ollama.com/library/qwen2.5)
- [Qwen Tool Calling Best Practices](https://modelscope-agent.readthedocs.io/en/stable/llms/qwen2_tool_calling.html)

---

## Appendix: Model Specifications

```
Model: qwen2.5:7b
Architecture: qwen2
Parameters: 7.6B
Context Length: 32768 tokens
Embedding Length: 3584
Quantization: Q4_K_M
Capabilities: completion, tools ✅
License: Apache 2.0
```

---

**Questions or Issues?**

If you encounter tool calling issues not covered here, check:
1. Qwen model capabilities: `ollama show qwen2.5:7b`
2. LangChain version: `pip show langchain-ollama`
3. Tool descriptions for clarity and keyword coverage
4. System prompt for explicit guidance
5. Temperature setting (should be ≤0.15)
