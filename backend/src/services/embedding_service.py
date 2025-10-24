"""
Minimal Embedding Service - Generate embeddings for episodic memory.

Simple, focused implementation for goal storage/retrieval.
"""

import logging

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Minimal embedding service using Ollama mxbai-embed-large (1024-dim)."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.ollama_base_url = self.settings.ollama_base_url
        self.embedding_model = self.settings.embedding_model  # mxbai-embed-large
        logger.info(
            f"EmbeddingService initialized: {self.embedding_model} @ {self.ollama_base_url}"
        )

    async def generate_embedding(self, text: str) -> list[float] | None:
        """
        Generate 1024-dim embedding for text.

        Args:
            text: Text to embed (e.g., "User's weight goal is 125 lbs")

        Returns:
            1024-dimensional embedding vector or None on failure
        """
        if not text or not text.strip():
            logger.warning("Empty text for embedding")
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text},
                )
                response.raise_for_status()

                data = response.json()
                embedding = data.get("embedding")

                if not embedding:
                    logger.error("No embedding in Ollama response")
                    return None

                if len(embedding) != 1024:
                    logger.error(
                        f"Wrong embedding dimension: {len(embedding)} (expected 1024)"
                    )
                    return None

                return embedding

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None


# Singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create singleton embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
