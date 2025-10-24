"""
Pytest configuration and shared fixtures for Redis Wellness tests.

Provides:
- Test markers (unit, integration, agent, e2e)
- Redis fixtures with cleanup
- Memory manager fixtures
- Health data fixtures
- Mock LLM response fixtures
"""

import asyncio
import json
import uuid
from collections.abc import Generator
from contextlib import contextmanager, suppress
from typing import Any

import pytest
from redis import Redis

from src.config import get_settings
from src.services.memory_coordinator import get_memory_coordinator
from src.services.redis_connection import get_redis_manager
from src.services.short_term_memory_manager import get_short_term_memory_manager

# ========== Pytest Configuration ==========


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (require Redis)")
    config.addinivalue_line("markers", "agent: Agent tests (LLM-dependent)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (full workflows)")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ========== Redis Fixtures ==========


@pytest.fixture(scope="session")
def redis_client() -> Generator[Redis, None, None]:
    """Provide Redis client for tests with session-level cleanup."""
    manager = get_redis_manager()
    with manager.get_connection() as client:
        # Verify connection
        client.ping()
        yield client
        # Cleanup: flush test data at end of session
        with suppress(Exception):
            client.flushdb()


@pytest.fixture(scope="function")
def clean_redis(redis_client):
    """Ensure clean Redis state for each test function."""
    redis_client.flushdb()
    yield redis_client
    redis_client.flushdb()


# ========== Memory Fixtures ==========


@pytest.fixture
def memory_coordinator():
    """Provide memory coordinator for tests."""
    return get_memory_coordinator()


@pytest.fixture
def short_term_memory_manager():
    """Provide short-term memory manager for tests."""
    return get_short_term_memory_manager()


@pytest.fixture
async def isolated_memory_session(short_term_memory_manager):
    """Provide isolated memory session with auto-cleanup."""
    session_id = f"test_{uuid.uuid4()}"
    user_id = "test_user"

    yield user_id, session_id

    # Cleanup
    with suppress(Exception):
        await short_term_memory_manager.clear_session(user_id, session_id)


# ========== Health Data Fixtures ==========


@pytest.fixture
def sample_health_data():
    """Provide sample health data for tests."""
    return {
        "metrics_summary": {
            "BodyMass": {
                "latest_value": 70,
                "unit": "kg",
                "count": 30,
                "latest_date": "2024-10-22",
            },
            "BodyMassIndex": {
                "latest_value": 23.6,
                "unit": "count",
                "count": 30,
                "latest_date": "2024-10-22",
            },
            "HeartRate": {
                "latest_value": 72,
                "unit": "count/min",
                "count": 100,
                "latest_date": "2024-10-22",
            },
        },
        "metrics_records": {
            "BodyMass": [
                {"date": "2024-10-20", "value": 70.2, "unit": "kg"},
                {"date": "2024-10-21", "value": 70.0, "unit": "kg"},
                {"date": "2024-10-22", "value": 69.8, "unit": "kg"},
            ],
            "BodyMassIndex": [
                {"date": "2024-10-20", "value": 23.8, "unit": "count"},
                {"date": "2024-10-21", "value": 23.7, "unit": "count"},
                {"date": "2024-10-22", "value": 23.6, "unit": "count"},
            ],
        },
    }


@pytest.fixture
def health_data_fixture(sample_health_data, redis_client):
    """Context manager to load health data into Redis for tests."""

    @contextmanager
    def _load_health_data(user_id: str = "default_user"):
        from src.utils.user_config import get_user_health_data_key

        key = get_user_health_data_key(user_id)
        redis_client.set(key, json.dumps(sample_health_data))

        try:
            yield
        finally:
            redis_client.delete(key)

    return _load_health_data


# ========== Mock LLM Fixtures ==========


@pytest.fixture
def mock_ollama_response():
    """Provide mock Ollama responses for deterministic tests."""
    from langchain_core.messages import AIMessage

    def _create_response(content: str = "", tool_calls: list | None = None):
        return AIMessage(content=content, tool_calls=tool_calls or [])

    return _create_response


@pytest.fixture
def mock_tool_call():
    """Create mock tool call structure."""

    def _create_tool_call(name: str, args: dict[str, Any], call_id: str | None = None):
        return {
            "name": name,
            "args": args,
            "id": call_id or f"call_{uuid.uuid4()}",
        }

    return _create_tool_call


# ========== Settings Fixtures ==========


@pytest.fixture
def settings():
    """Provide application settings."""
    return get_settings()
