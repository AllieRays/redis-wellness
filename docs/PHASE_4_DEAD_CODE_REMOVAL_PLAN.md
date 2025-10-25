# Phase 4: Dead Code Removal Plan

**Date:** 2025-10-25
**Status:** PLANNING

---

## Overview

Remove dead code identified in Phase 3 review. Each removal will be tested to ensure no regressions.

---

## Dead Code Identified

### 1. memory_coordinator.py (Entire File)
**Location:** `src/services/memory_coordinator.py`
**Size:** ~550 lines
**Reason:** Not used in production - agents call memory managers directly
**Risk:** LOW - No imports found in production code

**Evidence:**
```bash
# Check for imports
grep -r "memory_coordinator\|MemoryCoordinator" src/
# Result: Only found in the file itself and short_term_memory_manager (which also isn't used)
```

---

### 2. short_term_memory_manager.py (Entire File)
**Location:** `src/services/short_term_memory_manager.py`
**Reason:** Not used - LangGraph checkpointer handles short-term memory
**Risk:** LOW - No production usage

---

### 3. RedisHealthManager - 3 Unused Methods
**Location:** `src/services/redis_apple_health_manager.py`
**Lines:** 116-206

**Methods to remove:**
- `query_health_metrics()` (lines 116-159) - Uses broken `self.redis`
- `get_conversation_context()` (lines 161-181) - Uses broken `self.redis`
- `cleanup_expired_data()` (lines 183-206) - Uses broken `self.redis`

**Risk:** LOW - Verified no tools call these methods

---

## Removal Strategy: One at a Time with Testing

### Step 1: Remove 3 methods from redis_apple_health_manager.py
**Why first:** Smallest change, easiest to verify
**Test after:** Run baseline tests (5/5 should still pass)
**Rollback:** Git revert if tests fail

### Step 2: Remove short_term_memory_manager.py
**Why second:** Small file, clear non-usage
**Test after:** Run baseline tests
**Rollback:** Git revert if tests fail

### Step 3: Remove memory_coordinator.py
**Why last:** Largest file, want to be most cautious
**Test after:** Run baseline tests
**Rollback:** Git revert if tests fail

---

## Testing Protocol (After Each Removal)

1. **Verify file removed:** `ls -la src/services/`
2. **Check for broken imports:** `python -c "from src.services.redis_chat import get_redis_chat_service"`
3. **Run baseline tests:** `./test_baseline.sh`
4. **Verify results:** Must get 5/5 tests passing
5. **Check response quality:** Review test output for accuracy
6. **Git commit:** Commit successful removal

**If ANY test fails:**
1. Stop immediately
2. Git revert the removal
3. Re-run tests to verify revert worked
4. Investigate why it failed

---

## Detailed Removal Instructions

### Removal 1: redis_apple_health_manager.py methods

**File:** `src/services/redis_apple_health_manager.py`

**Lines to delete:** 116-206 (3 complete methods)

**What to keep:**
- Class definition and `__init__` (lines 28-48)
- `store_health_data()` (lines 49-88) ✅ USED
- `_create_indices()` (lines 90-114) ✅ USED

**Git commit message:**
```
Remove dead code from RedisHealthManager

- Removed query_health_metrics() (broken self.redis)
- Removed get_conversation_context() (broken self.redis)
- Removed cleanup_expired_data() (broken self.redis)

These methods were never called by any tools.
Production methods (store_health_data, _create_indices) unchanged.

Tested: Baseline tests 5/5 passing
```

---

### Removal 2: short_term_memory_manager.py

**Action:** Delete entire file
```bash
rm src/services/short_term_memory_manager.py
```

**Verify no imports:**
```bash
grep -r "short_term_memory_manager\|ShortTermMemoryManager" src/
# Should return: No matches (except possibly in memory_coordinator which will be deleted)
```

**Git commit message:**
```
Remove short_term_memory_manager.py (dead code)

LangGraph checkpointer handles short-term memory.
This manager was never used in production.

Tested: Baseline tests 5/5 passing
```

---

### Removal 3: memory_coordinator.py

**Action:** Delete entire file
```bash
rm src/services/memory_coordinator.py
```

**Verify no imports:**
```bash
grep -r "memory_coordinator\|MemoryCoordinator" src/
# Should return: No matches
```

**Git commit message:**
```
Remove memory_coordinator.py (dead code)

Agents call episodic/procedural managers directly.
This coordinator was bypassed in production flow.

Tested: Baseline tests 5/5 passing
```

---

## Safety Checks

### Before Starting:
- ✅ Baseline tests passing (5/5) - CONFIRMED in Phase 2
- ✅ Git repository clean
- ✅ Backend running
- ✅ No uncommitted changes

### After Each Removal:
- ✅ Python imports work (no ImportError)
- ✅ Backend starts without errors
- ✅ Baseline tests pass (5/5)
- ✅ Response quality maintained

### Emergency Rollback:
```bash
# If any removal causes issues:
git log --oneline -5  # Find the removal commit
git revert <commit-hash>
./test_baseline.sh    # Verify rollback worked
```

---

## Expected Test Results

All 5 baseline tests should continue passing:

| Test | Expected Result |
|------|-----------------|
| 1 - Simple Query | ✅ PASS (6 workouts) |
| 2 - Follow-up (Memory) | ✅ PASS (workout types) |
| 3 - Numeric Accuracy | ✅ PASS (89.2 bpm) |
| 4 - Tool Calling | ✅ PASS (comparison) |
| 5 - Complex Query | ✅ PASS (graceful handling) |

If ANY test fails, STOP and rollback.

---

## Files That Will Remain

After all removals, these services will remain (all actively used):

1. ✅ `redis_connection.py` - Connection management
2. ✅ `redis_chat.py` - Chat orchestration
3. ✅ `episodic_memory_manager.py` - Goals/preferences
4. ✅ `procedural_memory_manager.py` - Tool patterns
5. ✅ `redis_apple_health_manager.py` - Health data (2 working methods)
6. ✅ `redis_search_manager.py` - Vector search
7. ✅ `redis_workouts_search_manager.py` - Workout queries
8. ✅ (Other services remain unchanged)

---

## Success Criteria

**All 3 removals successful if:**
- ✅ Dead code removed
- ✅ No broken imports
- ✅ Backend starts cleanly
- ✅ Baseline tests: 5/5 passing
- ✅ Response quality maintained
- ✅ No errors in logs

**If any criteria fails:** Rollback that specific removal.

---

## Next Step

Run through removals sequentially:
1. Remove 3 methods from redis_apple_health_manager.py
2. Test (5/5)
3. Remove short_term_memory_manager.py
4. Test (5/5)
5. Remove memory_coordinator.py
6. Test (5/5)
7. Final verification

Ready to proceed?
