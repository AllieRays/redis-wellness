# Health Data Pipeline: Apple Health → Redis

Complete flow from Apple Health XML export to Redis-cached structured data.

---

## Pipeline Overview

```
Apple Health Export (XML)
    ↓
1. XML Parsing & Security Validation
    ↓
2. Domain Model Creation (Python objects)
    ↓
3. JSON Serialization
    ↓
4. Redis Storage with TTL
    ↓
AI Agent Tools (instant retrieval)
```

---

## Stage 1: Apple Health Export → XML File

**Input:** `export.xml` from Apple Health app
**Location:** `apple_health_export/export.xml`

**Format:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData>
<HealthData locale="en_US">
  <Me HKCharacteristicTypeIdentifierDateOfBirth="1990-01-01"
      HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexMale"/>

  <Record type="HKQuantityTypeIdentifierBodyMass"
          sourceName="Apple Health"
          value="75.5"
          unit="kg"
          startDate="2024-01-15 08:00:00 -0800"
          endDate="2024-01-15 08:00:00 -0800"/>

  <Record type="HKQuantityTypeIdentifierBodyMassIndex"
          value="23.6"
          unit="count"
          startDate="2024-01-15 08:00:00 -0800"
          endDate="2024-01-15 08:00:00 -0800"/>

  <Workout workoutActivityType="HKWorkoutActivityTypeRunning"
           duration="30" durationUnit="min"
           startDate="2024-01-15 06:00:00 -0800"
           endDate="2024-01-15 06:30:00 -0800">
    <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned"
                       sum="250" unit="kcal"/>
  </Workout>
</HealthData>
```

**Typical size:** 255K+ records, 48 metric types, 50MB+ file

---

## Stage 2: XML Parsing → Domain Models

**Module:** `backend/src/parsers/apple_health_parser.py`
**Trigger:** AI agent calls `parse_health_file()` tool or API upload endpoint

### Security & Validation

```python
# Security checks before parsing
1. File path validation (prevent directory traversal)
2. XML structure validation (check for Apple Health markers)
3. Element count limits (prevent XML bomb attacks)
4. Attribute count limits (prevent attribute bombing)
5. No external entity processing (prevent XXE attacks)
```

### Parsing Process

```python
from backend.src.parsers.apple_health_parser import AppleHealthParser

parser = AppleHealthParser(allowed_directories=['/path/to/exports'])

# Iterative parsing (memory-efficient for large files)
health_data = parser.parse_file('apple_health_export/export.xml')

# Returns: HealthDataCollection object
```

**Parsed Structure:**
```python
HealthDataCollection(
    export_date=datetime(2024, 1, 15, tzinfo=UTC),
    record_count=255432,
    user_profile=UserProfile(
        date_of_birth=date(1990, 1, 1),
        biological_sex="Male",
        blood_type="O+"
    ),
    records=[
        HealthRecord(
            record_type=HealthMetricType.BODY_MASS,
            value="75.5",
            unit="kg",
            start_date=datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC),  # Normalized to UTC
            end_date=datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC),
            source_name="Apple Health",
            device="iPhone14,7"
        ),
        HealthRecord(
            record_type=HealthMetricType.BODY_MASS_INDEX,
            value="23.6",
            unit="count",
            start_date=datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC),
            end_date=datetime(2024, 1, 15, 16, 0, 0, tzinfo=UTC)
        ),
        # ... 255,430 more records
    ],
    workouts=[
        WorkoutSummary(
            workout_activity_type="HKWorkoutActivityTypeRunning",
            duration=30.0,
            duration_unit="min",
            total_energy_burned=250.0,
            start_date=datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC),
            end_date=datetime(2024, 1, 15, 14, 30, 0, tzinfo=UTC)
        )
    ]
)
```

**Key Features:**
- **Memory-efficient:** Iterative parsing with element cleanup
- **UTC normalization:** All timestamps converted to UTC
- **Privacy protection:** Anonymization methods available
- **Type safety:** Pydantic validation for all fields

---

## Stage 3: Domain Models → JSON

**Module:** `backend/src/tools/health_parser_tool.py`
**Function:** `parse_health_file()` → creates AI-friendly summary

### JSON Structure

**File:** `parsed_health_data.json` (or Redis storage)

```json
{
  "record_count": 255432,
  "export_date": "2024-01-15T00:00:00+00:00",
  "anonymized": true,
  "date_range": {
    "earliest": "2019-09-15T12:00:00+00:00",
    "latest": "2024-01-15T23:59:00+00:00",
    "span_days": 1583
  },
  "data_categories": [
    "BodyMass",
    "BodyMassIndex",
    "Height",
    "StepCount",
    "DistanceWalkingRunning",
    "ActiveEnergyBurned",
    "HeartRate",
    "DietaryWater",
    "SleepAnalysis"
  ],
  "metrics_summary": {
    "BodyMass": {
      "count": 450,
      "latest_value": "75.5 kg",
      "latest_date": "2024-01-15T16:00:00+00:00"
    },
    "BodyMassIndex": {
      "count": 450,
      "latest_value": "23.6 count",
      "latest_date": "2024-01-15T16:00:00+00:00"
    },
    "StepCount": {
      "count": 1583,
      "latest_value": "8452 count",
      "latest_date": "2024-01-15T23:59:00+00:00"
    },
    "HeartRate": {
      "count": 125000,
      "latest_value": "72 count/min",
      "latest_date": "2024-01-15T23:55:00+00:00"
    }
  },
  "workouts": [
    {
      "type": "Running",
      "date": "2024-01-15T14:00:00+00:00",
      "duration_minutes": 30,
      "calories": 250,
      "source": "Apple Watch"
    }
  ],
  "workout_count": 342,
  "conversation_context": "Recent health data (10 records): BodyMass: 75.5 kg | Date: 2024-01-15 || BMI: 23.6 | Date: 2024-01-15 || ..."
}
```

---

## Stage 4: JSON → Redis Storage

**Module:** `backend/src/services/redis_health_tool.py`
**Redis Keys:** Structured for instant O(1) lookups

### Redis Key Structure

```
# Main health data cache
health:user:{user_id}:data
→ Full parsed JSON (TTL: 7 months)

