"""
Redis-powered Chat Service with Full RAG + Memory.

Features:
- LangGraph agent with tool calling
- RedisVL semantic vector search
- Dual memory system (short-term + long-term)
- Conversation persistence (7-month TTL)
"""

import json
from typing import Any

from ..agents import StatefulRAGAgent
from ..config import get_settings
from ..services.redis_connection import get_redis_manager
from ..utils.exceptions import (
    InfrastructureError,
    MemoryRetrievalError,
    sanitize_user_id,
)
from ..utils.pronoun_resolver import get_pronoun_resolver
from ..utils.user_config import extract_user_id_from_session, get_user_session_key
from .memory_manager import get_memory_manager


class RedisChatService:
    """Redis chat service with full RAG and memory."""

    def __init__(self):
        self.settings = get_settings()

        # Use the connection manager instead of direct client
        self.redis_manager = get_redis_manager()

        # Get memory manager
        self.memory_manager = get_memory_manager()

        # Initialize stateful agent with memory
        self.agent = StatefulRAGAgent(memory_manager=self.memory_manager)

    def _get_session_key(self, session_id: str) -> str:
        """Generate session key for Redis (single-user mode)."""
        return get_user_session_key(session_id)

    async def get_conversation_history(
        self, session_id: str, limit: int = 10
    ) -> list[dict]:
        """Get conversation history for a session."""
        try:
            session_key = self._get_session_key(session_id)

            with self.redis_manager.get_connection() as redis_client:
                history = redis_client.lrange(session_key, 0, limit - 1)

                if not history:
                    return []

                messages = []
                for msg_json in reversed(history):
                    try:
                        msg_data = json.loads(msg_json)
                        messages.append(
                            {
                                "role": msg_data["role"],
                                "content": msg_data["content"],
                                "timestamp": msg_data.get("timestamp", ""),
                            }
                        )
                    except json.JSONDecodeError:
                        continue

                return messages

        except Exception as e:
            raise InfrastructureError(
                message="Failed to retrieve conversation history",
                error_code="REDIS_OPERATION_FAILED",
                details={"operation": "get_conversation_history"},
            ) from e

    async def store_message(self, session_id: str, role: str, content: str) -> None:
        """Store a message in conversation history using MemoryManager."""
        try:
            user_id = self._extract_user_id(session_id)

            # Use MemoryManager for storage (single source of truth)
            success = await self.memory_manager.store_short_term_message(
                user_id=user_id, session_id=session_id, role=role, content=content
            )

            if not success:
                raise InfrastructureError(
                    message="Failed to store message in conversation",
                    error_code="REDIS_OPERATION_FAILED",
                    details={"operation": "store_message"},
                )

        except Exception as e:
            raise InfrastructureError(
                message="Failed to store message in conversation",
                error_code="REDIS_OPERATION_FAILED",
                details={"operation": "store_message"},
            ) from e

    def _extract_user_id(self, session_id: str) -> str:
        """Extract user ID from session (single-user mode)."""
        return extract_user_id_from_session(session_id)

    async def chat(self, message: str, session_id: str = "default") -> dict[str, Any]:
        """
        Process chat message with full RAG + memory.

        Flow:
        1. Resolve pronouns in user message (NEW - Phase 2)
        2. Retrieve conversation history (short-term memory)
        3. Retrieve semantic memories (long-term memory)
        4. Process with RAG agent + tool calling
        5. Store conversation
        6. Store in semantic memory
        7. Update pronoun context (NEW - Phase 2)

        Args:
            message: User's message
            session_id: Session ID

        Returns:
            Dict with response and metadata
        """
        try:
            user_id = self._extract_user_id(session_id)

            # NEW Phase 2: Resolve pronouns before processing
            with self.redis_manager.get_connection() as redis_client:
                pronoun_resolver = get_pronoun_resolver(redis_client)
                resolved_message = pronoun_resolver.resolve_pronouns(
                    session_id, message
                )

                # Use resolved message if different
                if resolved_message != message:
                    # Store BOTH original and resolved for transparency
                    await self.store_message(session_id, "user", message)
                    message_to_process = resolved_message
                else:
                    message_to_process = message

            # Store user message
            await self.store_message(session_id, "user", message_to_process)

            # Get conversation history with token-aware trimming (short-term memory)
            (
                context_str,
                token_stats,
            ) = await self.memory_manager.get_short_term_context_token_aware(
                user_id, session_id, limit=20
            )

            # Parse context back to history format for agent
            history = await self.get_conversation_history(session_id, limit=10)

            # Process with stateful RAG agent (includes memory retrieval)
            result = await self.agent.chat(
                message=message_to_process,
                user_id=user_id,
                session_id=session_id,
                conversation_history=history,
            )

            # Store AI response
            await self.store_message(session_id, "assistant", result["response"])

            # NEW Phase 2: Update pronoun context for next query
            with self.redis_manager.get_connection() as redis_client:
                pronoun_resolver = get_pronoun_resolver(redis_client)
                pronoun_resolver.update_context(
                    session_id=session_id,
                    query=message,  # Original query
                    response=result["response"],
                    tools_used=result.get("tools_used", []),
                )

            return {
                "response": result["response"],
                "tools_used": result.get("tools_used", []),
                "tool_calls_made": result.get("tool_calls_made", 0),
                "memory_stats": result.get("memory_stats", {}),
                "token_stats": token_stats,  # Include token usage info
                "session_id": session_id,
                "type": "redis_rag_with_memory",
                "validation": result.get("validation", {}),
            }

        except Exception as e:
            raise InfrastructureError(
                message="Chat processing failed",
                error_code="CHAT_PROCESSING_FAILED",
                details={"user_id": sanitize_user_id(user_id)},
            ) from e

    async def chat_stream(self, message: str, session_id: str = "default"):
        """Stream tokens as they're generated (with memory)."""
        try:
            user_id = self._extract_user_id(session_id)

            # Resolve pronouns
            with self.redis_manager.get_connection() as redis_client:
                pronoun_resolver = get_pronoun_resolver(redis_client)
                resolved_message = pronoun_resolver.resolve_pronouns(
                    session_id, message
                )
                message_to_process = (
                    resolved_message if resolved_message != message else message
                )

            # Store user message
            await self.store_message(session_id, "user", message_to_process)

            # Get history
            history = await self.get_conversation_history(session_id, limit=10)

            # Stream from agent and collect metadata
            response_text = ""
            final_data = None
            async for chunk in self.agent.chat_stream(
                message=message_to_process,
                user_id=user_id,
                session_id=session_id,
                conversation_history=history,
            ):
                if chunk.get("type") == "token":
                    response_text += chunk.get("content", "")
                    yield chunk
                elif chunk.get("type") == "done":
                    final_data = chunk.get("data", {})

            # Store AI response
            await self.store_message(session_id, "assistant", response_text)

            # Get token stats for frontend metrics
            (
                _,
                token_stats,
            ) = await self.memory_manager.get_short_term_context_token_aware(
                user_id, session_id, limit=20
            )

            # Update pronoun context
            with self.redis_manager.get_connection() as redis_client:
                pronoun_resolver = get_pronoun_resolver(redis_client)
                pronoun_resolver.update_context(
                    session_id=session_id,
                    query=message,
                    response=response_text,
                    tools_used=final_data.get("tools_used", []) if final_data else [],
                )

            # Yield done event with token_stats for frontend
            if final_data:
                final_data["token_stats"] = token_stats
                yield {"type": "done", "data": final_data}

        except Exception as e:
            raise InfrastructureError(
                message="Streaming chat failed",
                error_code="STREAM_PROCESSING_FAILED",
                details={"user_id": sanitize_user_id(user_id)},
            ) from e

    async def get_memory_stats(self, session_id: str) -> dict[str, Any]:
        """Get memory statistics for a session."""
        try:
            user_id = self._extract_user_id(session_id)
            return await self.memory_manager.get_memory_stats(user_id, session_id)
        except Exception as e:
            raise MemoryRetrievalError(memory_type="memory_stats", reason=str(e)) from e

    async def clear_session(self, session_id: str) -> bool:
        """Clear all memories for a session."""
        try:
            return await self.memory_manager.clear_session_memory(session_id)
        except Exception as e:
            raise InfrastructureError(
                message="Failed to clear session",
                error_code="SESSION_CLEAR_FAILED",
                details={"session_id": session_id},
            ) from e


# Global service instance
redis_chat_service = RedisChatService()
