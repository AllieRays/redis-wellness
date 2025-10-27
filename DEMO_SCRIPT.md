# Redis Wellness Demo Script

**Duration**: 3-5 minutes  
**Goal**: Show memory transforms AI from simple Q&A into intelligent conversation

---

## Setup (Before Demo)

```bash
# Clear any previous session
make clear-session

# Verify services are running
make health

# Open UI
open http://localhost:3000
```

---

## Demo Flow: Side-by-Side Comparison

### Part 1: Basic Query (Both Work The Same) ⚡ ~5 seconds

**Type in BOTH panels simultaneously:**

```
Tell me about my recent workouts
```

**Expected Result:**
- ✅ Both agents answer correctly
- ✅ Both show workout count and summary
- ✅ Both use `get_workout_data` tool

**Point to make:** *"Both agents work great on first queries - they have the same tools and data access."*

---

### Part 2: Follow-Up Question (Memory Difference) ⚡ ~3 seconds

**Type in BOTH panels:**

```
What's the most common type?
```

**Expected Results:**

| Stateless | Stateful |
|-----------|----------|
| ❌ "What are you referring to?" | ✅ "Traditional Strength Training (X workouts)" |

**Point to make:** *"The stateless agent forgot we were talking about workouts. The stateful agent remembers via Redis checkpointing."*

---

### Part 3: Pronoun Resolution (Checkpointing) ⚡ ~4 seconds

**Type in BOTH panels:**

```
When was my last workout?
```

Both answer correctly (e.g., "October 17, 2024")

**Then type:**

```
How long was it?
```

**Expected Results:**

| Stateless | Stateful |
|-----------|----------|
| ❌ "How long was what?" | ✅ "27 minutes" |

**Point to make:** *"Stateful agent resolves 'it' to the workout we just discussed. Pure LLM with conversation history in Redis."*

---

### Part 4: Goal Memory (Optional - If Time Allows) ⚡ ~6 seconds

**First, set a goal (Stateful only):**

```
My goal is to work out 3 times per week
```

Response: "Got it! I'll remember your goal..."

**Then ask (Stateful only):**

```
Am I meeting my goal?
```

**Expected Result:**
- ✅ Retrieves goal from RedisVL episodic memory
- ✅ Compares to actual workout frequency
- ✅ Answers: "You're averaging X workouts per week..."

**Point to make:** *"The agent stored my goal in RedisVL vector memory and retrieved it autonomously when I asked about progress."*

---

## Backup Questions (If Something Goes Wrong)

### Safe Fallback #1: Heart Rate
```
What was my average heart rate last week?
```
Then: 
```
Is that normal?
```

### Safe Fallback #2: Steps
```
How many steps did I walk yesterday?
```
Then:
```
What about today?
```

---

## Key Talking Points

### 1. Same Tools, Different Memory
- Both agents have identical health data tools
- Only difference is memory architecture
- Stateful: Redis checkpointing + RedisVL vector search

### 2. Four-Layer Memory (Quick)
- **Short-term**: Conversation history (checkpointing)
- **Episodic**: Goals and facts (vector search)
- **Procedural**: Learned patterns (workflow optimization)
- **Semantic**: Optional knowledge base

### 3. 100% Local & Private
- All data stays on your machine
- Ollama (Qwen 2.5 7B) runs locally
- Redis stores everything locally
- Zero external API calls

---

## Performance Stats to Highlight

Point to the **Performance Comparison** panel at top:

- **Tokens**: Should be similar initially
- **Avg Response**: Both fast (1-3 seconds)
- **Memory overhead**: Minimal (checkpointing is fast)

**Key message:** *"Memory doesn't slow things down - Redis is optimized for sub-millisecond retrieval."*

---

## Troubleshooting During Demo

### Agent gives wrong answer
**Recovery:** Clear session and restart
```bash
make clear-session
```
Refresh browser and try again

### Agent is slow
**Recovery:** 
- Check Ollama is running: `curl http://localhost:11434`
- Model might be cold - first query warms it up

### Tools not showing
**Recovery:** Tools are displayed below each response as badges

---

## Demo Variants

### Quick Demo (2 minutes)
- Part 1: Recent workouts
- Part 2: Most common type
- Done!

### Full Demo (5 minutes)
- All 4 parts
- Show RedisInsight (optional)

### Technical Demo (10 minutes)
- Include goal setting
- Show Redis keys: `make redis-keys`
- Explain memory architecture
- Show code structure

---

## After Demo

Show the codebase structure:
```bash
# Show comprehensive docs
ls docs/

# Show memory patterns
cat docs/10_MEMORY_ARCHITECTURE.md

# Show Redis patterns
make redis-keys
```

Point them to:
- GitHub repo: https://github.com/AllieRays/redis-wellness
- RedisVL docs: https://redisvl.com
- LangGraph docs: https://langchain-ai.github.io/langgraph/

---

## Emergency Reset

If demo goes completely sideways:

```bash
# Nuclear option - full reset
make down
make clean
make up
make import
make clear-session

# Wait 30 seconds for services to stabilize
sleep 30

# Verify
make health
```

Then refresh browser and start over.
