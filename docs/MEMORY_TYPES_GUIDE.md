# Memory Types Guide

A comprehensive guide to understanding the different memory types in the stateful RAG health application.

## Memory Types Comparison

| Memory Type | Purpose | Duration | Storage | Example |
|------------|---------|----------|---------|---------|
| **Episodic** | Personal events, goals, context about YOUR data | Long-term (months/years) | RedisVL vector index | "I started a new workout routine on Oct 1st" |
| **Procedural** | Learned behaviors, preferences, successful patterns | Long-term (persistent) | RedisVL vector index | User asks "show weekly trends" 3x → Agent learns: default to weekly aggregation |
| **Semantic** | General health knowledge, medical facts, formulas | Long-term (universal) | RedisVL vector index | "Normal resting heart rate is 60-100 bpm" |
| **Conversation** | Recent dialogue context, references, follow-ups | Short-term (session) | LangGraph checkpointing | "What about yesterday?" (after asking about today) |
| **Tools** | Raw Apple Health data queries | N/A (stateless) | Redis indexes | "Show me my step count for Oct 15th" |

---

## Questions → Memory Type Examples

### Episodic Memory (Personal context about YOUR data)

| Question You'd Ask | What Gets Stored | Why Episodic |
|-------------------|------------------|--------------|
| "I'm trying to hit 8000 steps daily" | Goal: 8000 steps/day, started 2025-10-24 | Personal goal with timeline |
| "I was sick last week with the flu" | Event: Flu Oct 14-20, expect low activity | Context explaining data anomaly |
| "I started strength training on Mondays" | Routine change: Started Mon workouts Oct 1 | Behavior change affecting patterns |
| "Ignore my sleep data from the wedding weekend" | Exception: Oct 12-13 invalid sleep data | User-provided data quality note |
| "I want to lose 5 pounds by December" | Goal: Weight 5 lbs down by Dec 31, 2025 | Weight goal with deadline |
| "I switched from iPhone to Apple Watch for tracking" | Device change: Watch tracking started Oct 10 | Explains data discontinuity |

---

### Procedural Memory (How YOU like answers)

**Note:** Procedural memory can be stored two ways:
1. **Explicit**: User directly states a preference ("Always show me X")
2. **Learned**: Agent observes repeated patterns and infers behavior (user asks for weekly trends 3 times → agent learns to default to weekly)

| Question You'd Ask | What Gets Stored | Why Procedural |
|-------------------|------------------|--------------|
| "Always show me weekly averages, not daily" | Preference: Weekly aggregation default | Explicit communication style preference |
| "Compare my workouts month-over-month" (asked 3x) | Pattern: This user compares monthly trends → default to monthly | Learned from repeated query pattern |
| "Keep answers under 3 sentences" | Preference: Brief responses | Explicit response length preference |
| "Show me step count AND distance together" (works well, repeats) | Tool chain: steps → distance when steps queried | Learned successful tool sequence |
| "I prefer metric units" | Preference: kg not lbs, km not miles | Explicit unit system preference |
| "Don't round my weight, show decimals" | Preference: Precision over readability | Explicit data display preference |

---

### Semantic Memory (General health knowledge)

| Question You'd Ask | What Gets Stored | Why Semantic |
|-------------------|------------------|--------------|
| "What's a healthy resting heart rate?" | Knowledge: RHR 60-100 bpm is normal | Universal health fact |
| "How many steps should I aim for daily?" | Knowledge: 7000-10000 steps/day recommended | General wellness guideline |
| "What counts as moderate exercise?" | Knowledge: 50-70% max HR, 3+ METs | Exercise definition |
| "How much water should I drink daily?" | Knowledge: ~2L/day or 0.5 oz per lb bodyweight | Hydration guideline |
| "What's the formula for BMI?" | Knowledge: weight(kg) / height(m)² | Medical calculation |
| "How long should a good workout be?" | Knowledge: 30+ min moderate, 150 min/week | CDC/WHO guidelines |

---

### Conversation History (Recent chat context)

| Question You'd Ask | Stored in LangGraph Checkpoint | Why Conversational |
|-------------------|-------------------------------|-------------------|
| "What was my step count yesterday?" → "How about the day before?" | Last exchange about steps | Anaphora ("the day before") |
| "Show me my workouts this week" → "Which one burned the most calories?" | Recent workout query + results | Reference ("which one") |
| "My average heart rate is 72" → "Is that good?" | Recent HR fact mentioned | Reference ("that") |
| "I walked 12k steps today" → "Was that more than usual?" | Recent step count claim | Comparison to just-stated value |

---

### Tools (Raw data queries—same across all memory types)

These hit Redis directly, no memory needed:

- "What was my total distance walked last week?"
- "Show me all my workouts in October 2025"
- "What's my average heart rate over the last 30 days?"
- "How many calories did I burn yesterday?"
- "What was my step count on October 15th?"

---

## Key Insight

**Episodic ≠ Raw Apple Health Data**

Your Apple Health XML data (heart rate readings, step counts, workouts) lives in **Redis indexes** and is accessed via **tools**.

**Episodic memory** stores the *context* around that data—the "why" behind the numbers that isn't in the XML:

- "I was training for a 5K in September 2025" ← explains why workouts spiked
- "I injured my ankle on Oct 1st" ← explains why steps dropped

**The raw numbers live in Redis. The *meaning* of those numbers lives in episodic memory.**

---

## Storage in Redis/RedisVL

```
Episodic:    redisvl_index:episodic → vector embeddings
                                      "2025-10-15: Started new med,
                                       expect HR changes"

Procedural:  redisvl_index:procedural → vector embeddings
                                        "User prefers 90-day trends"

Semantic:    redisvl_index:semantic → vector embeddings
                                      "Normal RHR: 60-100 bpm"

Conversation: langraph:checkpoint:{thread_id} → managed by LangGraph
                                                (last N messages)

Tools:       Pure functions → query Redis health data directly
```
