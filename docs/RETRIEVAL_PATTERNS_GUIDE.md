# Retrieval Patterns Guide: Semantic Search vs Simple Retrieval

This document explains **when the system uses semantic search (RedisVL)** vs **simple retrieval** based on question types.

## Quick Reference

| Memory Type | Storage | Retrieval Method | Use Case |
|------------|---------|------------------|----------|
| **Episodic** | RedisVL (vector) | Semantic search | User goals, preferences, events |
| **Semantic** | RedisVL (vector) | Semantic search | General health knowledge |
| **Procedural** | Redis Hash | Simple lookup | Tool calling patterns |
| **Short-term** | Redis List | Simple read | Recent conversation |
| **Health Data** | Redis indexes | Simple query | Factual metrics |

## Your Available Health Metrics

Based on your actual imported data:
- **ActiveEnergyBurned** - Calories burned through activity
- **BodyMass** - Weight measurements
- **BodyMassIndex** - BMI calculations
- **DietaryEnergyConsumed** - Calories consumed
- **DietaryWater** - Water intake
- **DistanceWalkingRunning** - Distance traveled
- **HeartRate** - Heart rate measurements
- **Height** - Height measurements
- **SleepAnalysis** - Sleep tracking
- **StepCount** - Daily step counts
- **Workouts** - Exercise sessions

---

## 1. Semantic Search (RedisVL Vector Search)

Uses **vector embeddings** and **cosine similarity** to find semantically related content.

### Episodic Memory (User Goals & Preferences)

**When Used**: Questions about personal goals, preferences, or past user statements

**Storage**: `episodic:{user_id}:{event_type}:{timestamp}` (RedisVL hash with vector embedding)

**Retrieval**: Vector similarity search with filters

**Sample Questions**:
```
✅ "What's my weight goal?"
✅ "Am I on track with my fitness target?"
✅ "What BMI am I aiming for?"
✅ "What was my step count target for this month?"
✅ "How many workouts per week did I want to do?"
✅ "What's my target daily calorie intake?"
✅ "Did I set a goal for water consumption?"
✅ "What's my target resting heart rate?"
```

**Why Semantic**: You can ask the same question many different ways:
- "What's my target weight?" vs "How much do I want to weigh?" vs "What weight am I shooting for?"
- All map to the same stored goal via embeddings

---

### Semantic Memory (General Health Knowledge)

**When Used**: Questions requiring general medical/health facts (not user-specific)

**Storage**: `semantic:{category}:{fact_type}:{timestamp}` (RedisVL hash with vector embedding)

**Retrieval**: Vector similarity search with optional category filters

**Sample Questions**:
```
✅ "What's a normal resting heart rate?"
✅ "How is BMI calculated?"
✅ "What's considered moderate cardio intensity?"
✅ "Explain active energy vs basal metabolic rate"
✅ "What are healthy blood pressure ranges?"
✅ "How much sleep should I get per night?"
✅ "What's a healthy daily step count?"
✅ "How many calories should I burn per day?"
```

**Why Semantic**: Medical facts can be expressed many ways:
- "What's normal heart rate?" vs "Typical resting pulse range?" vs "Healthy BPM values?"
- All should retrieve the same fact: "60-100 bpm"

---

## 2. Simple Retrieval (No Vector Search)

Uses **direct Redis operations** (read, scan, query) without embeddings.

### Short-Term Memory (Conversation History)

**When Used**: Always - for maintaining conversation context

**Storage**: `health_chat_session:{session_id}` (Redis LIST)

**Retrieval**: Simple list read (`LRANGE`)

**Sample Questions**:
```
✅ "Is that good?" (after asking about heart rate)
✅ "What about last month?" (continuing a comparison)
✅ "Can you explain that in more detail?"
✅ "Show me the breakdown"
✅ "Why did it increase?"
✅ "How does that compare?"
```

**Why Simple**: Chronological order, recent messages, no semantic matching needed

---

### Health Data (Direct Tool Queries)

**When Used**: All factual health metric queries (tool-first policy)

