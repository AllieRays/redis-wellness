# Quick Start Guide

Get Redis Wellness AI running in 5 minutes.

---

## Prerequisites Check

Before starting, ensure you have:
- Docker Desktop installed and running
- Ollama installed and running
- 10 GB free disk space (for models)

**See [Prerequisites Guide](./02_PREREQUISITES.md) for detailed installation instructions.**

---

## Step 1: Start Ollama

```bash
# Verify Ollama is running
curl http://localhost:11434

# If not running, start it
ollama serve
```

---

## Step 2: Pull Required Models

```bash
# Pull Qwen 2.5 7B (main LLM) - 4.7 GB
ollama pull qwen2.5:7b

# Pull mxbai-embed-large (embeddings) - 669 MB
ollama pull mxbai-embed-large
```

**Note**: First-time pull takes 5-10 minutes depending on internet speed.

---

## Step 3: Start Services

```bash
# Clone repository (if not already done)
cd /path/to/redis-wellness

# Start all services
docker-compose up --build
```

**Expected output**:
```
✓ redis      Running
✓ backend    Running
✓ frontend   Running
```

---

## Step 4: Verify Services

Open these URLs in your browser:

1. **Frontend**: http://localhost:3000
   - Should show side-by-side chat interface

2. **API Docs**: http://localhost:8000/docs
   - Should show Swagger UI

3. **RedisInsight**: http://localhost:8001
   - Should show Redis database

4. **Health Check**: http://localhost:8000/health
   - Should return `{"status": "healthy"}`

---

## Step 5: Try a Query

### Using the Frontend (Recommended)

1. Go to http://localhost:3000
2. Type in **stateless chat**: "What was my average heart rate last week?"
3. Type in **Redis chat**: "What was my average heart rate last week?"
4. Compare responses

### Using curl

```bash
# Stateless chat
curl -X POST http://localhost:8000/api/chat/stateless \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my average heart rate last week?"}'

# Redis chat with memory
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my average heart rate last week?", "session_id": "demo"}'
```

---

## Step 6: Load Health Data (Optional)

**To get real health insights**, load your Apple Health data.

### Quick Method: Export from iPhone

1. **On iPhone**: Health app → Profile → Export All Health Data
2. **Transfer** `export.zip` to your Mac (AirDrop or email)
3. **Extract** to get `export.xml`
4. **Upload**:

```bash
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@/path/to/export.xml"
```

**Expected**: "Health data imported successfully" with metrics count

### No iPhone?

Generate sample data for testing:
```bash
cd backend
uv run python scripts/generate_sample_data.py
```

**Full guide**: See [Apple Health Data Guide](./10_HEALTH_DATA.md) for:
- Detailed export instructions with screenshots
- Troubleshooting import errors
- Privacy & security details
- Data management (backup, clear, re-import)

---

## Common Issues

### Ollama Not Running
```bash
# Error: Connection refused to localhost:11434
# Solution: Start Ollama
ollama serve
```

### Redis Connection Failed
```bash
# Error: Could not connect to Redis
# Solution: Restart Docker services
docker-compose down
docker-compose up --build
```

### Port Already in Use
```bash
# Error: Port 3000/8000/6379 already in use
# Solution: Stop conflicting services or change ports in docker-compose.yml
```

---

## Next Steps

- **[Architecture Guide](./03_ARCHITECTURE.md)** - Understand the system design
- **[Development Guide](./06_DEVELOPMENT.md)** - Set up local development
- **[Demo Guide](./13_DEMO_GUIDE.md)** - Prepare for technical presentations

---

## Stopping Services

```bash
# Stop services (keep data)
docker-compose down

# Stop services and clear Redis data
docker-compose down -v
```

---

**Need Help?** See [FAQ](./14_FAQ.md) or check archived docs in `/docs/archive/`
