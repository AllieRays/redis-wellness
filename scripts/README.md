# Health Data Scripts

This directory contains scripts for parsing and loading Apple Health data into the Redis wellness system.

## Scripts Overview

### 🆕 Recommended Scripts (Fixed & Improved)

**`parse_apple_health.py`** - Parse Apple Health XML to JSON
- Reads `apple_health_export/export.xml`
- Generates `parsed_health_data.json` with structured health data
- Usage: `python scripts/parse_apple_health.py`

**`load_health_to_redis.py`** - Load parsed JSON into Redis
- Reads `parsed_health_data.json`
- Stores data in Redis with proper keys for chat system
- Sets 7-month TTL on all data
- Usage: `python scripts/load_health_to_redis.py`

### 📜 Legacy Scripts (Fixed)

**`load_health_data.py`** - Original combined parser + Redis loader
- Does both XML parsing and Redis loading in one step
- Usage: `python scripts/load_health_data.py`

**`simple_load_health.py`** - Alternative loader using backend tools
- Uses the backend's health parser tools directly
- Usage: `python scripts/simple_load_health.py`

**`load_real_health.py`** - Existing loader (untouched)

## Quick Start

### First Time Setup
```bash
# 1. Parse your Apple Health export
python scripts/parse_apple_health.py

# 2. Load into Redis for chat system
python scripts/load_health_to_redis.py
```

### Re-parsing After New Export
```bash
# When you get a new Apple Health export:
# 1. Replace apple_health_export/export.xml with new file
# 2. Re-parse and reload
python scripts/parse_apple_health.py
python scripts/load_health_to_redis.py
```

## Prerequisites

- Apple Health export placed in `apple_health_export/export.xml`
- Redis running (via `docker-compose up redis`)
- Python packages: `redis`, plus backend dependencies

## Output

- **`parsed_health_data.json`** - Structured health data (255k+ records)
- **Redis keys** - Data stored at `health:user:your_user:data` etc.
- **Chat ready** - System can answer health queries

## Data Structure

The parsed JSON contains:
- `record_count` - Total health records
- `workouts` - Exercise/activity data
- `metrics_summary` - Latest values by metric type
- `metrics_records` - Full historical data
- `date_range` - Data span (2020-2025+)
- `conversation_context` - Summary for AI chat

## Troubleshooting

**Import Errors**: Make sure you're running from the project root directory

**Redis Connection**: Ensure Redis is running with `docker-compose up redis`

**Missing Export**: Place your Apple Health export.xml in `apple_health_export/`
