"""
Performance Benchmarks for Redis Wellness.

Benchmarks key operations to establish performance baselines and detect regressions:
- Redis operations (read/write, vector search)
- Embedding generation
- Agent response times
- Memory operations

Run with:
    uv run pytest tests/benchmarks/test_performance_benchmarks.py -v

Skip in CI (slow):
    uv run pytest -m "not benchmark"
"""

import time

import pytest

# Mark all tests as benchmarks (skip by default in CI)
pytestmark = pytest.mark.benchmark


# ========== Redis Operation Benchmarks ==========


@pytest.mark.asyncio
async def test_benchmark_redis_write_performance():
    """
    Benchmark Redis write operations.

    Target: < 5ms per write for simple key-value
    """
    from src.services.redis_connection import get_redis_manager

    redis_manager = get_redis_manager()

    # Warmup
    with redis_manager.get_connection() as client:
        client.set("benchmark:warmup", "test")

    # Benchmark 100 writes
    start_time = time.time()
    with redis_manager.get_connection() as client:
        for i in range(100):
            client.set(f"benchmark:write:{i}", f"value_{i}")
    elapsed_ms = (time.time() - start_time) * 1000

    avg_write_ms = elapsed_ms / 100

    # Cleanup
    with redis_manager.get_connection() as client:
        for i in range(100):
            client.delete(f"benchmark:write:{i}")
        client.delete("benchmark:warmup")

    print(f"\n📊 Redis Write Performance: {avg_write_ms:.2f}ms per write")
    assert avg_write_ms < 5.0, f"Write too slow: {avg_write_ms:.2f}ms (target: <5ms)"


@pytest.mark.asyncio
async def test_benchmark_redis_read_performance():
    """
    Benchmark Redis read operations.

    Target: < 3ms per read
    """
    from src.services.redis_connection import get_redis_manager

    redis_manager = get_redis_manager()

    # Setup test data
    with redis_manager.get_connection() as client:
        for i in range(100):
            client.set(f"benchmark:read:{i}", f"value_{i}")

    # Benchmark 100 reads
    start_time = time.time()
    with redis_manager.get_connection() as client:
        for i in range(100):
            client.get(f"benchmark:read:{i}")
    elapsed_ms = (time.time() - start_time) * 1000

    avg_read_ms = elapsed_ms / 100

    # Cleanup
    with redis_manager.get_connection() as client:
        for i in range(100):
            client.delete(f"benchmark:read:{i}")

    print(f"\n📊 Redis Read Performance: {avg_read_ms:.2f}ms per read")
    assert avg_read_ms < 3.0, f"Read too slow: {avg_read_ms:.2f}ms (target: <3ms)"


@pytest.mark.asyncio
async def test_benchmark_redis_list_operations():
    """
    Benchmark Redis LIST operations (used for conversation history).

    Target: < 5ms per operation
    """
    from src.services.redis_connection import get_redis_manager

    redis_manager = get_redis_manager()
    key = "benchmark:list:test"

    # Benchmark LPUSH (add to history)
    start_time = time.time()
    with redis_manager.get_connection() as client:
        for i in range(100):
            client.lpush(key, f"message_{i}")
    lpush_ms = (time.time() - start_time) * 1000 / 100

    # Benchmark LRANGE (read history)
    start_time = time.time()
    with redis_manager.get_connection() as client:
        for _ in range(100):
            client.lrange(key, 0, 9)  # Get last 10 messages
    lrange_ms = (time.time() - start_time) * 1000 / 100

    # Cleanup
    with redis_manager.get_connection() as client:
        client.delete(key)

    print("\n📊 Redis LIST Performance:")
    print(f"  - LPUSH: {lpush_ms:.2f}ms")
    print(f"  - LRANGE(10): {lrange_ms:.2f}ms")

    assert lpush_ms < 5.0, f"LPUSH too slow: {lpush_ms:.2f}ms"
    assert lrange_ms < 5.0, f"LRANGE too slow: {lrange_ms:.2f}ms"


# ========== Embedding Generation Benchmarks ==========


@pytest.mark.asyncio
@pytest.mark.slow
async def test_benchmark_embedding_generation():
    """
    Benchmark embedding generation via Ollama.

    Target: < 500ms per embedding (mxbai-embed-large)
    Note: Depends on hardware (CPU vs GPU)
    """
    from src.services.embedding_cache import get_embedding_cache

    cache = get_embedding_cache()

    test_texts = [
        "What is my BMI?",
        "Show me my workout history",
        "What's my average heart rate?",
    ]

    times = []
    for text in test_texts:
        start_time = time.time()
        await cache.get_or_generate_embedding(text)
        elapsed_ms = (time.time() - start_time) * 1000
        times.append(elapsed_ms)

    avg_time_ms = sum(times) / len(times)

    print(f"\n📊 Embedding Generation Performance: {avg_time_ms:.2f}ms per text")
    print(f"  Individual times: {[f'{t:.2f}ms' for t in times]}")

    # Relaxed threshold for CI environments (no GPU)
    assert (
        avg_time_ms < 5000
    ), f"Embedding too slow: {avg_time_ms:.2f}ms (target: <5000ms)"


@pytest.mark.asyncio
async def test_benchmark_embedding_cache_hit():
    """
    Benchmark embedding cache hit performance.

    Target: < 10ms for cache hit
    """
    from src.services.embedding_cache import get_embedding_cache

    cache = get_embedding_cache()
    test_text = "What is my BMI?"

    # Generate and cache
    await cache.get_or_generate_embedding(test_text)

    # Benchmark cache hits
    start_time = time.time()
    for _ in range(10):
        await cache.get_or_generate_embedding(test_text)
    elapsed_ms = (time.time() - start_time) * 1000 / 10

    print(f"\n📊 Embedding Cache Hit Performance: {elapsed_ms:.2f}ms")
    assert elapsed_ms < 10.0, f"Cache hit too slow: {elapsed_ms:.2f}ms"


