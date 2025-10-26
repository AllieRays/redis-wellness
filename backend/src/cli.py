"""
CLI commands for Redis Wellness application.

This module provides command-line interfaces for common operations like
importing health data, running diagnostics, etc.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import redis
import requests

# Get Redis connection details from environment
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# Import the import script from the same directory
import_health_data_path = Path(__file__).parent / "import_health_data.py"


def health_check():
    """Comprehensive health check for all services: API, Redis, RedisVL, Ollama."""
    print("=" * 80)
    print("  Redis Wellness - System Health Check")
    print("=" * 80)
    print()

    all_healthy = True

    # 1. Check Redis
    print("1️⃣  Redis")
    print("-" * 80)
    try:
        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        client.ping()
        info = client.info("server")
        version = info.get("redis_version", "unknown")
        print(f"✅ Redis: Running (v{version})")

        # Check memory
        mem_info = client.info("memory")
        used_memory = mem_info.get("used_memory_human", "unknown")
        print(f"   Memory: {used_memory}")
    except Exception as e:
        print("❌ Redis: Not accessible")
        print(f"   Error: {e}")
        print("   Fix: docker compose up -d redis")
        all_healthy = False

    print()

    # 2. Check API Server
    print("2️⃣  API Server (FastAPI)")
    print("-" * 80)
    try:
        response = requests.get("http://localhost:8000/api/health/check", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ API: Running")
            print(f"   Status: {data.get('status', 'unknown')}")
            print("   URL: http://localhost:8000")
            print("   Docs: http://localhost:8000/docs")
        else:
            print(f"❌ API: Unhealthy (status {response.status_code})")
            all_healthy = False
    except requests.exceptions.ConnectionError:
        print("❌ API: Not running")
        print(
            "   Fix: make dev  OR  cd backend && uv run uvicorn src.main:app --reload"
        )
        all_healthy = False
    except Exception as e:
        print(f"❌ API: Error - {e}")
        all_healthy = False

    print()

    # 3. Check RedisVL (vector search capability)
    print("3️⃣  RedisVL (Vector Search)")
    print("-" * 80)
    try:
        import redisvl

        print(f"✅ RedisVL: Installed (v{redisvl.__version__})")

        # Try to connect and check vector search capability
        try:
            from redisvl.redis.connection import RedisConnectionFactory

            conn = RedisConnectionFactory.get_redis_connection(
                f"redis://{REDIS_HOST}:{REDIS_PORT}"
            )
            conn.ping()
            print("   Connection: Active")
        except Exception:
            print("   Connection: Not tested (Redis may not be running)")
    except ImportError:
        print("❌ RedisVL: Not installed")
        print("   Fix: uv add redisvl")
        all_healthy = False
    except Exception as e:
        print(f"⚠️  RedisVL: Installed but not functional - {e}")

    print()

    # 4. Check Ollama
    print("4️⃣  Ollama (LLM Runtime)")
    print("-" * 80)
    try:
        # Check if ollama is running
        response = requests.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            models = response.json().get("models", [])
            print("✅ Ollama: Running")
            print(f"   Models available: {len(models)}")

            # Check for qwen2.5 specifically
            qwen_models = [m for m in models if "qwen" in m.get("name", "").lower()]
            if qwen_models:
                for model in qwen_models[:3]:  # Show first 3
                    name = model.get("name", "unknown")
                    size = model.get("size", 0) / (1024**3)  # Convert to GB
                    print(f"      • {name} ({size:.1f} GB)")
            else:
                print("   ⚠️  No Qwen models found")
                print("      Run: ollama pull qwen2.5:latest")
        else:
            print(f"❌ Ollama: Running but unhealthy (status {response.status_code})")
            all_healthy = False
    except requests.exceptions.ConnectionError:
        print("❌ Ollama: Not running")
        print("   Fix: ollama serve")
        all_healthy = False
    except Exception as e:
        print(f"❌ Ollama: Error - {e}")
        all_healthy = False

    print()

    # 5. Check Frontend (if running)
    print("5️⃣  Frontend (Optional)")
    print("-" * 80)
    try:
        response = requests.get("http://localhost:3000", timeout=2)
        if response.status_code == 200:
            print("✅ Frontend: Running")
            print("   URL: http://localhost:3000")
        else:
            print(f"⚠️  Frontend: Unhealthy (status {response.status_code})")
    except requests.exceptions.ConnectionError:
        print("⚠️  Frontend: Not running (optional)")
        print("   To start: cd frontend && npm run dev")
    except Exception as e:
        print(f"⚠️  Frontend: {e}")

    print()
    print("=" * 80)

    if all_healthy:
        print("✅ SYSTEM HEALTHY - All critical services are running")
    else:
        print("❌ SYSTEM UNHEALTHY - Some services need attention")

    print("=" * 80)
    print()

    return all_healthy


def import_health():
    """Import Apple Health data - CLI entry point."""
    # Re-execute the import script in the correct context
    # This ensures all imports work correctly
    with open(import_health_data_path) as f:
        code = compile(f.read(), str(import_health_data_path), "exec")
        exec(code, {"__name__": "__main__", "__file__": str(import_health_data_path)})


def verify_data(user_id: str = "wellness_user", verbose: bool = False):
    """Verify Redis data is loaded, indexed, and using hash sets."""
    print("=" * 80)
    print("  Redis Wellness - Data Verification")
    print("=" * 80)
    print()

    # Connect to Redis
    print("🔌 Connecting to Redis...")
    try:
        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        client.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("   Run: docker compose up -d redis")
        return False

    print()
    print("-" * 80)
    print("1️⃣  Checking Main Data Blob")
    print("-" * 80)

    # Check main data blob
    main_key = f"health:user:{user_id}:data"
    data_blob = client.get(main_key)

    if not data_blob:
        print(f"❌ No data blob found at {main_key}")
        print("   Run: wellness import")
        return False

    print(f"✅ Found main data blob: {main_key}")

    # Parse and analyze data blob
    try:
        data = json.loads(data_blob)
        record_count = data.get("record_count", 0)
        workouts_in_blob = len(data.get("workouts", []))
        metrics_count = len(data.get("metrics_summary", {}))

        print(f"   📊 Health records: {record_count:,}")
        print(f"   🏃 Workouts in blob: {workouts_in_blob}")
        print(f"   📈 Metric types: {metrics_count}")

        if verbose and workouts_in_blob > 0:
            print("\n   Sample workout types:")
            workout_types: dict[str, int] = {}
            for w in data.get("workouts", [])[:10]:
                wtype = w.get("type_cleaned", w.get("type", "Unknown"))
                workout_types[wtype] = workout_types.get(wtype, 0) + 1
            for wtype, count in list(workout_types.items())[:5]:
                print(f"      • {wtype}: {count}")
    except json.JSONDecodeError as e:
        print(f"⚠️  Warning: Could not parse data blob: {e}")

    print()
    print("-" * 80)
    print("2️⃣  Checking Workout Hash Indexes (O(1) lookups)")
    print("-" * 80)

    # Check workout hash keys
    workout_pattern = f"user:{user_id}:workout:*"
    workout_keys = list(client.scan_iter(match=workout_pattern, count=1000))

    if not workout_keys:
        print(f"❌ No workout hash keys found (pattern: {workout_pattern})")
        print("   Workouts are in the blob but not indexed")
        print("   Run: wellness import  (will create indexes)")
        return False

    print(f"✅ Found {len(workout_keys)} workout hash keys")
    print(f"   Pattern: {workout_pattern}")

    # Sample a few workout hashes to verify structure
    sample_keys = workout_keys[:3]
    print(f"\n   Verifying hash structure (sampling {len(sample_keys)} workouts)...")

    hash_verified = True
    for key in sample_keys:
        key_type = client.type(key)
        if key_type != "hash":
            print(f"   ❌ {key} is type '{key_type}' (expected 'hash')")
            hash_verified = False
        else:
            # Get hash fields
            workout_data = client.hgetall(key)
            required_fields = ["type", "startDate", "duration"]
            missing = [f for f in required_fields if f not in workout_data]

            if missing:
                print(f"   ⚠️  {key} missing fields: {missing}")
            elif verbose:
                workout_type = workout_data.get(
                    "type_cleaned", workout_data.get("type", "Unknown")
                )
                duration = workout_data.get("duration", "?")
                print(f"   ✅ {key.split(':')[-2]} - {workout_type} ({duration}min)")

    if hash_verified:
        print("   ✅ All sampled workouts are using Redis hashes")
    else:
        print("   ❌ Some workouts are not properly indexed as hashes")
        return False

    print()
    print("-" * 80)
    print("3️⃣  Checking Metric Indexes")
    print("-" * 80)

    # Check metric indexes
    metric_pattern = f"health:user:{user_id}:metric:*"
    metric_keys = list(client.scan_iter(match=metric_pattern, count=100))

    if metric_keys:
        print(f"✅ Found {len(metric_keys)} metric indexes")
        if verbose:
            for key in metric_keys[:5]:
                metric_type = key.split(":")[-1]
                print(f"      • {metric_type}")
    else:
        print(f"⚠️  No metric indexes found (pattern: {metric_pattern})")
        print("   This is OK if you have no health metrics in your data")

    print()
    print("-" * 80)
    print("4️⃣  Redis Memory & Performance Stats")
    print("-" * 80)

    # Redis stats
    info = client.info("memory")
    used_memory = info.get("used_memory_human", "unknown")
    total_keys = client.dbsize()

    print(f"   💾 Memory used: {used_memory}")
    print(f"   🔑 Total keys: {total_keys:,}")
    print(f"   📦 Workouts indexed: {len(workout_keys):,}")

    # Calculate indexing percentage
    if workouts_in_blob > 0:
        index_pct = (len(workout_keys) / workouts_in_blob) * 100
        print(
            f"   📊 Indexing: {index_pct:.1f}% ({len(workout_keys)}/{workouts_in_blob})"
        )

        if index_pct < 100:
            print(f"   ⚠️  Only {index_pct:.1f}% of workouts are indexed")
            print("      Run: wellness import  (to reindex)")

    print()
    print("=" * 80)
    print("✅ VERIFICATION COMPLETE")
    print("=" * 80)
    print()
    print("Summary:")
    print(f"  • Main data blob: ✅ Present ({record_count:,} records)")
    print(f"  • Workout indexes: ✅ {len(workout_keys)} hash sets")
    print(
        f"  • Metric indexes: {'✅' if metric_keys else '⚠️ '} {len(metric_keys)} indices"
    )
    print(f"  • Redis memory: {used_memory}")
    print()

    return True


def show_stats(user_id: str = "wellness_user", verbose: bool = False):
    """Show statistics about health data types and availability."""
    print("=" * 80)
    print("  Redis Wellness - Health Data Statistics")
    print("=" * 80)
    print()

    # Connect to Redis
    print("🔌 Connecting to Redis...")
    try:
        client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        client.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("   Run: docker compose up -d redis")
        return False

    print()
    print("-" * 80)
    print("1️⃣  Loading Health Data")
    print("-" * 80)

    # Load main data blob
    main_key = f"health:user:{user_id}:data"
    data_blob = client.get(main_key)

    if not data_blob:
        print(f"❌ No data found at {main_key}")
        print("   Run: wellness import")
        return False

    try:
        data = json.loads(data_blob)
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse data: {e}")
        return False

    record_count = data.get("record_count", 0)
    export_date = data.get("export_date", "unknown")

    print(f"✅ Loaded health data for {user_id}")
    print(f"   Total records: {record_count:,}")
    print(f"   Export date: {export_date}")

    print()
    print("-" * 80)
    print("2️⃣  Health Metrics Summary")
    print("-" * 80)

    metrics_summary = data.get("metrics_summary", {})

    if not metrics_summary:
        print("⚠️  No metric summaries found")
    else:
        print(f"✅ Found {len(metrics_summary)} metric types\n")

        # Sort by count (most common first)
        sorted_metrics = sorted(
            metrics_summary.items(), key=lambda x: x[1].get("count", 0), reverse=True
        )

        # Show top metrics
        display_limit = len(sorted_metrics) if verbose else min(10, len(sorted_metrics))

        for metric_type, summary in sorted_metrics[:display_limit]:
            count = summary.get("count", 0)
            unit = summary.get("unit", "")
            latest_value = summary.get("latest_value", "")
            latest_date = summary.get("latest_date", "")

            # Format latest date
            if latest_date:
                try:
                    dt = datetime.fromisoformat(latest_date.replace("Z", "+00:00"))
                    latest_date_str = dt.strftime("%Y-%m-%d")
                except Exception:
                    latest_date_str = latest_date[:10]
            else:
                latest_date_str = "N/A"

            print(f"   📊 {metric_type}")
            print(f"      Records: {count:,}")
            if latest_value and unit:
                print(f"      Latest: {latest_value} {unit} ({latest_date_str})")
            print()

        if not verbose and len(sorted_metrics) > 10:
            remaining = len(sorted_metrics) - 10
            print(f"   ... and {remaining} more metric types")
            print("   Run with --verbose to see all metrics\n")

    print("-" * 80)
    print("3️⃣  Workout Types Summary")
    print("-" * 80)

    workouts = data.get("workouts", [])

    if not workouts:
        print("⚠️  No workouts found")
    else:
        print(f"✅ Found {len(workouts)} total workouts\n")

        # Count workout types
        workout_types: dict[str, int] = {}
        total_duration = 0
        total_calories = 0
        date_range = {"min": None, "max": None}

        for workout in workouts:
            wtype = workout.get("type_cleaned", workout.get("type", "Unknown"))
            workout_types[wtype] = workout_types.get(wtype, 0) + 1

            # Aggregate stats
            duration = workout.get("duration", 0)
            calories = workout.get("calories", 0) or workout.get("totalEnergyBurned", 0)

            if duration:
                total_duration += duration
            if calories:
                total_calories += calories

            # Track date range
            start_date = workout.get("startDate", "")
            if start_date:
                try:
                    dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    if date_range["min"] is None or dt < date_range["min"]:
                        date_range["min"] = dt
                    if date_range["max"] is None or dt > date_range["max"]:
                        date_range["max"] = dt
                except Exception:
                    pass

        # Sort by count
        sorted_types = sorted(workout_types.items(), key=lambda x: x[1], reverse=True)

        # Show workout types
        display_limit = len(sorted_types) if verbose else min(10, len(sorted_types))

        for wtype, count in sorted_types[:display_limit]:
            percentage = (count / len(workouts)) * 100
            print(f"   🏃 {wtype}: {count} workouts ({percentage:.1f}%)")

        if not verbose and len(sorted_types) > 10:
            remaining = len(sorted_types) - 10
            print(f"   ... and {remaining} more workout types")
            print("   Run with --verbose to see all types")

        # Show aggregate stats
        print()
        print("   Aggregate Statistics:")
        print(f"      Total workouts: {len(workouts):,}")
        if total_duration > 0:
            hours = total_duration / 3600
            print(f"      Total duration: {hours:.1f} hours")
        if total_calories > 0:
            print(f"      Total calories: {total_calories:,.0f} kcal")
        if date_range["min"] and date_range["max"]:
            days = (date_range["max"] - date_range["min"]).days
            print(
                f"      Date range: {date_range['min'].strftime('%Y-%m-%d')} to {date_range['max'].strftime('%Y-%m-%d')} ({days} days)"
            )

    print()
    print("-" * 80)
    print("4️⃣  Storage Statistics")
    print("-" * 80)

    # Redis memory stats
    info = client.info("memory")
    used_memory = info.get("used_memory_human", "unknown")
    total_keys = client.dbsize()

    print(f"   💾 Redis memory: {used_memory}")
    print(f"   🔑 Total keys: {total_keys:,}")

    # Count workout indexes
    workout_pattern = f"user:{user_id}:workout:*"
    workout_keys = list(client.scan_iter(match=workout_pattern, count=1000))
    print(f"   📦 Workout indexes: {len(workout_keys):,}")

    print()
    print("=" * 80)
    print("✅ STATISTICS COMPLETE")
    print("=" * 80)
    print()

    return True


def main():
    """Main CLI entry point with subcommands."""
    parser = argparse.ArgumentParser(
        description="Redis Wellness CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  wellness health                          # Check all services (Redis, API, Ollama, etc.)
  wellness import                          # Import health data (auto-detect)
  wellness import export.xml               # Import from specific XML file
  wellness verify                          # Verify data is loaded and indexed
  wellness verify --verbose                # Verbose verification with samples
  wellness stats                           # Show health data statistics
  wellness stats --verbose                 # Show all metric and workout types
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Health check command
    subparsers.add_parser(
        "health", help="Check all services (Redis, API, Ollama, RedisVL)"
    )

    # Import command
    import_parser = subparsers.add_parser("import", help="Import Apple Health data")
    import_parser.add_argument(
        "file", nargs="?", help="Path to export.xml or parsed JSON file"
    )
    import_parser.add_argument(
        "--user-id", default="wellness_user", help="User ID (default: wellness_user)"
    )

    # Verify command
    verify_parser = subparsers.add_parser(
        "verify", help="Verify Redis data is loaded and indexed"
    )
    verify_parser.add_argument(
        "--user-id", default="wellness_user", help="User ID (default: wellness_user)"
    )
    verify_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed information"
    )

    # Stats command
    stats_parser = subparsers.add_parser(
        "stats", help="Show health data statistics and types"
    )
    stats_parser.add_argument(
        "--user-id", default="wellness_user", help="User ID (default: wellness_user)"
    )
    stats_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show all metric and workout types"
    )

    args = parser.parse_args()

    if args.command == "health":
        success = health_check()
        sys.exit(0 if success else 1)
    elif args.command == "import":
        # Set sys.argv for the import script
        sys.argv = ["import_health_data.py"]
        if args.file:
            sys.argv.append(args.file)
        if args.user_id != "wellness_user":
            sys.argv.extend(["--user-id", args.user_id])

        import_health()
    elif args.command == "verify":
        success = verify_data(user_id=args.user_id, verbose=args.verbose)
        sys.exit(0 if success else 1)
    elif args.command == "stats":
        success = show_stats(user_id=args.user_id, verbose=args.verbose)
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