# Metric-specific caches (for fast queries)
health:user:{user_id}:metric:{metric_type}:{date}
→ Individual metric values (TTL: 7 months)

# Summary cache
health:user:{user_id}:summary
→ Quick stats (record count, date range, categories)

# Workout cache
health:user:{user_id}:workouts
→ Workout list for activity queries
```

### Redis Storage Example

```python
import redis
import json

# Store main health data
redis_client.setex(
    name="health:user:demo_user:data",
    time=18144000,  # 7 months in seconds
    value=json.dumps(parsed_health_data)
)

# Store metric summary for fast access
redis_client.setex(
    name="health:user:demo_user:metric:BodyMass:2024-01-15",
    time=18144000,
    value=json.dumps({
        "value": "75.5",
        "unit": "kg",
        "timestamp": "2024-01-15T16:00:00+00:00"
    })
)
```

### Redis Data Structure Visualization

```
Redis Server
├── health:user:demo_user:data (HASH)
│   ├── record_count: "255432"
│   ├── export_date: "2024-01-15T00:00:00+00:00"
│   └── full_json: "{...}" (compressed)
│
├── health:user:demo_user:metric:BodyMass:2024-01-15 (STRING)
│   └── "{'value': '75.5', 'unit': 'kg'}"
│
├── health:user:demo_user:metric:BodyMassIndex:2024-01-15 (STRING)
│   └── "{'value': '23.6', 'unit': 'count'}"
│
└── health:user:demo_user:workouts (LIST)
    ├── "{'type': 'Running', 'duration': 30, 'date': '2024-01-15'}"
    ├── "{'type': 'Cycling', 'duration': 45, 'date': '2024-01-14'}"
    └── ... (342 workouts)
```

---

## Stage 5: AI Agent Retrieval

**Module:** `backend/src/tools/health_insights_tool.py`
**Access:** AI agents query Redis for instant responses

### Query Examples

**1. Get BMI:**
```python
# Agent calls: query_health_metrics(metric_type="BodyMassIndex", days=7)

# Backend retrieves from Redis
redis_client.get("health:user:demo_user:metric:BodyMassIndex:2024-01-15")
# Returns instantly: {"value": "23.6", "unit": "count"}
```

**2. Generate Insights:**
```python
# Agent calls: generate_health_insights(focus_area="weight")

# Backend retrieves from Redis
health_data = json.loads(redis_client.get("health:user:demo_user:data"))

# Processes and returns:
{
    "bmi_analysis": {
        "latest_value": "23.6 count",
        "health_category": "Normal weight",
        "insight": "Your BMI is within the healthy range"
    }
}
```

---

## Complete Pipeline Code Flow

### Step 1: Upload & Parse

```python
# API endpoint: POST /api/health/upload
from backend.src.tools.health_parser_tool import parse_health_file

result = parse_health_file(
    file_path="apple_health_export/export.xml",
    anonymize=True
)

# Returns ToolResult with JSON summary
parsed_data = result.data
```

### Step 2: Store in Redis

```python
from backend.src.services.redis_health_tool import RedisHealthTool

redis_tool = RedisHealthTool()

# Cache parsed data
redis_tool.cache_health_data(
    user_id="demo_user",
    health_data=parsed_data,
    ttl_days=210  # 7 months
)
```

### Step 3: AI Agent Queries

```python
# Agent conversation:
# User: "What's my current BMI?"

# Agent calls tool:
from backend.src.tools.health_insights_tool import generate_health_insights

insights = generate_health_insights(
    user_id="demo_user",
    focus_area="weight"
)

