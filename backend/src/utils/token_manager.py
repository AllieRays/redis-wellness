"""Token counting and context window management for LLM conversations.

Provides utilities to:
1. Count tokens in messages using tiktoken
2. Trim conversations when approaching token limits
3. Track token usage for monitoring
"""

import logging
from typing import Any

try:
    import tiktoken
except ImportError:
    tiktoken = None

from ..config import get_settings

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages token counting and context window limits."""

    def __init__(self):
        """Initialize token manager with model-specific encoding."""
        self.settings = get_settings()

        # Use cl100k_base encoding (compatible with GPT-3.5/4 and Ollama models)
        if tiktoken:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        else:
            self.encoding = None
            logger.warning("tiktoken not installed, token counting disabled")

        self.max_tokens = self.settings.max_context_tokens
        self.threshold = int(self.max_tokens * self.settings.token_usage_threshold)
        self.min_messages = self.settings.min_messages_to_keep

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens (or len(text)//4 if tiktoken unavailable)
        """
        if not self.encoding:
            # Rough approximation: 1 token ≈ 4 characters
            return len(text) // 4

        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            return len(text) // 4

    def count_message_tokens(self, messages: list[dict[str, Any]]) -> int:
        """
        Count total tokens in a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Returns:
            Total token count
        """
        total_tokens = 0

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            # Format: "role: content"
            message_text = f"{role}: {content}"
            total_tokens += self.count_tokens(message_text)

        # Add overhead for conversation markers (~50 tokens)
        total_tokens += 50

        return total_tokens

    def should_trim(self, token_count: int) -> bool:
        """
        Check if conversation should be trimmed based on token count.

        Args:
            token_count: Current token count

        Returns:
            True if exceeding threshold
        """
        return token_count > self.threshold

    def trim_messages(
        self, messages: list[dict[str, Any]], target_tokens: int | None = None
    ) -> tuple[list[dict[str, Any]], int, int]:
        """
        Trim messages to stay under token limit, keeping most recent messages.

        Args:
            messages: List of messages to trim
            target_tokens: Target token limit (defaults to threshold)

        Returns:
            Tuple of (trimmed_messages, original_tokens, trimmed_tokens)
        """
        if not messages:
            return [], 0, 0

        original_tokens = self.count_message_tokens(messages)
        target = target_tokens or self.threshold

        # Already under limit
        if original_tokens <= target:
            return messages, original_tokens, original_tokens

        logger.info(
            f"Trimming messages: {original_tokens} tokens > {target} limit. "
            f"Keeping {self.min_messages} most recent messages."
        )

        # Remove oldest messages until under target
        trimmed = messages.copy()

        while len(trimmed) > self.min_messages:
            trimmed = trimmed[1:]  # Remove oldest message
            trimmed_tokens = self.count_message_tokens(trimmed)

            if trimmed_tokens <= target:
                logger.info(
                    f"Trimmed to {len(trimmed)} messages ({trimmed_tokens} tokens)"
                )
                return trimmed, original_tokens, trimmed_tokens

        # Worst case: keep minimum messages
        trimmed_tokens = self.count_message_tokens(trimmed)
        logger.warning(
            f"Reached minimum message limit ({self.min_messages}). "
            f"Still using {trimmed_tokens} tokens."
        )

        return trimmed, original_tokens, trimmed_tokens

    def get_usage_stats(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Get token usage statistics for messages.

        Args:
            messages: List of messages

        Returns:
            Dict with usage stats
        """
        token_count = self.count_message_tokens(messages)
        usage_percent = (token_count / self.max_tokens) * 100
        threshold_percent = (token_count / self.threshold) * 100

        return {
            "message_count": len(messages),
            "token_count": token_count,
            "max_tokens": self.max_tokens,
            "usage_percent": round(usage_percent, 1),
            "threshold_percent": round(threshold_percent, 1),
            "is_over_threshold": token_count > self.threshold,
        }


# Global token manager instance
_token_manager: TokenManager | None = None


def get_token_manager() -> TokenManager:
    """Get or create global token manager instance."""
    global _token_manager

    if _token_manager is None:
        _token_manager = TokenManager()

    return _token_manager
