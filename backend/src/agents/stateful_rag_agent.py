"""
Stateful LangGraph agent with autonomous memory retrieval.

Memory is now tool-based (following Redis AI Resources pattern):
- Memory RETRIEVAL: LLM decides when to call memory tools
- Memory STORAGE: Automatic after response (episodic + procedural)
- Checkpointing: LangGraph manages conversation history

This makes memory truly autonomous - the LLM decides what context it needs.
"""

import logging
import time
from typing import Annotated, Any

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict  # Use typing_extensions for Python 3.11

from ..apple_health.query_tools import create_user_bound_tools
from ..services.episodic_memory_manager import EpisodicMemoryManager
from ..services.procedural_memory_manager import ProceduralMemoryManager
from ..utils.agent_helpers import build_base_system_prompt, create_health_llm
from ..utils.conversation_fact_extractor import get_fact_extractor
from ..utils.numeric_validator import get_numeric_validator

logger = logging.getLogger(__name__)


class MemoryState(TypedDict):
    """State with messages, user ID, episodic memory, and procedural memory."""

    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    episodic_context: str | None  # Injected into LLM prompt
    procedural_patterns: list[dict] | None  # Retrieved patterns
    execution_plan: dict | None  # Planned tool sequence
    workflow_start_time: int  # For timing workflows


