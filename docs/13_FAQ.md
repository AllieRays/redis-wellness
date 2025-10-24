# FAQ - Frequently Asked Questions

Common questions, troubleshooting tips, performance tuning, and best practices for Redis Wellness.

## Table of Contents
- [Getting Started](#getting-started)
- [Architecture & Design](#architecture--design)
- [Common Issues](#common-issues)
- [Performance Tuning](#performance-tuning)
- [Best Practices](#best-practices)
- [Advanced Topics](#advanced-topics)

---

## Getting Started

### Q: What is Redis Wellness?

**A**: Redis Wellness is a side-by-side demo comparing **stateless chat** vs. **agentic RAG chat** powered by Redis and RedisVL. It demonstrates the transformative power of memory in AI conversations using:
- **Stateless Agent**: No memory, each message independent
- **Redis RAG Agent**: Full dual memory system (short-term + long-term semantic memory)
- **100% Local**: All processing happens on your machine (Redis + Ollama)

### Q: What are the system requirements?

**A**: Minimum requirements:
- **Docker & Docker Compose**: For containerized deployment
- **Ollama**: Local LLM inference (~8GB RAM for Qwen 2.5 7B)
- **8GB RAM minimum**: 16GB+ recommended
- **10GB disk space**: For models and Docker images
- **macOS, Linux, or Windows** (with Docker Desktop)

### Q: How do I get started quickly?

**A**: Three simple steps:
```bash
# 1. Pull required models
ollama pull qwen2.5:7b
ollama pull mxbai-embed-large

# 2. Start Ollama
ollama serve

# 3. Start application
./start.sh
```

Access the demo at http://localhost:3000

### Q: Why did you choose Qwen 2.5 7B over other models?

**A**: Qwen 2.5 7B provides the best balance for this demo:
- ✅ **Excellent tool-calling** - Optimized for function calling
- ✅ **32k context window** - Handles long conversations
- ✅ **Fast inference** - Reasonable speed on consumer hardware
- ✅ **Good reasoning** - Strong performance on health queries
- ✅ **Local deployment** - Runs well on 16GB RAM

---

## Architecture & Design

### Q: Why separate stateless and stateful agents?

**A**: The side-by-side comparison demonstrates Redis memory value:

**Stateless Agent**:
- No context between messages
- Cannot answer follow-up questions
- Repeats information
- **Use case**: Baseline to show limitations

**Redis RAG Agent**:
- Remembers conversation history
- Semantic memory for long-term context
- Answers "What did you just say?" correctly
- **Use case**: Production-ready memory system

### Q: What is the CoALA framework?

**A**: CoALA (Cognitive Architectures for Language Agents) is our memory system:

**Memory Types**:
1. **Short-term**: Recent conversation (Redis LIST)
2. **Long-term Episodic**: Personal events and experiences
3. **Long-term Procedural**: Health goals and plans
4. **Long-term Semantic**: Facts and knowledge (vector search)

See [04_MEMORY_SYSTEM.md](04_MEMORY_SYSTEM.md) for complete details.

### Q: Why simple loops instead of LangGraph?

**A**: Design decision for maintainability:

❌ **LangGraph overhead**:
- Checkpointing duplicates Redis persistence
- Added complexity for no benefit
- Queries complete in one turn (~3-15 seconds)

✅ **Simple loops**:
- Same agentic behavior (autonomous tool selection)
- Easier to debug and maintain
- Redis already handles persistence
- Perfect for single-turn completions

See [LANGGRAPH_REMOVAL_PLAN.md](../docs/LANGGRAPH_REMOVAL_PLAN.md) for full analysis.

### Q: How does semantic memory work?

**A**: Vector search powered by RedisVL:

1. **Embedding Generation**: Text → 1024-dim vector (mxbai-embed-large)
2. **Storage**: Redis HNSW index for fast similarity search
3. **Retrieval**: Find relevant memories via cosine similarity
4. **Context**: Inject into LLM prompt for contextual responses

**Example**:
```
User: "My weight goal is 130 lbs"
→ Stored in semantic memory with embedding

User (later): "What's my goal?"
→ Vector search finds "weight goal" memory
→ Agent responds: "Your weight goal is 130 lbs"
```

---

## Common Issues

### Q: Backend can't connect to Redis

**Symptoms**: `redis.exceptions.ConnectionError` in logs

**Solutions**:
```bash
# 1. Check Redis is running
docker-compose ps
# Should show redis-wellness as "healthy"

# 2. Verify Redis health
docker exec redis-wellness redis-cli ping
# Should return: PONG

# 3. Check environment variable
docker exec redis-wellness-backend env | grep REDIS_HOST
# Should be "redis" in Docker, "localhost" locally

# 4. Test connectivity
docker exec redis-wellness-backend ping redis
```

**Fix**:
```bash
# Restart Redis
docker-compose restart redis

# Or full reset
docker-compose down
docker-compose up -d --build
```

### Q: Backend can't reach Ollama

**Symptoms**: `httpx.ConnectError` or "Ollama service unavailable"

**Solutions**:
```bash
# 1. Verify Ollama is running on host
curl http://localhost:11434
# Should return: "Ollama is running"

# 2. Check models are pulled
ollama list
# Should show qwen2.5:7b and mxbai-embed-large

# 3. Test from container
docker exec redis-wellness-backend curl http://host.docker.internal:11434

# 4. Check firewall (macOS)
# System Preferences → Security → Firewall → Allow Ollama
```

**Fix**:
```bash
# Start Ollama
ollama serve

# Pull missing models
ollama pull qwen2.5:7b
ollama pull mxbai-embed-large
```

### Q: Port already in use (3000, 8000, or 6379)

**Symptoms**: `Error: bind: address already in use`

**Solutions**:
```bash
# Find what's using the port
lsof -i :3000
lsof -i :8000
lsof -i :6379

# Kill the process
kill -9 <PID>

# Or change ports in docker-compose.yml
# Example: "3001:3000" instead of "3000:3000"
```

### Q: Redis out of memory

**Symptoms**: `OOM command not allowed when used memory > 'maxmemory'`

**Solutions**:
```bash
# 1. Check memory usage
docker exec redis-wellness redis-cli INFO memory
# Look for: used_memory_human

# 2. Clear old data
docker exec redis-wellness redis-cli FLUSHDB

# 3. Check TTL configuration
docker exec redis-wellness redis-cli CONFIG GET maxmemory
```

**Prevention**:
- Enable TTLs (7 months default)
- Monitor memory usage
- Clear old sessions periodically

### Q: Slow response times (>30 seconds)

**Possible Causes**:
1. **Ollama slow on hardware** - Check GPU availability
2. **Cold start** - First query loads model into memory
3. **Long context** - Too many messages in history
4. **Multiple tool calls** - Complex queries need chaining

**Solutions**:
```bash
# 1. Check Ollama performance
time ollama run qwen2.5:7b "What is 2+2?"
# Should be < 5 seconds

# 2. Monitor token usage
curl http://localhost:8000/api/chat/tokens/demo
# Check if context is too large

# 3. Clear session to reset context
curl -X DELETE http://localhost:8000/api/chat/session/demo

# 4. Check tool execution times in response
# Look at response_time_ms and tool_calls_made
```

---

## Performance Tuning

### Q: How can I improve response times?

**Optimizations**:

1. **Use GPU acceleration** (if available):
   ```bash
   # Check if Ollama is using GPU
   ollama ps
   # Should show GPU usage
   ```

2. **Enable embedding cache** (already enabled by default):
   ```bash
   # Check cache stats
   curl http://localhost:8000/api/cache/embedding/stats
   # Target: 30-50% hit rate
   ```

3. **Reduce context window**:
   ```bash
   # In .env
   MAX_CONTEXT_TOKENS=16000  # Reduce from 24000
   ```

4. **Limit tool complexity**:
   - Simple queries (BMI, weight) are fast (~3-5 seconds)
   - Complex aggregations take longer (~10-15 seconds)

### Q: How much memory does Redis use?

**Typical Usage**:
- **Empty database**: ~10-20 MB
- **One user, 100 messages**: ~50-100 MB
- **One user with health data**: ~200-300 MB
- **Target**: < 1 GB for demo purposes

**Monitor**:
```bash
# Check Redis memory
docker exec redis-wellness redis-cli INFO memory | grep used_memory_human

# Check key count
docker exec redis-wellness redis-cli DBSIZE
```

### Q: Can I reduce memory usage?

**Yes, several strategies**:

1. **Shorter TTLs**:
   ```bash
   # 30 days instead of 7 months
   REDIS_SESSION_TTL_SECONDS=2592000
   ```

2. **Smaller context window**:
   ```bash
   MAX_CONTEXT_TOKENS=12000  # Half of default
   ```

3. **Aggressive trimming**:
   ```bash
   TOKEN_USAGE_THRESHOLD=0.5  # Trim at 50% instead of 80%
   ```

4. **Clear old sessions**:
   ```bash
   # Delete specific session
   curl -X DELETE http://localhost:8000/api/chat/session/{session_id}
   ```

### Q: What's the best embedding cache configuration?

**Current Settings** (optimal for demo):
```python
TTL: 7 days
Max size: Unlimited (relies on TTL)
```

**Tuning**:
- **High TTL (7+ days)**: Better for repeated queries, more memory
- **Low TTL (1 day)**: Less memory, more cache misses
- **Monitor**: `/api/cache/embedding/stats`

**Expected Performance**:
- Hit rate: 30-50% with normal usage
- Time saved per hit: ~100ms
- Memory cost: ~4KB per embedding

---

## Best Practices

### Q: Should I use stateless or Redis agent in production?

**Always use Redis RAG Agent** for production:

✅ **Redis Agent Benefits**:
- Context-aware responses
- Remembers user preferences
- Handles follow-up questions
- Better user experience
- Production-ready error handling

❌ **Stateless Agent**:
- Only for baseline comparison
- No memory = poor UX
- Cannot maintain conversation flow

### Q: How should I structure health data imports?

**Best Practices**:

1. **Import once**:
   ```bash
   # Run import script
   uv run python backend/src/scripts/import_health.py data/export.xml
   ```

2. **Clear semantic memory** after new imports:
   - Import script does this automatically
   - Prevents stale cached summaries

3. **Validate data** after import:
   ```bash
   curl "http://localhost:8000/api/chat/redis" \
     -H "Content-Type: application/json" \
     -d '{"message": "How many health records do I have?", "session_id": "test"}'
   ```

4. **Monitor Redis memory**:
   ```bash
   docker exec redis-wellness redis-cli INFO memory
   ```

### Q: How do I handle errors gracefully?

**Error Handling Strategy**:

1. **Check health endpoints**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Use correlation IDs** for tracing:
   ```json
   {
     "error": {
       "code": "REDIS_CONNECTION_FAILED",
       "correlation_id": "req_a1b2c3d4"
     }
   }
   ```

3. **Log errors properly**:
   ```python
   logger.error(f"Error: {e}", exc_info=True, extra={"correlation_id": cid})
   ```

4. **Implement retries** for transient failures:
   ```python
   for attempt in range(3):
       try:
           return await redis_operation()
       except RedisConnectionError:
           if attempt == 2:
               raise
           await asyncio.sleep(1 * (attempt + 1))
   ```

### Q: What's the recommended session management strategy?

**Session Best Practices**:

1. **Generate unique session IDs**:
   ```typescript
   const sessionId = `session_${Date.now()}_${Math.random().toString(36)}`;
   ```

2. **Use meaningful session names**:
   - Good: `demo`, `user_john_mobile`, `onboarding_2025`
   - Bad: `abc123`, `test`, `session`

3. **Clear sessions periodically**:
   ```bash
   # Clear specific session
   curl -X DELETE http://localhost:8000/api/chat/session/demo
   ```

4. **Monitor session memory**:
   ```bash
   curl http://localhost:8000/api/chat/memory/demo
   ```

---

## Advanced Topics

### Q: Can I use different LLMs besides Qwen 2.5?

**Yes**, any Ollama-compatible model:

**Requirements**:
- Tool-calling support (function calling)
- 16k+ context window recommended
- Fast inference speed

**Alternative Models**:
```bash
# Llama 3.1 8B
ollama pull llama3.1:8b
OLLAMA_MODEL=llama3.1:8b

# Mistral 7B
ollama pull mistral:7b
OLLAMA_MODEL=mistral:7b
```

**Trade-offs**:
- Larger models: Better quality, slower inference
- Smaller models: Faster, may struggle with complex queries

### Q: Can I deploy this to production?

**Yes, with modifications**:

**Required Changes**:
1. **Security**:
   - Enable Redis AUTH
   - Add API authentication
   - Use HTTPS/TLS
   - Implement rate limiting

2. **Scalability**:
   - Horizontal scaling (multiple backend replicas)
   - Load balancer
   - Redis clustering for HA

3. **Monitoring**:
   - Prometheus + Grafana
   - Log aggregation (ELK stack)
   - Health check endpoints

4. **Data Persistence**:
   - Redis RDB + AOF
   - Regular backups
   - Volume snapshots

See [10_DEPLOYMENT.md](10_DEPLOYMENT.md) for production deployment guide.

### Q: How do I add custom health metrics?

**Steps**:

1. **Define Pydantic model** (`backend/src/apple_health/models.py`):
   ```python
   class CustomMetric(HealthRecord):
       metric_type: str = "CustomMetric"
       value: float
       unit: str
   ```

2. **Add parser** (`backend/src/apple_health/parser.py`):
   ```python
   def parse_custom_metric(record_element):
       # Parse XML to CustomMetric
   ```

3. **Create tool** (`backend/src/apple_health/query_tools/`):
   ```python
   @tool
   def get_custom_metrics(time_period: str) -> dict:
       """Query custom metrics from Redis."""
   ```

4. **Register tool** with agents (`backend/src/agents/`)

### Q: Can I use a different vector database?

**Currently**: RedisVL is tightly integrated

**To switch** (e.g., to Qdrant, Pinecone):
1. Replace `backend/src/services/memory_manager.py`
2. Implement same interface (store, search methods)
3. Update embedding cache to use new DB
4. Re-index existing data

**Why RedisVL?**
- Single dependency (Redis for everything)
- Fast HNSW index
- Built-in persistence
- Simple deployment

---

## Related Documentation

- [03_ARCHITECTURE.md](03_ARCHITECTURE.md) - System architecture and design decisions
- [06_DEVELOPMENT.md](06_DEVELOPMENT.md) - Development workflow and local setup
- [07_TESTING.md](07_TESTING.md) - Testing strategy and anti-hallucination
- [10_DEPLOYMENT.md](10_DEPLOYMENT.md) - Deployment strategies
- [11_CONFIGURATION.md](11_CONFIGURATION.md) - Complete configuration reference

---

**Last Updated**: October 2025 (Phase 3 improvements)
