# Utils Organization - Final State

**Date:** October 22, 2025
**Audience:** Senior Developers
**Status:** Production-Ready Demo Code

## Summary

**15 utils organized by purpose** - Clean, professional, appropriately documented for senior developers.

---

## Organization by Category

### 🎯 **Core Infrastructure (3 files)**

#### `user_config.py` (4.3K)
**Single-user configuration management**
- Environment-based user ID (`WELLNESS_USER_ID`)
- Redis key generation (sessions, health data, memory)
- Singleton pattern for global config
```python
get_user_id() → "wellness_user"
get_user_health_data_key() → "health:user:wellness_user:data"
```

#### `exceptions.py` (7.5K)
**Production exception hierarchy**
- Base: `WellnessError` (with correlation IDs)
- Business: `HealthDataNotFoundError`, `ToolExecutionError`
- Infrastructure: `RedisConnectionError`, `LLMServiceError`
- Standardized error responses

#### `api_errors.py` (8.1K)
**FastAPI error handling**
- HTTP status mapping (422, 503, etc.)
- Correlation ID middleware
- Exception handlers for FastAPI
- `setup_exception_handlers()` hook

---

### 🕐 **Time & Date Parsing (1 file)**

#### `time_utils.py` (12K)
**Natural language time period parsing**
```python
parse_time_period("last week") → (start_date, end_date, "Oct 15-22")
parse_time_period("September") → (sept_1, sept_30, "September 2025")
parse_health_record_date("2025-10-22T16:19:34+00:00") → datetime
```
- Month names ("September", "early August")
- Relative periods ("last 2 weeks", "this month")
- Apple Health date formats

---

### 📊 **Health Data Processing (7 files)**

#### `conversion_utils.py` (2.2K)
**Unit conversions**
```python
convert_weight_to_lbs("72.5", "kg") → "159.8 lbs"
kg_to_lbs(72.5) → 159.83
```

#### `metric_classifier.py` (5.6K)
**Aggregation strategy classification**
```python
get_aggregation_strategy("StepCount") → CUMULATIVE
get_aggregation_strategy("HeartRate") → DAILY_AVERAGE
get_aggregation_strategy("BodyMass") → LATEST_VALUE
```
- Prevents incorrect statistics (e.g., averaging steps instead of summing)

#### `metric_aggregators.py` (9.6K)
**Smart metric aggregation**
```python
aggregate_metric_values(records, "StepCount", date_range)
→ [12453, 8901, 15234]  # Daily totals
```
- Applies correct strategy per metric type
- HeartRate: average of daily averages
- StepCount: sum per day, then statistics

#### `health_analytics.py` (13K)
**Statistical analysis**
```python
calculate_weight_trends(records, "last_90_days")
→ {"slope": -0.12, "r_squared": 0.87, "trend": "decreasing"}

compare_time_periods(records, "HeartRate", "October", "September")
→ {"percent_change": -5.2%, "p_value": 0.03, "significant": True}
```
- Linear regression for trends
- Moving averages
- T-tests for significance

#### `stats_utils.py` (8.3K)
**Pure statistical functions**
```python
calculate_linear_regression(x, y) → (slope, intercept, r_squared, p_value)
compare_periods(period1, period2) → t_statistic, p_value
```
- No side effects - pure math
- Used by health_analytics

#### `numeric_validator.py` (10K)
**LLM hallucination detection**
```python
validator.validate_response(
    response_text="Your average is 72.5 bpm",
    tool_results=[{"average": "72.5 bpm"}]
) → {"valid": True, "score": 1.0}
```
- Extracts numbers from LLM response
- Compares against tool output
- Detects fabricated statistics

#### `base.py` (9.0K)
**Tool base classes**
```python
@measure_execution_time
def my_tool(user_id: str) -> ToolResult:
    return create_success_result({"data": "value"})
```
- `ToolResult` standardized format
- Performance decorators
- Validation helpers

---

