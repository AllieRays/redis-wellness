# CLAUDE.md - Debugging Guidelines for AI Assistants

This document provides systematic debugging guidance for AI assistants (Claude, GPT, etc.) working on the Redis Wellness codebase.

## Overview

This codebase is a **full-stack TypeScript/Python application** with:
- **Backend**: FastAPI (Python) with LangGraph agents
- **Frontend**: TypeScript + Vite
- **Infrastructure**: Docker Compose (Redis, backend, frontend)
- **Deployment**: Docker COPY (not volume mounts for backend)

**Critical**: Backend source code is COPIED during Docker build, not mounted as volumes. Any code change requires a rebuild.

---

## Golden Rule: Check API Contracts FIRST

When debugging data flow issues (e.g., "backend calculates correctly but frontend shows 0"):

### Step 1: Verify Field Names Match

**DO THIS FIRST** before any other debugging:

```bash
# Check TypeScript interface
grep -r "interface.*Stats" frontend/src/types.ts

# Check backend response
grep -r "memory_stats" backend/src/agents/
grep -r "memory_stats" backend/src/services/

# Look for mismatches like:
# Backend sends: semantic_retrieval
# Frontend expects: semantic_hits
```

**Why**: Field name mismatches are silent failures - no errors, data just disappears.

**Lesson from October 2024**: Spent multiple hours debugging episodic memory when the entire issue was:
- Backend sent `{"memory_stats": {"semantic_retrieval": 1}}`
- Frontend expected `{"memory_stats": {"semantic_hits": 1}}`

### Step 2: Check Streaming Response Completeness

For streaming endpoints, verify ALL fields are included:

```python
# ❌ BAD - Missing field in done event
yield {"type": "done", "data": {"response": result["response"]}}

# ✅ GOOD - All fields included
yield {
    "type": "done",
    "data": {
        "response": result["response"],
        "tools_used": result["tools_used"],
        "memory_stats": result.get("memory_stats", {}),  # Don't forget!
    }
}
```

---

## Debugging Workflow: Test in Order

Debug systematically from backend to frontend:

### Level 1: Verify Data Exists

```bash
# Check Redis directly
redis-cli
> KEYS episodic:*
> HGETALL episodic:user123:1234567890
```

### Level 2: Verify Backend Calculates Correctly

```bash
# Check logs for calculation
docker compose logs backend | grep "Memory stats"

# Should see: "💾 Memory stats: semantic_hits=1, goals_stored=1"
```

### Level 3: Verify Backend Returns Correctly

```bash
# Test API directly
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "session_id": "debug"}' | jq '.memory_stats'

# Should return: {"semantic_hits": 1, "goals_stored": 1}
```

### Level 4: Verify Frontend Receives Correctly

```javascript
// Add console.log in frontend code
console.log('📥 Received memory_stats:', data.memory_stats);
console.log('📊 Keys:', Object.keys(data.memory_stats || {}));

// Check browser DevTools → Network → Response tab
```

**If Level 2 passes but Level 3 fails**: API serialization issue
**If Level 3 passes but Level 4 fails**: Field name mismatch or frontend parsing issue

---

## Docker Development Workflow

### Critical Understanding: COPY vs Volume Mounts

The backend Dockerfile uses `COPY src/ ./src/`, which means:

- ✅ Source code is **copied** during build
- ❌ NOT mounted as a volume
- ⚠️ Code changes require rebuild

### When to Rebuild Docker

**MUST rebuild after:**
- Any change to `backend/src/` files
- Changes to `pyproject.toml` or `uv.lock`
- Changes to environment variables in `docker-compose.yml`

**NO rebuild needed:**
- Frontend changes (frontend IS volume mounted)

### Rebuild Commands

```bash
# Standard rebuild
docker compose build backend
docker compose up -d backend

# Quick one-liner with log check
docker compose build backend && docker compose up -d backend && docker compose logs backend --tail 50

# Emergency fix without rebuild (temporary)
docker cp /path/to/file.py redis-wellness-backend:/app/src/path/to/file.py
docker compose restart backend
```

### How to Know if Rebuild is Needed

**User says**: "I tried again and it's still showing 0"
**Your response**: "Let me rebuild the Docker container to ensure the changes take effect"

**User asks**: "Do we need to rebuild Docker?"
**Your response**: "Yes, since we changed backend code, we need to rebuild"

---

## Logging Best Practices

### Add Logging EARLY, Not After Hours of Debugging

**DO THIS** at the start of implementation:

