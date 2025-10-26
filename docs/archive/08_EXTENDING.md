# Extending the Demo: Build on This Foundation

**Teaching Goal:** Learn how to add new tools, integrate different data sources, deploy for production, and test your changes systematically.

## Adding New Tools (Step-by-Step)

### Example: Add "Sleep Analysis" Tool

Let's walk through adding a complete new tool from scratch.

#### Step 1: Create the Tool File

Create `/Users/allierays/Sites/redis-wellness/backend/src/apple_health/query_tools/sleep_analysis.py`:

```python
"""
Sleep Analysis Tool - Analyze sleep patterns from Apple Health data.
"""

import json
import logging
from typing import Any
from langchain_core.tools import tool
from ...services.redis_apple_health_manager import redis_manager
from ...utils.time_utils import parse_time_period
from ...utils.user_config import get_user_health_data_key

logger = logging.getLogger(__name__)


def create_sleep_analysis_tool(user_id: str):
    """
    Create sleep_analysis tool bound to a specific user.

    Args:
        user_id: The user identifier to bind to this tool

    Returns:
        LangChain tool instance
    """

    @tool
    def analyze_sleep_patterns(time_period: str = "last 30 days") -> dict[str, Any]:
        """
        Analyze sleep patterns and quality over time.

        Use this when the user asks about:
        - Sleep duration trends ("How much am I sleeping?")
        - Sleep quality ("Am I sleeping well?")
        - Sleep consistency ("Do I sleep at consistent times?")

        Args:
            time_period: Time range to analyze (e.g., "last 30 days", "this month")

        Returns:
            Dict with sleep statistics and patterns
        """
        logger.info(f"🔧 analyze_sleep_patterns called: time_period='{time_period}', user_id={user_id}")

        try:
            # Parse time period
            filter_start, filter_end, time_range_desc = parse_time_period(time_period)

            # Get health data from Redis
            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = get_user_health_data_key()
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return {"error": "No health data found", "sleep_records": []}

                health_data = json.loads(health_data_json)
                metrics_records = health_data.get("metrics_records", {})

                # Get sleep records (Apple Health tracks as "SleepAnalysis")
                sleep_records = metrics_records.get("SleepAnalysis", [])

                if not sleep_records:
                    return {"error": "No sleep data found", "sleep_records": []}

                # Filter by time period
                from datetime import datetime
                filtered_records = [
                    r for r in sleep_records
                    if filter_start <= datetime.fromisoformat(r["date"]) <= filter_end
                ]

                if not filtered_records:
                    return {
                        "message": f"No sleep data in {time_range_desc}",
                        "sleep_records": []
                    }

                # Calculate statistics
                total_hours = sum(r.get("value", 0) for r in filtered_records)
                avg_hours = total_hours / len(filtered_records) if filtered_records else 0
                min_hours = min(r.get("value", 0) for r in filtered_records)
                max_hours = max(r.get("value", 0) for r in filtered_records)

                return {
                    "time_period": time_range_desc,
                    "total_nights": len(filtered_records),
                    "average_hours": round(avg_hours, 1),
                    "min_hours": round(min_hours, 1),
                    "max_hours": round(max_hours, 1),
                    "total_hours": round(total_hours, 1),
                    "sleep_records": filtered_records[:10]  # Return last 10 for detail
                }

        except Exception as e:
            logger.error(f"Sleep analysis failed: {e}", exc_info=True)
            return {"error": f"Sleep analysis failed: {str(e)}"}

    return analyze_sleep_patterns
```

#### Step 2: Register the Tool

Update `/Users/allierays/Sites/redis-wellness/backend/src/apple_health/query_tools/__init__.py`:

```python
from .sleep_analysis import create_sleep_analysis_tool

__all__ = [
    "create_user_bound_tools",
    # ...existing tools
    "create_sleep_analysis_tool",  # Add new tool
]

def create_user_bound_tools(user_id: str, conversation_history=None) -> list[BaseTool]:
    """
    Create tool instances bound to the single application user.

    Now includes sleep analysis tool (10 tools total).
    """
    tools = [
        create_search_health_records_tool(user_id),
        create_search_workouts_tool(user_id),
        create_aggregate_metrics_tool(user_id),
        create_weight_trends_tool(user_id),
        create_compare_periods_tool(user_id),
        create_compare_activity_tool(user_id),
        create_workout_schedule_tool(user_id),
        create_intensity_analysis_tool(user_id),
        create_progress_tracking_tool(user_id),
        create_sleep_analysis_tool(user_id),  # NEW: Sleep analysis
    ]

    logger.info(f"✅ Created {len(tools)} user-bound tools")
    return tools
```

