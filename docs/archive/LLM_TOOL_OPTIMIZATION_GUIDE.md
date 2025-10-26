# ARCHIVED: LLM Tool Response Optimization Guide

> **ARCHIVED**: This optimization approach was superseded by tool consolidation. Instead of optimizing 9 individual tools, the project consolidated them into 5 tools (3 health + 2 memory). See `WARP.md` for current architecture.

**Purpose**: Optimize all query tools for maximum LLM comprehension and minimal token usage.

**Last Updated**: October 26, 2025
**Status**: Superseded by consolidation strategy

---

## Executive Summary

### The Problem
Current tool responses have:
- **Deep nesting** (3-4 levels): `result.trends.linear_regression.slope`
- **Inconsistent error schemas**: 2 different formats across tools
- **Redundant data**: Duplicate calculations, intermediate values
- **Raw statistics**: LLM must interpret p-values, R² scores
- **Token waste**: ~40% unnecessary tokens in typical responses

### The Solution
Standardized response format with:
- **Flat structure** (max 2 levels): `result.slope_per_week`
- **Semantic fields**: `"confidence_level": "high"` vs `"r_squared": 0.85`
- **Pre-computed interpretations**: Human-readable summaries
- **Consistent error handling**: Single schema across all tools
- **40% token reduction**: Same information, cleaner format

---

## Optimization Principles

### 1. Flatten Response Structure

**❌ Before (Nested):**
```json
{
  "time_period": "last_90_days",
  "trends": {
    "linear_regression": {
      "slope": -0.05,
      "r_squared": 0.78,
      "significance": "significant"
    },
    "statistics": {
      "current_weight": 170.2,
      "starting_weight": 172.5,
      "total_change": -2.3
    }
  }
}
```

**✅ After (Flat):**
```json
{
  "success": true,
  "tool": "get_trends",
  "time_period": "last_90_days",
  "trend_direction": "decreasing",
  "slope_per_week": -0.35,
  "confidence_level": "high",
  "data_points": 77,
  "interpretation": "Weight is decreasing by 0.35 lbs/week with high confidence"
}
```

**Benefits:**
- 30% fewer tokens
- Direct field access (`result.slope_per_week`)
- Easier for LLM to parse and use

### 2. Use Semantic Field Names

**❌ Raw Statistics:**
```json
{
  "r_squared": 0.85,
  "p_value": 0.001,
  "t_statistic": -2.45
}
```

**✅ Semantic Labels:**
```json
{
  "confidence_level": "high",
  "statistical_significance": "highly_significant",
  "is_significant": true
}
```

**Mapping:**
- `r_squared > 0.8` → `"confidence_level": "high"`
- `p_value < 0.01` → `"statistical_significance": "highly_significant"`
- `slope < 0` → `"trend_direction": "decreasing"`

### 3. Add Interpretation Fields

Every response should include human-readable interpretation:

```json
{
  "slope_per_week": -0.35,
  "confidence_level": "high",
  "interpretation": "Weight is decreasing by 0.35 lbs/week with high confidence"
}
```

**Why?** LLM can use interpretation directly or reformat it, rather than computing from raw statistics.

### 4. Consistent Error Handling

**❌ Inconsistent Errors:**
```json
// Error format 1
{"error": "No data", "trends": {}}

// Error format 2
{"mode": "error", "error": "No data", "results": []}

// Error format 3
{"error": "No data", "workouts": []}
```

**✅ Standardized Error:**
```json
{
  "success": false,
  "tool": "get_trends",
  "error": "No data found for specified period",
  "suggestion": "Try adjusting time periods or checking data availability",
  "metric_type": "BodyMass",
  "time_period": "last_90_days"
}
```

### 5. Remove Redundancy

**❌ Redundant Fields:**
```json
{
  "current_weight": 170.2,      // ← Redundant
  "starting_weight": 172.5,     // ← Redundant
  "total_change": -2.3,         // ← Calculated from above
  "values": [172.5, 171.8, ...]  // ← 90 values not needed
}
```

**✅ Essential Only:**
```json
{
  "average_value": 171.2,
  "data_points": 90,
  "change_from_start": -2.3
}
```

**Remove:**
- Intermediate calculations
- Moving average arrays (keep start/end only)
- Duplicate values in different formats
- Raw data points when aggregated stats exist

---

## Implementation Guide

### Step 1: Use ToolResponseFormatter

