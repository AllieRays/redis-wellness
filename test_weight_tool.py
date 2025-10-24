#!/usr/bin/env python3
"""Test what the search_health_records_by_metric tool returns."""

import asyncio
import sys
sys.path.insert(0, '/Users/allierays/Sites/redis-wellness/backend')

from src.apple_health.query_tools.search_health_records import create_search_health_records_tool

async def test_weight_query():
    """Test weight query."""
    tool = create_search_health_records_tool("wellness_user")

    result = await tool.ainvoke({
        "metric_types": ["BodyMass"],
        "time_period": "recent"
    })

    import json
    print(json.dumps(result, indent=2))

    # Extract the weight values
    if "results" in result:
        for metric_result in result["results"]:
            if "records" in metric_result:
                records = metric_result["records"]
                print(f"\n\nFound {len(records)} records")
                print("Recent values:")
                for record in records[-5:]:
                    print(f"  {record['date']}: {record['value']}")

if __name__ == "__main__":
    asyncio.run(test_weight_query())
