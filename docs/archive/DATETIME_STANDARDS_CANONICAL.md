# CANONICAL DATETIME STANDARDS - DO NOT MODIFY

**Last Updated**: October 25, 2025
**Status**: ✅ **ENFORCED ACROSS CODEBASE**
**Review Policy**: Any PR changing datetime handling MUST reference this document

---

## 🚨 CRITICAL RULE

**NEVER change datetime handling without updating this document first.**

Every code review that touches datetime code should verify compliance with these standards. If you find yourself wanting to change how we do datetime somewhere, **STOP** and:

1. Check if this document already has the answer
2. If not, update THIS document first with the new standard
3. Then apply it consistently everywhere
4. Document WHY the change was needed

---

## Core Principles

### 1. ALL datetime objects MUST be timezone-aware
```python
# ✅ CORRECT - Timezone-aware
from datetime import UTC, datetime
now = datetime.now(UTC)

# ❌ WRONG - Naive datetime
from datetime import datetime
now = datetime.now()  # Missing UTC!
```

### 2. ALL imports MUST include UTC
```python
# ✅ CORRECT
from datetime import UTC, datetime

# ❌ WRONG
from datetime import datetime  # Missing UTC!
```

### 3. Backend is timezone-agnostic (always UTC)
- All internal storage: UTC
- All calculations: UTC
- Frontend handles local timezone conversion
- Never hardcode timezones other than UTC

### 4. ISO 8601 is the ONLY storage format
```python
# Storage format: "2025-10-25T14:30:00+00:00"
stored_date = datetime.now(UTC).isoformat()

# Parsing from storage:
from utils.time_utils import parse_health_record_date
parsed = parse_health_record_date(stored_date)
```

---

## Canonical Functions - Use These

### 1. Get Current Time
**Location**: `backend/src/utils/time_utils.py:62-78`

```python
from utils.time_utils import get_utc_timestamp

# For unix timestamps (seconds since epoch)
timestamp = get_utc_timestamp()  # Returns: 1729865400

# For datetime objects
from datetime import UTC, datetime
now = datetime.now(UTC)
```

**WHY**: Centralizes current time logic, ensures UTC, easier to mock in tests.

### 2. Parse Stored Dates
**Location**: `backend/src/utils/time_utils.py:296-352`

```python
from utils.time_utils import parse_health_record_date

# Parse ISO 8601 from Redis/database
dt = parse_health_record_date("2025-10-25T14:30:00+00:00")
# Returns: timezone-aware datetime in UTC

# Also handles 'Z' notation:
dt = parse_health_record_date("2025-10-25T14:30:00Z")
```

**WHY**: Handles all edge cases (Z notation, naive datetimes, validation).

### 3. Format for Storage
**Location**: `backend/src/utils/time_utils.py:258-274`

```python
from utils.time_utils import format_datetime_utc
from datetime import UTC, datetime

dt = datetime(2025, 10, 25, 14, 30, tzinfo=UTC)
iso_string = format_datetime_utc(dt)
# Returns: "2025-10-25T14:30:00+00:00"
```

**WHY**: Ensures consistent ISO 8601 format with timezone.

### 4. Format for LLM Display
**Location**: `backend/src/utils/time_utils.py:277-293`

```python
from utils.time_utils import format_date_utc
from datetime import UTC, datetime

dt = datetime(2025, 10, 25, 14, 30, tzinfo=UTC)
date_string = format_date_utc(dt)
# Returns: "2025-10-25"
```

**WHY**: LLMs struggle with full ISO timestamps. Date-only is clearer.

### 5. Parse Natural Language
**Location**: `backend/src/utils/time_utils.py:81-255`

```python
from utils.time_utils import parse_time_period

start, end, desc = parse_time_period("last week")
# Returns: (datetime(2025, 10, 14, tzinfo=UTC),
#           datetime(2025, 10, 21, tzinfo=UTC),
#           'Last 7 days')
```

**WHY**: Handles "last week", "October", "this month" consistently.

---

## File-by-File Compliance Status

### ✅ COMPLIANT FILES (Import UTC correctly)

1. `backend/src/api/models/errors.py` - ✅ `from datetime import UTC, datetime`
2. `backend/src/apple_health/models.py` - ✅ `from datetime import UTC, date, datetime, timedelta`
3. `backend/src/apple_health/parser.py` - ✅ `from datetime import UTC, date, datetime`
4. `backend/src/apple_health/query_tools/progress_tracking.py` - ✅ UTC imported
5. `backend/src/apple_health/query_tools/search_workouts.py` - ✅ UTC imported
6. `backend/src/services/memory_coordinator.py` - ✅ UTC imported
7. `backend/src/services/procedural_memory_manager.py` - ✅ UTC imported
8. `backend/src/services/redis_apple_health_manager.py` - ✅ UTC imported
9. `backend/src/services/redis_workout_indexer.py` - ✅ UTC imported
10. `backend/src/services/short_term_memory_manager.py` - ✅ UTC imported
11. `backend/src/utils/base.py` - ✅ UTC imported (FIXED Oct 25, 2025)
12. `backend/src/utils/exceptions.py` - ✅ UTC imported
13. `backend/src/utils/time_utils.py` - ✅ UTC imported (canonical source)
14. `backend/src/utils/workout_fetchers.py` - ✅ UTC imported

### ⚠️ INTENTIONALLY EXEMPT (Don't need UTC)

1. `backend/src/utils/metric_aggregators.py`
   - **Reason**: Uses `parse_health_record_date` from time_utils
   - Converts to naive datetime for comparison (documented in code)
   - **Status**: SAFE - delegates to canonical function

