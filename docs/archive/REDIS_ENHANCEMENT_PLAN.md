# Redis Enhancement Implementation Plan

## Mission
Transform redis-wellness into a compelling demo that showcases Redis + RedisVL's capabilities for intelligent health conversations while making it reusable for any user.

## Goals
1. ✅ **Make it reusable** - Works for anyone's Apple Health data
2. ✅ **Intelligent conversations** - Natural health insights without manual analysis
3. ✅ **Take burden off Qwen** - Dynamic tools do data analysis, LLM formats responses
4. ✅ **Make Redis shine** - Showcase Redis/RedisVL's unique capabilities
5. ✅ **Never make stateless stateful** - Clear separation for demo comparison

---

## Phase 1: Dynamic Analysis Tools (Week 1)
**Goal**: Take counting/analysis burden off Qwen with pure-Python tools

### 1.1 Workout Pattern Analysis Tool

**File**: `backend/src/apple_health/query_tools/workout_patterns.py`

```python
@tool
def get_workout_schedule_analysis(days_back: int = 60):
    """
    Analyze workout schedule patterns from actual data.

    Returns:
    - Which days user actually works out (by frequency)
    - Workout consistency metrics
    - Weekly averages

    Use when user asks: "What days do I work out?" "How often do I exercise?"
    """
    # Get workouts from Redis
    workouts = fetch_workouts_from_redis(user_id, days_back)

    # Count by day_of_week (uses enriched field)
    from collections import Counter
    day_counts = Counter([w['day_of_week'] for w in workouts])

    # Calculate consistency (appeared in X% of weeks)
    weeks = days_back / 7
    regular_threshold = weeks * 0.4  # 40% of weeks = "regular"

    return {
        "period": f"last {days_back} days",
        "total_workouts": len(workouts),
        "workouts_per_week_avg": round(len(workouts) / weeks, 1),
        "day_frequency": dict(day_counts.most_common()),
        "regular_days": [day for day, count in day_counts.items()
                        if count >= regular_threshold],
        "most_common_day": day_counts.most_common(1)[0] if day_counts else None
    }
```

### 1.2 Workout Intensity Analysis Tool

**File**: `backend/src/apple_health/query_tools/workout_patterns.py`

```python
@tool
def analyze_workout_intensity_by_day(days_back: int = 60):
    """
    Compare workout intensity across different days of the week.

    Returns average duration and calories burned per day.

    Use when user asks: "What day do I work out harder?"
    "Which day has my longest workouts?"
    """
    workouts = fetch_workouts_from_redis(user_id, days_back)

    # Group by day_of_week
    from collections import defaultdict
    by_day = defaultdict(list)
    for w in workouts:
        by_day[w['day_of_week']].append(w)

    # Calculate averages per day
    intensity = {}
    for day, day_workouts in by_day.items():
        durations = [w['duration_minutes'] for w in day_workouts
                    if w.get('duration_minutes')]
        calories = [w['calories'] for w in day_workouts
                   if w.get('calories')]

        intensity[day] = {
            "count": len(day_workouts),
            "avg_duration_minutes": round(mean(durations), 1) if durations else 0,
            "avg_calories": round(mean(calories), 1) if calories else 0,
            "total_duration_minutes": round(sum(durations), 1) if durations else 0
        }

    # Sort by intensity (duration * frequency)
    sorted_days = sorted(
        intensity.items(),
        key=lambda x: x[1]['total_duration_minutes'],
        reverse=True
    )

    return {
        "period": f"last {days_back} days",
        "intensity_by_day": dict(sorted_days),
        "hardest_day": sorted_days[0][0] if sorted_days else None
    }
```

### 1.3 Progress Tracking Tool

**File**: `backend/src/apple_health/query_tools/progress_tracking.py`

