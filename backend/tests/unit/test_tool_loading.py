#!/usr/bin/env python3
"""
Test script to verify aggregate_metrics tool is loaded correctly.
"""

import sys

sys.path.insert(0, "backend/src")

from src.tools import create_user_bound_tools

# Create tools for test user
tools = create_user_bound_tools("your_user")

print(f"✅ Total tools loaded: {len(tools)}")
print("\n📋 Tool names:")
for i, tool in enumerate(tools, 1):
    print(f"   {i}. {tool.name}")
    if hasattr(tool, "description"):
        desc = (
            tool.description[:100] + "..."
            if len(tool.description) > 100
            else tool.description
        )
        print(f"      Description: {desc}")

# Check if aggregate_metrics is present
tool_names = [tool.name for tool in tools]
if "aggregate_metrics" in tool_names:
    print("\n✅ aggregate_metrics tool IS loaded!")
else:
    print("\n❌ aggregate_metrics tool NOT found!")
    print(f"Available tools: {tool_names}")
