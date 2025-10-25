"""
Pytest configuration and shared fixtures for Redis Wellness tests.

REAL TESTS - NO MOCKS:
- Redis fixtures use real Redis (docker-compose required)
- LLM fixtures use real Ollama/Qwen (expensive, marked as @llm)
- All fixtures handle cleanup automatically
"""

import asyncio
import contextlib
import uuid
from collections.abc import Generator
from typing import Any

import pytest
from redis import Redis

from src.config import get_settings
from src.services.redis_connection import get_redis_manager

# ==================== Pytest Configuration ====================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Fast unit tests (no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (require Redis via docker-compose)"
    )
    config.addinivalue_line(
        "markers",
        "llm: LLM tests (require Ollama/Qwen - expensive, slow)",
    )
    config.addinivalue_line("markers", "api: API tests (require FastAPI TestClient)")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


# ==================== Settings ====================


@pytest.fixture(scope="session")
def settings():
    """Provide application settings."""
    return get_settings()


# ==================== Redis Fixtures (Real Redis Required) ====================


@pytest.fixture(scope="session")
def redis_client() -> Generator[Redis, None, None]:
    """
    Provide REAL Redis client for tests.

    Requires: docker-compose up redis

    Cleanup: Flushes test database at end of session.
    """
    manager = get_redis_manager()
    with manager.get_connection() as client:
        # Verify connection
        try:
            client.ping()
        except Exception as e:
            pytest.fail(
                f"Redis connection failed. Is docker-compose running?\n"
                f"Run: docker-compose up -d redis\n"
                f"Error: {e}"
            )

        yield client

        # Cleanup: flush test data at end of session
        with contextlib.suppress(Exception):
            client.flushdb()


@pytest.fixture
def clean_redis(redis_client: Redis) -> Generator[Redis, None, None]:
    """
    Ensure clean Redis state for each test function.

    Flushes database before and after test.
    """
    redis_client.flushdb()
    yield redis_client
    redis_client.flushdb()


# ==================== Test Data Fixtures ====================


@pytest.fixture
def sample_health_data() -> dict[str, Any]:
    """Provide sample health data for tests."""
    return {
        "BodyMass": [
            {"date": "2024-10-20", "value": 70.2, "unit": "kg"},
            {"date": "2024-10-21", "value": 70.0, "unit": "kg"},
            {"date": "2024-10-22", "value": 69.8, "unit": "kg"},
        ],
        "HeartRate": [
            {"date": "2024-10-20", "value": 72, "unit": "count/min"},
            {"date": "2024-10-21", "value": 75, "unit": "count/min"},
            {"date": "2024-10-22", "value": 70, "unit": "count/min"},
        ],
        "BodyMassIndex": [
            {"date": "2024-10-20", "value": 23.8, "unit": "count"},
            {"date": "2024-10-21", "value": 23.7, "unit": "count"},
            {"date": "2024-10-22", "value": 23.6, "unit": "count"},
        ],
    }


@pytest.fixture
def test_session_id() -> str:
    """Generate unique test session ID."""
    return f"test_session_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_user_id() -> str:
    """Get configured user ID for tests."""
    from src.utils.user_config import get_user_id

    return get_user_id()


# ==================== Agent Fixtures (Real Ollama Required) ====================


@pytest.fixture
async def stateless_agent():
    """
    Provide REAL stateless agent with Ollama/Qwen.

    Requires: Ollama running with qwen2.5:7b model
    Tests using this fixture should be marked with @pytest.mark.llm
    """
    from src.agents.stateless_agent import StatelessHealthAgent

    agent = StatelessHealthAgent()
    return agent


@pytest.fixture
async def stateful_agent(clean_redis: Redis):
    """
    Provide REAL stateful RAG agent with Ollama/Qwen + Redis memory.

    Mimics production initialization from RedisChatService.

    Requires:
    - Ollama running with qwen2.5:7b model
    - Redis running
    Tests using this fixture should be marked with @pytest.mark.llm
    """
    from src.agents.stateful_rag_agent import StatefulRAGAgent
    from src.services.episodic_memory_manager import get_episodic_memory
    from src.services.procedural_memory_manager import get_procedural_memory
    from src.services.redis_connection import get_redis_manager

    # Initialize memory components using same pattern as RedisChatService
    redis_manager = get_redis_manager()
    checkpointer = await redis_manager.get_checkpointer()
    episodic_memory = get_episodic_memory()
    procedural_memory = get_procedural_memory()

    agent = StatefulRAGAgent(
        checkpointer=checkpointer,
        episodic_memory=episodic_memory,
        procedural_memory=procedural_memory,
    )
    return agent


# ==================== API Test Fixtures ====================


@pytest.fixture
def test_client():
    """
    Provide FastAPI TestClient for API tests.

    Note: TestClient is synchronous, use for API endpoint testing only.
    """
    from fastapi.testclient import TestClient

    from src.main import app

    return TestClient(app)
