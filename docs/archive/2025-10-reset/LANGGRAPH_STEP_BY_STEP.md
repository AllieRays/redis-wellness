# LangGraph Migration: Step-by-Step with Test Gates

**Goal**: Replace fragile simple loop with LangGraph, adding complexity ONE feature at a time with validation at each step.

**Critical Rule**: DO NOT proceed to next step until current step is fully working and tested.

---

## Phase 0: Preparation (10 min) ✅ DONE

**What**: Save current working state

```bash
# Backup current working agents
cp backend/src/agents/stateful_rag_agent.py backend/src/agents/stateful_rag_agent.py.simple_loop_backup
cp backend/src/agents/stateless_agent.py backend/src/agents/stateless_agent.py.backup
```

**✅ Success Criteria**:
- Backups created
- Current stateless endpoint still works: `curl -X POST http://localhost:8000/api/chat/stateless -d '{"message": "how much do I weigh"}'`

---

## Phase 1: Minimal LangGraph (No Memory, No Checkpointing) - 1 hour

**What**: Build absolute simplest LangGraph agent with ZERO features except tool calling.

### Step 1.1: Create Minimal Agent (30 min)

**File**: `backend/src/agents/langgraph_minimal.py`

```python
"""
Minimal LangGraph agent - NO memory, NO checkpointing, JUST tools.
This is the baseline to prove LangGraph works before adding complexity.
"""

import logging
from typing import Annotated, Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict  # Use typing_extensions for Python 3.11

from ..apple_health.query_tools import create_user_bound_tools
from ..utils.agent_helpers import build_base_system_prompt, create_health_llm

logger = logging.getLogger(__name__)


class MinimalState(TypedDict):
    """Minimal state - just messages and user ID."""
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str


class MinimalLangGraphAgent:
    """Bare minimum LangGraph agent to prove it works."""

    def __init__(self):
        self.llm = create_health_llm()
        self.graph = self._build_graph()
        logger.info("✅ MinimalLangGraphAgent initialized")

    def _build_graph(self):
        """Build simplest possible graph: LLM → Tools → End."""
        workflow = StateGraph(MinimalState)

        workflow.add_node("llm", self._llm_node)
        workflow.add_node("tools", self._tool_node)

        workflow.set_entry_point("llm")
        workflow.add_conditional_edges("llm", self._should_continue, {"tools": "tools", "end": END})
        workflow.add_edge("tools", "llm")  # Loop back after tools

        return workflow.compile()

    async def _llm_node(self, state: MinimalState) -> dict:
        """Call LLM with tools."""
        logger.info("🤖 LLM node")

        # Build simple system prompt
        system_prompt = build_base_system_prompt()

        # Bind tools
        tools = create_user_bound_tools(state["user_id"], conversation_history=state["messages"])
        llm_with_tools = self.llm.bind_tools(tools)

        # Call LLM
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response = await llm_with_tools.ainvoke(messages)

        logger.info(f"LLM called tools: {bool(getattr(response, 'tool_calls', None))}")
        return {"messages": [response]}

    async def _tool_node(self, state: MinimalState) -> dict:
        """Execute tools."""
        last_msg = state["messages"][-1]
        tool_calls = getattr(last_msg, "tool_calls", [])

        logger.info(f"🔧 Executing {len(tool_calls)} tools")

        tools = create_user_bound_tools(state["user_id"], conversation_history=state["messages"])
        tool_messages = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            logger.info(f"   → {tool_name}")

            for tool in tools:
                if tool.name == tool_name:
                    result = await tool.ainvoke(tool_call["args"])
                    tool_messages.append(
                        ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call.get("id", ""),
                            name=tool_name
                        )
                    )
                    break

        return {"messages": tool_messages}

    def _should_continue(self, state: MinimalState) -> str:
        """Check if we need to call tools."""
        last_msg = state["messages"][-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            return "tools"
        return "end"

    async def chat(self, message: str, user_id: str) -> dict[str, Any]:
        """Process message through graph."""
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id
        }

        final_state = await self.graph.ainvoke(initial_state)

        # Extract response from final message
        response_text = final_state["messages"][-1].content

        # Extract tools used
        tools_used = []
        for msg in final_state["messages"]:
            if isinstance(msg, ToolMessage):
                tools_used.append(msg.name)

        return {
            "response": response_text,
            "tools_used": list(set(tools_used)),  # Deduplicate
            "tool_calls_made": len(tools_used)
        }
```