```python
# Backend - Add comprehensive logging
logger.info(f"💾 Memory stats calculated: semantic_hits={hits}, goals_stored={goals}")
logger.info(f"📊 Final state: {len(final_state['messages'])} messages")
logger.info(f"✅ Episodic context retrieved: {state.get('episodic_context') is not None}")

# Use emojis for visual scanning in logs
logger.info("🧠 Retrieving episodic memory...")
logger.info("💾 Storing interaction in episodic memory...")
logger.info("🔧 Executing 3 tools")
```

```typescript
// Frontend - Log what you receive
console.log('📥 Received memory_stats:', data.memory_stats);
console.log('📊 Stats object:', this.stats);
```

### Log Visibility Issues

**Problem**: Logs not appearing even though code is executing

**Check**:
1. Multiple processes running? `lsof -i :8000`
2. Docker running old code? Rebuild needed
3. Wrong container? `docker compose ps`
4. Background processes? Use `/bashes` to see running shells

**Fix**:
```bash
# Kill all instances on port 8000
lsof -ti:8000 | xargs kill -9

# View Docker logs
docker compose logs backend -f

# View last 50 lines
docker compose logs backend --tail 50
```

---

## Environment Variables

### Common Mistake: Variable Name Mismatches

**Problem**: `docker-compose.yml` uses different names than `config.py` expects

**Example from October 2024**:
```yaml
# docker-compose.yml had:
environment:
  - OLLAMA_HOST=http://host.docker.internal:11434  # ❌ Wrong name

# But backend/src/config.py expects:
ollama_base_url: str = Field(default="...")  # Expects OLLAMA_BASE_URL
```

**Fix**: Ensure variable names match exactly:
```yaml
environment:
  - OLLAMA_BASE_URL=http://host.docker.internal:11434  # ✅ Correct
```

### Verification Command

```bash
# Check what environment variables are set in container
docker compose exec backend env | grep OLLAMA

# Should show: OLLAMA_BASE_URL=http://host.docker.internal:11434
```

---

## TypeScript Interface Verification

### When Adding New API Fields

**Always verify both sides of the contract:**

```typescript
// 1. Define interface (frontend/src/types.ts)
export interface MemoryStats {
  semantic_hits: number;      // ← Note the exact field name
  goals_stored: number;
}

// 2. Check usage (frontend/src/stats.ts)
this.stats.semanticMemories = data.memory_stats?.semantic_hits || 0;
//                                                 ^^^^^^^^^^^^^ Must match interface

// 3. Grep for consistency
// grep -r "semantic_hits" frontend/src/
// grep -r "semantic_hits" backend/src/
```

### Backend Response Structure

```python
# Ensure backend sends exactly what TypeScript expects
return {
    "response": response_text,
    "tools_used": tools_used,
    "memory_stats": {
        "semantic_hits": 1,    # ← Must match TypeScript interface
        "goals_stored": 1,     # ← Must match TypeScript interface
    }
}
```

---

## Testing Strategy for New Features

### Phase 1: Isolation Tests

Test components in isolation BEFORE integration:

```bash
# Test fact extraction alone
cd backend
uv run python test_goal_extraction.py

# Test episodic memory alone
uv run python test_episodic_memory.py
```

### Phase 2: Integration Tests

Test with the full agent:

```bash
# Test via API
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "my goal weight is 125 lbs", "session_id": "test"}'
```

### Phase 3: End-to-End Tests

Test through the frontend:

```bash
# 1. Open http://localhost:3000
# 2. Open DevTools → Network tab
# 3. Send message
# 4. Check Response payload
# 5. Check Console logs
```

**Don't skip phases** - isolation tests catch issues early.

---

## Common Debugging Patterns

### Pattern 1: "Backend calculates correctly but frontend shows 0"

**Likely cause**: Field name mismatch

**Fix**:
1. Check backend logs for calculated value
2. Check API response with curl
3. Check TypeScript interface
4. Grep both codebases for field name
5. Update backend to match frontend (or vice versa)

### Pattern 2: "Changes not taking effect"

**Likely cause**: Docker rebuild needed

**Fix**:
```bash
docker compose build backend
docker compose up -d backend
docker compose logs backend --tail 50
```

### Pattern 3: "No logs appearing"

**Likely cause**: Multiple processes or wrong container

**Fix**:
```bash
# Check running processes
lsof -i :8000
ps aux | grep uvicorn

# Kill all
lsof -ti:8000 | xargs kill -9

# Check Docker
docker compose ps
docker compose logs backend -f
```

### Pattern 4: "Ollama connection refused"

**Likely cause**: Environment variable mismatch

