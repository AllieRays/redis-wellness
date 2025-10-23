#!/usr/bin/env python3
"""
Quick reload of health data from parsed_health_data.json into Redis.

Usage:
    python3 reload_health_data.py
"""
import json
import redis
from datetime import datetime

print("🔄 Reloading health data into Redis...")

# Load parsed data
with open('parsed_health_data.json') as f:
    data = json.load(f)

# Enrich workout data with all computed fields
print("📝 Enriching workout data...")
for workout in data.get('workouts', []):
    # Add day_of_week and date
    start_date_str = workout.get('startDate', '')
    if start_date_str:
        try:
            dt = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            workout['day_of_week'] = dt.strftime('%A')  # Monday, Tuesday, etc.
            workout['date'] = dt.strftime('%Y-%m-%d')  # Date only
        except:
            pass

    # Clean up type (remove HKWorkoutActivityType prefix if present)
    workout_type = workout.get('type', '')
    if workout_type.startswith('HKWorkoutActivityType'):
        workout['type_cleaned'] = workout_type.replace('HKWorkoutActivityType', '')
    else:
        workout['type_cleaned'] = workout_type

    # Standardize energy field name
    if 'totalEnergyBurned' in workout and 'calories' not in workout:
        workout['calories'] = workout['totalEnergyBurned']

    # Fix duration_minutes if it's wrong (should be duration/60, not rounded seconds)
    if workout.get('duration') and workout.get('duration_minutes'):
        # Check if it looks like rounded seconds instead of minutes
        if workout['duration_minutes'] > workout['duration'] / 10:  # Heuristic: if minutes > duration/10, it's wrong
            workout['duration_minutes'] = round(workout['duration'] / 60, 1)

# Connect to Redis
client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)
client.ping()

# Store in Redis
main_key = 'health:user:wellness_user:data'
client.set(main_key, json.dumps(data))

print(f'✅ Loaded {len(data.get("workouts", []))} workouts')
print(f'✅ Loaded {len(data.get("metrics_records", {}))} metric types')
print(f'✅ Stored at key: {main_key}')
