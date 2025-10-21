#!/usr/bin/env python3
"""Test script to verify RedisVL data storage and retrieval."""

import json
import os
import sys

# Add the backend src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from redisvl.redis.connection import Redis

from src.config import get_settings


def test_redis_connection():
    """Test basic Redis connection and data verification."""
    try:
        # Use application settings (environment-aware)
        settings = get_settings()

        # Connect to Redis using config
        redis_client = Redis(
            host=settings.redis_host,  # "redis" in Docker, configurable via env
            port=settings.redis_port,
            db=settings.redis_db,
            decode_responses=True,
        )

        # Test connection
        print(f"Connecting to Redis at {settings.redis_host}:{settings.redis_port}")
        ping_result = redis_client.ping()
        print(f"✅ Redis ping: {ping_result}")

        # Get all keys
        print("\n📋 All Redis keys:")
        keys = redis_client.keys("*")
        for key in keys:
            print(f"  - {key}")

        # Check chat sessions
        print("\n💬 Chat session data:")
        chat_keys = [k for k in keys if "chat_session" in k]

        for session_key in chat_keys:
            message_count = redis_client.llen(session_key)
            ttl = redis_client.ttl(session_key)

            print(f"\nSession: {session_key}")
            print(f"  Messages: {message_count}")
            print(f"  TTL: {ttl} seconds")

            # Get recent messages
            if message_count > 0:
                messages = redis_client.lrange(session_key, 0, 2)
                print("  Recent messages:")
                for i, msg_json in enumerate(messages):
                    try:
                        msg = json.loads(msg_json)
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")[:100]
                        if len(msg.get("content", "")) > 100:
                            content += "..."
                        print(f"    {i + 1}. {role}: {content}")
                    except json.JSONDecodeError:
                        print(f"    {i + 1}. Invalid JSON")

        # Check health data keys
        print("\n🏥 Health data keys:")
        health_keys = [
            k
            for k in keys
            if any(
                term in k.lower()
                for term in ["health", "bmi", "weight", "activity", "heart"]
            )
        ]

        if health_keys:
            for health_key in health_keys[:10]:
                key_type = redis_client.type(health_key)
                print(f"  - {health_key} (type: {key_type})")
        else:
            print("  No health-specific keys found")

        # Database info
        print("\n📊 Redis info:")
        info = redis_client.info()
        print(f"  Version: {info.get('redis_version', 'Unknown')}")
        print(f"  Memory: {info.get('used_memory_human', 'Unknown')}")
        print(f"  Keys: {info.get('db0', {}).get('keys', 0) if 'db0' in info else 0}")

        return True

    except Exception as e:
        print(f"❌ Redis connection error: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing RedisVL Data Storage")
    print("=" * 50)

    if test_redis_connection():
        print("\n✅ RedisVL verification complete!")
        print("💡 RedisInsight UI: http://localhost:8001")
    else:
        print("❌ Test failed - check containers:")
        print("  docker-compose ps")
