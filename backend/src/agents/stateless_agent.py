"""
Stateless Health Agent - Demo Baseline.

Purely stateless chat with ZERO memory:
- NO conversation history
- NO episodic memory
- NO procedural memory
- NO semantic memory
- NO short-term memory
- NO Redis storage (except through tools)
- Tools can access data but agent stores NOTHING

Purpose: Baseline comparison to demonstrate CoALA memory value.
Both agents have the SAME tools - only difference is memory system.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from ..apple_health.query_tools import create_user_bound_tools
from ..utils.agent_helpers import (
    build_base_system_prompt,
    build_error_response,
    create_health_llm,
)
from ..utils.intent_bypass_handler import handle_intent_bypass
from ..utils.token_manager import get_token_manager
from ..utils.tool_deduplication import ToolCallTracker
from ..utils.validation_retry import (
    build_validation_result,
    validate_and_retry_response,
)
from ..utils.verbosity_detector import VerbosityLevel, detect_verbosity
from .constants import (
    LOG_SYSTEM_PROMPT_PREVIEW_LENGTH,
    MAX_TOOL_ITERATIONS,
    VALIDATION_STRICT_MODE,
)

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

    def __init__(self) -> None:
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

        # Note: TOOL-FIRST POLICY now in build_base_system_prompt() for consistency across agents

        return "\n".join(prompt_parts)

    async def chat(
        self,
        message: str,
        user_id: str,
        max_tool_calls: int = MAX_TOOL_ITERATIONS,
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
        max_tool_calls: int = MAX_TOOL_ITERATIONS,
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
        max_tool_calls: int = 8,
        stream: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Process stateless chat with basic tool calling but NO memory.

        Args:
            message: User's message
            user_id: User identifier
            max_tool_calls: Maximum tool iterations (default: MAX_TOOL_ITERATIONS)

        Returns:
            Dict with response and validation
        """
        try:
            # PRE-ROUTE: Check if this is a goal-setting or goal-retrieval statement
            bypass_result = await handle_intent_bypass(
                message=message, user_id=user_id, is_stateful=False
            )

            if bypass_result:
                # Stream response as tokens for frontend compatibility
                if stream:
                    for char in bypass_result["response"]:
                        yield {"type": "token", "content": char}

                yield {"type": "done", "data": bypass_result}
                return

            # Detect verbosity level from query (for response style only)
            verbosity = detect_verbosity(message)
            logger.info(f"Stateless query verbosity: {verbosity}")

            # Create tools (health only - NO memory tools for stateless baseline)
            messages = [HumanMessage(content=message)]
            user_tools = create_user_bound_tools(
                user_id,
                conversation_history=messages,
                include_memory_tools=False,  # Stateless agent has NO memory
            )

            # Simple tool calling loop
            system_content = self._build_system_prompt_with_verbosity(verbosity)
            logger.debug(
                f"📝 Stateless system prompt preview:\n{system_content[:LOG_SYSTEM_PROMPT_PREVIEW_LENGTH]}..."
            )
            system_msg = SystemMessage(content=system_content)

            conversation = [system_msg, HumanMessage(content=message)]
            tool_calls_made = 0
            tools_used_list = []
            tool_results = []
            tool_tracker = ToolCallTracker()  # Track tool calls to prevent duplicates

            # Simple tool loop (no memory stored)
            for iteration in range(max_tool_calls):
                # Bind tools and call LLM
                llm_with_tools = self.llm.bind_tools(user_tools)
                logger.debug(
                    f"🔄 Stateless iteration {iteration + 1}/{max_tool_calls}: {len(conversation)} messages in context"
                )

                # If streaming and first iteration, use astream directly
                if stream and iteration == 0:
                    response_content = ""
                    response_has_tool_calls = False

                    async for chunk in llm_with_tools.astream(conversation):
                        if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                            response_has_tool_calls = True
                        if hasattr(chunk, "content") and chunk.content:
                            response_content += chunk.content
                            if not response_has_tool_calls:
                                yield {"type": "token", "content": chunk.content}

                    response = AIMessage(content=response_content)
                    if response_has_tool_calls:
                        # Need full response with tool_calls - re-invoke
                        response = await llm_with_tools.ainvoke(conversation)
                else:
                    # Non-streaming or after tools - use ainvoke
                    response = await llm_with_tools.ainvoke(conversation)

                conversation.append(response)

                # Check if LLM wants to call tools (fallback to additional_kwargs)
                tool_calls_present = hasattr(response, "tool_calls") and bool(
                    response.tool_calls
                )
                if not tool_calls_present:
                    extra_calls = getattr(response, "additional_kwargs", {}).get(
                        "tool_calls"
                    )
                    if extra_calls:
                        response.tool_calls = extra_calls
                        tool_calls_present = True

                if not tool_calls_present:
                    logger.info(
                        f"✅ Stateless agent finished after {iteration + 1} iteration(s)"
                    )

                    # If streaming enabled, stream the final response (after tool calls)
                    if stream and iteration > 0:
                        streamed_content = ""
                        async for chunk in llm_with_tools.astream(conversation[:-1]):
                            if hasattr(chunk, "content") and chunk.content:
                                streamed_content += chunk.content
                                yield {"type": "token", "content": chunk.content}
                        response.content = streamed_content
                        conversation[-1] = response

                    break

                # Execute tools
                for tool_call in response.tool_calls:
                    tool_name = tool_call.get("name", "unknown")
                    tool_args = tool_call.get("args", {})

                    # Check if this exact tool call was already made
                    if tool_tracker.is_duplicate(tool_name, tool_args):
                        # Add a message saying we already have this data
                        tool_msg = ToolMessage(
                            content="Data already retrieved in previous tool call. Use the existing results.",
                            tool_call_id=tool_call.get("id", ""),
                            name=tool_name,
                        )
                        conversation.append(tool_msg)
                        continue

                    tool_calls_made += 1
                    tools_used_list.append(tool_name)

                    logger.info(
                        f"🔧 Stateless tool call #{tool_calls_made}: {tool_name}"
                    )

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

            # If we exited the loop because of max iterations with pending tool results,
            # call LLM one more time WITHOUT tools to generate final response
            final_message = conversation[-1]
            if not isinstance(final_message, AIMessage):
                logger.info(
                    f"⚠️ Stateless reached max iterations ({max_tool_calls}), generating final response..."
                )
                # Call LLM WITHOUT tools to force a final text response
                final_response = await self.llm.ainvoke(conversation)
                conversation.append(final_response)
                response_text = final_response.content
            else:
                response_text = final_message.content

            # Validate response and retry if needed (shared utility)
            if stream:
                # For streaming, validation happens after all tokens streamed
                # We'll handle retry in streaming mode if needed
                retry_generator = validate_and_retry_response(
                    response_text=response_text,
                    tool_results=tool_results,
                    user_query=message,
                    llm=self.llm,
                    conversation=conversation,
                    stream=True,
                )
                # If retry is needed, it will yield tokens
                async for chunk in retry_generator:
                    if chunk.get("type") == "token":
                        yield chunk
                    elif chunk.get("type") == "validation_retry":
                        response_text = chunk["corrected_text"]

                # Get final validation results
                from ..utils.date_validator import get_date_validator
                from ..utils.numeric_validator import get_numeric_validator

                numeric_validator = get_numeric_validator()
                numeric_validation = numeric_validator.validate_response(
                    response_text=response_text,
                    tool_results=tool_results,
                    strict=VALIDATION_STRICT_MODE,
                )
                date_validator = get_date_validator()
                date_validation = date_validator.validate_response(
                    user_query=message,
                    response_text=response_text,
                )
            else:
                # Non-streaming mode
                (
                    response_text,
                    numeric_validation,
                    date_validation,
                ) = await validate_and_retry_response(
                    response_text=response_text,
                    tool_results=tool_results,
                    user_query=message,
                    llm=self.llm,
                    conversation=conversation,
                    stream=False,
                )

            # Calculate token usage stats for conversation
            token_manager = get_token_manager()
            conversation_dicts = []
            for msg in conversation:
                if hasattr(msg, "content"):
                    role = (
                        "system"
                        if isinstance(msg, SystemMessage)
                        else "assistant"
                        if isinstance(msg, AIMessage)
                        else "user"
                    )
                    conversation_dicts.append(
                        {"role": role, "content": str(msg.content)}
                    )
            token_stats = token_manager.get_usage_stats(conversation_dicts)
            logger.info(
                f"📊 Stateless token stats: {token_stats.get('token_count', 0)} tokens "
                f"({token_stats.get('usage_percent', 0):.1f}% of context)"
            )

            result = {
                "response": response_text,
                "tools_used": list(set(tools_used_list)),
                "tool_calls_made": tool_calls_made,
                "token_stats": token_stats,
                "validation": build_validation_result(
                    numeric_validation, date_validation
                ),
                "type": "stateless_with_tools",
            }

            yield {"type": "done", "data": result}

        except Exception as e:
            logger.error(f"❌ Stateless agent error: {e}", exc_info=True)
            error_response = build_error_response(e, "stateless_with_tools")
            yield {"type": "error", "data": error_response}