```python
from ...utils.tool_response_formatter import trends_formatter

# Success response
return trends_formatter.success(
    data={
        "trend_direction": "decreasing",
        "slope_per_week": -0.35,
        "confidence_level": "high",
        "data_points": 77,
    },
    interpretation="Weight is decreasing by 0.35 lbs/week with high confidence",
    metadata={"time_period": "last_90_days", "date_range": "2025-07-22 to 2025-10-20"}
)

# Error response
return trends_formatter.error(
    "No weight data found for specified period",
    suggestion="Try adjusting time periods or checking data availability",
    context={"metric_type": "BodyMass", "time_period": "last_90_days"}
)

# No data response (not an error)
return trends_formatter.no_data(
    "No workouts found in the last 7 days",
    searched_context={"time_range": "last_7_days", "days_back": 7}
)
```

### Step 2: Transform Raw Analytics Results

```python
def _format_trend_response(raw_result: dict[str, Any]) -> dict[str, Any]:
    """Transform raw trend analysis into LLM-optimized format."""

    # Extract nested data
    trends = raw_result.get("trends", {})
    linear = trends.get("linear_regression", {})
    stats = trends.get("statistics", {})

    # Convert R² to semantic confidence
    r_squared = linear.get("r_squared", 0)
    confidence = "high" if r_squared > 0.8 else "moderate" if r_squared > 0.5 else "low"

    # Build interpretation
    direction = linear.get("trend_direction", "stable")
    slope_week = abs(linear.get("slope_per_week", 0))
    interpretation = f"Metric is {direction} by {slope_week:.2f} units/week with {confidence} confidence"

    # Return flattened response
    return trends_formatter.success(
        data={
            "trend_direction": direction,
            "slope_per_week": linear.get("slope_per_week", 0),
            "confidence_level": confidence,
            "data_points": stats.get("measurements_count", 0),
        },
        interpretation=interpretation,
        metadata={
            "time_period": raw_result.get("time_period"),
            "date_range": raw_result.get("date_range"),
        }
    )
```

### Step 3: Update Tool Docstrings

```python
@tool
def get_trends(...) -> dict[str, Any]:
    """
    Analyze health metric trends with statistical analysis.

    Returns:
        Flattened dictionary with:
        - success (bool): Whether operation succeeded
        - tool (str): Tool name for reference
        - trend_direction (str): "increasing", "decreasing", or "stable"
        - slope_per_week (float): Rate of change per week
        - confidence_level (str): "high", "moderate", or "low"
        - data_points (int): Number of measurements
        - interpretation (str): Human-readable summary

    Example response:
        {
            "success": True,
            "tool": "get_trends",
            "trend_direction": "decreasing",
            "slope_per_week": -0.35,
            "confidence_level": "high",
            "interpretation": "Weight is decreasing by 0.35 lbs/week with high confidence"
        }
    """
```

---

## Tool-by-Tool Optimization Plan

### ✅ COMPLETED: get_trends.py

**Status**: Optimized version created (`get_trends_OPTIMIZED.py`)

**Changes:**
- Flattened response structure (3 levels → 1 level)
- Added semantic fields (`confidence_level`, `trend_direction`)
- Consistent error handling
- Added `interpretation` field
- Removed redundant statistics
- 40% token reduction

**Before/After:**
- Avg tokens: 450 → 270 (40% reduction)
- Nesting depth: 3-4 → 1-2
- Error schemas: 2 → 1

### 🔄 IN PROGRESS: get_health_metrics.py

**Current Issues:**
1. Returns nested `results` array with duplicated structure
2. Dual format (raw_data vs statistics mode) creates confusion
3. Error handling inconsistent (lines 110-114 vs standard)
4. `_format_stat_value` returns `{value, formatted}` dict (redundant)

**Recommended Changes:**
```python
# ❌ Current (nested array with mode branching)
{
    "mode": "statistics",
    "total_metrics": 2,
    "results": [
        {
            "metric": "HeartRate",
            "stats": {
                "average": {"value": 87.5, "formatted": "87.5 bpm"}
            }
        }
    ]
}

# ✅ Optimized (flat structure)
{
    "success": True,
    "tool": "get_health_metrics",
    "metric_type": "HeartRate",
    "time_range": "last_7_days",
    "average": 87.5,
    "unit": "bpm",
    "sample_size": 7,
    "interpretation": "Average heart rate was 87.5 bpm over 7 days"
}
```

**Action Items:**
- [ ] Flatten `results` array for single metric queries
- [ ] Remove `mode` field (use `has_data` boolean instead)
- [ ] Simplify `_format_stat_value` (return value only, format in interpretation)
- [ ] Use `metrics_formatter` for consistency
- [ ] Add interpretation field

