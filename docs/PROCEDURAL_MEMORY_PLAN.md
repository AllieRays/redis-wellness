# Procedural Memory with Orchestration - Implementation Plan

## Current State

**Existing Implementation** (`services/procedural_memory_manager.py`):
- ✅ Already exists with hash-based pattern matching
- ✅ Records tool sequences with success scores
- ✅ Suggests procedures based on query hash
- ❌ No vector search (uses MD5 hash matching)
- ❌ No LangGraph orchestration nodes
- ❌ No planning/execution/reflection workflow

## Decision Point: Two Approaches

### Approach A: Enhance Existing (Simpler)
**Keep hash-based matching, add LangGraph orchestration**

**Pros**:
- Faster (no embedding generation)
- Simpler implementation
- Exact pattern matching (predictable)
- Already partially implemented

**Cons**:
- Won't match similar queries ("weight trend" vs "weight pattern")
- Less flexible than semantic search

**Work Required**:
1. Add LangGraph nodes to stateful agent (retrieve, plan, execute, reflect, store)
2. Wire existing `suggest_procedure()` into retrieve node
3. Add planning logic (currently missing)
4. Add reflection/evaluation (currently missing)
5. Update frontend stats

### Approach B: Vector Search + Orchestration (Original Plan)
**Replace with vector search, full orchestration**

**Pros**:
- Semantic matching (finds similar queries)
- More intelligent pattern retrieval
- Aligns with episodic memory approach
- Better long-term scalability

**Cons**:
- More complex implementation
- Slower (embedding generation required)
- Requires RedisVL index setup

**Work Required**:
1. Rewrite procedural manager with RedisVL (like episodic memory)
2. Add query classification, planning, evaluation helpers
3. Add LangGraph nodes (retrieve, plan, execute, reflect, store)
4. Update frontend stats

---

## Recommended Approach: **Approach A** (Enhance Existing)

**Rationale**:
1. **Lessons from episodic memory**: Start simple, enhance later
2. **Existing code works**: Don't throw away working implementation
3. **Single user app**: Hash matching sufficient for now
4. **Faster iteration**: Can always add vector search later
5. **Focus on orchestration**: The value is in planning/reflection, not search method

---

## Implementation Plan (Approach A)

### Phase 1: Add Planning & Evaluation Logic (30 min)

**File**: `services/procedural_memory_manager.py`

**Add Methods**:

```python
def _classify_query(self, query: str) -> str:
    """Simple keyword-based query classification."""
    # weight_analysis, workout_analysis, comparison, progress, health_metric
    pass

def _plan_tool_sequence(self, query: str, past_procedures: list[dict]) -> dict:
    """Create execution plan from past procedures or defaults."""
    # Returns: {suggested_tools, reasoning, confidence}
    pass

def _evaluate_success(self, tools_used, tool_results, response_ok, exec_time) -> dict:
    """Evaluate if workflow should be stored."""
    # Returns: {success: bool, success_score: float, reasons: list}
    pass
```

### Phase 2: Add LangGraph Orchestration Nodes (45 min)

**File**: `agents/stateful_rag_agent.py`

**New State**:
```python
class OrchestrationState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    episodic_context: str | None
    procedural_suggestion: dict | None  # From suggest_procedure()
    execution_plan: dict | None  # From _plan_tool_sequence()
    workflow_start_time: int  # For timing
```

**New Nodes**:
1. `_retrieve_procedural_node` - Call `suggest_procedure()`
2. `_plan_node` - Create execution plan from suggestion
3. `_execute_node` - Execute tools according to plan
4. `_reflect_node` - Evaluate success
5. `_store_procedural_node` - Call `record_procedure()` if successful

**Graph Flow**:
```
retrieve_episodic → retrieve_procedural → plan → execute → reflect → store_episodic → store_procedural → END
```

### Phase 3: Wire into Service Layer (15 min)

**File**: `services/redis_chat.py`

```python
from .procedural_memory_manager import get_procedural_memory_manager

def __init__(self):
    procedural_memory = get_procedural_memory_manager()

    self.agent = StatefulRAGAgent(
        checkpointer=checkpointer,
        episodic_memory=episodic_memory,
        procedural_memory=procedural_memory,  # NEW
    )
```

### Phase 4: Update Frontend (20 min)

**Files**:
- `frontend/src/types.ts` - Add `procedural_patterns_used: number`
- `frontend/src/stats.ts` - Display "Procedural Patterns: N"

### Phase 5: Testing (30 min)

Test scenarios:
1. First query: "what's my weight trend" → No suggestion, explores, stores pattern
2. Second similar query → Retrieves pattern, suggests tools, faster execution
3. Frontend displays: "Procedural Patterns: 1"

---

## API Contract (CRITICAL)

**TypeScript** (`frontend/src/types.ts`):
```typescript
export interface MemoryStats {
  semantic_hits: number;
  goals_stored: number;
  procedural_patterns_used: number;  // NEW - exact name!
}
```

**Python** (`agents/stateful_rag_agent.py`):
```python
"memory_stats": {
    "semantic_hits": 1,
    "goals_stored": 1,
    "procedural_patterns_used": 1 if suggestion else 0,  // MUST MATCH!
}
```

---

## Estimated Time

- Phase 1 (Planning/Eval): 30 min
- Phase 2 (LangGraph): 45 min
- Phase 3 (Service): 15 min
- Phase 4 (Frontend): 20 min
- Phase 5 (Testing): 30 min

**Total**: ~2.5 hours

---

## Key Differences from Original Plan

| Original Plan | This Plan |
|---------------|-----------|
| Vector search with RedisVL | Hash-based matching (existing) |
| Rewrite procedural manager | Enhance existing manager |
| Semantic query matching | Exact query pattern matching |
| Complex planning logic | Simple: use past or defaults |

**Why This Is Better**:
- ✅ Faster to implement
- ✅ Uses existing working code
- ✅ Simpler to debug
- ✅ Still achieves orchestration goal
- ✅ Can add vector search later if needed

---

## Success Criteria

- ✅ Procedural patterns retrieved for similar queries
- ✅ LangGraph orchestrates: retrieve → plan → execute → reflect → store
- ✅ Frontend displays "Procedural Patterns: N"
- ✅ Patterns stored with success scores
- ✅ Faster execution on repeated queries
- ✅ Stateless agent unaffected (no procedural memory access)

---

Ready to proceed with Approach A?
