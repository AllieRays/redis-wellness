"""
Memory Coordinator - Orchestrates all memory systems for AI agents.

⚠️ IMPORTANT: This service is currently NOT USED in production.

The StatefulRAGAgent (src/agents/stateful_rag_agent.py) uses episodic_memory_manager
and procedural_memory_manager DIRECTLY, bypassing this coordinator. This code is
preserved for potential future refactoring but does not affect current agent behavior.

Current production flow:
  redis_chat.py → StatefulRAGAgent → episodic/procedural managers (direct)

This coordinator was designed to provide a unified interface for all memory types,
but the agent architecture evolved to use managers directly for better control.

---

Coordinates 4 types of memory based on CoALA framework:
1. Short-term: Conversation history (working memory)
2. Episodic: User-specific events (preferences, goals)
3. Procedural: Learned tool sequences (skills)
4. Semantic: General health knowledge (facts)

Based on Redis AI Agent Memory Guide:
https://redis.io/blog/ai-agents-memory/

Single-User Mode:
- This is a single-user application (utils.user_config.get_user_id())
- All memory operations are for the configured user
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ..utils.exceptions import MemoryRetrievalError
from ..utils.user_config import get_user_id
from .episodic_memory_manager import get_episodic_memory
from .procedural_memory_manager import get_procedural_memory_manager
from .semantic_memory_manager import get_semantic_memory_manager
from .short_term_memory_manager import get_short_term_memory_manager

logger = logging.getLogger(__name__)


@dataclass
class MemoryContext:
    """
    Complete memory context from all memory systems.

    Returned by retrieve_all_context() to provide full memory state.
    """

    # Short-term: Recent conversation
    short_term: str | None = None
    short_term_messages: int = 0

    # Episodic: User preferences, goals, events
    episodic: str | None = None
    episodic_hits: int = 0

    # Procedural: Suggested tool sequence
    procedural: dict | None = None
    procedural_confidence: float = 0.0
    procedural_recommended: bool = False

    # Semantic: General health knowledge
    semantic: str | None = None
    semantic_hits: int = 0

    # Metadata
    user_id: str = ""
    session_id: str = ""
    retrieved_at: str = ""


class MemoryCoordinator:
    """
    Coordinates all memory systems for AI agent.

    Provides unified interface for:
    - Memory retrieval (all 4 types)
    - Memory storage (all 4 types)
    - Memory statistics (all 4 types)
    - Memory clearing (all 4 types)

    Architecture:
    - Uses existing memory managers
    - Enforces single-user mode
    - Consistent error handling
    - UTC datetime tracking
    """

    def __init__(self) -> None:
        """Initialize coordinator with all memory managers."""
        # Get single user ID (enforced throughout application)
        self.user_id = get_user_id()

        # Initialize all memory managers
        self.short_term = get_short_term_memory_manager()
        self.episodic = get_episodic_memory()
        self.procedural = get_procedural_memory_manager()
        self.semantic = get_semantic_memory_manager()

        logger.info(
            f"MemoryCoordinator initialized for user: {self.user_id} "
            f"(episodic + procedural + semantic + short-term)"
        )

    async def retrieve_all_context(
        self,
        session_id: str,
        query: str,
        include_episodic: bool = True,
        include_procedural: bool = True,
        include_semantic: bool = True,
        include_short_term: bool = True,
    ) -> MemoryContext:
        """
        Retrieve context from all memory systems.

        Args:
            session_id: Session identifier
            query: Current query for semantic search
            include_episodic: Whether to retrieve episodic memories
            include_procedural: Whether to suggest tool sequence
            include_semantic: Whether to retrieve general knowledge
            include_short_term: Whether to retrieve conversation history

        Returns:
            Complete memory context from all systems

        Raises:
            MemoryRetrievalError: If critical memory retrieval fails
        """
        context = MemoryContext(
            user_id=self.user_id,
            session_id=session_id,
            retrieved_at=datetime.now(UTC).isoformat(),
        )

        # 1. Short-term: Recent conversation (always useful for context)
        if include_short_term:
            try:
                context.short_term = await self.short_term.get_short_term_context(
                    self.user_id, session_id, limit=10
                )

                if context.short_term:
                    # Count messages in context
                    context.short_term_messages = context.short_term.count("\n") - 1
                    logger.debug(f"Short-term: {context.short_term_messages} messages")
            except Exception as e:
                logger.warning(f"Short-term retrieval failed: {e}")
                # Non-critical: continue without short-term

        # 2. Episodic: User preferences, goals, events (personal context)
        if include_episodic:
            try:
                episodic_result = await self.episodic.retrieve_episodic_memories(
                    self.user_id, query, top_k=3
                )
                context.episodic = episodic_result.get("context")
                context.episodic_hits = episodic_result.get("hits", 0)

                if context.episodic_hits > 0:
                    logger.debug(f"Episodic: {context.episodic_hits} memories")
            except MemoryRetrievalError:
                # Re-raise structured exceptions for proper error handling
                raise
            except Exception as e:
                logger.warning(f"Episodic retrieval failed: {e}")
                # Non-critical: continue without episodic

        # 3. Semantic: General health knowledge (factual context)
        if include_semantic:
            try:
                semantic_result = await self.semantic.retrieve_semantic_knowledge(
                    query, top_k=3
                )
                context.semantic = semantic_result.get("context")
                context.semantic_hits = semantic_result.get("hits", 0)

                if context.semantic_hits > 0:
                    logger.debug(f"Semantic: {context.semantic_hits} facts")
            except MemoryRetrievalError:
                # Re-raise structured exceptions for proper error handling
                raise
            except Exception as e:
                logger.warning(f"Semantic retrieval failed: {e}")
                # Non-critical: continue without semantic

        # 4. Procedural: Suggest tool sequence (optimization hint)
        if include_procedural:
            try:
                context.procedural = await self.procedural.suggest_procedure(
                    self.user_id, query
                )

                if context.procedural:
                    context.procedural_confidence = context.procedural.get(
                        "confidence", 0.0
                    )
                    context.procedural_recommended = context.procedural.get(
                        "recommended", False
                    )

                    if context.procedural_recommended:
                        logger.debug(
                            f"Procedural: Suggested {context.procedural.get('tool_sequence')} "
                            f"(confidence: {context.procedural_confidence:.2f})"
                        )
            except MemoryRetrievalError:
                # Re-raise structured exceptions for proper error handling
                raise
            except Exception as e:
                logger.warning(f"Procedural retrieval failed: {e}")
                # Non-critical: continue without procedural

        return context

    async def store_interaction(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        tools_used: list[str] | None = None,
        execution_time_ms: float = 0.0,
        success_score: float = 1.0,
    ) -> dict[str, bool]:
        """
        Store interaction in all relevant memory systems.

        Automatically:
        - Stores in short-term (conversation history)
        - Stores in episodic (if meaningful interaction)
        - Records in procedural (if tools were used)
        - Semantic is pre-populated (not per-interaction)

        Args:
            session_id: Session identifier
            user_message: User's message
            assistant_response: Agent's response
            tools_used: List of tools called (if any)
            execution_time_ms: Total execution time
            success_score: Success rating (0.0-1.0)

        Returns:
            Dict indicating which systems stored successfully
        """
        results = {}

        # 1. Short-term: Always store conversation
        try:
            results["short_term_user"] = await self.short_term.store_short_term_message(
                self.user_id, session_id, "user", user_message
            )
            results[
                "short_term_assistant"
            ] = await self.short_term.store_short_term_message(
                self.user_id, session_id, "assistant", assistant_response
            )

            logger.debug("Stored in short-term memory")
        except MemoryRetrievalError:
            # Re-raise structured exceptions for critical storage failures
            raise
        except Exception as e:
            logger.error(f"Short-term storage failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="short_term",
                reason=f"Failed to store conversation: {str(e)}",
            ) from e

        # 2. Episodic: Store meaningful interactions
        # Store if response is substantial
        if len(assistant_response) > 50:
            try:
                # Import EpisodicEventType here to avoid circular imports
                from .episodic_memory_manager import EpisodicEventType

                # Store directly in episodic manager (avoid recursion through short_term)
                results["episodic"] = await self.episodic.store_episodic_event(
                    user_id=self.user_id,
                    event_type=EpisodicEventType.INTERACTION,
                    description=f"User asked: {user_message[:100]}",
                    context=f"Response: {assistant_response[:200]}",
                    metadata={"session_id": session_id},
                )

                if results["episodic"]:
                    logger.debug("Stored in episodic memory")
            except MemoryRetrievalError:
                # Re-raise structured exceptions for critical storage failures
                raise
            except Exception as e:
                logger.error(f"Episodic storage failed: {e}", exc_info=True)
                raise MemoryRetrievalError(
                    memory_type="episodic",
                    reason=f"Failed to store episodic memory: {str(e)}",
                ) from e
        else:
            results["episodic"] = True  # Skip short responses

        # 3. Procedural: Record tool sequence if tools were used
        if tools_used and len(tools_used) > 0:
            try:
                results["procedural"] = await self.procedural.record_procedure(
                    user_id=self.user_id,
                    query=user_message,
                    tool_sequence=tools_used,
                    execution_time_ms=execution_time_ms,
                    success_score=success_score,
                )

                if results["procedural"]:
                    logger.debug(
                        f"Stored in procedural memory: {tools_used} "
                        f"(score: {success_score:.2f})"
                    )
            except MemoryRetrievalError:
                # Re-raise structured exceptions for critical storage failures
                raise
            except Exception as e:
                logger.error(f"Procedural storage failed: {e}", exc_info=True)
                raise MemoryRetrievalError(
                    memory_type="procedural",
                    reason=f"Failed to store procedural memory: {str(e)}",
                ) from e
        else:
            results["procedural"] = True  # No tools used, skip

        # 4. Semantic: Pre-populated knowledge base (not per-interaction)
        results["semantic"] = True

        return results

    # ========== Agent Compatibility Wrappers ==========

    async def get_full_context(
        self,
        user_id: str,
        session_id: str,
        current_query: str,
        skip_long_term: bool = False,
    ) -> dict[str, Any]:
        """
        Get full context for agent compatibility.

        Note: user_id parameter is kept for API compatibility but the coordinator
        uses the configured single-user ID (self.user_id).

        Args:
            user_id: User ID (for API compatibility)
            session_id: Session identifier
            current_query: Current query
            skip_long_term: Skip episodic/semantic for factual queries

        Returns:
            Dict with all memory types
        """
        context = await self.retrieve_all_context(
            session_id=session_id,
            query=current_query,
            include_episodic=not skip_long_term,
            include_semantic=not skip_long_term,
            include_procedural=True,
            include_short_term=True,
        )

        return {
            "short_term": context.short_term,
            "episodic": context.episodic,
            "episodic_hits": context.episodic_hits,
            "semantic": context.semantic,
            "semantic_hits": context.semantic_hits,
            "procedural": context.procedural,
        }

    async def store_interaction_compat(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        assistant_response: str,
        tools_used: list[str],
    ) -> bool:
        """
        Store interaction for agent compatibility.

        Note: user_id parameter is kept for API compatibility but the coordinator
        uses the configured single-user ID (self.user_id).

        Args:
            user_id: User ID (for API compatibility)
            session_id: Session ID
            user_message: User message
            assistant_response: Response
            tools_used: Tools used

        Returns:
            Success bool
        """
        results = await self.store_interaction(
            session_id=session_id,
            user_message=user_message,
            assistant_response=assistant_response,
            tools_used=tools_used,
        )

        return results.get("short_term_user", False)

    async def clear_user_specific_memories(self, user_id: str) -> bool:
        """
        Clear user-specific memories (episodic and procedural only).

        Does NOT clear semantic knowledge base.

        Note: user_id parameter is kept for API compatibility but the coordinator
        uses the configured single-user ID (self.user_id).

        Args:
            user_id: User ID (for API compatibility)

        Returns:
            Success bool
        """
        try:
            await self.clear_user_memories(
                clear_episodic=True,
                clear_procedural=True,
                clear_semantic=False,  # Don't clear knowledge base
            )
            return True
        except Exception:
            return False

    async def get_memory_stats(
        self, session_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
        """
        Get statistics from all memory systems.

        Args:
            session_id: Session identifier
            user_id: User ID (optional - uses self.user_id if not provided)

        Returns:
            Dict with memory statistics from all systems
        """
        try:
            # Get stats from short-term memory manager
            short_term_stats = await self.short_term.get_memory_stats(
                self.user_id, session_id
            )

            # Get procedural stats
            procedural_stats = await self.procedural.get_procedure_stats(self.user_id)

            return {
                "short_term": short_term_stats.get("short_term", {}),
                "episodic": {
                    "memory_count": short_term_stats.get("long_term", {}).get(
                        "memory_count", 0
                    ),
                },
                "procedural": procedural_stats,
                "semantic": {
                    "note": "Pre-populated knowledge base",
                    "available": True,
                },
                "user_id": self.user_id,
                "session_id": session_id,
            }
        except MemoryRetrievalError:
            # Re-raise structured exceptions
            raise
        except Exception as e:
            logger.error(f"Memory stats retrieval failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="memory_stats",
                reason=str(e),
            ) from e

    async def clear_session_memories(self, session_id: str) -> dict[str, Any]:
        """
        Clear all memories for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dict with counts of cleared memories per system
        """
        results = {}

        try:
            # Clear short-term and semantic memories for session
            success = await self.short_term.clear_session_memory(session_id)
            results["short_term"] = success
            results["episodic"] = success

            logger.info(f"Cleared session memories: {session_id}")
        except MemoryRetrievalError:
            # Re-raise structured exceptions
            raise
        except Exception as e:
            logger.error(f"Session memory clearing failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="session",
                reason=f"Failed to clear session memories: {str(e)}",
            ) from e

        # Note: Procedural and semantic are not session-scoped
        results["procedural"] = "not_session_scoped"
        results["semantic"] = "not_session_scoped"

        return results

    async def clear_user_memories(
        self,
        clear_episodic: bool = False,
        clear_procedural: bool = False,
        clear_semantic: bool = False,
    ) -> dict[str, Any]:
        """
        Clear user-level memories (not session-specific).

        Args:
            clear_episodic: Clear user preferences/goals/events
            clear_procedural: Clear learned tool sequences
            clear_semantic: Clear general knowledge (use with caution)

        Returns:
            Dict with counts of cleared memories per system
        """
        results = {}

        if clear_episodic:
            try:
                result = await self.episodic.clear_episodic_memories(self.user_id)
                results["episodic"] = result
                logger.info(f"Cleared episodic memories: {result}")
            except MemoryRetrievalError:
                # Re-raise structured exceptions
                raise
            except Exception as e:
                logger.error(f"Episodic clearing failed: {e}", exc_info=True)
                raise MemoryRetrievalError(
                    memory_type="episodic",
                    reason=f"Failed to clear episodic memories: {str(e)}",
                ) from e

        if clear_procedural:
            try:
                result = await self.procedural.clear_procedures(self.user_id)
                results["procedural"] = result
                logger.info(f"Cleared procedural memories: {result}")
            except MemoryRetrievalError:
                # Re-raise structured exceptions
                raise
            except Exception as e:
                logger.error(f"Procedural clearing failed: {e}", exc_info=True)
                raise MemoryRetrievalError(
                    memory_type="procedural",
                    reason=f"Failed to clear procedural memories: {str(e)}",
                ) from e

        if clear_semantic:
            try:
                result = await self.semantic.clear_semantic_knowledge()
                results["semantic"] = result
                logger.warning(
                    f"Cleared semantic knowledge (use with caution): {result}"
                )
            except MemoryRetrievalError:
                # Re-raise structured exceptions
                raise
            except Exception as e:
                logger.error(f"Semantic clearing failed: {e}", exc_info=True)
                raise MemoryRetrievalError(
                    memory_type="semantic",
                    reason=f"Failed to clear semantic knowledge: {str(e)}",
                ) from e

        return results


# Global memory coordinator instance
_memory_coordinator: MemoryCoordinator | None = None


def get_memory_coordinator() -> MemoryCoordinator:
    """
    Get or create the global memory coordinator.

    Returns:
        MemoryCoordinator instance
    """
    global _memory_coordinator

    if _memory_coordinator is None:
        _memory_coordinator = MemoryCoordinator()

    return _memory_coordinator
