#!/usr/bin/env python3
"""
Direct test of health parsing without import issues.
"""

import os
import xml.etree.ElementTree as ET


# Test if we can access the health file first
def test_file_access():
    """Test if we can access the Apple Health export file."""
    print("🔍 Testing file access...")

    file_path = "../apple_health_export/export.xml"

    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        print("📂 Current directory contents:")
        print(os.listdir(".."))
        return False

    print(f"✅ File found: {file_path}")
    print(f"📏 File size: {os.path.getsize(file_path)} bytes")

    # Try to read first few lines
    try:
        with open(file_path, encoding="utf-8") as f:
            first_lines = [f.readline().strip() for _ in range(5)]

        print("📄 First 5 lines:")
        for i, line in enumerate(first_lines, 1):
            print(f"  {i}: {line[:100]}...")

        return True
    except Exception as e:
        print(f"❌ Error reading file: {str(e)}")
        return False


def test_xml_parsing():
    """Test basic XML parsing of the health file."""
    print("\n🔍 Testing XML parsing...")

    file_path = "../apple_health_export/export.xml"

    try:
        # Parse XML iteratively (memory efficient)
        print("📊 Analyzing XML structure...")

        record_count = 0
        export_date = None
        record_types = {}

        # Parse with iterparse for large files
        context = ET.iterparse(file_path, events=("start", "end"))
        context = iter(context)

        # Get root
        event, root = next(context)
        print(f"📁 Root element: {root.tag}")

        for event, elem in context:
            if event == "end":
                if elem.tag == "ExportDate":
                    export_date = elem.get("value")
                elif elem.tag == "Record":
                    record_count += 1
                    record_type = elem.get("type", "Unknown")

                    # Track record types
                    if record_type not in record_types:
                        record_types[record_type] = 0
                    record_types[record_type] += 1

                    # Show progress
                    if record_count % 1000 == 0:
                        print(f"  📈 Processed {record_count} records...")

                # Clear element to save memory
                elem.clear()

        # Clear root
        root.clear()

        print("✅ Successfully parsed XML!")
        print(f"📅 Export date: {export_date}")
        print(f"📊 Total records: {record_count}")
        print(f"🏷️ Record types found: {len(record_types)}")

        # Show top record types
        print("\n🔝 Top 10 Record Types:")
        sorted_types = sorted(record_types.items(), key=lambda x: x[1], reverse=True)
        for record_type, count in sorted_types[:10]:
            clean_type = record_type.replace("HKQuantityTypeIdentifier", "")
            print(f"  • {clean_type}: {count} records")

        return {
            "record_count": record_count,
            "export_date": export_date,
            "record_types": record_types,
        }

    except Exception as e:
        print(f"❌ XML parsing failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def test_specific_records():
    """Extract specific health records we care about."""
    print("\n🔍 Testing specific record extraction...")

    file_path = "../apple_health_export/export.xml"

    try:
        target_types = [
            "HKQuantityTypeIdentifierBodyMassIndex",
            "HKQuantityTypeIdentifierDietaryWater",
            "HKQuantityTypeIdentifierStepCount",
            "HKQuantityTypeIdentifierBodyMass",
        ]

        found_records = {t: [] for t in target_types}

        context = ET.iterparse(file_path, events=("start", "end"))
        context = iter(context)

        # Get root
        event, root = next(context)

        for event, elem in context:
            if event == "end" and elem.tag == "Record":
                record_type = elem.get("type")

                if record_type in target_types:
                    record_data = {
                        "type": record_type,
                        "value": elem.get("value"),
                        "unit": elem.get("unit"),
                        "start_date": elem.get("startDate"),
                        "end_date": elem.get("endDate"),
                        "source": elem.get("sourceName"),
                    }
                    found_records[record_type].append(record_data)

                    # Only keep recent ones to avoid memory issues
                    if len(found_records[record_type]) > 10:
                        found_records[record_type] = found_records[record_type][-10:]

                elem.clear()

        root.clear()

        print("✅ Extracted specific records:")
        for record_type, records in found_records.items():
            clean_type = record_type.replace("HKQuantityTypeIdentifier", "")
            print(f"\n📊 {clean_type}: {len(records)} recent records")

            if records:
                # Show latest record
                latest = records[-1]
                print(
                    f"  Latest: {latest['value']} {latest['unit']} on {latest['start_date']}"
                )
                print(f"  Source: {latest['source']}")

        return found_records

    except Exception as e:
        print(f"❌ Record extraction failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def main():
    """Run all tests."""
    print("🚀 Direct Health Data Parsing Test")
    print("=" * 50)

    # Test 1: File access
    if not test_file_access():
        print("❌ Cannot access health file - stopping")
        return

    # Test 2: XML structure
    xml_info = test_xml_parsing()
    if not xml_info:
        print("❌ XML parsing failed - stopping")
        return

    # Test 3: Specific records
    records = test_specific_records()
    if not records:
        print("❌ Record extraction failed")
        return

    print("\n✨ All tests completed successfully!")
    print(f"📊 Found {xml_info['record_count']} total health records")
    print("🎯 Ready to integrate with Redis and LangGraph!")


if __name__ == "__main__":
    main()
