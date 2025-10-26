# Refactor: `get_health_metrics.py` - Optimized for LLM Consumption

**Date**: October 26, 2025
**File**: `backend/src/apple_health/query_tools/get_health_metrics.py`
**Status**: ✅ Complete - All tests passing

## Summary

Refactored the health metrics tool to provide cleaner, more consistent data to the LLM chat agent. This improves the agent's ability to understand and work with health data.

---

## Key Improvements

### 1. **Unified Response Schema** ✅

**Before**: Raw mode returned two different shapes depending on data source
```python
# If historical records exist:
{"metric_type": "BodyMass", "records": [...]}

# If falling back to summary:
{"metric_type": "BodyMass", "latest_value": "150.5 lbs", "latest_date": "2025-10-20"}
```

**After**: Consistent structure regardless of data source
```python
{
    "metric": "BodyMass",
    "unit": "lbs",
    "count": 5,
    "data": [
        {"date": "2025-10-20", "value": 150.5},
        {"date": "2025-10-21", "value": 149.8}
    ],
    "data_source": "historical"  # or "summary_fallback" or "none"
}
```

**Impact**: LLM no longer needs to handle multiple schemas for the same mode.

---

### 2. **Separated Numeric from Formatted Values** ✅

**Before**: Mixed data types in statistics
```python
{"average": "87.5 bpm (daily avg)"}  # String only
```

**After**: Both numeric and formatted available
```python
{
    "average": {
        "value": 87.5,          # Numeric for calculations
        "formatted": "87.5 bpm (daily avg)"  # Human-readable
    }
}
```

**Impact**: LLM can perform calculations on numeric values if needed, while still having clean formatted strings for display.

---

### 3. **Extracted Formatting Logic** ✅

**Before**: Copypasta formatting code repeated 4 times (average, min, max, sum)
```python
if metric_type == "StepCount":
    statistics["average"] = f"{avg_value:.0f} steps/day"
elif metric_type == "HeartRate":
    statistics["average"] = f"{avg_value:.1f} bpm (daily avg)"
# ... repeated for min, max, sum
```

**After**: Single helper function
```python
def _format_stat_value(
    metric_type: str, stat_type: str, value: float, unit: str, sample_size: int = 0
) -> dict[str, Any]:
    """Format statistic value with metric-specific context."""
    formatters = {
        "StepCount": {
            "average": lambda v: f"{v:.0f} steps/day",
            "min": lambda v: f"{v:.0f} steps (lowest day)",
            # ...
        },
        # ...
    }
    # Single source of truth for formatting
```

**Impact**: Easier to maintain and extend. Adding new metrics or modifying formats requires changes in one place only.

---

### 4. **Reduced Logging Noise** ✅

**Before**: Verbose emoji logs cluttering LLM context
```python
logger.info("📅 Parsed 'last week' → 2025-01-15 to 2025-01-22")
logger.info("📊 Found 150 total StepCount records")
logger.info("✅ Filtered to 7 StepCount records (last week)")
```

**After**: Debug level for details, info for milestones only
```python
logger.debug("Parsed 'last week' → 2025-01-15 to 2025-01-22")
logger.debug("Found 150 total StepCount records")
logger.info("Filtered to 7 StepCount records in last week")  # Key milestone only
```

**Impact**: Cleaner logs reduce token consumption and improve LLM focus on relevant information.

---

### 5. **Cleaner Imports** ✅

**Before**: Dual imports with unnecessary aliasing
```python
from ...utils.conversion_utils import (
    convert_weight_to_lbs as _convert_weight_to_lbs,
)
from ...utils.conversion_utils import (
    kg_to_lbs as _kg_to_lbs,
)
```

**After**: Consolidated imports
```python
from ...utils.conversion_utils import kg_to_lbs
```

**Impact**: More readable and maintainable code.

---

### 6. **Better Error Handling** ✅

**Before**: Generic catch-all
```python
except Exception as e:
    raise ToolExecutionError("get_health_metrics", str(e)) from e
```

