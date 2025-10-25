"""
Stateful LangGraph agent with episodic AND procedural memory.

Now includes:
- Checkpointing (conversation history)
- Episodic memory (user goals, preferences)
- Procedural memory (learned workflows with orchestration)
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
        """Build graph with episodic AND procedural memory orchestration."""
        workflow = StateGraph(MemoryState)

        # Add all nodes
        if self.episodic:
            workflow.add_node("retrieve_episodic", self._retrieve_episodic_node)
            workflow.add_node("store_episodic", self._store_episodic_node)

        if self.procedural:
            workflow.add_node("retrieve_procedural", self._retrieve_procedural_node)
            workflow.add_node("reflect", self._reflect_node)
            workflow.add_node("store_procedural", self._store_procedural_node)

        workflow.add_node("llm", self._llm_node)
        workflow.add_node("tools", self._tool_node)

        # Build graph flow with orchestration
        if self.episodic and self.procedural:
            # Full orchestration: retrieve_episodic → retrieve_procedural → llm → tools → reflect → store_episodic → store_procedural → END
            workflow.set_entry_point("retrieve_episodic")
            workflow.add_edge("retrieve_episodic", "retrieve_procedural")
            workflow.add_edge("retrieve_procedural", "llm")
            workflow.add_conditional_edges(
                "llm", self._should_continue, {"tools": "tools", "end": "reflect"}
            )
            workflow.add_edge("tools", "llm")
            workflow.add_edge("reflect", "store_episodic")
            workflow.add_edge("store_episodic", "store_procedural")
            workflow.add_edge("store_procedural", END)
        elif self.episodic:
            # Episodic only (original flow)
            workflow.set_entry_point("retrieve_episodic")
            workflow.add_edge("retrieve_episodic", "llm")
            workflow.add_conditional_edges(
                "llm",
                self._should_continue,
                {"tools": "tools", "end": "store_episodic"},
            )
            workflow.add_edge("tools", "llm")
            workflow.add_edge("store_episodic", END)
        else:
            # No memory
            workflow.set_entry_point("llm")
            workflow.add_conditional_edges(
                "llm", self._should_continue, {"tools": "tools", "end": END}
            )
            workflow.add_edge("tools", "llm")

        return workflow.compile(checkpointer=self.checkpointer)

    async def _retrieve_episodic_node(self, state: MemoryState) -> dict:
        """Retrieve episodic memory before LLM call."""
        if not self.episodic:
            return {"episodic_context": None}

        logger.info("🧠 Retrieving episodic memory...")

        # Get user's message as query
        user_message = state["messages"][-1].content if state["messages"] else ""
        user_id = state["user_id"]

        try:
            # Retrieve goals from episodic memory
            result = await self.episodic.retrieve_goals(
                user_id=user_id, query=user_message, top_k=3
            )

            context = result.get("context")
            if context:
                logger.info(f"✅ Retrieved {result['hits']} episodic memories")
            else:
                logger.info("ℹ️ No episodic memories found")

            return {"episodic_context": context}

        except Exception as e:
            logger.error(f"❌ Memory retrieval failed: {e}")
            return {"episodic_context": None}

    async def _retrieve_procedural_node(self, state: MemoryState) -> dict:
        """Retrieve procedural patterns and create execution plan."""
        if not self.procedural:
            return {
                "procedural_patterns": None,
                "execution_plan": None,
                "workflow_start_time": int(time.time() * 1000),
            }

        logger.info("🔧 Retrieving procedural patterns...")
        user_message = state["messages"][-1].content if state["messages"] else ""
        start_time = int(time.time() * 1000)

        try:
            result = await self.procedural.retrieve_patterns(
                query=user_message, top_k=3
            )
            patterns = result.get("patterns", [])
            plan = result.get("plan")

            if patterns:
                logger.info(f"✅ Retrieved {len(patterns)} procedural patterns")
                if plan:
                    logger.info(
                        f"📋 Execution plan: {plan.get('suggested_tools')} (confidence: {plan.get('confidence'):.2%})"
                    )
            else:
                logger.info("ℹ️ No procedural patterns found")

            return {
                "procedural_patterns": patterns,
                "execution_plan": plan,
                "workflow_start_time": start_time,
            }

        except Exception as e:
            logger.error(f"❌ Procedural retrieval failed: {e}")
            return {
                "procedural_patterns": None,
                "execution_plan": None,
                "workflow_start_time": start_time,
            }

    async def _reflect_node(self, state: MemoryState) -> dict:
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

    async def _store_episodic_node(self, state: MemoryState) -> dict:
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

    async def _store_procedural_node(self, state: MemoryState) -> dict:
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

    async def _llm_node(self, state: MemoryState) -> dict:
        """Call LLM with tools and episodic context."""
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

        # DEBUG: Log system prompt to verify TOOL-FIRST POLICY is included
        logger.warning(f"📝 STATEFUL SYSTEM PROMPT:\n{system_prompt[:500]}...")

        # Inject episodic memory context
        if state.get("episodic_context"):
            system_prompt += (
                f"\n\n📋 USER CONTEXT (from memory):\n{state['episodic_context']}"
            )
            logger.info("✅ Injected episodic context into prompt")

        # Bind tools
        tools = create_user_bound_tools(
            state["user_id"], conversation_history=state["messages"]
        )
        llm_with_tools = self.llm.bind_tools(tools)

        # Call LLM
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        logger.info(
            f"   Calling LLM with {len(messages)} total messages (system + {len(state['messages'])} history)"
        )
        response = await llm_with_tools.ainvoke(messages)

        logger.info(f"LLM called tools: {bool(getattr(response, 'tool_calls', None))}")
        return {"messages": [response]}

    async def _tool_node(self, state: MemoryState) -> dict:
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

            for tool in tools:
                if tool.name == tool_name:
                    result = await tool.ainvoke(tool_call["args"])
                    tool_messages.append(
                        ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call.get("id", ""),
                            name=tool_name,
                        )
                    )
                    break

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
        input_state = {
            "messages": [HumanMessage(content=message)],
            "user_id": user_id,
            "episodic_context": None,  # Will be populated by retrieve_memory node
            "procedural_patterns": None,  # Will be populated by retrieve_procedural node
            "execution_plan": None,  # Will be populated by retrieve_procedural node
            "workflow_start_time": int(time.time() * 1000),  # For procedural timing
        }

        # Add config for checkpointing
        config = (
            {"configurable": {"thread_id": session_id}} if self.checkpointer else None
        )

        if config:
            logger.info(f"📝 Using checkpoint thread_id: {session_id}")

        # Use ainvoke with MemorySaver (async-compatible checkpointer)
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

        # Calculate memory stats
        episodic_retrieved = final_state.get("episodic_context") is not None
        procedural_retrieved = final_state.get("procedural_patterns") is not None
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

        # Check for episodic memory (past conversations from Redis)
        if episodic_retrieved:
            memory_types_used.append("episodic")

        # Check for procedural memory (learned tool-calling patterns)
        if procedural_retrieved:
            memory_types_used.append("procedural")

        # Check for semantic memory (health data accessed via tools)
        health_tools = [
            "search_health_records",
            "search_workouts",
            "search_health_records_by_metric",
        ]
        semantic_used = any(tool in health_tools for tool in tools_used)
        if semantic_used:
            memory_types_used.append("semantic")

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
            f"💾 Memory stats: episodic={episodic_retrieved}, procedural={procedural_retrieved}, "
            f"semantic={semantic_used}, short_term={conversation_history_available}, "
            f"memory_types={memory_types_used}, primary={memory_type}, procedural_patterns_used={procedural_patterns_used}"
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