# Agent receives:
# "Your latest BMI is 23.6, which is within the healthy range (Normal weight).
#  This is based on 450 BMI measurements tracked since 2019."
```

---

## Performance Characteristics

| Stage | Time | Memory | Notes |
|-------|------|--------|-------|
| XML Parse | ~30-60s | ~500MB peak | Iterative parsing, 255K records |
| Model Creation | ~5s | ~200MB | Pydantic validation |
| JSON Serialization | ~2s | ~100MB | Dict conversion |
| Redis Storage | <100ms | ~50MB compressed | O(1) write |
| Redis Retrieval | <5ms | ~1KB | O(1) read per query |

**Key Advantage:** Parse once (1 minute), query forever (<5ms)

---

## Redis Advantages Over File-Based Storage

### With Redis (Current System):
```
User: "What's my BMI?"
→ Agent calls tool (2ms)
→ Redis lookup: O(1) - 3ms
→ Response: "23.6" - TOTAL: 5ms ⚡
```

### Without Redis (Stateless):
```
User: "What's my BMI?"
→ Agent calls tool (2ms)
→ Parse entire XML file: 45 seconds
→ Search 255K records: 2 seconds
→ Response: "23.6" - TOTAL: 47 seconds 🐌
```

**Benefits:**
- ⚡ **1000x faster queries** (5ms vs 47s)
- 🧠 **Persistent memory** across sessions
- 🔄 **Automatic TTL** (cleanup after 7 months)
- 📊 **Structured caching** for common queries
- 💾 **Memory efficient** (compressed JSON)

---

## File Locations

```
redis-wellness/
├── apple_health_export/
│   └── export.xml                           # Stage 1: Raw XML
│
├── backend/src/
│   ├── models/
│   │   └── health.py                        # Stage 2: Domain models
│   │
│   ├── parsers/
│   │   └── apple_health_parser.py           # Stage 2: XML → Models
│   │
│   ├── tools/
│   │   ├── health_parser_tool.py            # Stage 3: AI tool wrapper
│   │   └── health_insights_tool.py          # Stage 5: AI insights
│   │
│   └── services/
│       └── redis_health_tool.py             # Stage 4: Redis storage
│
└── parsed_health_data.json (optional)       # Stage 3: JSON output
```

---

## Error Handling & Privacy

### Security Protections
- ✅ XML bomb prevention (element/attribute limits)
- ✅ XXE attack prevention (no external entities)
- ✅ Directory traversal protection (path validation)
- ✅ Memory limits (iterative parsing with cleanup)

### Privacy Features
- 🔒 Anonymization available (hash device/source names)
- 🔒 No raw metadata stored (only essential fields)
- 🔒 UTC normalization (removes timezone info)
- 🔒 Error sanitization (no sensitive data in logs)
- 🔒 Redis TTL (automatic cleanup after 7 months)

---

## Testing the Pipeline

### Manual Test

```bash
# 1. Place your Apple Health export
cp ~/Downloads/export.xml apple_health_export/

# 2. Start services
docker-compose up

# 3. Parse and cache
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@apple_health_export/export.xml"

# 4. Query via AI agent (frontend)
# Visit http://localhost:3000
# Ask: "What's my latest BMI?"
```

### Programmatic Test

```python
# Full pipeline test
from backend.src.tools.health_parser_tool import parse_health_file
from backend.src.services.redis_health_tool import redis_manager

# Step 1: Parse
result = parse_health_file("apple_health_export/export.xml", anonymize=True)
print(f"Parsed {result.data['record_count']} records")

# Step 2: Verify Redis storage
with redis_manager.get_connection() as redis_client:
    cached = redis_client.get("health:user:demo_user:data")
    print(f"Redis cache size: {len(cached)} bytes")

# Step 3: Query
from backend.src.tools.health_insights_tool import generate_health_insights
insights = generate_health_insights("demo_user", focus_area="overall")
print(f"Generated insights: {insights.data['summary']}")
```

---

## Troubleshooting

### Issue: "File not found"
```
✓ Check: apple_health_export/export.xml exists
✓ Check: File path in allowed_directories
✓ Check: File permissions (readable)
```

### Issue: "Invalid XML format"
```
✓ Verify: File is Apple Health export (not edited)
✓ Check: File contains <HealthData> root element
✓ Try: Export fresh XML from Apple Health app
```

### Issue: "Redis connection failed"
```
✓ Check: Docker containers running (docker-compose ps)
✓ Check: Redis port 6379 accessible
✓ Check: Redis service started (redis-cli ping)
```

### Issue: "Parsing too slow"
```
✓ Expected: 30-60s for 255K records (normal)
✓ Optimize: Increase MAX_ELEMENT_COUNT if hitting limits
✓ Monitor: Memory usage (should stay <500MB)
```

---

## Summary

```
Apple Health Export (XML, 50MB)
    ↓ [30-60s] XML parsing + validation
HealthDataCollection (Python objects, 200MB)
    ↓ [2s] JSON serialization + summarization
parsed_health_data.json (Structured JSON, 10MB)
    ↓ [100ms] Redis storage with compression
Redis Cache (Compressed, 5MB, TTL: 7 months)
    ↓ [5ms] AI agent queries
Instant Health Insights ⚡
```

**Result:** Parse once, query forever with sub-10ms latency.
