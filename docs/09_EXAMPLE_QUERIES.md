# Example Queries: Stateless vs Stateful Comparison

## 1. Overview

This guide demonstrates the difference between stateless and stateful AI agents using **real health queries**. Each example shows what tools are used, which memory systems activate, and how responses differ.

**Teaching Goal**: See why memory transforms AI from simple Q&A into intelligent conversation.

### What You'll Learn

- **[Basic Health Queries](#2-basic-health-queries)** - Simple metric retrieval and statistics
- **[Follow-up Questions](#3-follow-up-questions)** - Where stateless fails and stateful shines
- **[Pronoun Resolution](#4-pronoun-resolution)** - Understanding "it", "that", "those"
- **[Goal-Based Queries](#5-goal-based-queries-episodic-memory)** - Episodic memory retrieval
- **[Pattern Learning](#6-pattern-learning-procedural-memory)** - Procedural memory optimization
- **[Multi-Turn Reasoning](#7-multi-turn-reasoning)** - Complex conversations with context
- **[Tool Chaining](#8-tool-chaining-examples)** - Multi-step autonomous workflows

---

## 2. Basic Health Queries

### Query: "What was my average heart rate last week?"

| Aspect | Details |
|--------|---------|
| **Feature** | Health metric retrieval with statistics |
| **Tool Used** | `get_health_metrics` |
| **Memory Type** | None (stateless) / Short-term (stateful) |
| **Stateless Response** | "Your average heart rate last week was 72 bpm." |
| **Stateful Response** | "Your average heart rate last week was 72 bpm." |
| **Key Difference** | ✅ Both agents answer correctly on first query |

**Why they're the same**: First queries don't need memory. Both agents call the same tool and return the same data.

---

### Query: "How many calories did I burn this month?"

| Aspect | Details |
|--------|---------|
| **Feature** | Workout calorie aggregation |
| **Tool Used** | `get_workout_data` |
| **Memory Type** | None |
| **Stateless Response** | "You burned 2,847 calories across 12 workouts this month." |
| **Stateful Response** | "You burned 2,847 calories across 12 workouts this month." |
| **Key Difference** | ✅ Both agents provide same factual answer |

**Why they're the same**: Simple factual queries work for both agents.

---

## 3. Follow-up Questions

### Initial Query: "How many workouts do I have?"

| Aspect | Details |
|--------|---------|
| **Tool Used** | `get_workout_data` |
| **Stateless Response** | "You have 154 workouts recorded." |
| **Stateful Response** | "You have 154 workouts recorded." |

### Follow-up: "What's the most common type?"

| Aspect | Details |
|--------|---------|
| **Memory Type** | None / Short-term checkpointing |
| **Stateless Response** | ❌ "What are you referring to? Please provide more context about what you want to know the most common type of." |
| **Stateful Response** | ✅ "Traditional Strength Training is your most common workout type (40 workouts, 26% of your total)." |
| **Key Difference** | Stateful remembers "workouts" from previous turn |

**Redis Keys Used (Stateful)**:
- `langgraph:checkpoint:{session_id}:*` - Conversation history

---

### Initial: "When was my last cycling workout?"

| Aspect | Details |
|--------|---------|
| **Tool Used** | `get_workout_data` |
| **Stateless Response** | "Your last cycling workout was on October 17, 2024 at 4:19 PM." |
| **Stateful Response** | "Your last cycling workout was on October 17, 2024 at 4:19 PM." |

### Follow-up: "How many calories did I burn?"

| Aspect | Details |
|--------|---------|
| **Memory Type** | Short-term checkpointing |
| **Stateless Response** | ❌ "I need more information. Which workout or time period are you asking about?" |
| **Stateful Response** | ✅ "You burned 420 calories during that cycling workout on October 17th." |
| **Key Difference** | Stateful connects "I burn" to "last cycling workout" |

**How It Works**:
```python
# Stateful agent has conversation history in context:
messages = [
    HumanMessage("When was my last cycling workout?"),
    AIMessage("Your last cycling workout was on October 17, 2024 at 4:19 PM."),
    HumanMessage("How many calories did I burn?")  # LLM understands implicit reference
]
```

---

## 4. Pronoun Resolution

### Initial: "Show me my workouts from last Friday"

| Aspect | Details |
|--------|---------|
| **Tool Used** | `get_workout_data` |
| **Stateless Response** | "You had 2 workouts last Friday: Cycling (45 min, 420 cal) and Yoga (30 min, 150 cal)." |
| **Stateful Response** | "You had 2 workouts last Friday: Cycling (45 min, 420 cal) and Yoga (30 min, 150 cal)." |

### Follow-up: "Which one was more intense?"

| Aspect | Details |
|--------|---------|
| **Memory Type** | Short-term checkpointing |
| **Stateless Response** | ❌ "Which workouts are you comparing? Please specify." |
| **Stateful Response** | ✅ "The cycling workout was more intense - you averaged 142 bpm vs 98 bpm for yoga, and burned 2.8x more calories per minute." |
| **Pronoun Resolved** | "one" → "cycling vs yoga from last Friday" |

**Redis Keys Used (Stateful)**:
- `langgraph:checkpoint:{session_id}:*` - Stores both messages

---

### Query: "Did I work out yesterday? If so, how long?"

| Aspect | Details |
|--------|---------|
| **Feature** | Conditional query with implicit follow-up |
| **Tool Used** | `get_workout_data` |
| **Stateless Response** | "Yes, you did a 52-minute strength training workout yesterday." |
| **Stateful Response** | "Yes, you did a 52-minute strength training workout yesterday." |
| **Key Difference** | ✅ Both handle compound queries in single turn |

**Why they're the same**: Single-turn compound queries work for both.

---

## 5. Goal-Based Queries (Episodic Memory)

### Query: "Am I on track for my weight goal?"

| Aspect | Details |
|--------|---------|
| **Tool Used (Stateless)** | `get_health_metrics` only |
| **Tool Used (Stateful)** | `get_my_goals` (RedisVL) → `get_health_metrics` |
| **Memory Type** | None / Episodic (vector search) |
| **Stateless Response** | ❌ "I don't have information about your goals. What is your target weight?" |
| **Stateful Response** | ✅ "Your goal is 125 lbs by December. Current weight: 136.8 lbs. You've lost 8.2 lbs since September - you're making excellent progress!" |
| **Redis Keys** | `episodic:wellness_user:goal:1729962000` |
| **How Retrieved** | LLM autonomously calls `get_my_goals` tool |

**How It Works**:
```python
# Stateful agent workflow:
# 1. LLM sees query mentions "goal"
# 2. LLM autonomously calls get_my_goals tool
# 3. Tool uses RedisVL vector search to find goal
# 4. LLM calls get_health_metrics with current weight
# 5. LLM synthesizes comparison
```

---

### Query: "How close am I to my step goal?"

| Aspect | Details |
|--------|---------|
| **Tool Used (Stateless)** | `get_health_metrics` only |
| **Tool Used (Stateful)** | `get_my_goals` → `get_health_metrics` |
| **Memory Type** | Episodic |
| **Stateless Response** | ❌ "I need to know your step goal first. What's your daily target?" |
| **Stateful Response** | ✅ "Your goal is 10,000 steps daily. Today you have 8,432 steps - 84% of your goal with a few hours left!" |
| **Vector Search Query** | "step goal" → finds stored goal embedding |

**Redis Vector Search**:
```python
# RedisVL searches episodic memory:
query_embedding = ollama.embeddings.create(
    model="mxbai-embed-large",
    prompt="step goal"
)

results = redisvl_index.search(
    query_embedding,
    top_k=3,
    filter="@user_id:{wellness_user}"
)
# Returns: {"metric": "StepCount", "target": 10000, "unit": "steps"}
```

---

## 6. Pattern Learning (Procedural Memory)

### First Time Query: "Compare my activity this month vs last month"

| Aspect | Details |
|--------|---------|
| **Tool Used (Both)** | `get_workout_data` + `get_health_metrics` |
| **Memory Type** | None / Procedural (learning phase) |
| **Stateless Performance** | 2.8s (figures out tools each time) |
| **Stateful Performance** | 2.8s (first time, no pattern yet) |
| **Key Difference** | ✅ Same performance on first query |

---

### Same Query Asked Again: "Compare my activity this month vs last month"

| Aspect | Details |
|--------|---------|
| **Tool Used (Stateless)** | `get_workout_data` + `get_health_metrics` (figures out again) |
| **Tool Used (Stateful)** | `get_tool_suggestions` → retrieves pattern → uses same tools |
| **Memory Type** | None / Procedural (retrieval phase) |
| **Stateless Performance** | 2.8s (same as before) |
| **Stateful Performance** | 1.9s (pattern known, faster execution) |
| **Redis Key** | `procedural:pattern:1729962000` |
| **How Retrieved** | LLM calls `get_tool_suggestions` for similar queries |

**Procedural Memory Storage**:
```python
# After successful workflow, stateful agent stores:
{
    "query_type": "activity_comparison",
    "query": "Compare my activity this month vs last month",
    "tools_used": ["get_workout_data", "get_health_metrics"],
    "success_score": 0.95,
    "execution_time_ms": 2800,
    "embedding": <1024-dim vector>
}
```

---

### Query: "How has my workout frequency changed?"

| Aspect | Details |
|--------|---------|
| **Tool Used (Stateful 1st)** | `get_workout_data` (learns pattern) |
| **Tool Used (Stateful 2nd+)** | `get_tool_suggestions` → knows to use `get_workout_data` |
| **Memory Type** | Procedural |
| **Performance Improvement** | 32% faster on subsequent similar queries |

**Key Insight**: Stateful agent learns which tools work for which query types.

---

## 7. Multi-Turn Reasoning

### Conversation Flow

**Turn 1**: "What was my heart rate during workouts last week?"

| Aspect | Details |
|--------|---------|
| **Stateless** | "Your average workout heart rate last week was 142 bpm." |
| **Stateful** | "Your average workout heart rate last week was 142 bpm." |

---

**Turn 2**: "How does that compare to this week?"

| Aspect | Details |
|--------|---------|
| **Stateless** | ❌ "I need context. What are you comparing?" |
| **Stateful** | ✅ "This week your average workout heart rate is 156 bpm - 14 bpm higher (10% increase)." |

---

**Turn 3**: "Is the trend concerning?"

| Aspect | Details |
|--------|---------|
| **Stateless** | ❌ "I need more information. What trend are you referring to?" |
| **Stateful** | ✅ "This 10% increase isn't concerning if you intensified your workouts. Your data shows you replaced walking with cycling this week, which explains the higher heart rate. If your workout intensity didn't change, consider checking recovery and hydration." |

**Memory Used (Stateful)**:
- **Short-term**: All 3 conversation turns in context
- **Episodic**: User's heart rate goals (if set)
- **Procedural**: Similar comparison query patterns

---

## 8. Tool Chaining Examples

### Query: "Show me my workout pattern and tell me if I'm improving"

**Stateless Agent Workflow**:
1. ❌ Calls `get_workout_data` → retrieves workout list
2. ❌ Stops (no context to know user wants improvement analysis)
3. Response: "Here are your workouts over the past month: [lists 12 workouts]. What would you like to know about them?"

**Stateful Agent Workflow**:
1. ✅ Calls `get_workout_data` with pattern analysis
2. ✅ Sees pattern result, autonomously calls `get_workout_data` again for historical comparison
3. ✅ Calls `get_my_goals` to check if improvement aligns with goals
4. Response: "You work out most consistently on Fridays (24 workouts) and Mondays (18 workouts). Your frequency increased 50% this month (12 workouts vs 8 last month), which aligns with your goal of 3x per week. You're making excellent progress!"

| Aspect | Stateless | Stateful |
|--------|-----------|----------|
| **Tool Calls** | 1 (incomplete) | 3 (comprehensive) |
| **Context Used** | None | Conversation + Goals |
| **Response Quality** | Lists data | Analyzes + interprets |

**Key Difference**: Stateful agent chains tools autonomously to provide complete answer.

---

### Query: "What's my BMI and is it healthy for my goals?"

**Stateless Agent Workflow**:
1. Calls `get_health_metrics` (BMI)
2. Response: "Your BMI is 22.1 (normal range). Generally, BMI 18.5-24.9 is considered healthy."

**Stateful Agent Workflow**:
1. Calls `get_health_metrics` (BMI)
2. Autonomously calls `get_my_goals` (weight/BMI goals)
3. Response: "Your BMI is 22.1 (normal range). Based on your goal of reaching 125 lbs, your target BMI would be 20.8 - still in the healthy range. You're currently 11.8 lbs away from your goal."

| Aspect | Stateless | Stateful |
|--------|-----------|----------|
| **Goal Awareness** | ❌ None | ✅ Retrieves from episodic memory |
| **Personalization** | Generic health info | Tailored to user goals |

---

## 9. Intent Routing (Fast Path)

### Query: "My goal is to run 3 times per week"

| Aspect | Details |
|--------|---------|
| **Intent Router** | Detects goal-setting pattern |
| **Fast Path** | Bypasses LLM, direct Redis HSET |
| **Stateless Response** | "Goal noted (not stored - no memory)" |
| **Stateful Response** | "✅ Goal stored: Run 3x per week" |
| **Performance** | <100ms (no LLM call) |
| **Redis Key** | `episodic:wellness_user:goal:{timestamp}` |

**How Fast Path Works**:
```python
# Intent router regex match:
if re.search(r'\bgoal\b.*\bis\b', query, re.IGNORECASE):
    # Direct Redis operation (no LLM)
    redis.hset(goal_key, mapping={
        "user_id": "wellness_user",
        "goal": "Run 3x per week",
        "timestamp": time.time()
    })
    return "✅ Goal stored"
```

---

### Query: "What are my goals?"

| Aspect | Details |
|--------|---------|
| **Intent Router** | Detects goal-retrieval pattern |
| **Fast Path** | Direct Redis hash lookup |
| **Stateless Response** | "I don't store goals (no memory)" |
| **Stateful Response** | "Your goals: Weight 125 lbs by December, Run 3x/week, Sleep 7+ hours" |
| **Performance** | <100ms (no LLM, no vector search) |

---

## 10. Related Documentation

- **[03_STATELESS_AGENT.md](03_STATELESS_AGENT.md)** - How stateless agent works
- **[04_STATEFUL_AGENT.md](04_STATEFUL_AGENT.md)** - How stateful agent works
- **[05_TOOLS_AND_CALLING.md](05_TOOLS_AND_CALLING.md)** - Tool catalog and autonomous calling
- **[06_MEMORY_ARCHITECTURE.md](06_MEMORY_ARCHITECTURE.md)** - Four-layer memory system
- **[07_REDIS_PATTERNS.md](07_REDIS_PATTERNS.md)** - Redis data structures for AI
- **[02_THE_DEMO.md](02_THE_DEMO.md)** - Try these queries in the UI

---

**Key takeaway:** Memory transforms AI from isolated Q&A into intelligent conversation. Stateful agents remember context (short-term), recall goals (episodic), learn patterns (procedural), and chain tools autonomously to provide comprehensive answers.
