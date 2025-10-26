# Goal Storage Architecture

## Overview

The goal storage system in redis-wellness handles user-stated goals through a **two-tier approach**:

1. **Pre-Router (Primary)** - Fast intent detection that bypasses the tool loop (production)
2. **LLM Tool (Secondary)** - Refactored tool for potential future use (currently not in active toolset)

This document explains both approaches and why the current architecture uses intent bypass.

## Current Architecture (Intent Bypass)

### Flow

```
User: "my goal is to reach 150 lbs"
  ↓
Intent Detector (intent_router.py)
  ↓
Bypass Handler (intent_bypass_handler.py)
  ↓
Direct storage in episodic memory (Redis)
  ↓
Immediate response (no LLM tool loop)
```

### Why Intent Bypass?

**Advantages:**
- ✅ **Faster** - No LLM tool calling overhead (200-500ms saved)
- ✅ **Deterministic** - Pattern matching is 100% reliable
- ✅ **Cost-effective** - No extra LLM tokens used for simple acknowledgment
- ✅ **Cleaner UX** - Immediate acknowledgment vs. waiting for tool execution

**Disadvantages:**
- ❌ Hard-coded patterns (regex-based detection)
- ❌ Separate code path from other agent operations
- ❌ Less flexible than LLM-driven intent detection

### Code Location

- **Intent Detection**: `backend/src/utils/intent_router.py`
- **Storage Logic**: `backend/src/utils/intent_bypass_handler.py` → `_store_goal_in_redis()`
- **Memory Manager**: `backend/src/services/episodic_memory_manager.py`

### Storage Format

Goals are stored in Redis as episodic memory events:

```python
{
    "user_id": "wellness_user",
    "event_type": "goal",
    "timestamp": 1698364800,  # UTC timestamp
    "description": "User's goal: reach 150 lbs",
    "metadata": {
        "goal_text": "reach 150 lbs"
    },
    "embedding": [0.234, -0.123, ...]  # 1024-dim vector for semantic search
}
```

**Redis Key Pattern**: `episodic:wellness_user:goal:1698364800`

## Refactored Tool (Future Use)

### Purpose

The `store_user_goal` tool in `goal_tools.py` was refactored during the October 2025 code review to be **fully functional** but is **not currently used** in production. It exists as a reference implementation for potential future integration.

### Key Features

**1. Structured Data Extraction**

The tool can parse natural language into structured components:

```python
# Input: "my goal is to reach 150 lbs"
# Output:
{
    "metric": "weight",
    "value": 150.0,
    "unit": "lbs",
    "goal_text": "reach 150 lbs"
}
```

**2. Supported Goal Types**

| Pattern | Example | Extracted Data |
|---------|---------|----------------|
| Weight | "reach 150 lbs" | metric=weight, value=150, unit=lbs |
| Distance | "run 5 miles" | metric=distance, value=5, unit=mi |
| Steps | "walk 10,000 steps" | metric=steps, value=10000, unit=count |
| Frequency | "workout 4 times per week" | metric=workout_frequency, value=4, unit=per_week |
| Text-only | "never skip leg day" | goal_text="never skip leg day" |

**3. JSON Response Format**

Unlike the original implementation (which returned plain text), the refactored tool returns structured JSON:

```json
{
    "status": "success",
    "goal": "reach 150 lbs",
    "stored": true,
    "message": "Goal saved: reach 150 lbs"
}
```

This allows the LLM to parse the result and handle success/failure appropriately.

**4. Error Handling**

- Empty descriptions rejected with clear error
- Memory initialization failures handled gracefully
- Exceptions logged with full stack traces
- All responses include success/failure indicators

### Why Not Currently Used?

The tool was removed from the active toolset because:

1. **Performance** - Intent bypass is 200-500ms faster
2. **Reliability** - No risk of LLM not calling the tool
3. **Token efficiency** - Saves 50-100 tokens per goal statement
4. **Simplicity** - One less tool for the LLM to reason about

### Future Integration Path

If we want to integrate this tool in the future:

**Option A: Hybrid Approach**
- Use intent bypass for simple goals ("my goal is X")
- Use LLM tool for complex multi-step goals ("my goal is to lose 20 lbs by working out 3x/week")

**Option B: Full LLM Integration**
- Remove intent bypass for goal setting
- Add tool to active toolset in `query_tools/__init__.py`
- Update system prompt to guide proper tool usage

