# Quickstart

## 1. Overview

Get the Redis Wellness demo running in under 5 minutes using simple Make commands. This guide assumes you've completed [01_PREREQUISITES.md](01_PREREQUISITES.md).

### Quick Start (TL;DR)

```bash
# 1. Start all services
make up

# 2. Import your health data
make import

# 3. Open http://localhost:3000
```

That's it! Continue reading for detailed steps and troubleshooting.

### What You'll Learn

- **[Prerequisites Check](#2-prerequisites-check)** - Verify your environment is ready
- **[Start the Application](#3-start-the-application)** - Launch all services
- **[Import Health Data](#4-import-health-data)** - Load your Apple Health data
- **[Try the Demo](#5-try-the-demo)** - Test the side-by-side comparison
- **[Troubleshooting & Next Steps](#6-troubleshooting--next-steps)** - Common issues and where to go next

---

## 2. Prerequisites Check

**Quick verification:**

```bash
# Verify Docker is running
docker --version

# Verify Ollama has required models
ollama list | grep -E "qwen2.5:7b|mxbai-embed-large"

# Verify health data export exists
ls apple_health_export/export.xml
```

**If any check fails**, complete [01_PREREQUISITES.md](01_PREREQUISITES.md) first.

---

## 3. Start the Application

```bash
# Start all services
make up
```

This starts Frontend (3000), Backend (8000), Redis (6379), and RedisInsight (8001).

**Verify services:**

```bash
# Check all services are healthy
make health
```

**Access points:**
- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs
- **RedisInsight**: http://localhost:8001

---

## 4. Import Health Data

```bash
# Import your Apple Health data
make import

# Verify import was successful
make verify

# (Optional) View statistics
make stats
```

**Import time**: 1-5 minutes depending on data volume.

**What gets imported**: Health metrics (heart rate, steps, weight, BMI), sleep analysis, workout records, and indexes for fast queries.

---

## 5. Try the Demo

Open **http://localhost:3000** to see both agents side-by-side. See [05_STATELESS_VS_STATEFUL_COMPARISON.md](05_STATELESS_VS_STATEFUL_COMPARISON.md) for the full comparison.

### Test the Memory Difference

Try this sequence to see memory in action:

1. **"How many workouts do I have?"**
   - Both agents answer correctly

2. **"What day do I work out most?"**
   - Both agents analyze your workout patterns

3. **"Why did you say that?"** ← *This reveals the difference*
   - ❌ **Stateless**: "I don't have context about what I said before."
   - ✅ **Stateful**: "Based on your last 6 workouts, 3 were on Friday..."

The stateful agent remembers the conversation and can reference previous responses using its [four-layer memory architecture](10_MEMORY_ARCHITECTURE.md).

### Useful Commands

```bash
make logs           # View real-time logs
make redis-keys     # Check Redis data (see 11_REDIS_PATTERNS.md)
make clear-session  # Clear chat (keeps health data)
make stats          # View health data statistics
```

See [05_STATELESS_VS_STATEFUL_COMPARISON.md](05_STATELESS_VS_STATEFUL_COMPARISON.md) for detailed comparison.

---

## 6. Troubleshooting & Next Steps

### Common Issues

**Services not starting:**
```bash
# View logs for all services
make logs

# Check service health
make health
```

**Ollama not running:**
```bash
# Check Ollama is running
curl http://localhost:11434

# Verify models are downloaded
ollama list

# Restart Ollama (macOS)
open /Applications/Ollama.app
```

**Redis connection issues:**
```bash
# Check Redis container
docker compose ps redis

# Test Redis connection
redis-cli -h localhost -p 6379 ping
# Should return: PONG
```

**Import failed:**
```bash
# Check export.xml exists
ls -lh apple_health_export/export.xml

# View backend logs
make logs

# Try fresh import (cleans Redis and reimports)
make fresh-start
```

**Port conflicts:**
```bash
# Check if ports are in use
lsof -i :3000  # Frontend
lsof -i :8000  # Backend
lsof -i :6379  # Redis

# Stop all services
make down

# Or change ports in docker-compose.yml and restart
make up
```

**Need to rebuild containers:**
```bash
# Rebuild Docker images (preserves Redis data)
make rebuild

# Or full clean rebuild
make down
make clean
make up
```

### Make Command Reference

Run `make help` anytime to see all available commands:

**Setup & Development:**
- `make up` - Start all Docker containers
- `make down` - Stop all Docker containers
- `make logs` - View Docker logs
- `make health` - Check all services status

**Data Management:**
- `make import` - Import Apple Health data
- `make verify` - Verify data is loaded
- `make stats` - Show health data statistics
- `make import-xml` - Import from specific XML file (prompts for path)

**Testing & Quality:**
- `make test` - Run all tests
- `make test-unit` - Run unit tests only
- `make lint` - Run code linting

**Redis Operations:**
- `make redis-keys` - Show Redis keys
- `make redis-clean` - Clean Redis data (FLUSHALL, prompts for confirmation)
- `make clear-session` - Clear chat session (keeps health data)

**Quick Commands:**
- `make fresh-start` - Clean + Import + Start (full reset)
- `make rebuild` - Rebuild Docker images (preserves data)
- `make clean` - Clean build artifacts

### Next Steps

Now that the demo is running:

1. **Explore the UI** - Try various health queries and compare responses
2. **Check Redis data** - Run `make redis-keys` or open http://localhost:8001 (RedisInsight)
3. **View API docs** - Open http://localhost:8000/docs for Swagger documentation
4. **Monitor logs** - Run `make logs` to watch service activity in real-time

---

## Related Documentation

- **[01_PREREQUISITES.md](01_PREREQUISITES.md)** - Prerequisites setup guide
- **[05_STATELESS_VS_STATEFUL_COMPARISON.md](05_STATELESS_VS_STATEFUL_COMPARISON.md)** - Detailed demo walkthrough and comparison
- **[10_MEMORY_ARCHITECTURE.md](10_MEMORY_ARCHITECTURE.md)** - Four-layer memory system explained
- **[06_AGENTIC_RAG.md](06_AGENTIC_RAG.md)** - How agentic tool calling works
- **[07_HOW_TO_IMPORT_APPLE_HEALTH_DATA.md](07_HOW_TO_IMPORT_APPLE_HEALTH_DATA.md)** - Apple Health data pipeline details

---

**Key takeaway:** Three commands (`make up`, `make import`, open browser) gets you a working demo comparing stateless vs. stateful AI agents powered by Redis memory.