#### Step 3: Update System Prompt (Optional)

If you want to guide the LLM on when to use the new tool, update `/Users/allierays/Sites/redis-wellness/backend/src/utils/agent_helpers.py`:

```python
def build_base_system_prompt() -> str:
    base_prompt = """You are a health AI assistant with access to the user's Apple Health data.

You have tools to search health records, query workouts, aggregate metrics, compare time periods, and analyze sleep patterns.

⚠️ TOOL-FIRST POLICY:
- For factual questions about workouts/health data → ALWAYS call tools (source of truth)
- NEVER answer workout/metric questions without tool data

CRITICAL - TOOL USAGE EXAMPLES:
- For "last workout" queries → Use search_workouts_and_activity
- For "what is my weight/heart rate/steps" → Use search_health_records
- For "sleep patterns" or "how much am I sleeping" → Use analyze_sleep_patterns  # NEW
- NEVER make up data
"""
    return base_prompt
```

#### Step 4: Test the New Tool

Create a test file `/Users/allierays/Sites/redis-wellness/backend/tests/tools/test_sleep_analysis.py`:

```python
import pytest
from src.apple_health.query_tools.sleep_analysis import create_sleep_analysis_tool

@pytest.mark.integration
def test_sleep_analysis_tool():
    """Test sleep analysis tool with sample data."""
    tool = create_sleep_analysis_tool(user_id="test_user")

    # Call tool
    result = tool.invoke({"time_period": "last 30 days"})

    # Verify structure
    assert "average_hours" in result or "error" in result
    if "average_hours" in result:
        assert result["average_hours"] > 0
        assert result["total_nights"] > 0
```

Run test:
```bash
cd backend
uv run pytest tests/tools/test_sleep_analysis.py -v
```

#### Step 5: Try It Live

Start the demo and ask:
```
You: "How much am I sleeping on average?"

Bot: Calls analyze_sleep_patterns tool
     Returns: "You're averaging 7.2 hours of sleep per night over the last 30 days."
```

### Tool Development Checklist

When adding any new tool:

- [ ] Create tool file in `backend/src/apple_health/query_tools/`
- [ ] Use `@tool` decorator for LangChain compatibility
- [ ] Add docstring explaining when to use the tool
- [ ] Bind to `user_id` for security (single-user mode)
- [ ] Handle errors gracefully (return dict with "error" key)
- [ ] Register in `__init__.py` `create_user_bound_tools()` function
- [ ] Update system prompt if needed (optional)
- [ ] Write integration test
- [ ] Test manually via chat interface

## Adding New Memory Types

### When You Might Need Episodic Memory

**Current demo:** Short-term (checkpointing) + Procedural (tool patterns)

**When to add episodic memory:**
- **Long-term user applications** (months/years of history)
- **User preferences** ("I don't like running", "I'm vegetarian")
- **Goals tracking** ("My goal is to lose 10 lbs by March")
- **Medical context** ("I injured my knee in January")

### Example: Add Goal Tracking (Episodic Memory)

#### Step 1: Define Episodic Schema

Already exists in `/Users/allierays/Sites/redis-wellness/backend/src/services/episodic_memory_manager.py`:

```python
schema = {
    "index": {
        "name": "episodic_memory_idx",
        "prefix": "episodic:",
    },
    "fields": [
        {"name": "user_id", "type": "tag"},
        {"name": "event_type", "type": "tag"},  # "goal", "preference", "injury"
        {"name": "timestamp", "type": "numeric"},
        {"name": "description", "type": "text"},
        {"name": "metadata", "type": "text"},  # JSON
        {
            "name": "embedding",
            "type": "vector",
            "attrs": {"dims": 1024, "distance_metric": "cosine", "algorithm": "hnsw"}
        }
    ]
}
```

#### Step 2: Store Goals

```python
async def store_goal(user_id: str, metric: str, value: float, unit: str) -> bool:
    """Store a user goal in episodic memory."""
    description = f"User's {metric} goal is {value} {unit}"

    # Generate embedding for semantic search
    embedding = await embedding_service.generate_embedding(description)

    memory_data = {
        "user_id": user_id,
        "event_type": "goal",
        "timestamp": int(datetime.now(UTC).timestamp()),
        "description": description,
        "metadata": json.dumps({"metric": metric, "value": value, "unit": unit}),
        "embedding": np.array(embedding, dtype=np.float32).tobytes()
    }

    redis_client.hset(memory_key, mapping=memory_data)
    return True
```

#### Step 3: Retrieve Goals

