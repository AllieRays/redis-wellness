# Comprehensive Data Enrichment Plan

## Current Status: ❌ INCOMPLETE

### Workouts: ✅ ENRICHED
- ISO datetime with timezone ✅
- `day_of_week` field ✅
- `date` field ✅
- `type_cleaned` field ✅
- `calories` standardized ✅

### Metrics: ❌ NEEDS ENRICHMENT
All metric types have **naive datetime** format (`2021-03-14 05:00:00` instead of ISO with timezone).

## Metrics Requiring Enrichment

### High-Value Metrics (Used Frequently)

1. **BodyMass** (431 records)
   - Current: `{"date": "2021-03-14 05:00:00", "value": "140", "unit": "lb"}`
   - Needs: ISO datetime, date field, day_of_week
   - Use case: "What's my weight trend?" "When did I weigh 140 lbs?"

2. **HeartRate** (100,047 records)
   - Current: Naive datetime
   - Needs: ISO datetime, date field, time_of_day (morning/afternoon/evening)
   - Use case: "What's my resting heart rate?" "Heart rate during workouts"

3. **StepCount** (25,387 records)
   - Current: Naive datetime
   - Needs: ISO datetime, date field, day_of_week
   - Use case: "How many steps today?" "What day do I walk most?"

4. **ActiveEnergyBurned** (13,643 records)
   - Current: Naive datetime
   - Needs: ISO datetime, date field, day_of_week
   - Use case: "How many calories burned?" "Activity trends"

5. **Sleep Analysis** (1,195 records)
   - Current: `{"date": "...", "value": "HKCategoryValueSleepAnalysisAsleepUnspecified"}`
   - Needs: ISO datetime, sleep_stage_cleaned ("Asleep", "Awake", "InBed"), duration calculation
   - Use case: "How much did I sleep?" "Sleep quality"

6. **BodyMassIndex** (359 records)
   - Current: Naive datetime
   - Needs: ISO datetime, date field
   - Use case: "What's my BMI trend?"

7. **DistanceWalkingRunning** (25,409 records)
   - Current: Naive datetime
   - Needs: ISO datetime, date field, day_of_week
   - Use case: "How far did I walk?" "Distance trends"

### Medium-Value Metrics

8. **DietaryEnergyConsumed** (178 records)
   - Needs: ISO datetime, date field
   - Use case: "How many calories did I eat?"

9. **DietaryWater** (29 records)
   - Needs: ISO datetime, date field
   - Use case: "Water intake tracking"

10. **Height** (6 records)
    - Needs: ISO datetime
    - Use case: Profile data

## Enrichment Fields Needed

### Universal Fields (All Metrics)
```python
{
    "date": "2025-10-17T16:59:18+00:00",  # ISO format with timezone
    "date_only": "2025-10-17",  # For easy filtering
    "value": "140",
    "unit": "lb",
    "source": "Connect"
}
```

### Time-Based Metrics (Steps, Heart Rate, Energy, Distance)
```python
{
    # ... universal fields ...
    "day_of_week": "Friday",  # Monday, Tuesday, etc.
    "time_of_day": "morning",  # morning/afternoon/evening/night
    "hour": 16  # 0-23 for hourly analysis
}
```

### Sleep-Specific
```python
{
    # ... universal fields ...
    "sleep_stage": "Asleep",  # Clean value (not HKCategoryValue...)
    "sleep_stage_raw": "HKCategoryValueSleepAnalysisAsleepUnspecified",  # Original
}
```

### Body Metrics (Weight, BMI)
```python
{
    # ... universal fields ...
    "value_numeric": 140.0,  # Always float for math
}
```

## Implementation Priority

### Phase 1: Critical Datetime Fixes (URGENT)
**Impact**: Fixes all timezone comparison bugs

1. Update `import_health.py` line 121: Use `.isoformat()` instead of `.strftime()`
2. Update `reload_health_data.py` to convert all existing naive datetimes to ISO
3. Test: Verify all dates have timezone

**Affected**: All 164,000+ metric records

### Phase 2: High-Value Enrichment
**Impact**: Enables pattern queries

1. Add `day_of_week` to: StepCount, ActiveEnergyBurned, DistanceWalkingRunning, BodyMass
2. Add `date_only` field to all metrics
3. Test: "What day do I walk most?" "Weight on Mondays vs Fridays"

**Affected**: ~65,000 records

### Phase 3: Sleep Analysis
**Impact**: Sleep quality insights

1. Clean sleep stage values
2. Calculate sleep duration from consecutive records
3. Group by night (not just date)
4. Test: "How much did I sleep last night?"

**Affected**: 1,195 records

### Phase 4: Time-of-Day Analysis
**Impact**: Circadian pattern insights

1. Add `time_of_day` and `hour` to HeartRate, ActiveEnergyBurned
2. Test: "What's my resting heart rate in the morning?"

**Affected**: ~113,000 records

