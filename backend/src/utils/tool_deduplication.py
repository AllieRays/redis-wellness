"""
Shared tool deduplication logic for both stateless and stateful agents.

Prevents agents from calling the same tool with identical arguments multiple times.
"""

import logging

logger = logging.getLogger(__name__)


class ToolCallTracker:
    """Track tool calls to prevent duplicates within a conversation turn."""

    def __init__(self):
        """Initialize empty tool call history."""
        self.tool_call_history: list[str] = []

    def is_duplicate(self, tool_name: str, tool_args: dict) -> bool:
        """
        Check if this tool call was already made.

        Args:
            tool_name: Name of the tool
            tool_args: Arguments passed to the tool

        Returns:
            True if this exact call was already made, False otherwise
        """
        tool_signature = f"{tool_name}:{str(tool_args)}"

        if tool_signature in self.tool_call_history:
            logger.warning(
                f"⚠️ Skipping duplicate tool call: {tool_name} with same args"
            )
            return True

        self.tool_call_history.append(tool_signature)
        return False

    def mark_called(self, tool_name: str, tool_args: dict) -> None:
        """
        Mark a tool call as completed (alternative to is_duplicate).

        Args:
            tool_name: Name of the tool
            tool_args: Arguments passed to the tool
        """
        tool_signature = f"{tool_name}:{str(tool_args)}"
        if tool_signature not in self.tool_call_history:
            self.tool_call_history.append(tool_signature)

    def get_call_count(self) -> int:
        """Get total number of unique tool calls made."""
        return len(self.tool_call_history)

    def reset(self) -> None:
        """Clear tool call history (for new conversation turn)."""
        self.tool_call_history.clear()