**After**: Specific exception handling
```python
except HealthDataNotFoundError:
    raise
except json.JSONDecodeError as e:
    logger.error(f"Invalid health data format: {e}", exc_info=True)
    raise ToolExecutionError("get_health_metrics", f"Invalid health data format: {e}") from e
except Exception as e:
    logger.error(f"Error in get_health_metrics: {type(e).__name__}: {e}", exc_info=True)
    raise ToolExecutionError("get_health_metrics", str(e)) from e
```

**Impact**: Better debugging and more informative error messages.

---

### 7. **Consistent Field Naming** ✅

**Before**: Verbose field names
```python
{"metric_type": "BodyMass", "statistics": {...}}
```

**After**: Concise, consistent naming
```python
{"metric": "BodyMass", "stats": {...}}
```

**Impact**: Shorter field names reduce token consumption while maintaining clarity.

---

## Response Schema Examples

### Raw Data Mode
```json
{
    "mode": "raw_data",
    "time_range": "September 2024",
    "total_metrics": 2,
    "results": [
        {
            "metric": "BodyMass",
            "unit": "lbs",
            "count": 15,
            "data": [
                {"date": "2024-09-01", "value": 150.5},
                {"date": "2024-09-02", "value": 149.8}
            ],
            "data_source": "historical"
        }
    ]
}
```

### Statistics Mode
```json
{
    "mode": "statistics",
    "time_range": "last week",
    "total_metrics": 1,
    "results": [
        {
            "metric": "HeartRate",
            "unit": "bpm",
            "sample_size": 7,
            "aggregation_strategy": "daily_average",
            "original_records": 150,
            "stats": {
                "average": {
                    "value": 87.5,
                    "formatted": "87.5 bpm (daily avg)"
                },
                "min": {
                    "value": 65.0,
                    "formatted": "65.0 bpm (lowest daily avg)"
                },
                "max": {
                    "value": 110.0,
                    "formatted": "110.0 bpm (highest daily avg)"
                }
            }
        }
    ]
}
```

---

## Files Modified

1. **`backend/src/apple_health/query_tools/get_health_metrics.py`**
   - Refactored `_get_raw_data()` for unified schema
   - Added `_format_stat_value()` helper
   - Refactored `_calculate_statistics()` to use helper
   - Improved error handling and logging

2. **`backend/tests/integration/test_health_tools.py`**
   - Updated assertions to match new field names:
     - `metric_type` → `metric`
     - `records` → `data`
     - `statistics` → `stats`

---

## Testing

✅ **All tests passing**
```bash
cd backend
uv run pytest tests/integration/test_health_tools.py::TestGetHealthMetricsTool -v
# 4 passed
```

✅ **Code quality checks passing**
```bash
uv run ruff check src/apple_health/query_tools/get_health_metrics.py
# No errors
uv run ruff format src/apple_health/query_tools/get_health_metrics.py
# Formatted
```

---

## Benefits for LLM

1. **Consistent Structure**: LLM doesn't need to handle multiple schemas
2. **Numeric Values Available**: Can perform calculations when needed
3. **Reduced Token Usage**: Shorter field names and less logging noise
4. **Clear Data Source**: `data_source` field indicates origin of data
5. **Flat Hierarchy**: Less nesting makes parsing easier
6. **Type Safety**: Numeric values always numeric, strings always strings

---

## Future Optimization Opportunities

1. **Cache Parsed JSON**: Parse health data once at service layer instead of on every call
2. **Redis Hash Structures**: Use Redis hashes instead of JSON strings for faster access
3. **Batch Conversion**: Convert units during aggregation phase to avoid double iteration
4. **Streaming Results**: For large datasets, consider streaming results back to LLM

---

## Related Files

- Tool definition: `backend/src/apple_health/query_tools/get_health_metrics.py`
- Tests: `backend/tests/integration/test_health_tools.py`
- Conversion utils: `backend/src/utils/conversion_utils.py`
- Metric aggregators: `backend/src/utils/metric_aggregators.py`
- WARP guidance: `/Users/allierays/Sites/redis-wellness/WARP.md`