**✅ Test 1.1**: Standalone test (outside Docker)

```bash
cd backend
uv run python -c "
import asyncio
import sys
sys.path.insert(0, 'src')

from agents.langgraph_minimal import MinimalLangGraphAgent

async def test():
    agent = MinimalLangGraphAgent()
    result = await agent.chat('how much do I weigh', 'wellness_user')
    print(f'Response: {result[\"response\"][:100]}...')
    print(f'Tools: {result[\"tools_used\"]}')
    assert result['tools_used'], '❌ NO TOOLS CALLED'
    assert 'search_health_records_by_metric' in result['tools_used']
    print('✅ Minimal agent works!')

asyncio.run(test())
"
```

**Expected Output**:
```
🤖 LLM node
🔧 Executing 1 tools
   → search_health_records_by_metric
🤖 LLM node
Response: Here are your recent body mass measurements...
Tools: ['search_health_records_by_metric']
✅ Minimal agent works!
```

**⛔ STOP**: If this test fails, DO NOT PROCEED. Fix minimal agent first.

---

### Step 1.2: Integrate Minimal Agent into Service (20 min)

**File**: `backend/src/services/redis_chat.py`

```python
# Change line 15
from ..agents import MinimalLangGraphAgent  # Instead of StatefulRAGAgent

# Change line 40
self.agent = MinimalLangGraphAgent()
```

**✅ Test 1.2**: Through Docker + API

```bash
# Rebuild
docker-compose up -d --build backend

# Wait for startup
sleep 5

# Test
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "how much do I weigh", "session_id": "test-minimal"}'
```

**Expected**: JSON response with correct weight (136-139 lbs) and tools called.

**⛔ STOP**: If API returns error or no tools called, DO NOT PROCEED. Debug minimal agent.

---

### Step 1.3: Test Streaming (10 min)

```bash
curl -X POST http://localhost:8000/api/chat/redis/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "how much do I weigh", "session_id": "test-stream"}'
```

**Expected**: Streaming tokens followed by final data with tools.

**⛔ STOP**: If streaming fails, fix it before proceeding.

---

## Phase 2: Add Redis Checkpointing (45 min)

**What**: Add state persistence to Redis WITHOUT changing any logic.

### Step 2.1: Add Checkpointer to Agent (20 min)

**File**: `backend/src/agents/langgraph_minimal.py`

```python
from langgraph.checkpoint.postgres import PostgresSaver  # Actually use Redis
from langgraph.checkpoint.base import BaseCheckpointSaver

class MinimalLangGraphAgent:
    def __init__(self, checkpointer: BaseCheckpointSaver | None = None):
        self.llm = create_health_llm()
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

    def _build_graph(self):
        # ... same as before
        return workflow.compile(checkpointer=self.checkpointer)  # Add checkpointer

    async def chat(self, message: str, user_id: str, session_id: str = "default") -> dict:
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id
        }

        # Add config for checkpointing
        config = {"configurable": {"thread_id": session_id}}
        final_state = await self.graph.ainvoke(initial_state, config)

        # ... rest same
```

### Step 2.2: Create Redis Checkpointer (15 min)

**File**: `backend/src/services/redis_connection.py`

Add method:
```python
def get_checkpointer(self):
    """Get LangGraph Redis checkpointer."""
    from langgraph.checkpoint.redis import RedisSaver
    return RedisSaver(self.get_connection())
```

Update `redis_chat.py`:
```python
self.checkpointer = self.redis_manager.get_checkpointer()
self.agent = MinimalLangGraphAgent(checkpointer=self.checkpointer)
```

