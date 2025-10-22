"""
Memory Scope Classifier.

Determines whether a query needs session-specific memory or semantic memory.
Fixes Bug #1: Memory confusion between current session and past conversations.
"""

from enum import Enum


class MemoryScope(Enum):
    """Memory scope types."""

    SESSION = "session"  # Only current conversation
    SEMANTIC = "semantic"  # Cross-session insights
    BOTH = "both"  # Combined retrieval


def classify_memory_scope(query: str) -> MemoryScope:
    """
    Classify which memory scope a query needs.

    Args:
        query: User's query

    Returns:
        MemoryScope enum value

    Examples:
        >>> classify_memory_scope("What was the first thing I asked?")
        MemoryScope.SESSION

        >>> classify_memory_scope("What are my fitness goals?")
        MemoryScope.SEMANTIC

        >>> classify_memory_scope("Tell me about my workouts")
        MemoryScope.BOTH
    """
    query_lower = query.lower()

    # Session-specific keywords (current conversation)
    session_keywords = [
        "first thing i asked",
        "first thing i said",
        "what did i just",
        "what did i ask",
        "earlier you said",
        "you just told me",
        "you said before",
        "beginning of our conversation",
        "start of this chat",
        "what was i asking about",
        "earlier in our chat",
        "earlier today",
    ]

    # Check for session-specific patterns
    for keyword in session_keywords:
        if keyword in query_lower:
            return MemoryScope.SESSION

    # Semantic/historical keywords (cross-session patterns)
    semantic_keywords = [
        "my goals",
        "my preferences",
        "my target",
        "usually",
        "typically",
        "in the past",
        "historically",
        "always",
        "never",
        "my habits",
        "my routine",
    ]

    # Check for semantic patterns
    for keyword in semantic_keywords:
        if keyword in query_lower:
            return MemoryScope.SEMANTIC

    # Default: use both for general queries
    return MemoryScope.BOTH
