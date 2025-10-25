# Apple Health Data Guide

**Teaching Goal:** Understand how to export Apple Health data from iPhone, import it into Redis, and why Apple Health is ideal for teaching time-series health data patterns.

## Why Apple Health?

### The Problem with Synthetic Data

**Synthetic health data (typical demo approach):**
```python
# Fake data - obvious patterns, no real variance
workouts = [
    {"date": "2024-10-01", "type": "Running", "calories": 300},
    {"date": "2024-10-02", "type": "Running", "calories": 300},
    {"date": "2024-10-03", "type": "Running", "calories": 300},
    # ...perfectly consistent
]
```

**Problems:**
- **Too clean:** Real health data is messy (missed workouts, varying intensity)
- **No patterns:** Real users work out on specific days, have favorite activities
- **Unrealistic queries:** "What day do I work out most?" is obvious with synthetic data
- **No teaching value:** Doesn't prepare you for production health apps

### Why Apple Health is Realistic

**Apple Health exports provide:**

1. **Real time-series data** - Years of actual health metrics
2. **Natural variance** - Missed workouts, intensity fluctuations, seasonal patterns
3. **Multiple metrics** - Weight, heart rate, steps, sleep, workouts (not just one)
4. **Complex relationships** - Heart rate during workouts, weight trends over time
5. **Privacy-preserving** - Stays on your machine (no cloud upload)

**Example: Real workout pattern**
```
Monday: Strength Training (high intensity, evening)
Tuesday: Rest
Wednesday: Yoga (low intensity, morning)
Thursday: Rest
Friday: Cycling (high intensity, lunch)
Saturday: Running (moderate, morning)
Sunday: Rest

→ Teaches agents about:
- Weekly patterns (workout on Mon/Wed/Fri/Sat)
- Intensity variation (high on Mon/Fri, low on Wed)
- Time-of-day preferences (morning on Sat/Sun, evening on Mon)
```

This data teaches agents to handle **real-world complexity**, not just toy examples.

## Exporting Apple Health Data from iPhone

### Step 1: Open Health App

1. Open **Health** app on iPhone
2. Tap your **profile picture** (top-right corner)

### Step 2: Export All Health Data

1. Scroll down to **"Export All Health Data"**
2. Tap it - you'll see a warning:
   ```
   "This will export all your health and fitness data as an XML file.
   The export may take several minutes."
   ```
3. Tap **Export** and wait (2-10 minutes depending on data size)

### Step 3: Save Export

1. iOS will show **Share Sheet**
2. Choose **Save to Files** (or AirDrop to your Mac)
3. Save as `export.zip` in a location you remember

### Step 4: Unzip Export

```bash
# Unzip export
unzip export.zip

# You'll see:
# export.xml              (main health data - 50-200 MB)
# workout-routes/         (GPS tracks - optional)
# export_cda.xml          (clinical records - optional)
```

### What's in the Export?

**File structure:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
  <ExportDate value="2024-10-25 14:30:00 +0000"/>
  <Me HKCharacteristicTypeIdentifierDateOfBirth="1990-01-01"
      HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexMale"
      HKCharacteristicTypeIdentifierBloodType="HKBloodTypeAPositive"
      HKCharacteristicTypeIdentifierFitzpatrickSkinType="HKFitzpatrickSkinTypeNotSet"/>

  <!-- Health Records (weight, heart rate, steps, etc.) -->
  <Record type="HKQuantityTypeIdentifierBodyMass"
          sourceName="Health"
          unit="lb"
          creationDate="2024-10-22 07:15:00 +0000"
          startDate="2024-10-22 07:15:00 +0000"
          endDate="2024-10-22 07:15:00 +0000"
          value="136.8"/>

  <Record type="HKQuantityTypeIdentifierHeartRate"
          sourceName="Apple Watch"
          unit="count/min"
          creationDate="2024-10-22 14:32:05 +0000"
          startDate="2024-10-22 14:32:00 +0000"
          endDate="2024-10-22 14:32:05 +0000"
          value="68"/>

  <!-- Workouts -->
  <Workout workoutActivityType="HKWorkoutActivityTypeCycling"
           duration="45.12"
           durationUnit="min"
           totalDistance="15.3"
           totalDistanceUnit="mi"
           totalEnergyBurned="420"
           totalEnergyBurnedUnit="kcal"
           sourceName="Apple Watch"
           creationDate="2024-10-17 12:34:56 +0000"
           startDate="2024-10-17 12:00:00 +0000"
           endDate="2024-10-17 12:45:07 +0000">

    <!-- Heart rate samples during workout -->
    <WorkoutEvent type="HKWorkoutEventTypePause"
                  date="2024-10-17 12:15:00 +0000"/>
    <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate"
                       average="142" unit="count/min"
                       minimum="98" maximum="168"/>
  </Workout>

  <!-- More records... -->