**✅ Test 2.2**: Test conversation memory

```bash
# First message
curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "My goal is 150 lbs", "session_id": "checkpoint-test"}'

# Second message (should remember goal from checkpoint)
curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "Am I close to my goal?", "session_id": "checkpoint-test"}'
```

**Expected**: Second response references "150 lbs goal".

### Step 2.3: Inspect Checkpoints in Redis (10 min)

```bash
docker exec redis-wellness redis-cli --scan --pattern "langgraph:*"
```

**Expected**: See checkpoint keys for your session.

**⛔ STOP**: If checkpointing doesn't work, DO NOT add memory yet. Fix persistence first.

---

## Phase 3: Add Conversation History (30 min)

**What**: Pass conversation history to tools WITHOUT adding CoALA memory yet.

### Step 3.1: Update State Schema

```python
class ConversationState(TypedDict):
    """State with conversation history."""
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    session_id: str  # Added
```

No other changes needed - checkpointer handles history automatically!

**✅ Test 3.1**: Multi-turn conversation

```bash
# Turn 1
curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "how much do I weigh", "session_id": "conv-test"}'

# Turn 2 (references previous)
curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "Is that good?", "session_id": "conv-test"}'
```

**Expected**: Second response references weight from first turn.

**⛔ STOP**: If conversation doesn't persist, fix before adding memory.

---

## Phase 4: Add ONE Memory Type (Episodic Only) - 45 min

**What**: Add ONLY episodic memory (user preferences/goals). No semantic, no procedural yet.

### Step 4.1: Add Memory Retrieval Node

```python
class MemoryState(TypedDict):
    """State with single memory type."""
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    session_id: str
    episodic_memory: str | None  # ONLY THIS


class MemoryLangGraphAgent:
    def __init__(self, checkpointer, memory_coordinator):
        self.memory = memory_coordinator
        # ...

    def _build_graph(self):
        workflow.add_node("retrieve_memory", self._memory_node)
        workflow.add_node("llm", self._llm_node)
        workflow.add_node("tools", self._tool_node)
        workflow.add_node("store_memory", self._store_node)

        workflow.set_entry_point("retrieve_memory")
        workflow.add_edge("retrieve_memory", "llm")
        # ... rest

    async def _memory_node(self, state: MemoryState) -> dict:
        """Retrieve ONLY episodic memory."""
        if not self.memory:
            return {"episodic_memory": None}

        message = state["messages"][-1].content
        episodic = await self.memory.episodic.retrieve(
            user_id=state["user_id"],
            query=message
        )

        logger.info(f"Episodic memory: {bool(episodic)}")
        return {"episodic_memory": episodic}
```

### Step 4.2: Inject Memory into Prompt

```python
def _llm_node(self, state: MemoryState) -> dict:
    system_prompt = build_base_system_prompt()

    # Add episodic memory if present
    if state.get("episodic_memory"):
        system_prompt += f"\n\n🎯 Personal Context:\n{state['episodic_memory']}"

    # ... rest same
```

**✅ Test 4.2**: Memory injection

```bash
# Store a preference
curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "My goal is to weigh 150 lbs", "session_id": "memory-test"}'

# New session, ask about goals
curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "What are my health goals?", "session_id": "memory-test-2"}'
```

**Expected**: Second response mentions 150 lbs goal (retrieved from episodic memory).

**⛔ STOP**: If episodic memory doesn't work, DO NOT add more memory types. Fix this first.

---

## Phase 5: Add Semantic Memory (30 min)

**What**: Add semantic memory (health facts) ONLY after episodic works.

### Step 5.1: Update State

```python
class MemoryState(TypedDict):
    # ... existing fields
    episodic_memory: str | None
    semantic_memory: str | None  # NEW
```

### Step 5.2: Retrieve Both

