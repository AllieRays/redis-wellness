"""Redis-based chat service with RedisVL for conversational memory."""

import json
import uuid
from datetime import datetime

import httpx
from fastapi import HTTPException
from redisvl.redis.connection import Redis

from src.config import get_settings


class RedisChatService:
    """Chat service that uses Redis for conversation memory."""

    def __init__(self):
        self.settings = get_settings()
        self.redis_client = None
        self._initialize_redis()

    def _initialize_redis(self):
        """Initialize Redis connection."""
        try:
            # Create Redis client using RedisVL
            self.redis_client = Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
                decode_responses=True,
            )
            # Test connection
            self.redis_client.ping()

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Redis connection: {str(e)}",
            ) from e

    def _get_session_key(self, session_id: str) -> str:
        """Generate a consistent session key."""
        return f"chat_session:{session_id}"

    async def get_conversation_history(
        self, session_id: str, limit: int = 10
    ) -> list[dict]:
        """
        Retrieve conversation history for a session.

        Args:
            session_id: The session identifier
            limit: Maximum number of messages to retrieve

        Returns:
            List of conversation messages
        """
        try:
            session_key = self._get_session_key(session_id)

            # Get conversation history from Redis
            history = self.redis_client.lrange(session_key, 0, limit - 1)

            if not history:
                return []

            # Parse and return messages (newest first, so reverse for chronological order)
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
                detail=f"Failed to retrieve conversation history: {str(e)}",
            ) from e

    async def store_message(self, session_id: str, role: str, content: str) -> None:
        """
        Store a message in the conversation history.

        Args:
            session_id: The session identifier
            role: The role of the message sender (user/assistant)
            content: The message content
        """
        try:
            session_key = self._get_session_key(session_id)

            message_data = {
                "id": str(uuid.uuid4()),
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Store in Redis list (newest messages at the front)
            self.redis_client.lpush(session_key, json.dumps(message_data))

            # Set expiration for session (24 hours)
            self.redis_client.expire(session_key, 86400)

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to store message: {str(e)}"
            ) from e

    async def search_similar_conversations(
        self, query: str, limit: int = 5
    ) -> list[dict]:
        """
        Search for similar conversations using vector similarity.

        Args:
            query: The search query
            limit: Maximum number of results

        Returns:
            List of similar conversation snippets
        """
        try:
            # Use RedisVL's vector search capabilities
            # This would require setting up vector embeddings
            # For now, we'll return an empty list as this requires additional setup
            return []

        except Exception:
            # Don't raise exception for search failures, just return empty results
            return []

    async def chat(self, message: str, session_id: str = "default") -> str:
        """
        Process a chat message with conversation memory.

        Args:
            message: The user's message
            session_id: Session identifier for conversation context

        Returns:
            The AI's response

        Raises:
            HTTPException: If there's an error processing the chat
        """
        try:
            # Store the user message
            await self.store_message(session_id, "user", message)

            # Get conversation history
            history = await self.get_conversation_history(session_id, limit=10)

            # Prepare messages for Ollama (convert to the format expected by Ollama)
            messages = []
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})

            # Call Ollama with conversation context
            async with httpx.AsyncClient(timeout=30.0) as client:
                ollama_response = await client.post(
                    f"{self.settings.ollama_base_url}/api/chat",
                    json={
                        "model": self.settings.ollama_model,
                        "messages": messages,
                        "stream": False,
                    },
                )

                if ollama_response.status_code != 200:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Ollama error: {ollama_response.status_code}",
                    )

                ollama_data = ollama_response.json()
                ai_response = ollama_data.get("message", {}).get(
                    "content", "No response"
                )

            # Store the AI response
            await self.store_message(session_id, "assistant", ai_response)

            return ai_response

        except httpx.TimeoutException as e:
            raise HTTPException(status_code=504, detail="Ollama request timeout") from e
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=503, detail=f"Ollama connection error: {str(e)}"
            ) from e
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Internal server error: {str(e)}"
            ) from e

    async def clear_session(self, session_id: str) -> bool:
        """
        Clear conversation history for a session.

        Args:
            session_id: The session identifier

        Returns:
            True if successful
        """
        try:
            session_key = self._get_session_key(session_id)

            # Delete session data
            self.redis_client.delete(session_key)

            return True

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to clear session: {str(e)}"
            ) from e

    def get_session_info(self, session_id: str) -> dict:
        """
        Get information about a chat session.

        Args:
            session_id: The session identifier

        Returns:
            Dictionary with session information
        """
        try:
            session_key = self._get_session_key(session_id)

            message_count = self.redis_client.llen(session_key)
            ttl = self.redis_client.ttl(session_key)

            return {
                "session_id": session_id,
                "message_count": message_count,
                "ttl_seconds": ttl,
                "exists": message_count > 0,
            }

        except Exception:
            return {
                "session_id": session_id,
                "message_count": 0,
                "ttl_seconds": -1,
                "exists": False,
            }
