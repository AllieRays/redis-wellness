"""
Quick test of LangGraph agent (no memory coordinator yet).
"""

import asyncio
import sys

sys.path.insert(0, "/Users/allierays/Sites/redis-wellness/backend/src")

from agents.langgraph_agent import LangGraphHealthAgent


async def test_weight_query():
    """Test basic weight query without memory."""
    print("🧪 Testing LangGraph agent (no memory)...")

    # Initialize without memory
    agent = LangGraphHealthAgent(memory_coordinator=None)

    # Test weight query
    result = await agent.chat(
        message="how much do I weigh", user_id="wellness_user", session_id="test"
    )

    print(f"\n✅ Response: {result['response'][:200]}...")
    print(f"📊 Tools used: {result['tools_used']}")
    print(f"🔧 Tool calls made: {result['tool_calls_made']}")
    print(f"✓ Validation: {result['validation']}")

    # Verify tools were called
    assert result["tools_used"], "❌ NO TOOLS CALLED"
    assert "search_health_records_by_metric" in result["tools_used"], "❌ Wrong tool"

    print("\n🎉 LangGraph agent works! Tools called successfully.")


if __name__ == "__main__":
    asyncio.run(test_weight_query())