class StatefulRAGAgent:
    """LangGraph-based stateful agent with checkpointing AND episodic memory."""

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver | None = None,
        episodic_memory: EpisodicMemoryManager | None = None,
        procedural_memory: ProceduralMemoryManager | None = None,
    ):
        self.llm = create_health_llm()
        self.checkpointer = checkpointer
        self.episodic = episodic_memory
        self.procedural = procedural_memory
        self.fact_extractor = get_fact_extractor()
        self.graph = self._build_graph()

        # Log initialization status
        memory_features = []
        if checkpointer:
            memory_features.append("checkpointing")
        if episodic_memory:
            memory_features.append("episodic memory")
        if procedural_memory:
            memory_features.append("procedural memory")

        if memory_features:
            logger.info(
                f"✅ StatefulRAGAgent initialized WITH {', '.join(memory_features)}"
            )
        else:
            logger.info("✅ StatefulRAGAgent initialized (no memory features)")

    def _build_graph(self):
        """
        Build graph with autonomous memory retrieval.

        New flow (memory as tools):
        1. LLM entry point (with ALL tools including memory)
        2. LLM decides: call tools (health OR memory) or finish?
        3. If tools: execute and loop back to LLM
        4. If finish: reflect → store episodic → store procedural → END

        Memory retrieval is now autonomous - LLM calls memory tools when needed.
        Memory storage still automatic at end (reflection-based).
        """
        workflow = StateGraph(MemoryState)

        # Core nodes (LLM + tools)
        workflow.add_node("llm", self._llm_node)
        workflow.add_node("tools", self._tool_node)

        # Storage nodes (keep these - automatic after response)
        if self.episodic:
            workflow.add_node("store_episodic", self._store_episodic_node)
        if self.procedural:
            workflow.add_node("reflect", self._reflect_node)
            workflow.add_node("store_procedural", self._store_procedural_node)

        # Build flow: LLM entry point → tools loop → storage at end
        workflow.set_entry_point("llm")  # Start with LLM (not memory retrieval!)

        # LLM decides: call tools or finish?
        if self.episodic and self.procedural:
            # Full memory: llm → tools → llm (loop) → reflect → store_episodic → store_procedural → END
            workflow.add_conditional_edges(
                "llm", self._should_continue, {"tools": "tools", "end": "reflect"}
            )
            workflow.add_edge("tools", "llm")
            workflow.add_edge("reflect", "store_episodic")
            workflow.add_edge("store_episodic", "store_procedural")
            workflow.add_edge("store_procedural", END)
        elif self.episodic:
            # Episodic only: llm → tools → llm (loop) → store_episodic → END
            workflow.add_conditional_edges(
                "llm",
                self._should_continue,
                {"tools": "tools", "end": "store_episodic"},
            )
            workflow.add_edge("tools", "llm")
            workflow.add_edge("store_episodic", END)
        else:
            # No memory storage: llm → tools → llm (loop) → END
            workflow.add_conditional_edges(
                "llm", self._should_continue, {"tools": "tools", "end": END}
            )
            workflow.add_edge("tools", "llm")

        return workflow.compile(checkpointer=self.checkpointer)

    async def _reflect_node(self, state: MemoryState) -> dict[str, Any]:
        """Evaluate workflow success for procedural memory storage."""
        if not self.procedural:
            return {}

        logger.info("🤔 Reflecting on workflow success...")

        # Extract execution metrics
        tools_used = [
            msg.name for msg in state["messages"] if isinstance(msg, ToolMessage)
        ]
        tool_results = [
            {"name": msg.name, "content": msg.content}
            for msg in state["messages"]
            if isinstance(msg, ToolMessage)
        ]
        response_generated = any(
            hasattr(msg, "content") and msg.content
            for msg in state["messages"]
            if not isinstance(msg, HumanMessage | ToolMessage)
        )

        start_time = state.get("workflow_start_time", 0)
        execution_time_ms = int(time.time() * 1000) - start_time if start_time else 0

        # Evaluate success
        evaluation = self.procedural.evaluate_workflow(
            tools_used=tools_used,
            tool_results=tool_results,
            response_generated=response_generated,
            execution_time_ms=execution_time_ms,
        )

        logger.info(
            f"✅ Workflow evaluation: success={evaluation['success']}, score={evaluation['success_score']:.2%}"
        )
        return {}  # Evaluation stored in state for store_procedural_node

    async def _store_episodic_node(self, state: MemoryState) -> dict[str, Any]:
        """Extract facts and store in episodic memory after LLM response."""
        logger.info("💾 Storing episodic memory...")

        if not self.episodic:
            print("⚠️ NO EPISODIC MEMORY CONFIGURED")
            logger.warning("⚠️ No episodic memory configured, skipping storage")
            return {}

        print(f"💾 Storing interaction (state has {len(state['messages'])} messages)")
        logger.info("💾 Storing interaction in episodic memory...")
        logger.info(f"   State has {len(state['messages'])} messages")

        try:
            # Extract user message (find last HumanMessage)
            user_msg = None
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    user_msg = msg
                    break

            if not user_msg:
                print("⚠️ NO USER MESSAGE FOUND")
                logger.warning("⚠️ No user message found to extract facts from")
                return {}

            print(f"✅ Found user message: {user_msg.content[:100]}")
            logger.info(f"   Found user message: {user_msg.content[:100]}")

            # Extract facts (goals) from user message
            facts = self.fact_extractor.extract_facts([user_msg])
            user_id = state["user_id"]

            print(f"📊 Extracted {len(facts.get('goals', []))} goals")
            logger.info(f"   Extracted facts: {len(facts.get('goals', []))} goals")

            # Store each goal in episodic memory
            for goal in facts.get("goals", []):
                print(f"💾 Storing goal: {goal}")

                await self.episodic.store_goal(
                    user_id=user_id,
                    metric="weight",  # For now, assume weight goals
                    value=float(goal["value"]),
                    unit=goal["unit"],
                )
                logger.info(f"💾 Stored goal: {goal['value']} {goal['unit']}")

            return {}

        except Exception as e:
            logger.error(f"❌ Memory storage failed: {e}")
            return {}

    async def _store_procedural_node(self, state: MemoryState) -> dict[str, Any]:
        """Store successful workflow pattern in procedural memory."""
        if not self.procedural:
            return {}

        logger.info("💾 Storing procedural pattern...")

        try:
            # Get user query
            user_msg = None
            for msg in reversed(state["messages"]):
                if isinstance(msg, HumanMessage):
                    user_msg = msg
                    break

            if not user_msg:
                return {}

            # Extract workflow metrics
            tools_used = [
                msg.name for msg in state["messages"] if isinstance(msg, ToolMessage)
            ]
            tool_results = [
                {"name": msg.name, "content": msg.content}
                for msg in state["messages"]
                if isinstance(msg, ToolMessage)
            ]
            response_generated = any(
                hasattr(msg, "content") and msg.content
                for msg in state["messages"]
                if not isinstance(msg, HumanMessage | ToolMessage)
            )

            start_time = state.get("workflow_start_time", 0)
            execution_time_ms = (
                int(time.time() * 1000) - start_time if start_time else 0
            )

            # Evaluate success
            evaluation = self.procedural.evaluate_workflow(
                tools_used=tools_used,
                tool_results=tool_results,
                response_generated=response_generated,
                execution_time_ms=execution_time_ms,
            )

            # Store if successful
            if evaluation.get("success"):
                await self.procedural.store_pattern(
                    query=user_msg.content,
                    tools_used=tools_used,
                    success_score=evaluation.get("success_score", 0.0),
                    execution_time_ms=execution_time_ms,
                )
                logger.info(
                    f"✅ Stored procedural pattern (score: {evaluation.get('success_score'):.2%})"
                )
            else:
                logger.info(
                    f"⏭️ Skipped procedural storage (score: {evaluation.get('success_score'):.2%})"
                )

            return {}

        except Exception as e:
            logger.error(f"❌ Procedural storage failed: {e}")
            return {}

    async def _llm_node(self, state: MemoryState) -> dict[str, list[BaseMessage]]:
        """
        Call LLM with ALL tools (health + memory).

        Memory is now tool-based - LLM decides when to retrieve memory.
        No more hardcoded episodic context injection.
        """
        logger.info("🤖 LLM node")
        logger.info(f"   State has {len(state['messages'])} messages")

        # Log message types for debugging
        for i, msg in enumerate(state["messages"]):
            msg_type = type(msg).__name__
            content_preview = (
                str(msg.content)[:80] if hasattr(msg, "content") else "no content"
            )
            logger.info(f"   [{i}] {msg_type}: {content_preview}")

        # Build system prompt
        system_prompt = build_base_system_prompt()

        # DEBUG: Log system prompt
        logger.warning(f"📝 STATEFUL SYSTEM PROMPT:\n{system_prompt[:500]}...")

        # Bind ALL tools (health + memory)
        # Memory retrieval is now autonomous via tools
        tools = create_user_bound_tools(
            state["user_id"], conversation_history=state["messages"]
        )
        llm_with_tools = self.llm.bind_tools(tools)

        logger.info(f"   🛠️ LLM has access to {len(tools)} tools (health + memory)")

        # Call LLM with limited history (last 10 messages for demo)
        # Keep only recent messages to avoid context bloat
        recent_messages = (
            state["messages"][-10:]
            if len(state["messages"]) > 10
            else state["messages"]
        )
        messages = [SystemMessage(content=system_prompt)] + recent_messages
        logger.info(
            f"   Calling LLM with {len(messages)} total messages (system + {len(recent_messages)} recent history, trimmed from {len(state['messages'])})"
        )
        response = await llm_with_tools.ainvoke(messages)

        logger.info(f"LLM called tools: {bool(getattr(response, 'tool_calls', None))}")
        return {"messages": [response]}

    async def _tool_node(self, state: MemoryState) -> dict[str, list[ToolMessage]]:
        """Execute tools."""
        last_msg = state["messages"][-1]
        tool_calls = getattr(last_msg, "tool_calls", [])

        logger.info(f"🔧 Executing {len(tool_calls)} tools")

        tools = create_user_bound_tools(
            state["user_id"], conversation_history=state["messages"]
        )
        tool_messages = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            logger.info(f"   → {tool_name}")

            tool_found = False
            for tool in tools:
                if tool.name == tool_name:
                    try:
                        result = await tool.ainvoke(tool_call["args"])
                        tool_messages.append(
                            ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call.get("id", ""),
                                name=tool_name,
                            )
                        )
                        tool_found = True
                    except Exception as e:
                        logger.error(f"❌ Tool {tool_name} failed: {e}")
                        tool_messages.append(
                            ToolMessage(
                                content=f"Error: {str(e)}",
                                tool_call_id=tool_call.get("id", ""),
                                name=tool_name,
                            )
                        )
                        tool_found = True
                    break

            if not tool_found:
                logger.warning(f"⚠️ Tool {tool_name} not found")

        return {"messages": tool_messages}

    def _should_continue(self, state: MemoryState) -> str:
        """Check if we need to call tools."""
        last_msg = state["messages"][-1]
        has_tool_calls = hasattr(last_msg, "tool_calls") and last_msg.tool_calls

        result = "tools" if has_tool_calls else "end"
        print(
            f"🔀 _should_continue returning: {result} (has_tool_calls={has_tool_calls})"
        )

        return result

    async def chat(
        self, message: str, user_id: str, session_id: str = "default"
    ) -> dict[str, Any]:
        """Process message through graph with episodic memory."""
        print("=" * 100)
        print(f"🎯 CHAT METHOD CALLED: message='{message[:50]}', session={session_id}")
        print("=" * 100)
        logger.info(
            f"🎯 StatefulRAGAgent.chat() called: message='{message[:50]}...', session_id={session_id}"
        )

        # PRE-ROUTE: Check if this is a goal-setting or goal-retrieval statement
        from ..utils.intent_router import (
            extract_goal_from_statement,
            should_bypass_tools,
        )

        should_bypass, direct_response, intent = await should_bypass_tools(message)

        if should_bypass and intent == "goal_setting":
            logger.info(
                "✅ Bypassed tools for goal-setting statement - storing goal in Redis"
            )

            # Extract and store the goal in episodic memory
            goal_text = extract_goal_from_statement(message)

            try:
                from ..services.episodic_memory_manager import get_episodic_memory

                get_episodic_memory()

                # Store as a generic text goal (not metric-specific)
                # We create a simple memory entry with the goal text
                import json

                from ..services.redis_connection import get_redis_manager
                from ..utils.redis_keys import RedisKeys
                from ..utils.time_utils import get_utc_timestamp

                redis_manager = get_redis_manager()
                timestamp = get_utc_timestamp()
                memory_key = RedisKeys.episodic_memory(user_id, "goal", timestamp)

                # Generate embedding for semantic search
                from ..services.embedding_service import get_embedding_service

                embedding_service = get_embedding_service()
                embedding = await embedding_service.generate_embedding(
                    f"User's goal: {goal_text}"
                )

                if embedding:
                    import numpy as np

                    memory_data = {
                        "user_id": user_id,
                        "event_type": "goal",
                        "timestamp": timestamp,
                        "description": f"User's goal: {goal_text}",
                        "metadata": json.dumps({"goal_text": goal_text}),
                        "embedding": np.array(embedding, dtype=np.float32).tobytes(),
                    }

                    with redis_manager.get_connection() as redis_client:
                        redis_client.hset(memory_key, mapping=memory_data)
                        # Set TTL (7 months)
                        from ..config import get_settings

                        settings = get_settings()
                        redis_client.expire(
                            memory_key, settings.redis_session_ttl_seconds
                        )

                    logger.info(f"💾 Stored goal in Redis: '{goal_text}'")

            except Exception as e:
                logger.error(f"❌ Failed to store goal: {e}", exc_info=True)

            # Calculate token stats for the bypassed response
            token_stats = {}
            try:
                from ..utils.token_manager import get_token_manager

                token_manager = get_token_manager()

                # Count tokens for user message + assistant response
                messages_for_counting = [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": direct_response},
                ]

                token_stats = token_manager.get_usage_stats(messages_for_counting)
                logger.info(
                    f"📊 Token stats (bypassed): {token_stats.get('token_count', 0)} tokens ({token_stats.get('usage_percent', 0):.1f}%)"
                )
            except Exception as e:
                logger.warning(
                    f"Could not calculate token stats for bypassed response: {e}"
                )
                token_stats = {}

            return {
                "response": direct_response,
                "tools_used": [],
                "tool_calls_made": 0,
                "memory_stats": {
                    "semantic_hits": 0,
                    "goals_stored": 1,  # We're storing a goal
                    "procedural_patterns_used": 0,
                    "memory_type": "none",
                    "memory_types": [],
                    "short_term_available": False,
                },
                "token_stats": token_stats,
                "validation": {
                    "valid": True,
                    "score": 1.0,
                    "hallucinations_detected": 0,
                    "numbers_validated": 0,
                    "total_numbers": 0,
                },
            }

        if should_bypass and intent == "goal_retrieval":
            logger.info(
                "✅ Bypassed tools for goal retrieval - instant response from Redis"
            )

            # Calculate token stats
            token_stats = {}
            try:
                from ..utils.token_manager import get_token_manager

                token_manager = get_token_manager()
                messages_for_counting = [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": direct_response},
                ]
                token_stats = token_manager.get_usage_stats(messages_for_counting)
            except Exception as e:
                logger.warning(f"Could not calculate token stats: {e}")
                token_stats = {}

            return {
                "response": direct_response,
                "tools_used": [],
                "tool_calls_made": 0,
                "memory_stats": {
                    "semantic_hits": 0,
                    "goals_stored": 0,
                    "procedural_patterns_used": 0,
                    "memory_type": "none",
                    "memory_types": [],
                    "short_term_available": False,
                },
                "token_stats": token_stats,
                "validation": {
                    "valid": True,
                    "score": 1.0,
                    "hallucinations_detected": 0,
                    "numbers_validated": 0,
                    "total_numbers": 0,
                },
            }

        input_state = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "episodic_context": None,  # Will be populated by retrieve_memory node
            "procedural_patterns": None,  # Will be populated by retrieve_procedural node
            "execution_plan": None,  # Will be populated by retrieve_procedural node
            "workflow_start_time": int(time.time() * 1000),  # For procedural timing
        }

        # Add config for checkpointing with recursion limit to prevent infinite loops
        # recursion_limit=16 allows ~8 tool-calling cycles (each cycle = llm + tools = 2 nodes)
        config = (
            {"configurable": {"thread_id": session_id}, "recursion_limit": 16}
            if self.checkpointer
            else {"recursion_limit": 16}
        )

        if self.checkpointer:
            logger.info(f"📝 Using checkpoint thread_id: {session_id}")
        logger.info("⚠️ Recursion limit: 16 iterations (~8 tool cycles)")

        # Use ainvoke with recursion limit (max 16 iterations = ~8 tool-calling cycles)
        final_state = await self.graph.ainvoke(input_state, config)
        logger.info(f"📊 Final state has {len(final_state['messages'])} messages")

        # Extract response from final message
        response_text = final_state["messages"][-1].content

        # Extract tools used and tool results
        tools_used = []
        tool_results = []
        for msg in final_state["messages"]:
            if isinstance(msg, ToolMessage):
                tools_used.append(msg.name)
                tool_results.append({"name": msg.name, "content": msg.content})

        # Validate response for numeric hallucinations
        validator = get_numeric_validator()
        validation_result = validator.validate_response(
            response_text=response_text,
            tool_results=tool_results,
            strict=False,
        )

        # Log validation results
        if not validation_result["valid"]:
            logger.warning(
                f"⚠️ Validation failed (score: {validation_result['score']:.2%}) - "
                f"Hallucinations detected: {len(validation_result.get('hallucinations', []))}"
            )
            for hallucination in validation_result.get("hallucinations", []):
                logger.warning(f"   Hallucinated number: {hallucination}")
        else:
            logger.info(
                f"✅ Validation passed (score: {validation_result['score']:.2%})"
            )

        # Calculate memory stats based on ACTUAL TOOL CALLS (autonomous memory retrieval)
        # Memory is now retrieved via tools, not hardcoded state fields
        episodic_retrieved = "get_my_goals" in tools_used
        procedural_retrieved = "get_tool_suggestions" in tools_used

        goals_stored = len(
            [
                msg
                for msg in final_state["messages"]
                if "goal" in str(getattr(msg, "content", "")).lower()
                and isinstance(msg, HumanMessage)
            ]
        )
        procedural_patterns_used = 1 if procedural_retrieved else 0

        # Determine ALL memory types actually used (can be multiple)
        memory_types_used = []

        # Check for episodic memory tool (get_my_goals)
        if episodic_retrieved:
            memory_types_used.append("episodic")

        # Check for procedural memory tool (get_tool_suggestions)
        if procedural_retrieved:
            memory_types_used.append("procedural")

        # NOTE: Health data tools are shown separately in tools_used, not as memory types
        # We don't include 'semantic' in memory_types anymore since health tools are explicit

        # Check for short-term memory (conversation history in LangGraph state)
        # Short-term is the immediate conversation context (current session)
        conversation_history_available = (
            len(final_state["messages"]) > 2
        )  # More than just user question + AI response
        if conversation_history_available:
            memory_types_used.append("short-term")

        # For backwards compatibility, keep single memory_type (primary one)
        memory_type = memory_types_used[0] if memory_types_used else "none"

        logger.info(
            f"💾 Memory stats: episodic_tool={episodic_retrieved}, procedural_tool={procedural_retrieved}, "
            f"short_term={conversation_history_available}, memory_types={memory_types_used}, "
            f"primary={memory_type}, tools_used={tools_used}"
        )

        # Calculate token stats from LangGraph state messages
        token_stats = {}
        try:
            from ..utils.token_manager import get_token_manager

            token_manager = get_token_manager()

            # Convert LangGraph messages to format expected by token manager
            messages_for_counting = []
            for msg in final_state["messages"]:
                if isinstance(msg, HumanMessage):
                    messages_for_counting.append(
                        {"role": "user", "content": msg.content}
                    )
                elif isinstance(msg, SystemMessage):
                    messages_for_counting.append(
                        {"role": "system", "content": msg.content}
                    )
                elif hasattr(msg, "content") and not isinstance(msg, ToolMessage):
                    messages_for_counting.append(
                        {"role": "assistant", "content": msg.content}
                    )

            # Get token stats using token manager
            token_stats = token_manager.get_usage_stats(messages_for_counting)
            logger.info(
                f"📊 Token stats: {token_stats.get('token_count', 0)} tokens ({token_stats.get('usage_percent', 0):.1f}%)"
            )
        except Exception as e:
            logger.warning(f"Could not calculate token stats: {e}")
            token_stats = {}

        return {
            "response": response_text,
            "tools_used": list(set(tools_used)),  # Deduplicate
            "tool_calls_made": len(tools_used),
            "memory_stats": {
                "semantic_hits": 1
                if episodic_retrieved
                else 0,  # Keep for backwards compatibility
                "goals_stored": goals_stored,
                "procedural_patterns_used": procedural_patterns_used,
                "memory_type": memory_type,  # Primary memory type (backwards compatibility)
                "memory_types": memory_types_used,  # NEW: All memory types actually used
                "short_term_available": len(final_state["messages"])
                > 1,  # Conversation history exists
            },
            "token_stats": token_stats,  # NEW: Token usage stats
            "validation": {
                "valid": validation_result["valid"],
                "score": validation_result["score"],
                "hallucinations_detected": len(
                    validation_result.get("hallucinations", [])
                ),
                "numbers_validated": validation_result.get("stats", {}).get(
                    "matched", 0
                ),
                "total_numbers": validation_result.get("stats", {}).get(
                    "total_numbers", 0
                ),
            },
        }

    async def chat_stream(
        self, message: str, user_id: str, session_id: str = "default"
    ):
        """Stream tokens through graph (simplified - just return full response for now)."""
        # For Phase 1, just use non-streaming and yield the result
        # We'll add proper streaming in later phases
        result = await self.chat(message, user_id, session_id)

        # Yield the response as if it were streaming
        yield {"type": "token", "content": result["response"]}

        # Yield done event
        yield {
            "type": "done",
            "data": {
                "response": result["response"],
                "tools_used": result["tools_used"],
                "tool_calls_made": result["tool_calls_made"],
                "memory_stats": result.get("memory_stats", {}),
                "token_stats": result.get(
                    "token_stats", {}
                ),  # NEW: Include token stats in stream
            },
        }