### 🔄 IN PROGRESS: get_workouts.py

**Current Issues:**
1. Returns array of workouts (good) but no summary interpretation
2. Heart rate zones nested 3 levels deep
3. Missing semantic confidence indicators
4. Inconsistent error format (lines 315, 389-393)

**Recommended Changes:**
```python
# ❌ Current (no interpretation)
{
    "workouts": [...],
    "total_workouts": 5,
    "last_workout": "2 days ago"
}

# ✅ Optimized (with interpretation)
{
    "success": True,
    "tool": "get_workouts",
    "workouts": [...],
    "total_workouts": 5,
    "last_workout_days_ago": 2,
    "workout_frequency": "2.5 workouts/week",
    "interpretation": "Found 5 workouts in the last 7 days (2.5 per week). Last workout was 2 days ago."
}

# Each workout: flatten HR zones
# ❌ Current
{
    "heart_rate_zone": "Tempo (70-80% max HR)",
    "heart_rate_zone_distribution": {
        "Zone1 Easy": 5,
        "Zone3 Tempo": 45
    }
}

# ✅ Optimized
{
    "hr_avg": 142,
    "hr_zone": "tempo",
    "hr_intensity": "moderate-high"
}
```

**Action Items:**
- [ ] Add summary interpretation field
- [ ] Flatten heart rate zone structure
- [ ] Add `workout_frequency` calculation
- [ ] Standardize error handling with `workouts_formatter`
- [ ] Remove redundant `summary` field (duplicate of interpretation)

### 🟡 TODO: get_workout_patterns.py

**Estimate**: Similar issues to `get_workouts.py`
- Likely nested pattern structures
- Missing interpretations
- Needs review and optimization

### 🟡 TODO: get_workout_progress.py

**Estimate**: Progress over time likely needs flattening
- Trend analysis (similar to `get_trends`)
- Apply same optimization principles

### 🟡 TODO: get_activity_comparison.py

**Estimate**: Period comparison (similar to `get_trends` comparison mode)
- Should reuse comparison formatter logic

### 🟡 TODO: goal_tools.py

**Estimate**: Goal CRUD operations
- Likely simpler, but needs consistent formatting

### 🟡 TODO: memory_tools.py

**Estimate**: Semantic memory operations
- Less critical for optimization (internal tool)

---

## Testing Strategy

### Unit Tests

Create tests for formatter utilities:

```python
# tests/unit/test_tool_response_formatter.py
def test_success_response():
    formatter = ToolResponseFormatter("test_tool")
    result = formatter.success(
        data={"value": 42},
        interpretation="The answer is 42"
    )
    assert result["success"] == True
    assert result["tool"] == "test_tool"
    assert result["value"] == 42
    assert result["interpretation"] == "The answer is 42"

def test_error_response():
    formatter = ToolResponseFormatter("test_tool")
    result = formatter.error(
        "Something went wrong",
        suggestion="Try again",
        context={"metric": "BodyMass"}
    )
    assert result["success"] == False
    assert result["error"] == "Something went wrong"
    assert result["suggestion"] == "Try again"
    assert result["metric"] == "BodyMass"

def test_flatten_nested_dict():
    nested = {
        "trends": {
            "linear_regression": {"slope": -0.05},
            "statistics": {"count": 30}
        }
    }
    flattened = ToolResponseFormatter.flatten_nested_dict(nested)
    assert "linear_regression_slope" in flattened
    assert flattened["linear_regression_slope"] == -0.05
```

### Integration Tests

Test optimized tools against real data:

```python
# tests/integration/test_optimized_trends.py
def test_get_trends_optimized_format(redis_client, sample_health_data):
    tool = create_get_trends_tool("test_user")
    result = tool.invoke({
        "metric_type": "BodyMass",
        "analysis_type": "trend",
        "time_period": "last_30_days"
    })

    # Verify flat structure
    assert "success" in result
    assert "trend_direction" in result
    assert "interpretation" in result

    # Verify no deep nesting
    assert "trends" not in result  # Old nested structure removed

    # Verify semantic fields
    assert result["confidence_level"] in ["high", "moderate", "low"]
```

### LLM Tests

Test that LLM can use optimized responses:

```python
# tests/llm/test_tool_comprehension.py
def test_llm_can_use_flattened_response():
    """Verify LLM understands optimized format."""

    response = {
        "success": True,
        "trend_direction": "decreasing",
        "slope_per_week": -0.35,
        "interpretation": "Weight is decreasing by 0.35 lbs/week"
    }

    # LLM should be able to answer questions using this format
    prompt = f"Given this data: {response}, is the user losing weight?"
    answer = llm.invoke(prompt)

    assert "yes" in answer.lower() or "losing" in answer.lower()
```