```python
async def retrieve_goals(user_id: str, query: str, top_k: int = 3) -> dict:
    """Retrieve relevant goals via semantic search."""
    query_embedding = await embedding_service.generate_embedding(query)

    # Filter by user_id AND event_type=goal
    filter_expr = Tag("user_id") == user_id
    filter_expr = filter_expr & (Tag("event_type") == "goal")

    vector_query = VectorQuery(
        vector=query_embedding,
        vector_field_name="embedding",
        filter_expression=filter_expr,
        num_results=top_k
    )

    results = episodic_index.query(vector_query)

    # Format for LLM
    context = "\n".join([
        f"{r['metadata']['metric']} goal: {r['metadata']['value']} {r['metadata']['unit']}"
        for r in results
    ])

    return {"context": context, "hits": len(results), "goals": results}
```

#### Step 4: Inject into Agent

Update `stateful_rag_agent.py` to retrieve goals before LLM call:

```python
async def _retrieve_episodic_node(self, state: MemoryState) -> dict:
    """Retrieve episodic memory (goals, preferences) before LLM call."""
    user_message = state["messages"][-1].content
    user_id = state["user_id"]

    result = await self.episodic.retrieve_goals(user_id, user_message, top_k=3)

    if result["context"]:
        logger.info(f"✅ Retrieved {result['hits']} goals")

    return {"episodic_context": result["context"]}
```

Then inject into LLM prompt:

```python
async def _llm_node(self, state: MemoryState) -> dict:
    system_prompt = build_base_system_prompt()

    # Inject episodic context (goals)
    if state.get("episodic_context"):
        system_prompt += f"\n\n📋 USER GOALS:\n{state['episodic_context']}"

    # LLM now sees user's goals when answering
```

**Example conversation:**
```
You: "My goal is to weigh 125 lbs by March"
Bot: "I've noted your goal. I'll help you track progress toward 125 lbs."

[Goal stored in episodic memory]

You: "Am I on track to hit my goal?"
Bot: [Retrieves goal from episodic memory]
     "Your current weight is 136.8 lbs. You're 11.8 lbs away from your goal of 125 lbs."
```

## Using Different Data Sources (Not Just Apple Health)

### Fitbit Integration

**Fitbit API data structure:**
```json
{
    "activities-steps": [
        {"dateTime": "2024-10-22", "value": "8547"}
    ],
    "activities-heart": [
        {"dateTime": "2024-10-22", "value": {"restingHeartRate": 62}}
    ],
    "sleep": [
        {
            "dateOfSleep": "2024-10-22",
            "duration": 25200000,
            "minutesAsleep": 420
        }
    ]
}
```

**Adapter pattern:**
```python
class FitbitAdapter:
    """Adapt Fitbit API data to our Redis schema."""

    def normalize_to_health_data(self, fitbit_data: dict) -> dict:
        """Convert Fitbit format to our standard format."""
        health_data = {
            "metrics_summary": {},
            "metrics_records": {},
            "workouts": []
        }

        # Convert steps
        if "activities-steps" in fitbit_data:
            health_data["metrics_records"]["Steps"] = [
                {"date": r["dateTime"], "value": int(r["value"]), "unit": "count"}
                for r in fitbit_data["activities-steps"]
            ]

        # Convert sleep
        if "sleep" in fitbit_data:
            health_data["metrics_records"]["Sleep"] = [
                {
                    "date": r["dateOfSleep"],
                    "value": r["minutesAsleep"] / 60,  # Convert to hours
                    "unit": "hr"
                }
                for r in fitbit_data["sleep"]
            ]

        return health_data

    def import_from_api(self, user_id: str, access_token: str):
        """Fetch from Fitbit API and store in Redis."""
        import requests

        # Fetch from Fitbit
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get("https://api.fitbit.com/1/user/-/activities/steps/date/today/30d.json", headers=headers)
        fitbit_data = response.json()

        # Normalize
        health_data = self.normalize_to_health_data(fitbit_data)

        # Store in Redis (same as Apple Health)
        from services.redis_apple_health_manager import redis_manager
        redis_manager.store_health_data(user_id, health_data)
```

### CSV Import (Generic Time-Series Data)

**CSV format:**
```csv
date,metric,value,unit
2024-10-22,weight,136.8,lb
2024-10-22,steps,8547,count
2024-10-22,heart_rate,68,bpm
```

**Import script:**
```python
import csv
from collections import defaultdict

def import_csv(csv_path: str, user_id: str):
    """Import generic health CSV."""
    health_data = {
        "metrics_summary": {},
        "metrics_records": defaultdict(list)
    }

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            metric = row["metric"]
            health_data["metrics_records"][metric].append({
                "date": row["date"],
                "value": float(row["value"]),
                "unit": row["unit"]
            })

    # Store in Redis
    from services.redis_apple_health_manager import redis_manager
    redis_manager.store_health_data(user_id, dict(health_data))
```