**Fix**:
```bash
# Check variable name in docker-compose.yml
grep OLLAMA docker-compose.yml

# Should be: OLLAMA_BASE_URL (not OLLAMA_HOST)
```

---

## LangGraph-Specific Debugging

### State Flow Verification

```python
# Add logging at each node
async def _retrieve_memory_node(self, state: MemoryState) -> dict:
    logger.info(f"🧠 Retrieve node: {len(state['messages'])} messages")
    # ... node logic ...
    logger.info(f"✅ Retrieved context: {context is not None}")
    return {"episodic_context": context}

async def _llm_node(self, state: MemoryState) -> dict:
    logger.info(f"🤖 LLM node: {len(state['messages'])} messages")
    logger.info(f"   Episodic context: {state.get('episodic_context') is not None}")
    # ... node logic ...
    return {"messages": [response]}

async def _store_memory_node(self, state: MemoryState) -> dict:
    logger.info(f"💾 Store node: {len(state['messages'])} messages")
    # ... node logic ...
    logger.info(f"✅ Stored {len(goals)} goals")
    return {}
```

### Graph Flow Debugging

```python
# Verify conditional edges
def _should_continue(self, state: MemoryState) -> str:
    last_msg = state["messages"][-1]
    has_tools = hasattr(last_msg, "tool_calls") and last_msg.tool_calls
    result = "tools" if has_tools else "end"

    # Add explicit logging
    logger.info(f"🔀 Decision: {result} (has_tools={has_tools})")
    return result
```

---

## Preventive Measures

### Before Starting Implementation

1. **Check existing TypeScript interfaces** for related features
2. **Add comprehensive logging** to all new functions
3. **Write isolation tests** before integration
4. **Document field names** in both backend and frontend

### During Implementation

1. **Test at each layer** (Redis → Backend → API → Frontend)
2. **Rebuild Docker after each backend change**
3. **Check logs immediately** after each test
4. **Grep for field names** when adding new API fields

### After Implementation

1. **Verify TypeScript types match backend responses**
2. **Test browser refresh** to ensure session persistence
3. **Check Docker logs** for warnings or errors
4. **Document any gotchas** in WARP.md or this file

---

## Key Lessons from October 2024 Episodic Memory Implementation

### What Went Wrong

**Problem**: Episodic memory was working perfectly, but frontend showed 0 for semantic hits.

**Root Cause**: Field name mismatch
- Backend: `semantic_retrieval`
- Frontend: `semantic_hits`

**Time Wasted**: Multiple hours debugging when the issue was a simple field name.

### What Should Have Been Done

1. ✅ **Check TypeScript interfaces FIRST** before any debugging
2. ✅ **Add explicit logging** showing exact field names being calculated
3. ✅ **Test API response** with curl to see actual field names
4. ✅ **Grep both codebases** for the field name to find mismatches

### The Fix

```python
# Changed this:
"memory_stats": {"semantic_retrieval": 1}

# To this:
"memory_stats": {"semantic_hits": 1}
```

**Total fix time**: 2 minutes (once the issue was identified)
**Debugging time before fix**: Multiple hours

---

## Quick Reference Commands

```bash
# Rebuild backend after code changes
docker compose build backend && docker compose up -d backend

# View logs
docker compose logs backend -f
docker compose logs backend --tail 50

# Test API endpoint
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "session_id": "debug"}' | jq

# Check Redis data
redis-cli
> KEYS *
> HGETALL episodic:user123:1234567890

# Kill processes on port
lsof -ti:8000 | xargs kill -9

# Grep for field names
grep -r "semantic_hits" frontend/src/
grep -r "semantic_hits" backend/src/

# Check environment variables in Docker
docker compose exec backend env | grep OLLAMA
```

---

## Summary: The Debugging Philosophy

1. **API contracts matter most** - Check field names before diving deep
2. **Docker COPY requires rebuilds** - Always rebuild after backend changes
3. **Log early, log often** - Add logging before multi-hour debugging sessions
4. **Test in layers** - Redis → Backend → API → Frontend
5. **TypeScript interfaces are source of truth** - Backend must match them
6. **Field name mismatches are silent** - They don't error, data just disappears

**Remember**: Most "complex" bugs are actually simple contract mismatches. Check the obvious things first.

---

## When to Update This Document

Add to this document when:
- You encounter a debugging pattern not covered here
- You waste more than 30 minutes on an issue with a simple fix
- You discover a new gotcha specific to this codebase
- A user asks "why was X so hard?"

**Goal**: Prevent future AI assistants (and developers) from wasting hours on the same issues.
