"""
Stateful LangGraph agent with episodic memory.

Now includes:
- Checkpointing (conversation history)
- Episodic memory (user goals, preferences)
"""

import logging
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
from ..utils.agent_helpers import build_base_system_prompt, create_health_llm
from ..utils.conversation_fact_extractor import get_fact_extractor
from ..utils.numeric_validator import get_numeric_validator

logger = logging.getLogger(__name__)


class MemoryState(TypedDict):
    """State with messages, user ID, and episodic memory context."""

    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    episodic_context: str | None  # Injected into LLM prompt


class StatefulRAGAgent:
    """LangGraph-based stateful agent with checkpointing AND episodic memory."""

    def __init__(
        self,
        checkpointer: BaseCheckpointSaver | None = None,
        episodic_memory: EpisodicMemoryManager | None = None,
    ):
        self.llm = create_health_llm()
        self.checkpointer = checkpointer
        self.episodic = episodic_memory
        self.fact_extractor = get_fact_extractor()
        self.graph = self._build_graph()

        if checkpointer and episodic_memory:
            logger.info(
                "✅ StatefulRAGAgent initialized WITH checkpointing AND episodic memory"
            )
        elif checkpointer:
            logger.info(
                "✅ StatefulRAGAgent initialized WITH checkpointing (no episodic memory)"
            )
        else:
            logger.info("✅ StatefulRAGAgent initialized (no checkpointing, no memory)")

    def _build_graph(self):
        """Build graph with episodic memory: Retrieve → LLM → Tools → Store → End."""
        workflow = StateGraph(MemoryState)

        # Add memory nodes if episodic memory is available
        if self.episodic:
            workflow.add_node("retrieve_memory", self._retrieve_memory_node)
            workflow.add_node("store_memory", self._store_memory_node)

        workflow.add_node("llm", self._llm_node)
        workflow.add_node("tools", self._tool_node)

        # Set entry point based on memory availability
        if self.episodic:
            workflow.set_entry_point("retrieve_memory")
            workflow.add_edge("retrieve_memory", "llm")
        else:
            workflow.set_entry_point("llm")

        # LLM → Tools (if needed) or Store Memory / End
        if self.episodic:
            workflow.add_conditional_edges(
                "llm",
                self._should_continue,
                {"tools": "tools", "end": "store_memory"},
            )
            workflow.add_edge("tools", "llm")  # Tools loop back to LLM
            workflow.add_edge("store_memory", END)  # Store memory then end
        else:
            workflow.add_conditional_edges(
                "llm", self._should_continue, {"tools": "tools", "end": END}
            )
            workflow.add_edge("tools", "llm")

        # Compile with checkpointer if provided
        return workflow.compile(checkpointer=self.checkpointer)

    async def _retrieve_memory_node(self, state: MemoryState) -> dict:
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

    async def _store_memory_node(self, state: MemoryState) -> dict:
        """Extract facts and store in episodic memory after LLM response."""
        print("=" * 80)
        print("🔵 STORE_MEMORY_NODE CALLED")
        print("=" * 80)
        logger.info("🔵 STORE_MEMORY_NODE called")

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
        }

        # Add config for checkpointing
        config = (
            {"configurable": {"thread_id": session_id}} if self.checkpointer else None
        )

        if config:
            logger.info(f"📝 Using checkpoint thread_id: {session_id}")

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

        return {
            "response": response_text,
            "tools_used": list(set(tools_used)),  # Deduplicate
            "tool_calls_made": len(tools_used),
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
            },
        }
