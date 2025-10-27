# Agent Comparison: Stateless vs Stateful

## Executive Summary

Both agents are designed to be **functionally identical except for memory features**. This document tracks the current state of parity and documents intentional differences.

## ✅ Core Parity (IDENTICAL)

| Feature | Implementation | Notes |
|---------|---------------|-------|
| **LLM Model** | `create_health_llm()` | Same model, temperature, settings |
| **System Prompt** | `build_base_system_prompt()` | Includes TOOL-FIRST POLICY (fixed 2025-10-25) |
| **Tools** | `create_user_bound_tools()` | Identical tool access to Apple Health data |
| **Numeric Validation** | `get_numeric_validator()` | Both detect hallucinated numbers |
| **Token Management** | `get_token_manager()` | Both track token usage |
| **Max Tool Calls** | Default: 5 | Prevents infinite loops |

## ⚠️ Known Differences (Documented)

### 1. Date Validation (Stateless Only)

**Location**: `stateless_agent.py:270-305`

**What it does**: Catches when LLM says wrong date in natural language response
- User asks: "What was my heart rate on October 15th?"
- LLM responds: "Your heart rate on October 11th was..." ❌
- Validator catches mismatch and retries

**Why different**:
- Stateless: Has date validation + retry logic
- Stateful: No date validation (relies on TOOL-FIRST POLICY to prevent hallucinations)

**Status**: Intentionally different. Stateless is working, don't touch it. TOOL-FIRST POLICY fix should prevent this issue in both agents.

### 2. Verbosity Detection (Stateless Only)

**Location**: `stateless_agent.py:61-96, 145-146`

**What it does**: Detects if user wants detailed/comprehensive response and adjusts system prompt

**Why different**:
- Stateless: Detects verbosity from query and modifies prompt
- Stateful: Uses base prompt only (no verbosity adjustment)

**Status**: Intentionally different. Would require adding `verbosity` to MemoryState and modifying `_llm_node` in stateful agent. Low priority.

### 3. Validation Retry Logic (Stateless Only)

**Location**: `stateless_agent.py:278-331`

**What it does**:
- If numeric validation score = 0, retries with correction prompt
- If date validation fails, retries with correction prompt

**Why different**:
- Stateless: Has retry loop in single function
- Stateful: Just logs warnings (no retry)
- Adding retry to stateful would require new graph nodes

**Status**: Intentionally different. TOOL-FIRST POLICY should make retries unnecessary.

### 4. Streaming Implementation

**Stateless** (`stateless_agent.py:169-215`):
- True token-by-token streaming with `llm_with_tools.astream()`
- Streams first response if no tools needed
- Re-streams final response after tool execution

**Stateful** (`stateful_rag_agent.py:611-635`):
- Simplified streaming - yields full response at once
- Comment: "For Phase 1, just use non-streaming and yield the result"

**Status**: Intentionally different. LangGraph streaming requires `astream_events` implementation. Lower priority UX improvement.

## 🔧 Recent Fixes (2025-10-25)

### Hallucination Fix - TOOL-FIRST POLICY

**Problem**: Stateful agent was hallucinating workout data without calling tools

**Root Cause**: Stateless had stronger "TOOL-FIRST POLICY" prompt that stateful was missing

**Fix**: Moved TOOL-FIRST POLICY to shared `build_base_system_prompt()` so both agents get it

**Files Changed**:
- `backend/src/utils/agent_helpers.py:54-64` - Added TOOL-FIRST POLICY to shared prompt
- `backend/src/agents/stateless_agent.py:94` - Removed duplicate (now in shared prompt)

**Result**: Both agents now have identical strong anti-hallucination prompts

### Memory Classification Fix

**Problem**: Memory type badges not displaying correctly (showing "short-term" instead of "semantic")

**Fix**: Changed from single `memory_type` to `memory_types` array to track multiple memory systems

**Files Changed**:
- `backend/src/agents/stateful_rag_agent.py:519-549` - Detect ALL memory types used
- `frontend/src/streaming.ts:86-118` - Display all memory type badges

## 📊 Test Strategy

Since the agents are intentionally different in implementation but should be functionally similar:

### What to Test

1. **Tool Calling**: Both should call tools for health data queries (not hallucinate)
2. **Numeric Accuracy**: Both should return accurate numbers from tool results
3. **Memory Behavior**:
   - Stateless: Should NOT remember previous conversations
   - Stateful: Should remember and use episodic/procedural memory

### Test Queries

```
"what is my goal weight"
→ Both should call search_health_records_by_metric
→ Both should return "125 lbs"
→ Stateful should show semantic + procedural memory badges

"tell me about my recent workouts"
→ Both should call search_workouts_and_activity
→ Both should return actual workout data
→ Neither should hallucinate fake workouts
```

## 🎯 Recommendation

**Keep agents different**. The stateless agent is working well. The differences are:
1. Documented here
2. Not critical to core functionality
3. Would require significant refactoring of stateful agent to add

The TOOL-FIRST POLICY fix addresses the core hallucination issue. The additional validation layers in stateless are "defense in depth" but not strictly necessary.

## Future Improvements (Optional)

If needed later:
1. Add date validation to stateful (without retry)
2. Add verbosity detection to stateful
3. Implement proper streaming in stateful with `astream_events`
4. Add validation retry nodes to stateful graph

Priority: Low. Current state is acceptable for demonstrating memory value.