```python
@tool
def get_workout_progress(
    compare_period1: str = "last_30_days",
    compare_period2: str = "previous_30_days"
):
    """
    Compare workout metrics between two time periods.

    Shows if user is improving: more workouts, longer duration, etc.

    Use when user asks: "Am I getting stronger?" "How's my progress?"
    """
    from utils.time_utils import parse_time_period

    # Parse periods
    start1, end1, desc1 = parse_time_period(compare_period1)
    start2, end2, desc2 = parse_time_period(compare_period2)

    # Get workouts for each period
    workouts1 = fetch_workouts_in_range(user_id, start1, end1)
    workouts2 = fetch_workouts_in_range(user_id, start2, end2)

    # Calculate metrics
    def calc_metrics(workouts):
        return {
            "count": len(workouts),
            "total_duration": sum(w['duration_minutes'] for w in workouts),
            "avg_duration": mean([w['duration_minutes'] for w in workouts]),
            "total_calories": sum(w.get('calories', 0) for w in workouts)
        }

    metrics1 = calc_metrics(workouts1)
    metrics2 = calc_metrics(workouts2)

    # Calculate changes
    def calc_change(new, old):
        if old == 0:
            return 0
        return round(((new - old) / old) * 100, 1)

    return {
        "period1": {"name": desc1, **metrics1},
        "period2": {"name": desc2, **metrics2},
        "changes": {
            "workout_count": calc_change(metrics1['count'], metrics2['count']),
            "avg_duration": calc_change(metrics1['avg_duration'], metrics2['avg_duration']),
            "total_duration": calc_change(metrics1['total_duration'], metrics2['total_duration']),
        },
        "trend": "improving" if metrics1['avg_duration'] > metrics2['avg_duration'] else "declining"
    }
```

### 1.4 Update Tool Registry

**File**: `backend/src/apple_health/query_tools/__init__.py`

```python
def create_user_bound_tools(user_id: str, conversation_history=None):
    """Create all tools bound to a specific user."""
    return [
        # Existing tools
        create_search_records_tool(user_id),
        create_search_workouts_tool(user_id),
        create_aggregate_metrics_tool(user_id),
        create_compare_periods_tool(user_id),
        create_weight_trends_tool(user_id),
        create_compare_activity_tool(user_id),

        # NEW: Pattern analysis tools
        create_workout_schedule_tool(user_id),
        create_intensity_analysis_tool(user_id),
        create_progress_tracking_tool(user_id),
    ]
```

**Deliverable**: Users can ask "What days do I work out?" and get accurate, consistent answers.

---

## Phase 2: Redis Aggregation Layer (Week 2)
**Goal**: Use Redis's speed instead of Python processing

### 2.1 Create Workout Indexes on Import

**File**: `backend/src/services/redis_workout_indexer.py`

```python
class WorkoutIndexer:
    """Index workouts in Redis for fast aggregation queries."""

    def index_workouts(self, user_id: str, workouts: list):
        """Create Redis indexes for workouts."""

        with redis_client.pipeline() as pipe:
            # Clear old indexes
            pipe.delete(f"user:{user_id}:workout:days")
            pipe.delete(f"user:{user_id}:workout:by_date")

            for workout in workouts:
                workout_id = f"{user_id}:{workout['date']}:{workout['type_cleaned']}"

                # 1. Count by day of week (Hash)
                pipe.hincrby(
                    f"user:{user_id}:workout:days",
                    workout['day_of_week'],
                    1
                )

                # 2. Sorted set by date (for time range queries)
                timestamp = datetime.fromisoformat(workout['startDate']).timestamp()
                pipe.zadd(
                    f"user:{user_id}:workout:by_date",
                    {workout_id: timestamp}
                )

                # 3. Store workout details (Hash)
                pipe.hset(
                    f"user:{user_id}:workout:{workout_id}",
                    mapping={
                        "date": workout['date'],
                        "day_of_week": workout['day_of_week'],
                        "type": workout['type_cleaned'],
                        "duration": workout.get('duration_minutes', 0),
                        "calories": workout.get('calories', 0)
                    }
                )

                # 4. TTL (7 months to match health data)
                pipe.expire(f"user:{user_id}:workout:{workout_id}", 210 * 24 * 60 * 60)

            pipe.execute()
```

### 2.2 Update Import to Build Indexes

**File**: `import_health.py` (add after storing main data)

```python
# After line 199: client.set(main_key, json.dumps(data))

# Build Redis indexes for fast queries
from backend.src.services.redis_workout_indexer import WorkoutIndexer
indexer = WorkoutIndexer(client)
indexer.index_workouts(user_id, data['workouts'])
print(f"✅ Built Redis indexes for fast queries")
```

