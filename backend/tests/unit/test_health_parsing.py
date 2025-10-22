#!/usr/bin/env python3
"""
Test script to verify health data parsing works with actual Apple Health export.

This script will test the complete pipeline:
1. Parse the Apple Health XML file
2. Store data in Redis with TTL
3. Query specific metrics
4. Generate health insights
"""

import asyncio
import pathlib
import sys

# Add the backend src to Python path
repo_root = pathlib.Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root / "backend" / "src"))

from src.agents.health_agent import process_health_conversation  # noqa: E402
from src.services.redis_health_tool import (  # noqa: E402
    query_health_metrics,
    store_health_data,
)
from src.tools.health_parser_tool import parse_health_file  # noqa: E402


def test_health_parser():
    """Test the health parser with actual Apple Health data."""
    print("🔍 Testing Apple Health XML Parser...")

    file_path = "apple_health_export/export.xml"

    try:
        # Test parsing
        print(f"📁 Parsing file: {file_path}")
        result = parse_health_file(file_path, anonymize=True)

        if result.success:
            data = result.data
            print(f"✅ Successfully parsed {data['record_count']} health records")
            print(f"📅 Export date: {data['export_date']}")
            print(f"📊 Data categories: {', '.join(data['data_categories'])}")
            print(f"📈 Date range: {data['date_range']['span_days']} days")
            print(f"🔒 Anonymized: {data['anonymized']}")

            # Show some metrics
            print("\n📋 Health Metrics Summary:")
            for metric, info in list(data["metrics_summary"].items())[:5]:
                count = info["count"]
                latest = info.get("latest_value", "N/A")
                print(f"  • {metric}: {count} records, latest: {latest}")

            return result
        else:
            print(f"❌ Parsing failed: {result.message}")
            return None

    except Exception as e:
        print(f"💥 Error during parsing: {str(e)}")
        return None


def test_redis_storage(parsed_data):
    """Test storing parsed health data in Redis."""
    print("\n💾 Testing Redis Storage...")

    if not parsed_data:
        print("❌ No parsed data to store")
        return None

    try:
        user_id = "test_user_123"

        # Test storing data
        print(f"🔧 Storing health data for user: {user_id}")
        store_result = store_health_data(
            user_id=user_id, health_data=parsed_data.data, ttl_days=7
        )

        if store_result.success:
            storage_info = store_result.data
            print(f"✅ Successfully stored data with {storage_info['ttl_days']} day TTL")
            print(f"🗝️ Redis keys created: {storage_info['redis_keys_created']}")
            print(f"⏰ Expires at: {storage_info['ttl_expires_at']}")

            return user_id
        else:
            print(f"❌ Storage failed: {store_result.message}")
            return None

    except Exception as e:
        print(f"💥 Error during storage: {str(e)}")
        return None


def test_redis_querying(user_id):
    """Test querying health metrics from Redis."""
    print("\n🔍 Testing Redis Querying...")

    if not user_id:
        print("❌ No user ID to query")
        return None

    try:
        # Test querying metrics
        metrics_to_query = ["BodyMassIndex", "DietaryWater"]
        print(f"📊 Querying metrics: {', '.join(metrics_to_query)}")

        query_result = query_health_metrics(
            user_id=user_id, metric_types=metrics_to_query, days_back=30
        )

        if query_result.success:
            query_data = query_result.data
            print(f"✅ Cache hit ratio: {query_data['cache_hit_ratio']:.2%}")
            print(
                f"⚡ Redis advantages: {query_data['redis_advantages']['lookup_speed']}"
            )

            # Show retrieved metrics
            print("\n📈 Retrieved Metrics:")
            for metric_type, data in query_data["metrics"].items():
                if "error" not in data:
                    print(f"  • {metric_type}: {data['count']} records")
                    if data.get("latest_value"):
                        print(f"    Latest: {data['latest_value']}")
                else:
                    print(f"  • {metric_type}: {data['error']}")

            return True
        else:
            print(f"❌ Query failed: {query_result.message}")
            return False

    except Exception as e:
        print(f"💥 Error during querying: {str(e)}")
        return False


async def test_langgraph_agent():
    """Test the complete LangGraph agent workflow."""
    print("\n🤖 Testing LangGraph AI Agent...")

    try:
        # Test various queries
        test_queries = [
            "How's my health data looking?",
            "What's my BMI trend?",
            "Parse my health file",
            "Show me my water intake",
        ]

        user_id = "test_user_123"

        for query in test_queries:
            print(f'\n👤 User: "{query}"')
            print("🤖 Agent: Processing...")

            response = await process_health_conversation(
                message=query, user_id=user_id, session_id="test_session"
            )

            print(f"💬 Response: {response[:200]}...")
            print("---")

        return True

    except Exception as e:
        print(f"💥 Error during agent testing: {str(e)}")
        return False


def main():
    """Run all health data tests."""
    print("🚀 Starting Redis Wellness Health Data Tests")
    print("=" * 60)

    # Test 1: Parse health data
    parsed_data = test_health_parser()

    if not parsed_data:
        print("❌ Cannot proceed - parsing failed")
        return

    # Test 2: Store in Redis
    user_id = test_redis_storage(parsed_data)

    if not user_id:
        print("❌ Cannot proceed - storage failed")
        return

    # Test 3: Query from Redis
    query_success = test_redis_querying(user_id)

    if not query_success:
        print("❌ Cannot proceed - querying failed")
        return

    # Test 4: LangGraph agent (async)
    print("\n🧠 Testing AI Agent Integration...")
    try:
        asyncio.run(test_langgraph_agent())
    except Exception as e:
        print(f"💥 Agent test failed: {str(e)}")

    print("\n✨ Health Data Pipeline Testing Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
