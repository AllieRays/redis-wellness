"""
Procedural Memory Manager - Learns and stores optimal tool-calling procedures.

Based on CoALA framework (https://arxiv.org/pdf/2309.02427):
"Procedural memory stores learned skills, procedures, and 'how-to' knowledge,
forming the AI's repertoire of actions."

Examples of Procedural Memories:
- "For 'weekly workout summary' queries, call aggregate_metrics then compare_periods"
- "When user asks 'am I improving?', use trend_analysis + progress_tracking"
- "Workout frequency questions require search_workouts then aggregate_metrics"

Storage Strategy:
- Redis Hash for fast lookup
- Prefix: procedure:{user_id}:{query_hash}
- Tracks: tool_sequence, execution_time, success_score
- Learns from repeated successful patterns
"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from ..config import get_settings
from ..utils.exceptions import MemoryRetrievalError
from ..utils.redis_keys import RedisKeys
from .redis_connection import RedisConnectionManager

logger = logging.getLogger(__name__)


class ProceduralMemoryManager:
    """
    Manages procedural memories: learned tool sequences and execution patterns.

    Procedural memory makes the agent smarter over time by learning:
    - Which tool sequences work best for specific query types
    - Optimal execution patterns
    - Common workflows for user tasks

    This is separate from episodic memory (user-specific events)
    and semantic memory (general health knowledge).
    """

    def __init__(self) -> None:
        """Initialize procedural memory manager."""
        self.settings = get_settings()
        self.redis_manager = RedisConnectionManager()

        # TTL for procedural memories (7 months, same as other memories)
        self.memory_ttl = self.settings.redis_session_ttl_seconds

        logger.info("ProceduralMemoryManager initialized successfully")

    def _hash_query_pattern(self, query: str) -> str:
        """
        Create a hash for query pattern matching.

        Args:
            query: Query string

        Returns:
            Hash string for similarity grouping
        """
        # Normalize query: lowercase, remove punctuation
        normalized = query.lower().strip()
        # Use first 8 chars of hash for grouping similar queries
        return hashlib.md5(normalized.encode()).hexdigest()[:8]

    async def record_procedure(
        self,
        user_id: str,
        query: str,
        tool_sequence: list[str],
        execution_time_ms: float,
        success_score: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Record a successful tool-calling procedure.

        Args:
            user_id: User identifier
            query: Original user query
            tool_sequence: List of tools called in order
            execution_time_ms: Total execution time in milliseconds
            success_score: Success rating (0.0-1.0, where 1.0 is perfect)
            metadata: Additional context (e.g., validation score, user feedback)

        Returns:
            True if successful, False otherwise

        Examples:
            from ..utils.user_config import get_user_id

            await record_procedure(
                user_id=get_user_id(),
                query="What was my average heart rate last week?",
                tool_sequence=["aggregate_metrics", "compare_periods"],
                execution_time_ms=1250.5,
                success_score=0.95,
                metadata={"validation_score": 0.98, "tool_calls": 2}
            )
        """
        try:
            with self.redis_manager.get_connection() as redis_client:
                # Hash query for pattern matching
                query_hash = self._hash_query_pattern(query)
                procedure_key = RedisKeys.procedural_memory(user_id, query_hash)

                # Get existing procedure if it exists
                existing_data = redis_client.hgetall(procedure_key)

                if existing_data:
                    # Update existing procedure with averaging
                    execution_count = int(existing_data.get(b"execution_count", b"0"))
                    avg_time = float(existing_data.get(b"avg_execution_time_ms", b"0"))
                    avg_score = float(existing_data.get(b"avg_success_score", b"0"))

                    # Calculate new averages
                    new_count = execution_count + 1
                    new_avg_time = (
                        avg_time * execution_count + execution_time_ms
                    ) / new_count
                    new_avg_score = (
                        avg_score * execution_count + success_score
                    ) / new_count

                    procedure_data = {
                        "user_id": user_id,
                        "query_pattern": query,
                        "tool_sequence": json.dumps(tool_sequence),
                        "execution_count": new_count,
                        "avg_execution_time_ms": new_avg_time,
                        "avg_success_score": new_avg_score,
                        "last_used": datetime.now(UTC).isoformat(),
                        "metadata": json.dumps(metadata or {}),
                    }
                else:
                    # Create new procedure
                    procedure_data = {
                        "user_id": user_id,
                        "query_pattern": query,
                        "tool_sequence": json.dumps(tool_sequence),
                        "execution_count": 1,
                        "avg_execution_time_ms": execution_time_ms,
                        "avg_success_score": success_score,
                        "created_at": datetime.now(UTC).isoformat(),
                        "last_used": datetime.now(UTC).isoformat(),
                        "metadata": json.dumps(metadata or {}),
                    }

                # Store procedure
                redis_client.hset(procedure_key, mapping=procedure_data)

                # Set TTL
                redis_client.expire(procedure_key, self.memory_ttl)

                logger.info(
                    f"Recorded procedure: {query[:50]}... -> {tool_sequence} "
                    f"(score: {success_score:.2f})"
                )
                return True

        except Exception as e:
            logger.error(f"Procedural memory recording failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="procedural",
                reason=f"Failed to record procedure: {str(e)}",
            ) from e

    async def suggest_procedure(
        self, user_id: str, query: str
    ) -> dict[str, Any] | None:
        """
        Suggest optimal tool sequence based on past procedures.

        Args:
            user_id: User identifier
            query: Current user query

        Returns:
            Dict with suggested tool sequence and confidence, or None if no match

        Example:
            from ..utils.user_config import get_user_id

            suggestion = await suggest_procedure(
                user_id=get_user_id(),
                query="What was my average heart rate last week?"
            )
            # Returns: {
            #     "tool_sequence": ["aggregate_metrics", "compare_periods"],
            #     "confidence": 0.95,
            #     "execution_count": 12,
            #     "avg_time_ms": 1200.5
            # }
        """
        try:
            with self.redis_manager.get_connection() as redis_client:
                # Hash query for pattern matching
                query_hash = self._hash_query_pattern(query)
                procedure_key = RedisKeys.procedural_memory(user_id, query_hash)

                # Get procedure if it exists
                procedure_data = redis_client.hgetall(procedure_key)

                if not procedure_data:
                    return None

                # Parse and return suggestion
                tool_sequence = json.loads(procedure_data.get(b"tool_sequence", b"[]"))
                avg_score = float(procedure_data.get(b"avg_success_score", b"0"))
                execution_count = int(procedure_data.get(b"execution_count", b"0"))
                avg_time = float(procedure_data.get(b"avg_execution_time_ms", b"0"))

                # Confidence increases with execution count and success score
                # Max out confidence at 10+ executions with high success
                confidence = min(avg_score * (1 + execution_count / 10), 1.0)

                suggestion = {
                    "tool_sequence": tool_sequence,
                    "confidence": confidence,
                    "execution_count": execution_count,
                    "avg_time_ms": avg_time,
                    "avg_success_score": avg_score,
                    "recommended": confidence >= 0.7,  # Recommend if high confidence
                }

                logger.info(
                    f"Found procedure suggestion: {tool_sequence} "
                    f"(confidence: {confidence:.2f})"
                )
                return suggestion

        except Exception as e:
            logger.error(f"Procedure suggestion failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="procedural",
                reason=f"Failed to suggest procedure: {str(e)}",
            ) from e

    async def get_user_procedures(
        self, user_id: str, min_confidence: float = 0.5
    ) -> list[dict[str, Any]]:
        """
        Get all learned procedures for a user.

        Args:
            user_id: User identifier
            min_confidence: Minimum confidence threshold (0.0-1.0)

        Returns:
            List of procedure dicts sorted by confidence
        """
        try:
            with self.redis_manager.get_connection() as redis_client:
                # Scan for all user procedures
                pattern = f"procedure:{user_id}:*"
                cursor = 0
                procedures = []

                while True:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)

                    for key in keys:
                        procedure_data = redis_client.hgetall(key)
                        if not procedure_data:
                            continue

                        tool_sequence = json.loads(
                            procedure_data.get(b"tool_sequence", b"[]")
                        )
                        avg_score = float(
                            procedure_data.get(b"avg_success_score", b"0")
                        )
                        execution_count = int(
                            procedure_data.get(b"execution_count", b"0")
                        )

                        # Calculate confidence
                        confidence = min(avg_score * (1 + execution_count / 10), 1.0)

                        if confidence >= min_confidence:
                            procedures.append(
                                {
                                    "query_pattern": procedure_data.get(
                                        b"query_pattern", b""
                                    ).decode(),
                                    "tool_sequence": tool_sequence,
                                    "confidence": confidence,
                                    "execution_count": execution_count,
                                    "avg_success_score": avg_score,
                                }
                            )

                    if cursor == 0:
                        break

                # Sort by confidence (highest first)
                procedures.sort(key=lambda x: x["confidence"], reverse=True)

                logger.info(f"Retrieved {len(procedures)} procedures for user")
                return procedures

        except Exception as e:
            logger.error(f"Procedure retrieval failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="procedural",
                reason=f"Failed to retrieve procedures: {str(e)}",
            ) from e

    async def get_procedure_stats(self, user_id: str) -> dict[str, Any]:
        """
        Get statistics about user's procedural learning.

        Args:
            user_id: User identifier

        Returns:
            Dict with procedure statistics
        """
        try:
            with self.redis_manager.get_connection() as redis_client:
                # Scan for all user procedures
                pattern = f"procedure:{user_id}:*"
                cursor = 0
                total_procedures = 0
                total_executions = 0
                avg_scores = []

                while True:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)

                    for key in keys:
                        procedure_data = redis_client.hgetall(key)
                        if not procedure_data:
                            continue

                        total_procedures += 1
                        execution_count = int(
                            procedure_data.get(b"execution_count", b"0")
                        )
                        avg_score = float(
                            procedure_data.get(b"avg_success_score", b"0")
                        )

                        total_executions += execution_count
                        avg_scores.append(avg_score)

                    if cursor == 0:
                        break

                # Calculate overall statistics
                overall_avg_score = (
                    sum(avg_scores) / len(avg_scores) if avg_scores else 0.0
                )

                return {
                    "total_procedures": total_procedures,
                    "total_executions": total_executions,
                    "overall_avg_score": overall_avg_score,
                    "user_id": user_id,
                }

        except Exception as e:
            logger.error(f"Procedure stats retrieval failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="procedural",
                reason=f"Failed to retrieve procedure stats: {str(e)}",
            ) from e

    async def clear_procedures(self, user_id: str) -> dict[str, int]:
        """
        Clear all procedural memories for a user.

        Args:
            user_id: User identifier

        Returns:
            Dict with count of deleted keys
        """
        try:
            with self.redis_manager.get_connection() as redis_client:
                # Clear all procedures for this user
                pattern = f"procedure:{user_id}:*"
                cursor = 0
                deleted_count = 0

                while True:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)

                    if keys:
                        redis_client.delete(*keys)
                        deleted_count += len(keys)

                    if cursor == 0:
                        break

            logger.info(f"Cleared {deleted_count} procedures for user: {user_id}")
            return {"deleted_count": deleted_count, "user_id": user_id}

        except Exception as e:
            logger.error(f"Procedure clearing failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="procedural",
                reason=f"Failed to clear procedures: {str(e)}",
            ) from e


# Global procedural memory manager instance
_procedural_memory_manager: ProceduralMemoryManager | None = None


def get_procedural_memory_manager() -> ProceduralMemoryManager:
    """
    Get or create the global procedural memory manager.

    Returns:
        ProceduralMemoryManager instance
    """
    global _procedural_memory_manager

    if _procedural_memory_manager is None:
        _procedural_memory_manager = ProceduralMemoryManager()

    return _procedural_memory_manager
