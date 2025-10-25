# Demo Guide

**Last Updated**: October 24, 2024
**Target Audience**: Senior developers and technical decision-makers
**Demo Duration**: 15 minutes

## Pre-Demo Checklist

### Environment Check (5 minutes before)

```bash
# 1. Check Ollama is running
curl http://localhost:11434
# Expected: Ollama is running

# 2. Verify models are available
ollama list
# Expected:
# qwen2.5:7b              (4.7 GB)
# mxbai-embed-large       (669 MB)

# 3. Check Docker services
docker-compose ps
# Expected: redis, frontend, backend all "Up"

# 4. Test frontend
curl http://localhost:3000
# Expected: HTML response

# 5. Test backend health
curl http://localhost:8000/health
# Expected: {"status":"healthy"}

# 6. Check Redis connectivity
docker exec -it redis-wellness-redis-1 redis-cli ping
# Expected: PONG

# 7. Verify health data is loaded
curl http://localhost:8000/api/health/summary
# Expected: workout_count > 0
```

### Quick Fix Commands

```bash
# If Ollama not running
ollama serve

# If models missing
ollama pull qwen2.5:7b
ollama pull mxbai-embed-large

# If Docker services down
docker-compose up -d

# If Redis memory full
docker exec redis-wellness-redis-1 redis-cli FLUSHDB

# If ports in use
lsof -ti:3000 | xargs kill -9  # Frontend
lsof -ti:8000 | xargs kill -9  # Backend
lsof -ti:6379 | xargs kill -9  # Redis
```

---

## Demo Script (15 minutes)

### Part 1: The Problem (2 minutes)

**Talking Point**:
> "Traditional chatbots suffer from amnesia. Let me show you what I mean."

**Live Demo - Stateless Chat**:

```bash
# Terminal 1: Start conversation
curl -X POST http://localhost:8000/api/chat/stateless \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my average heart rate last week?"}'

# Response: "Your average heart rate last week was 87 bpm"

# Terminal 2: Follow-up question
curl -X POST http://localhost:8000/api/chat/stateless \
  -H "Content-Type: application/json" \
  -d '{"message": "Is that good?"}'

# Response: ❌ "What are you referring to?"
# (Forgot the context!)
```

**Show in Browser**:
- Open http://localhost:3000
- Toggle to "Stateless Chat" tab
- Type same queries
- Show the failure live

---

### Part 2: The Solution (3 minutes)

**Talking Point**:
> "Now let's see the same conversation with Redis-powered memory using the CoALA framework."

**Explain CoALA Framework** (30 seconds):
- **Episodic**: User preferences, goals, health events
- **Procedural**: Learned tool patterns (gets smarter over time)
- **Semantic**: General health knowledge
- **Short-Term**: Recent conversation history

**Show Architecture** (open `docs/04_MEMORY_SYSTEM.md`):
- 4 Redis data structures
- RedisVL vector search for episodic & semantic
- Redis Hash for O(1) procedural lookup
- Redis List for conversation history

---

### Part 3: Live Comparison (5 minutes)

**Scenario 1: Follow-up Questions**

```bash
# RAG Chat with Memory
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my average heart rate last week?", "session_id": "demo"}'

# Response: "Your average heart rate last week was 87 bpm"

# Follow-up
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "Is that good?", "session_id": "demo"}'

# Response: ✅ "87 bpm is within the normal range for adults (60-100 bpm)..."
# (Remembered "that" = 87 bpm!)
```

**Scenario 2: Pronoun Resolution**

```bash
# First question
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "When did I last work out?", "session_id": "demo2"}'

# Response: "2 days ago - Running, 30 minutes, 245 calories"

# Pronoun test
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my heart rate during that?", "session_id": "demo2"}'

# Response: ✅ "During your run 2 days ago, your average heart rate was 145 bpm"
# (Understood "that" = run from 2 days ago!)
```

**Scenario 3: Complex Multi-Step Query**

```bash
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Compare my workout frequency this month vs last month. Am I improving?",
    "session_id": "demo3"
  }'

# Watch the agent:
# 1. Call search_workouts_and_activity (this month)
# 2. Call search_workouts_and_activity (last month)
# 3. Call compare_workout_periods
# 4. Synthesize: "You worked out 12 times this month vs 8 last month - 50% increase!"
```

---

### Part 4: Architecture Deep-Dive (3 minutes)

