#!/usr/bin/env python3
"""Check workout data in Redis."""
import redis
import json
from datetime import datetime, timezone

r = redis.Redis(host='localhost', port=6379, decode_responses=True)
data_str = r.get('health:user:wellness_user:data')

if not data_str:
    print("❌ No health data found in Redis")
    exit(1)

data = json.loads(data_str)
workouts = data.get('workouts', [])

print(f"📊 Total workouts in Redis: {len(workouts)}")

if workouts:
    # Get most recent workouts
    recent = sorted(workouts, key=lambda w: w.get('startDate', ''), reverse=True)[:5]

    print(f"\n🏃 Most recent 5 workouts:")
    for i, w in enumerate(recent, 1):
        date = w.get('startDate', 'NO DATE')
        workout_type = w.get('type', 'unknown').replace('HKWorkoutActivityType', '')
        duration = w.get('duration_minutes', w.get('duration', 0) / 60)
        print(f"  {i}. {date}: {workout_type} ({duration:.1f} min)")

    # Check if any are recent (last 30 days)
    now = datetime.now(timezone.utc)
    cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0).replace(day=now.day-30)

    recent_count = 0
    for w in workouts:
        try:
            w_date = datetime.fromisoformat(w.get('startDate', '').replace('Z', '+00:00'))
            if w_date >= cutoff:
                recent_count += 1
        except:
            pass

    print(f"\n✅ Workouts in last 30 days: {recent_count}")
    print(f"📅 Today (UTC): {now.date()}")
else:
    print("❌ No workouts found in data")
