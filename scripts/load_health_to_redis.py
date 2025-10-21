#!/usr/bin/env python3
"""
Load parsed health data from JSON into Redis.

Usage:
    python scripts/load_health_to_redis.py
    
This script:
1. Reads parsed_health_data.json
2. Connects to Redis (localhost:6379)
3. Stores data with proper keys for the chat system
4. Sets 7-month TTL on all data
"""
import sys
import json
from pathlib import Path

def main():
    project_root = Path(__file__).parent.parent
    
    print("🔌 Loading parsed health data into Redis...")
    
    # Import Redis
    try:
        import redis
    except ImportError:
        print("❌ Redis package not installed. Run: pip install redis")
        return False
    
    # Connect to Redis
    try:
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
        print("✅ Connected to Redis")
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        print("Make sure Redis is running: docker-compose up redis")
        return False
    
    # Load the parsed JSON file
    json_file = project_root / "parsed_health_data.json"
    if not json_file.exists():
        print(f"❌ Parsed health data not found: {json_file}")
        print("Run 'python scripts/parse_apple_health.py' first")
        return False
    
    try:
        with open(json_file, "r") as f:
            health_data = json.load(f)
        print(f"✅ Loaded JSON file with {health_data['record_count']:,} records")
    except Exception as e:
        print(f"❌ Failed to load {json_file}: {e}")
        return False
    
    # Store in Redis with the keys the chat system expects
    user_id = health_data.get("user_id", "your_user")
    
    try:
        # Main health data key
        main_key = f"health:user:{user_id}:data"
        r.set(main_key, json.dumps(health_data))
        print(f"✅ Stored main health data at {main_key}")
        
        # Context key for conversation
        context_key = f"health:user:{user_id}:context"
        context = health_data.get("conversation_context", "Health data available")
        r.set(context_key, context)
        print(f"✅ Stored conversation context at {context_key}")
        
        # Set TTL (Time To Live) for data - 7 months as per project standard
        ttl_seconds = 7 * 30 * 24 * 60 * 60  # 7 months in seconds
        r.expire(main_key, ttl_seconds)
        r.expire(context_key, ttl_seconds)
        print(f"✅ Set TTL to 7 months for health data")
        
        # Store individual metric summaries for quick access
        metrics_summary = health_data.get("metrics_summary", {})
        for metric_type, data in metrics_summary.items():
            key = f"health:user:{user_id}:metric:{metric_type}"
            r.set(key, json.dumps(data))
            r.expire(key, ttl_seconds)
        print(f"✅ Stored {len(metrics_summary)} metric summaries")
        
        # Store a few sample workouts for compatibility
        workouts = health_data.get("workouts", [])
        for i, workout in enumerate(workouts[:10]):  # Store first 10 workouts
            key = f"health:user:{user_id}:workout:{i}"
            r.set(key, json.dumps(workout))
            r.expire(key, ttl_seconds)
        print(f"✅ Stored {min(10, len(workouts))} sample workout records")
        
        print(f"\n🎉 SUCCESS! Health data loaded for user: {user_id}")
        print(f"📊 Summary:")
        print(f"   • Records: {health_data['record_count']:,}")
        print(f"   • Workouts: {len(workouts):,}")
        print(f"   • Metrics: {len(metrics_summary):,}")
        print(f"   • Date range: {health_data['date_range']['start_date']} to {health_data['date_range']['end_date']}")
        print(f"\n💬 Ready for chat queries!")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to store in Redis: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)