**Storage**: Redis indexes and sorted sets

**Retrieval**: Direct Redis queries (no embeddings)

**Sample Questions Based on Your Actual Data**:

**Heart Rate:**
```
✅ "What was my heart rate on October 20?"
✅ "What's my average heart rate this week?"
✅ "Show my resting heart rate today"
✅ "What was my max heart rate during my last workout?"
✅ "Is my heart rate trending up or down?"
```

**Steps & Distance:**
```
✅ "How many steps did I take yesterday?"
✅ "Average steps last week"
✅ "Total distance walked this month"
✅ "Compare my steps now vs last month"
✅ "What day did I walk the most?"
```

**Weight & BMI:**
```
✅ "What's my current weight?"
✅ "What was my weight on September 1?"
✅ "Show my weight trend over the last 3 months"
✅ "What's my BMI today?"
✅ "Compare my BMI now vs 6 months ago"
```

**Calories & Energy:**
```
✅ "How many active calories did I burn yesterday?"
✅ "What's my average daily calorie burn?"
✅ "Total calories consumed this week"
✅ "How much water did I drink yesterday?"
✅ "Compare calories burned vs consumed today"
```

**Sleep:**
```
✅ "How many hours did I sleep last night?"
✅ "What's my average sleep duration this week?"
✅ "Show my sleep patterns for the past month"
✅ "What night did I sleep the longest?"
```

**Workouts:**
```
✅ "What workouts did I do last week?"
✅ "How many workouts this month?"
✅ "Show my running workouts from October"
✅ "What was my longest workout?"
✅ "Total workout time this week"
```

**Why Simple**:
- Exact metric names (HeartRate, Steps, BodyMass)
- Exact date ranges
- Fast O(1) or O(log N) lookups
- No ambiguity - no need for semantic matching

---

## Decision Flow

```
┌─────────────────────────────────────┐
│      You ask a question             │
└─────────────────┬───────────────────┘
                  ↓
         Does it ask for factual data?
         (metrics, dates, numbers)
                  ↓
              ┌───YES → Tool-First (Simple Retrieval)
              │         - search_health_records
              │         - aggregate_health_metrics
              │         - Direct Redis queries
              │         - No embeddings needed
              │
              NO
              ↓
         Does it reference goals/preferences?
         (personal context)
                  ↓
              ┌───YES → Episodic Memory (Semantic Search)
              │         - Generate query embedding
              │         - Vector search with user_id filter
              │         - Return top_k matches
              │
              NO
              ↓
         Does it ask general health knowledge?
         (medical facts, definitions)
                  ↓
              ┌───YES → Semantic Memory (Semantic Search)
              │         - Generate query embedding
              │         - Vector search (optional category filter)
              │         - Return general facts
              │
              NO
              ↓
         Does it reference previous conversation?
         ("that", "it", follow-ups)
                  ↓
              YES → Short-Term Memory (Simple Retrieval)
                    - LRANGE recent messages
                    - No embeddings needed
```

---

## Real Examples by Pattern

### Pattern 1: Pure Semantic (Episodic)
```
Q: "What's my target weight?"
→ Episodic memory (semantic search)
→ Vector search for "weight goal"
→ Returns: "User's weight goal is 125 lbs"
```

### Pattern 2: Pure Simple (Health Data)
```
Q: "What was my heart rate yesterday?"
→ Tool: search_health_records
→ Direct Redis query: health:user:wellness_user:metric:HeartRate
→ Returns: [65, 72, 88, 95, 78, ...]
```

### Pattern 3: Hybrid (Tool + Episodic)
```
Q: "Am I on track with my weight goal?"
→ Tool: search_health_records (current weight from BodyMass)
→ Episodic: retrieve_goals (target weight via semantic search)
→ Compare: 130 lbs current vs 125 lbs target
→ Returns: "You're 5 lbs from your goal, making good progress"
```

