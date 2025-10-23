# Bug Fix Plan - Redis Wellness Chat System

**Date:** October 21, 2025
**Priority:** HIGH - Production Blocker Bugs Identified
**Estimated Timeline:** 2-3 days

---

## 🐛 Critical Bugs Identified

### Bug #1: Memory Confusion (Session vs Semantic)
**Severity:** HIGH
**Impact:** Users get answers from wrong conversations
**File:** `backend/src/agents/health_rag_agent.py`, `backend/src/services/memory_manager.py`

### Bug #2: Pronoun Resolution Failure
**Severity:** MEDIUM
**Impact:** Follow-up questions don't work naturally
**File:** `backend/src/agents/health_rag_agent.py`

### Bug #3: Insufficient Test Data
**Severity:** LOW (Testing issue, not production bug)
**Impact:** Can't properly validate fixes
**File:** Test data generation needed

---

## 📋 Detailed Fix Plan

## Phase 1: Fix Memory Confusion Bug (Priority 1)

### Problem Analysis
When user asks "What was the first thing I asked you?", the system returns:
- **Current behavior:** Pulls from semantic/long-term memory across all sessions
- **Expected behavior:** Returns first message from THIS session's conversation history

### Root Cause
The LangGraph agent or memory retrieval logic doesn't distinguish between:
1. **Session-specific history** (short-term memory for current conversation)
2. **Cross-session semantic memory** (long-term memory for all past conversations)

### Investigation Steps

1. **Check memory retrieval in agent**
   ```bash
   # Files to examine:
   backend/src/agents/health_rag_agent.py        # Agent logic
   backend/src/services/memory_manager.py        # Memory retrieval
   backend/src/api/chat_routes.py                # How history is passed
   ```

2. **Identify where semantic search is called**
   - Find where `search_memories()` or similar is invoked
   - Check if it's filtering by session_id

3. **Check conversation history structure**
   - Verify Redis keys: `conversation:{session_id}`
   - Confirm history is session-scoped

### Implementation Plan

**Step 1.1: Add Session-Scoped Memory Flag**

Create a parameter to distinguish memory types:

```python
# backend/src/services/memory_manager.py

def search_memories(
    self,
    query: str,
    limit: int = 3,
    session_id: str = None,  # NEW: Session filter
    scope: str = "all"  # NEW: "session", "semantic", "all"
) -> list:
    """
    Search memories with scope control.

    Args:
        query: Search query
        limit: Max results
        session_id: Current session ID
        scope:
            - "session": Only current session history
            - "semantic": Only long-term cross-session memory
            - "all": Both (current default behavior)
    """
    if scope == "session" and session_id:
        # Return ONLY conversation history from this session
        return self._get_session_history(session_id, limit)
    elif scope == "semantic":
        # Return ONLY semantic memories (exclude current session)
        return self._search_semantic_excluding_session(query, session_id, limit)
    else:
        # Current behavior: return both
        return self._search_all_memories(query, limit)

def _get_session_history(self, session_id: str, limit: int) -> list:
    """Get conversation history for current session only."""
    history_key = f"conversation:{session_id}"
    messages = self.redis.lrange(history_key, 0, -1)
    # Return most recent 'limit' messages
    return messages[-limit:] if messages else []
```

**Step 1.2: Update Agent Prompt to Use Correct Memory Scope**

```python
# backend/src/agents/health_rag_agent.py

# Add to agent's system prompt:
MEMORY_USAGE_GUIDELINES = """
MEMORY USAGE RULES:

1. For "what did I just ask?" or "first thing I asked" queries:
   - Use ONLY session history (current conversation)
   - DO NOT pull from semantic memory across sessions

2. For health insights like "my BMI goals" or "workout preferences":
   - Use semantic memory (long-term patterns)

3. For follow-ups like "tell me more" or "what about that?":
   - Use session history for immediate context
   - Then semantic memory for related facts

EXAMPLE:
Q: "What was the first thing I asked you?"
A: Look at THIS SESSION's first message, not global memory

Q: "What are my fitness goals?"
A: Look at semantic memory across all sessions
"""

# Add to agent state:
def classify_memory_need(query: str, conversation_history: list) -> str:
    """
    Determine which memory scope to use.

    Returns: "session", "semantic", or "both"
    """
    query_lower = query.lower()

    # Session-specific queries
    session_keywords = [
        "first thing i asked",
        "what did i just",
        "earlier you said",
        "you just told me",
        "beginning of our conversation",
        "start of this chat"
    ]

    if any(keyword in query_lower for keyword in session_keywords):
        return "session"

    # Semantic/historical queries
    semantic_keywords = [
        "my goals",
        "my preferences",
        "usually",
        "in the past",
        "historically"
    ]

    if any(keyword in query_lower for keyword in semantic_keywords):
        return "semantic"

    # Default: use both
    return "both"
```

