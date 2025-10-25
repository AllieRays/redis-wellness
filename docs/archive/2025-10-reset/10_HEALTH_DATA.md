# Apple Health Data Guide

How to export your Apple Health data and load it into Redis Wellness AI.

---

## Overview

Redis Wellness AI uses your Apple Health data to provide personalized health insights. Your data stays 100% local - it never leaves your machine.

**Supported Data**:
- Workouts (Running, Cycling, Swimming, etc.)
- Heart Rate
- Body Mass (Weight)
- Body Mass Index (BMI)
- Steps
- Active Energy (Calories)
- And more...

---

## Step 1: Export from Apple Health

### On iPhone

1. **Open Health App**
   - Tap on your profile icon (top right)

2. **Export All Health Data**
   - Scroll down and tap **"Export All Health Data"**
   - Tap **"Export"** to confirm
   - Wait for processing (may take 1-5 minutes depending on data size)

3. **Save the Export**
   - A share sheet will appear with `export.zip`
   - Choose **"Save to Files"** or **"AirDrop"** to your Mac
   - Or email it to yourself

4. **Extract the ZIP**
   - Unzip the file on your Mac
   - Look for `export.xml` (the main data file)
   - Size typically: 5-50 MB depending on years of data

### What's in the Export?

```
export.zip
├── export.xml          ← Main health data (this is what we need!)
├── export_cda.xml      ← Clinical data (optional)
└── workout-routes/     ← GPS data (not used)
```

---

## Step 2: Verify the Export File

```bash
# Check file size
ls -lh /path/to/export.xml

# Quick peek at contents (should show XML)
head -20 /path/to/export.xml
```

**Expected output**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE HealthData>
<HealthData locale="en_US">
  <ExportDate value="2024-10-22 12:00:00 -0700"/>
  <Me HKCharacteristicTypeIdentifierDateOfBirth="1990-01-01".../>
  <Record type="HKQuantityTypeIdentifierBodyMass" value="70" unit="kg".../>
  ...
</HealthData>
```

---

## Step 3: Load Data into Redis Wellness

### Option 1: Using the API (Recommended)

```bash
# Make sure services are running
docker-compose up -d

# Upload health data
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@/path/to/export.xml"
```

**Expected response**:
```json
{
  "status": "success",
  "message": "Health data imported successfully",
  "metrics_processed": 12543,
  "workouts_processed": 234,
  "date_range": {
    "earliest": "2020-01-01",
    "latest": "2024-10-22"
  }
}
```

### Option 2: Using Python Script

```bash
cd backend

# Run import script
uv run python scripts/import_health.py /path/to/export.xml
```

---

## Step 4: Verify Data Loaded

### Check via RedisInsight

1. Go to http://localhost:8001
2. Look for keys like:
   - `health:default_user`
   - `workout:*`
   - `memory:*`

### Check via API

```bash
# Get health stats
curl http://localhost:8000/api/health/stats

# Example query
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "What workouts did I do last week?"}'
```

---

## Privacy & Security

### Your Data Stays Local

- ✅ **Processed locally**: XML parsing happens on your machine
- ✅ **Stored locally**: Redis runs in Docker container on localhost
- ✅ **LLM is local**: Ollama runs on your machine
- ❌ **Never sent to cloud**: No external API calls
- ❌ **Not committed to git**: `.gitignore` excludes all health files

### What Data Is Used?

The system extracts:
- **Metrics**: Weight, BMI, heart rate, steps, calories
- **Workouts**: Type, duration, distance, date
- **Statistics**: Aggregates like averages, trends, patterns

**Not extracted**:
- Personal identifiers (name, birthday)
- Medical records (unless you explicitly include them)
- GPS routes (we don't process workout-routes/)

---

## Data Management

### View Loaded Data

```bash
# Check what's in Redis
docker exec -it redis-wellness-redis-1 redis-cli

# In Redis CLI:
KEYS health:*
KEYS workout:*
```

### Clear Health Data

```bash
# Clear all health data from Redis
docker exec -it redis-wellness-redis-1 redis-cli FLUSHDB

# Or restart containers to clear
docker-compose down -v
docker-compose up -d
```

### Re-import Data

```bash
# Just upload again - it will replace existing data
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@/path/to/export.xml"
```

---

## Troubleshooting

### Export File Too Large

**Issue**: Upload fails with "File too large" error

**Solution**: The default limit is 100 MB. For larger files:
```bash
# Edit backend/src/main.py
# Increase: max_upload_size = 200 * 1024 * 1024  # 200 MB
```

### XML Parsing Errors

**Issue**: "Invalid XML format" error

**Solution**:
1. Check XML is well-formed: `xmllint /path/to/export.xml`
2. Re-export from Health app (may be corrupted)
3. Check file size is > 0 bytes

### No Data After Import

**Issue**: Import succeeds but queries return "no data"

**Solution**:
```bash
# Check Redis has data
docker exec -it redis-wellness-redis-1 redis-cli KEYS '*'

# Restart backend
docker-compose restart backend

# Check logs
docker-compose logs backend | grep "health"
```

### Partial Data Import

**Issue**: Only some metrics imported

**Solution**: Not all metrics may be in your export. Check what's available:
```bash
# See what metrics are present
grep -o 'type="[^"]*"' export.xml | sort -u | head -20
```

---

## Sample Data (for Testing)

If you don't have Apple Health data, you can create sample data:

```bash
cd backend

# Generate sample health data
uv run python scripts/generate_sample_data.py

# This creates a sample export.xml with:
# - 90 days of weight data
# - 30 workouts
# - Heart rate records
# - Step counts
```

---

## Data Retention

### How Long Is Data Stored?

- **Redis Memory**: 7-month TTL (automatically expires)
- **Health Records**: Persists until you run `FLUSHDB`
- **Conversation History**: 7-month TTL per session

### Backup Your Data

Redis data is volatile. To backup:

```bash
# Backup Redis data
docker exec redis-wellness-redis-1 redis-cli SAVE

# Copy dump file
docker cp redis-wellness-redis-1:/data/dump.rdb ./redis-backup.rdb

# Restore (if needed)
docker cp ./redis-backup.rdb redis-wellness-redis-1:/data/dump.rdb
docker-compose restart redis
```

---

## Advanced: Custom Data Processing

### Filter Specific Date Ranges

```python
# Edit backend/src/apple_health/parser.py
# Add date filtering in parse_health_data()

from datetime import datetime

def parse_health_data(xml_path, start_date=None, end_date=None):
    # ... existing code ...
    if start_date:
        records = [r for r in records if r.date >= start_date]
    if end_date:
        records = [r for r in records if r.date <= end_date]
```

### Select Specific Metrics

```python
# Only import specific metrics
METRICS_TO_IMPORT = [
    "BodyMass",
    "BodyMassIndex",
    "HeartRate",
    "StepCount"
]
```

---

## Next Steps

- **[Quick Start](./01_QUICK_START.md)** - Get the app running
- **[Demo Guide](./13_DEMO_GUIDE.md)** - Try example queries
- **[Architecture](./03_ARCHITECTURE.md)** - Understand data flow

---

**Questions?** See [FAQ](./14_FAQ.md) or check the main [README](../README.md)
