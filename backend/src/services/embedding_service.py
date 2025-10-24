"""
Embedding Service - Centralized embedding generation for all memory systems.

Provides cached embedding generation for:
- Episodic memory (user events)
- Semantic memory (general facts)
- Any other services requiring text embeddings

Uses Ollama mxbai-embed-large model (1024 dimensions) with 1-hour cache.

Single-User Mode:
- This is a single-user application (utils.user_config.get_user_id())
- All embedding operations are for the configured user
"""

import logging

import httpx

from ..config import get_settings
from ..utils.exceptions import LLMServiceError
from .embedding_cache import get_embedding_cache

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Centralized embedding generation service.

    Provides:
    - Ollama embedding generation with mxbai-embed-large
    - 1-hour caching for performance
    - Consistent error handling
    - Single source of truth for embeddings
    """

    def __init__(self) -> None:
        """Initialize embedding service with Ollama connection."""
        self.settings = get_settings()
        self.ollama_base_url = self.settings.ollama_base_url
        self.embedding_model = self.settings.embedding_model
        self.embedding_cache = get_embedding_cache(ttl_seconds=3600)

        logger.info(
            f"EmbeddingService initialized: model={self.embedding_model}, "
            f"base_url={self.ollama_base_url}"
        )

    async def generate_embedding(self, text: str) -> list[float] | None:
        """
        Generate embedding for text with caching.

        Args:
            text: Text to embed

        Returns:
            1024-dimensional embedding vector or None if generation fails

        Raises:
            LLMServiceError: If Ollama service is unavailable
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None

        try:
            # Try to get from cache first
            embedding = await self.embedding_cache.get_or_generate(
                query=text, generate_fn=lambda: self._generate_uncached(text)
            )

            if embedding and len(embedding) != 1024:
                logger.error(
                    f"Unexpected embedding dimension: {len(embedding)} (expected 1024)"
                )
                return None

            return embedding

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}", exc_info=True)
            raise LLMServiceError(
                reason=f"Failed to generate embedding: {str(e)}"
            ) from e

    async def _generate_uncached(self, text: str) -> list[float] | None:
        """
        Generate embedding via Ollama (no cache lookup).

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if generation fails

        Raises:
            LLMServiceError: If Ollama service fails
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text},
                )
                response.raise_for_status()
                embedding = response.json()["embedding"]

                logger.debug(f"Generated embedding: {len(embedding)} dimensions")
                return embedding

        except httpx.TimeoutException as e:
            logger.error(f"Ollama embedding timeout: {e}")
            raise LLMServiceError(reason="Ollama service timeout") from e

        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama embedding HTTP error: {e.response.status_code}")
            raise LLMServiceError(reason=f"Ollama HTTP {e.response.status_code}") from e

        except Exception as e:
            logger.error(f"Unexpected embedding error: {e}", exc_info=True)
            raise LLMServiceError(reason=f"Embedding failed: {str(e)}") from e

    async def generate_embeddings_batch(
        self, texts: list[str]
    ) -> list[list[float] | None]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings (None for failed items)
        """
        embeddings = []

        for text in texts:
            try:
                embedding = await self.generate_embedding(text)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Batch embedding failed for text: {e}")
                embeddings.append(None)

        return embeddings


# Global embedding service instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """
    Get or create the global embedding service.

    Returns:
        EmbeddingService instance
    """
    global _embedding_service

    if _embedding_service is None:
        _embedding_service = EmbeddingService()

    return _embedding_service