**Step 1.3: Modify Memory Retrieval in Chat Route**

```python
# backend/src/api/chat_routes.py

@router.post("/redis")
async def redis_rag_chat(request: ChatRequest):
    # ... existing code ...

    # Classify memory need before retrieval
    from ..agents.health_rag_agent import classify_memory_need

    memory_scope = classify_memory_need(
        request.message,
        conversation_history
    )

    # Retrieve appropriate memories
    if memory_scope == "session":
        # Only use conversation history
        relevant_memories = memory_manager.search_memories(
            query=request.message,
            session_id=request.session_id,
            scope="session",
            limit=5
        )
    else:
        # Use semantic or both
        relevant_memories = memory_manager.search_memories(
            query=request.message,
            session_id=request.session_id,
            scope=memory_scope,
            limit=3
        )

    # Pass to agent
    response = await agent.process_with_memory(
        request.message,
        conversation_history,
        relevant_memories,
        memory_scope  # NEW: tell agent what scope was used
    )
```

**Step 1.4: Update Agent to Respect Memory Scope**

```python
# backend/src/agents/health_rag_agent.py

async def process_with_memory(
    self,
    query: str,
    conversation_history: list,
    relevant_memories: list,
    memory_scope: str  # NEW parameter
):
    """Process query with appropriate memory context."""

    # Format context based on scope
    if memory_scope == "session":
        context = self._format_session_context(
            conversation_history,
            relevant_memories
        )
        instruction = "Answer based ONLY on THIS conversation's history."
    else:
        context = self._format_full_context(
            conversation_history,
            relevant_memories
        )
        instruction = "Answer using conversation history and past insights."

    # Add to agent prompt
    enhanced_prompt = f"""
{self.base_prompt}

{instruction}

CONTEXT:
{context}

USER QUERY: {query}
"""

    return await self.agent.ainvoke(enhanced_prompt)
```

### Testing Plan for Bug #1

```bash
# Test 1: Session-scoped recall
./test_memory_scope.sh

# Test 2: Cross-session semantic memory
# (should still work for "what are my goals?")

# Test 3: Mixed queries
# (should use both appropriately)
```

---

## Phase 2: Fix Pronoun Resolution (Priority 2)

### Problem Analysis
When user asks "Is that considered healthy?" after asking about BMI:
- **Current:** Both systems fail to understand "that" = BMI
- **Expected:** Recognize "that" refers to most recent topic

### Implementation Plan

**Step 2.1: Add Coreference Tracking**

