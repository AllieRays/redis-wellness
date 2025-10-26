"""
Test episodic memory in isolation - store and retrieve goal of 125 lbs.
"""

import asyncio

from src.services.episodic_memory_manager import get_episodic_memory
from src.utils.user_config import get_user_id


async def test_goal_storage():
    """Test storing and retrieving 125 lbs goal."""
    print("\n🧪 Testing Episodic Memory (Goal: 125 lbs)\n" + "=" * 50)

    episodic = get_episodic_memory()
    user_id = get_user_id()

    # Test 1: Store goal
    print("\n📝 Test 1: Storing goal 'weight goal is 125 lbs'...")
    success = await episodic.store_goal(
        user_id=user_id,
        metric="weight",
        value=125,
        unit="lbs",
    )
    print(f"   Result: {'✅ SUCCESS' if success else '❌ FAILED'}")

    # Test 2: Retrieve goal with exact query
    print("\n🔍 Test 2: Retrieving with query 'what is my weight goal'...")
    result = await episodic.retrieve_goals(
        user_id=user_id,
        query="what is my weight goal",
        top_k=1,
    )
    print(f"   Hits: {result['hits']}")
    print(f"   Context: {result['context']}")
    print(f"   Goals: {result['goals']}")

    # Test 3: Retrieve with casual query
    print("\n🔍 Test 3: Retrieving with query 'my goal'...")
    result = await episodic.retrieve_goals(
        user_id=user_id,
        query="my goal",
        top_k=1,
    )
    print(f"   Hits: {result['hits']}")
    print(f"   Context: {result['context']}")

    # Test 4: Verify it's exactly 125 (not 128 or 130)
    print("\n✅ Test 4: Verifying exact value...")
    if result["goals"]:
        goal = result["goals"][0]
        if goal["value"] == 125 and goal["unit"] == "lbs":
            print(f"   ✅ CORRECT: {goal['value']} {goal['unit']}")
        else:
            print(f"   ❌ WRONG: Expected 125 lbs, got {goal['value']} {goal['unit']}")
    else:
        print("   ❌ No goals found")

    print("\n" + "=" * 50)
    print("🎉 Test complete!")


if __name__ == "__main__":
    asyncio.run(test_goal_storage())