### 2.3 Update Tools to Use Redis Aggregations

**File**: `backend/src/apple_health/query_tools/workout_patterns.py`

```python
@tool
def get_workout_schedule_analysis_fast(days_back: int = 60):
    """Get workout schedule using Redis aggregations (instant)."""

    # Use Redis hash to get counts by day (O(1))
    day_counts = redis_client.hgetall(f"user:{user_id}:workout:days")
    day_counts = {k.decode(): int(v) for k, v in day_counts.items()}

    # Get total workouts in time range using sorted set
    cutoff_ts = (datetime.now() - timedelta(days=days_back)).timestamp()
    workout_ids = redis_client.zrangebyscore(
        f"user:{user_id}:workout:by_date",
        cutoff_ts,
        '+inf'
    )

    return {
        "period": f"last {days_back} days",
        "total_workouts": len(workout_ids),
        "day_frequency": day_counts,
        "regular_days": [day for day, count in day_counts.items()
                        if count >= (days_back / 7) * 0.4]
    }
    # Redis query: ~1ms vs Python processing: ~50-100ms
```

**Deliverable**: Queries are 50-100x faster using Redis aggregations.

---

## Phase 3: RedisVL Semantic Search (Week 3)
**Goal**: Enable "find similar workouts" and semantic queries

### 3.1 Create Workout Semantic Index

**File**: `backend/src/services/redis_workout_semantic.py`

```python
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.schema import IndexSchema

class WorkoutSemanticSearch:
    """Semantic search over workout data using RedisVL."""

    def __init__(self, redis_url: str):
        self.schema = IndexSchema.from_dict({
            "index": {
                "name": "workout_idx",
                "prefix": "workout:semantic:",
            },
            "fields": [
                {
                    "name": "workout_id",
                    "type": "tag"
                },
                {
                    "name": "user_id",
                    "type": "tag"
                },
                {
                    "name": "workout_text",
                    "type": "text",
                    "attrs": {
                        "weight": 2.0  # Boost text relevance
                    }
                },
                {
                    "name": "embedding",
                    "type": "vector",
                    "attrs": {
                        "dims": 1024,  # mxbai-embed-large
                        "algorithm": "hnsw",
                        "distance_metric": "cosine"
                    }
                },
                {
                    "name": "date",
                    "type": "tag"
                },
                {
                    "name": "day_of_week",
                    "type": "tag"
                },
                {
                    "name": "type",
                    "type": "tag"
                },
                {
                    "name": "duration",
                    "type": "numeric"
                },
                {
                    "name": "calories",
                    "type": "numeric"
                }
            ]
        })

        self.index = SearchIndex(schema=self.schema, redis_url=redis_url)
        self.index.create(overwrite=False)

    def index_workouts(self, user_id: str, workouts: list, embedder):
        """Add workouts to semantic index."""

        documents = []
        for workout in workouts:
            # Create searchable text
            text = f"{workout['type_cleaned']} workout on {workout['day_of_week']}, {workout.get('duration_minutes', 0)} minutes"
            if workout.get('calories'):
                text += f", {workout['calories']} calories burned"

            # Generate embedding
            embedding = embedder.embed(text)

            doc = {
                "workout_id": f"{user_id}:{workout['date']}:{workout['type_cleaned']}",
                "user_id": user_id,
                "workout_text": text,
                "embedding": embedding,
                "date": workout['date'],
                "day_of_week": workout['day_of_week'],
                "type": workout['type_cleaned'],
                "duration": workout.get('duration_minutes', 0),
                "calories": workout.get('calories', 0)
            }
            documents.append(doc)

        # Batch load
        self.index.load(documents)

    def search_similar_workouts(
        self,
        user_id: str,
        reference_workout_id: str,
        limit: int = 5
    ):
        """Find workouts similar to a reference workout."""

        # Get reference workout embedding
        ref_doc = self.index.fetch(reference_workout_id)
        ref_embedding = ref_doc['embedding']

        # Vector search with user filter
        query = VectorQuery(
            vector=ref_embedding,
            vector_field_name="embedding",
            return_fields=["workout_id", "workout_text", "date", "type", "duration"],
            num_results=limit,
            filter_expression=f"@user_id:{{{user_id}}}"
        )

        results = self.index.query(query)
        return results

    def semantic_workout_search(
        self,
        user_id: str,
        query_text: str,
        embedder,
        limit: int = 10
    ):
        """Semantic search for workouts matching query."""

        # Embed query
        query_embedding = embedder.embed(query_text)

        # Vector search
        query = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            return_fields=["workout_text", "date", "day_of_week", "duration", "calories"],
            num_results=limit,
            filter_expression=f"@user_id:{{{user_id}}}"
        )

        results = self.index.query(query)
        return results
```

