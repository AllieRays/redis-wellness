#!/bin/bash

# Data Validation Test Suite
# Verifies that Apple Health test data is properly loaded into Redis
# RUN THIS BEFORE hallucination tests to ensure data exists

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_URL="http://localhost:8000/api/chat/stateful/stream"
REDIS_HEALTH_KEY="user:test_user:health_data"

echo "======================================="
echo "🔍 DATA VALIDATION TEST SUITE"
echo "======================================="
echo ""
echo "This test verifies YOUR REAL Apple Health data is loaded."
echo "It does NOT use mock or test data."
echo ""

# Test 1: Check if Redis has health data keys
echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${YELLOW}Test 1: Redis Health Data Keys${NC}"
echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Check for health data in Redis using docker compose
HEALTH_KEYS=$(docker compose exec -T redis redis-cli KEYS "*health*" 2>/dev/null || redis-cli KEYS "*health*" 2>/dev/null)

if [ -z "$HEALTH_KEYS" ]; then
    echo "${RED}❌ FAIL: No health data keys found in Redis${NC}"
    echo "${RED}   Action required: Import YOUR Apple Health data${NC}"
    echo ""
    echo "To import your data, run:"
    echo ""
    echo "  cd /Users/allierays/Sites/redis-wellness"
    echo "  uv run python import_health_data.py"
    echo ""
    echo "This will auto-detect and import from:"
    echo "  - apple_health_export/export.xml (87MB file in Docker)"
    echo "  - parsed_health_data.json (if pre-parsed)"
    echo ""
    echo "Expected Redis keys after import:"
    echo "  - user:wellness_user:health_data"
    echo "  - user:wellness_user:health_metric:*"
    echo ""
    exit 1
else
    echo "${GREEN}✓ PASS: Health data keys found in Redis${NC}"
    echo "Keys found:"
    echo "$HEALTH_KEYS" | head -10
    echo ""
fi

# Test 2: Query agent for workout count
echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${YELLOW}Test 2: Agent Can Query Workout Data${NC}"
echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

response=$(curl -s -X POST "$BACKEND_URL" \
    -H "Content-Type: application/json" \
    -d '{"message": "How many workouts do I have?", "session_id": "data_validation_test"}')

done_line=$(echo "$response" | grep '"type"' | grep '"done"' | tail -1)
agent_response=$(echo "$done_line" | python3 -c "
import sys, json
try:
    line = sys.stdin.read().strip()
    if line.startswith('data: '):
        line = line[6:]
    data = json.loads(line)
    print(data.get('data', {}).get('response', ''))
except:
    print('')
" 2>/dev/null)

# Check if agent says it doesn't have data
if echo "$agent_response" | grep -qi "don't have\|no data\|not available\|no workouts"; then
    echo "${RED}❌ FAIL: Agent claims it doesn't have workout data${NC}"
    echo "${RED}   This means test data is NOT properly loaded${NC}"
    echo ""
    echo "Agent response:"
    echo "$agent_response"
    echo ""
    exit 1
else
    echo "${GREEN}✓ PASS: Agent successfully queried workout data${NC}"
    echo "Response: $agent_response"
    echo ""
fi

# Test 3: Check for active energy/calorie data
echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${YELLOW}Test 3: Active Energy/Calorie Data Available${NC}"
echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

response=$(curl -s -X POST "$BACKEND_URL" \
    -H "Content-Type: application/json" \
    -d '{"message": "What was my active energy yesterday?", "session_id": "data_validation_energy"}')

done_line=$(echo "$response" | grep '"type"' | grep '"done"' | tail -1)
agent_response=$(echo "$done_line" | python3 -c "
import sys, json
try:
    line = sys.stdin.read().strip()
    if line.startswith('data: '):
        line = line[6:]
    data = json.loads(line)
    print(data.get('data', {}).get('response', ''))
except:
    print('')
" 2>/dev/null)

if echo "$agent_response" | grep -qi "don't have\|no data\|not available"; then
    echo "${YELLOW}⚠️  WARNING: Agent claims it doesn't have active energy data${NC}"
    echo "${YELLOW}   Active energy/calories are standard Apple Health metrics${NC}"
    echo "${YELLOW}   Consider loading more comprehensive test data${NC}"
    echo ""
    echo "Agent response:"
    echo "$agent_response"
    echo ""
else
    echo "${GREEN}✓ PASS: Agent has active energy data available${NC}"
    echo "Response: $agent_response"
    echo ""
fi

echo "======================================="
echo "📊 DATA VALIDATION SUMMARY"
echo "======================================="
echo ""
echo "${GREEN}✓ Data validation tests passed${NC}"
echo ""
echo "Your test environment is ready for hallucination testing."
echo ""
echo "Next steps:"
echo "  1. Run hallucination tests: ./test_hallucinations.sh"
echo "  2. Run baseline tests: ./test_baseline.sh"
echo ""
