"""
Redis-powered Chat Service with Full RAG + Memory.

Features:
- LangGraph agent with tool calling
- RedisVL semantic vector search
- Dual memory system (short-term + long-term)
- Conversation persistence (7-month TTL)
"""

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from ..agents.health_rag_agent import process_health_chat
from ..config import get_settings
from ..services.redis_connection import get_redis_manager
from .memory_manager import get_memory_manager


class RedisChatService:
    """Redis chat service with full RAG and memory."""

    def __init__(self):
        self.settings = get_settings()

        # Use the connection manager instead of direct client
        self.redis_manager = get_redis_manager()

        # Get memory manager
        self.memory_manager = get_memory_manager()

    def _get_session_key(self, session_id: str) -> str:
        """Generate session key for Redis."""
        return f"health_chat_session:{session_id}"

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
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve history: {str(e)}",
            ) from e

    async def store_message(self, session_id: str, role: str, content: str) -> None:
        """Store a message in conversation history."""
        try:
            session_key = self._get_session_key(session_id)

            message_data = {
                "id": str(uuid.uuid4()),
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Store in Redis using connection manager
            with self.redis_manager.get_connection() as redis_client:
                redis_client.lpush(session_key, json.dumps(message_data))
                redis_client.expire(
                    session_key, self.settings.redis_session_ttl_seconds
                )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to store message: {str(e)}"
            ) from e

    def _extract_user_id(self, session_id: str) -> str:
        """Extract user ID from session."""
        # In production, this would come from authentication
        return "your_user"

    async def chat(self, message: str, session_id: str = "default") -> dict[str, Any]:
        """
        Process chat message with full RAG + memory.

        Flow:
        1. Retrieve conversation history (short-term memory)
        2. Retrieve semantic memories (long-term memory)
        3. Process with RAG agent + tool calling
        4. Store conversation
        5. Store in semantic memory

        Args:
            message: User's message
            session_id: Session ID

        Returns:
            Dict with response and metadata
        """
        try:
            user_id = self._extract_user_id(session_id)

            # Store user message
            await self.store_message(session_id, "user", message)

            # Get conversation history (short-term memory)
            history = await self.get_conversation_history(session_id, limit=10)

            # Process with RAG agent (includes memory retrieval)
            result = await process_health_chat(
                message=message,
                user_id=user_id,
                session_id=session_id,
                conversation_history=history,
                memory_manager=self.memory_manager,
            )

            # Store AI response
            await self.store_message(session_id, "assistant", result["response"])

            return {
                "response": result["response"],
                "tools_used": result.get("tools_used", []),
                "tool_calls_made": result.get("tool_calls_made", 0),
                "memory_stats": result.get("memory_stats", {}),
                "session_id": session_id,
                "type": "redis_rag_with_memory",
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}") from e

    async def get_memory_stats(self, session_id: str) -> dict[str, Any]:
        """Get memory statistics for a session."""
        try:
            user_id = self._extract_user_id(session_id)
            return await self.memory_manager.get_memory_stats(user_id, session_id)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Memory stats error: {str(e)}"
            ) from e

    async def clear_session(self, session_id: str) -> bool:
        """Clear all memories for a session."""
        try:
            return await self.memory_manager.clear_session_memory(session_id)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Session clear error: {str(e)}"
            ) from e


# Global service instance
redis_chat_service = RedisChatService()
