# Systematic Unused Code Removal Guide

**Repository**: redis-wellness
**Date**: 2025-10-24
**Purpose**: Find and safely remove unused code

---

## Phase 1: Discovery - Find What's Actually Used

### Step 1: Find All Function/Class Definitions

```bash
# Find all function definitions in Python
cd /Users/allierays/Sites/redis-wellness
grep -r "^def " backend/src/ --include="*.py" | wc -l
grep -r "^async def " backend/src/ --include="*.py" | wc -l
grep -r "^class " backend/src/ --include="*.py" | wc -l
```

### Step 2: Find All Imports

```bash
# Find what's being imported
grep -r "^from " backend/src/ --include="*.py" > /tmp/imports.txt
grep -r "^import " backend/src/ --include="*.py" >> /tmp/imports.txt
cat /tmp/imports.txt | sort | uniq
```

### Step 3: Use Python Tools for Dead Code Detection

**Install vulture (dead code detector):**
```bash
pip install vulture
# or with uv
uv pip install vulture
```

**Run vulture:**
```bash
cd /Users/allierays/Sites/redis-wellness/backend
vulture src/ --min-confidence 60
```

This will show:
- Unused functions
- Unused classes
- Unused variables
- Unused imports

---

## Phase 2: Verification - Confirm It's Safe to Remove

### Method 1: Grep for Usage

For each suspicious function, search for calls to it:

```bash
# Example: Check if store_semantic_memory is used
cd /Users/allierays/Sites/redis-wellness
grep -r "store_semantic_memory" backend/ --include="*.py"
```

**Interpret Results:**
- Only 1 result (the definition) = **Unused**
- 2+ results = **Used** (keep it)

### Method 2: Check Public APIs

**Check if function is exported in `__init__.py`:**
```bash
grep -r "__all__" backend/src/ --include="*.py"
```

**If it's in `__all__`**, it's part of the public API - be careful!

### Method 3: Check External Callers

**Frontend might call backend endpoints:**
```bash
# Check if frontend uses an endpoint
grep -r "/api/chat/redis" frontend/src/
```

**Scripts might import functions:**
```bash
# Check root-level scripts
grep -r "from backend" *.py
grep -r "import backend" *.py
```

---

## Phase 3: Safe Removal Strategy

### For Functions/Methods

**Step 1: Comment out, don't delete**
```python
# def old_function():
#     """This function is no longer used."""
#     pass
```

**Step 2: Run tests**
```bash
cd backend
uv run pytest tests/
```

**Step 3: If tests pass, delete**
```python
# Delete the commented code
```

### For Entire Files

**Step 1: Move to archive folder**
```bash
mkdir -p /tmp/redis-wellness-archive
mv backend/src/services/old_service.py /tmp/redis-wellness-archive/
```

**Step 2: Run tests**
```bash
cd backend
uv run pytest tests/
```

**Step 3: If tests pass for 1 week, delete permanently**

---

## Phase 4: Target-Specific Analysis

### Candidate: Wrapper Functions in short_term_memory_manager.py

**Functions to Investigate:**
```bash
cd /Users/allierays/Sites/redis-wellness
grep -n "async def store_semantic_memory\|async def retrieve_semantic_memory\|async def clear_factual_memory" backend/src/services/short_term_memory_manager.py
```

**Check who calls them:**
```bash
# Find all callers
grep -r "\.store_semantic_memory\(" backend/ --include="*.py"
grep -r "\.retrieve_semantic_memory\(" backend/ --include="*.py"
grep -r "\.clear_factual_memory\(" backend/ --include="*.py"
```

**Expected Results:**
- If only `memory_coordinator.py` calls them → **Keep as internal API**
- If nothing calls them → **Remove**
- If tests call them → **Remove tests too**

### Candidate: get_memory_manager vs get_short_term_memory_manager

**Check which is used:**
```bash
grep -r "get_memory_manager()" backend/ --include="*.py"
grep -r "get_short_term_memory_manager()" backend/ --include="*.py"
```

**Decision:**
- If both are used → Keep both
- If only one is used → Remove the other

---

## Phase 5: Automated Dead Code Removal

### Using vulture with whitelist

**Step 1: Run vulture and save output**
```bash
cd /Users/allierays/Sites/redis-wellness/backend
vulture src/ --min-confidence 80 > vulture_report.txt
```