### 3.2 Update Import to Build Semantic Index

**File**: `import_health.py`

```python
# After building Redis indexes

# Build semantic search index
from backend.src.services.redis_workout_semantic import WorkoutSemanticSearch
from backend.src.services.embedding_cache import get_embedding_service

semantic_search = WorkoutSemanticSearch(f"redis://{redis_host}:{redis_port}")
embedder = get_embedding_service()

print("\n📊 Building semantic search index...")
semantic_search.index_workouts(user_id, data['workouts'], embedder)
print(f"✅ Indexed {len(data['workouts'])} workouts for semantic search")
```

### 3.3 Create Semantic Search Tools

**File**: `backend/src/apple_health/query_tools/semantic_search.py`

```python
@tool
def find_similar_workouts(reference_date: str, reference_type: str, limit: int = 5):
    """
    Find workouts similar to a specific workout using semantic search.

    Use when user asks: "Find workouts like my best Monday session"
    "Show me similar strength training workouts"
    """
    from services.redis_workout_semantic import WorkoutSemanticSearch

    search = WorkoutSemanticSearch(redis_url)
    workout_id = f"{user_id}:{reference_date}:{reference_type}"

    results = search.search_similar_workouts(user_id, workout_id, limit)

    return {
        "reference": f"{reference_type} on {reference_date}",
        "similar_workouts": [
            {
                "date": r['date'],
                "type": r['type'],
                "duration": r['duration'],
                "similarity_score": r['vector_score']
            }
            for r in results
        ]
    }

@tool
def semantic_workout_query(query: str, limit: int = 10):
    """
    Search workouts using natural language.

    Use when user asks: "Find my most intense workouts"
    "Show workouts where I pushed really hard"
    """
    from services.redis_workout_semantic import WorkoutSemanticSearch
    from services.embedding_cache import get_embedding_service

    search = WorkoutSemanticSearch(redis_url)
    embedder = get_embedding_service()

    results = search.semantic_workout_search(user_id, query, embedder, limit)

    return {
        "query": query,
        "matches": [
            {
                "date": r['date'],
                "day_of_week": r['day_of_week'],
                "description": r['workout_text'],
                "duration": r['duration'],
                "relevance_score": r['vector_score']
            }
            for r in results
        ]
    }
```

**Deliverable**: Users can ask "Find my hardest workouts" and get semantically ranked results.

---

## Phase 4: Enhanced System Prompt (Week 4)
**Goal**: Guide Qwen to use tools effectively

### 4.1 Update System Prompt

**File**: `backend/src/utils/agent_helpers.py`

