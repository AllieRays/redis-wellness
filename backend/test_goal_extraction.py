"""Test goal extraction and storage in isolation."""

import asyncio
import logging

from langchain_core.messages import HumanMessage

from src.utils.conversation_fact_extractor import get_fact_extractor

logging.basicConfig(level=logging.INFO)


async def test_extraction():
    """Test if fact extractor recognizes 'my goal weight is 125 lbs'."""
    print("\n🧪 Testing Fact Extraction")
    print("=" * 60)

    extractor = get_fact_extractor()

    # Test various phrasings
    test_messages = [
        "my goal weight is 125 lbs",
        "my goal is 125 lbs",
        "goal: 125 lbs",
        "I want to reach 125 lbs",
    ]

    for text in test_messages:
        msg = HumanMessage(content=text)
        facts = extractor.extract_facts([msg])

        print(f"\nInput: '{text}'")
        print(f"Goals extracted: {len(facts.get('goals', []))}")
        if facts.get("goals"):
            for goal in facts["goals"]:
                print(f"  → {goal}")
        else:
            print("  ❌ NO GOALS EXTRACTED")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_extraction())
