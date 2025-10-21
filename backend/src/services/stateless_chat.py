"""
Stateless RAG Agent Chat Service.

STRICTLY stateless - NO memory, NO history, NO state.

Each request is completely independent:
- No conversation history
- No semantic memory retrieval
- No Redis reads/writes (except for health data tools)
- New random session ID per request
- Pure agent + tools only

Purpose: Demonstrate the difference when memory is absent.
"""

import uuid

from ..agents.health_rag_agent import process_health_chat


class StatelessChatService:
    """
    Stateless chat service with NO memory.

    Guarantees:
    - No conversation history
    - No semantic memory
    - No session persistence
    - Each message processed independently
    """

    async def chat(self, message: str) -> dict:
        """
        Process a completely stateless chat message.

        Args:
            message: The user's message

        Returns:
            Dict with response and validation metadata
        """
        # Generate unique session ID for this single request
        # (ensures no accidental state sharing)
        ephemeral_session_id = f"stateless_{uuid.uuid4().hex[:8]}"

        # Process with RAG agent but WITHOUT memory manager
        # AND without conversation history
        result = await process_health_chat(
            message=message,
            user_id="your_user",
            session_id=ephemeral_session_id,
            conversation_history=None,  # ← NO HISTORY
            memory_manager=None,  # ← NO MEMORY
        )

        # Return response with validation info
        return {
            "response": result["response"],
            "validation": result.get("validation", {}),
        }


# Global service instance
stateless_chat_service = StatelessChatService()