```python
async def _memory_node(self, state: MemoryState) -> dict:
    episodic = await self.memory.episodic.retrieve(...)
    semantic = await self.memory.semantic.retrieve(query=message)  # NEW

    return {
        "episodic_memory": episodic,
        "semantic_memory": semantic
    }
```

**✅ Test 5.2**: Semantic memory

```bash
curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "What is a healthy BMI?", "session_id": "semantic-test"}'
```

**Expected**: Response includes general health knowledge from semantic memory.

**⛔ STOP**: If semantic breaks episodic, rollback and fix.

---

## Phase 6: Add Procedural Memory (30 min)

**What**: Add tool pattern learning LAST.

### Step 6.1: Update State

```python
class FullMemoryState(TypedDict):
    # ... existing
    procedural_memory: dict | None  # Tool patterns
```

### Step 6.2: Store Tool Patterns

```python
async def _store_node(self, state: FullMemoryState) -> dict:
    # ... store episodic

    # Store tool patterns
    if state.get("tools_used"):
        await self.memory.procedural.record_pattern(
            query=state["messages"][0].content,
            tools=state["tools_used"],
            success=True
        )
```

**✅ Test 6.2**: Procedural memory

```bash
# Ask same question twice
curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "how much do I weigh", "session_id": "proc-test-1"}'

curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "how much do I weigh", "session_id": "proc-test-2"}'
```

**Expected**: Second query suggests same tool pattern from procedural memory.

---

## Testing Checklist (Run After Each Phase)

```bash
# 1. Weight query (tools work)
curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "how much do I weigh", "session_id": "test-'$RANDOM'"}'

# 2. Workout query (different tools)
curl -X POST http://localhost:8000/api/chat/redis \
  -d '{"message": "when was my last workout", "session_id": "test-'$RANDOM'"}'

# 3. Stateless still works
curl -X POST http://localhost:8000/api/chat/stateless \
  -d '{"message": "how much do I weigh"}'

# 4. Frontend works
open http://localhost:3000
```

---

## Rollback Commands (If Phase Fails)

```bash
# Rollback to previous working state
git stash
git checkout HEAD -- backend/src/agents/

# Rebuild
docker-compose up -d --build backend
```

---

## Success Criteria (Final Validation)

After completing all phases:

- ✅ Weight queries return correct data (136-139 lbs)
- ✅ Tools are called (not hallucinating)
- ✅ Conversation history works across messages
- ✅ Episodic memory stores user preferences
- ✅ Semantic memory provides health knowledge
- ✅ Procedural memory learns tool patterns
- ✅ Streaming works
- ✅ Frontend displays correctly
- ✅ Can inspect checkpoints in Redis
- ✅ Stateless endpoint still works (baseline comparison)

---

## Time Estimates

| Phase | Time | Can Stop? |
|-------|------|-----------|
| 0. Preparation | 10 min | ✅ Yes |
| 1. Minimal LangGraph | 1 hour | ✅ Yes - Best stopping point |
| 2. Checkpointing | 45 min | ✅ Yes |
| 3. Conversation History | 30 min | ✅ Yes |
| 4. Episodic Memory | 45 min | ✅ Yes |
| 5. Semantic Memory | 30 min | ✅ Yes |
| 6. Procedural Memory | 30 min | ✅ Yes |

**Total**: ~4.5 hours (with testing at each gate)

**Recommended Stop Points**:
1. **After Phase 1** - Minimal agent working (best place to stop tonight)
2. **After Phase 2** - Checkpointing added
3. **After Phase 4** - One memory type working

---

## Key Learnings from Today's Failure

1. **Don't add 3 memory types at once** - We tried to add episodic, semantic, and procedural simultaneously. Failed.
2. **Test after every change** - We made multiple changes before testing. Couldn't isolate failures.
3. **Start with absolute minimum** - Even "simple" loop was too complex. Need bare bones LangGraph first.
4. **Use test gates** - Don't proceed if current step is broken.
5. **Keep stateless working** - Always have baseline to compare against.

**This time**: Add ONE thing, test it works, then add next thing.