```python
def build_base_system_prompt() -> str:
    return """You are a health recovery assistant with Redis-powered memory and intelligent data analysis.

🎯 YOUR ROLE:
- Help users understand their health data and recovery progress
- Use tools to analyze data - don't try to count or calculate yourself
- Be direct and concise - answer the exact question asked

🔧 AVAILABLE TOOLS:

**Workout Schedule & Patterns:**
- get_workout_schedule_analysis → "What days do I work out?"
- analyze_workout_intensity_by_day → "What day do I work out harder?"
- search_workouts_and_activity → Individual workout details

**Progress & Trends:**
- get_workout_progress → "Am I improving?" "How's my progress?"
- compare_time_periods_tool → Compare specific metrics between periods
- calculate_weight_trends_tool → Weight loss/gain trends

**Semantic Search:**
- semantic_workout_query → "Find my hardest workouts" "Most intense sessions"
- find_similar_workouts → "Find workouts like my best one"

**Health Metrics:**
- search_health_records_by_metric → Individual readings (weight, heart rate, etc.)
- aggregate_metrics → Statistical analysis (average, min, max)

⚡ CRITICAL RULES:

1. **Pattern Questions** → Use analysis tools:
   - "What days do I work out?" → get_workout_schedule_analysis
   - "What day is hardest?" → analyze_workout_intensity_by_day
   - DON'T try to count manually from workout lists

2. **Progress Questions** → Use progress tools:
   - "Am I improving?" → get_workout_progress
   - "How do I compare to last month?" → get_workout_progress

3. **Search Questions** → Use semantic search:
   - "Find my best workouts" → semantic_workout_query
   - "Show similar sessions" → find_similar_workouts

4. **Be Direct:**
   - Answer in 1-3 sentences unless detail requested
   - State findings clearly: "You work out on Monday, Wednesday, and Friday"
   - Don't list all data unless asked

5. **Use Memory:**
   - Remember surgery/injury context from conversation
   - Reference past progress when relevant
   - Build on previous answers

💾 MEMORY ADVANTAGE:
- Redis stores your conversation context and semantic memory
- You can reference past discussions about goals, injuries, progress
- Use this context to provide personalized insights

🚫 DON'T:
- Count records manually - use analysis tools
- List all workouts when asked for patterns
- Ignore available tools and try to analyze yourself
- Make up data - only report what tools return

Example:
User: "What days do I work out?"
✅ GOOD: [Call get_workout_schedule_analysis] → "You work out on Monday, Wednesday, and Friday (9, 6, and 8 times respectively in the last 60 days)"
❌ BAD: [List all workouts] → "October 17 Friday, October 15 Wednesday..."
"""
```

**Deliverable**: Qwen knows which tools to use and how to format responses.

---

## Phase 5: Testing & Documentation (Week 5)

### 5.1 Create Test Suite

**File**: `backend/tests/test_redis_enhancements.py`

```python
def test_workout_schedule_analysis():
    """Test pattern analysis returns accurate day counts."""
    result = get_workout_schedule_analysis(days_back=90)
    assert "day_frequency" in result
    assert "regular_days" in result
    assert result["total_workouts"] > 0

def test_redis_aggregations():
    """Test Redis indexes return same results as Python."""
    python_result = get_workout_schedule_analysis(days_back=60)
    redis_result = get_workout_schedule_analysis_fast(days_back=60)
    assert python_result["total_workouts"] == redis_result["total_workouts"]

def test_semantic_search():
    """Test RedisVL semantic search returns relevant results."""
    results = semantic_workout_query("intense strength training", limit=5)
    assert len(results["matches"]) > 0
    # All results should be strength training
    assert all("Strength" in r["description"] for r in results["matches"])

def test_stateless_remains_stateless():
    """Ensure stateless chat doesn't access Redis memory."""
    # Stateless should only use tools, no memory access
    response = stateless_agent.chat("What days do I work out?")
    assert "memory_stats" not in response
```

### 5.2 Create Demo Script

**File**: `docs/DEMO_SCRIPT.md`

```markdown
# Redis Wellness Demo Script

## Setup (30 seconds)
1. Start services: `./start.sh`
2. Verify: http://localhost:3000

## Demo Flow (5 minutes)

### Part 1: Stateless Chat Limitations (1 min)
```
User: "I'm recovering from a collarbone injury in April"
Stateless: "I understand. How can I help with your recovery?"

User: "What days do I work out?"
Stateless: "Monday, Wednesday, and Friday"

User: "Am I getting stronger since my injury?"
Stateless: ❌ "I don't have context about your injury timeline"
```
*Point: Stateless forgets context between messages*

### Part 2: Redis-Powered Memory (2 min)
```
User: "I'm recovering from a collarbone injury in April"
Redis Chat: ✅ [Stores in semantic memory] "I'll track your recovery progress."

User: "What days do I work out?"
Redis Chat: "Monday, Wednesday, and Friday consistently"