### 🤖 **Agent Support (3 files)**

#### `agent_helpers.py` (6.5K)
**Shared agent utilities**
```python
create_health_llm() → ChatOllama(model="qwen2.5:7b", temperature=0.05)
build_base_system_prompt() → "You are a health AI..."
build_message_history(history, "current message", limit=10)
```
- Prevents code duplication between agents
- Standardized LLM configuration
- Message formatting

#### `verbosity_detector.py` (2.4K)
**Response style detection**
```python
detect_verbosity("Tell me more") → VerbosityLevel.DETAILED
detect_verbosity("Break it down") → VerbosityLevel.COMPREHENSIVE
detect_verbosity("What's my weight?") → VerbosityLevel.CONCISE
```
- Simple regex patterns
- No complex classification
- Replaced `query_classifier.py` (300 lines → 90 lines)

#### `pronoun_resolver.py` (6.2K)
**Pronoun resolution (Phase 2)**
```python
resolver.resolve_pronouns(session_id, "What was it?")
→ "What was my heart rate?"  # Resolves "it" from context
```
- Context tracking per session
- Enhances conversational UX

---

### 🧠 **Memory Management (1 file)**

#### `token_manager.py` (5.4K)
**Context window tracking**
```python
count_tokens(messages) → 8450
should_trim_context(8450, max=24000, threshold=0.8) → False
trim_messages(messages, keep=2) → trimmed_list
```
- Prevents Qwen 2.5 context overflow (32K window)
- Automatic message trimming at 80% threshold
- Used by memory_manager

---

## Documentation Quality Assessment

### ✅ **Well-Documented (Professional Level)**

**Module docstrings:**
```python
"""
Time parsing utilities for health data.

Handles natural language time periods and Apple Health date formats.
"""
```

**Function docstrings:**
```python
def parse_time_period(time_period: str) -> tuple[datetime, datetime, str]:
    """
    Parse natural language time period into date range.

    Args:
        time_period: Natural language ("last week", "September 2024")

    Returns:
        (start_date, end_date, description)

    Examples:
        parse_time_period("last week") → (2025-10-15, 2025-10-22, "Oct 15-22")
    """
```

**Verdict:** Just right for senior developers - clear purpose, examples where helpful, not over-explained.

---

### ⚠️ **Minor Overlap (Acceptable)**

**`base.py` vs `exceptions.py`:**
- Both define `ToolResult` and error handling
- **Reason:** Different contexts
  - `exceptions.py`: Application-wide exceptions
  - `base.py`: Tool-specific results and decorators
- **Verdict:** Keep separate - contexts are distinct

---

## File Size Distribution

```
Large (10K+):
  health_analytics.py     13K  - Complex statistical analysis
  time_utils.py           12K  - Many date parsing scenarios
  numeric_validator.py    10K  - LLM validation logic

Medium (5-10K):
  metric_aggregators.py   9.6K - Metric-specific aggregation
  base.py                 9.0K - Tool utilities
  stats_utils.py          8.3K - Pure math functions
  api_errors.py           8.1K - FastAPI error handling
  exceptions.py           7.5K - Exception hierarchy
  agent_helpers.py        6.5K - Agent utilities
  pronoun_resolver.py     6.2K - Pronoun resolution
  metric_classifier.py    5.6K - Metric classification
  token_manager.py        5.4K - Token tracking

Small (<5K):
  user_config.py          4.3K - User configuration
  verbosity_detector.py   2.4K - Verbosity detection
  conversion_utils.py     2.2K - Unit conversions
```

**Total:** ~110K (~3,000 lines across 15 files)

---

## Import Heat Map

**Most Critical (6+ imports):**
- `user_config.py` - Used everywhere
- `time_utils.py` - Used by all health tools

**Core (3-5 imports):**
- `exceptions.py` - Error handling
- `conversion_utils.py` - Health tools

