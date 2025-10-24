"""
Integration tests for Redis connection management.

Tests:
- Connection pooling
- Connection lifecycle
- Error handling
- Ping/health checks
"""

import pytest

from src.services.redis_connection import get_redis_manager


@pytest.mark.integration
class TestRedisConnection:
    """Test Redis connection manager."""

    def test_redis_connection_basic(self, redis_client):
        """Test basic Redis connection."""
        # Set and get value
        redis_client.set("test_key", "test_value")
        value = redis_client.get("test_key")

        assert value == b"test_value"

    def test_redis_ping(self, redis_client):
        """Test Redis ping/health check."""
        assert redis_client.ping() is True

    def test_redis_connection_manager_context(self):
        """Test connection manager context."""
        manager = get_redis_manager()

        with manager.get_connection() as client:
            client.set("context_test", "value")
            assert client.get("context_test") == b"value"

    def test_redis_connection_pool_reuse(self):
        """Test that connections are pooled and reused."""
        manager = get_redis_manager()

        with manager.get_connection() as client1:
            pool_id1 = id(client1.connection_pool)

        with manager.get_connection() as client2:
            pool_id2 = id(client2.connection_pool)

        # Same pool should be reused
        assert pool_id1 == pool_id2

    def test_redis_multiple_keys(self, clean_redis):
        """Test storing and retrieving multiple keys."""
        clean_redis.mset({"key1": "value1", "key2": "value2", "key3": "value3"})

        values = clean_redis.mget(["key1", "key2", "key3"])

        assert values == [b"value1", b"value2", b"value3"]

    def test_redis_key_expiration(self, clean_redis):
        """Test key expiration (TTL)."""
        import time

        clean_redis.set("expire_test", "value", ex=1)  # 1 second TTL
        assert clean_redis.get("expire_test") == b"value"

        # Wait for expiration
        time.sleep(1.5)
        assert clean_redis.get("expire_test") is None

    def test_redis_delete_key(self, clean_redis):
        """Test deleting keys."""
        clean_redis.set("delete_test", "value")
        assert clean_redis.get("delete_test") == b"value"

        clean_redis.delete("delete_test")
        assert clean_redis.get("delete_test") is None

    def test_redis_list_operations(self, clean_redis):
        """Test Redis list operations."""
        clean_redis.lpush("test_list", "item1", "item2", "item3")
        items = clean_redis.lrange("test_list", 0, -1)

        assert len(items) == 3
        assert b"item3" in items  # Last pushed is first

    def test_redis_json_storage(self, clean_redis):
        """Test storing JSON data."""
        import json

        data = {"name": "test", "value": 123, "nested": {"key": "value"}}
        clean_redis.set("json_test", json.dumps(data))

        retrieved = json.loads(clean_redis.get("json_test"))

        assert retrieved["name"] == "test"
        assert retrieved["value"] == 123
        assert retrieved["nested"]["key"] == "value"


@pytest.mark.integration
class TestRedisCheckpointer:
    """Test LangGraph checkpointer uses Redis, not MemorySaver."""

    def test_checkpointer_uses_redis_saver(self):
        """
        CRITICAL TEST: Verify we're using RedisSaver for conversation persistence.

        This test ensures conversation history persists across container restarts.
        If this test fails, we're using MemorySaver which loses all data on restart.
        """
        from langgraph.checkpoint.memory import MemorySaver
        from langgraph.checkpoint.redis import RedisSaver

        manager = get_redis_manager()
        checkpointer = manager.get_checkpointer()

        # CRITICAL: Must be RedisSaver, not MemorySaver
        assert isinstance(
            checkpointer, RedisSaver
        ), f"Expected RedisSaver but got {type(checkpointer).__name__}. Conversation history will NOT persist!"

        # Ensure it's NOT MemorySaver
        assert not isinstance(
            checkpointer, MemorySaver
        ), "Using MemorySaver! Conversations will be lost on restart!"

    def test_checkpointer_is_cached(self):
        """Test that checkpointer instance is cached and reused."""
        manager = get_redis_manager()

        checkpointer1 = manager.get_checkpointer()
        checkpointer2 = manager.get_checkpointer()

        # Should return the same instance
        assert (
            checkpointer1 is checkpointer2
        ), "Checkpointer should be cached, not recreated"


@pytest.mark.integration
class TestRedisErrorHandling:
    """Test Redis error handling."""

    def test_nonexistent_key(self, clean_redis):
        """Test accessing nonexistent key."""
        value = clean_redis.get("nonexistent_key")
        assert value is None

    def test_flushdb_cleanup(self, clean_redis):
        """Test database flush cleanup."""
        clean_redis.set("key1", "value1")
        clean_redis.set("key2", "value2")

        clean_redis.flushdb()

        assert clean_redis.get("key1") is None
        assert clean_redis.get("key2") is None