2. `backend/src/utils/stats_utils.py`
   - **Reason**: Pure math functions, only imports `datetime` for type hints
   - Never creates datetime objects
   - **Status**: SAFE - no datetime manipulation

---

## Common Patterns

### Pattern 1: Creating timestamps
```python
# ✅ CORRECT
from datetime import UTC, datetime
timestamp = int(datetime.now(UTC).timestamp())

# ❌ WRONG
from datetime import datetime
timestamp = int(datetime.now().timestamp())  # Missing UTC!
```

### Pattern 2: Storing to Redis/JSON
```python
# ✅ CORRECT
from datetime import UTC, datetime
now = datetime.now(UTC)
stored = now.isoformat()  # "2025-10-25T14:30:00+00:00"

# ❌ WRONG
from datetime import datetime
now = datetime.now()
stored = now.isoformat()  # "2025-10-25T14:30:00" (no timezone!)
```

### Pattern 3: Loading from Redis/JSON
```python
# ✅ CORRECT
from utils.time_utils import parse_health_record_date
dt = parse_health_record_date(stored_value)

# ❌ WRONG
from datetime import datetime
dt = datetime.fromisoformat(stored_value)  # Missing validation
```

### Pattern 4: Displaying to LLM
```python
# ✅ CORRECT - Date only for clarity
from utils.time_utils import format_date_utc
display = format_date_utc(dt)  # "2025-10-25"

# ❌ WRONG - Full timestamp confuses LLM
display = dt.isoformat()  # "2025-10-25T14:30:00+00:00" (too technical)
```

---

## Testing Standards

### Unit Tests Must:
1. Import UTC when testing datetime code
2. Use fixed datetimes, not `datetime.now()`
3. Mock `get_utc_timestamp()` for consistent test times

```python
# ✅ CORRECT - Mockable and deterministic
from unittest.mock import patch
from utils.time_utils import get_utc_timestamp

with patch('utils.time_utils.get_utc_timestamp', return_value=1729865400):
    result = function_under_test()

# ❌ WRONG - Non-deterministic
from datetime import datetime, UTC
result = function_under_test()  # Uses datetime.now(UTC) internally
```

---

## Review Checklist

Before approving ANY PR that touches datetime code:

- [ ] All `from datetime import` include `UTC`
- [ ] No bare `datetime.now()` (must be `datetime.now(UTC)`)
- [ ] Stored dates use `.isoformat()` format
- [ ] Parsed dates use `parse_health_record_date()`
- [ ] LLM responses use date-only format (not full ISO)
- [ ] Tests mock `get_utc_timestamp()` not `datetime.now()`
- [ ] Timezone awareness preserved through all transformations

---

## Why This Matters

### Problem: Inconsistent Datetime Handling
**Before this standard**, every code review changed datetime somewhere:
- Review 1: "Use timezone-aware datetimes"
- Review 2: "Import UTC from datetime"
- Review 3: "Fix datetime.now() to datetime.now(UTC)"
- **This is technical debt accumulation!**

### Solution: Canonical Standards
**With this document**:
- ✅ One source of truth for datetime handling
- ✅ Clear compliance checklist
- ✅ Prevents regressions
- ✅ Easier code reviews

### Real Impact
1. **Prevents bugs**: Timezone-naive datetimes cause silent failures
2. **Reduces review churn**: No more "fix datetime again" comments
3. **Easier debugging**: Consistent format everywhere
4. **Future-proof**: Works correctly in any timezone

---

## Migration Guide (If You Find Non-Compliant Code)

### Step 1: Update Import
```python
# BEFORE
from datetime import datetime

# AFTER
from datetime import UTC, datetime
```

### Step 2: Fix datetime.now() Calls
```python
# BEFORE
timestamp = datetime.now()

# AFTER
timestamp = datetime.now(UTC)
```

### Step 3: Run Tests
```bash
cd backend
uv run pytest tests/
```

### Step 4: Update This Document
If you found a new pattern or edge case, document it here!

---

## Enforcement

### Pre-commit Hook (Recommended)
Add to `.pre-commit-config.yaml`:
```yaml
- id: check-datetime-imports
  name: Check datetime imports include UTC
  entry: bash -c 'grep -r "from datetime import datetime$" backend/src --include="*.py" && exit 1 || exit 0'
  language: system
  pass_filenames: false
```

### CI Check (Required)
Add to CI pipeline:
```bash
# Fail if any file imports datetime without UTC (excluding exempt files)
! grep -r "from datetime import datetime$" backend/src --include="*.py" \
  --exclude=stats_utils.py --exclude=metric_aggregators.py
```

---

## Version History

| Date | Change | Reason |
|------|--------|--------|
| 2025-10-25 | Initial standard created | Prevent datetime review churn |
| 2025-10-25 | Fixed `base.py` datetime.now() | Missing UTC import |
| 2025-10-25 | Documented exempt files | stats_utils.py, metric_aggregators.py |

---

## Questions?

**Q: Can I use a different datetime library (arrow, pendulum)?**
A: No. Stick to stdlib `datetime` with `UTC` for consistency.

**Q: What about frontend datetime handling?**
A: Frontend handles local timezone conversion. Backend stays UTC-only.

**Q: Can I use timezone-naive datetimes for comparisons?**
A: Only if you're in `metric_aggregators.py` AND you document why. Otherwise, NO.

**Q: Should I update this document?**
A: YES! If you find a new pattern or fix a bug, document it here.

---

**REMEMBER**: This is the ONE TRUE SOURCE for datetime standards. If you're changing datetime code and this document doesn't have the answer, UPDATE THE DOCUMENT FIRST, then apply the change consistently.

**Last Reviewed**: October 25, 2025
**Next Review**: Post-demo (October 28, 2025)