**Usage:**
```bash
python import_csv.py /path/to/health_data.csv
```

## Deployment Considerations

### Production Checklist

When moving from demo to production:

#### 1. Redis Persistence

**Demo (in-memory only):**
```yaml
# docker-compose.yml
redis:
  image: redis/redis-stack:latest
  # No persistence - data lost on restart
```

**Production (persistent):**
```yaml
redis:
  image: redis/redis-stack:latest
  volumes:
    - redis_data:/data
  command: redis-server --save 60 1 --loglevel warning
  # Saves to disk every 60 seconds if 1+ key changed

volumes:
  redis_data:
```

#### 2. Multi-User Support

**Demo (single user):**
```python
user_id = "wellness_user"  # Hardcoded
```

**Production (multi-user):**
```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

def get_current_user(token: str = Depends(security)) -> str:
    """Extract user_id from JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/chat/redis")
async def chat(request: ChatRequest, user_id: str = Depends(get_current_user)):
    """Chat endpoint with user authentication."""
    result = await redis_service.chat(request.message, user_id=user_id)
    return result
```

#### 3. Rate Limiting

**Protect against abuse:**
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/api/chat/redis", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def chat(request: ChatRequest):
    """Max 10 requests per minute per user."""
    pass
```

#### 4. Monitoring and Logging

**Add structured logging:**
```python
import structlog

logger = structlog.get_logger()

@app.post("/api/chat/redis")
async def chat(request: ChatRequest, user_id: str):
    logger.info(
        "chat_request",
        user_id=user_id,
        message_length=len(request.message),
        session_id=request.session_id
    )

    result = await redis_service.chat(request.message, user_id=user_id)

    logger.info(
        "chat_response",
        user_id=user_id,
        tools_used=result["tools_used"],
        response_length=len(result["response"])
    )

    return result
```

#### 5. Error Handling

**Production-ready error handling:**
```python
from fastapi import HTTPException