```python
# backend/src/utils/context_tracker.py (NEW FILE)

from typing import List, Dict, Optional

class ConversationContext:
    """Track conversation entities for pronoun resolution."""

    def __init__(self):
        self.last_topic: Optional[str] = None
        self.last_metric: Optional[str] = None
        self.last_value: Optional[str] = None
        self.last_entities: List[str] = []

    def update_from_query(self, query: str):
        """Extract entities from user query."""
        query_lower = query.lower()

        # Health metrics
        if "bmi" in query_lower or "body mass index" in query_lower:
            self.last_topic = "BMI"
            self.last_metric = "BodyMassIndex"
        elif "weight" in query_lower:
            self.last_topic = "weight"
            self.last_metric = "BodyMass"
        elif "heart rate" in query_lower:
            self.last_topic = "heart rate"
            self.last_metric = "HeartRate"
        elif "workout" in query_lower or "exercise" in query_lower:
            self.last_topic = "workouts"
            self.last_metric = None

        # Time periods
        if "september" in query_lower:
            self.last_entities.append("September")
        elif "last week" in query_lower:
            self.last_entities.append("last week")

    def update_from_response(self, response: str, tool_results: dict):
        """Extract entities from agent response and tools."""

        # Track values mentioned
        if "bmi" in response.lower() and tool_results:
            # Extract BMI value if returned
            pass

    def resolve_pronoun(self, query: str) -> str:
        """Replace pronouns with explicit references."""
        query_lower = query.lower()

        # "that" -> last topic
        if query_lower.startswith("is that ") and self.last_topic:
            return query.replace(
                "Is that",
                f"Is {self.last_topic}"
            )

        if query_lower.startswith("what about that") and self.last_topic:
            return query.replace(
                "What about that",
                f"What about {self.last_topic}"
            )

        # "it" -> last topic
        if " it " in query_lower and self.last_topic:
            return query.replace(" it ", f" {self.last_topic} ")

        return query
```

**Step 2.2: Integrate Context Tracking**

```python
# backend/src/api/chat_routes.py

# Add to session state (stored in Redis)
context_tracker_key = f"context:{request.session_id}"

# Load existing context
context_data = redis.get(context_tracker_key)
if context_data:
    context = ConversationContext.from_json(context_data)
else:
    context = ConversationContext()

# Update context with new query
context.update_from_query(request.message)

# Resolve pronouns BEFORE processing
resolved_query = context.resolve_pronoun(request.message)

# Use resolved query
response = await agent.process(resolved_query, ...)

# Update context with response
context.update_from_response(response, tool_results)

# Save context
redis.setex(
    context_tracker_key,
    ttl=7 * 24 * 60 * 60,  # 7 days
    value=context.to_json()
)
```

**Step 2.3: Add to Agent Prompt**

```python
# backend/src/agents/health_rag_agent.py

PRONOUN_HANDLING = """
PRONOUN RESOLUTION:

When user says "that", "it", or "this", look at conversation history to determine the referent:

Example:
User: "What was my BMI in September?"
Agent: "Your BMI in September was 24.5"
User: "Is that considered healthy?"
Agent should understand: "that" = BMI of 24.5

Always check the last 2-3 exchanges for context.
"""
```

### Testing Plan for Bug #2

```bash
# Test pronoun resolution
SESSION="pronoun_test_$(date +%s)"

# Q1: Establish context
curl -X POST .../redis -d '{"message": "What was my BMI?", "session_id": "'$SESSION'"}'

# Q2: Use pronoun
curl -X POST .../redis -d '{"message": "Is that healthy?", "session_id": "'$SESSION'"}'
# Should understand "that" = BMI

# Q3: Different pronoun
curl -X POST .../redis -d '{"message": "Tell me more about it", "session_id": "'$SESSION'"}'
# Should understand "it" = BMI
```

---

## Phase 3: Add Comprehensive Test Data (Priority 3)

### Problem
70% of test queries fail with "no data" - can't test conversation quality without data.

### Implementation Plan

**Step 3.1: Create Test Data Generator**