**Step 2: Review report manually**
```bash
cat vulture_report.txt
```

**Step 3: Create whitelist for false positives**
```python
# vulture_whitelist.py
# Functions that look unused but are actually used dynamically

# FastAPI routes (called by framework)
_.basic_health_check  # main.py - FastAPI route
_.stateless_chat  # chat_routes.py - FastAPI route

# LangChain tools (called by LLM)
_.search_health_records_by_metric  # query_tools - LangChain tool
```

**Step 4: Run with whitelist**
```bash
vulture src/ vulture_whitelist.py --min-confidence 80
```

---

## Phase 6: Specific Candidates to Check

### Run These Commands Now:

```bash
cd /Users/allierays/Sites/redis-wellness

# 1. Check wrapper functions
echo "=== Checking store_semantic_memory usage ==="
grep -r "store_semantic_memory" backend/src/ --include="*.py" | grep -v "def store_semantic_memory"

echo "=== Checking retrieve_semantic_memory usage ==="
grep -r "retrieve_semantic_memory" backend/src/ --include="*.py" | grep -v "def retrieve_semantic_memory"

echo "=== Checking clear_factual_memory usage ==="
grep -r "clear_factual_memory" backend/src/ --include="*.py" | grep -v "def clear_factual_memory"

# 2. Check alias functions
echo "=== Checking get_memory_manager usage ==="
grep -r "get_memory_manager" backend/src/ --include="*.py" | grep -v "def get_memory_manager"

# 3. Check for unused imports
echo "=== Checking unused imports ==="
cd backend && uv run python -m pylint src/ --disable=all --enable=unused-import 2>/dev/null || echo "pylint not installed"
```

---

## Decision Matrix

| Scenario | Action |
|----------|--------|
| Function defined but never called | **DELETE** |
| Function called only in tests | **DELETE** (both function and tests) |
| Function called by one place | **INLINE** (replace call with function body) |
| Function called from multiple places | **KEEP** |
| Function in `__all__` export | **KEEP** (public API) |
| Function is FastAPI route | **KEEP** (called by framework) |
| Function is LangChain tool | **KEEP** (called by LLM) |
| Function has TODO comment | **Either implement or DELETE** |
| Function returns fake data | **DELETE or IMPLEMENT** |

---

## Safety Checklist

Before deleting ANY code:

- [ ] Searched codebase for all calls to function
- [ ] Checked if it's exported in `__all__`
- [ ] Checked if it's a FastAPI route (endpoints)
- [ ] Checked if it's a LangChain tool
- [ ] Checked if frontend calls it
- [ ] Checked if root scripts import it
- [ ] Ran full test suite
- [ ] Checked git history (was it recently added?)
- [ ] Asked team if anyone is working on it

---

## Tools Summary

```bash
# Install analysis tools
pip install vulture pylint

# Run dead code detection
vulture backend/src/ --min-confidence 70

# Run unused import detection
pylint backend/src/ --disable=all --enable=unused-import

# Search for function usage
grep -r "function_name" backend/ --include="*.py"

# Count definitions vs usages
grep -r "def my_function" backend/ | wc -l  # Should be 1
grep -r "my_function(" backend/ | wc -l     # Should be > 1 if used
```

---

## Example Workflow

Let's check `store_semantic_memory`:

```bash
# 1. Find definition
grep -n "def store_semantic_memory" backend/src/services/short_term_memory_manager.py

# 2. Find all usages
grep -r "store_semantic_memory" backend/src/ --include="*.py"

# 3. Count them
echo "Definition count:"
grep -r "def store_semantic_memory" backend/src/ | wc -l

echo "Usage count (excluding definition):"
grep -r "\.store_semantic_memory\(" backend/src/ | wc -l

# 4. Decision
# If usage count = 0: DELETE
# If usage count = 1 and it's memory_coordinator: KEEP (internal API)
# If usage count > 1: KEEP
```

---

## Want Me To Run This Now?

I can run the systematic analysis right now to find:
1. All unused functions in your codebase
2. Wrapper functions that are never called
3. Import statements that are unused
4. Dead code candidates

**Should I run the analysis?** Let me know and I'll give you a concrete list of what can be safely removed.
