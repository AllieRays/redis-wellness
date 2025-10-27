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
from ..services.episodic_memory_manager import get_episodic_memory
from ..services.procedural_memory_manager import get_procedural_memory
from ..services.redis_connection import get_redis_manager
from ..utils.exceptions import (
    InfrastructureError,
    sanitize_user_id,
)
from ..utils.user_config import extract_user_id_from_session, get_user_session_key


class RedisChatService:
    """Redis chat service with CoALA framework memory."""

    def __init__(self) -> None:
        self.settings = get_settings()

        # Use the connection manager instead of direct client
        self.redis_manager = get_redis_manager()

        # Get episodic memory for goal storage/retrieval (sync init OK)
        self.episodic_memory = get_episodic_memory()

        # Get procedural memory for workflow pattern learning (sync init OK)
        self.procedural_memory = get_procedural_memory()

        # Agent will be lazily initialized on first async use
        # (checkpointer requires async initialization)
        self._agent = None

    async def _ensure_agent_initialized(self) -> None:
        """
        Lazy async initialization of agent with AsyncRedisSaver checkpointer.

        This method ensures the StatefulRAGAgent is created with an async Redis
        checkpointer, which is required for LangGraph state persistence. The agent
        is only initialized once and reused for all subsequent requests.

        The agent is initialized with:
        - checkpointer: AsyncRedisSaver for conversation state persistence
        - episodic_memory: User goals and preferences storage
        - procedural_memory: Learned tool-calling patterns

        Returns:
            None

        Raises:
            InfrastructureError: If Redis checkpointer initialization fails.
        """
        if self._agent is not None:
            return

        # Get checkpointer asynchronously
        checkpointer = await self.redis_manager.get_checkpointer()

        # Create agent with all CoALA memory components
        self._agent = StatefulRAGAgent(
            checkpointer=checkpointer,
            episodic_memory=self.episodic_memory,
            procedural_memory=self.procedural_memory,
        )

    @property
    def agent(self) -> StatefulRAGAgent:
        """Get the agent instance (must call _ensure_agent_initialized first)."""
        if self._agent is None:
            raise RuntimeError(
                "Agent not initialized. Call await _ensure_agent_initialized() first."
            )
        return self._agent

    def _get_session_key(self, session_id: str) -> str:
        """
        Generate Redis key for storing conversation session data.

        In single-user mode, this creates a namespaced key combining the
        configured user ID with the session ID.

        Args:
            session_id: Session identifier (e.g., "default", "session_123").

        Returns:
            Redis key string in format "user:{user_id}:session:{session_id}".
        """
        return get_user_session_key(session_id)

    async def get_conversation_history(
        self, session_id: str, limit: int = 10
    ) -> list[dict]:
        """
        Retrieve conversation history from Redis for a given session.

        Fetches the most recent conversation messages stored in Redis LIST.
        Messages are stored in chronological order (oldest first).

        Args:
            session_id: Session identifier to retrieve history for.
            limit: Maximum number of messages to retrieve (default: 10).

        Returns:
            List of message dictionaries, each containing:
            {
                "role": "user" or "assistant",
                "content": "message text",
                "timestamp": "ISO 8601 timestamp"
            }

        Raises:
            InfrastructureError: If Redis operation fails.
        """
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
        """
        Extract user ID from session identifier in single-user mode.

        In single-user applications, all sessions belong to one configured user.
        This method retrieves that user ID from the application configuration.

        Args:
            session_id: Session identifier (unused in single-user mode).

        Returns:
            The configured user ID from application settings.
        """
        return extract_user_id_from_session(session_id)

    async def chat(self, message: str, session_id: str = "default") -> dict[str, Any]:
        """
        Process chat message with CoALA memory framework.

        Flow:
        1. Resolve pronouns in user message ("that" → "BMI", etc.)
        2. Process with stateful RAG agent (checkpointer handles conversation history)
        3. Agent retrieves semantic + episodic + procedural memory as needed
        4. Update pronoun context for future queries

        Args:
            message: User's input message to process.
            session_id: Session identifier for conversation continuity (default: "default").

        Returns:
            Dictionary containing:
            {
                "response": "Assistant's generated response text",
                "tools_used": ["tool_name1", "tool_name2"],
                "tool_calls_made": 2,
                "memory_stats": {
                    "semantic_hits": 1,
                    "goals_stored": 0,
                    "procedural_patterns_used": 1
                },
                "session_id": "default",
                "type": "redis_rag_with_coala_memory",
                "validation": {
                    "valid": True,
                    "score": 0.95,
                    "hallucinations_detected": 0
                }
            }

        Raises:
            InfrastructureError: If chat processing or Redis operations fail.

        Example:
            service = RedisChatService()
            result = await service.chat("What was my average heart rate?", "session_123")
            print(result["response"])
            # "Your average heart rate over the last 7 days was 72 bpm."
            print(f"Tools called: {result['tools_used']}")
            # Tools called: ['search_health_records']
        """
        try:
            # Ensure agent is initialized with async checkpointer
            await self._ensure_agent_initialized()

            user_id = self._extract_user_id(session_id)

            # Resolve pronouns in user message
            # TEMPORARILY DISABLED - causing incorrect topic resolution
            # with self.redis_manager.get_connection() as redis_client:
            #     pronoun_resolver = get_pronoun_resolver(redis_client)
            #     message_to_process = pronoun_resolver.resolve_pronouns(
            #         session_id=session_id, query=message
            #     )
            message_to_process = message  # Use original message

            # Process with stateful RAG agent (checkpointer handles history)
            result = await self.agent.chat(
                message=message_to_process,
                user_id=user_id,
                session_id=session_id,  # Checkpointer uses this as thread_id
            )

            # Update pronoun context
            # TEMPORARILY DISABLED - causing incorrect topic resolution
            # with self.redis_manager.get_connection() as redis_client:
            #     pronoun_resolver = get_pronoun_resolver(redis_client)
            #     pronoun_resolver.update_context(
            #         session_id=session_id,
            #         query=message,
            #         response=result["response"],
            #         tools_used=result.get("tools_used", []),
            #     )

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
        """
        Stream chat response tokens in real-time using Server-Sent Events (SSE).

        Processes the user's message through the stateful agent and yields
        response chunks as they're generated, allowing for real-time UI updates.

        Args:
            message: User's input message to process.
            session_id: Session identifier for conversation continuity (default: "default").

        Yields:
            Dictionaries with two types of events:
            - Token chunks: {"type": "token", "content": "text fragment"}
            - Done event: {"type": "done", "data": {response metadata}}

        Raises:
            InfrastructureError: If chat processing or streaming fails.

        Example:
            async for chunk in service.chat_stream("Hello", "session_123"):
                if chunk["type"] == "token":
                    print(chunk["content"], end="", flush=True)
                elif chunk["type"] == "done":
                    print(f"\\nTools used: {chunk['data']['tools_used']}")
        """
        try:
            # Ensure agent is initialized with async checkpointer
            await self._ensure_agent_initialized()

            user_id = self._extract_user_id(session_id)

            # Resolve pronouns in user message
            # TEMPORARILY DISABLED - causing incorrect topic resolution
            # with self.redis_manager.get_connection() as redis_client:
            #     pronoun_resolver = get_pronoun_resolver(redis_client)
            #     message_to_process = pronoun_resolver.resolve_pronouns(
            #         session_id=session_id, query=message
            #     )
            message_to_process = message  # Use original message

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
            # TEMPORARILY DISABLED - causing incorrect topic resolution
            # with self.redis_manager.get_connection() as redis_client:
            #     pronoun_resolver = get_pronoun_resolver(redis_client)
            #     pronoun_resolver.update_context(
            #         session_id=session_id,
            #         query=message,
            #         response=response_text,
            #         tools_used=final_data.get("tools_used", []) if final_data else [],
            #     )

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
        """Get memory statistics for a session."""
        # Memory stats are now returned in chat response
        # This endpoint is for backward compatibility only
        return {
            "session_id": session_id,
            "episodic_memory": "enabled",
            "procedural_memory": "enabled",
            "short_term_memory": "enabled (checkpointer)",
        }

    async def clear_session(self, session_id: str) -> bool:
        """Clear conversation history for a session."""
        try:
            # Clear conversation history (Redis LIST)
            session_key = self._get_session_key(session_id)
            with self.redis_manager.get_connection() as redis_client:
                redis_client.delete(session_key)

            # Note: Episodic memory (goals) is kept intentionally
            # Users can clear goals via "make clear-session" if needed
            return True
        except Exception as e:
            raise InfrastructureError(
                message="Failed to clear session",
                error_code="SESSION_CLEAR_FAILED",
                details={"session_id": session_id},
            ) from e


# Global service instance (lazy initialization)
_redis_chat_service: RedisChatService | None = None


def get_redis_chat_service() -> RedisChatService:
    """Get the global Redis chat service instance."""
    global _redis_chat_service
    if _redis_chat_service is None:
        _redis_chat_service = RedisChatService()
    return _redis_chat_service
