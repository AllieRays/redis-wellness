# Tools, Services & Utils Reference

## 1. Overview

This document provides a comprehensive reference for every tool, service, and utility in the redis-wellness codebase. Each component is categorized by its role in the architecture.

**Key Point**: The codebase follows clean architecture principles with clear separation of concerns.

### What You'll Learn

- **[Query Tools](#2-query-tools)** - LangChain tools callable by AI agents
- **[Services](#3-services)** - Data layer and business logic
- **[Utils](#4-utils)** - Pure utilities and helpers
- **[Component Relationships](#5-component-relationships)** - How everything fits together

---

## 2. Query Tools

**Location**: `backend/src/apple_health/query_tools/`

LangChain-compatible tools that AI agents can invoke. These are the only functions directly callable by the LLM.

### 2.1 Health Data Tools

#### `get_health_metrics.py` {#get-health-metrics}

[📄 View source](../backend/src/apple_health/query_tools/get_health_metrics.py)

**Purpose**: Query all non-sleep, non-workout health data (heart rate, steps, weight, BMI, blood pressure, etc.)

**Capabilities**:
- Single metric queries: "What was my heart rate yesterday?"
- Multi-metric queries: "Show me my weight and BMI this week"
- Time-based queries: "What's my average steps in October?"
- Trend analysis: "Is my heart rate improving?"
- Raw data vs. aggregated views

**When Used**: Any query about health metrics that isn't sleep or workouts

**Example Queries**:
```
"What was my resting heart rate last week?"
"Show me my weight trend for the past month"
"Did my blood pressure improve?"
```

---

#### `get_sleep_analysis.py` {#get-sleep-analysis}

[📄 View source](../backend/src/apple_health/query_tools/get_sleep_analysis.py)

**Purpose**: Query sleep data with daily aggregation and efficiency metrics

**Capabilities**:
- Sleep duration queries: "How much did I sleep last night?"
- Sleep quality metrics: "What's my sleep efficiency?"
- Date range analysis: "Show me my sleep patterns this month"
- Daily aggregation: Combines all sleep sessions per day
- Efficiency calculation: Time asleep / time in bed

**When Used**: Any query about sleep patterns, quality, or duration

**Example Queries**:
```
"How many hours did I sleep last night?"
"What's my average sleep efficiency this week?"
"When did I have the best sleep?"
```

---

#### `get_workout_data.py` {#get-workout-data}

[📄 View source](../backend/src/apple_health/query_tools/get_workout_data.py)

**Purpose**: **ALL** workout-related queries (consolidated tool)

**Capabilities**:
- List workouts: "Show me my workouts this week"
- Workout patterns: "What day do I work out most?"
- Progress tracking: "Am I working out more?"
- Type-specific queries: "How many runs this month?"
- Comparisons: "Compare my workouts to last month"
- Detailed metrics: Duration, calories, heart rate zones

**When Used**: Any query about exercise, workouts, or activity patterns

**Example Queries**:
```
"How many workouts do I have?"
"What's my most common workout day?"
"Did I work out on October 17th?"
"Compare my cardio vs strength training"
```

**Note**: This is a consolidated tool that replaced multiple smaller workout tools for better LLM reasoning.

---

### 2.2 Memory Tools

#### `memory_tools.py` {#memory-tools}

[📄 View source](../backend/src/apple_health/query_tools/memory_tools.py)

Contains two memory retrieval tools:

##### `get_my_goals()` {#get-my-goals}

**Purpose**: Retrieve user goals and important facts from episodic memory

**Capabilities**:
- Semantic search across stored goals
- Cross-session recall: "What did I say yesterday?"
- Goal tracking: "What's my weight goal?"
- Vector similarity matching

**When Used**: User asks about their goals, preferences, or previously stated facts

**Example Queries**:
```
"What's my fitness goal?"
"What did I tell you about my sleep goal?"
"Am I on track for my December target?"
```

---

##### `get_tool_suggestions()` {#get-tool-suggestions}

**Purpose**: Retrieve successful workflow patterns from procedural memory

**Capabilities**:
- Pattern matching: Find similar past queries
- Tool recommendations: "What tools worked before?"
- Query optimization: Speed up complex queries (32% faster)
- Learning from history

**When Used**: Agent encounters complex multi-step queries

**Example Queries**:
```
"Compare my activity this month vs last month"
→ Retrieves pattern showing get_workout_data + get_health_metrics works
```

**Note**: This tool is called internally by the agent, not directly by users.

---

## 3. Services

**Location**: `backend/src/services/`

Business logic layer that sits between API endpoints and Redis. Services handle data transformation, caching, and complex operations.

### 3.1 Chat Services

#### `stateless_chat.py` {#stateless-chat}

[📄 View source](../backend/src/services/stateless_chat.py)

**Purpose**: Baseline chat service with NO memory

**What It Does**:
- Simple tool-calling loop (no LangGraph)
- No conversation history
- No session persistence
- Each query is independent
- Demonstrates "before Redis" baseline

**Used By**: `/api/chat/stateless` endpoint

**Key Method**: `process_message(message: str) -> dict`

---

#### `redis_chat.py` {#redis-chat}

[📄 View source](../backend/src/services/redis_chat.py)

**Purpose**: Full RAG chat service with four-layer memory architecture

**What It Does**:
- LangGraph StateGraph workflow with checkpointing
- Short-term memory: Conversation history (7 months TTL)
- Episodic memory: User goals and facts (permanent)
- Procedural memory: Workflow patterns (permanent)
- Semantic memory: Optional health knowledge (permanent)
- Streaming support via SSE

**Used By**: `/api/chat/stateful` endpoint

**Key Method**: `process_message(message: str, session_id: str) -> dict`

**Memory Flow**:
1. Load conversation history (short-term)
2. Vector search for goals (episodic)
3. Vector search for patterns (procedural)
4. Vector search for facts (semantic)
5. Execute tools with full context
6. Store new memories automatically

---

### 3.2 Memory Services

#### `episodic_memory_manager.py` {#episodic-memory-manager}

[📄 View source](../backend/src/services/episodic_memory_manager.py)

**Purpose**: Manage user goals and important facts (RedisVL vector search)

**What It Does**:
- Store goals: `store_event(user_id, description, metadata)`
- Retrieve goals: `retrieve_events(query, top_k=3)`
- Vector similarity search using HNSW index
- 1024-dimensional embeddings (mxbai-embed-large)
- Cross-session persistence

**Storage Pattern**:
```python
# Redis key: episodic:user_id:goal:timestamp
{
    "user_id": "wellness_user",
    "event_type": "goal",
    "timestamp": 1729962000,
    "description": "Weight goal is 125 lbs by December",
    "metadata": {"metric": "weight", "value": 125},
    "embedding": [0.234, -0.123, ...]  # 1024 dimensions
}
```

**Used By**: `redis_chat.py`, `memory_tools.py`

---

#### `procedural_memory_manager.py` {#procedural-memory-manager}

[📄 View source](../backend/src/services/procedural_memory_manager.py)

**Purpose**: Track successful workflow patterns (RedisVL vector search)

**What It Does**:
- Store patterns: `store_pattern(query, tools_used, success_score)`
- Retrieve patterns: `get_suggestions(query, top_k=3)`
- Learn from successful tool combinations
- Speed up similar future queries (32% faster)
- Vector similarity for pattern matching

**Storage Pattern**:
```python
# Redis key: procedural:pattern:timestamp
{
    "query": "Compare activity this month vs last",
    "query_type": "comparison",
    "tools_used": ["get_workout_data", "get_health_metrics"],
    "success_score": 0.95,
    "execution_time_ms": 2800,
    "embedding": [0.456, -0.234, ...]  # 1024 dimensions
}
```

**Used By**: `redis_chat.py`, `memory_tools.py`

---

#### `semantic_memory_manager.py` {#semantic-memory-manager}

[📄 View source](../backend/src/services/semantic_memory_manager.py)

**Purpose**: Optional long-term domain knowledge (RedisVL vector search)

**What It Does**:
- Store facts: `store_memory(text, category, metadata)`
- Retrieve facts: `retrieve_memories(query, top_k=5)`
- General health knowledge (not user-specific)
- Example: "Normal resting heart rate is 60-100 bpm"

**Storage Pattern**:
```python
# Redis key: semantic:category:timestamp
{
    "text": "Normal resting heart rate is 60-100 bpm",
    "category": "health_metrics",
    "source": "medical_reference",
    "embedding": [0.789, -0.456, ...]  # 1024 dimensions
}
```

**Used By**: `redis_chat.py`

**Note**: Currently optional - not heavily used in demo.

---

### 3.3 Redis Data Services

#### `redis_connection.py` {#redis-connection}

[📄 View source](../backend/src/services/redis_connection.py)

**Purpose**: Production-ready Redis connection management

**What It Does**:
- Connection pooling with health checks
- Automatic reconnection on failure
- Exponential backoff retry logic
- Connection validation (PING)
- Resource cleanup on shutdown

**Used By**: All services that need Redis access

**Key Methods**:
- `get_redis_sync()` - Synchronous Redis client
- `get_redis_async()` - Async Redis client
- `health_check()` - Verify connection

---

#### `redis_apple_health_manager.py` {#redis-apple-health-manager}

[📄 View source](../backend/src/services/redis_apple_health_manager.py)

**Purpose**: CRUD operations for Apple Health data in Redis

**What It Does**:
- Store health records: `store_health_record(record)`
- Store workouts: `store_workout(workout)`
- Store sleep data: `store_sleep_analysis(sleep)`
- Retrieve by date range: `get_health_data(start, end, metric_type)`
- Efficient Redis Hash storage
- 7-month TTL on all health data

**Storage Patterns**:
```python
# Health metrics: health:HeartRate:2024-10-20
# Workouts: workout:2024-10-20T14:30:00
# Sleep: sleep:2024-10-20
```

**Used By**: Import script, query tools

---

#### `redis_workout_indexer.py` {#redis-workout-indexer}

[📄 View source](../backend/src/services/redis_workout_indexer.py)

**Purpose**: Fast O(1) workout aggregations using Redis indexes

**What It Does**:
- Pre-compute workout counts by date
- Pre-compute workout counts by type
- Pre-compute workout counts by day-of-week
- Instant lookups: "How many workouts this week?" → O(1)
- Automatic index updates on data import

**Index Patterns**:
```python
# workouts:count:2024-10-20 → 2
# workouts:by_type:Running → 45
# workouts:by_dow:Friday → 18
# workouts:by_month:2024-10 → 23
```

**Used By**: `get_workout_data.py` tool

**Performance**: Reduces complex aggregation queries from O(n) to O(1)

---

#### `redis_sleep_indexer.py` {#redis-sleep-indexer}

[📄 View source](../backend/src/services/redis_sleep_indexer.py)

**Purpose**: Fast sleep data aggregation and daily summaries

**What It Does**:
- Aggregate multiple sleep sessions per day
- Pre-compute sleep efficiency (asleep / in_bed)
- Store daily sleep summaries
- Handle overlapping sleep sessions
- Efficient date range queries

**Index Patterns**:
```python
# sleep:daily:2024-10-20 → {duration: 28800, efficiency: 0.92}
# sleep:range:2024-10 → [date1, date2, ...]
```

**Used By**: `get_sleep_analysis.py` tool

---

#### `embedding_service.py` {#embedding-service}

[📄 View source](../backend/src/services/embedding_service.py)

**Purpose**: Embedding generation and caching

**What It Does**:
- Generate embeddings: `generate_embedding(text)`
- Cache embeddings: Avoids redundant Ollama calls
- Uses mxbai-embed-large (1024 dimensions)
- Batch embedding support
- Connection pooling to Ollama

**Used By**: All memory services for vector search

**Performance**: Caching reduces embedding calls by ~60%

---

## 4. Utils

**Location**: `backend/src/utils/`

Pure utilities and helper functions. These should have NO side effects and NO external dependencies (except math/logic).

### 4.1 Agent Helpers

#### `agent_helpers.py` {#agent-helpers}

[📄 View source](../backend/src/utils/agent_helpers.py)

**Purpose**: Shared utilities for both agents

**What It Does**:
- LLM client initialization: `get_llm_client()`
- System prompt management: `get_system_prompt()`
- Message formatting: `format_messages()`
- Response parsing: `parse_llm_response()`
- Tool binding: `bind_tools_to_llm()`

**Used By**: `stateless_agent.py`, `stateful_rag_agent.py`

---

### 4.2 Validation Utils

#### `numeric_validator.py` {#numeric-validator}

[📄 View source](../backend/src/utils/numeric_validator.py)

**Purpose**: LLM hallucination detection for numeric values

**What It Does**:
- Validate numeric claims against source data
- Detect fabricated statistics
- Flag impossible values (e.g., 500 bpm heart rate)
- Cross-reference tool outputs with final response

**Example**:
```python
# LLM says: "Your average heart rate was 87 bpm"
# Tool returned: {avg_heart_rate: 72}
# Validator: ⚠️ Hallucination detected - correcting to 72 bpm
```

**Used By**: Both agents after LLM generates response

**Reduces Hallucinations**: ~40% reduction in numeric errors

---

#### `date_validator.py` {#date-validator}

[📄 View source](../backend/src/utils/date_validator.py)

**Purpose**: Validate and normalize date ranges

**What It Does**:
- Parse natural language dates: "last week", "October", "yesterday"
- Validate date ranges: Ensure start < end
- Detect impossible dates: "February 30th"
- Convert to ISO format
- Handle timezone issues

**Used By**: All query tools

---

#### `validation_retry.py` {#validation-retry}

[📄 View source](../backend/src/utils/validation_retry.py)

**Purpose**: Retry logic with validation for LLM calls

**What It Does**:
- Retry failed LLM calls with exponential backoff
- Validate structured outputs (JSON, tool calls)
- Provide better error messages to LLM
- Max 3 retries before giving up

**Used By**: Agent workflows

---

### 4.3 Data Fetching Utils

#### `workout_fetchers.py` {#workout-fetchers}

[📄 View source](../backend/src/utils/workout_fetchers.py)

**Purpose**: Fetch workout data from Redis indexes

**What It Does**:
- Fetch by date range: `get_workouts_by_date_range(start, end)`
- Fetch by type: `get_workouts_by_type(workout_type)`
- Fetch by day-of-week: `get_workouts_by_dow(day)`
- Use pre-computed indexes (O(1) lookups)

**Used By**: `get_workout_data.py` tool

---

#### `metric_aggregators.py` {#metric-aggregators}

[📄 View source](../backend/src/utils/metric_aggregators.py)

**Purpose**: Aggregate health metrics (average, min, max, trends)

**What It Does**:
- Calculate averages: `calculate_average(values)`
- Find min/max: `find_extremes(values)`
- Compute trends: `calculate_trend(time_series)`
- Statistical summaries: Mean, median, std dev
- Handle missing data gracefully

**Used By**: `get_health_metrics.py`, `get_sleep_analysis.py`

---

#### `sleep_aggregator.py` {#sleep-aggregator}

[📄 View source](../backend/src/utils/sleep_aggregator.py)

**Purpose**: Aggregate multiple sleep sessions into daily summaries

**What It Does**:
- Combine overlapping sleep sessions
- Calculate total sleep per day
- Compute sleep efficiency: asleep / in_bed
- Handle naps and main sleep separately
- Daily aggregation logic

**Used By**: `get_sleep_analysis.py` tool

---

### 4.4 Analysis Utils

#### `health_analytics.py` {#health-analytics}

[📄 View source](../backend/src/utils/health_analytics.py)

**Purpose**: Health trend analysis and insights

**What It Does**:
- Detect trends: Improving, declining, stable
- Compare time periods: This week vs last week
- Identify anomalies: Unusual values
- Calculate percentiles: "You're in the top 20%"
- Health score calculations

**Used By**: All health query tools

---

#### `stats_utils.py` {#stats-utils}

[📄 View source](../backend/src/utils/stats_utils.py)

**Purpose**: Statistical calculation utilities

**What It Does**:
- Mean, median, mode
- Standard deviation, variance
- Percentiles and quartiles
- Moving averages
- Correlation analysis

**Used By**: `health_analytics.py`, `metric_aggregators.py`

---

### 4.5 NLP Utils

#### `intent_router.py` {#intent-router}

[📄 View source](../backend/src/utils/intent_router.py)

**Purpose**: Route user intents to appropriate tools

**What It Does**:
- Classify query type: Health, sleep, workout, goal, comparison
- Determine which tools to invoke
- Handle multi-intent queries
- Bypass semantic memory for factual queries (tool-first policy)

**Used By**: `redis_chat.py` service

**Example**:
```python
# "Show me my workouts and sleep this week"
# → Routes to: [get_workout_data, get_sleep_analysis]
```

---

#### `intent_bypass_handler.py` {#intent-bypass-handler}

[📄 View source](../backend/src/utils/intent_bypass_handler.py)

**Purpose**: Detect queries that should skip semantic memory

**What It Does**:
- Identify factual queries: "How many workouts?"
- Skip semantic cache for fresh data
- Implement "tool-first policy"
- Prevent stale data responses

**Used By**: `redis_chat.py` service

**Rationale**: Factual queries need fresh data from tools, not cached semantic memory.

---

#### `pronoun_resolver.py` {#pronoun-resolver}

[📄 View source](../backend/src/utils/pronoun_resolver.py)

**Purpose**: Resolve pronouns using conversation context

**What It Does**:
- Replace "it" with the actual reference
- Handle "that", "this", "those" references
- Use short-term memory for context
- Improve query clarity for tools

**Example**:
```
User: "What was my heart rate?"
Agent: "72 bpm"
User: "Is that good?"
→ Resolves to: "Is 72 bpm heart rate good?"
```

**Used By**: Both agents before processing query

---

#### `conversation_fact_extractor.py` {#conversation-fact-extractor}

[📄 View source](../backend/src/utils/conversation_fact_extractor.py)

**Purpose**: Extract important facts from conversations for semantic memory

**What It Does**:
- Identify goals: "My target is..."
- Identify preferences: "I prefer..."
- Identify important facts: "I have..."
- Convert to storeable format
- Filter noise

**Used By**: `redis_chat.py` after each response

---

#### `verbosity_detector.py` {#verbosity-detector}

[📄 View source](../backend/src/utils/verbosity_detector.py)

**Purpose**: Detect user preference for verbose vs. concise responses

**What It Does**:
- Analyze query complexity
- Detect "explain", "why", "how" keywords
- Default to concise for simple queries
- Adjust response length accordingly

**Used By**: Both agents when generating responses

---

### 4.6 Classification Utils

#### `metric_classifier.py` {#metric-classifier}

[📄 View source](../backend/src/utils/metric_classifier.py)

**Purpose**: Classify health metrics into categories

**What It Does**:
- Categorize metrics: Cardiovascular, activity, body, nutrition
- Map Apple Health types to categories
- Normalize metric names
- Handle aliases (e.g., "HR" → "HeartRate")

**Used By**: `get_health_metrics.py` tool

**Example Categories**:
- Cardiovascular: HeartRate, BloodPressure, VO2Max
- Activity: Steps, Distance, Calories, Exercise
- Body: Weight, BMI, BodyFat, Height
- Nutrition: Protein, Carbs, Fats, Water

---

#### `workout_helpers.py` {#workout-helpers}

[📄 View source](../backend/src/utils/workout_helpers.py)

**Purpose**: Workout type classification and normalization

**What It Does**:
- Normalize workout names: "Running" vs "Run"
- Group workout types: Cardio, strength, flexibility
- Calculate workout intensity
- Map HKWorkoutActivityType to readable names

**Used By**: `get_workout_data.py` tool

---

### 4.7 Time Utils

#### `time_utils.py` {#time-utils}

[📄 View source](../backend/src/utils/time_utils.py)

**Purpose**: Time parsing and date utilities

**What It Does**:
- Parse natural language dates: "last week", "October", "yesterday"
- Convert between timezones
- Calculate date ranges
- ISO 8601 formatting
- Handle relative dates: "3 days ago"

**Used By**: All query tools, date_validator.py

---

### 4.8 Conversion Utils

#### `conversion_utils.py` {#conversion-utils}

[📄 View source](../backend/src/utils/conversion_utils.py)

**Purpose**: Unit conversion utilities

**What It Does**:
- Convert distance: Miles ↔ Kilometers
- Convert weight: Pounds ↔ Kilograms
- Convert temperature: Fahrenheit ↔ Celsius
- Convert calories: kcal ↔ kJ
- Handle imperial/metric display preferences

**Used By**: All health query tools

---

### 4.9 Redis Utils

#### `redis_keys.py` {#redis-keys}

[📄 View source](../backend/src/utils/redis_keys.py)

**Purpose**: Centralized Redis key management

**What It Does**:
- Generate consistent Redis keys
- Namespace management: `health:`, `workout:`, `episodic:`
- Key pattern documentation
- Prevent key collisions

**Pattern Examples**:
```python
# Health: health:{metric_type}:{date}
# Workouts: workout:{iso_timestamp}
# Sleep: sleep:{date}
# Episodic: episodic:{user_id}:goal:{timestamp}
# Procedural: procedural:pattern:{timestamp}
# Semantic: semantic:{category}:{timestamp}
```

**Used By**: All services that interact with Redis

---

### 4.10 Tool Utils

#### `tool_deduplication.py` {#tool-deduplication}

[📄 View source](../backend/src/utils/tool_deduplication.py)

**Purpose**: Prevent duplicate tool calls in single query

**What It Does**:
- Track tool calls within request
- Prevent redundant calls with same parameters
- Cache tool results for request lifetime
- Improve performance (avoid duplicate work)

**Example**:
```python
# LLM wants to call get_workout_data twice with same params
# → Second call uses cached result
```

**Used By**: Agent tool execution loops

---

### 4.11 Management Utils

#### `token_manager.py` {#token-manager}

[📄 View source](../backend/src/utils/token_manager.py)

**Purpose**: Token counting and management

**What It Does**:
- Count tokens in messages
- Estimate API costs
- Enforce context window limits (8192 tokens for Qwen)
- Truncate messages if needed

**Used By**: Both agents

---

#### `user_config.py` {#user-config}

[📄 View source](../backend/src/utils/user_config.py)

**Purpose**: User configuration and preferences

**What It Does**:
- Load user preferences: Units, timezone, verbosity
- Store display preferences
- Handle defaults
- Configuration validation

**Used By**: All query tools (for display formatting)

---

### 4.12 Error Handling Utils

#### `exceptions.py` {#exceptions}

[📄 View source](../backend/src/utils/exceptions.py)

**Purpose**: Custom exception classes

**What It Does**:
- Define domain-specific exceptions
- Structured error messages
- Error codes for frontend
- Inheritance hierarchy

**Exception Types**:
- `HealthDataNotFoundError`
- `InvalidDateRangeError`
- `RedisConnectionError`
- `OllamaConnectionError`
- `ToolExecutionError`

**Used By**: All services and tools

---

#### `api_errors.py` {#api-errors}

[📄 View source](../backend/src/utils/api_errors.py)

**Purpose**: API error handling and formatting

**What It Does**:
- Convert exceptions to HTTP responses
- Error logging
- User-friendly error messages
- Stack trace sanitization (don't leak internals)

**Used By**: API endpoints

---

#### `base.py` {#base}

[📄 View source](../backend/src/utils/base.py)

**Purpose**: Base classes and decorators

**What It Does**:
- `@retry` decorator for resilience
- `@log_execution` decorator for debugging
- `BaseService` class with common methods
- `BaseManager` class for memory managers

**Used By**: All services and managers

---

## 5. Component Relationships

### 5.1 Data Flow

```
User Query
    ↓
API Endpoint (chat_routes.py)
    ↓
Service (redis_chat.py or stateless_chat.py)
    ↓
Agent (stateful_rag_agent.py or stateless_agent.py)
    ↓
┌─────────────────────────────────────────┐
│  Agent decides which tools to call      │
│  - Uses intent_router.py                │
│  - Uses pronoun_resolver.py             │
│  - Uses tool_deduplication.py           │
└─────────────────────────────────────────┘
    ↓
Query Tools (apple_health/query_tools/)
    ↓
┌─────────────────────────────────────────┐
│  Tools use utils to fetch/process data  │
│  - workout_fetchers.py                  │
│  - metric_aggregators.py                │
│  - health_analytics.py                  │
│  - time_utils.py                        │
└─────────────────────────────────────────┘
    ↓
Services (redis_apple_health_manager.py, redis_workout_indexer.py)
    ↓
Redis (via redis_connection.py)
    ↓
Tool returns structured data
    ↓
Agent synthesizes response (uses numeric_validator.py)
    ↓
Service adds memory stats
    ↓
API returns to user
```

---

### 5.2 Memory Flow

```
User Message
    ↓
redis_chat.py service
    ↓
┌─────────────────────────────────────────────────────┐
│  Load Memories (before LLM sees message)            │
│  1. Short-term: LangGraph checkpointer (automatic)  │
│  2. Episodic: episodic_memory_manager.py            │
│  3. Procedural: procedural_memory_manager.py        │
│  4. Semantic: semantic_memory_manager.py (optional) │
└─────────────────────────────────────────────────────┘
    ↓
Agent processes with full context
    ↓
Agent generates response
    ↓
┌─────────────────────────────────────────────────────┐
│  Store Memories (after response generated)          │
│  1. Short-term: LangGraph auto-saves                │
│  2. Extract facts: conversation_fact_extractor.py   │
│  3. Store goals: episodic_memory_manager.py         │
│  4. Store patterns: procedural_memory_manager.py    │
└─────────────────────────────────────────────────────┘
    ↓
Return response + memory_stats to user
```

---

### 5.3 Tool Execution Flow

```
Agent receives: "What was my heart rate last week?"
    ↓
intent_router.py → Classifies as "health_metric_query"
    ↓
Agent calls: get_health_metrics(metric="HeartRate", start="2024-10-13", end="2024-10-20")
    ↓
get_health_metrics.py:
    ↓
    1. date_validator.py validates dates
    2. metric_classifier.py normalizes "HeartRate"
    3. redis_apple_health_manager.py fetches raw data from Redis
    4. metric_aggregators.py calculates average
    5. health_analytics.py detects trends
    6. conversion_utils.py formats for display
    ↓
Returns: {"avg": 72, "min": 65, "max": 88, "trend": "stable"}
    ↓
Agent synthesizes: "Your average heart rate was 72 bpm..."
    ↓
numeric_validator.py verifies 72 matches tool output ✅
    ↓
Response sent to user
```

---

## 6. Quick Reference Tables

### Tools Summary

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `get_health_metrics` | All non-sleep, non-workout health data | metric, start, end | Aggregated metrics + trends |
| `get_sleep_analysis` | Sleep data with efficiency | start, end | Daily sleep summaries |
| `get_workout_data` | ALL workout queries | start, end, type, patterns | Workout list + patterns |
| `get_my_goals` | Retrieve user goals | query | Relevant goals from episodic memory |
| `get_tool_suggestions` | Retrieve workflow patterns | query | Relevant patterns from procedural memory |

---

### Services Summary

| Service | Purpose | Key Methods |
|---------|---------|-------------|
| `stateless_chat` | Baseline no-memory chat | `process_message(message)` |
| `redis_chat` | Full RAG chat with 4-layer memory | `process_message(message, session_id)` |
| `episodic_memory_manager` | User goals and facts | `store_event()`, `retrieve_events()` |
| `procedural_memory_manager` | Workflow patterns | `store_pattern()`, `get_suggestions()` |
| `semantic_memory_manager` | Domain knowledge | `store_memory()`, `retrieve_memories()` |
| `redis_connection` | Redis connection management | `get_redis_sync()`, `get_redis_async()` |
| `redis_apple_health_manager` | Health data CRUD | `store_health_record()`, `get_health_data()` |
| `redis_workout_indexer` | Workout indexes (O(1) queries) | `index_workout()`, `get_workout_count()` |
| `redis_sleep_indexer` | Sleep aggregation | `index_sleep()`, `get_daily_summary()` |
| `embedding_service` | Embedding generation + cache | `generate_embedding(text)` |

---

### Utils Summary (by Category)

#### Agent & Workflow
- `agent_helpers.py` - LLM setup, prompts, message formatting
- `tool_deduplication.py` - Prevent duplicate tool calls
- `validation_retry.py` - Retry logic for LLM calls

#### Validation
- `numeric_validator.py` - Detect LLM hallucinations
- `date_validator.py` - Validate and normalize dates

#### Data Fetching
- `workout_fetchers.py` - Fetch workouts from indexes
- `metric_aggregators.py` - Aggregate health metrics
- `sleep_aggregator.py` - Aggregate sleep sessions

#### Analysis
- `health_analytics.py` - Trend analysis, insights
- `stats_utils.py` - Statistical calculations

#### NLP
- `intent_router.py` - Route queries to tools
- `intent_bypass_handler.py` - Skip semantic memory for factual queries
- `pronoun_resolver.py` - Resolve "it", "that", etc.
- `conversation_fact_extractor.py` - Extract facts for memory
- `verbosity_detector.py` - Detect verbose vs. concise preference

#### Classification
- `metric_classifier.py` - Classify health metrics
- `workout_helpers.py` - Classify workout types

#### Utilities
- `time_utils.py` - Date parsing, formatting
- `conversion_utils.py` - Unit conversions
- `redis_keys.py` - Centralized key management
- `token_manager.py` - Token counting
- `user_config.py` - User preferences

#### Error Handling
- `exceptions.py` - Custom exception classes
- `api_errors.py` - API error formatting
- `base.py` - Base classes, decorators

---

## 7. Related Documentation

- **[02_QUICKSTART.md](02_QUICKSTART.md)** - Get started quickly
- **[06_AGENTIC_RAG.md](06_AGENTIC_RAG.md)** - How tools are called by agents
- **[10_MEMORY_ARCHITECTURE.md](10_MEMORY_ARCHITECTURE.md)** - Four-layer memory system
- **[11_REDIS_PATTERNS.md](11_REDIS_PATTERNS.md)** - Redis usage patterns
- **[13_AUTONOMOUS_AGENTS.md](13_AUTONOMOUS_AGENTS.md)** - Agent decision-making

---

**Key Takeaway**: The codebase follows clean architecture with clear boundaries:
- **Tools** = LLM-callable functions (LangChain tools)
- **Services** = Business logic and data layer (Redis operations)
- **Utils** = Pure functions (no side effects, no external dependencies)

This separation ensures testability, maintainability, and clear data flow throughout the system.