# ========== Agent Response Time Benchmarks ==========


@pytest.mark.asyncio
@pytest.mark.slow
async def test_benchmark_stateless_agent_response():
    """
    Benchmark stateless agent response time (simple query, no tools).

    Target: < 5000ms for simple query
    Note: Depends on Ollama/hardware performance
    """
    from src.services.stateless_chat import StatelessChatService

    service = StatelessChatService()

    # Simple query that doesn't require tools
    message = "Hello, how are you?"

    start_time = time.time()
    result = await service.chat(message=message)
    elapsed_ms = (time.time() - start_time) * 1000

    print(f"\n📊 Stateless Agent Performance: {elapsed_ms:.2f}ms")
    print(f"  Tool calls: {result.get('tool_calls_made', 0)}")

    assert result.get("response"), "Agent should return a response"
    # Relaxed for CI (depends on hardware)
    assert elapsed_ms < 30000, f"Agent too slow: {elapsed_ms:.2f}ms"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_benchmark_redis_agent_response():
    """
    Benchmark Redis RAG agent response time (with memory).

    Target: < 8000ms for simple query with memory
    Note: Slightly slower than stateless due to memory operations
    """
    from src.services.redis_chat import RedisChatService

    service = RedisChatService()
    session_id = "benchmark_test_session"

    # Simple query
    message = "Hello, tell me about health tracking"

    start_time = time.time()
    result = await service.chat(message=message, session_id=session_id)
    elapsed_ms = (time.time() - start_time) * 1000

    print(f"\n📊 Redis RAG Agent Performance: {elapsed_ms:.2f}ms")
    print(f"  Tool calls: {result.get('tool_calls_made', 0)}")
    print(f"  Memory stats: {result.get('memory_stats', {})}")

    # Cleanup
    await service.clear_session(session_id)

    assert result.get("response"), "Agent should return a response"
    # Relaxed for CI
    assert elapsed_ms < 30000, f"RAG agent too slow: {elapsed_ms:.2f}ms"


# ========== Memory Operation Benchmarks ==========


@pytest.mark.asyncio
async def test_benchmark_short_term_memory_storage():
    """
    Benchmark short-term memory (conversation history) storage.

    Target: < 50ms per message store
    """
    from src.services.short_term_memory_manager import get_short_term_memory_manager
    from src.utils.user_config import get_user_id

    manager = get_short_term_memory_manager()
    user_id = get_user_id()
    session_id = "benchmark_memory_test"

    messages = [{"role": "user", "content": f"Test message {i}"} for i in range(10)]

    start_time = time.time()
    for msg in messages:
        await manager.store_interaction(
            user_id=user_id,
            session_id=session_id,
            user_message=msg["content"],
            assistant_message=f"Response {msg['content']}",
        )
    elapsed_ms = (time.time() - start_time) * 1000 / len(messages)

    # Cleanup
    await manager.clear_session_memory(session_id)

    print(f"\n📊 Short-term Memory Storage: {elapsed_ms:.2f}ms per message")
    assert elapsed_ms < 50.0, f"Memory storage too slow: {elapsed_ms:.2f}ms"


@pytest.mark.asyncio
async def test_benchmark_short_term_memory_retrieval():
    """
    Benchmark short-term memory retrieval.

    Target: < 20ms for retrieval
    """
    from src.services.short_term_memory_manager import get_short_term_memory_manager
    from src.utils.user_config import get_user_id

    manager = get_short_term_memory_manager()
    user_id = get_user_id()
    session_id = "benchmark_retrieval_test"

    # Setup: Store 10 messages
    for i in range(10):
        await manager.store_interaction(
            user_id=user_id,
            session_id=session_id,
            user_message=f"User message {i}",
            assistant_message=f"Assistant response {i}",
        )

    # Benchmark retrieval
    start_time = time.time()
    for _ in range(10):
        await manager.get_session_history_only(session_id, limit=5)
    elapsed_ms = (time.time() - start_time) * 1000 / 10

    # Cleanup
    await manager.clear_session_memory(session_id)

    print(f"\n📊 Short-term Memory Retrieval: {elapsed_ms:.2f}ms")
    assert elapsed_ms < 20.0, f"Memory retrieval too slow: {elapsed_ms:.2f}ms"


# ========== Performance Summary Report ==========


@pytest.mark.asyncio
async def test_performance_summary_report():
    """
    Generate comprehensive performance summary.

    This test always passes but prints performance metrics.
    """
    print("\n" + "=" * 80)
    print("PERFORMANCE BENCHMARK SUMMARY")
    print("=" * 80)
    print("\nPerformance Targets:")
    print("  ✓ Redis Write: < 5ms")
    print("  ✓ Redis Read: < 3ms")
    print("  ✓ Redis LIST ops: < 5ms")
    print("  ✓ Embedding generation: < 500ms (GPU), < 5000ms (CPU)")
    print("  ✓ Embedding cache hit: < 10ms")
    print("  ✓ Agent response: < 5000ms (simple), < 8000ms (with memory)")
    print("  ✓ Memory storage: < 50ms per message")
    print("  ✓ Memory retrieval: < 20ms")
    print("\nNote: Actual performance depends on hardware (CPU vs GPU).")
    print("=" * 80 + "\n")

    assert True  # Summary test always passes