@app.post("/api/chat/redis")
async def chat(request: ChatRequest):
    try:
        result = await redis_service.chat(request.message)
        return result
    except MemoryRetrievalError as e:
        logger.error("Memory retrieval failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve conversation history")
    except InfrastructureError as e:
        logger.error("Redis connection failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except Exception as e:
        logger.error("Unexpected error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

#### 6. Scaling Ollama

**Demo (single Ollama instance):**
```yaml
ollama:
  # Runs on host machine (localhost:11434)
```

**Production (multiple Ollama instances with load balancing):**
```python
import random

OLLAMA_INSTANCES = [
    "http://ollama-1:11434",
    "http://ollama-2:11434",
    "http://ollama-3:11434"
]

def get_ollama_url() -> str:
    """Round-robin load balancing."""
    return random.choice(OLLAMA_INSTANCES)

llm = ChatOllama(model="qwen2.5:7b", base_url=get_ollama_url())
```

## Testing Strategy

Reference: `/Users/allierays/Sites/redis-wellness/backend/TEST_PLAN.md`

### Unit Tests (Pure Functions)

**Test tool logic without LLM:**
```python
def test_parse_time_period():
    """Test time period parsing (no external dependencies)."""
    from utils.time_utils import parse_time_period

    start, end, desc = parse_time_period("last 30 days")

    assert (end - start).days == 30
    assert "last 30 days" in desc
```

### Integration Tests (Redis Required)

**Test Redis operations:**
```python
@pytest.mark.integration
def test_workout_indexer(redis_client):
    """Test workout indexing with real Redis."""
    from services.redis_workout_indexer import WorkoutIndexer

    indexer = WorkoutIndexer()
    workouts = [
        {"date": "2024-10-22", "day_of_week": "Friday", "type": "Cycling"}
    ]

    result = indexer.index_workouts("test_user", workouts)

    assert result["workouts_indexed"] == 1

    # Verify index
    day_counts = indexer.get_workout_count_by_day("test_user")
    assert day_counts["Friday"] == 1
```

### Agent Tests (LLM-Dependent)

**Test tool calling (validate structure, not exact text):**
```python
@pytest.mark.agent
async def test_agent_calls_correct_tool():
    """Test that agent selects appropriate tool."""
    agent = StatefulRAGAgent(checkpointer=checkpointer)

    result = await agent.chat("What's my weight?", user_id="test_user")

    # ✅ GOOD: Validate structure
    assert "tools_used" in result
    assert any("search_health_records" in str(t) for t in result["tools_used"])

    # ❌ BAD: Don't check exact response text (LLM varies)
    # assert "Your weight is" in result["response"]
```

### Running Tests

```bash
# Run all tests
cd backend
uv run pytest tests/

# Run by category
uv run pytest tests/unit/           # Pure functions only
uv run pytest tests/integration/    # Redis-dependent
uv run pytest tests/agent/          # LLM-dependent

# Run specific test
uv run pytest tests/unit/test_time_utils.py::test_parse_time_period -v

# Run with coverage
uv run pytest --cov=src --cov-report=html tests/
```

## Code Structure Best Practices

### Services Layer

**Location:** `/Users/allierays/Sites/redis-wellness/backend/src/services/`

**What belongs here:**
- Redis connection management (`redis_connection.py`)
- Data managers (`redis_apple_health_manager.py`, `redis_workout_indexer.py`)
- Memory managers (`episodic_memory_manager.py`, `procedural_memory_manager.py`)
- Embedding service (`embedding_service.py`)

**Pattern:** Services are singletons with clear responsibilities

```python
# Good: Clear responsibility
class WorkoutIndexer:
    """Index workouts in Redis for O(1) aggregation queries."""

    def index_workouts(self, user_id: str, workouts: list[dict]) -> dict:
        """Create Redis indexes for fast workout queries."""

    def get_workout_count_by_day(self, user_id: str) -> dict[str, int]:
        """Get workout counts by day of week from Redis index."""
```

### Agents Layer

**Location:** `/Users/allierays/Sites/redis-wellness/backend/src/agents/`

**What belongs here:**
- Stateful RAG agent (`stateful_rag_agent.py`)
- Stateless agent (if you add one)

**Pattern:** Agents orchestrate services and tools

```python
class StatefulRAGAgent:
    """LangGraph-based stateful agent with checkpointing AND memory."""

    def __init__(self, checkpointer, episodic_memory, procedural_memory):
        self.llm = create_health_llm()
        self.checkpointer = checkpointer
        self.episodic = episodic_memory
        self.procedural = procedural_memory
        self.graph = self._build_graph()

    async def chat(self, message: str, user_id: str, session_id: str) -> dict:
        """Process message through graph with memory."""
```

### Tools Layer

**Location:** `/Users/allierays/Sites/redis-wellness/backend/src/apple_health/query_tools/`

**What belongs here:**
- Individual tool files (`search_health_records.py`, `search_workouts.py`, etc.)
- Tool factory (`__init__.py` with `create_user_bound_tools()`)

**Pattern:** Each tool is a LangChain `@tool` with clear docstring

```python
@tool
def search_health_records_by_metric(metric_types: list[str], time_period: str) -> dict:
    """
    Search for specific health metrics within a time period.

    Use this when the user asks about:
    - BMI, weight, steps, heart rate
    - Recent values or trends

    Args:
        metric_types: List of metric types (e.g., ["BodyMass", "HeartRate"])
        time_period: Time description (e.g., "recent", "last week")

    Returns:
        Dict with matching records and metadata
    """
```

### Utils Layer

**Location:** `/Users/allierays/Sites/redis-wellness/backend/src/utils/`

**What belongs here:**
- Pure functions (no side effects)
- Shared utilities (`time_utils.py`, `conversion_utils.py`)
- Validators (`numeric_validator.py`, `date_validator.py`)

**Pattern:** Stateless, testable functions

```python
def parse_time_period(description: str) -> tuple[datetime, datetime, str]:
    """
    Parse natural language time description into date range.

    Args:
        description: Natural language (e.g., "last 30 days", "October")

    Returns:
        Tuple of (start_date, end_date, description)

    Examples:
        >>> parse_time_period("last 30 days")
        (datetime(2024, 9, 25), datetime(2024, 10, 25), "last 30 days")
    """
```

## Key Takeaways

1. **Adding tools is straightforward** - Create tool file, register in `__init__.py`, test
2. **Memory types scale with data** - Add episodic for long-term apps, skip for short demos
3. **Adapt to any data source** - Fitbit, Garmin, CSV - just normalize to our schema
4. **Production requires persistence** - Redis RDB snapshots, multi-user auth, rate limiting
5. **Test at multiple levels** - Unit (pure functions), integration (Redis), agent (structure validation)
6. **Clear code structure** - Services (data), agents (orchestration), tools (LLM-callable), utils (pure functions)

## Next Steps

- **Explore backend/TEST_PLAN.md** - Comprehensive testing strategy
- **Review backend/src/services/** - See production-ready service patterns
- **Experiment with tools** - Add nutrition tracking, exercise recommendations, etc.
- **Deploy locally first** - Test with persistence before cloud deployment
