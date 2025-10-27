# Apple Health Data Reload Instructions

## Overview

This document provides instructions for reloading Apple Health data into Redis when the database needs to be refreshed with updated health records.

## File Locations

- **Raw Apple Health Export**: `/apple_health_export/`
  - Contains the original XML export from Apple Health
  - File: `export.xml`

- **Parsed Health Data**: `parsed_health_data.json`
  - Preprocessed JSON format of health data
  - Located in project root

- **Import Script**: `import_health.py`
  - Python script to load parsed data into Redis
  - Located in project root

## Prerequisites

1. **Services Running**: Ensure Docker services are running
   ```bash
   docker-compose ps
   # Should show backend, frontend, and redis containers running
   ```

2. **Redis Available**: Verify Redis is accessible
   ```bash
   curl http://localhost:8000/health
   # Should return healthy status
   ```

## Data Reload Process

### Option 1: Using Parsed Data (Fastest)

If you already have `parsed_health_data.json`, use the import script:

```bash
# From project root
python3 import_health.py
```

This will:
- Read `parsed_health_data.json`
- Load data into Redis at key `health:user:wellness_user:data`
- Preserve all metrics, workouts, and records

### Option 2: Re-parse from Raw Export

If you need to re-parse the Apple Health XML:

```bash
# Parse the raw export
python3 backend/src/apple_health/parser.py /apple_health_export/export.xml parsed_health_data.json

# Then load into Redis
python3 import_health.py
```

### Option 3: Using the API Endpoint

Upload via the HTTP API:

```bash
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@/apple_health_export/export.xml"
```

**Note**: This requires the backend to be running and may take longer for large exports.

## Verification

After reloading, verify the data:

```bash
# Check total records
docker exec redis-wellness redis-cli GET "health:user:wellness_user:data" | \
  python3 -c "import sys, json; data=json.loads(sys.stdin.read()); \
  print(f'Metrics: {len(data.get(\"metrics_records\", {}))} types'); \
  print(f'Workouts: {len(data.get(\"workouts\", []))} total')"
```

Expected output:
```
Metrics: 10+ types (StepCount, BodyMass, HeartRate, etc.)
Workouts: 100+ total
```

### Verify Specific Time Period

Check September 2025 workouts:

```bash
docker exec redis-wellness redis-cli GET "health:user:wellness_user:data" | \
  python3 -c "import sys, json; data=json.loads(sys.stdin.read()); \
  workouts=data.get('workouts',[]); \
  sept=[w for w in workouts if '2025-09' in w.get('startDate','')]; \
  print(f'September 2025: {len(sept)} workouts')"
```

### Test via Chat API

```bash
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "How many workouts did I do in September 2025?", "session_id": "test"}'
```

## Troubleshooting

### Issue: "No health data found"

**Solution**: Run the import script to reload data
```bash
python3 import_health.py
```

### Issue: "Old data still showing"

**Solution**: Clear Redis and reload
```bash
# Clear the health data key
docker exec redis-wellness redis-cli DEL "health:user:wellness_user:data"

# Reload
python3 import_health.py
```

### Issue: "Import script not found"

**Solution**: Ensure you're in the project root directory
```bash
cd /Users/allierays/Sites/redis-wellness
ls -la import_health.py  # Should exist
```

### Issue: "parsed_health_data.json missing"

**Solution**: Re-parse from raw export
```bash
python3 backend/src/apple_health/parser.py /apple_health_export/export.xml parsed_health_data.json
```

## Data Format

The `parsed_health_data.json` file structure:

```json
{
  "metrics_records": {
    "StepCount": [...],
    "BodyMass": [...],
    "HeartRate": [...],
    "ActiveEnergyBurned": [...]
  },
  "workouts": [
    {
      "type": "TraditionalStrengthTraining",
      "startDate": "2025-10-17 16:59:18",
      "endDate": "2025-10-17 17:26:18",
      "duration": 27.0,
      "calories": 116.0
    }
  ]
}
```

## Notes for Claude

When assisting with data reload:

1. **Always check current data first**: Use verification commands to see what's in Redis
2. **Use import script by default**: It's faster than re-parsing XML
3. **Verify after reload**: Always confirm the data loaded correctly
4. **Check date ranges**: Ensure new data covers the expected time periods
5. **Watch for parser issues**: If workouts/metrics are missing, the parser may need debugging

## Common Workflow

```bash
# 1. Check what's currently in Redis
docker exec redis-wellness redis-cli GET "health:user:wellness_user:data" | \
  python3 -c "import sys, json; data=json.loads(sys.stdin.read()); \
  print('Current data loaded')"

# 2. Reload from parsed file
python3 import_health.py

# 3. Verify the reload
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "How many total workouts do I have?", "session_id": "verify"}'
```

## Related Documentation

- **Parser Details**: `docs/HEALTH_DATA_PIPELINE.md`
- **Redis Structure**: `docs/RAG_IMPLEMENTATION.md`
- **API Endpoints**: `http://localhost:8000/docs`
