#!/usr/bin/env python3
"""Quick test script to debug compare_time_periods_tool."""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from apple_health.query_tools import create_user_bound_tools


async def test_compare():
    """Test the compare tool directly."""
    tools = create_user_bound_tools("wellness_user")

    # Find compare tool
    compare_tool = None
    for tool in tools:
        if "compare" in tool.name.lower():
            compare_tool = tool
            break

    if not compare_tool:
        print("❌ Compare tool not found!")
        return

    print(f"✅ Found tool: {compare_tool.name}")
    print(f"Tool description: {compare_tool.description[:100]}...")

    # Test with different period formats
    test_cases = [
        {"metric_type": "StepCount", "period1": "October 2025", "period2": "September 2025"},
        {"metric_type": "StepCount", "period1": "October_2025", "period2": "September_2025"},
    ]

    for i, args in enumerate(test_cases, 1):
        print(f"\n\n--- Test {i}: {args['period1']} vs {args['period2']} ---")
        try:
            result = await compare_tool.ainvoke(args)
            print(f"Result type: {type(result)}")
            print(f"Result: {json.dumps(result, indent=2)}")
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_compare())
