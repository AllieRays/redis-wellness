# Qwen 2.5 7B Tool Calling Implementation Plan

**Author**: Senior Engineering Analysis
**Date**: 2025-10-20
**Status**: Design Review
**Purpose**: Production-ready tool calling for demo environment

---

## Executive Summary

This document provides a comprehensive implementation plan for fixing tool calling issues with Qwen 2.5 7B in the Redis Wellness application. The current system successfully calls tools but exhibits **poor tool selection** - the LLM consistently chooses `search_health_records_by_metric` even for explicit aggregation queries that should use `aggregate_metrics`.

### Problem Statement

**Observed Behavior**:
- User query: "what was my average heart rate last week?"
- **Expected**: LLM calls `aggregate_metrics` tool
- **Actual**: LLM calls `search_health_records_by_metric` and manually analyzes data in response
- **Impact**: New `aggregate_metrics` tool is never used, defeating its purpose

**Root Cause Analysis**:
1. **Tool selection guidance insufficient** - System prompt doesn't strongly differentiate tool use cases
2. **Possible format mismatch** - LangChain's `bind_tools()` may not align with Qwen's native tool calling format
3. **Temperature too high** - Using 0.1, should be ≤0.15 for tool calling (per Qwen docs)
4. **Lack of tool routing** - No explicit tool selection logic before LLM invocation

---

## Current Architecture Review

### ✅ What's Working

1. **Tool Infrastructure**
   - `backend/src/agents/tool_wrappers.py:164-397` - User-bound tool creation works
   - `backend/src/agents/health_rag_agent.py:131` - `bind_tools()` succeeds
   - Tools execute correctly when called
   - LangGraph workflow functions properly

2. **Model Capabilities**
   ```bash
   $ ollama show qwen2.5:7b
   Capabilities: completion, tools  ✅
   ```

3. **Tech Stack**
   - `langchain-ollama>=0.2.0` - Latest LangChain Ollama integration
   - `langgraph>=0.2.0` - Agentic workflow orchestration
   - Qwen 2.5 7B Instruct - Confirmed tool calling support

### ❌ What's Broken

1. **Tool Selection Logic**
   - LLM cannot distinguish between `search_health_records_by_metric` (data retrieval) and `aggregate_metrics` (statistics)
   - System prompt provides guidance but LLM ignores it
   - No fallback mechanism when wrong tool is selected

2. **Temperature Configuration**
   - `backend/src/agents/health_rag_agent.py:73` - `temperature=0.1`
   - Qwen docs recommend ≤0.15 **but specifically for tool calling** scenarios
   - Need to verify if this affects tool selection vs. argument filling

3. **Tool Descriptions**
   - Current descriptions may not be distinctive enough
   - LangChain converts Python docstrings → JSON schema → Ollama format
   - Potential loss of semantic meaning in conversion chain

---

## Research Findings: Qwen 2.5 Tool Calling Best Practices

### Official Qwen Recommendations

1. **Use Hermes-Style Tool Templates**
   - Qwen 2.5 was pre-trained with function calling templates
   - Hermes format maximizes function calling performance
   - Ollama supports this via `--tool-call-parser hermes` (vLLM deployment)

2. **Temperature Settings**
   - Tool calling requires **significantly reduced temperature (0.15 or lower)**
   - Rationale: Tool selection prioritizes accuracy/reliability
   - Model must confidently select correct tool and format call precisely

3. **Tool Library Management**
   - **Problem**: Large tool libraries (dozens+ tools) cause performance degradation
   - **Solution**: Add tool routing/retrieval layer before LLM
   - Filter relevant subset of tools based on query
   - Our app has 3 tools (low count) but routing would still help

4. **Avoid ReAct-Style Templates**
   - Don't use stopword-based templates for reasoning models
   - Model may output stopwords in thought section
   - Leads to unexpected tool call behavior

### LangChain + Ollama Integration Points

