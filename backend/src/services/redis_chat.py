"""
Redis-powered Chat Service with Full CoALA Memory.

Features:
- CoALA framework (episodic, procedural, semantic, short-term memory)
- RedisVL vector search for episodic and semantic memory
- Redis Hash for procedural memory (tool patterns)
- Conversation persistence (7-month TTL)
- Tool calling with autonomous selection
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


class RedisChatService:
    """Redis chat service with CoALA framework memory."""

    def __init__(self) -> None:
        self.settings = get_settings()

        # Use the connection manager instead of direct client
        self.redis_manager = get_redis_manager()

        # Get checkpointer for conversation persistence
        checkpointer = self.redis_manager.get_checkpointer()

        # Use stateful LangGraph agent with checkpointing only (no memory yet)
        self.agent = StatefulRAGAgent(checkpointer=checkpointer)

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

    def _extract_user_id(self, session_id: str) -> str:
        """Extract user ID from session (single-user mode)."""
        return extract_user_id_from_session(session_id)

    async def chat(self, message: str, session_id: str = "default") -> dict[str, Any]:
        """
        Process chat message with CoALA memory.

        Flow:
        1. Resolve pronouns in user message
        2. Retrieve conversation history (short-term memory)
        3. Process with stateful RAG agent (agent handles memory retrieval/storage)
        4. Update pronoun context

        Args:
            message: User's message
            session_id: Session ID

        Returns:
            Dict with response and metadata
        """
        try:
            user_id = self._extract_user_id(session_id)

            # DISABLED pronoun resolution for testing
            message_to_process = message

            # Get conversation history for agent
            # TEMPORARILY DISABLED - testing without history
            # history = await self.get_conversation_history(session_id, limit=10)

            # Process with stateful RAG agent (checkpointer handles history)
            result = await self.agent.chat(
                message=message_to_process,
                user_id=user_id,
                session_id=session_id,  # Checkpointer uses this as thread_id
            )

            # Update pronoun context
            with self.redis_manager.get_connection() as redis_client:
                pronoun_resolver = get_pronoun_resolver(redis_client)
                pronoun_resolver.update_context(
                    session_id=session_id,
                    query=message,
                    response=result["response"],
                    tools_used=result.get("tools_used", []),
                )

            return {
                "response": result["response"],
                "tools_used": result.get("tools_used", []),
                "tool_calls_made": result.get("tool_calls_made", 0),
                "memory_stats": result.get("memory_stats", {}),
                "session_id": session_id,
                "type": "redis_rag_with_coala_memory",
                "validation": result.get("validation", {}),
            }

        except Exception as e:
            raise InfrastructureError(
                message="Chat processing failed",
                error_code="CHAT_PROCESSING_FAILED",
                details={"user_id": sanitize_user_id(user_id)},
            ) from e

    async def chat_stream(self, message: str, session_id: str = "default"):
        """Stream tokens as they're generated."""
        try:
            user_id = self._extract_user_id(session_id)

            # DISABLED pronoun resolution for testing
            message_to_process = message

            # Stream from agent (checkpointer handles history)
            response_text = ""
            final_data = None
            async for chunk in self.agent.chat_stream(
                message=message_to_process,
                user_id=user_id,
                session_id=session_id,  # Checkpointer uses this
            ):
                if chunk.get("type") == "token":
                    response_text += chunk.get("content", "")
                    yield chunk
                elif chunk.get("type") == "done":
                    final_data = chunk.get("data", {})

            # Update pronoun context
            with self.redis_manager.get_connection() as redis_client:
                pronoun_resolver = get_pronoun_resolver(redis_client)
                pronoun_resolver.update_context(
                    session_id=session_id,
                    query=message,
                    response=response_text,
                    tools_used=final_data.get("tools_used", []) if final_data else [],
                )

            # Yield final data
            if final_data:
                # Convert tools_used from list of strings to list of dicts for frontend
                tools_used = final_data.get("tools_used", [])
                if tools_used and isinstance(tools_used[0], str):
                    tools_used = [{"name": tool} for tool in tools_used]
                    final_data["tools_used"] = tools_used

                yield {"type": "done", "data": final_data}

        except Exception as e:
            raise InfrastructureError(
                message="Streaming chat failed",
                error_code="STREAM_PROCESSING_FAILED",
                details={"user_id": sanitize_user_id(user_id)},
            ) from e

    async def get_memory_stats(self, session_id: str) -> dict[str, Any]:
        """Get CoALA memory statistics for a session."""
        try:
            user_id = self._extract_user_id(session_id)
            return await self.memory_coordinator.get_memory_stats(user_id, session_id)
        except Exception as e:
            raise MemoryRetrievalError(memory_type="memory_stats", reason=str(e)) from e

    async def clear_session(self, session_id: str) -> bool:
        """Clear all memories for a session."""
        try:
            result = await self.memory_coordinator.clear_session_memories(session_id)
            return result.get("short_term", False)
        except Exception as e:
            raise InfrastructureError(
                message="Failed to clear session",
                error_code="SESSION_CLEAR_FAILED",
                details={"session_id": session_id},
            ) from e


# Global service instance
redis_chat_service = RedisChatService()
