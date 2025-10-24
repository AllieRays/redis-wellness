"""
Minimal LangGraph agent - NO memory, NO checkpointing, JUST tools.
This is the baseline to prove LangGraph works before adding complexity.
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
from ..utils.agent_helpers import build_base_system_prompt, create_health_llm
from ..utils.numeric_validator import get_numeric_validator

logger = logging.getLogger(__name__)


class MinimalState(TypedDict):
    """Minimal state - just messages and user ID."""

    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str


class StatefulRAGAgent:
    """LangGraph-based stateful agent (minimal version - checkpointing only)."""

    def __init__(self, checkpointer: BaseCheckpointSaver | None = None):
        self.llm = create_health_llm()
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

        if checkpointer:
            logger.info("✅ StatefulRAGAgent initialized WITH checkpointing")
        else:
            logger.info("✅ StatefulRAGAgent initialized (no checkpointing yet)")

    def _build_graph(self):
        """Build simplest possible graph: LLM → Tools → End."""
        workflow = StateGraph(MinimalState)

        workflow.add_node("llm", self._llm_node)
        workflow.add_node("tools", self._tool_node)

        workflow.set_entry_point("llm")
        workflow.add_conditional_edges(
            "llm", self._should_continue, {"tools": "tools", "end": END}
        )
        workflow.add_edge("tools", "llm")  # Loop back after tools

        # Compile with checkpointer if provided
        return workflow.compile(checkpointer=self.checkpointer)

    async def _llm_node(self, state: MinimalState) -> dict:
        """Call LLM with tools."""
        logger.info("🤖 LLM node")
        logger.info(f"   State has {len(state['messages'])} messages")

        # Log message types for debugging
        for i, msg in enumerate(state["messages"]):
            msg_type = type(msg).__name__
            content_preview = (
                str(msg.content)[:80] if hasattr(msg, "content") else "no content"
            )
            logger.info(f"   [{i}] {msg_type}: {content_preview}")

        # Build simple system prompt
        system_prompt = build_base_system_prompt()

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

    async def _tool_node(self, state: MinimalState) -> dict:
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

    def _should_continue(self, state: MinimalState) -> str:
        """Check if we need to call tools."""
        last_msg = state["messages"][-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            return "tools"
        return "end"

    async def chat(
        self, message: str, user_id: str, session_id: str = "default"
    ) -> dict[str, Any]:
        """Process message through graph."""
        logger.info(
            f"🎯 StatefulRAGAgent.chat() called: message='{message[:50]}...', session_id={session_id}"
        )
        input_state = {"messages": [HumanMessage(content=message)], "user_id": user_id}

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
