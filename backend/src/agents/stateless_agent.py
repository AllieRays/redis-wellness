"""
Stateless Health Chat - Demo Baseline.

Demonstrates chat WITHOUT memory:
- NO conversation history
- NO semantic memory
- NO Redis storage
- NO LangGraph workflow
- Simple tool calling (same tools as stateful, but no memory context)

Purpose: Baseline comparison to show memory value.
Both agents have the SAME tools - only difference is memory.
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from ..apple_health.query_tools import create_user_bound_tools
from ..utils.agent_helpers import (
    build_base_system_prompt,
    build_error_response,
    create_health_llm,
)
from ..utils.numeric_validator import get_numeric_validator
from ..utils.verbosity_detector import VerbosityLevel, detect_verbosity

logger = logging.getLogger(__name__)


class StatelessHealthAgent:
    """
    Simple stateless chat with basic tool calling but NO memory.

    Features:
    - Tool calling (health data retrieval)
    - Basic system prompt
    - Response validation
    - Simple tool execution loop

    NO Features:
    - NO conversation history
    - NO semantic memory
    - NO Redis storage
    - NO memory context

    This is the BASELINE for demonstrating memory value.
    Both agents have SAME tools - difference is memory.
    """

    def __init__(self):
        """Initialize stateless chat."""
        self.llm = create_health_llm()
        logger.info("StatelessHealthAgent initialized (no memory, simple tool calling)")

    def _build_system_prompt_with_verbosity(self, verbosity: VerbosityLevel) -> str:
        """Build system prompt with verbosity instructions."""
        prompt_parts = [build_base_system_prompt(), ""]

        # Add verbosity instructions (same as stateful agent)
        if verbosity == VerbosityLevel.DETAILED:
            prompt_parts.extend(
                [
                    "📊 VERBOSITY MODE: DETAILED",
                    "User requested more information. Provide:",
                    "- Comprehensive explanations of the data",
                    "- Analytical insights and trends",
                    "- Contextual interpretations (what the numbers mean)",
                    "- Relevant comparisons to typical ranges or previous data",
                    "- Actionable takeaways when appropriate",
                    "",
                ]
            )
        elif verbosity == VerbosityLevel.COMPREHENSIVE:
            prompt_parts.extend(
                [
                    "📊 VERBOSITY MODE: COMPREHENSIVE",
                    "User requested in-depth analysis. Provide:",
                    "- Full breakdown of all data points",
                    "- Statistical analysis with context",
                    "- Health implications and interpretations",
                    "- Comparisons across time periods",
                    "- Detailed patterns and trends",
                    "- Recommendations based on the data",
                    "",
                ]
            )

        # Add tool-first policy (same as stateful agent for consistent behavior)
        prompt_parts.extend(
            [
                "⚠️ TOOL-FIRST POLICY:",
                "- For factual questions about workouts/health data → ALWAYS call tools (source of truth)",
                "- NEVER answer workout/metric questions without tool data",
                "- Always verify data through tools before responding",
                "",
            ]
        )

        return "\n".join(prompt_parts)

    async def chat(
        self,
        message: str,
        user_id: str,
        max_tool_calls: int = 5,
    ) -> dict[str, Any]:
        """Non-streaming chat (original implementation)."""
        result = None
        async for chunk in self._chat_impl(
            message, user_id, max_tool_calls, stream=False
        ):
            if chunk.get("type") in ["done", "error"]:
                result = chunk.get("data")
        return result if result else {}

    async def chat_stream(
        self,
        message: str,
        user_id: str,
        max_tool_calls: int = 5,
    ):
        """Streaming chat that yields tokens as they arrive."""
        async for chunk in self._chat_impl(
            message, user_id, max_tool_calls, stream=True
        ):
            yield chunk

    async def _chat_impl(
        self,
        message: str,
        user_id: str,
        max_tool_calls: int = 5,
        stream: bool = False,
    ):
        """
        Process stateless chat with basic tool calling but NO memory.

        Args:
            message: User's message
            user_id: User identifier
            max_tool_calls: Maximum tool calls per turn (default: 8)

        Returns:
            Dict with response and validation
        """
        try:
            # Detect verbosity level from query (for response style only)
            verbosity = detect_verbosity(message)
            logger.info(f"Stateless query verbosity: {verbosity}")

            # Create tools (same as stateful agent)
            messages = [HumanMessage(content=message)]
            user_tools = create_user_bound_tools(user_id, conversation_history=messages)

            # Simple tool calling loop
            system_content = self._build_system_prompt_with_verbosity(verbosity)
            system_msg = SystemMessage(content=system_content)

            conversation = [system_msg, HumanMessage(content=message)]
            tool_calls_made = 0
            tools_used_list = []
            tool_results = []

            # Simple tool loop (same as stateful agent, but no memory)
            for iteration in range(max_tool_calls):
                # Bind tools and call LLM
                llm_with_tools = self.llm.bind_tools(user_tools)

                # Always use streaming mode for the LLM call if stream=True
                if stream:
                    response_content = ""
                    response_has_tool_calls = False

                    async for chunk in llm_with_tools.astream(conversation):
                        # Check for tool calls
                        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                            response_has_tool_calls = True

                        # Stream text content
                        if hasattr(chunk, "content") and chunk.content:
                            response_content += chunk.content
                            # Only yield tokens if this is the final response (no tool calls)
                            if not response_has_tool_calls:
                                yield {"type": "token", "content": chunk.content}

                    # Create AIMessage from streamed content
                    response = AIMessage(content=response_content)
                    if response_has_tool_calls:
                        # Re-invoke to get tool_calls attribute properly
                        response = await llm_with_tools.ainvoke(conversation)
                else:
                    # Non-streaming mode
                    response = await llm_with_tools.ainvoke(conversation)

                conversation.append(response)

                # Check if LLM wants to call tools
                if not hasattr(response, "tool_calls") or not response.tool_calls:
                    logger.info(f"Agent finished after {iteration + 1} iteration(s)")
                    break

                # Execute tools
                for tool_call in response.tool_calls:
                    tool_calls_made += 1
                    tool_name = tool_call.get("name", "unknown")
                    tools_used_list.append(tool_name)

                    logger.info(f"Tool call #{tool_calls_made}: {tool_name}")

                    # Find and execute tool
                    tool_found = False
                    for tool in user_tools:
                        if tool.name == tool_name:
                            try:
                                result = await tool.ainvoke(tool_call["args"])
                                tool_msg = ToolMessage(
                                    content=str(result),
                                    tool_call_id=tool_call.get("id", ""),
                                    name=tool_name,
                                )
                                conversation.append(tool_msg)
                                tool_results.append(
                                    {"name": tool_name, "content": str(result)}
                                )
                                tool_found = True
                                break
                            except Exception as e:
                                logger.error(f"Tool {tool_name} failed: {e}")
                                tool_msg = ToolMessage(
                                    content=f"Error: {str(e)}",
                                    tool_call_id=tool_call.get("id", ""),
                                    name=tool_name,
                                )
                                conversation.append(tool_msg)

                    if not tool_found:
                        logger.warning(f"Tool {tool_name} not found")

            # Extract final response
            final_response = conversation[-1]
            if isinstance(final_response, AIMessage):
                response_text = final_response.content
            else:
                response_text = str(final_response)

            # Validate response (same as stateful agent)
            validator = get_numeric_validator()
            validation_result = validator.validate_response(
                response_text=response_text,
                tool_results=tool_results,
                strict=False,
            )

            # Log validation results
            if not validation_result["valid"]:
                logger.warning(
                    f"Validation failed (score: {validation_result['score']:.2%})"
                )
            else:
                logger.info(
                    f"Validation passed (score: {validation_result['score']:.2%})"
                )

            result = {
                "response": response_text,
                "tools_used": list(set(tools_used_list)),
                "tool_calls_made": tool_calls_made,
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
                "type": "stateless_with_tools",
            }

            yield {"type": "done", "data": result}

        except Exception as e:
            error_response = build_error_response(e, "stateless_with_tools")
            yield {"type": "error", "data": error_response}
