# How to Import Apple Health Data

## Overview

This guide walks you through importing Apple Health data from your iPhone's `export.xml` file into Redis. The process involves exporting data from your iPhone, placing it in the correct directory, running the `make import` command, and verifying the data is properly indexed in Redis.

### Steps

- **Step 1: [Exporting from iPhone](#1-exporting-from-iphone)** - How to export your Apple Health data as XML
- **Step 2: [Preparing the Data](#2-preparing-the-data)** - Where to place export.xml in the project
- **Step 3: [Running the Import](#3-running-the-import)** - Using `make import` to load data into Redis
- **Step 4: [Verifying the Import](#4-verifying-the-import)** - Confirming data is properly indexed
- **Step 5: [What Gets Stored](#5-what-gets-stored-in-redis)** - Understanding Redis data structure
- **Step 6: [Related Documentation](#6-related-documentation)** - Links to related docs

---

## 1. Exporting from iPhone


**Step 1: Open Health App**

1. Open **Health** app on iPhone
2. Tap your **profile picture** (top-right corner)

**Step 2: Export All Health Data**

1. Scroll down to **"Export All Health Data"**
2. Tap it - you'll see a warning:
   ```
   "This will export all your health and fitness data as an XML file.
   The export may take several minutes."
   ```
3. Tap **Export** and wait (2-10 minutes depending on data size)

**Step 3: Save Export**

1. iOS will show **Share Sheet**
2. Choose **Save to Files** (or AirDrop to your Mac)
3. Save as `export.zip` in a location you remember

**Step 4: Transfer to Your Mac**

Use AirDrop, Files app, or iCloud Drive to transfer the export to your development machine.

---

## 2. Preparing the Data

**Step 1: Unzip the Export**

```bash
# Navigate to where you saved export.zip
cd ~/Downloads  # or wherever you saved it

# Unzip export
unzip export.zip

# You'll see:
# export.xml              (main health data - 50-200 MB)
# workout-routes/         (GPS tracks - optional)
# export_cda.xml          (clinical records - optional)
```

**Step 2: Move to Project Directory**

The import script expects the file at `apple_health_export/export.xml`:

```bash
# From the project root
cd /path/to/redis-wellness

# Create directory if it doesn't exist
mkdir -p apple_health_export

# Move the export file
mv ~/Downloads/export.xml apple_health_export/
```

**Your project structure should now look like:**

```
redis-wellness/
├── apple_health_export/
│   └── export.xml           ← Your health data
├── backend/
├── frontend/
├── docker-compose.yml
└── Makefile
```

---

## 3. Running the Import

### Using Make (Recommended)

The simplest way to import data is using the Makefile:

```bash
# Make sure Docker containers are running
make up

# Import data into Docker Redis
make import
```

**What happens during import:**

1. Parses `apple_health_export/export.xml` (2-10 minutes for large files)
2. Normalizes workout types (removes `HKWorkoutActivityType` prefix)
3. Enriches data with computed fields (day_of_week, type_cleaned, etc.)
4. Stores main health data in Redis as JSON
5. Creates Redis indexes for fast queries:
   - Workout indexes (HASH + ZSET)
   - Sleep indexes (HASH)
   - Metric indexes (STRING)

**Expected output:**

```
📱 Importing Apple Health data into Docker Redis...
🐳 Running import inside backend container...

📱 Parsing XML: export.xml (152.3 MB)
⏳ This may take several minutes for large files...
✅ Parsed 45,287 health records

🔄 Converting to storage format...
✅ Conversion complete

💾 Storing in Redis...
✅ Stored: user:wellness_user:health_data
✅ Created 12 metric indices

📊 Indexing 154 workouts...
   (Creating Redis hashes for O(1) lookups + deduplication)
✅ Created 154 workout hashes (462 Redis keys)
   TTL: 210 days

🛌 Indexing 1,234 sleep records...
   (Creating Redis hashes for O(1) lookups)
✅ Created 182 sleep summaries (182 Redis keys)
   TTL: 210 days

✅ Import complete! Data is now in Docker Redis.
💡 Verify: make verify
```

### Alternative Import Methods

**Import from a specific XML file:**

```bash
make import-xml
# Will prompt: "Enter path to export.xml (inside container):"
# Enter: /apple_health_export/your_file.xml
```

**Import in local dev mode (not Docker):**

```bash
make import-local
# Imports to localhost:6379 instead of Docker Redis
```

### Troubleshooting Import Issues

**Issue: "File not found: /apple_health_export/export.xml"**

Solution: Make sure the file is in the correct location and Docker can access it:

```bash
# Check file exists
ls -lh apple_health_export/export.xml

# Check docker-compose.yml has volume mount
grep apple_health_export docker-compose.yml
# Should see: - ./apple_health_export:/apple_health_export:ro
```

**Issue: "Cannot connect to Redis"**

Solution: Make sure Redis is running:

```bash
make redis-start
# Or check all services
docker compose ps
```

**Issue: "Import is very slow (>10 minutes)"**

Solution: Large XML files (>200 MB) take time. Consider:

```bash
# Monitor progress in logs
docker compose logs backend -f

# Or use pre-parsed JSON for faster imports (if available)
make import-local  # If you have parsed_health_data.json
```

---

## 4. Verifying the Import

### Quick Verification

```bash
# Verify data is loaded and indexed
make verify
```

**Expected output:**

```
🔍 Verifying Redis data (Docker)...

✅ Main health data found
   Key: user:wellness_user:health_data
   Size: 15.2 MB

✅ Workout indexes found
   Total workouts: 154
   Date range: 2023-01-15 to 2024-10-25
   Types: Cycling, Running, Yoga, Strength Training

✅ Sleep indexes found
   Total nights: 182
   Date range: 2023-06-01 to 2024-10-25

✅ Metric indexes found
   Types: BodyMass, HeartRate, StepCount, ActiveEnergyBurned (12 total)

✅ All data verified!
```

### Detailed Statistics

```bash
# Show detailed health data statistics
make stats
```

**Example output:**

```
📊 Showing health data statistics (Docker)...

=== Health Metrics Summary ===
BodyMass: 245 records (latest: 136.8 lb on 2024-10-22)
HeartRate: 12,543 records (latest: 68 bpm on 2024-10-22)
StepCount: 687 records (latest: 8,432 steps on 2024-10-21)
ActiveEnergyBurned: 687 records (latest: 450 kcal on 2024-10-21)

=== Workout Summary ===
Total workouts: 154
Most common type: Cycling (42 workouts)
Most active day: Friday (24 workouts)
Average duration: 38.5 minutes
Total calories burned: 58,240 kcal

=== Sleep Summary ===
Total nights tracked: 182
Average sleep duration: 7.2 hours
Sleep efficiency: 92%
```

### Manual Verification with Redis CLI

```bash
# Show Redis keys
make redis-keys
```

**Expected keys:**

```
user:wellness_user:health_data                    # Main JSON blob
user:wellness_user:workout:days                   # Day-of-week counts
user:wellness_user:workout:by_date                # Date-sorted index
user:wellness_user:workout:2024-10-17:Cycling:*   # Individual workouts
user:wellness_user:sleep:2024-10-17               # Sleep summaries
user:wellness_user:metric:BodyMass                # Metric indexes

Total keys: 462
```

---

## 5. What Gets Stored in Redis


After import, Redis contains multiple data structures optimized for different query patterns:

### Main Health Data (STRING)

```redis
KEY: user:wellness_user:health_data
TYPE: String (JSON blob)
TTL: 210 days (7 months)
SIZE: ~15 MB (typical)
```

Contains complete parsed health data:

```json
{
  "record_count": 45287,
  "export_date": "2024-10-25T14:30:00+00:00",
  "metrics_records": {
    "BodyMass": [{"date": "2024-10-22", "value": 136.8, "unit": "lb"}],
    "HeartRate": [{"date": "2024-10-22", "value": 68, "unit": "count/min"}]
  },
  "metrics_summary": {
    "BodyMass": {"count": 245, "latest_value": 136.8, "unit": "lb"}
  },
  "workouts": [
    {
      "date": "2024-10-17",
      "day_of_week": "Thursday",
      "type": "HKWorkoutActivityTypeCycling",
      "type_cleaned": "Cycling",
      "duration_minutes": 45.2,
      "calories": 420,
      "startDate": "2024-10-17T12:00:00+00:00"
    }
  ]
}
```

### Workout Indexes (HASH + ZSET)

Optimized for fast workout queries:

**Day-of-week counts (HASH):**

```redis
KEY: user:wellness_user:workout:days
TYPE: Hash

HGETALL user:wellness_user:workout:days
→ {"Friday": "24", "Monday": "18", "Wednesday": "12", "Thursday": "20", ...}
```

**Date-sorted index (SORTED SET):**

```redis
KEY: user:wellness_user:workout:by_date
TYPE: Sorted Set

ZRANGE user:wellness_user:workout:by_date 0 -1
→ [workout_id_1, workout_id_2, workout_id_3, ...] (sorted by timestamp)
```

**Individual workout details (HASH per workout):**

```redis
KEY: user:wellness_user:workout:2024-10-17:Cycling:161934
TYPE: Hash

HGETALL user:wellness_user:workout:2024-10-17:Cycling:161934
→ {
    "date": "2024-10-17",
    "type": "Cycling",
    "type_cleaned": "Cycling",
    "duration_minutes": "45.2",
    "calories": "420",
    "day_of_week": "Thursday"
  }
```

### Sleep Indexes (HASH)

Daily sleep summaries for fast sleep analysis:

```redis
KEY: user:wellness_user:sleep:2024-10-17
TYPE: Hash

HGETALL user:wellness_user:sleep:2024-10-17
→ {
    "date": "2024-10-17",
    "total_hours": "7.2",
    "in_bed_hours": "7.8",
    "sleep_efficiency": "0.92",
    "asleep_periods": "3",
    "awake_periods": "2"
  }
```

### Metric Indexes (STRING)

Quick access to metric summaries:

```redis
KEY: user:wellness_user:metric:BodyMass
TYPE: String (JSON)
TTL: 210 days

GET user:wellness_user:metric:BodyMass
→ {"count": 245, "latest_value": 136.8, "unit": "lb", "latest_date": "2024-10-22"}
```

### Index Benefits

| Query Type | Without Indexes | With Indexes |
|------------|-----------------|---------------|
| "Workouts on Friday?" | O(n) scan of JSON | O(1) HGET |
| "Workouts in October?" | O(n) filter JSON | O(log n) ZRANGE |
| "Last cycling workout?" | O(n) reverse scan | O(1) HGET |
| "Sleep on specific date?" | O(n) scan JSON | O(1) HGET |

**Performance improvement:** 1000x faster for typical queries.

---

## 6. Related Documentation

- **[02_QUICKSTART.md](02_QUICKSTART.md)** - Get started with the demo
- **[10_MEMORY_ARCHITECTURE.md](10_MEMORY_ARCHITECTURE.md)** - Understanding the memory system
- **[11_REDIS_PATTERNS.md](11_REDIS_PATTERNS.md)** - Redis data structure patterns and best practices
- **[13_TOOLS_SERVICES_UTILS_REFERENCE.md](13_TOOLS_SERVICES_UTILS_REFERENCE.md)** - Data retrieval strategies and tools

---

**Key takeaway:** Import Apple Health data into Redis using `make import` from `apple_health_export/export.xml`, creating optimized indexes for fast health data queries.
