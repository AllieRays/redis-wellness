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
from ..utils.intent_bypass_handler import handle_intent_bypass
from ..utils.numeric_validator import get_numeric_validator
from ..utils.validation_retry import build_validation_result
from .constants import (
    CONVERSATION_HISTORY_LIMIT,
    DEFAULT_SESSION_ID,
    LANGGRAPH_RECURSION_LIMIT,
    LOG_SYSTEM_PROMPT_PREVIEW_LENGTH,
    VALIDATION_STRICT_MODE,
)

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
            logger.warning("⚠️ No episodic memory configured, skipping storage")
            return {}

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
                logger.warning("⚠️ No user message found to extract facts from")
                return {}

            logger.info(f"   Found user message: {user_msg.content[:100]}")

            # Extract facts (goals) from user message
            facts = self.fact_extractor.extract_facts([user_msg])
            user_id = state["user_id"]

            logger.info(f"   Extracted facts: {len(facts.get('goals', []))} goals")

            # Store each goal in episodic memory
            for goal in facts.get("goals", []):
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

        logger.debug(
            f"📝 Stateful system prompt preview:\n{system_prompt[:LOG_SYSTEM_PROMPT_PREVIEW_LENGTH]}..."
        )

        # Bind ALL tools (health + memory)
        # Memory retrieval is now autonomous via tools
        tools = create_user_bound_tools(
            state["user_id"], conversation_history=state["messages"]
        )
        llm_with_tools = self.llm.bind_tools(tools)

        logger.info(f"   🛠️ LLM has access to {len(tools)} tools (health + memory)")

        # Call LLM with limited history to avoid context bloat
        # Keep only recent messages (configurable limit)
        recent_messages = (
            state["messages"][-CONVERSATION_HISTORY_LIMIT:]
            if len(state["messages"]) > CONVERSATION_HISTORY_LIMIT
            else state["messages"]
        )
        messages = [SystemMessage(content=system_prompt)] + recent_messages
        logger.debug(
            f"💬 Stateful calling LLM: {len(messages)} total messages "
            f"(system + {len(recent_messages)} recent, trimmed from {len(state['messages'])})"
        )
        response = await llm_with_tools.ainvoke(messages)

        has_tool_calls = bool(getattr(response, "tool_calls", None))
        logger.debug(f"⚙️ Stateful LLM response: tool_calls={has_tool_calls}")
        return {"messages": [response]}

    async def _tool_node(self, state: MemoryState) -> dict[str, list[ToolMessage]]:
        """Execute tools."""
        last_msg = state["messages"][-1]
        tool_calls = getattr(last_msg, "tool_calls", [])

        logger.info(f"🔧 Stateful executing {len(tool_calls)} tool(s)")

        tools = create_user_bound_tools(
            state["user_id"], conversation_history=state["messages"]
        )
        tool_messages = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            logger.info(f"🔧 Stateful tool: {tool_name}")

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
        logger.debug(f"🔀 Stateful routing: {result} (has_tool_calls={has_tool_calls})")

        return result

    async def chat(
        self, message: str, user_id: str, session_id: str = DEFAULT_SESSION_ID
    ) -> dict[str, Any]:
        """Process message through graph with episodic memory."""
        logger.info(
            f"🎯 Stateful agent processing: session={session_id}, message='{message[:50]}...'"
        )

        try:
            # PRE-ROUTE: Check if this is a goal-setting or goal-retrieval statement
            bypass_result = await handle_intent_bypass(
                message=message, user_id=user_id, is_stateful=True
            )

            if bypass_result:
                return bypass_result

            input_state = {
                "messages": [HumanMessage(content=message)],
                "user_id": user_id,
                "episodic_context": None,  # Will be populated by retrieve_memory node
                "procedural_patterns": None,  # Will be populated by retrieve_procedural node
                "execution_plan": None,  # Will be populated by retrieve_procedural node
                "workflow_start_time": int(time.time() * 1000),  # For procedural timing
            }

            # Add config for checkpointing with recursion limit to prevent infinite loops
            config = (
                {
                    "configurable": {"thread_id": session_id},
                    "recursion_limit": LANGGRAPH_RECURSION_LIMIT,
                }
                if self.checkpointer
                else {"recursion_limit": LANGGRAPH_RECURSION_LIMIT}
            )

            if self.checkpointer:
                logger.debug(f"📝 Stateful using checkpoint thread: {session_id}")
            logger.debug(
                f"⚠️ Stateful recursion limit: {LANGGRAPH_RECURSION_LIMIT} iterations "
                f"(~{LANGGRAPH_RECURSION_LIMIT // 2} tool cycles)"
            )

            # Use ainvoke with recursion limit
            final_state = await self.graph.ainvoke(input_state, config)
            logger.info(
                f"✅ Stateful workflow complete: {len(final_state['messages'])} messages in final state"
            )

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
                strict=VALIDATION_STRICT_MODE,
            )

            # Log validation results
            if not validation_result["valid"]:
                logger.warning(
                    f"⚠️ Stateful validation failed (score: {validation_result['score']:.2%}) - "
                    f"Hallucinations: {len(validation_result.get('hallucinations', []))}"
                )
                for hallucination in validation_result.get("hallucinations", []):
                    logger.warning(f"   Hallucinated number: {hallucination}")
            else:
                logger.info(
                    f"✅ Stateful validation passed (score: {validation_result['score']:.2%})"
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
                f"💾 Stateful memory stats: episodic={episodic_retrieved}, procedural={procedural_retrieved}, "
                f"short_term={conversation_history_available}, types={memory_types_used}, tools={tools_used}"
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
                    f"📊 Stateful token stats: {token_stats.get('token_count', 0)} tokens "
                    f"({token_stats.get('usage_percent', 0):.1f}% of context)"
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
                "validation": build_validation_result(
                    validation_result,
                    {
                        "valid": True,
                        "date_mismatches": [],
                    },  # Date validation placeholder
                ),
            }

        except Exception as e:
            logger.error(f"❌ Stateful agent error: {e}", exc_info=True)
            # Return error response in same format
            from ..utils.agent_helpers import build_error_response

            return build_error_response(e, "stateful_rag_agent")

    async def chat_stream(
        self, message: str, user_id: str, session_id: str = DEFAULT_SESSION_ID
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