User: "Am I getting stronger since my injury?"
Redis Chat: ✅ "Yes! Since April, your average workout duration increased 15% (from 32 to 38 minutes) and you're maintaining 3x/week consistency."
```
*Point: Redis remembers and connects context*

### Part 3: Redis Speed & Intelligence (2 min)

**Fast Aggregations:**
```
User: "Compare my last 12 weeks week-by-week"
→ Redis aggregations return instantly (< 10ms)
→ Shows: Weeks 1-4: 2.5 workouts/week → Weeks 9-12: 3.2 workouts/week
```

**Semantic Search:**
```
User: "Find my most intense strength training sessions"
→ RedisVL semantic search ranks by intensity
→ Returns: Top 5 workouts with similarity scores
```

**Pattern Recognition:**
```
User: "What day do I push hardest?"
→ Analysis tool: "Monday workouts average 45 min vs 38 min overall"
```

## Key Talking Points
1. **Redis Speed**: Sub-millisecond aggregations on 255K records
2. **RedisVL Semantic Search**: Understands "intense" means long + high calories
3. **Dual Memory**: Short-term (conversation) + Long-term (semantic)
4. **Privacy**: 100% local with Ollama - no data leaves your machine
5. **Reusable**: Upload your own Apple Health data and try it
```

### 5.3 Update Main Documentation

**File**: `docs/README.md`

Update architecture diagram to show:
- Redis indexes (hashes, sorted sets)
- RedisVL semantic layer
- Dual memory system (conversation + semantic)
- Tool calling flow with dynamic analysis

**Deliverable**: Demo is reliable, repeatable, and impressive.

---

## Success Metrics

### Before Enhancements
- ❌ "What days do I work out?" → Inconsistent answers
- ❌ Pattern queries require LLM counting
- ❌ No semantic search capability
- ❌ Redis used only for simple storage

### After Enhancements
- ✅ "What days do I work out?" → Consistent, accurate every time
- ✅ Pattern analysis done by Redis/Python (instant)
- ✅ Semantic search: "Find my hardest workouts" works
- ✅ Redis showcases: speed, aggregations, vector search, memory
- ✅ Reusable for any user's data

---

## Implementation Checklist

### Week 1: Dynamic Tools
- [ ] Create `workout_patterns.py` with 3 analysis tools
- [ ] Create `progress_tracking.py` with trend analysis
- [ ] Update tool registry to include new tools
- [ ] Test: "What days do I work out?" returns consistent answer
- [ ] Test: "What day do I work out harder?" returns accurate ranking

### Week 2: Redis Aggregations
- [ ] Create `redis_workout_indexer.py`
- [ ] Update `import_health.py` to build indexes
- [ ] Create fast versions of tools using Redis queries
- [ ] Benchmark: Verify 50-100x speedup
- [ ] Test: Redis results match Python results

### Week 3: RedisVL Semantic
- [ ] Create `redis_workout_semantic.py` with SearchIndex
- [ ] Update import to build semantic index
- [ ] Create `semantic_search.py` tools
- [ ] Test: "Find my hardest workouts" returns relevant results
- [ ] Test: "Find similar workouts" ranks by semantic similarity

### Week 4: System Prompt
- [ ] Update `agent_helpers.py` with enhanced prompt
- [ ] Add tool selection guidance
- [ ] Test: Qwen consistently chooses correct tools
- [ ] Test: Responses are concise and accurate

### Week 5: Testing & Demo
- [ ] Create test suite for all enhancements
- [ ] Write demo script with talking points
- [ ] Update architecture documentation
- [ ] Record demo video
- [ ] Test with fresh Apple Health data upload

---

## Maintenance

### When Users Upload New Data
All enhancements are automatic:
1. `import_health.py` parses XML
2. Enriches data (day_of_week, etc.)
3. Builds Redis indexes
4. Builds RedisVL semantic index
5. Ready for queries immediately

### Adding New Tools
Follow the pattern:
1. Create tool in `query_tools/`
2. Use Redis aggregations where possible
3. Add to tool registry
4. Update system prompt with usage guidance
5. Add tests

### Monitoring Redis Performance
```bash
# Check index sizes
redis-cli INFO memory

# Check semantic index status
redis-cli FT.INFO workout_idx

# Monitor query performance
redis-cli SLOWLOG GET 10
```

---

## Notes

- **Never touch stateless agent** - All enhancements are Redis-specific
- **Data quality first** - Enrichment ensures tools have clean data to analyze
- **Tools over prompts** - Better to create a tool than write a long prompt
- **Redis everywhere** - Showcase Redis at every opportunity (speed, search, memory)
- **Reusability** - Every tool works for any user's data, no hardcoding