</HealthData>
```

**Key sections:**
- **`<Record>`** - Individual health metrics (weight, heart rate, steps, sleep)
- **`<Workout>`** - Exercise sessions with duration, calories, heart rate zones
- **`<WorkoutStatistics>`** - Aggregated stats per workout (avg/min/max heart rate)

## Importing Apple Health Data into Redis

### Import Script Overview

The demo includes a Python script that:
1. Parses XML export
2. Normalizes data (clean types, convert units, add day_of_week)
3. Builds Redis indexes (HASH, ZSET for fast queries)
4. Stores everything in Redis

**Location:** `/Users/allierays/Sites/redis-wellness/backend/import_health_data.py` (if exists)

### Manual Import (if script doesn't exist)

If you don't have the import script, here's the pattern:

```python
import xml.etree.ElementTree as ET
from datetime import datetime, UTC
import json
import redis

def parse_apple_health_export(xml_path: str) -> dict:
    """Parse Apple Health XML export."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    health_data = {
        "metrics_summary": {},
        "metrics_records": {},
        "workouts": []
    }

    # Parse health records (weight, heart rate, etc.)
    for record in root.findall("Record"):
        record_type = record.get("type", "")
        value = record.get("value", "")
        unit = record.get("unit", "")
        start_date = record.get("startDate", "")

        # Clean type name: "HKQuantityTypeIdentifierBodyMass" → "BodyMass"
        metric_type = record_type.replace("HKQuantityTypeIdentifier", "")

        if metric_type not in health_data["metrics_records"]:
            health_data["metrics_records"][metric_type] = []

        # Parse date (ISO format with timezone)
        try:
            date_obj = datetime.fromisoformat(start_date.replace(" +0000", "+00:00"))
            date_str = date_obj.strftime("%Y-%m-%d")
        except:
            continue

        health_data["metrics_records"][metric_type].append({
            "date": date_str,
            "value": float(value),
            "unit": unit
        })

    # Parse workouts
    for workout in root.findall("Workout"):
        workout_type = workout.get("workoutActivityType", "")
        # Clean: "HKWorkoutActivityTypeCycling" → "Cycling"
        workout_type_clean = workout_type.replace("HKWorkoutActivityType", "")

        duration = float(workout.get("duration", 0))
        calories = float(workout.get("totalEnergyBurned", 0))
        start_date = workout.get("startDate", "")

        # Parse date and day of week
        try:
            date_obj = datetime.fromisoformat(start_date.replace(" +0000", "+00:00"))
            date_str = date_obj.strftime("%Y-%m-%d")
            day_of_week = date_obj.strftime("%A")  # "Friday", "Monday", etc.
        except:
            continue

        # Extract heart rate stats (if available)
        hr_stats = workout.find(".//WorkoutStatistics[@type='HKQuantityTypeIdentifierHeartRate']")
        avg_hr = int(hr_stats.get("average", 0)) if hr_stats is not None else None
        max_hr = int(hr_stats.get("maximum", 0)) if hr_stats is not None else None

        health_data["workouts"].append({
            "date": date_str,
            "startDate": start_date,
            "day_of_week": day_of_week,
            "type": workout_type_clean,
            "duration_minutes": duration,
            "calories": calories,
            "avg_heart_rate": avg_hr,
            "max_heart_rate": max_hr
        })

    # Build metrics summary (latest value per metric)
    for metric_type, records in health_data["metrics_records"].items():
        if records:
            latest = max(records, key=lambda r: r["date"])
            health_data["metrics_summary"][metric_type] = {
                "latest_value": latest["value"],
                "unit": latest["unit"],
                "count": len(records),
                "latest_date": latest["date"]
            }

    return health_data


def store_in_redis(health_data: dict, user_id: str = "wellness_user"):
    """Store parsed health data in Redis."""
    redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

    # 1. Store main health data as JSON STRING
    main_key = f"user:{user_id}:health_data"
    redis_client.set(main_key, json.dumps(health_data))
    redis_client.expire(main_key, 210 * 24 * 60 * 60)  # 7 months

    # 2. Build workout indexes (HASH + ZSET)
    from redis_workout_indexer import WorkoutIndexer
    indexer = WorkoutIndexer()
    indexer.index_workouts(user_id, health_data["workouts"])

    print(f"✅ Stored {len(health_data['workouts'])} workouts for {user_id}")


# Usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python import_health_data.py <path/to/export.xml>")
        sys.exit(1)

    xml_path = sys.argv[1]
    print(f"Parsing {xml_path}...")

    health_data = parse_apple_health_export(xml_path)
    print(f"Found {len(health_data['workouts'])} workouts")
    print(f"Found {len(health_data['metrics_records'])} metric types")

    store_in_redis(health_data)
    print("✅ Import complete!")
```

### Running the Import

```bash
# From backend directory
cd backend

# Install dependencies (if needed)
pip install redis lxml

# Run import
python import_health_data.py /path/to/export.xml

# Output:
# Parsing /path/to/export.xml...
# Found 154 workouts
# Found 12 metric types
# ✅ Stored 154 workouts for wellness_user
# ✅ Import complete!
```

### What Gets Stored in Redis

After import, Redis contains:

```
# Main health data (STRING)
user:wellness_user:health_data
→ JSON blob with all metrics and workouts

# Workout indexes (HASH)
user:wellness_user:workout:days
→ {"Friday": "24", "Monday": "18", "Wednesday": "12", ...}

# Workout index by date (SORTED SET)
user:wellness_user:workout:by_date
→ {workout_id: timestamp, ...}

# Individual workout details (HASH per workout)
user:wellness_user:workout:2024-10-22:Cycling:161934
→ {date: "2024-10-22", type: "Cycling", calories: "420", ...}
```

## Data Normalization and Cleaning

### Problem: Raw Apple Health Data is Messy

**Issues:**
1. **Inconsistent type names:** `HKWorkoutActivityTypeCycling` vs `Cycling`
2. **Multiple units:** Weight in `lb` or `kg`, distance in `mi` or `km`
3. **Missing fields:** Some workouts lack heart rate, distance, or calories
4. **Timezone complexity:** All dates in UTC, need local time context
5. **Duplicates:** Multiple apps can record the same workout

### Solution: Normalize During Import

**Type cleaning:**
```python
# Before: "HKWorkoutActivityTypeTraditionalStrengthTraining"
# After: "Traditional Strength Training"

def clean_workout_type(raw_type: str) -> str:
    # Remove prefix
    clean = raw_type.replace("HKWorkoutActivityType", "")

    # Add spaces before capitals
    import re
    clean = re.sub(r"([A-Z])", r" \1", clean).strip()

    return clean

# "TraditionalStrengthTraining" → "Traditional Strength Training"
```

**Unit conversion (standardize to pounds):**
```python
def convert_to_pounds(value: float, unit: str) -> float:
    if unit == "kg":
        return value * 2.20462
    elif unit in ["lb", "lbs"]:
        return value
    else:
        raise ValueError(f"Unknown weight unit: {unit}")

# 70 kg → 154.3 lbs
```

**Day of week enrichment:**
```python
from datetime import datetime

def add_day_of_week(workout: dict) -> dict:
    date_str = workout["startDate"]
    date_obj = datetime.fromisoformat(date_str.replace(" +0000", "+00:00"))
    workout["day_of_week"] = date_obj.strftime("%A")  # "Friday"
    return workout
```

### Workout Indexing Strategy

**Why separate indexes?**

Because different queries need different data structures:

1. **"How many workouts on Friday?"** → HASH (O(1) lookup)
2. **"Workouts in October"** → SORTED SET (O(log N) range query)
3. **"Details of last cycling workout"** → HASH per workout (O(1) lookup)

**Indexing workflow:**

```python
# For each workout, create 3 Redis keys:

# 1. Increment day count (HASH)
redis.hincrby("user:wellness_user:workout:days", "Friday", 1)

# 2. Add to date index (SORTED SET)
timestamp = workout_date.timestamp()
redis.zadd("user:wellness_user:workout:by_date", {workout_id: timestamp})

# 3. Store workout details (HASH)
redis.hset(f"user:wellness_user:workout:{workout_id}", mapping={
    "date": "2024-10-22",
    "type": "Cycling",
    "duration_minutes": "45.2",
    "calories": "420",
    "avg_heart_rate": "142",
    "max_heart_rate": "168",
    "day_of_week": "Friday"
})
```

**Result:** Fast queries (O(1) or O(log N)) instead of scanning entire dataset.

## Privacy Guarantees

### Where Data Lives

**Apple Health export flow:**
```
iPhone → export.xml (local file) → import script (local) → Redis (local Docker container)
```

**Data NEVER:**
- ❌ Uploaded to cloud
- ❌ Sent to external APIs
- ❌ Shared with third parties
- ❌ Leaves your machine

**Data ALWAYS:**
- ✅ Stays on local Docker containers
- ✅ Processed by local Ollama (no cloud LLM)
- ✅ Stored in local Redis (not cloud Redis)
- ✅ Can be deleted with `docker-compose down -v`

### Verifying Privacy (Network Test)

**Test:** Run demo with network disabled

```bash
# Disable network
sudo ifconfig en0 down

# Start demo
docker-compose up

# Chat with agent
# → Should work perfectly (because everything is local)

# Re-enable network
sudo ifconfig en0 up
```

If the demo works offline, you have **100% privacy guarantee**.

## Common Issues and Solutions

### Issue 1: "export.xml is too large (>100 MB)"

**Solution:** Redis can handle large files, but import might be slow.

```python
# Option 1: Import only recent data (last 2 years)
def filter_recent_data(health_data: dict, years: int = 2) -> dict:
    cutoff_date = datetime.now(UTC) - timedelta(days=365 * years)

    health_data["workouts"] = [
        w for w in health_data["workouts"]
        if datetime.fromisoformat(w["startDate"].replace(" +0000", "+00:00")) > cutoff_date
    ]

    return health_data

# Option 2: Import in batches
for batch in chunks(health_data["workouts"], size=100):
    indexer.index_workouts(user_id, batch)
```

### Issue 2: "Workout types are inconsistent"

**Problem:** Apple Health uses long names like `HKWorkoutActivityTypeTraditionalStrengthTraining`

**Solution:** Normalize during import

```python
WORKOUT_TYPE_MAP = {
    "HKWorkoutActivityTypeCycling": "Cycling",
    "HKWorkoutActivityTypeRunning": "Running",
    "HKWorkoutActivityTypeTraditionalStrengthTraining": "Strength Training",
    "HKWorkoutActivityTypeYoga": "Yoga",
    # ...add more as needed
}

def clean_workout_type(raw_type: str) -> str:
    return WORKOUT_TYPE_MAP.get(raw_type, raw_type.replace("HKWorkoutActivityType", ""))
```

### Issue 3: "Missing heart rate data for some workouts"

**Problem:** Older workouts or non-Apple Watch workouts lack heart rate stats

**Solution:** Handle gracefully

```python
workout = {
    "avg_heart_rate": workout.get("avg_heart_rate") or None,  # None if missing
    "max_heart_rate": workout.get("max_heart_rate") or None
}

# In agent responses:
if workout["avg_heart_rate"]:
    response += f" (avg HR: {workout['avg_heart_rate']} bpm)"
else:
    # Don't mention heart rate if unavailable
    pass
```

## Using Sample Data (No iPhone)

If you don't have an iPhone, use sample data:

**Sample export (minimal):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
  <ExportDate value="2024-10-25 14:30:00 +0000"/>

  <!-- Sample weight records -->
  <Record type="HKQuantityTypeIdentifierBodyMass"
          sourceName="Health" unit="lb"
          startDate="2024-10-22 07:15:00 +0000"
          value="136.8"/>
  <Record type="HKQuantityTypeIdentifierBodyMass"
          sourceName="Health" unit="lb"
          startDate="2024-10-21 07:15:00 +0000"
          value="137.2"/>

  <!-- Sample workouts -->
  <Workout workoutActivityType="HKWorkoutActivityTypeCycling"
           duration="45" durationUnit="min"
           totalEnergyBurned="420" totalEnergyBurnedUnit="kcal"
           startDate="2024-10-17 12:00:00 +0000"
           endDate="2024-10-17 12:45:00 +0000">
    <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate"
                       average="142" minimum="98" maximum="168"/>
  </Workout>

  <Workout workoutActivityType="HKWorkoutActivityTypeRunning"
           duration="30" durationUnit="min"
           totalEnergyBurned="280" totalEnergyBurnedUnit="kcal"
           startDate="2024-10-15 06:30:00 +0000"
           endDate="2024-10-15 07:00:00 +0000">
    <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate"
                       average="155" minimum="120" maximum="175"/>
  </Workout>
</HealthData>
```

Save as `sample_export.xml` and import normally.

## Key Takeaways

1. **Apple Health = realistic time-series data** - Real patterns, variance, and complexity
2. **Export is simple** - Health app → Export → Save as XML
3. **Import = parse XML + normalize + index** - Clean types, convert units, build Redis indexes
4. **Indexes enable fast queries** - HASH for aggregations, ZSET for date ranges, HASH per workout
5. **Privacy guaranteed** - Data stays local (iPhone → local Redis, no cloud)
6. **Sample data works too** - Don't need iPhone to try the demo

## Next Steps

- **08_EXTENDING.md** - Add new data sources (Fitbit, Garmin), new tools, and deployment strategies
- **backend/TEST_PLAN.md** - Test health data import and querying
