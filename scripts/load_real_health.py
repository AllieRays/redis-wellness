#!/usr/bin/env python3
"""
Load real Apple Health data into Redis.
Parses last 90 days of data.
"""
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import json
import redis
from collections import defaultdict

print("🏥 Loading Real Apple Health Data...")
print("=" * 60)

# Connect to Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Parse XML
print("📄 Parsing export.xml...")
tree = ET.parse('apple_health_export/export.xml')
root = tree.getroot()

# Get all records
all_records = root.findall('.//Record')
print(f"📊 Total records in file: {len(all_records):,}")

# Date cutoff (90 days ago)
cutoff_date = datetime.now() - timedelta(days=90)
print(f"📅 Loading data from: {cutoff_date.strftime('%Y-%m-%d')} to today")

# Collect metrics
metrics_data = defaultdict(list)
date_range = {'earliest': None, 'latest': None}

for i, record in enumerate(all_records):
    if i % 10000 == 0 and i > 0:
        print(f"   Processed {i:,} records...")

    start_date_str = record.get('startDate', '')
    if not start_date_str:
        continue

    try:
        # Parse date: "2020-12-08 00:15:06 -0700"
        start_date = datetime.strptime(start_date_str[:19], '%Y-%m-%d %H:%M:%S')

        # Skip old records
        if start_date < cutoff_date:
            continue

        record_type = record.get('type', '').replace('HKQuantityTypeIdentifier', '')
        value = record.get('value')
        unit = record.get('unit')

        if not record_type or not value:
            continue

        # Track date range
        if date_range['earliest'] is None or start_date < date_range['earliest']:
            date_range['earliest'] = start_date
        if date_range['latest'] is None or start_date > date_range['latest']:
            date_range['latest'] = start_date

        # Store metric data
        metrics_data[record_type].append({
            'value': value,
            'unit': unit,
            'date': start_date
        })

    except Exception as e:
        continue

print(f"✅ Found {sum(len(v) for v in metrics_data.values()):,} recent records")
print(f"📋 Unique metrics: {len(metrics_data)}")

# Create metrics summary AND store recent records for key metrics
metrics_summary = {}
metrics_records = {}  # Store actual data points for key metrics

# Key metrics we want to store full records for
KEY_METRICS = ['BodyMass', 'BodyMassIndex', 'HeartRate', 'StepCount', 'ActiveEnergyBurned']

for metric_type, data_points in metrics_data.items():
    if not data_points:
        continue

    # Sort by date
    data_points.sort(key=lambda x: x['date'])
    latest = data_points[-1]

    metrics_summary[metric_type] = {
        'count': len(data_points),
        'latest_value': latest['value'],
        'unit': latest['unit'],
        'latest_date': latest['date'].strftime('%Y-%m-%d')
    }

    # Store full records for key metrics (for historical queries)
    if metric_type in KEY_METRICS:
        metrics_records[metric_type] = [
            {
                'value': dp['value'],
                'unit': dp['unit'],
                'date': dp['date'].strftime('%Y-%m-%d %H:%M:%S')
            }
            for dp in data_points
        ]

# Parse workouts
print("\n🏃 Parsing workouts...")
workouts = []
workout_elements = root.findall('.//Workout')

for workout in workout_elements:
    start_date_str = workout.get('startDate', '')
    if not start_date_str:
        continue

    try:
        start_date = datetime.strptime(start_date_str[:19], '%Y-%m-%d %H:%M:%S')
        if start_date < cutoff_date:
            continue

        end_date_str = workout.get('endDate', '')
        end_date = datetime.strptime(end_date_str[:19], '%Y-%m-%d %H:%M:%S') if end_date_str else None

        workouts.append({
            'type': workout.get('workoutActivityType', ''),
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat() if end_date else '',
            'duration': float(workout.get('duration', 0)),
            'totalDistance': float(workout.get('totalDistance', 0)) if workout.get('totalDistance') else 0,
            'totalEnergyBurned': float(workout.get('totalEnergyBurned', 0)) if workout.get('totalEnergyBurned') else 0
        })
    except Exception as e:
        continue

workouts.sort(key=lambda x: x['startDate'])
print(f"✅ Found {len(workouts)} recent workouts")

# Build health data structure
user_id = "your_user"
health_data = {
    "user_id": user_id,
    "record_count": sum(len(v) for v in metrics_data.values()),
    "export_date": datetime.now().isoformat(),
    "data_categories": list(metrics_summary.keys()),
    "date_range": {
        "start_date": date_range['earliest'].strftime("%Y-%m-%d") if date_range['earliest'] else "",
        "end_date": date_range['latest'].strftime("%Y-%m-%d") if date_range['latest'] else "",
        "span_days": (date_range['latest'] - date_range['earliest']).days if date_range['earliest'] and date_range['latest'] else 0
    },
    "metrics_summary": metrics_summary,
    "metrics_records": metrics_records,  # Historical data for key metrics
    "workouts": workouts
}

# Store in Redis
print("\n💾 Storing in Redis...")
main_key = f"health:user:{user_id}:data"
r.set(main_key, json.dumps(health_data))
print(f"✅ Stored: {main_key}")

# Force immediate persistence to disk
print("💾 Forcing Redis SAVE to ensure persistence...")
r.save()
print("✅ Data persisted to disk")

# Print summary
print("\n" + "=" * 60)
print("📊 HEALTH DATA SUMMARY")
print("=" * 60)
print(f"Total records: {health_data['record_count']:,}")
print(f"Date range: {health_data['date_range']['start_date']} to {health_data['date_range']['end_date']}")
print(f"Span: {health_data['date_range']['span_days']} days")
print(f"Workouts: {len(workouts)}")

print("\n📊 Top 15 Metrics:")
sorted_metrics = sorted(metrics_summary.items(), key=lambda x: x[1]['count'], reverse=True)[:15]
for metric, data in sorted_metrics:
    latest_val = str(data['latest_value']) if data['latest_value'] is not None else 'N/A'
    unit = data.get('unit', '') or ''
    print(f"   • {metric:30s}: {data['count']:5,} records | Latest: {latest_val:10s} {unit:5s} ({data['latest_date']})")

print("\n✅ Real Apple Health data loaded successfully!")