**Moderate (2 imports):**
- `agent_helpers.py` - Both agents
- `verbosity_detector.py` - Both agents
- `numeric_validator.py` - Both agents
- `metric_aggregators.py` - Statistics + analytics
- `base.py` - Health manager + processors

**Specialized (1 import):**
- `health_analytics.py` - Trend tools
- `metric_classifier.py` - Statistics tool
- `stats_utils.py` - Analytics
- `token_manager.py` - Memory manager
- `pronoun_resolver.py` - Redis chat service
- `api_errors.py` - Main app

---

## Code Quality Standards

### ✅ **Followed Consistently**

1. **Type hints** - All functions have proper type annotations
2. **Docstrings** - Google-style with Args/Returns/Examples
3. **Pure functions** - Most utils are stateless (stats, conversion, time)
4. **Single responsibility** - Each file has clear purpose
5. **No circular dependencies** - Clean import graph
6. **Error handling** - Proper exception hierarchy
7. **Testing** - Key utils have unit tests

### 📏 **Naming Conventions**

- Files: `snake_case.py`
- Functions: `verb_noun()` (e.g., `parse_time_period()`)
- Classes: `PascalCase` (e.g., `VerbosityLevel`)
- Constants: `UPPER_CASE` (e.g., `DEFAULT_USER_ID`)

---

## What Makes This Demo-Ready

### For Senior Developers:

1. **Clean organization** - Easy to navigate by category
2. **Professional docs** - Clear without being patronizing
3. **No cruft** - Removed 3 unused files (query_classifier, performance_tool, memory_scope_classifier)
4. **Production patterns** - Exception hierarchy, correlation IDs, circuit breakers
5. **Type safety** - Full type hints throughout
6. **Testability** - Pure functions where possible
7. **Real-world complexity** - Handles edge cases (timezones, aggregation strategies)

### What Sets This Apart:

- **Smart metric aggregation** - Understands StepCount needs summing, HeartRate needs averaging
- **Hallucination detection** - Validates LLM responses against tool output
- **Token management** - Automatic context window trimming
- **Production error handling** - Correlation IDs, structured exceptions
- **Pronoun resolution** - Contextual "it"/"that" resolution

---

## Quick Navigation

```
utils/
├── Core Infrastructure
│   ├── user_config.py       # Single-user configuration
│   ├── exceptions.py        # Exception hierarchy
│   └── api_errors.py        # FastAPI error handling
│
├── Time & Date
│   └── time_utils.py        # Natural language parsing
│
├── Health Data
│   ├── conversion_utils.py      # Unit conversions
│   ├── metric_classifier.py     # Aggregation strategies
│   ├── metric_aggregators.py    # Smart aggregation
│   ├── health_analytics.py      # Statistical analysis
│   ├── stats_utils.py           # Pure math functions
│   ├── numeric_validator.py     # LLM validation
│   └── base.py                  # Tool utilities
│
├── Agent Support
│   ├── agent_helpers.py         # Shared utilities
│   ├── verbosity_detector.py    # Response style
│   └── pronoun_resolver.py      # Context resolution
│
└── Memory Management
    └── token_manager.py         # Context window tracking
```

---

## Testing Status

**Has Tests:**
- ✅ `numeric_validator.py` - Unit tests for validation
- ✅ `time_utils.py` - Parsing tests
- ✅ `stats_utils.py` - Math function tests

**Should Add Tests:**
- ⚠️ `health_analytics.py` - Trend calculations
- ⚠️ `metric_aggregators.py` - Aggregation strategies
- ⚠️ `pronoun_resolver.py` - Pronoun resolution

---

## Conclusion

**Production-ready utils for senior developer demo.**

**Strengths:**
- Clean organization by purpose
- Professional documentation level
- No unnecessary files
- Type-safe and testable
- Real production patterns

**Perfect for demo because:**
- Shows thought put into design
- Handles complex real-world scenarios
- Not over-engineered
- Easy to navigate and understand
- Production-grade error handling

**15 files, ~3,000 lines, zero cruft.** ✨
