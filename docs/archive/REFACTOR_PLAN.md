# Health Metrics Aggregation Refactoring Plan

## Problem
- `tools/agent_tools.py` is 800+ lines with one-size-fits-all aggregation
- Step counts return individual readings (948, 410, 22) instead of daily totals (20,646)
- Heart rate would sum all BPM readings instead of averaging
- Weight would sum all measurements instead of trending

## Solution: Proper Separation of Concerns

### 1. NEW UTILS (Pure Functions)
Create dedicated utilities in `/utils` for each aggregation pattern:

#### `utils/metric_aggregators.py` (NEW)
```python
def aggregate_daily_sums(records, date_range) -> dict[date, float]
    """For StepCount, DistanceWalkingRunning - sum incremental readings by day"""

def aggregate_daily_averages(records, date_range) -> dict[date, float]
    """For HeartRate - average multiple readings by day"""

def aggregate_daily_latest(records, date_range) -> dict[date, float]
    """For BodyMass, Height - take latest reading per day"""

def get_individual_values(records, date_range) -> list[float]
    """For BMI, ActiveEnergy - use readings directly"""
```

#### `utils/metric_classifier.py` (NEW)
```python
CUMULATIVE_METRICS = {"StepCount", "DistanceWalkingRunning", "DietaryWater"}
HIGH_FREQ_POINT_METRICS = {"HeartRate"}
LATEST_VALUE_METRICS = {"BodyMass", "Height"}
POINT_IN_TIME_METRICS = {"BodyMassIndex", "ActiveEnergyBurned"}

def get_metric_aggregation_strategy(metric_type: str) -> str
def should_aggregate_daily(metric_type: str) -> bool
```

### 2. REFACTOR EXISTING TOOLS
Break down the monolithic `agent_tools.py` into focused tools:

#### `tools/metric_aggregation_tool.py` (REFACTORED)
- Clean, focused aggregation logic
- Uses utils for actual aggregation
- Metric-aware aggregation strategy
- ~100-150 lines instead of 800+

#### Keep existing tools:
- `tools/health_insights_tool.py` - Health insights generation
- `tools/health_parser_tool.py` - Apple Health XML parsing

### 3. REMOVE/REPLACE
- Remove monolithic aggregation logic from `agent_tools.py`
- Replace with calls to focused utils
- Keep the tool interface the same for LLM compatibility

## Implementation Steps

### Step 1: Create metric aggregation utilities
```bash
touch backend/src/utils/metric_aggregators.py
touch backend/src/utils/metric_classifier.py
```

### Step 2: Extract pure aggregation logic to utils
- Daily aggregation functions
- Metric classification constants
- Strategy selection logic

### Step 3: Refactor agent_tools.py
- Replace 600+ line aggregation logic with utils calls
- Keep same tool interface for LLM
- Add proper logging and error handling

### Step 4: Test and validate
- Unit tests for each aggregation strategy
- Integration tests with real data
- Validate step counts return daily totals

## Expected Results

### Before (Broken):
```
StepCount last 30 days: 880 readings
Sample: 948, 410, 22, 16 steps
Total: 199,209 (meaningless sum of all readings)
```

### After (Fixed):
```
StepCount last 30 days: 30 daily totals
Daily totals: 20,646, 6,918, 2,980 steps
Average daily: 6,640 steps
Most active day: 20,646 steps
```

## File Structure After Refactor
```
backend/src/
├── utils/
│   ├── metric_aggregators.py     # Daily aggregation functions (NEW)
│   ├── metric_classifier.py     # Metric type strategies (NEW)
│   ├── stats_utils.py           # Statistical calculations (EXISTS)
│   ├── conversion_utils.py      # Unit conversions (EXISTS)
│   └── time_utils.py            # Time parsing (EXISTS)
├── tools/
│   ├── metric_aggregation_tool.py  # Clean aggregation tool (REFACTORED)
│   ├── health_insights_tool.py     # Health insights (EXISTS)
│   └── health_parser_tool.py       # XML parsing (EXISTS)
```

## Benefits
- ✅ **Separation of concerns**: Utils = pure functions, Tools = LLM interface
- ✅ **Testable**: Each aggregation strategy can be unit tested
- ✅ **Maintainable**: Small, focused files instead of 800-line monolith
- ✅ **Accurate**: Step counts show daily totals, heart rate averages correctly
- ✅ **Extensible**: Easy to add new metric types with specific strategies
