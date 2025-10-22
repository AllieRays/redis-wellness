"""
Stateless Chat Service - Demo Baseline.

STRICTLY stateless - NO memory, NO history, NO state.

Each request is completely independent:
- No conversation history
- No semantic memory retrieval
- No Redis reads/writes (except for health data tools)
- Pure agent + tools only

Purpose: Demonstrate the difference when memory is absent.
"""

from ..agents import StatelessHealthAgent
from ..utils.user_config import get_user_id


class StatelessChatService:
    """
    Stateless chat service with NO memory.

    Guarantees:
    - No conversation history
    - No semantic memory
    - No session persistence
    - Each message processed independently
    """

    def __init__(self):
        """Initialize stateless service with dedicated agent."""
        self.agent = StatelessHealthAgent()

    async def chat(self, message: str) -> dict:
        """
        Process a completely stateless chat message.

        Args:
            message: The user's message

        Returns:
            Dict with response and validation metadata
        """
        # Process with stateless agent (NO memory)
        result = await self.agent.chat(
            message=message,
            user_id=get_user_id(),
        )

        # Return full agent response with metrics for demo comparison
        return {
            "response": result["response"],
            "tools_used": result.get("tools_used", []),
            "tool_calls_made": result.get("tool_calls_made", 0),
            "validation": result.get("validation", {}),
        }


# Global service instance
stateless_chat_service = StatelessChatService()