1. **ChatOllama.bind_tools() Format**
   - Converts LangChain tools → OpenAI-compatible JSON schema
   - Passes to Ollama API with `tools` parameter
   - Ollama adapts schema to model-specific format

2. **Known Issues (from research)**
   - Some users report empty `tool_calls` with Qwen2.5:14b + bind_tools
   - May be version-specific or configuration-dependent
   - Our logs show tools ARE being called, just wrong selection

3. **No tool_choice Parameter**
   - ChatOllama doesn't support OpenAI's `tool_choice` parameter
   - Cannot force LLM to use specific tool
   - Must rely entirely on prompting + tool descriptions

---

## Proposed Solution Architecture

### Multi-Layered Approach

```
User Query
    ↓
[1. Query Classification] ← NEW
    ↓
[2. Tool Routing Layer] ← NEW
    ↓
[3. Enhanced Tool Descriptions] ← IMPROVE
    ↓
[4. Optimized System Prompt] ← IMPROVE
    ↓
[5. Temperature Tuning] ← ADJUST
    ↓
Qwen 2.5 7B (bind_tools)
    ↓
Tool Execution
```

---

## Implementation Plan

### Phase 1: Quick Wins (1-2 hours)

**Objective**: Immediate improvements with minimal code changes

#### 1.1 Temperature Adjustment
**File**: `backend/src/agents/health_rag_agent.py:73`

```python
# CURRENT
self.llm = ChatOllama(
    model=self.settings.ollama_model,
    base_url=self.settings.ollama_base_url,
    temperature=0.1  # Low temperature for factual responses
)

# PROPOSED
self.llm = ChatOllama(
    model=self.settings.ollama_model,
    base_url=self.settings.ollama_base_url,
    temperature=0.05,  # Ultra-low for tool calling (Qwen recommendation)
    num_predict=512,   # Limit response length for tool calls
)
```

**Rationale**: Qwen documentation explicitly recommends 0.15 or lower for tool calling accuracy.

#### 1.2 Tool Description Enhancement
**File**: `backend/src/agents/tool_wrappers.py:395-404`

Make tool docstrings more distinctive and keyword-rich:

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
    - "minimum", "min", "lowest", "best", "worst", "highest", "maximum", "max"
    - "total", "sum", "count", "how many"
    - "statistics", "stats", "numbers", "calculations"

    ❌ DO NOT USE for:
    - Individual data points (use search_health_records_by_metric)
    - Viewing trends (use search_health_records_by_metric)
    - Listing all values (use search_health_records_by_metric)

    This tool performs MATHEMATICAL AGGREGATION on health metric data.
    Returns computed statistics, NOT raw data.

    Args:
        metric_types: List of metrics to aggregate ["HeartRate", "BodyMass", etc.]
        time_period: Natural language time ("last week", "September 2024")
        aggregations: Statistics to compute ["average", "min", "max", "sum", "count"]

    Returns:
        Dict with computed statistics for each metric

    Example:
        Query: "What was my average heart rate last week?"
        → This tool calculates: {average: 72.5 bpm, min: 58, max: 145}
    """
```

**Rationale**:
- Emojis for visual distinction (🔢 vs other tools)
- Explicit "USE THIS TOOL WHEN" section
- Keywords that match common query patterns
- Negative examples ("DO NOT USE for")

#### 1.3 System Prompt Strengthening
**File**: `backend/src/agents/health_rag_agent.py:223-228`

Add explicit tool selection decision tree:

```python
"📋 TOOL SELECTION DECISION TREE:",
"",
"Step 1: Identify query intent",
"  - Does query contain: 'average', 'min', 'max', 'total', 'sum', 'statistics'?",
"    → YES: Use aggregate_metrics tool",
"    → NO: Continue to Step 2",
"",
"Step 2: Check for specific values vs. aggregation",
"  - 'Show me my weight values' → search_health_records_by_metric",
"  - 'Calculate my average weight' → aggregate_metrics",
"  - 'What was my heart rate on Sept 15?' → search_health_records_by_metric",
"  - 'What was my highest heart rate in September?' → aggregate_metrics",
"",
"Step 3: When in doubt",
"  - If user wants RAW DATA → search_health_records_by_metric",
"  - If user wants COMPUTED STATISTICS → aggregate_metrics",
"  - If user wants WORKOUTS → search_workouts_and_activity",
```

**Rationale**: Explicit decision logic may help LLM make correct choice even if it doesn't "understand" nuance.

---

### Phase 2: Tool Routing Layer (2-4 hours)

**Objective**: Add pre-processing layer to select tools before LLM invocation

#### 2.1 Create Query Classifier

**New File**: `backend/src/agents/query_classifier.py`

```python
"""
Query classification for intelligent tool routing.

