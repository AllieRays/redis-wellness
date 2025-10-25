# Redis Wellness - Critical Project Information

## Project Architecture

**We ALWAYS use Docker** - All services run in containers via `docker compose`

### Key Locations:
- **Import script**: `/import_health_data.py` (project root)
- **Backend source**: `/backend/src/`
- **Apple Health logic**: `/backend/src/apple_health/` (parser, query tools)
- **Tests**: `/backend/tests/e2e/`
- **Data in Docker**: `/apple_health_export/export.xml` (87MB, inside backend container)

### Docker Commands:
```bash
# Start all services
docker compose up -d

# View logs
docker compose logs backend -f

# Access Redis (from host)
docker compose exec redis redis-cli

# Run import script (runs on HOST, connects to Docker Redis)
uv run python import_health_data.py

# Access backend container
docker compose exec backend bash
```

**IMPORTANT**: The import script runs on your HOST machine (not inside Docker), but connects to Redis inside the Docker container via port 6379.

## ⚠️ CRITICAL: Data Import Script

**Location:** `/import_health_data.py` (project root)

**THIS IS THE ONLY SCRIPT FOR IMPORTING HEALTH DATA**

### Why This Matters:
- Uses hash sets to prevent duplicate imports
- Correctly handles datetime parsing (ISO format with timezone)
- Enriches workout data with required fields (`day_of_week`, `type_cleaned`, `calories`)
- Calls `rebuild_workout_indexes.py` for proper Redis indexing
- **DO NOT create new import scripts** - this one handles all the edge cases

### Usage:
```bash
# From XML export (slow, ~2-5 minutes for 87MB file)
uv run python import_health_data.py apple_health_export/export.xml

# From pre-parsed JSON (fast, seconds)
uv run python import_health_data.py parsed_health_data.json

# Auto-detect
uv run python import_health_data.py
```

### What It Does:
1. **Parses** Apple Health XML or pre-parsed JSON
2. **Enriches** workouts with computed fields:
   - `day_of_week`: "Monday", "Tuesday", etc. (REQUIRED by tools)
   - `type_cleaned`: "Running", "Cycling" (removes HK prefix)
   - `calories`: Standardizes `totalEnergyBurned` field
3. **Stores** in Redis:
   - `user:wellness_user:health_data` - Main health data
   - `user:wellness_user:health_metric:{type}` - Metric indices (7 month TTL)
4. **Indexes** workouts via `rebuild_workout_indexes.py` for fast queries

### Important Fields:
- **startDate**: ISO format (`2024-10-15T10:30:00Z`) - DO NOT change format
- **day_of_week**: Must be full day name ("Monday", not "Mon")
- **Hash sets**: Prevents re-importing same data

## Data Flow

```
Apple Health Export (export.xml)
         ↓
  import_health_data.py
         ↓
      Redis
         ↓
   Agent Tools
         ↓
     Frontend
```

## Testing

### E2E Tests Location:
`/backend/tests/e2e/`

#### Available Tests:
1. **`test_data_validation.sh`** - Verifies real data is loaded
2. **`test_hallucinations.sh`** - Detects AI hallucinations
3. **`test_baseline.sh`** - Quality baseline for agent behavior

#### Run Tests:
```bash
cd backend/tests/e2e

# 1. Validate data is loaded
./test_data_validation.sh

# 2. Test for hallucinations
./test_hallucinations.sh

# 3. Baseline quality tests
./test_baseline.sh
```

## Key Constraints

### DO NOT:
- ❌ Create new import scripts
- ❌ Change datetime formats
- ❌ Remove hash set deduplication
- ❌ Skip workout enrichment step
- ❌ Modify Redis key structure without updating `utils/redis_keys.py`

### DO:
- ✅ Use `import_health_data.py` for ALL imports
- ✅ Test with `test_data_validation.sh` after importing
- ✅ Run hallucination tests to verify agent accuracy
- ✅ Check `rebuild_workout_indexes.py` for workout indexing

## Data Location

### In Docker Container (backend):
- **XML Export**: `/apple_health_export/export.xml` (87MB)
- **Parsed JSON**: `/parsed_health_data.json` (if pre-parsed)

### In Redis Container:
Access via: `docker compose exec redis redis-cli`

- **Main data**: `user:wellness_user:health_data`
- **Metrics**: `user:wellness_user:health_metric:{MetricType}` (7-month TTL)
- **Workout indexes**: Managed by `rebuild_workout_indexes.py`
- **LangGraph state**: `checkpoint:*` keys (agent memory)

### Apple Health Module Structure

```
backend/src/apple_health/
├── parser.py                    # XML parsing (AppleHealthParser)
├── query_tools/                 # LangChain tools for agents
│   ├── __init__.py             # Tool registration
│   ├── search_health_records.py
│   ├── search_workouts.py
│   ├── aggregate_metrics.py
│   ├── compare_periods.py
│   └── ...other analysis tools
└── models.py                    # Data models
```

**Important**: Tools in `query_tools/` are what agents use to access data. They query Redis via `redis_manager`.

## Related Scripts

- **`rebuild_workout_indexes.py`**: Called automatically by import script
- **`scripts/startup_health_check.py`**: Validates data on backend startup

## Troubleshooting

### "Agent says it doesn't have data"
1. Check if data is imported: `cd backend/tests/e2e && ./test_data_validation.sh`
2. Verify Redis keys exist: `docker compose exec redis redis-cli KEYS "*health*"`
3. Check Redis is running: `docker compose ps`
4. Re-import if needed: `uv run python import_health_data.py`

### "Datetime format errors"
- **Solution**: Use `import_health_data.py` - it handles all datetime edge cases
- **DO NOT** manually parse dates - use the script's `datetime.fromisoformat()`
- All dates stored in ISO format with timezone (`2024-10-15T10:30:00Z`)

### "Duplicate workout entries"
- **Cause**: Not using hash sets properly
- **Solution**: `import_health_data.py` handles deduplication automatically

### "Redis commands fail"
- **Always use Docker**: `docker compose exec redis redis-cli` (NOT `redis-cli`)
- Redis runs in container, not on host

### "Backend can't connect to Redis"
- Check both containers running: `docker compose ps`
- Check Docker network: `docker compose logs backend | grep -i redis`
- Redis host in code is `redis` (container name), not `localhost`
