#!/usr/bin/env python3
"""
Simple script to load Apple Health data via the backend API.

This bypasses import issues by calling the backend tools through the API.
"""
import sys
import os

# Set Python path to find modules
project_root = os.path.dirname(os.path.dirname(__file__))
backend_src = os.path.join(project_root, 'backend', 'src')
sys.path.insert(0, backend_src)

from tools.health_parser_tool import parse_health_file
from tools.redis_health_tool import redis_manager

def main():
    project_root = os.path.dirname(os.path.dirname(__file__))
    export_path = os.path.join(project_root, "apple_health_export", "export.xml")
    user_id = "your_user"
    ttl_days = 30

    print("🏥 Loading Apple Health data...")
    print(f"📁 Parsing: {export_path}")

    # Parse the health file
    try:
        result = parse_health_file(export_path, user_id)

        if not result.success:
            print(f"❌ Parse failed: {result.message}")
            return False

        health_data = result.data
        print(f"✅ Parsed {health_data['record_count']:,} records")

        # Store in Redis
        print("💾 Storing in Redis...")
        store_result = redis_manager.store_health_data(
            user_id=user_id,
            health_data=health_data,
            ttl_days=ttl_days
        )

        print(f"✅ Stored {store_result['redis_keys_created']} Redis keys")
        print(f"🔑 Main key: {store_result['main_key']}")

        # Show metrics
        print("\n📊 Metrics Summary:")
        metrics = health_data.get('metrics_summary', {})
        for name, info in list(metrics.items())[:10]:
            count = info.get('count', 0)
            if count > 0:
                print(f"  • {name}: {count:,} records")

        print(f"\n✅ Ready! Health data loaded for user: {user_id}")
        return True

    except FileNotFoundError:
        print(f"❌ File not found: {export_path}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
