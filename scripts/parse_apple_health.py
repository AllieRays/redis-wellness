#!/usr/bin/env python3
"""
Parse Apple Health XML export and generate JSON data.

Usage:
    python scripts/parse_apple_health.py

This script:
1. Reads apple_health_export/export.xml
2. Parses all health records and workouts
3. Generates structured JSON output
4. Saves to parsed_health_data.json
"""
import sys
import json
from pathlib import Path

def main():
    # Add backend/src to Python path for imports
    project_root = Path(__file__).parent.parent
    backend_src = project_root / "backend" / "src"
    sys.path.insert(0, str(backend_src))

    try:
        # Import with absolute path to avoid relative import issues
        import importlib.util
        import os

        parser_path = project_root / "backend" / "src" / "parsers" / "apple_health_parser.py"
        spec = importlib.util.spec_from_file_location("apple_health_parser", parser_path)
        parser_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(parser_module)
        AppleHealthParser = parser_module.AppleHealthParser
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're running this from the redis-wellness directory")
        return False

    print("🏥 Parsing Apple Health export...")

    # Initialize parser
    parser = AppleHealthParser()
    xml_path = project_root / "apple_health_export" / "export.xml"

    if not xml_path.exists():
        print(f"❌ Apple Health export not found: {xml_path}")
        print("Please place your export.xml file in apple_health_export/")
        return False

    # Parse the XML
    print(f"📄 Parsing {xml_path}...")
    try:
        health_data = parser.parse_file(str(xml_path))
    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        return False

    print(f"✅ Parsed {len(health_data.records):,} health records")
    print(f"✅ Parsed {len(health_data.workouts):,} workouts")

    # Convert to JSON structure
    print("📦 Converting to JSON structure...")

    # Group records by type
    metrics_records = {}
    metrics_summary = {}

    for record in health_data.records:
        record_type = record.record_type.replace("HKQuantityTypeIdentifier", "")

        if record_type not in metrics_records:
            metrics_records[record_type] = []
            metrics_summary[record_type] = {
                "latest_value": None,
                "unit": record.unit,
                "count": 0,
                "latest_date": None,
            }

        # Add to records
        metrics_records[record_type].append({
            "date": record.start_date.strftime("%Y-%m-%d %H:%M:%S"),
            "value": record.value,
            "unit": record.unit,
            "source": record.source_name,
        })

        # Update summary
        metrics_summary[record_type]["count"] += 1
        if (
            not metrics_summary[record_type]["latest_date"]
            or record.start_date.strftime("%Y-%m-%d") > metrics_summary[record_type]["latest_date"]
        ):
            metrics_summary[record_type]["latest_date"] = record.start_date.strftime("%Y-%m-%d")
            metrics_summary[record_type]["latest_value"] = record.value

    # Process workouts
    workouts = []
    for workout in health_data.workouts:
        workout_dict = {
            "type": workout.workout_activity_type,
            "date": workout.start_date.strftime("%Y-%m-%d"),
            "startDate": workout.start_date.isoformat(),
            "endDate": workout.end_date.isoformat(),
            "duration": workout.duration * 60 if workout.duration else None,  # Convert to seconds
            "duration_minutes": workout.duration,
            "totalDistance": workout.total_distance,
            "totalEnergyBurned": workout.total_energy_burned,
            "calories": workout.total_energy_burned,  # Alias
            "source": workout.source_name,
        }
        workouts.append(workout_dict)

    # Sort workouts by date (most recent first)
    workouts.sort(key=lambda x: x["date"], reverse=True)

    # Create main health data structure
    parsed_data = {
        "user_id": "your_user",
        "record_count": len(health_data.records),
        "export_date": health_data.export_date.isoformat(),
        "data_categories": list(metrics_records.keys()),
        "date_range": {
            "start_date": (
                min((r.start_date for r in health_data.records)).strftime("%Y-%m-%d")
                if health_data.records
                else None
            ),
            "end_date": (
                max((r.start_date for r in health_data.records)).strftime("%Y-%m-%d")
                if health_data.records
                else None
            ),
        },
        "metrics_summary": metrics_summary,
        "metrics_records": metrics_records,
        "workouts": workouts,
        "conversation_context": f"Health data export from {health_data.export_date.strftime('%Y-%m-%d')} with {len(health_data.records)} records and {len(workouts)} workouts.",
    }

    # Save to JSON file
    output_file = project_root / "parsed_health_data.json"
    print(f"💾 Saving to {output_file}...")

    with open(output_file, "w") as f:
        json.dump(parsed_data, f, indent=2)

    print("✅ Health data successfully parsed and saved!")
    print(f"\n📊 Summary:")
    print(f"   • Total records: {len(health_data.records):,}")
    print(f"   • Total workouts: {len(workouts):,}")
    print(f"   • Metric types: {len(metrics_records):,}")
    print(f"   • Date range: {parsed_data['date_range']['start_date']} to {parsed_data['date_range']['end_date']}")
    print(f"   • Saved to: {output_file}")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