Uses keyword matching and pattern recognition to pre-select
appropriate tools before LLM invocation.
"""
from typing import List, Dict, Any
import re


class QueryClassifier:
    """Classify user queries to route to appropriate tools."""

    # Aggregation keywords
    AGGREGATION_KEYWORDS = [
        r'\baverage\b', r'\bmean\b', r'\bavg\b',
        r'\bminimum\b', r'\bmin\b', r'\blowest\b',
        r'\bmaximum\b', r'\bmax\b', r'\bhighest\b',
        r'\btotal\b', r'\bsum\b', r'\bcount\b',
        r'\bstatistics\b', r'\bstats\b',
        r'\bcalculate\b', r'\bcompute\b',
    ]

    # Data retrieval keywords
    RETRIEVAL_KEYWORDS = [
        r'\bshow me\b', r'\bwhat was\b', r'\blist\b',
        r'\bview\b', r'\bsee\b', r'\bdisplay\b',
        r'\btrend\b', r'\bover time\b', r'\bhistory\b',
    ]

    # Workout keywords
    WORKOUT_KEYWORDS = [
        r'\bworkout\b', r'\bexercise\b', r'\brun\b',
        r'\btrain\b', r'\bactivity\b', r'\bgym\b',
    ]

    def classify_intent(self, query: str) -> Dict[str, Any]:
        """
        Classify query intent and recommend tools.

        Args:
            query: User's natural language query

        Returns:
            Dict with:
              - intent: "aggregation", "retrieval", "workout", "unknown"
              - confidence: 0.0-1.0
              - recommended_tools: List of tool names
              - reasoning: Why this classification
        """
        query_lower = query.lower()

        # Check for aggregation intent
        aggregation_matches = sum(
            1 for pattern in self.AGGREGATION_KEYWORDS
            if re.search(pattern, query_lower)
        )

        # Check for retrieval intent
        retrieval_matches = sum(
            1 for pattern in self.RETRIEVAL_KEYWORDS
            if re.search(pattern, query_lower)
        )

        # Check for workout intent
        workout_matches = sum(
            1 for pattern in self.WORKOUT_KEYWORDS
            if re.search(pattern, query_lower)
        )

        # Decision logic
        if workout_matches > 0:
            return {
                "intent": "workout",
                "confidence": min(workout_matches / 3, 1.0),
                "recommended_tools": ["search_workouts_and_activity"],
                "reasoning": f"Query contains workout keywords (matched {workout_matches})"
            }

        if aggregation_matches > retrieval_matches and aggregation_matches > 0:
            return {
                "intent": "aggregation",
                "confidence": min(aggregation_matches / 3, 1.0),
                "recommended_tools": ["aggregate_metrics"],
                "reasoning": f"Query contains aggregation keywords (matched {aggregation_matches})"
            }

        if retrieval_matches > 0:
            return {
                "intent": "retrieval",
                "confidence": min(retrieval_matches / 3, 1.0),
                "recommended_tools": ["search_health_records_by_metric"],
                "reasoning": f"Query contains retrieval keywords (matched {retrieval_matches})"
            }

        return {
            "intent": "unknown",
            "confidence": 0.0,
            "recommended_tools": None,  # Let LLM decide
            "reasoning": "No clear keyword matches, deferring to LLM"
        }


def get_query_classifier() -> QueryClassifier:
    """Get singleton instance of query classifier."""
    return QueryClassifier()
```

#### 2.2 Integrate Classifier into Agent

**File**: `backend/src/agents/health_rag_agent.py:116-142`

```python
from .query_classifier import get_query_classifier

class HealthRAGAgent:
    def __init__(self, memory_manager=None):
        self.settings = get_settings()
        self.memory_manager = memory_manager
        self.query_classifier = get_query_classifier()  # NEW
        # ... rest of init

    def _agent_node(self, state: AgentState) -> Dict:
        """
        Main agent reasoning node with query classification.
        """
        messages = state["messages"]
        user_id = state.get("user_id", "unknown")

        # Get latest user message
        latest_message = messages[-1].content if messages else ""

        # Classify query intent
        classification = self.query_classifier.classify_intent(latest_message)

        # Create tools bound to this user
        user_tools = create_user_bound_tools(user_id)

        # FILTER tools based on classification (if confident)
        if classification["confidence"] >= 0.6 and classification["recommended_tools"]:
            recommended_tool_names = set(classification["recommended_tools"])
            filtered_tools = [
                tool for tool in user_tools
                if tool.name in recommended_tool_names
            ]

            # Always include at least one tool
            tools_to_use = filtered_tools if filtered_tools else user_tools

            logger.info(f"🎯 Query classified as '{classification['intent']}' "
                       f"(confidence: {classification['confidence']:.2f}). "
                       f"Filtered to tools: {[t.name for t in tools_to_use]}")
        else:
            tools_to_use = user_tools
            logger.info(f"🤷 Low confidence classification, using all tools")

        llm_with_tools = self.llm.bind_tools(tools_to_use)

        # Add classification info to system prompt
        system_content = self._build_system_prompt(state, classification)
        system_msg = SystemMessage(content=system_content)

        messages_with_system = [system_msg] + messages

        # Call LLM with filtered tools
        response = llm_with_tools.invoke(messages_with_system)

        return {"messages": [response]}
```

**Rationale**:
- Pre-filter tools to reduce LLM's decision space
- If classifier is confident (≥0.6), only present relevant tools
- LLM can't select wrong tool if it's not in the list
- Fallback to all tools if uncertain

#### 2.3 Update System Prompt to Include Classification

**File**: `backend/src/agents/health_rag_agent.py:158`

```python
def _build_system_prompt(self, state: AgentState, classification: Dict = None) -> str:
    """
    Build system prompt with classification hints.
    """
    prompt_parts = [
        "You are a health AI assistant with access to the user's Apple Health data.",
        "",
    ]

    # Add classification guidance if available
    if classification and classification["intent"] != "unknown":
        prompt_parts.extend([
            f"🎯 QUERY ANALYSIS:",
            f"   Intent: {classification['intent']}",
            f"   Confidence: {classification['confidence']:.0%}",
            f"   Reasoning: {classification['reasoning']}",
            f"   Recommended tool: {', '.join(classification['recommended_tools']) if classification['recommended_tools'] else 'None'}",
            "",
            "⚠️ The above analysis suggests which tool to use. Follow this guidance.",
            "",
        ])

    # ... rest of system prompt
```

---

### Phase 3: Validation & Testing (2-3 hours)

**Objective**: Comprehensive testing to ensure tool selection works

#### 3.1 Create Test Suite

**New File**: `tests/test_tool_selection.py`

```python
"""
Test suite for tool selection accuracy.
"""
import pytest
from backend.src.agents.query_classifier import get_query_classifier


class TestQueryClassification:
    """Test query classifier accuracy."""

    @pytest.fixture
    def classifier(self):
        return get_query_classifier()

    def test_aggregation_queries(self, classifier):
        """Test aggregation query detection."""
        test_cases = [
            ("what was my average heart rate last week?", "aggregation"),
            ("calculate my total steps this month", "aggregation"),
            ("show me my minimum weight in September", "aggregation"),
            ("give me stats on my BMI", "aggregation"),
            ("what's the highest heart rate I had during workouts?", "aggregation"),
        ]

        for query, expected_intent in test_cases:
            result = classifier.classify_intent(query)
            assert result["intent"] == expected_intent, \
                f"Query '{query}' classified as '{result['intent']}', expected '{expected_intent}'"
            assert result["confidence"] > 0.3, \
                f"Low confidence ({result['confidence']}) for clear aggregation query"

    def test_retrieval_queries(self, classifier):
        """Test data retrieval query detection."""
        test_cases = [
            ("show me my weight in September", "retrieval"),
            ("what was my heart rate yesterday?", "retrieval"),
            ("display my BMI over the last month", "retrieval"),
            ("list my weight measurements", "retrieval"),
        ]

        for query, expected_intent in test_cases:
            result = classifier.classify_intent(query)
            assert result["intent"] == expected_intent, \
                f"Query '{query}' classified as '{result['intent']}', expected '{expected_intent}'"

    def test_workout_queries(self, classifier):
        """Test workout query detection."""
        test_cases = [
            ("when did I last work out?", "workout"),
            ("show me my recent exercise", "workout"),
            ("what workouts did I do this week?", "workout"),
        ]

        for query, expected_intent in test_cases:
            result = classifier.classify_intent(query)
            assert result["intent"] == expected_intent, \
                f"Query '{query}' classified as '{result['intent']}', expected '{expected_intent}'"
```

**Run tests**:
```bash
docker-compose exec backend pytest tests/test_tool_selection.py -v
```

#### 3.2 Integration Testing

Create test script to verify end-to-end tool selection:

**New File**: `tests/test_agent_tool_selection.py`

```python
"""
Integration tests for agent tool selection.
"""
import pytest
from backend.src.agents.health_rag_agent import HealthRAGAgent


@pytest.mark.asyncio
class TestAgentToolSelection:
    """Test that agent selects correct tools."""

    @pytest.fixture
    async def agent(self):
        return HealthRAGAgent()

    async def test_aggregate_metrics_selected(self, agent):
        """Test that aggregate_metrics is called for aggregation queries."""
        result = await agent.chat(
            message="what was my average heart rate last week?",
            user_id="your_user",
            session_id="test_aggregation"
        )

        # Check that aggregate_metrics was called
        tool_names = [t["name"] for t in result.get("tools_used", [])]
        assert "aggregate_metrics" in tool_names, \
            f"Expected aggregate_metrics, got: {tool_names}"

        # Ensure search_health_records_by_metric was NOT called
        assert "search_health_records_by_metric" not in tool_names, \
            "Should not call search_health_records_by_metric for aggregation query"

    async def test_search_records_selected(self, agent):
        """Test that search_health_records_by_metric is called for retrieval queries."""
        result = await agent.chat(
            message="show me my weight in September",
            user_id="your_user",
            session_id="test_retrieval"
        )

        tool_names = [t["name"] for t in result.get("tools_used", [])]
        assert "search_health_records_by_metric" in tool_names, \
            f"Expected search_health_records_by_metric, got: {tool_names}"
```

**Run tests**:
```bash
docker-compose exec backend pytest tests/test_agent_tool_selection.py -v
```

---

### Phase 4: Monitoring & Observability (1-2 hours)

**Objective**: Add detailed logging to track tool selection decisions

#### 4.1 Enhanced Logging

**File**: `backend/src/agents/health_rag_agent.py`

Add structured logging for all tool selection decisions:

```python
import logging
import json

logger = logging.getLogger(__name__)

class HealthRAGAgent:
    def _agent_node(self, state: AgentState) -> Dict:
        # ... existing code

        # Log query classification
        logger.info(
            "Tool Selection Decision",
            extra={
                "query": latest_message,
                "classification": classification,
                "tools_presented": [t.name for t in tools_to_use],
                "user_id": user_id,
                "session_id": state.get("session_id"),
            }
        )

        response = llm_with_tools.invoke(messages_with_system)

        # Log actual tool calls made
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(
                "Tool Calls Made",
                extra={
                    "query": latest_message,
                    "tools_called": [tc.get("name") for tc in response.tool_calls],
                    "classification_correct": (
                        response.tool_calls[0].get("name") in
                        (classification.get("recommended_tools") or [])
                    ),
                }
            )

        return {"messages": [response]}
```

#### 4.2 Metrics Dashboard

Add endpoint to track tool selection accuracy:

**New File**: `backend/src/api/metrics_routes.py`

```python
"""
Metrics API for monitoring tool selection performance.
"""
from fastapi import APIRouter
from typing import Dict, Any
import json

router = APIRouter(prefix="/metrics", tags=["Metrics"])

# In-memory metrics store (replace with Redis in production)
tool_selection_metrics = {
    "total_queries": 0,
    "tool_calls_by_name": {},
    "classification_accuracy": 0.0,
}


@router.get("/tool-selection")
async def get_tool_selection_metrics() -> Dict[str, Any]:
    """
    Get tool selection performance metrics.

    Returns metrics on:
    - Tool call distribution
    - Classification accuracy
    - Common query patterns
    """
    return tool_selection_metrics


@router.post("/tool-selection/record")
async def record_tool_selection(data: Dict[str, Any]):
    """Record a tool selection event for metrics."""
    tool_selection_metrics["total_queries"] += 1

    tool_name = data.get("tool_name")
    if tool_name:
        tool_selection_metrics["tool_calls_by_name"][tool_name] = \
            tool_selection_metrics["tool_calls_by_name"].get(tool_name, 0) + 1

    return {"status": "recorded"}
```

---

## Alternative Approaches (If Phases 1-2 Don't Work)

### Option A: Use Ollama Functions Instead of bind_tools

LangChain provides `OllamaFunctions` wrapper that may have better Qwen compatibility:

```python
from langchain_experimental.llms import OllamaFunctions

# Replace ChatOllama with OllamaFunctions
self.llm = OllamaFunctions(
    model=self.settings.ollama_model,
    base_url=self.settings.ollama_base_url,
    temperature=0.05,
    format="json",  # Enforce JSON responses
)
```

**Tradeoffs**:
- ✅ May have better tool format compatibility
- ❌ Experimental package, less maintained
- ❌ Requires code refactoring

### Option B: ReAct-Style Prompting (Not Recommended)

Manually implement ReAct pattern with explicit tool selection in prompt:

```
Thought: I need to calculate an average, so I should use aggregate_metrics.
Action: aggregate_metrics
Action Input: {"metric_types": ["HeartRate"], ...}
```

**Tradeoffs**:
- ✅ Full control over tool selection logic
- ❌ Fragile (stopwords in thought can break parsing)
- ❌ Qwen docs explicitly recommend against this
- ❌ More prompt engineering work

### Option C: Use Different Model

Switch to a model with better native tool calling support:

- `llama3.1:70b` - Larger model, better reasoning
- `mistral:7b-instruct-v0.3` - Known good tool calling
- `deepseek-coder:6.7b` - Excellent structured output

**Tradeoffs**:
- ✅ May immediately fix tool selection
- ❌ Defeats purpose of using Qwen 2.5 for demo
- ❌ Different model = different characteristics

---

## Success Criteria

### Minimum Viable Success

1. **Aggregation Query Test**: "What was my average heart rate last week?"
   - ✅ Calls `aggregate_metrics` tool
   - ✅ Returns computed statistics (not raw data analysis)
   - ✅ Response time < 3 seconds

2. **Retrieval Query Test**: "Show me my weight in September"
   - ✅ Calls `search_health_records_by_metric` tool
   - ✅ Returns list of data points with dates
   - ✅ Response time < 3 seconds

3. **Workout Query Test**: "When did I last work out?"
   - ✅ Calls `search_workouts_and_activity` tool
   - ✅ Returns workout information
   - ✅ Response time < 2 seconds

### Production-Ready Success

1. **Tool Selection Accuracy**: ≥90% correct tool selection on test set of 50 queries
2. **No Regressions**: Existing working queries continue to work
3. **Monitoring**: All tool selection decisions logged with structured data
4. **Tests**: ≥80% test coverage on new classification logic
5. **Documentation**: Updated with troubleshooting guide

---

## Implementation Timeline

| Phase | Duration | Blocker Dependencies |
|-------|----------|---------------------|
| Phase 1: Quick Wins | 1-2 hours | None - can start immediately |
| Phase 2: Tool Routing | 2-4 hours | Phase 1 complete |
| Phase 3: Testing | 2-3 hours | Phase 2 complete |
| Phase 4: Monitoring | 1-2 hours | Can parallelize with Phase 3 |
| **Total** | **6-11 hours** | Sequential recommended |

### Recommended Execution Order

1. **Start with Phase 1** (Quick Wins)
   - Low risk, immediate potential benefit
   - Can validate if simple changes solve the problem
   - Test after each change

2. **If Phase 1 insufficient → Phase 2** (Tool Routing)
   - Higher effort but more reliable
   - Explicit query classification reduces LLM uncertainty
   - Provides fallback if LLM makes wrong choice

3. **Phase 3 mandatory** (Testing)
   - Ensures changes don't break existing functionality
   - Validates improvements quantitatively
   - Creates regression test suite for future

4. **Phase 4 optional for demo** (Monitoring)
   - Important for production
   - Can defer if time-constrained
   - Helps debug issues if they arise later

---

## Risk Assessment

### High Risk Items

1. **Temperature Changes**
   - **Risk**: Too low temperature → generic/repetitive responses
   - **Mitigation**: Test with various queries, increase to 0.1 if quality degrades
   - **Rollback**: Easy - one line change

2. **Tool Filtering (Phase 2)**
   - **Risk**: Classifier wrongly excludes correct tool → agent cannot answer
   - **Mitigation**: Confidence threshold (≥0.6) prevents overly aggressive filtering
   - **Rollback**: Set confidence threshold to 1.0 (effectively disables filtering)

### Medium Risk Items

1. **Tool Description Changes**
   - **Risk**: New descriptions confuse LLM differently
   - **Mitigation**: A/B test old vs. new descriptions
   - **Rollback**: Revert docstrings

2. **System Prompt Expansion**
   - **Risk**: Too much information → LLM attention dilution
   - **Mitigation**: Keep additions concise, use clear structure
   - **Rollback**: Git revert

### Low Risk Items

1. **Logging/Monitoring**
   - **Risk**: Minimal (observability only)
   - **Mitigation**: N/A
   - **Rollback**: Remove log statements

---

## Rollback Plan

If implementation fails or causes regressions:

### Immediate Rollback (< 5 minutes)
```bash
# Revert all changes
git reset --hard HEAD~1

# Restart backend
docker-compose restart backend
```

### Partial Rollback

1. **Phase 1 only**: Revert `health_rag_agent.py` temperature to 0.1
2. **Phase 2 only**: Set classifier confidence threshold to 1.0 (disables filtering)
3. **Phase 3**: Delete test files (no production impact)
4. **Phase 4**: Comment out extra logging

---

## Appendix A: Tool Descriptions Comparison

### Current vs. Proposed

#### Current (Insufficient)
```python
@tool
def aggregate_metrics(...):
    """
    Calculate statistics (avg, min, max, sum, count) over health metric data.
    Use this when the user asks for averages, min/max, totals, statistics...
    """
```

#### Proposed (Enhanced)
```python
@tool
def aggregate_metrics(...):
    """
    🔢 CALCULATE STATISTICS: Average, Min, Max, Sum, Count over health metrics.

    ⚠️ USE THIS TOOL WHEN USER ASKS FOR:
    - "average", "mean", "avg"
    - "minimum", "min", "lowest", "best", "worst", "highest", "maximum", "max"
    ...

    ❌ DO NOT USE for:
    - Individual data points (use search_health_records_by_metric)
    ...
    """
```

**Key Improvements**:
1. Visual distinction (🔢 emoji)
2. Explicit "USE THIS TOOL WHEN" section
3. Keyword-rich (matches natural query patterns)
4. Negative examples (what NOT to use this for)
5. Example query → tool output

---

## Appendix B: Qwen 2.5 Model Specifications

```
Model: qwen2.5:7b
Architecture: qwen2
Parameters: 7.6B
Context Length: 32768 tokens
Embedding Length: 3584
Quantization: Q4_K_M
Capabilities: completion, tools ✅
System Prompt: "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
License: Apache 2.0
```

---

## Appendix C: Current Tech Stack

```toml
# backend/pyproject.toml
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "redis>=5.0.0",
    "redisvl>=0.2.0",
    "pydantic>=2.4.0",
    "pydantic-settings>=2.0.0",
    "python-multipart>=0.0.6",
    "httpx>=0.25.0",
    "python-dotenv>=1.0.0",
    # AI/ML dependencies
    "langgraph>=0.2.0",         ← LangGraph for agent workflow
    "langchain>=0.3.0",         ← LangChain core
    "langchain-core>=0.3.0",    ← LangChain primitives
    "langchain-ollama>=0.2.0",  ← Ollama integration (ChatOllama)
    # Embedding models for RAG
    "sentence-transformers>=3.0.0",
    "numpy>=1.24.0",
]
```

---

## Appendix D: References

1. **Qwen Official Documentation**
   - Function Calling: https://qwen.readthedocs.io/en/latest/framework/function_call.html
   - Ollama Integration: https://qwen.readthedocs.io/en/latest/run_locally/ollama.html

2. **LangChain Documentation**
   - Tool Calling Concept: https://python.langchain.com/docs/concepts/tool_calling/
   - ChatOllama Reference: https://python.langchain.com/api_reference/ollama/chat_models/langchain_ollama.chat_models.ChatOllama.html

3. **Ollama Resources**
   - Tool Calling Blog: https://ollama.com/blog/streaming-tool
   - Model Library: https://ollama.com/library/qwen2.5

4. **Research & Best Practices**
   - Qwen Tool Calling Service Best Practices: https://modelscope-agent.readthedocs.io/en/stable/llms/qwen2_tool_calling.html
   - DeepWiki Qwen 2.5 Function Calling: https://deepwiki.com/QwenLM/Qwen2.5/2.2-function-calling-and-tool-use

---

## Questions for Review

Before implementation, consider:

1. **Is demo correctness more important than speed?**
   - If yes → Implement all phases
   - If no → Quick wins (Phase 1) only

2. **What is acceptable tool selection accuracy?**
   - 90%? (Recommended for demo)
   - 100%? (May require more sophisticated routing)

3. **Should we add telemetry/metrics even for demo?**
   - Pro: Shows engineering rigor
   - Con: Extra work with no user-facing benefit

4. **Fallback strategy if Qwen tool calling fundamentally broken?**
   - Switch models? (defeats Qwen demo purpose)
   - Manual tool routing only? (no LLM tool selection)

---

**End of Document**
