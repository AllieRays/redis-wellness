"""
Stateful RAG Agent with Redis + RedisVL memory.

Provides context-aware conversations through dual memory architecture:
- Short-term: Recent conversation history (Redis LIST)
- Long-term: Semantic memory search (RedisVL vector index)

Uses simple tool loop (no LangGraph) for maintainability and performance.
"""

import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from ..apple_health.query_tools import create_user_bound_tools
from ..utils.agent_helpers import (
    build_base_system_prompt,
    build_error_response,
    build_message_history,
    create_health_llm,
)
from ..utils.numeric_validator import get_numeric_validator
from ..utils.query_classifier import QueryClassifier

logger = logging.getLogger(__name__)


@dataclass
class MemoryContext:
    """Memory retrieval results from Redis and RedisVL."""

    short_term: str | None = None
    long_term: str | None = None
    semantic_hits: int = 0


class StatefulRAGAgent:
    """
    RAG agent with Redis-backed memory and intelligent tool routing.

    Architecture:
    - Simple tool calling loop (like StatelessHealthAgent)
    - Query classification for optimized tool selection
    - Dual memory system (Redis + RedisVL)
    - Response validation against tool results

    Memory:
    - Short-term: Conversation history (Redis LIST, 7-month TTL)
    - Long-term: Semantic search (RedisVL HNSW, 1024-dim embeddings)
    """

    def __init__(self, memory_manager):
        """Initialize agent with memory manager."""
        if memory_manager is None:
            raise ValueError(
                "StatefulRAGAgent requires memory_manager. "
                "Use StatelessHealthAgent for no-memory mode."
            )

        self.memory_manager = memory_manager
        self.llm = create_health_llm()
        self.query_classifier = QueryClassifier()

        logger.info("StatefulRAGAgent initialized with Redis memory (simple loop)")

    def _extract_current_query(self, messages: list) -> str:
        """Extract the most recent user message content."""
        for msg in reversed(messages):
            if hasattr(msg, "content") and msg.content:
                return msg.content
        return ""

    def _filter_tools(self, user_tools: list, classification: dict) -> list:
        """Filter tools based on query classification confidence."""
        if self.query_classifier.should_filter_tools(classification, threshold=0.5):
            recommended = set(classification["recommended_tools"])
            filtered = [t for t in user_tools if t.name in recommended]
            logger.info(
                f"Tool filtering: {len(filtered)}/{len(user_tools)} tools "
                f"(confidence {classification['confidence']:.2f})"
            )
            return filtered

        logger.info(
            f"All {len(user_tools)} tools available "
            f"(confidence {classification['confidence']:.2f} below threshold)"
        )
        return user_tools

    def _build_system_prompt_with_memory(self, memory_context: MemoryContext) -> str:
        """Construct system prompt with memory context injected."""
        prompt_parts = [build_base_system_prompt(), ""]

        prompt_parts.extend(
            [
                "🧠 MEMORY SCOPE:",
                "- 'Earlier today' or 'first question' → Use current conversation",
                "- 'My goals' or 'usually' → Use semantic memory insights",
                "",
                "🧠 MEMORY CONTEXT:",
            ]
        )

        if memory_context.short_term:
            prompt_parts.append("Recent conversation:")
            prompt_parts.append(memory_context.short_term)
            prompt_parts.append("")

        if memory_context.long_term:
            hits = memory_context.semantic_hits
            prompt_parts.append(f"Semantic memory ({hits} insights):")
            prompt_parts.append(memory_context.long_term)
            prompt_parts.append("")

        return "\n".join(prompt_parts)

    async def _retrieve_memory_context(
        self, user_id: str, session_id: str, message: str
    ) -> MemoryContext:
        """Retrieve dual memory context from Redis and RedisVL."""
        context = MemoryContext()

        try:
            context.short_term = await self.memory_manager.get_short_term_context(
                user_id, session_id
            )
            if context.short_term:
                logger.info(f"Short-term context: {len(context.short_term)} chars")
        except Exception as e:
            logger.warning(f"Short-term retrieval failed: {e}", exc_info=True)
            context.short_term = None

        try:
            result = await self.memory_manager.retrieve_semantic_memory(
                user_id, message, top_k=3
            )
            context.long_term = result.get("context")
            context.semantic_hits = result.get("hits", 0)
            if context.semantic_hits > 0:
                logger.info(f"Semantic memory: {context.semantic_hits} hits")
        except Exception as e:
            logger.warning(f"Semantic retrieval failed: {e}", exc_info=True)
            context.long_term = None
            context.semantic_hits = 0

        return context

    async def _store_memory_interaction(
        self, user_id: str, session_id: str, user_message: str, response_text: str
    ) -> bool:
        """Store meaningful interactions in semantic memory."""
        if len(response_text) <= 50:
            return False

        try:
            await self.memory_manager.store_semantic_memory(
                user_id, session_id, user_message, response_text
            )
            logger.info("Stored in semantic memory")
            return True
        except Exception as e:
            logger.warning(f"Memory storage failed: {e}", exc_info=True)
            return False

    async def chat(
        self,
        message: str,
        user_id: str,
        session_id: str = "default",
        conversation_history: list[dict] | None = None,
        max_tool_calls: int = 8,  # Increased for complex multi-step queries
    ) -> dict[str, Any]:
        """Process message through RAG pipeline with memory retrieval and storage."""
        try:
            # 1. Build message history
            messages = build_message_history(
                conversation_history=conversation_history,
                current_message=message,
                limit=10,
            )

            # 2. Retrieve memory context (short-term + long-term)
            memory_context = await self._retrieve_memory_context(
                user_id, session_id, message
            )

            # 3. Create user-bound tools
            user_tools = create_user_bound_tools(user_id, conversation_history=messages)

            # 4. Query classification for tool filtering
            current_query = self._extract_current_query(messages)
            classification = self.query_classifier.classify_intent(current_query)

            logger.info(
                f"Query intent: {classification['intent']}, "
                f"confidence: {classification['confidence']:.2f}"
            )

            tools_to_use = self._filter_tools(user_tools, classification)

            # 5. Build system prompt with memory context
            system_content = self._build_system_prompt_with_memory(memory_context)
            system_msg = SystemMessage(content=system_content)

            conversation = [system_msg] + messages
            tool_calls_made = 0
            tools_used_list = []
            tool_results = []

            # 6. Simple tool loop (no LangGraph - same as stateless agent)
            for iteration in range(max_tool_calls):
                # Bind tools and call LLM
                llm_with_tools = self.llm.bind_tools(tools_to_use)
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
                    for tool in tools_to_use:
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

            # 7. Extract final response
            final_response = conversation[-1]
            if isinstance(final_response, AIMessage):
                response_text = final_response.content
            else:
                response_text = str(final_response)

            # 8. Validate response
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

            # 9. Store semantic memory for long-term insights
            await self._store_memory_interaction(
                user_id, session_id, message, response_text
            )

            return {
                "response": response_text,
                "tools_used": list(set(tools_used_list)),
                "tool_calls_made": tool_calls_made,
                "session_id": session_id,
                "memory_stats": {
                    "short_term_available": memory_context.short_term is not None,
                    "semantic_hits": memory_context.semantic_hits,
                    "long_term_available": memory_context.long_term is not None,
                },
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
                "type": "stateful_rag_agent",
            }

        except Exception as e:
            return build_error_response(e, "stateful_rag_agent")