```python
# backend/tests/fixtures/generate_health_data.py

from datetime import datetime, timedelta
import random

def generate_test_health_data(user_id: str = "test_user"):
    """Generate comprehensive health data for testing."""

    data = {
        "user_id": user_id,
        "export_date": datetime.now().isoformat(),
        "record_count": 0,
        "records": [],
        "workouts": [],
        "metrics_summary": {},
        "metrics_records": {}
    }

    # Generate 90 days of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    # BMI data (daily)
    bmi_records = []
    base_bmi = 23.5
    for days_ago in range(90, 0, -1):
        date = end_date - timedelta(days=days_ago)
        # Slight variation
        bmi = base_bmi + random.uniform(-0.5, 0.5)
        bmi_records.append({
            "value": round(bmi, 2),
            "unit": "count",
            "date": date.strftime("%Y-%m-%d %H:%M:%S")
        })

    data["metrics_records"]["BodyMassIndex"] = bmi_records

    # Weight data (3x per week)
    weight_records = []
    base_weight = 160  # lbs
    for week in range(13):  # 13 weeks = ~90 days
        for day in [0, 2, 5]:  # Mon, Wed, Sat
            days_ago = (12 - week) * 7 + (5 - day)
            if days_ago < 0:
                continue
            date = end_date - timedelta(days=days_ago)
            weight = base_weight + random.uniform(-2, 2)
            weight_records.append({
                "value": round(weight, 1),
                "unit": "lb",
                "date": date.strftime("%Y-%m-%d %H:%M:%S")
            })

    data["metrics_records"]["BodyMass"] = weight_records

    # Heart rate (5-10 readings per day)
    hr_records = []
    for days_ago in range(90, 0, -1):
        readings_today = random.randint(5, 10)
        for _ in range(readings_today):
            date = end_date - timedelta(
                days=days_ago,
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            hr = random.randint(60, 90)  # Resting heart rate
            hr_records.append({
                "value": hr,
                "unit": "count/min",
                "date": date.strftime("%Y-%m-%d %H:%M:%S")
            })

    data["metrics_records"]["HeartRate"] = hr_records

    # Workouts (3-4 per week, already have real data but add more)
    # ... existing workout data from Apple Health is fine ...

    # Calculate summaries
    data["metrics_summary"]["BodyMassIndex"] = {
        "count": len(bmi_records),
        "latest_value": f"{bmi_records[-1]['value']} count",
        "latest_date": bmi_records[-1]['date']
    }

    data["metrics_summary"]["BodyMass"] = {
        "count": len(weight_records),
        "latest_value": f"{weight_records[-1]['value']} lb",
        "latest_date": weight_records[-1]['date']
    }

    data["metrics_summary"]["HeartRate"] = {
        "count": len(hr_records),
        "latest_value": f"{hr_records[-1]['value']} count/min",
        "latest_date": hr_records[-1]['date']
    }

    data["record_count"] = (
        len(bmi_records) + len(weight_records) + len(hr_records)
    )

    return data
```

**Step 3.2: Create Data Loading Script**

```bash
# scripts/load_test_data.sh

#!/bin/bash

echo "Generating comprehensive test health data..."

python3 - << 'EOF'
import sys
sys.path.insert(0, '/path/to/backend')

from backend.tests.fixtures.generate_health_data import generate_test_health_data
from backend.src.services.redis_health_tool import store_health_data
import json

# Generate data
data = generate_test_health_data(user_id="your_user")

# Store in Redis
result = store_health_data(
    user_id="your_user",
    health_data=data,
    ttl_days=210
)

print(f"✅ Loaded {data['record_count']} health records")
print(f"   - BMI: {data['metrics_summary']['BodyMassIndex']['count']} records")
print(f"   - Weight: {data['metrics_summary']['BodyMass']['count']} records")
print(f"   - Heart Rate: {data['metrics_summary']['HeartRate']['count']} records")
print(f"   - Workouts: {len(data.get('workouts', []))} records")
EOF

echo "✅ Test data loaded successfully"
```

**Step 3.3: Run Data Generation**

```bash
chmod +x scripts/load_test_data.sh
./scripts/load_test_data.sh
```

---

## Phase 4: Verification & Re-Testing

### Step 4.1: Create Targeted Bug Tests

