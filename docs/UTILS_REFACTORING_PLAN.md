# Utils Refactoring Plan: Agent Tools Focus

Based on the comprehensive review, the **agents and services are using utils excellently**. The refactoring focus should be on the **tools layer** to match the quality patterns already established.

## Phase 1: High Priority - Agent Tools Cleanup

### 1.1 Move Inline Imports to Module Level (Quick Win)

**Current Problem:**
```python
# Inside function - BAD
def calculate_weight_trends_tool(...):
    from ..utils.health_analytics import calculate_weight_trends  # ❌ Inline
```

**Solution:**
```python
# At module level - GOOD
from ..utils.health_analytics import (
    calculate_weight_trends,
    compare_time_periods,
    correlate_metrics,
)

def calculate_weight_trends_tool(...):
    result = calculate_weight_trends(...)  # ✅ Direct use
```

**Files to Update:**
- `backend/src/tools/agent_tools.py` (lines 760, 830)

**Impact:**
- ✅ Better performance (no repeated imports)
- ✅ Clear dependencies at module level
- ✅ Consistent with other modules

### 1.2 Add Missing Utils Imports

**Current:** Ad-hoc imports scattered throughout
**Solution:** Consolidate all utility imports at the top:

```python
# Add to agent_tools.py imports section
from ..utils.health_analytics import (
    calculate_weight_trends,
    compare_time_periods,
    correlate_metrics,
)
from ..utils.metric_aggregators import aggregate_metric_values
from ..utils.metric_classifier import get_aggregation_strategy
from ..utils.conversion_utils import kg_to_lbs
from ..utils.time_utils import parse_time_period, parse_health_record_date
```

### 1.3 Standardize Error Handling Pattern

**Current Problem:** Mixed error handling approaches
**Solution:** Use consistent pattern throughout tools:

```python
# Add to utils/agent_helpers.py
def build_tool_error_response(error: Exception, tool_name: str) -> dict[str, Any]:
    """Standardized error response for tools."""
    logger.error(f"Tool {tool_name} failed: {error}", exc_info=True)
    return {
        "error": f"Failed to {tool_name.replace('_', ' ')}: {str(error)}",
        "error_type": type(error).__name__,
        "results": [],
    }
```

## Phase 2: Medium Priority - Extract Tool Business Logic

### 2.1 Create Health Tool Services Layer

**Goal:** Extract business logic from `agent_tools.py` into dedicated services

**New File:** `backend/src/services/health_tool_services.py`

```python
class HealthDataService:
    """Business logic for health data operations."""

    def __init__(self, redis_manager, memory_manager=None):
        self.redis_manager = redis_manager
        self.memory_manager = memory_manager

    async def search_health_records(
        self, user_id: str, metric_types: list[str], time_period: str
    ) -> dict[str, Any]:
        """Business logic for health record search."""
        # Move current logic from agent_tools.py here

    async def aggregate_health_metrics(
        self, user_id: str, metric_types: list[str], aggregations: list[str], time_period: str
    ) -> dict[str, Any]:
        """Business logic for metric aggregation."""
        # Move current logic from agent_tools.py here

    async def search_workouts(
        self, user_id: str, days_back: int, activity_type: str
    ) -> dict[str, Any]:
        """Business logic for workout search."""
        # Move current logic from agent_tools.py here
```

### 2.2 Simplify Agent Tools

**Goal:** Keep `agent_tools.py` focused ONLY on LangChain tool interfaces

```python
# Simplified tool pattern
@tool
def search_health_records_by_metric(
    metric_types: list[str], time_period: str = "recent"
) -> dict[str, Any]:
    """Search for specific health metrics within a time period."""
    try:
        # Simple delegation to service layer
        service = get_health_data_service(user_id)
        return await service.search_health_records(user_id, metric_types, time_period)
    except Exception as e:
        return build_tool_error_response(e, "search_health_records_by_metric")
```

## Phase 3: Lower Priority - Service Layer Enhancements

### 3.1 Add Memory Service Layer (Optional)

**Current:** Agents call memory_manager directly
**Potential Improvement:** Add service wrapper for consistent error handling

```python
# New file: backend/src/services/memory_service.py
class MemoryService:
    """Service layer for memory operations with consistent error handling."""

    def __init__(self, memory_manager):
        self.memory_manager = memory_manager

    async def get_conversation_context(self, user_id: str, session_id: str) -> dict:
        """Get conversation context with error handling."""
        try:
            return await self.memory_manager.get_short_term_context(user_id, session_id)
        except Exception as e:
            logger.warning(f"Memory retrieval failed: {e}")
            return {"context": None, "error": str(e)}
```

**Note:** This is optional since current memory usage works well.

## Implementation Priority

### ✅ **Phase 1 (High Priority - Do First)**
- [x] Fix inline imports in agent_tools.py
- [x] Standardize error handling
- [x] Add missing utility imports

### 🔄 **Phase 2 (Medium Priority - Optional)**
- [ ] Extract tool business logic to services
- [ ] Simplify agent_tools.py interfaces

### ⏸️ **Phase 3 (Low Priority - Skip for Now)**
- [ ] Memory service wrapper (current pattern works fine)

## Benefits of This Plan

### Immediate Benefits (Phase 1):
- 🚀 **Performance:** No repeated inline imports
- 📖 **Readability:** Clear dependencies at module level
- 🔧 **Maintainability:** Consistent error handling
- ✅ **Consistency:** Matches excellent patterns in agents/services

### Future Benefits (Phase 2):
- 🧪 **Testability:** Business logic separated from tool interfaces
- 🏗️ **Architecture:** Clean separation of concerns
- 📦 **Modularity:** Smaller, focused modules

## What NOT to Change

### ✅ Keep These Excellent Patterns:
- **Agent utilities** (`agent_helpers.py`) - Perfect as-is
- **Service layer separation** - Clean and well-designed
- **Utils organization** - Good separation of pure vs stateful functions
- **Validation patterns** - Consistent across both agents

## Success Metrics

After refactoring:
- [ ] No inline imports in any tools
- [ ] Consistent error handling across all tools
- [ ] Clear dependency declarations at module level
- [ ] All tests pass
- [ ] No performance regression
- [ ] Tool interfaces remain identical (backward compatibility)

This plan focuses on **high-impact, low-risk improvements** that align the tools layer with the excellent patterns already established in the agents and services.
