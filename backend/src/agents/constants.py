"""
Agent configuration constants.

Centralizes magic numbers and configuration values used across both agents.
"""

# Tool calling configuration
MAX_TOOL_ITERATIONS = 8
"""Maximum number of tool-calling iterations per conversation turn.

This prevents infinite loops while allowing complex multi-step queries.
Each iteration can involve multiple tool calls, so 8 iterations allows
for substantial query complexity.
"""

# LangGraph configuration (stateful agent only)
LANGGRAPH_RECURSION_LIMIT = 16
"""LangGraph recursion limit for stateful agent.

Set to 16 to allow ~8 tool-calling cycles (each cycle = llm node + tools node = 2 steps).
This matches MAX_TOOL_ITERATIONS for consistency between agents.
"""

# Conversation history management
CONVERSATION_HISTORY_LIMIT = 10
"""Number of recent messages to keep in conversation context.

Limits context window size to prevent token bloat while maintaining
recent conversation context. Applies to both short-term memory trimming
and LangGraph state management.
"""

# Validation configuration
VALIDATION_STRICT_MODE = False
"""Whether to use strict validation mode.

Strict mode fails validation on any numeric mismatch.
Non-strict mode uses a scoring system (0.0-1.0) and only retries on complete failure (0.0).
"""

VALIDATION_RETRY_THRESHOLD = 0.0
"""Validation score threshold that triggers automatic retry.

Only responses with score <= this threshold will trigger a retry with correction prompt.
Default 0.0 means only complete validation failures trigger retry.
"""

# Session configuration
DEFAULT_SESSION_ID = "default"
"""Default session ID for stateful agent when none provided."""

# Logging configuration
LOG_SYSTEM_PROMPT_PREVIEW_LENGTH = 500
"""Number of characters to show when logging system prompt preview."""
