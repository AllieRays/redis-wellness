"""Test procedural memory manager in isolation."""

import asyncio
import logging

logging.basicConfig(level=logging.INFO)


async def test_procedural_memory():
    """Test procedural memory store and retrieve."""
    print("\n" + "=" * 80)
    print("🧪 Testing Procedural Memory Manager")
    print("=" * 80)

    from src.services.procedural_memory_manager import get_procedural_memory

    # Get procedural memory instance
    procedural = get_procedural_memory()

    if not procedural:
        print("❌ Failed to initialize procedural memory")
        return

    print("\n✅ Procedural memory initialized")

    # Test 1: Store a successful pattern
    print("\n📝 Test 1: Store a successful workflow pattern")
    print("-" * 80)

    query1 = "What's my weight trend over the last month?"
    tools_used1 = [
        "search_health_records_by_metric",
        "aggregate_metrics",
        "calculate_weight_trends_tool",
    ]
    success_score1 = 0.95
    exec_time1 = 2340

    stored = await procedural.store_pattern(
        query=query1,
        tools_used=tools_used1,
        success_score=success_score1,
        execution_time_ms=exec_time1,
        metadata={"test": "pattern1"},
    )

    if stored:
        print(f"✅ Stored pattern: {query1[:50]}...")
        print(f"   Tools: {tools_used1}")
        print(f"   Score: {success_score1:.2%}, Time: {exec_time1}ms")
    else:
        print("❌ Failed to store pattern")

    # Test 2: Store another similar pattern
    print("\n📝 Test 2: Store similar pattern with different wording")
    print("-" * 80)

    query2 = "Show me my weight pattern recently"
    tools_used2 = ["search_health_records_by_metric", "calculate_weight_trends_tool"]
    success_score2 = 0.90
    exec_time2 = 1800

    stored = await procedural.store_pattern(
        query=query2,
        tools_used=tools_used2,
        success_score=success_score2,
        execution_time_ms=exec_time2,
    )

    if stored:
        print(f"✅ Stored pattern: {query2[:50]}...")
        print(f"   Tools: {tools_used2}")
        print(f"   Score: {success_score2:.2%}, Time: {exec_time2}ms")
    else:
        print("❌ Failed to store pattern")

    # Test 3: Retrieve patterns for similar query
    print("\n🔍 Test 3: Retrieve patterns for similar query")
    print("-" * 80)

    query3 = "What has my weight been doing lately?"
    result = await procedural.retrieve_patterns(query=query3, top_k=3)

    print(f"Query: {query3}")
    print(f"Query Type: {result.get('query_type')}")
    print(f"Patterns Found: {len(result.get('patterns', []))}")

    if result.get("patterns"):
        print("\nRetrieved Patterns:")
        for i, pattern in enumerate(result["patterns"], 1):
            print(f"\n  Pattern {i}:")
            print(f"    Query: {pattern.get('query_description')}")
            print(f"    Tools: {pattern.get('tools_used')}")
            print(f"    Success Score: {pattern.get('success_score'):.2%}")
            print(f"    Exec Time: {pattern.get('execution_time_ms')}ms")
    else:
        print("❌ No patterns retrieved")

    # Test 4: Check execution plan
    print("\n📋 Test 4: Check execution plan")
    print("-" * 80)

    plan = result.get("plan")
    if plan:
        print(f"Suggested Tools: {plan.get('suggested_tools')}")
        print(f"Reasoning: {plan.get('reasoning')}")
        print(f"Confidence: {plan.get('confidence'):.2%}")
    else:
        print("❌ No execution plan generated")

    # Test 5: Test workflow evaluation
    print("\n✅ Test 5: Test workflow success evaluation")
    print("-" * 80)

    tools_used_test = ["search_health_records_by_metric", "aggregate_metrics"]
    tool_results_test = [
        {"name": "search_health_records_by_metric", "content": "Found 30 records"},
        {"name": "aggregate_metrics", "content": "Average: 138.5 lbs"},
    ]

    evaluation = procedural.evaluate_workflow(
        tools_used=tools_used_test,
        tool_results=tool_results_test,
        response_generated=True,
        execution_time_ms=1500,
    )

    print(f"Success: {evaluation.get('success')}")
    print(f"Score: {evaluation.get('success_score'):.2%}")
    print(f"Reasons: {evaluation.get('reasons')}")

    # Test 6: Test query classification
    print("\n🏷️ Test 6: Test query classification (internal)")
    print("-" * 80)

    from src.services.procedural_memory_manager import _classify_query

    test_queries = [
        "What's my weight trend?",
        "Show me my workout schedule",
        "Compare this week to last week",
        "Am I making progress?",
        "What was my heart rate yesterday?",
    ]

    for query in test_queries:
        query_type = _classify_query(query)
        print(f"  '{query}' → {query_type}")

    print("\n" + "=" * 80)
    print("✅ All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_procedural_memory())