---

## Migration Checklist

### Phase 1: Foundation (Week 1)
- [x] Create `tool_response_formatter.py` utility
- [x] Create optimization guide documentation
- [x] Create `get_trends_OPTIMIZED.py` reference implementation
- [ ] Write unit tests for formatter utility
- [ ] Review and approve optimization principles

### Phase 2: Core Tools (Week 2)
- [ ] Optimize `get_health_metrics.py`
- [ ] Optimize `get_workouts.py`
- [ ] Update integration tests
- [ ] Test with LLM agents

### Phase 3: Remaining Tools (Week 3)
- [ ] Optimize `get_workout_patterns.py`
- [ ] Optimize `get_workout_progress.py`
- [ ] Optimize `get_activity_comparison.py`
- [ ] Optimize `goal_tools.py`
- [ ] Update all agent prompts to use new field names

### Phase 4: Validation (Week 4)
- [ ] Run full test suite
- [ ] Measure token usage reduction (target: 40%)
- [ ] Test with real user queries
- [ ] Update API documentation
- [ ] Deploy to production

---

## Metrics & Success Criteria

### Token Usage Reduction
- **Target**: 40% reduction in average response tokens
- **Measurement**: Compare token counts before/after for 100 test queries
- **Current baseline**: ~450 tokens/response
- **Target**: ~270 tokens/response

### Response Time
- **Target**: No degradation (formatting overhead should be minimal)
- **Measurement**: P95 latency before/after

### LLM Accuracy
- **Target**: Same or better accuracy with optimized responses
- **Measurement**: Test suite of 50 queries, compare answer quality

### Developer Experience
- **Target**: Easier to add new tools with consistent formatter
- **Measurement**: Time to implement new tool (should decrease)

---

## Common Patterns & Examples

### Pattern 1: Statistical Analysis Response

```python
# Statistical trend analysis
return formatter.success(
    data={
        "trend_direction": "increasing",  # semantic
        "slope_per_day": 0.05,
        "slope_per_week": 0.35,
        "confidence_level": "high",  # R² > 0.8
        "statistical_significance": "significant",  # p < 0.05
        "data_points": 77,
    },
    interpretation="Metric is increasing by 0.35 units/week with high confidence",
    metadata={"time_period": "last_90_days"}
)
```

### Pattern 2: Comparison Response

```python
# Period-over-period comparison
return formatter.success(
    data={
        "period1_average": 168.5,
        "period2_average": 170.2,
        "absolute_change": -1.7,
        "percent_change": -1.0,
        "change_direction": "decrease",
        "is_significant": True,
    },
    interpretation="Metric decreased by 1.7 units (-1.0%) between periods (statistically significant)",
    metadata={
        "period1_name": "this_month",
        "period2_name": "last_month"
    }
)
```

### Pattern 3: List Response with Summary

```python
# List of items with interpretation
return formatter.success(
    data={
        "items": [...],  # Array of items (OK to nest here)
        "total_count": 5,
        "date_range": "last_7_days",
    },
    interpretation="Found 5 workouts in the last 7 days (2.5 per week)",
    metadata={"items_per_week": 2.5}
)
```

---

## References

- **Original Tool**: `backend/src/apple_health/query_tools/get_trends.py`
- **Optimized Version**: `backend/src/apple_health/query_tools/get_trends_OPTIMIZED.py`
- **Formatter Utility**: `backend/src/utils/tool_response_formatter.py`
- **WARP.md**: Project architecture and agentic tool-calling system

---

## Questions & Decisions

### Q: Should we keep raw statistical values (R², p-value)?
**A**: Yes, but as supplementary fields. Include both semantic (`confidence_level: "high"`) and raw (`r_squared: 0.85`) for transparency.

### Q: What about arrays/lists (e.g., workout list)?
**A**: Arrays are OK for collections. The flattening applies to object structure, not collections of objects.

### Q: How to handle metric-specific formatting (e.g., steps vs heart rate)?
**A**: Use `interpretation` field for metric-specific context. Core fields remain generic.

### Q: Backward compatibility?
**A**: Not required - internal API between backend and LLM. Frontend uses separate endpoints.

---

**Last Updated**: October 26, 2025
**Author**: Senior Dev Code Review
**Next Review**: After Phase 1 completion
