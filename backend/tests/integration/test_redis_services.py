"""
Integration tests for Redis services.

REAL TESTS - REQUIRE REDIS:
- Tests real Redis connection and operations
- Requires: docker-compose up -d redis
- No mocks - tests actual Redis data flow
"""

import json

import pytest

from src.services.redis_connection import get_redis_manager


@pytest.mark.integration
class TestRedisConnection:
    """Test Redis connection management."""

    def test_redis_connection_ping(self, redis_client):
        """Test Redis is accessible."""
        result = redis_client.ping()

        assert result is True

    def test_redis_set_get(self, clean_redis):
        """Test basic Redis set/get operations."""
        clean_redis.set("test_key", "test_value")

        result = clean_redis.get("test_key")

        assert result == b"test_value" or result == "test_value"

    def test_redis_json_storage(self, clean_redis):
        """Test storing/retrieving JSON data."""
        data = {"weight": 70.2, "unit": "kg", "date": "2024-10-22"}

        clean_redis.set("health:weight", json.dumps(data))
        retrieved = json.loads(clean_redis.get("health:weight"))

        assert retrieved["weight"] == 70.2
        assert retrieved["unit"] == "kg"

    def test_redis_ttl(self, clean_redis):
        """Test TTL (time-to-live) setting."""
        clean_redis.set("temp_key", "value", ex=60)  # 60 seconds

        ttl = clean_redis.ttl("temp_key")

        assert ttl > 0
        assert ttl <= 60

    def test_redis_flushdb(self, redis_client):
        """Test database flush (cleanup)."""
        redis_client.set("key1", "value1")
        redis_client.set("key2", "value2")

        redis_client.flushdb()

        assert redis_client.get("key1") is None
        assert redis_client.get("key2") is None


@pytest.mark.integration
class TestRedisManager:
    """Test Redis connection manager."""

    def test_redis_manager_connection(self):
        """Test getting connection from manager."""
        manager = get_redis_manager()

        with manager.get_connection() as client:
            result = client.ping()

            assert result is True

    def test_redis_manager_multiple_connections(self):
        """Test manager handles multiple connection requests."""
        manager = get_redis_manager()

        with (
            manager.get_connection() as client1,
            manager.get_connection() as client2,
        ):
            assert client1.ping() is True
            assert client2.ping() is True
