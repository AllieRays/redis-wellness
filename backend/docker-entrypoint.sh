#!/bin/bash
set -e

echo "=================================================="
echo "  Redis Wellness Backend - Startup"
echo "=================================================="

# Wait for Redis to be ready (using Python)
echo "⏳ Waiting for Redis..."
until uv run python -c "import redis; redis.Redis(host='redis', port=6379).ping()" 2>/dev/null; do
  echo "   Redis not ready yet, waiting..."
  sleep 2
done
echo "✅ Redis is ready"

# Run startup health check (auto-import data if needed)
echo ""
echo "🔍 Running startup health check..."
cd /app/scripts
uv run python startup_health_check.py
echo ""

# Start the application
echo "🚀 Starting FastAPI application..."
echo "=================================================="
cd /app
exec "$@"
