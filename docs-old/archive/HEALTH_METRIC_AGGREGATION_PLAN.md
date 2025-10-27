# Health Metric Aggregation Strategy Plan

Based on comprehensive analysis of actual Apple Health data patterns over 30 days.

## 🔍 Analysis Results

| Metric | Records | Readings/Day | Strategy | Rationale |
|--------|---------|--------------|----------|-----------|
| **StepCount** | 883 | 29.4 | CUMULATIVE | High-frequency incremental readings |
| **DistanceWalkingRunning** | 632 | 21.1 | CUMULATIVE | Distance accumulates throughout day |
| **HeartRate** | 3,585 | 239.0 | ⚠️ SPECIAL | Too many for simple sum - need average |
| **ActiveEnergyBurned** | 25 | 1.9 | POINT-IN-TIME | Low frequency complete measurements |
| **BodyMassIndex** | 14 | 2.0 | POINT-IN-TIME | Each BMI reading is complete |
| **BodyMass** | 20 | 2.9 | ⚠️ UNCLEAR | Medium frequency - needs decision |
| **Sleep Analysis** | 53 | 26.5 | SPECIAL | Categorical data, needs duration calc |

## 📋 Implementation Strategy

### 1. CUMULATIVE METRICS (Daily Aggregation First)
**Metrics**: `StepCount`, `DistanceWalkingRunning`
**Logic**: Sum all readings per day → calculate statistics on daily totals

```python
# Example: StepCount
# Raw: [250, 488, 686, 435, 849] steps throughout Oct 17
# Daily total: 2,708 steps on Oct 17
# Statistics: avg_daily_steps, max_daily_steps, total_steps_month
```

**Why**: Users expect daily step totals (20,646 steps), not individual readings (488 steps)

### 2. POINT-IN-TIME METRICS (Direct Statistics)
**Metrics**: `ActiveEnergyBurned`, `BodyMassIndex`
**Logic**: Use individual readings directly for statistics

```python
# Example: BodyMassIndex
# Raw: [23.9, 23.7, 23.8, 24.2, 23.8] BMI readings
# Statistics: avg_BMI=23.88, min_BMI=23.7, max_BMI=24.2
```

**Why**: Each reading is a complete measurement, averaging makes sense

### 3. SPECIAL CASES

#### 3.1 HeartRate (High Frequency Point Data)
**Problem**: 239 readings/day - too many for sum, but each is a complete measurement
**Strategy**: Average per day first → statistics on daily averages

```python
# Raw: [81, 87, 77, 77, 77] bpm readings throughout day
# Daily average: 79.8 bpm on that day
# Statistics: avg_daily_hr, min_daily_hr, max_daily_hr
```

#### 3.2 BodyMass (Medium Frequency)
**Problem**: 2.9 readings/day - unclear if sum or average
**Decision**: Use LATEST reading per day → statistics on daily weights
**Rationale**: Multiple weight readings per day = user stepped on scale multiple times, latest is most accurate

```python
# Raw: [138.6, 137.2, 137.6] lbs on same day
# Daily value: 137.6 lbs (latest reading)
# Statistics: avg_weight, weight_change, weight_trend
```

#### 3.3 Sleep Analysis (Categorical Time-Based)
**Problem**: Categories like "AsleepCore", "AsleepDeep" with time ranges
**Strategy**: Calculate total sleep duration per day → statistics on sleep hours

### 4. DEFAULT FALLBACK
For unknown metrics: Analyze frequency automatically
- If avg_readings/day ≥ 10: Treat as CUMULATIVE
- If avg_readings/day ≤ 2: Treat as POINT-IN-TIME
- Else: Use POINT-IN-TIME (safer default)

## 🛠️ Implementation Requirements

### 1. New Aggregation Function
```python
def aggregate_metric_values(records, metric_type, date_range):
    """
    Apply metric-specific aggregation logic before statistics
    """
    if metric_type in CUMULATIVE_METRICS:
        return aggregate_daily_sums(records, date_range)
    elif metric_type in HIGH_FREQ_POINT_METRICS:
        return aggregate_daily_averages(records, date_range)
    elif metric_type in LATEST_VALUE_METRICS:
        return get_daily_latest_values(records, date_range)
    else:
        return get_individual_values(records, date_range)
```

### 2. Metric Classification Constants
```python
CUMULATIVE_METRICS = {
    "StepCount",
    "DistanceWalkingRunning",
    "DietaryWater",          # Water intake accumulates
    "DietaryEnergyConsumed"  # Calories consumed accumulate
}

HIGH_FREQ_POINT_METRICS = {
    "HeartRate"  # Average multiple readings per day
}

LATEST_VALUE_METRICS = {
    "BodyMass",      # Latest weight reading per day
    "Height"         # Latest height (rarely changes)
}

POINT_IN_TIME_METRICS = {
    "BodyMassIndex",        # Each BMI calculation is complete
    "ActiveEnergyBurned"    # Each workout burn reading is complete
}
```

### 3. Updated Tool Responses

#### Before (Wrong):
```
StepCount stats for last 30 days:
- 880 individual readings found
- Sample values: 948, 410, 22, 16 steps
- Average: 225 steps per reading
```

#### After (Correct):
```
StepCount stats for last 30 days:
- 30 daily totals calculated
- Daily totals: 20,646, 6,918, 2,980 steps
- Average daily steps: 6,640
- Most active day: 20,646 steps
- Total monthly steps: 199,209
```

## 🎯 Expected Impact

1. **Step Counts**: Will show meaningful daily totals instead of confusing individual readings
2. **Heart Rate**: Will show daily averages instead of summing all BPM readings
3. **Weight**: Will show weight trends instead of nonsensical weight sums
4. **Consistency**: All metrics will provide user-expected statistics
5. **Accuracy**: Prevents LLM from giving misleading health information

## ✅ Validation Plan

1. Test each metric type with known data
2. Verify daily aggregation math is correct
3. Compare old vs new tool outputs
4. Ensure edge cases (no data, single reading) work
5. Test with actual user queries about steps, weight, etc.