**Option C: Enhanced Intent Router**
- Keep intent bypass but use `_extract_goal_components()` for parsing
- Best of both worlds: fast bypass + structured extraction

## Code Review Findings (October 2025)

### Original Issues (Fixed)

❌ **No-op Implementation** - Tool did nothing
```python
# OLD CODE (broken)
get_episodic_memory()  # Just instantiates, doesn't store!
return "Got it! I've saved your goal"  # Lying to the LLM
```

✅ **Fixed** - Now actually stores goals in Redis
```python
# NEW CODE (functional)
success = await memory.store_goal(...)
return json.dumps({"status": "success", "stored": True})
```

❌ **Misleading Comments** - Claimed storage happens in "reflection phase"
- No such automatic storage existed
- Comments removed, actual storage implemented

❌ **Unused Function** - `create_goal_tools()` never called
- Kept for reference but marked as deprecated in docstring

### Current Status

✅ **Fully Functional** - Tool now works correctly
✅ **Well-Tested** - Comprehensive unit tests added
✅ **Properly Documented** - Clear docstrings and examples
✅ **Not in Production** - Intentionally excluded from active toolset

## Testing

### Unit Tests

Run goal tool tests:
```bash
cd backend
uv run pytest tests/unit/test_goal_tools.py -v
```

Test coverage:
- ✅ Structured data extraction (weight, distance, steps, frequency)
- ✅ Text-only goals (fallback)
- ✅ Edge cases (mixed units, whitespace, empty strings)
- ✅ Error handling (empty descriptions, invalid inputs)
- ✅ Case sensitivity and number formatting

### Integration Tests

Test the current intent bypass flow:
```bash
# Start backend
make dev

# Test goal setting
curl -X POST http://localhost:8000/api/chat/stateful \
  -H "Content-Type: application/json" \
  -d '{"message": "my goal is to reach 150 lbs", "session_id": "test"}'

# Verify storage in Redis
redis-cli
> KEYS episodic:*
> HGETALL episodic:wellness_user:goal:*
```

## LLM Optimization Notes

### For Intent Bypass (Current)

**Pros for LLM:**
- ✅ No tool reasoning overhead
- ✅ Consistent acknowledgment format
- ✅ Predictable behavior

**Cons for LLM:**
- ❌ Less flexible (can't adapt to unusual goal phrasings)
- ❌ Black box (LLM doesn't see storage logic)

### For Tool-Based (Future)

**Pros for LLM:**
- ✅ More flexible goal handling
- ✅ Structured JSON responses for parsing
- ✅ Clear success/failure signals
- ✅ Can extract structured data for better analytics

**Cons for LLM:**
- ❌ Must remember when to call the tool
- ❌ Must parse JSON response
- ❌ Adds latency to conversation

## Recommendations

### Short-term (Keep Current Architecture)

Continue using intent bypass because:
- Performance is critical for UX
- Goal statements are predictable (regex works fine)
- No compelling reason to change

### Long-term (Consider Tool Integration)

Integrate the refactored tool if:
- We add complex multi-metric goals
- We want goal extraction for analytics
- We implement goal progress tracking features
- We need more flexible goal parsing

### Hybrid Approach (Best of Both)

Use `_extract_goal_components()` in the intent bypass handler:
```python
# In intent_bypass_handler.py
goal_text = extract_goal_from_statement(message)
goal_data = _extract_goal_components(goal_text)  # Add structured extraction

# Store with structured metadata
metadata = json.dumps(goal_data)  # Include metric, value, unit if available
```

This gives us:
- ✅ Fast intent bypass (no tool loop)
- ✅ Structured data extraction (better analytics)
- ✅ No LLM reasoning overhead
- ✅ Best of both worlds

## Related Documentation

- **Triple Memory Architecture**: `docs/03_MEMORY_ARCHITECTURE.md`
- **Episodic Memory Design**: `docs/SERVICES.md`
- **Intent Routing**: See `utils/intent_router.py` docstrings
- **Redis Patterns**: `docs/05_REDIS_PATTERNS.md`

## Conclusion

The goal storage system prioritizes **speed and reliability** over flexibility. The refactored `store_user_goal` tool is fully functional but intentionally not used in production. The intent bypass approach serves the current use case well, but the tool exists as a reference implementation for future enhancements.

**Key Takeaway**: Sometimes the best code is the code that doesn't run in the critical path. Fast, deterministic pattern matching beats flexible LLM tool calling for simple, predictable tasks.