## Updated `reload_health_data.py`

```python
#!/usr/bin/env python3
import json
import redis
from datetime import datetime, UTC

print("🔄 Reloading health data into Redis...")

# Load parsed data
with open('parsed_health_data.json') as f:
    data = json.load(f)

# Enrich ALL metrics with proper datetime
print("📝 Enriching metrics data...")
for metric_type, records in data.get('metrics_records', {}).items():
    for record in records:
        date_str = record.get('date', '')
        if date_str and 'T' not in date_str:  # Naive datetime
            try:
                # Convert naive datetime to ISO with UTC
                dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                dt = dt.replace(tzinfo=UTC)
                record['date'] = dt.isoformat()
                record['date_only'] = dt.strftime('%Y-%m-%d')
                record['day_of_week'] = dt.strftime('%A')
                record['hour'] = dt.hour

                # Time of day classification
                hour = dt.hour
                if 5 <= hour < 12:
                    record['time_of_day'] = 'morning'
                elif 12 <= hour < 17:
                    record['time_of_day'] = 'afternoon'
                elif 17 <= hour < 21:
                    record['time_of_day'] = 'evening'
                else:
                    record['time_of_day'] = 'night'
            except:
                pass

# Enrich sleep data
sleep_records = data.get('metrics_records', {}).get('HKCategoryTypeIdentifierSleepAnalysis', [])
for record in sleep_records:
    value = record.get('value', '')
    if 'HKCategoryValue' in value:
        # Clean sleep stage
        clean = value.replace('HKCategoryValueSleepAnalysis', '')
        record['sleep_stage'] = clean
        record['sleep_stage_raw'] = value

# Enrich workouts (already done, but ensure consistency)
print("📝 Enriching workout data...")
for workout in data.get('workouts', []):
    start_date_str = workout.get('startDate', '')
    if start_date_str:
        try:
            dt = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            workout['day_of_week'] = dt.strftime('%A')
            workout['date'] = dt.strftime('%Y-%m-%d')
            workout['hour'] = dt.hour
        except:
            pass

    # Clean up type
    workout_type = workout.get('type', '')
    if workout_type.startswith('HKWorkoutActivityType'):
        workout['type_cleaned'] = workout_type.replace('HKWorkoutActivityType', '')
    else:
        workout['type_cleaned'] = workout_type

    # Standardize energy field
    if 'totalEnergyBurned' in workout and 'calories' not in workout:
        workout['calories'] = workout['totalEnergyBurned']

# Connect to Redis and store
client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
client.ping()

main_key = 'health:user:wellness_user:data'
client.set(main_key, json.dumps(data))

print(f'✅ Loaded {len(data.get("workouts", []))} workouts')
print(f'✅ Loaded {len(data.get("metrics_records", {}))} metric types')
print(f'✅ Enriched {sum(len(v) for v in data.get("metrics_records", {}).values())} metric records')
print(f'✅ Stored at key: {main_key}')
```

## Testing Plan

### Test 1: Datetime Format
```bash
# All dates should be ISO format
docker exec redis-wellness redis-cli GET "health:user:wellness_user:data" | \
  python3 -c "import sys, json; data=json.loads(sys.stdin.read()); \
  sample=data['metrics_records']['BodyMass'][0]; \
  print('✅ ISO' if 'T' in sample['date'] and '+' in sample['date'] else '❌ NAIVE')"
```

### Test 2: Day-of-Week Queries
```bash
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "What day do I walk the most steps?", "session_id": "test"}'
```

### Test 3: Sleep Analysis
```bash
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "How much did I sleep last night?", "session_id": "test"}'
```

## Long-Term: Pydantic Data Models

Create strict schemas to enforce enrichment:

```python
from pydantic import BaseModel
from datetime import datetime

class EnrichedMetric(BaseModel):
    date: datetime  # Must be timezone-aware
    date_only: str
    day_of_week: str
    value: str
    unit: str | None
    source: str

class EnrichedWorkout(BaseModel):
    date: datetime
    date_only: str
    day_of_week: str
    type_cleaned: str
    calories: float | None
    duration_minutes: float | None
    # ...
```

## Benefits After Full Enrichment

1. **No timezone bugs** - All comparisons work correctly
2. **Pattern queries work** - "What day do I...?" queries succeed
3. **Time-based insights** - Morning vs evening patterns
4. **Sleep analysis** - Duration, quality, consistency
5. **Repeatable** - New uploads automatically enriched
6. **LLM-friendly** - Data ready for analysis, no preprocessing needed

## Status Tracking

- [x] Audit completed
- [x] Plan documented
- [ ] Phase 1: Fix datetime formats
- [ ] Phase 2: Add day_of_week to high-value metrics
- [ ] Phase 3: Sleep enrichment
- [ ] Phase 4: Time-of-day enrichment
- [ ] Testing and validation
- [ ] Update import_health.py with all enrichment