### Pattern 4: Simple Follow-up (Short-Term)
```
Q1: "What was my average heart rate last week?"
A1: "87 bpm"

Q2: "Is that good?"
→ Short-term memory (simple list read)
→ Retrieves: "87 bpm" from previous message
→ Returns: "87 bpm is within normal range for adults (60-100 bpm)"
```

### Pattern 5: Multi-step Hybrid
```
Q: "How's my progress toward my step goal this week?"
→ Episodic: retrieve_goals (semantic search: "step goal" → "10,000 steps/day")
→ Tool: aggregate_health_metrics (simple query: StepCount for past 7 days)
→ Tool: compare_metrics (calculate average and compare)
→ Returns: "You're averaging 8,500 steps/day, 85% of your 10k goal"
```

### Pattern 6: Complex Multi-Metric
```
Q: "Am I in a calorie deficit this week?"
→ Tool: aggregate_health_metrics (DietaryEnergyConsumed - sum for 7 days)
→ Tool: aggregate_health_metrics (ActiveEnergyBurned - sum for 7 days)
→ Calculate: Burned - Consumed
→ Returns: "You burned 2,800 more calories than consumed this week, averaging 400/day deficit"
```

---

## Concrete Question Examples by Category

### Use Semantic Search (Episodic - Your Goals)
```
"What's my weight goal?"
"Am I meeting my workout frequency target?"
"What step count was I aiming for?"
"What's my target BMI?"
"How many workouts per week did I want to do?"
"What's my calorie intake goal?"
"Did I set a water consumption target?"
```

### Use Semantic Search (General Knowledge)
```
"What's a normal resting heart rate?"
"How is BMI calculated?"
"What are healthy sleep ranges?"
"Explain heart rate zones"
"What's a good daily step count?"
"How many calories should I burn?"
"What's a healthy BMI range?"
```

### Use Simple Retrieval (Your Actual Metrics)
```
"What was my heart rate on October 20?"
"Average steps last week"
"Total active calories this month"
"How much did I weigh on September 1?"
"How many hours did I sleep last night?"
"What workouts did I do yesterday?"
"How much water did I drink today?"
"Compare my weight now vs 3 months ago"
"Is my step count trending up or down?"
"What's my BMI today?"
"Total distance walked this week"
```

### Use Simple Retrieval (Conversation Follow-ups)
```
"Is that good?" (after any metric)
"What about last month?"
"Can you break that down?"
"Why did it change?"
"Show me more detail"
"How does that compare to my goal?"
```

---

## Performance Characteristics

### Semantic Search (RedisVL)
- **Latency**: ~50-100ms (embedding generation + vector search)
- **Accuracy**: High for similar phrasing
- **Storage**: Hash + 1024-dimensional vector per memory
- **Best For**: Open-ended questions, varied phrasing

### Simple Retrieval
- **Latency**: ~1-10ms (direct Redis operations)
- **Accuracy**: Exact match only
- **Storage**: Minimal (just data, no embeddings)
- **Best For**: Exact lookups, chronological data, factual queries

---

## Summary Table

| Question Type | Example | Memory Type | Retrieval | Embedding? |
|--------------|---------|-------------|-----------|------------|
| Personal goal | "What's my weight goal?" | Episodic | Semantic | ✅ Yes |
| Health fact | "What's normal heart rate?" | Semantic | Semantic | ✅ Yes |
| Metric value | "Heart rate yesterday?" | Tools | Simple | ❌ No |
| Follow-up | "Is that good?" | Short-term | Simple | ❌ No |
| Tool pattern | (Learning) | Procedural | Simple | ❌ No |

---

## See Also

- `/backend/src/services/episodic_memory_manager.py` - Episodic (semantic search)
- `/backend/src/services/semantic_memory_manager.py` - Semantic (semantic search)
- `/backend/src/services/short_term_memory_manager.py` - Short-term (simple retrieval)
- `/backend/src/services/procedural_memory_manager.py` - Procedural (simple lookup)
- `/backend/src/apple_health/query_tools/` - Health data tools (simple queries)
- `/docs/03_MEMORY_ARCHITECTURE.md` - Complete memory architecture