**Open RedisInsight** (http://localhost:8001):

1. **Show Memory Keys**:
   ```
   # Short-term memory
   health_chat_session:demo
   health_chat_session:demo2

   # Episodic memory (if any stored)
   episodic:user123:preference:*

   # Procedural memory
   procedure:user123:*

   # Embedding cache
   embedding_cache:*
   ```

2. **Inspect a Chat Session**:
   ```redis
   # Click on health_chat_session:demo
   # Show message history as JSON list
   LRANGE health_chat_session:demo 0 -1
   ```

3. **Show Vector Index**:
   ```redis
   # Show RedisVL indexes
   FT._LIST
   # Expected: episodic_memory_index, semantic_knowledge_index
   ```

**Talking Point**:
> "Notice how Redis stores everything: conversation history as lists, learned patterns as hashes, and memories as vector embeddings for semantic search. All with automatic TTL for privacy."

---

**Show Code** (backend/src/services/memory_coordinator.py):

```python
# Open memory_coordinator.py
# Highlight retrieve_all_context() method

async def retrieve_all_context(
    self,
    session_id: str,
    query: str,
    include_episodic: bool = True,
    include_procedural: bool = True,
    include_semantic: bool = True,
    include_short_term: bool = True,
) -> MemoryContext:
    # Shows unified access to all 4 memory types
    ...
```

**Talking Point**:
> "The Memory Coordinator orchestrates all 4 memory types. The agent just calls one method and gets full context. Clean abstraction."

---

### Part 5: Why Simple Loop, Not LangGraph? (2 minutes)

**Show** `docs/WHY_NO_LANGGRAPH.md` (key points):

1. **Redis already handles persistence** - No need for LangGraph checkpointers
2. **Queries complete in one turn** - No multi-hour workflows
3. **Simpler to debug** - Just a Python loop with tool calls
4. **Same agentic behavior** - LLM chooses tools autonomously

**Code Comparison**:

```python
# Simple loop (stateful_rag_agent.py)
for iteration in range(max_tool_calls):
    response = await llm_with_tools.ainvoke(conversation)

    if not response.tool_calls:
        break  # Done!

    # Execute tools
    for tool_call in response.tool_calls:
        result = await tool.ainvoke(tool_call["args"])
        conversation.append(ToolMessage(content=result))
```

**Talking Point**:
> "No framework overhead. Just Python. The agent is still fully agentic - Qwen 2.5 7B chooses tools autonomously. We just removed unnecessary abstractions."

---

## Q&A Preparation (Common Questions)

### Q1: "How fast is Redis memory retrieval?"

**Answer**:
- **Short-term memory** (last 10 messages): <1ms
- **Procedural memory** (O(1) hash lookup): <1ms
- **Episodic/Semantic search** (RedisVL vector): 10-50ms
- **Total memory retrieval**: ~50ms including all 4 types

**Show**: `docs/04_MEMORY_SYSTEM.md` (Performance Characteristics section)

---

### Q2: "Can this scale to multiple users?"

**Answer**:
Yes! The architecture is designed for multi-user:
- All keys are namespaced by `user_id` or `session_id`
- Redis can handle millions of keys
- Current demo is single-user for simplicity
- Production deployment would add authentication + user management

**Code**: All services already accept `user_id` parameter

---

### Q3: "What about privacy?"

**Answer**:
**100% local processing**:
- Ollama LLM runs on your machine (no cloud APIs)
- Redis stores data locally (no external database)
- Apple Health data never leaves your environment
- 7-month TTL for automatic data expiration

**Show**: `README.md` Privacy-First section

---

### Q4: "Why Qwen 2.5 7B instead of larger models?"

**Answer**:
**Optimized for tool calling**:
- Trained specifically for function calling workflows
- Better tool selection than larger general-purpose models
- 4.7 GB model size runs on most laptops
- Faster inference than 13B+ models
- Perfect balance of capability vs. speed

**Benchmark**: Show tool calling accuracy (if available)

---

### Q5: "How do you prevent LLM hallucinations?"

**Answer**:
**Multi-layered validation**:
1. **Tool-first policy**: Factual queries ALWAYS call tools (never answer from memory)
2. **Numeric validator**: Validates all numbers in response match tool results
3. **Response validation**: Checks LLM output against tool data
4. **Validation score**: Every response gets a validation score (0-100%)

**Code**: `backend/src/utils/numeric_validator.py`

---

### Q6: "What's the learning curve for developers?"

**Answer**:
**Very approachable**:
- Clean architecture (agents, services, utils separation)
- Standard FastAPI backend (familiar patterns)
- Simple tool loop (no framework magic)
- Well-documented (97.2% docstring coverage)
- 91+ passing tests

**Show**: `docs/06_DEVELOPMENT.md`

---

## Troubleshooting During Demo

### Issue: "Ollama not responding"

**Symptoms**:
- 500 errors from `/api/chat/*`
- "Connection refused" in logs

**Fix**:
```bash
# Check if Ollama is running
ps aux | grep ollama

# If not running
ollama serve

# Verify models
ollama list
```

---

### Issue: "Redis connection error"

**Symptoms**:
- "Redis circuit breaker is OPEN" error
- Memory retrieval failures

**Fix**:
```bash
# Check Redis container
docker-compose ps redis

# Restart Redis
docker-compose restart redis

# Verify connection
docker exec redis-wellness-redis-1 redis-cli ping
```

---

### Issue: "No workouts found"

**Symptoms**:
- Tools return empty results
- "No workouts in timeframe" message

**Fix**:
```bash
# Check health data is loaded
curl http://localhost:8000/api/health/summary

# If empty, reload data
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@export.xml"

# Rebuild workout indexes
docker exec redis-wellness-backend-1 \
  python -m backend.scripts.rebuild_workout_indexes
```

---

### Issue: "Frontend not loading"

**Symptoms**:
- Blank page at localhost:3000
- "Cannot GET /" error

**Fix**:
```bash
# Check frontend container
docker-compose ps frontend

# Rebuild frontend
docker-compose up --build frontend

# Check logs
docker-compose logs frontend
```

---

### Issue: "Slow LLM responses"

**Symptoms**:
- Responses taking >30 seconds
- Timeout errors

**Possible Causes**:
1. **First run** - Models loading into memory (normal, wait 1-2 min)
2. **CPU throttling** - Ollama needs CPU resources
3. **Too many concurrent requests** - Ollama is single-threaded

**Fix**:
```bash
# Check Ollama logs
ollama serve  # Watch output

# Reduce max_tool_calls if needed
# In agent config, set max_tool_calls=3 instead of 8
```

---

## Post-Demo Resources

### Share with Attendees

1. **GitHub Repository**: https://github.com/your-org/redis-wellness
2. **Documentation Index**: `docs/00_DOCUMENTATION_INDEX.md`
3. **Quick Start Guide**: `docs/01_QUICK_START.md`
4. **Memory System Deep-Dive**: `docs/04_MEMORY_SYSTEM.md`
5. **Why No LangGraph**: `docs/WHY_NO_LANGGRAPH.md`

### Follow-up Email Template

```
Subject: Redis Wellness Demo - Resources & Next Steps

Hi [Name],

Thanks for attending the Redis Wellness demo! Here are the resources I mentioned:

🚀 Quick Start:
- Clone: https://github.com/your-org/redis-wellness
- Run: ./start.sh
- Access: http://localhost:3000

📚 Key Documentation:
- Memory System (CoALA): docs/04_MEMORY_SYSTEM.md
- Architecture: docs/03_ARCHITECTURE.md
- API Reference: docs/09_API.md

🧠 Concepts:
- Why simple loop over LangGraph: docs/WHY_NO_LANGGRAPH.md
- Redis AI Agents: https://redis.io/blog/ai-agents-memory/
- CoALA Paper: https://arxiv.org/pdf/2309.02427

💬 Questions?
[Your contact info]

Best,
[Your name]
```

---

## Demo Variations

### Short Version (5 minutes)

1. Show stateless failure (1 min)
2. Show RAG success (2 min)
3. Open RedisInsight to show keys (2 min)

### Technical Deep-Dive (30 minutes)

1. Full demo (15 min)
2. Code walkthrough (10 min):
   - Memory coordinator
   - Agent implementation
   - Tool definitions
3. Q&A (5 min)

### Executive Version (10 minutes)

1. Business problem (2 min): "Chatbots that forget = poor user experience"
2. Solution demo (5 min): Side-by-side comparison
3. Value proposition (3 min):
   - 100% privacy (local)
   - Production-ready (Redis)
   - Cost-effective (no API fees)

---

## Success Metrics

After the demo, attendees should be able to:

- ✅ Explain the difference between stateless and stateful chat
- ✅ Understand the 4 CoALA memory types
- ✅ See the value of Redis for AI agent memory
- ✅ Know how to get started with the codebase

---

## Checklist: Day Before Demo

- [ ] Pull latest code: `git pull origin main`
- [ ] Rebuild containers: `docker-compose up --build`
- [ ] Verify Ollama models: `ollama list`
- [ ] Load fresh health data: `curl -X POST ... -F "file=@export.xml"`
- [ ] Test both chat endpoints (stateless + Redis)
- [ ] Open RedisInsight and verify keys
- [ ] Review Q&A section
- [ ] Prepare backup laptop (if presenting remotely)
- [ ] Test screen sharing setup
- [ ] Clear Redis if needed: `docker exec redis-wellness-redis-1 redis-cli FLUSHDB`

---

## Checklist: 30 Minutes Before Demo

- [ ] Run pre-demo health checks (see top of document)
- [ ] Clear browser cache
- [ ] Close unnecessary applications
- [ ] Prepare terminal windows:
   - Terminal 1: `curl` commands ready
   - Terminal 2: `docker-compose logs -f backend`
   - Terminal 3: RedisInsight open
- [ ] Open documentation tabs:
   - `docs/04_MEMORY_SYSTEM.md`
   - `docs/WHY_NO_LANGGRAPH.md`
- [ ] Test audio/video if remote
- [ ] Silence notifications

---

## Emergency Backup Plan

**If live demo fails**:

1. **Have screenshots ready** (`docs/screenshots/` folder)
2. **Record demo video beforehand** (upload to YouTube/Vimeo)
3. **Show code instead** - Walk through key files:
   - `backend/src/services/memory_coordinator.py`
   - `backend/src/agents/stateful_rag_agent.py`
   - `docs/04_MEMORY_SYSTEM.md`

**Always have Plan B!**

---

**Last Updated**: October 24, 2024
**Maintainer**: [Your Name]
**Feedback**: [Your Email/Slack]
