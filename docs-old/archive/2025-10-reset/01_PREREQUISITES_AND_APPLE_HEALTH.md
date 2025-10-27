# Prerequisites and Apple Health data

Goal: run locally with your real Apple Health export while keeping all data on your machine.

## Requirements

- Docker + Docker Compose (Redis Stack, frontend, backend)
- Ollama running locally with models:
  - `qwen2.5:7b` (LLM)
  - `mxbai-embed-large` (embeddings, 1024-dim)
- macOS/iPhone for Apple Health export (XML)

```bash path=null start=null
# Verify Ollama & models
curl -s http://localhost:11434 | jq .version || true
ollama pull qwen2.5:7b
ollama pull mxbai-embed-large

# Verify Redis Stack
docker compose up -d redis
curl -s localhost:8001 >/dev/null || echo "Open RedisInsight at http://localhost:8001"
```

## Export Apple Health from iPhone

- iPhone → Health app → your profile (top right) → Export All Health Data
- AirDrop or copy the ZIP to your Mac, unzip to get `export.xml`
- Place at `apple_health_export/export.xml` in this repository

```bash path=null start=null
mkdir -p apple_health_export
mv ~/Downloads/apple_health_export/export.xml apple_health_export/export.xml
```

## Import into Redis (one-time, local only)

- Parsing options:
  - XML path (full parse; slower, most accurate)
  - JSON path (if you already have `parsed_health_data.json`)

```bash path=null start=null
# From repo root, with Docker Redis running (6379 exposed)
uv run python import_health_data.py apple_health_export/export.xml
# or
uv run python import_health_data.py parsed_health_data.json
```

What the importer does:
- Parses and normalizes timestamps to UTC
- Stores `health:user:{user_id}:data` and metric indices with TTL
- Ensures workouts include `day_of_week`, `date`, `calories`, `type_cleaned`
- Rebuilds Redis workout indexes (O(1) aggregations)

Verify keys (optional):
```bash path=null start=null
redis-cli KEYS "health:user:*"
redis-cli GET health:user:wellness_user:data | head -c 200 && echo
```

## Health checks

```bash path=null start=null
# Backend dependency health
curl -s http://localhost:8000/api/health/check | jq

# API docs
open http://localhost:8000/docs
# Frontend
open http://localhost:3000
```

Notes
- No cloud calls; data lives in Redis locally
- You can re-run the importer after a new export; indexes are rebuilt automatically
