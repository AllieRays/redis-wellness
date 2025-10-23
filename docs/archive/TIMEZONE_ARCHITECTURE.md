# Timezone Architecture - Pure UTC Backend

**Date:** 2025-10-21
**Status:** ✅ IMPLEMENTED
**Principle:** Backend timezone-agnostic (UTC only), Frontend handles user timezones

---

## Architecture Overview

```
┌─────────────┐         ┌──────────────┐         ┌────────────────┐
│   Storage   │         │   Backend    │         │    Frontend    │
│   (Redis)   │────────▶│   (FastAPI)  │────────▶│  (TypeScript)  │
│             │         │              │         │                │
│  UTC ONLY   │         │   UTC ONLY   │         │  User's Local  │
│             │         │              │         │    Timezone    │
└─────────────┘         └──────────────┘         └────────────────┘
```

##  Core Principles

### 1. **Backend: Pure UTC**
- All date/time operations in UTC
- No timezone assumptions
- Works globally without modification
- Simplifies datetime math and comparisons

### 2. **Frontend: User's Timezone**
- Detects user's actual timezone
- Converts UTC to local time for display
- Handles DST transitions automatically
- Provides localized date formatting

### 3. **Storage: UTC ISO 8601**
- Consistent format: `YYYY-MM-DD HH:MM:SS`
- All stored dates assume UTC
- Single source of truth

---

## Implementation Details

### Backend Changes

#### Before (❌ Timezone-Coupled)
```python
# Assumed Pacific timezone
USER_TIMEZONE = ZoneInfo("America/Los_Angeles")
now_pst = datetime.now(USER_TIMEZONE)
now_utc = now_pst.astimezone(UTC)
```

#### After (✅ Timezone-Agnostic)
```python
# Pure UTC, no timezone assumptions
now_utc = datetime.now(UTC)
```

### Key Functions Refactored

#### 1. `parse_time_period()`
**Purpose:** Parse natural language time descriptions
**Change:** All date calculations now in pure UTC

```python
# Example: "last week"
# Before: Calculated from PST, converted to UTC
# After: Calculated directly in UTC

now_utc = datetime.now(UTC)
start_date = now_utc - timedelta(days=7)
return start_date, now_utc, "Last 7 days"
```

#### 2. `parse_health_record_date()`
**Purpose:** Parse stored health record dates
**Change:** Always returns UTC-aware datetime

```python
dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt
```

#### 3. `format_datetime_pst()` & `format_date_pst()`
**Status:** DEPRECATED
**Change:** Now returns UTC ISO format, frontend handles display

```python
# Before: Converted to PST for display
pst_time = utc_datetime.astimezone(USER_TIMEZONE)
return pst_time.strftime("%b %d, %Y at %I:%M %p %Z")

# After: Returns UTC ISO, frontend converts
return utc_datetime.isoformat()  # e.g. "2025-10-21T19:30:00Z"
```

---

## Frontend Implementation Guide

### JavaScript/TypeScript

```typescript
// Get user's actual timezone
const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
// e.g., "America/Los_Angeles", "America/New_York", "Europe/London"

// Convert UTC ISO string to user's local time
function formatDateTime(utcString: string): string {
  const date = new Date(utcString);
  return date.toLocaleString('en-US', {
    timeZone: userTimezone,
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });
}

// Example usage:
// Backend returns: "2025-10-21T19:30:00Z"
// User in PST sees: "Oct 21, 2025, 12:30 PM"
// User in EST sees: "Oct 21, 2025, 3:30 PM"
// User in UTC sees: "Oct 21, 2025, 7:30 PM"
```

### Display Formatters

```typescript
// Short date (no time)
function formatDate(utcString: string): string {
  return new Date(utcString).toLocaleDateString('en-US', {
    timeZone: userTimezone,
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

// Relative time ("2 hours ago")
function formatRelativeTime(utcString: string): string {
  const date = new Date(utcString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

  if (diffHours < 1) return "just now";
  if (diffHours < 24) return `${diffHours} hours ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return "yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return formatDate(utcString);
}
```

---

## Testing

### Unit Tests

```python
def test_parse_time_period_utc():
    """All time parsing should return UTC-aware datetimes."""
    start, end, desc = parse_time_period("last week")

    assert start.tzinfo == UTC
    assert end.tzinfo == UTC
    assert end > start

