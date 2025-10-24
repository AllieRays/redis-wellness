# Final Unused Code Removal Plan

**Date**: 2025-10-24
**Status**: Ready to Execute

---

## Complete Analysis Results

### ✅ **Currently Used (KEEP)**
1. `store_semantic_memory()` - Used by memory_coordinator.py
2. `get_memory_manager` - Used by import_health.py ⚠️
3. `clear_factual_memory()` - Used by import_health.py ⚠️

### ❌ **100% Unused (SAFE TO DELETE)**
1. `retrieve_semantic_memory()` - No usage found
2. `MemoryManager` class alias - No imports found

---

## The Problem

**`import_health.py` uses outdated imports:**

```python
# Lines 255-258 in import_health.py
from services.memory_manager import get_memory_manager

memory_manager = get_memory_manager()
result = asyncio.run(memory_manager.clear_factual_memory(user_id))
```

**This is OLD code** that should use the new memory coordinator.

---

## Solution: Fix First, Then Remove

### Step 1: Update import_health.py

**Replace lines 254-270 with modern approach:**

```python
# OLD (lines 255-270):
from services.memory_manager import get_memory_manager
memory_manager = get_memory_manager()
result = asyncio.run(memory_manager.clear_factual_memory(user_id))

# NEW (updated):
from services.memory_coordinator import get_memory_coordinator
coordinator = get_memory_coordinator()
result = asyncio.run(coordinator.clear_user_memories(
    clear_episodic=True,
    clear_procedural=False,
    clear_semantic=False
))
```

**Benefits:**
- Uses modern memory coordinator
- More explicit about what's being cleared
- Aligns with rest of codebase

---

### Step 2: Remove Truly Unused Code

After fixing import_health.py, these can be safely deleted:

**File**: `backend/src/services/short_term_memory_manager.py`

**Delete:**
```python
# Line ~313-324: retrieve_semantic_memory() - entire function
async def retrieve_semantic_memory(
    self,
    user_id: str,
    query: str,
    top_k: int = 3,
    exclude_session_id: str | None = None,
) -> dict[str, Any]:
    """..."""
    # DELETE ALL THIS

# Line ~449: MemoryManager alias
MemoryManager = ShortTermMemoryManager  # DELETE THIS LINE
```

---

### Step 3: Optional - Make Other Functions Private

Since these are only used internally, consider making them private:

```python
# In short_term_memory_manager.py

# Change from public to private (add underscore):
async def _store_semantic_memory(...)  # Only used by memory_coordinator
async def _clear_factual_memory(...)   # Only used by memory_coordinator

# Update memory_coordinator.py to call:
await self.short_term._store_semantic_memory(...)
await self.short_term._clear_factual_memory(...)
```

**Benefits:**
- Signals "internal API only"
- Prevents external usage
- Makes architecture clearer

---

## Execution Steps

### Safe Approach (Recommended):

```bash
cd /Users/allierays/Sites/redis-wellness

# 1. Fix import_health.py first
# (see edit below)

# 2. Test the import script
uv run python import_health.py apple_health_export/export.xml --user-id test

# 3. If that works, remove unused code
# (see edits below)

# 4. Run tests
cd backend && uv run pytest tests/

# 5. Commit
git add -A
git commit -m "refactor: remove unused code and modernize import_health.py"
```

---

## Files to Modify

### 1. import_health.py (lines 252-270)

**BEFORE:**
```python
        # Clear semantic memory to prevent stale cached answers
        print("\n🧹 Clearing semantic memory cache...")
        try:
            import asyncio
            from services.memory_manager import get_memory_manager

            memory_manager = get_memory_manager()
            result = asyncio.run(memory_manager.clear_factual_memory(user_id))

            if "error" in result:
                print(f"⚠️  Memory clearing failed: {result['error']}")
            else:
                deleted = result.get('deleted_count', 0)
                if deleted > 0:
                    print(f"✅ Cleared {deleted} cached memories (fresh data will be used)")
                else:
                    print(f"✅ No stale memories found")
        except Exception as e:
            print(f"⚠️  Memory clearing failed: {e}")
            print("   (Existing semantic memories may contain outdated information)")
```

**AFTER:**
```python
        # Clear episodic memory to prevent stale cached answers
        print("\n🧹 Clearing episodic memory cache...")
        try:
            import asyncio
            from services.memory_coordinator import get_memory_coordinator

            coordinator = get_memory_coordinator()
            result = asyncio.run(coordinator.clear_user_memories(
                clear_episodic=True,      # Clear cached memories
                clear_procedural=False,   # Keep learned tool patterns
                clear_semantic=False,     # Keep general knowledge
            ))

            episodic_result = result.get('episodic', {})
            if "error" in episodic_result:
                print(f"⚠️  Memory clearing failed: {episodic_result['error']}")
            else:
                deleted = episodic_result.get('deleted_count', 0)
                if deleted > 0:
                    print(f"✅ Cleared {deleted} cached memories (fresh data will be used)")
                else:
                    print(f"✅ No stale memories found")
        except Exception as e:
            print(f"⚠️  Memory clearing failed: {e}")
            print("   (Existing memories may contain outdated information)")
```

### 2. short_term_memory_manager.py

**Delete these lines:**

```python
# DELETE: retrieve_semantic_memory() function (lines ~313-324)
# DELETE: MemoryManager alias (line ~449)
```

---

## Verification Checklist

After changes:

- [ ] import_health.py runs without errors
- [ ] Backend tests pass
- [ ] No grep results for `retrieve_semantic_memory`
- [ ] No grep results for `MemoryManager` (except actual manager classes)
- [ ] `get_memory_manager` only exists as alias (line 448)
- [ ] `clear_factual_memory` only exists as wrapper (not deleted, still used by old alias)

---

## Summary

**What we're doing:**
1. ✅ **Modernize** `import_health.py` to use memory coordinator
2. ✅ **Delete** `retrieve_semantic_memory()` (unused)
3. ✅ **Delete** `MemoryManager` alias (unused)
4. ✅ **Keep** `get_memory_manager` and `clear_factual_memory` (used by import script)

**Result:**
- Clean, modern codebase
- No breaking changes
- import_health.py uses proper memory coordinator
- Zero unused code

---

**Ready to execute?** I can make these changes now.