```bash
# tests/test_bug_fixes.sh

#!/bin/bash

echo "Testing Bug Fixes..."

SESSION="bugfix_test_$(date +%s)"

# Bug #1 Test: Memory scope
echo "TEST 1: Session memory isolation"
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"My favorite exercise is swimming\", \"session_id\": \"$SESSION\"}"

sleep 1

RESULT=$(curl -s -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What was the first thing I told you?\", \"session_id\": \"$SESSION\"}" | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['response'])")

if [[ "$RESULT" == *"swimming"* ]]; then
  echo "✅ PASS: Correctly recalled session-specific memory"
else
  echo "❌ FAIL: Did not recall correct session memory"
  echo "Response: $RESULT"
fi

# Bug #2 Test: Pronoun resolution
echo ""
echo "TEST 2: Pronoun resolution"
NEW_SESSION="pronoun_$(date +%s)"

curl -s -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What was my BMI in September?\", \"session_id\": \"$NEW_SESSION\"}" > /dev/null

sleep 1

RESULT=$(curl -s -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Is that considered healthy?\", \"session_id\": \"$NEW_SESSION\"}" | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['response'].lower())")

if [[ "$RESULT" == *"bmi"* || "$RESULT" == *"body mass"* ]]; then
  echo "✅ PASS: Correctly understood 'that' refers to BMI"
else
  echo "❌ FAIL: Did not understand pronoun reference"
  echo "Response: $RESULT"
fi

# Bug #3 Test: Data availability
echo ""
echo "TEST 3: Test data loaded"
RESULT=$(curl -s -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my average BMI in the last 30 days?", "session_id": "data_test"}' | \
  python3 -c "import sys,json; r=json.load(sys.stdin); print('no data' in r['response'].lower())")

if [[ "$RESULT" == "False" ]]; then
  echo "✅ PASS: BMI data available"
else
  echo "❌ FAIL: BMI data still missing"
fi

echo ""
echo "Bug fix verification complete"
```

### Step 4.2: Re-run Full Test Suite

```bash
# After fixes, re-run original tests
./test_chat_comparison.sh > results_after_fixes.txt

# Compare results
diff TEST_RESULTS.md results_after_fixes.txt
```

---

## Implementation Timeline

### Day 1: Memory Confusion Fix
- Morning: Implement Step 1.1-1.2 (memory scope flag + classification)
- Afternoon: Implement Step 1.3-1.4 (integrate into routes + agent)
- Evening: Test Bug #1 fix

### Day 2: Pronoun Resolution
- Morning: Implement Step 2.1-2.2 (context tracker + integration)
- Afternoon: Test Bug #2 fix
- Evening: Generate and load test data (Phase 3)

### Day 3: Verification
- Morning: Run targeted bug tests
- Afternoon: Re-run full test suite
- Evening: Document results and update README

---

## Success Criteria

### Bug #1 Fixed:
✅ "What was the first thing I asked?" returns current session's first message
✅ "What are my fitness goals?" still pulls from semantic memory
✅ Memory scope classification works 95%+ accuracy

### Bug #2 Fixed:
✅ "Is that healthy?" after BMI query correctly understands "that" = BMI
✅ Follow-up questions work naturally without re-stating context
✅ Pronoun resolution works for "that", "it", "this"

### Bug #3 Fixed:
✅ BMI queries return actual data (not "no data")
✅ Weight queries return actual data
✅ Heart rate queries return actual data
✅ Test suite shows clear differences between systems

---

## Rollback Plan

If fixes cause regressions:

1. **Revert commits**
   ```bash
   git revert <commit-hash>
   ```

2. **Feature flag**
   ```python
   USE_MEMORY_SCOPE_CLASSIFICATION = os.getenv("ENABLE_MEMORY_FIX", "false") == "true"
   ```

3. **A/B test**
   - 50% traffic to old behavior
   - 50% traffic to new behavior
   - Monitor metrics

---

## Monitoring & Validation

After deployment, monitor:

1. **Memory accuracy** - Log when session vs semantic is used
2. **Pronoun resolution rate** - Track how often pronouns are resolved
3. **User satisfaction** - Track "that doesn't make sense" type responses
4. **Data availability** - Track "no data" response rate

Expected improvements:
- Session memory accuracy: 95%+
- Pronoun resolution: 80%+
- "No data" responses: < 10% (down from 70%)

---

## Files to Create/Modify

**New files:**
- `backend/src/utils/context_tracker.py`
- `backend/tests/fixtures/generate_health_data.py`
- `scripts/load_test_data.sh`
- `tests/test_bug_fixes.sh`

**Modified files:**
- `backend/src/services/memory_manager.py`
- `backend/src/agents/health_rag_agent.py`
- `backend/src/api/chat_routes.py`

---

## Next Steps

1. Review this plan with team
2. Create GitHub issues for each phase
3. Set up feature branch: `fix/memory-and-context-bugs`
4. Begin Phase 1 implementation
5. Write unit tests for each component
6. Deploy to staging for QA
7. A/B test in production if possible