def test_parse_health_record_date_utc():
    """Parsed health dates should be UTC-aware."""
    result = parse_health_record_date("2025-10-21 12:53:11")

    assert result.tzinfo == UTC
    assert result.year == 2025
```

### Integration Tests

```bash
# Test that queries work across timezones
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "what was my weight last week?", "user_id": "your_user"}'

# Response should include UTC timestamps
# Frontend converts to user's timezone
```

---

## Benefits

### ✅ Global Compatibility
- Works for users in any timezone
- No hardcoded timezone assumptions
- Easy to expand internationally

### ✅ Simplified Backend
- No timezone conversion logic
- Cleaner code
- Easier to test

### ✅ DST Handling
- UTC doesn't have DST
- No ambiguous times
- No "spring forward" / "fall back" bugs

### ✅ Frontend Flexibility
- Each user sees their local time
- Browser handles timezone detection
- Supports mobile apps with GPS-based timezones

---

## Migration Checklist

- [x] Remove `USER_TIMEZONE` constant
- [x] Refactor `parse_time_period()` to pure UTC
- [x] Update all datetime.now() calls to use UTC
- [x] Mark timezone formatting functions as deprecated
- [x] Document UTC-only architecture
- [x] Test with real health data
- [ ] Update frontend to handle timezone conversion
- [ ] Add timezone selector UI (optional)
- [ ] Add unit tests for all timezone edge cases

---

## Examples

### Backend API Response (UTC)
```json
{
  "response": "Your latest weight was 136.8 lbs on October 19th",
  "data": {
    "timestamp": "2025-10-19T12:53:11Z",  // ← UTC ISO format
    "value": 136.8,
    "unit": "lbs"
  }
}
```

### Frontend Display (User's Timezone)

**User in PST (UTC-7):**
```
Your latest weight was 136.8 lbs on October 19th at 5:53 AM PDT
```

**User in EST (UTC-4):**
```
Your latest weight was 136.8 lbs on October 19th at 8:53 AM EDT
```

**User in London (UTC+1):**
```
Your latest weight was 136.8 lbs on October 19th at 1:53 PM BST
```

---

## Common Pitfalls (Avoided)

### ❌ Don't Do This
```python
# BAD: Assuming user is in specific timezone
now_local = datetime.now()  # Naive datetime
now_pst = datetime.now(ZoneInfo("America/Los_Angeles"))  # Hardcoded
```

### ✅ Do This
```python
# GOOD: Pure UTC
now_utc = datetime.now(UTC)
```

### ❌ Don't Do This
```python
# BAD: Backend formatting for specific timezone
def format_for_user(dt):
    return dt.strftime("%b %d, %Y %I:%M %p PST")
```

### ✅ Do This
```python
# GOOD: Return UTC ISO, let frontend handle it
def format_for_api(dt):
    return dt.isoformat()  # "2025-10-21T19:30:00Z"
```

---

## References

- [ISO 8601 Standard](https://en.wikipedia.org/wiki/ISO_8601)
- [Python datetime Best Practices](https://docs.python.org/3/library/datetime.html)
- [JavaScript Intl.DateTimeFormat](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat)
- [Why UTC?](https://stackoverflow.com/questions/2532729/daylight-saving-time-and-time-zone-best-practices)

---

## Summary

**Before:**
- Backend assumed Pacific timezone
- Converted PST → UTC for storage
- Tightly coupled to single timezone
- Would break for users outside PST

**After:**
- Backend operates in pure UTC
- No timezone assumptions
- Frontend handles all timezone conversion
- Works globally out of the box

**Result:** Clean, maintainable, globally-compatible timezone architecture following industry best practices. 🌍✅
