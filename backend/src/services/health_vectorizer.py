"""
Health Data Vectorization Tool for RAG.

Converts health records into vector embeddings for semantic search.
Uses sentence-transformers for local embedding generation.
"""

import json
import logging
from datetime import datetime

from sentence_transformers import SentenceTransformer

from ..utils.base import ToolResult, create_error_result, create_success_result
from .redis_health_tool import redis_manager

logger = logging.getLogger(__name__)


class HealthVectorizer:
    """Vectorize health records for semantic search with RedisVL."""

    def __init__(self):
        """Initialize with embedding model."""
        try:
            # Use lightweight, fast embedding model
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded embedding model: all-MiniLM-L6-v2")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.model = None

    def vectorize_health_data(
        self, user_id: str, batch_size: int = 100, sample_size: int | None = None
    ) -> ToolResult:
        """
        Vectorize health records and store in RedisVL index.

        Args:
            user_id: User identifier
            batch_size: Number of records to process at once
            sample_size: Optional - only vectorize N most recent records per metric

        Returns:
            ToolResult with indexing statistics
        """
        if not self.model:
            return create_error_result("Embedding model not loaded", "MODEL_NOT_LOADED")

        try:
            # Get health data from Redis
            with redis_manager.redis_manager.get_connection() as redis_client:
                main_key = f"health:user:{user_id}:data"
                health_data_json = redis_client.get(main_key)

                if not health_data_json:
                    return create_error_result(
                        "No health data found for user", "NO_DATA"
                    )

                health_data = json.loads(health_data_json)

            # Extract records by metric type
            metrics_summary = health_data.get("metrics_summary", {})
            total_vectorized = 0
            total_metrics = 0

            # For demo, we'll create synthetic records from the summary
            # In production, you'd iterate through actual individual records
            records_to_index = []

            for metric_type, metric_info in metrics_summary.items():
                total_metrics += 1

                # Create a searchable text representation
                latest_value = metric_info.get("latest_value", "N/A")
                latest_date = metric_info.get("latest_date", "")
                count = metric_info.get("count", 0)

                record_text = f"{metric_type}: {latest_value} (recorded {count} times, latest: {latest_date})"

                # Parse date
                try:
                    if latest_date:
                        date_obj = datetime.fromisoformat(
                            latest_date.replace("Z", "+00:00")
                        )
                        timestamp = int(date_obj.timestamp())
                    else:
                        timestamp = int(datetime.now().timestamp())
                except (ValueError, AttributeError):
                    timestamp = int(datetime.now().timestamp())

                # Parse value
                try:
                    value = (
                        float(latest_value.split()[0]) if " " in latest_value else 0.0
                    )
                except (ValueError, IndexError, AttributeError):
                    value = 0.0

                unit = (
                    latest_value.split()[1]
                    if " " in latest_value and len(latest_value.split()) > 1
                    else ""
                )

                # Generate embedding
                embedding = self.model.encode(record_text).tolist()

                records_to_index.append(
                    {
                        "key": f"health:record:{user_id}:{metric_type}:latest",
                        "user_id": user_id,
                        "metric_type": metric_type,
                        "date": timestamp,
                        "value": value,
                        "unit": unit,
                        "record_text": record_text,
                        "embedding": embedding,
                    }
                )

                total_vectorized += 1

            # Store in Redis using RedisVL
            # For now, we'll store directly in Redis as hashes
            with redis_manager.redis_manager.get_connection() as redis_client:
                for record in records_to_index:
                    key = record.pop("key")

                    # Convert embedding to bytes for Redis storage
                    import numpy as np

                    embedding_bytes = np.array(
                        record["embedding"], dtype=np.float32
                    ).tobytes()
                    record["embedding"] = embedding_bytes

                    # Store as hash
                    redis_client.hset(key, mapping=record)

            return create_success_result(
                {
                    "user_id": user_id,
                    "metrics_vectorized": total_metrics,
                    "records_indexed": total_vectorized,
                    "embedding_model": "all-MiniLM-L6-v2",
                    "embedding_dimensions": 384,
                    "index_name": "health_records_vector_idx",
                },
                f"Successfully vectorized {total_vectorized} health records",
            )

        except Exception as e:
            logger.error(f"Vectorization failed: {e}")
            return create_error_result(
                f"Failed to vectorize health data: {str(e)}", "VECTORIZATION_ERROR"
            )


# Global vectorizer instance
health_vectorizer = HealthVectorizer()


def vectorize_user_health_data(
    user_id: str, sample_size: int | None = None
) -> ToolResult:
    """
    Vectorize user's health data for RAG retrieval.

    Args:
        user_id: User identifier
        sample_size: Optional limit on number of records per metric

    Returns:
        ToolResult with vectorization statistics
    """
    return health_vectorizer.vectorize_health_data(user_id, sample_size=sample_size)
