#!/usr/bin/env python3
"""
Standalone script to verify RedisSaver is being used for LangGraph checkpointing.

This is a CRITICAL production verification - conversation history must persist.
"""

import sys
from pathlib import Path

# Add src to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from src.services.redis_connection import get_redis_manager  # noqa: E402


def verify_redis_checkpointer():
    """Verify we're using RedisSaver, not MemorySaver."""
    print("🔍 Verifying LangGraph checkpointer configuration...")

    try:
        from langgraph.checkpoint.memory import MemorySaver
        from langgraph.checkpoint.redis import AsyncRedisSaver, RedisSaver

        manager = get_redis_manager()
        checkpointer = manager.get_checkpointer()

        # Check if it's AsyncRedisSaver or RedisSaver
        is_async_redis_saver = isinstance(checkpointer, AsyncRedisSaver)
        is_redis_saver = isinstance(checkpointer, RedisSaver)
        is_memory_saver = isinstance(checkpointer, MemorySaver)

        print(f"\nCheckpointer type: {type(checkpointer).__name__}")
        print(f"Is AsyncRedisSaver: {is_async_redis_saver}")
        print(f"Is RedisSaver: {is_redis_saver}")
        print(f"Is MemorySaver: {is_memory_saver}")

        if not (is_async_redis_saver or is_redis_saver):
            print("\n❌ CRITICAL FAILURE: Not using Redis-based saver!")
            print("   Conversation history will NOT persist across restarts.")
            return False

        if is_memory_saver:
            print("\n❌ CRITICAL FAILURE: Using MemorySaver!")
            print("   Conversations will be lost on container restart.")
            return False

        if is_redis_saver and not is_async_redis_saver:
            print("\n⚠️  WARNING: Using sync RedisSaver instead of AsyncRedisSaver!")
            print("   AsyncRedisSaver is recommended for async graph operations.")

        # Test checkpointer caching
        checkpointer2 = manager.get_checkpointer()
        is_cached = checkpointer is checkpointer2

        print(f"Checkpointer is cached: {is_cached}")

        if not is_cached:
            print("\n⚠️  WARNING: Checkpointer is not cached!")
            print("   This may create multiple Redis connections unnecessarily.")

        saver_type = "AsyncRedisSaver" if is_async_redis_saver else "RedisSaver"
        print(f"\n✅ SUCCESS: Using {saver_type} for conversation persistence!")
        print("   Conversations will persist across container restarts.")
        return True

    except ImportError as e:
        print(f"\n❌ IMPORT ERROR: {e}")
        print("   Cannot verify checkpointer type.")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_redis_checkpointer()
    sys.exit(0 if success else 1)
