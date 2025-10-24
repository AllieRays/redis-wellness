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
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from ..apple_health.query_tools import create_user_bound_tools
from ..utils.agent_helpers import (
    build_base_system_prompt,
    build_error_response,
    create_health_llm,
)
from ..utils.date_validator import get_date_validator
from ..utils.numeric_validator import get_numeric_validator
from ..utils.token_manager import get_token_manager
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
            # DEBUG: Log system prompt
            logger.warning(f"📝 STATELESS SYSTEM PROMPT:\n{system_content[:500]}...")
            system_msg = SystemMessage(content=system_content)

            conversation = [system_msg, HumanMessage(content=message)]
            tool_calls_made = 0
            tools_used_list = []
            tool_results = []

            # Simple tool loop (same as stateful agent, but no memory)
            for iteration in range(max_tool_calls):
                # Bind tools and call LLM
                llm_with_tools = self.llm.bind_tools(user_tools)

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
                    logger.info(f"Agent finished after {iteration + 1} iteration(s)")

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

            # Validate response (numeric + date validation)
            numeric_validator = get_numeric_validator()
            numeric_validation = numeric_validator.validate_response(
                response_text=response_text,
                tool_results=tool_results,
                strict=False,
            )

            # Validate dates to catch hallucinations like Oct 11 vs Oct 15
            date_validator = get_date_validator()
            date_validation = date_validator.validate_response(
                user_query=message,
                response_text=response_text,
            )

            # Log validation results and handle failures
            if not date_validation["valid"]:
                logger.error(f"❌ DATE MISMATCH DETECTED: {date_validation['warnings']}")
                # Append correction prompt and retry
                correction_prompt = (
                    f"\n\nYour response mentions the wrong date. "
                    f"User asked about {date_validation['query_dates'][0]['raw_match']}, "
                    f"but you mentioned {date_validation['response_dates'][0]['raw_match']}. "
                    f"Please correct your response to use the date the user asked about."
                )
                conversation.append(AIMessage(content=response_text))
                conversation.append(HumanMessage(content=correction_prompt))

                # Retry once without tools
                llm_without_tools = self.llm

                if stream:
                    # Stream the corrected response
                    response_text = ""
                    async for chunk in llm_without_tools.astream(conversation):
                        if hasattr(chunk, "content") and chunk.content:
                            response_text += chunk.content
                            yield {"type": "token", "content": chunk.content}
                else:
                    retry_response = await llm_without_tools.ainvoke(conversation)
                    response_text = retry_response.content

                logger.info("🔄 Retry response generated (date correction)")

            elif not numeric_validation["valid"]:
                logger.warning(
                    f"Validation failed (score: {numeric_validation['score']:.2%})"
                )
                # If validation completely failed (score = 0), append correction prompt and retry once
                if numeric_validation["score"] == 0.0 and tool_results:
                    logger.warning(
                        "⚠️ Zero validation score - retrying with correction prompt"
                    )
                    correction_prompt = (
                        "\n\nYour previous response contained numbers that don't match the tool data. "
                        "Please provide a response using ONLY the numbers from the tool results above. "
                        "Quote the exact values from the tool output."
                    )
                    conversation.append(
                        AIMessage(content=response_text)
                    )  # Add bad response
                    conversation.append(
                        HumanMessage(content=correction_prompt)
                    )  # Add correction

                    # Retry once without tools
                    llm_without_tools = self.llm
                    retry_response = await llm_without_tools.ainvoke(conversation)
                    response_text = retry_response.content
                    logger.info("🔄 Retry response generated (numeric correction)")
            else:
                logger.info(
                    f"Validation passed (score: {numeric_validation['score']:.2%})"
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

            result = {
                "response": response_text,
                "tools_used": list(set(tools_used_list)),
                "tool_calls_made": tool_calls_made,
                "token_stats": token_stats,
                "validation": {
                    "numeric_valid": numeric_validation["valid"],
                    "numeric_score": numeric_validation["score"],
                    "date_valid": date_validation["valid"],
                    "hallucinations_detected": len(
                        numeric_validation.get("hallucinations", [])
                    ),
                    "date_mismatches": len(date_validation.get("date_mismatches", [])),
                    "numbers_validated": numeric_validation.get("stats", {}).get(
                        "matched", 0
                    ),
                    "total_numbers": numeric_validation.get("stats", {}).get(
                        "total_numbers", 0
                    ),
                },
                "type": "stateless_with_tools",
            }

            yield {"type": "done", "data": result}

        except Exception as e:
            error_response = build_error_response(e, "stateless_with_tools")
            yield {"type": "error", "data": error_response}
