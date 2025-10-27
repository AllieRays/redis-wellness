# Redis Usage Patterns

**Complete reference for all Redis usage in redis-wellness project**

This document catalogs every way Redis is being used in the codebase, with real code examples extracted from the actual implementation.

---

## Table of Contents

1. [LangGraph Checkpointing (Conversation History)](#1-langgraph-checkpointing-conversation-history)
2. [Episodic Memory (Goals with RedisVL)](#2-episodic-memory-goals-with-redisvl)
3. [Semantic Memory (Health Knowledge with RedisVL)](#3-semantic-memory-health-knowledge-with-redisvl)
4. [Procedural Memory (Tool Patterns with RedisVL)](#4-procedural-memory-tool-patterns-with-redisvl)
5. [Workout Indexing (Aggregations)](#5-workout-indexing-aggregations)
6. [Health Data Storage](#6-health-data-storage)
7. [Connection Management](#7-connection-management)

---

## 1. LangGraph Checkpointing (Conversation History)

**Purpose**: Store conversation state/history automatically via LangGraph's AsyncRedisSaver

**Location**: `backend/src/services/redis_connection.py`

**Redis Structure**: Managed internally by LangGraph (likely `checkpoint:*` keys)

### Real Code Example

```python
# From redis_connection.py lines 255-300
async def get_checkpointer(self):
    """
    Get LangGraph checkpointer using Redis for persistence.

    CRITICAL: Uses Redis-based storage for conversation history.
    This ensures conversations persist across container restarts.

    Returns a checkpointer that stays open for the agent's lifetime.
    Uses direct initialization (not context manager) to avoid auto-close.
    """
    if self._checkpointer:
        return self._checkpointer

    try:
        # Use AsyncRedisSaver with direct initialization
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver

        # Build Redis connection URL
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        redis_password = os.getenv("REDIS_PASSWORD")

        # Build connection URL with optional password
        if redis_password:
            redis_url = (
                f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
            )
        else:
            redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

        # ✅ Direct initialization (connection stays open for agent lifetime)
        # AsyncRedisSaver uses its own built-in serializer
        self._checkpointer = AsyncRedisSaver(redis_url=redis_url)
        await self._checkpointer.asetup()

        logger.info("✅ AsyncRedisSaver initialized (conversations WILL persist)")
        return self._checkpointer

    except ImportError as e:
        logger.error(f"Failed to import AsyncRedisSaver: {e}")
        logger.error("   Install with: pip install langgraph-checkpoint-redis")
        raise
    except Exception as e:
        logger.error(f"Failed to create Redis checkpointer: {e}")
        raise
```

### Usage in Agent

```python
# From redis_chat.py lines 48-78
async def _ensure_agent_initialized(self) -> None:
    """
    Lazy async initialization of agent with AsyncRedisSaver checkpointer.

    The agent is initialized with:
    - checkpointer: AsyncRedisSaver for conversation state persistence
    - episodic_memory: User goals and preferences storage
    - procedural_memory: Learned tool-calling patterns
    """
    if self._agent is not None:
        return

    # Get checkpointer asynchronously
    checkpointer = await self.redis_manager.get_checkpointer()

    # Create agent with all CoALA memory components
    self._agent = StatefulRAGAgent(
        checkpointer=checkpointer,
        episodic_memory=self.episodic_memory,
        procedural_memory=self.procedural_memory,
    )
```

**Key Pattern**: LangGraph manages the conversation state automatically. You pass `session_id` to the agent, and it uses that as the thread ID for persistence.

---

## 2. Episodic Memory (Goals with RedisVL)

**Purpose**: Store user-specific goals and preferences with vector search

**Location**: `backend/src/services/episodic_memory_manager.py`

**Redis Structure**:
- Key pattern: `episodic:{user_id}:goal:{timestamp}`
- Storage type: Redis Hash with vector embeddings
- Index: RedisVL HNSW vector index

### Real Code: Index Initialization

```python
# From episodic_memory_manager.py lines 46-104
def _initialize_index(self) -> None:
    """Create RedisVL index for episodic memory."""
    try:
        schema = IndexSchema.from_dict(
            {
                "index": {
                    "name": RedisKeys.EPISODIC_MEMORY_INDEX,
                    "prefix": RedisKeys.EPISODIC_PREFIX,
                    "storage_type": "hash",
                },
                "fields": [
                    {"name": "user_id", "type": "tag"},
                    {
                        "name": "event_type",
                        "type": "tag",
                    },  # "goal", "preference", etc.
                    {"name": "timestamp", "type": "numeric"},
                    {
                        "name": "description",
                        "type": "text",
                    },  # "User's weight goal is 125 lbs"
                    {
                        "name": "metadata",
                        "type": "text",
                    },  # JSON: {"metric": "weight", "value": 125, "unit": "lbs"}
                    {
                        "name": "embedding",
                        "type": "vector",
                        "attrs": {
                            "dims": 1024,
                            "distance_metric": "cosine",
                            "algorithm": "hnsw",
                            "datatype": "float32",
                        },
                    },
                ],
            }
        )

        self.episodic_index = SearchIndex(schema=schema)

        # Connect to Redis using centralized utility
        redis_url = get_redis_url(
            host=self.settings.redis_host,
            port=self.settings.redis_port,
            db=self.settings.redis_db,
        )
        self.episodic_index.connect(redis_url)

        # Create index (don't overwrite if exists)
        try:
            self.episodic_index.create(overwrite=False)
            logger.info("📊 Created episodic memory index")
        except Exception:
            logger.info("📊 Episodic memory index already exists")

    except Exception as e:
        logger.error(f"❌ Failed to initialize episodic index: {e}")
        self.episodic_index = None
```

### Real Code: Storing Goals

```python
# From episodic_memory_manager.py lines 106-176
async def store_goal(
    self,
    user_id: str,
    metric: str,
    value: float | int,
    unit: str,
) -> bool:
    """
    Store a user goal in episodic memory.

    Example:
        await store_goal(user_id="wellness_user", metric="weight", value=125, unit="lbs")
        # Stores: "User's weight goal is 125 lbs" with embedding
    """
    if not self.episodic_index:
        logger.error("Episodic index not initialized")
        return False

    try:
        # Create description for embedding
        description = f"User's {metric} goal is {value} {unit}"

        # Generate embedding
        embedding = await self.embedding_service.generate_embedding(description)
        if embedding is None:
            logger.error("Failed to generate embedding for goal")
            return False

        # Create memory record using centralized utilities
        timestamp = get_utc_timestamp()
        memory_key = RedisKeys.episodic_memory(user_id, "goal", timestamp)

        metadata = {
            "metric": metric,
            "value": value,
            "unit": unit,
        }

        memory_data = {
            "user_id": user_id,
            "event_type": "goal",
            "timestamp": timestamp,
            "description": description,
            "metadata": json.dumps(metadata),
            "embedding": np.array(embedding, dtype=np.float32).tobytes(),
        }

        # Store in Redis
        with self.redis_manager.get_connection() as redis_client:
            redis_client.hset(memory_key, mapping=memory_data)
            # Set TTL (7 months)
            redis_client.expire(memory_key, self.settings.redis_session_ttl_seconds)

        logger.info(f"💾 Stored goal: {description}")
        return True

    except Exception as e:
        logger.error(f"❌ Goal storage failed: {e}", exc_info=True)
        raise MemoryStorageError(
            memory_type="episodic",
            reason=f"Failed to store goal: {str(e)}",
        ) from e
```

### Real Code: Retrieving Goals (Vector Search)

```python
# From episodic_memory_manager.py lines 178-271
async def retrieve_goals(
    self,
    user_id: str,
    query: str,
    top_k: int = 3,
) -> dict[str, Any]:
    """
    Retrieve user goals via semantic search.

    Example:
        result = await retrieve_goals(user_id="wellness_user", query="what's my weight goal")
        # Returns: {"context": "Weight goal: 125 lbs", "hits": 1, "goals": [{"metric": "weight", ...}]}
    """
    if not self.episodic_index:
        return {"context": None, "hits": 0, "goals": []}

    try:
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(query)
        if query_embedding is None:
            return {"context": None, "hits": 0, "goals": []}

        # Create vector query WITHOUT filter for debugging
        vector_query = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            return_fields=["description", "metadata", "timestamp", "user_id", "event_type"],
            filter_expression=None,  # DEBUG: No filter
            num_results=top_k,
        )

        # Execute search
        results = self.episodic_index.query(vector_query)

        if not results:
            return {"context": None, "hits": 0, "goals": []}

        # Format results for LLM
        goals = []
        context_lines = []

        for result in results:
            metadata = json.loads(result.get("metadata", "{}"))
            description = result.get("description", "")

            goals.append(metadata)

            # Handle two formats:
            # 1. Structured: {"metric": "weight", "value": 125, "unit": "lbs"}
            # 2. Text-only: {"goal_text": "to never skip leg day"}
            if "metric" in metadata and "value" in metadata and "unit" in metadata:
                # Structured goal format
                context_lines.append(
                    f"{metadata['metric'].capitalize()} goal: {metadata['value']} {metadata['unit']}"
                )
            elif "goal_text" in metadata:
                # Text-only goal format (from pre-router)
                context_lines.append(f"Goal: {metadata['goal_text']}")
            elif description:
                # Fallback to description
                context_lines.append(description)

        context = "\n".join(context_lines)

        logger.info(f"🔍 Retrieved {len(results)} goals for query: {query[:50]}")
        return {
            "context": context,
            "hits": len(results),
            "goals": goals,
        }

    except Exception as e:
        logger.error(f"❌ Goal retrieval failed: {e}", exc_info=True)
        raise MemoryRetrievalError(
            memory_type="episodic",
            reason=f"Failed to retrieve goals: {str(e)}",
        ) from e
```

**Key Pattern**: Store structured data as JSON in metadata field, with vector embeddings for semantic search. RedisVL handles the HNSW vector index automatically.

---

## 3. Semantic Memory (Health Knowledge with RedisVL)

**Purpose**: Store general health facts and knowledge (not user-specific)

**Location**: `backend/src/services/semantic_memory_manager.py`

**Redis Structure**:
- Key pattern: `semantic:{category}:{fact_type}:{timestamp}`
- Storage type: Redis Hash with vector embeddings
- Index: RedisVL HNSW vector index

### Real Code: Storing Health Facts

```python
# From semantic_memory_manager.py lines 133-217
async def store_semantic_fact(
    self,
    fact: str,
    fact_type: str = "general",  # "definition", "relationship", "guideline", "general"
    category: str = "general",  # "cardio", "nutrition", "metrics", "general"
    context: str = "",
    source: str = "system",
    metadata: dict[str, Any] | None = None,
) -> bool:
    """
    Store a semantic fact (general health knowledge).

    Examples:
        await store_semantic_fact(
            fact="Normal resting heart rate is 60-100 bpm",
            fact_type="guideline",
            category="cardio",
            context="Standard medical guideline for adults",
            source="medical_literature"
        )

        await store_semantic_fact(
            fact="VO2 max is a measure of cardiovascular fitness",
            fact_type="definition",
            category="metrics",
            context="Measures maximum oxygen consumption during exercise"
        )
    """
    if not self.semantic_index:
        return False

    try:
        # Combine fact and context for embedding
        combined_text = f"{fact}\n{context}" if context else fact

        # Generate embedding using centralized service
        embedding = await self.embedding_service.generate_embedding(combined_text)
        if embedding is None:
            return False

        # Create memory record using centralized utilities
        timestamp = get_utc_timestamp()
        memory_key = RedisKeys.semantic_memory(category, fact_type, timestamp)

        # Store in RedisVL
        with self.redis_manager.get_connection() as redis_client:
            import numpy as np

            memory_data = {
                "fact_type": fact_type,
                "category": category,
                "timestamp": timestamp,
                "fact": fact,
                "context": context,
                "source": source,
                "metadata": json.dumps(metadata or {}),
                "embedding": np.array(embedding, dtype=np.float32).tobytes(),
            }

            # Store as hash
            redis_client.hset(memory_key, mapping=memory_data)

            # Set TTL
            redis_client.expire(memory_key, self.memory_ttl)

        logger.info(f"Stored semantic fact: {fact[:50]}...")
        return True

    except Exception as e:
        logger.error(f"Semantic fact storage failed: {e}", exc_info=True)
        raise MemoryRetrievalError(
            memory_type="semantic",
            reason=f"Failed to store semantic fact: {str(e)}",
        ) from e
```

### Real Code: Default Health Knowledge

```python
# From semantic_memory_manager.py lines 320-367
async def populate_default_health_knowledge(self) -> int:
    """
    Populate semantic memory with default health knowledge.

    Returns:
        Number of facts stored
    """
    default_facts = [
        {
            "fact": "Normal resting heart rate for adults is 60-100 beats per minute",
            "fact_type": "guideline",
            "category": "cardio",
            "context": "Lower heart rate at rest generally indicates more efficient heart function and better cardiovascular fitness",
        },
        {
            "fact": "VO2 max is the maximum amount of oxygen the body can utilize during intense exercise",
            "fact_type": "definition",
            "category": "metrics",
            "context": "Measured in milliliters of oxygen per kilogram of body weight per minute (mL/kg/min)",
        },
        {
            "fact": "BMI is calculated as weight in kilograms divided by height in meters squared",
            "fact_type": "definition",
            "category": "metrics",
            "context": "BMI = weight(kg) / [height(m)]²",
        },
        {
            "fact": "Moderate intensity cardio exercise is 50-70% of maximum heart rate",
            "fact_type": "guideline",
            "category": "cardio",
            "context": "Maximum heart rate is roughly 220 minus your age",
        },
        {
            "fact": "Active energy is calories burned through physical activity",
            "fact_type": "definition",
            "category": "metrics",
            "context": "Excludes basal metabolic rate (BMR) - calories burned at rest",
        },
    ]

    stored_count = 0
    for fact_data in default_facts:
        success = await self.store_semantic_fact(**fact_data)
        if success:
            stored_count += 1

    logger.info(f"Populated {stored_count} default health facts")
    return stored_count
```

**Key Pattern**: Store general knowledge (not user-specific) with category tags for filtering. Use vector search to retrieve relevant facts based on query.

---

## 4. Procedural Memory (Tool Patterns with RedisVL)

**Purpose**: Learn and retrieve successful tool-calling patterns

**Location**: `backend/src/services/procedural_memory_manager.py`

**Redis Structure**:
- Key pattern: `procedural:{pattern_hash}:{timestamp}`
- Storage type: Redis Hash with vector embeddings
- Index: RedisVL HNSW vector index

### Real Code: Storing Patterns

```python
# From procedural_memory_manager.py lines 316-394
async def store_pattern(
    self,
    query: str,
    tools_used: list[str],
    success_score: float,
    execution_time_ms: int,
    metadata: dict | None = None,
) -> bool:
    """
    Store a successful workflow pattern.

    Args:
        query: Original user query
        tools_used: List of tools that were called
        success_score: Success score (0.0-1.0)
        execution_time_ms: Execution time in milliseconds
        metadata: Optional additional context

    Returns:
        True if stored successfully
    """
    if not self.procedural_index:
        logger.error("❌ Procedural index not initialized")
        return False

    if success_score < 0.7:
        logger.info(f"⏭️ Skipping pattern storage (low score: {success_score:.2%})")
        return False

    try:
        # Classify query
        query_type = _classify_query(query)

        # Generate embedding for semantic search
        query_description = f"{query_type}: {query}"
        embedding = await self.embedding_service.generate_embedding(
            query_description
        )

        if not embedding:
            logger.error("❌ Failed to generate embedding for pattern")
            return False

        # Generate pattern ID (hash of query + tools)
        pattern_content = f"{query}:{':'.join(sorted(tools_used))}"
        pattern_hash = hashlib.sha256(pattern_content.encode()).hexdigest()[:12]

        # Create Redis key (single user, but use wellness_user for consistency)
        timestamp = int(datetime.now(UTC).timestamp())
        pattern_key = f"{self.PROCEDURAL_PREFIX}{pattern_hash}:{timestamp}"

        # Store pattern data
        pattern_data = {
            "query_type": query_type,
            "timestamp": timestamp,
            "query_description": query_description,
            "tools_used": json.dumps(tools_used),
            "success_score": success_score,
            "execution_time_ms": execution_time_ms,
            "metadata": json.dumps(metadata or {}),
            "embedding": np.array(embedding, dtype=np.float32).tobytes(),
        }

        # Use context manager to get connection
        with self.redis_manager.get_connection() as redis_client:
            redis_client.hset(pattern_key, mapping=pattern_data)

            # Set TTL (7 months)
            ttl_seconds = self.settings.redis_session_ttl_seconds  # 7 months
            redis_client.expire(pattern_key, ttl_seconds)

        logger.info(
            f"💾 Stored procedural pattern: {query_type}, {len(tools_used)} tools, score={success_score:.2%}"
        )
        return True

    except Exception as e:
        logger.error(f"❌ Failed to store procedural pattern: {e}")
        return False
```

### Real Code: Retrieving Patterns

```python
# From procedural_memory_manager.py lines 396-476
async def retrieve_patterns(self, query: str, top_k: int = 3) -> dict:
    """
    Retrieve similar successful patterns via semantic search.

    Args:
        query: Current user query
        top_k: Number of similar patterns to retrieve

    Returns:
        Dict with patterns, query_type, and execution plan
    """
    if not self.procedural_index:
        logger.warning("⚠️ Procedural index not initialized")
        return {"patterns": [], "query_type": "unknown", "plan": None}

    try:
        # Classify query
        query_type = _classify_query(query)

        # Generate embedding for search
        query_description = f"{query_type}: {query}"
        query_embedding = await self.embedding_service.generate_embedding(
            query_description
        )

        if not query_embedding:
            logger.error("❌ Failed to generate query embedding")
            return {"patterns": [], "query_type": query_type, "plan": None}

        # Build vector query (no user filter - global patterns)
        vector_query = VectorQuery(
            vector=query_embedding,
            vector_field_name="embedding",
            num_results=top_k,
            return_fields=[
                "query_type",
                "query_description",
                "tools_used",
                "success_score",
                "execution_time_ms",
            ],
        )

        # Execute search
        results = self.procedural_index.query(vector_query)

        # Parse results
        patterns = []
        for result in results:
            try:
                patterns.append(
                    {
                        "query_type": result.get("query_type", "unknown"),
                        "query_description": result.get("query_description", ""),
                        "tools_used": json.loads(result.get("tools_used", "[]")),
                        "success_score": float(result.get("success_score", 0.0)),
                        "execution_time_ms": int(
                            result.get("execution_time_ms", 0)
                        ),
                    }
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse pattern result: {e}")
                continue

        logger.info(
            f"🧠 Retrieved {len(patterns)} procedural patterns for query_type={query_type}"
        )

        # Create execution plan
        plan = _plan_tool_sequence(query, query_type, patterns)

        return {
            "patterns": patterns,
            "query_type": query_type,
            "plan": plan,
        }

    except Exception as e:
        logger.error(f"❌ Failed to retrieve procedural patterns: {e}")
        return {"patterns": [], "query_type": "unknown", "plan": None}
```

**Key Pattern**: Store successful workflows with embeddings. Retrieve similar queries to suggest tool sequences based on past success.

---

## 5. Workout Indexing (Aggregations)

**Purpose**: Fast O(1) and O(log N) queries for workout statistics

**Location**: `backend/src/services/redis_workout_indexer.py`

**Redis Structures Used**:
- Hash: Day-of-week counts
- Sorted Set: Time-range queries
- Hash: Individual workout details

### Real Code: Creating Indexes

```python
# From redis_workout_indexer.py lines 30-132
def index_workouts(
    self, user_id: str, workouts: list[dict[str, Any]]
) -> dict[str, int | str]:
    """
    Create Redis indexes for fast workout queries.

    Indexes created:
    1. user:{user_id}:workout:days - Hash: day_of_week → count
    2. user:{user_id}:workout:by_date - Sorted Set: workout_id → timestamp
    3. user:{user_id}:workout:{id} - Hash: Individual workout details

    Args:
        user_id: User identifier
        workouts: List of workout dictionaries

    Returns:
        Dict with index statistics
    """
    if not workouts:
        logger.info(f"No workouts to index for user {user_id}")
        return {"workouts_indexed": 0, "keys_created": 0}

    try:
        with self.redis_manager.get_connection() as client:
            pipeline = client.pipeline()

            # Clear old indexes
            days_key = RedisKeys.workout_days(user_id)
            by_date_key = RedisKeys.workout_by_date(user_id)

            pipeline.delete(days_key)
            pipeline.delete(by_date_key)

            keys_created = 2  # days + by_date keys

            for workout in workouts:
                try:
                    # Generate workout ID
                    workout_id = self._generate_workout_id(user_id, workout)

                    # 1. Count by day of week (Hash)
                    day_of_week = workout.get("day_of_week", "Unknown")
                    pipeline.hincrby(days_key, day_of_week, 1)

                    # 2. Index by date for range queries (Sorted Set)
                    start_date_str = workout.get("startDate", "")
                    if start_date_str:
                        try:
                            workout_date = datetime.fromisoformat(
                                start_date_str.replace("Z", "+00:00")
                            )
                            if workout_date.tzinfo is None:
                                workout_date = workout_date.replace(tzinfo=UTC)

                            timestamp = workout_date.timestamp()
                            pipeline.zadd(by_date_key, {workout_id: timestamp})
                        except (ValueError, AttributeError):
                            logger.debug(
                                f"Invalid date for workout: {start_date_str}"
                            )
                            continue

                    # 3. Store workout details (Hash)
                    workout_key = RedisKeys.workout_detail(user_id, workout_id)
                    workout_data = {
                        "date": workout.get("date", ""),
                        "startDate": workout.get("startDate", ""),
                        "day_of_week": day_of_week,
                        "type": workout.get(
                            "type_cleaned", workout.get("type", "")
                        ),
                        "duration_minutes": str(workout.get("duration_minutes", 0)),
                        "calories": str(workout.get("calories", 0)),
                    }

                    pipeline.hset(workout_key, mapping=workout_data)
                    pipeline.expire(workout_key, self.ttl_seconds)
                    keys_created += 1

                except Exception as e:
                    logger.warning(f"Failed to index workout: {e}")
                    continue

            # Set TTLs on aggregate keys
            pipeline.expire(days_key, self.ttl_seconds)
            pipeline.expire(by_date_key, self.ttl_seconds)

            # Execute all commands
            pipeline.execute()

            logger.info(
                f"✅ Indexed {len(workouts)} workouts for {user_id} ({keys_created} Redis keys)"
            )

            return {
                "workouts_indexed": len(workouts),
                "keys_created": keys_created,
                "ttl_days": self.ttl_seconds // (24 * 60 * 60),
            }

    except Exception as e:
        logger.error(f"Failed to index workouts: {e}", exc_info=True)
        return {"error": str(e), "workouts_indexed": 0}
```

### Real Code: O(1) Day Counts

```python
# From redis_workout_indexer.py lines 151-178
def get_workout_count_by_day(self, user_id: str) -> dict[str, int]:
    """
    Get workout counts by day of week from Redis index.

    O(1) operation using Redis Hash.

    Args:
        user_id: User identifier

    Returns:
        Dict mapping day_of_week to count
    """
    try:
        with self.redis_manager.get_connection() as client:
            days_key = RedisKeys.workout_days(user_id)
            day_counts = client.hgetall(days_key)

            # Handle both bytes and strings (depends on Redis connection settings)
            result = {}
            for k, v in day_counts.items():
                key = k.decode() if isinstance(k, bytes) else k
                value = int(v.decode() if isinstance(v, bytes) else v)
                result[key] = value
            return result

    except Exception as e:
        logger.error(f"Failed to get workout counts by day: {e}")
        return {}
```

### Real Code: O(log N) Date Range Queries

```python
# From redis_workout_indexer.py lines 180-200
def get_workouts_in_date_range(
    self, user_id: str, start_timestamp: float, end_timestamp: float
) -> list[str]:
    """
    Get workout IDs in date range using Redis Sorted Set.

    O(log N) operation - much faster than scanning all workouts.

    Args:
        user_id: User identifier
        start_timestamp: Start of range (Unix timestamp)
        end_timestamp: End of range (Unix timestamp)

    Returns:
        List of workout IDs in range
    """
    try:
        with self.redis_manager.get_connection() as client:
            by_date_key = RedisKeys.workout_by_date(user_id)
            workout_ids = client.zrangebyscore(
                by_date_key, start_timestamp, end_timestamp
            )
            # ... handle results
```

**Key Pattern**: Use Redis Hashes for counts (HINCRBY), Sorted Sets for time-range queries (ZADD/ZRANGEBYSCORE), and individual Hashes for detailed records.

---

## 6. Health Data Storage

**Purpose**: Store Apple Health data with fast metric lookups

**Location**: `backend/src/services/redis_apple_health_manager.py`

**Redis Structure**:
- Main data: `user:{user_id}:health_data` (JSON blob)
- Metrics: `user:{user_id}:health_metric:{type}` (individual metrics)
- Context: `user:{user_id}:health_context` (conversation context)

### Real Code: Storing Health Data

```python
# From redis_apple_health_manager.py lines 49-88
def store_health_data(
    self, user_id: str, health_data: dict[str, Any], ttl_days: int = 210
) -> dict[str, Any]:
    """Store parsed health data permanently with optional TTL for indices."""
    try:
        ttl_seconds = ttl_days * 24 * 60 * 60

        with self.redis_manager.get_connection() as redis_client:
            # Store main health data collection WITHOUT TTL (permanent)
            main_key = RedisKeys.health_data(user_id)
            redis_client.set(main_key, json.dumps(health_data))

            # Store quick lookup indices with TTL
            indices_stored = self._create_indices(
                redis_client, user_id, health_data, ttl_seconds
            )

            # Store conversation context WITHOUT TTL (permanent)
            context_key = RedisKeys.health_context(user_id)
            conversation_context = health_data.get("conversation_context", "")
            redis_client.set(context_key, conversation_context)

            # Track storage metrics
            storage_info = {
                "user_id": user_id,
                "main_key": main_key,
                "indices_count": indices_stored,
                "health_data_ttl": "permanent",
                "indices_ttl_days": ttl_days,
                "indices_expire_at": (
                    datetime.now(UTC) + timedelta(days=ttl_days)
                ).isoformat(),
                "redis_keys_created": indices_stored
                + 2,  # main + context + indices
            }

            return storage_info

    except redis.RedisError as e:
        raise ToolError(f"Redis storage failed: {str(e)}", "REDIS_ERROR") from e
```

### Real Code: Creating Indices

```python
# From redis_apple_health_manager.py lines 90-114
def _create_indices(
    self, redis_client, user_id: str, health_data: dict[str, Any], ttl_seconds: int
) -> int:
    """Create Redis indices for fast metric queries."""
    indices_count = 0

    # Index by metric type for fast queries
    metrics_summary = health_data.get("metrics_summary", {})
    for metric_type, data in metrics_summary.items():
        key = RedisKeys.health_metric(user_id, metric_type)
        redis_client.setex(key, ttl_seconds, json.dumps(data))
        indices_count += 1

    # Index recent insights with TTL (key Redis advantage)
    recent_key = RedisKeys.health_recent_insights(user_id)
    recent_insights = {
        "record_count": health_data.get("record_count", 0),
        "data_categories": health_data.get("data_categories", []),
        "date_range": health_data.get("date_range", {}),
        "generated_at": datetime.now(UTC).isoformat(),
    }
    redis_client.setex(recent_key, ttl_seconds, json.dumps(recent_insights))
    indices_count += 1

    return indices_count
```

**Key Pattern**: Store large JSON blobs as permanent data, but create temporary indices with TTL for fast lookups. Use SETEX for automatic expiration.

---

## 7. Connection Management

**Purpose**: Production-ready connection pool with circuit breaker

**Location**: `backend/src/services/redis_connection.py`

### Real Code: Connection Pool with Circuit Breaker

```python
# From redis_connection.py lines 148-199
def _initialize_connection(self) -> None:
    """Initialize Redis connection pool with production settings."""
    try:
        # Get settings
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        redis_password = os.getenv("REDIS_PASSWORD")

        # Connection pool configuration
        pool_config = {
            "host": redis_host,
            "port": redis_port,
            "db": redis_db,
            "decode_responses": True,  # Auto-decode bytes to strings
            "max_connections": 50,  # Connection pool size
            "socket_timeout": 5,  # Socket timeout (seconds)
            "socket_connect_timeout": 5,  # Connection timeout
            "retry_on_timeout": True,  # Auto-retry on timeout
            "health_check_interval": 30,  # Health check every 30s
        }

        if redis_password:
            pool_config["password"] = redis_password

        # Create connection pool
        self._pool = ConnectionPool(**pool_config)
        self._client = redis.Redis(connection_pool=self._pool)

        # Test connection
        self._client.ping()
        logger.info("Redis connection pool initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Redis connection: {str(e)}")
        raise
```

### Real Code: Context Manager with Circuit Breaker

```python
# From redis_connection.py lines 201-227
@contextmanager
def get_connection(self):
    """
    Context manager for getting Redis connections with circuit breaker.

    Usage:
        with redis_manager.get_connection() as redis_client:
            redis_client.set("key", "value")
    """
    if not self.circuit_breaker.can_execute():
        raise redis.ConnectionError("Redis circuit breaker is OPEN")

    try:
        if not self._client:
            self._initialize_connection()

        yield self._client
        self.circuit_breaker.record_success()

    except redis.RedisError as e:
        self.circuit_breaker.record_failure()
        logger.error(f"Redis operation failed: {str(e)}")
        raise
    except Exception as e:
        self.circuit_breaker.record_failure()
        logger.error(f"Unexpected Redis error: {str(e)}")
        raise
```

**Key Pattern**: Use connection pooling for performance, circuit breaker for resilience, and context manager for safe resource cleanup.

---

## Summary of Redis Usage

| Purpose | Redis Structure | Key Pattern | Code Location |
|---------|----------------|-------------|---------------|
| Conversation History | LangGraph internal | `checkpoint:*` | `redis_connection.py:255-300` |
| Episodic Memory (Goals) | Hash + RedisVL | `episodic:{user}:goal:{ts}` | `episodic_memory_manager.py` |
| Semantic Memory (Facts) | Hash + RedisVL | `semantic:{cat}:{type}:{ts}` | `semantic_memory_manager.py` |
| Procedural Memory (Patterns) | Hash + RedisVL | `procedural:{hash}:{ts}` | `procedural_memory_manager.py` |
| Workout Day Counts | Hash (HINCRBY) | `user:{id}:workout:days` | `redis_workout_indexer.py:72` |
| Workout by Date | Sorted Set (ZADD) | `user:{id}:workout:by_date` | `redis_workout_indexer.py:85` |
| Workout Details | Hash | `user:{id}:workout:{wid}` | `redis_workout_indexer.py:105` |
| Health Data Main | JSON String | `user:{id}:health_data` | `redis_apple_health_manager.py:59` |
| Health Metrics | JSON String | `user:{id}:health_metric:{type}` | `redis_apple_health_manager.py:100` |

All code examples in this document are extracted directly from the codebase and represent the actual implementation as of October 2025.
