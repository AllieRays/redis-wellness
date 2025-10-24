#!/bin/bash
#
# Clear Redis Conversations Script
#
# This script clears conversation history and memory from Redis
# while preserving health data.
#
# Usage:
#   ./clear_conversations.sh

set -e  # Exit on error

echo "🧹 Clearing conversation cache..."
echo ""

# Check if Redis container is running
if ! docker ps | grep -q redis-wellness; then
    echo "❌ Error: Redis container 'redis-wellness' is not running"
    echo "   Start it with: docker-compose up -d"
    exit 1
fi

# Count conversations before clearing
CONV_COUNT=$(docker exec redis-wellness redis-cli --scan --pattern "conversation:*" 2>/dev/null | wc -l | tr -d ' ')
MEM_COUNT=$(docker exec redis-wellness redis-cli --scan --pattern "memory:*" 2>/dev/null | wc -l | tr -d ' ')

echo "Found:"
echo "  • ${CONV_COUNT} conversation keys"
echo "  • ${MEM_COUNT} memory keys"
echo ""

# Clear conversation keys
echo "Clearing conversation:* keys..."
docker exec redis-wellness redis-cli --scan --pattern "conversation:*" | \
    xargs -I {} docker exec redis-wellness redis-cli DEL {} >/dev/null 2>&1 || true

# Clear memory keys
echo "Clearing memory:* keys..."
docker exec redis-wellness redis-cli --scan --pattern "memory:*" | \
    xargs -I {} docker exec redis-wellness redis-cli DEL {} >/dev/null 2>&1 || true

echo ""
echo "✅ Conversation cache cleared!"
echo ""
echo "Health data preserved ✓"
echo "Ready for fresh conversations"
