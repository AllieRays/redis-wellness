"""
Unit tests for embedding cache service.

Tests cache hit/miss behavior, statistics tracking, and TTL management.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.embedding_cache import EmbeddingCache


@pytest.fixture
def mock_redis_manager():
    """Mock Redis connection manager."""
    mock_manager = Mock()
    mock_client = Mock()

    # Setup context manager
    mock_manager.get_connection.return_value.__enter__.return_value = mock_client
    mock_manager.get_connection.return_value.__exit__.return_value = None

    return mock_manager, mock_client


@pytest.mark.asyncio
async def test_cache_miss_then_hit(mock_redis_manager):
    """Test cache miss followed by cache hit."""
    mock_manager, mock_client = mock_redis_manager

    # First call: cache miss (returns None)
    mock_client.get.return_value = None

    with patch(
        "src.services.embedding_cache.get_redis_manager", return_value=mock_manager
    ):
        cache = EmbeddingCache(ttl_seconds=3600)

        # Cache miss
        result = await cache.get("test query")
        assert result is None
        assert cache.stats["misses"] == 1
        assert cache.stats["hits"] == 0

        # Store in cache
        test_embedding = [0.1, 0.2, 0.3]
        await cache.set("test query", test_embedding)

        # Verify SETEX was called with correct TTL
        mock_client.setex.assert_called_once()
        args = mock_client.setex.call_args[0]
        assert args[1] == 3600  # TTL


@pytest.mark.asyncio
async def test_get_or_generate_cache_miss(mock_redis_manager):
    """Test get_or_generate with cache miss."""
    mock_manager, mock_client = mock_redis_manager
    mock_client.get.return_value = None

    with patch(
        "src.services.embedding_cache.get_redis_manager", return_value=mock_manager
    ):
        cache = EmbeddingCache(ttl_seconds=3600)

        # Mock generation function
        test_embedding = [0.1, 0.2, 0.3]
        generate_fn = AsyncMock(return_value=test_embedding)

        # Get or generate (cache miss)
        result = await cache.get_or_generate("test query", generate_fn)

        # Verify generation was called
        generate_fn.assert_called_once()
        assert result == test_embedding

        # Verify cache stats
        assert cache.stats["misses"] == 1
        assert cache.stats["hits"] == 0


@pytest.mark.asyncio
async def test_get_or_generate_cache_hit(mock_redis_manager):
    """Test get_or_generate with cache hit."""
    import json

    mock_manager, mock_client = mock_redis_manager

    # Mock cached embedding
    cached_embedding = [0.1, 0.2, 0.3]
    mock_client.get.return_value = json.dumps(cached_embedding)

    with patch(
        "src.services.embedding_cache.get_redis_manager", return_value=mock_manager
    ):
        cache = EmbeddingCache(ttl_seconds=3600)

        # Mock generation function (should NOT be called)
        generate_fn = AsyncMock(return_value=[9.9, 9.9, 9.9])

        # Get or generate (cache hit)
        result = await cache.get_or_generate("test query", generate_fn)

        # Verify generation was NOT called
        generate_fn.assert_not_called()
        assert result == cached_embedding

        # Verify cache stats
        assert cache.stats["hits"] == 1
        assert cache.stats["misses"] == 0


def test_cache_key_generation():
    """Test cache key generation is deterministic."""
    with patch("src.services.embedding_cache.get_redis_manager"):
        cache = EmbeddingCache()

        # Same query generates same key
        key1 = cache._generate_cache_key("test query")
        key2 = cache._generate_cache_key("test query")
        assert key1 == key2

        # Different query generates different key
        key3 = cache._generate_cache_key("different query")
        assert key1 != key3

        # Key format
        assert key1.startswith("embedding_cache:")


def test_hit_rate_calculation():
    """Test hit rate calculation."""
    with patch("src.services.embedding_cache.get_redis_manager"):
        cache = EmbeddingCache()

        # Initial state
        assert cache.stats["hit_rate"] == 0.0

        # After 1 hit, 0 misses
        cache._record_hit()
        assert cache.stats["hit_rate"] == 1.0

        # After 1 hit, 1 miss
        cache._record_miss()
        assert cache.stats["hit_rate"] == 0.5

        # After 2 hits, 1 miss
        cache._record_hit()
        assert cache.stats["hit_rate"] == 2 / 3


def test_get_stats():
    """Test statistics retrieval."""
    with patch("src.services.embedding_cache.get_redis_manager"):
        cache = EmbeddingCache(ttl_seconds=3600)

        # Simulate some activity
        cache._record_hit()
        cache._record_hit()
        cache._record_miss()

        stats = cache.get_stats()

        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total_queries"] == 3
        assert stats["hit_rate"] == "66.67%"
        assert stats["hit_rate_float"] == 2 / 3
        assert stats["estimated_time_saved_ms"] == 400  # 2 hits × 200ms
        assert stats["cache_ttl_seconds"] == 3600
