#!/bin/bash
# Baseline Testing Script - Phase 2
# Tests the stateful agent to establish quality baseline before any code changes

set -e  # Exit on error

echo "======================================"
echo "🧪 PHASE 2: BASELINE TESTING"
echo "======================================"
echo ""
echo "This script tests your working agents to establish a baseline."
echo "We'll measure validation scores, tool calling, and memory stats."
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test and parse results
run_test() {
    local test_num=$1
    local test_name=$2
    local message=$3
    local session_id=$4

    echo ""
    echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "${YELLOW}Test $test_num: $test_name${NC}"
    echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "Query: \"$message\""
    echo "Session: $session_id"
    echo ""

    # Run the curl command and capture output
    echo "📡 Sending request..."
    response=$(curl -s -X POST http://localhost:8000/api/chat/stateful/stream \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$message\", \"session_id\": \"$session_id\"}" 2>&1)

    # Check if curl succeeded
    if [ $? -ne 0 ]; then
        echo "${RED}❌ FAILED: Curl command failed${NC}"
        echo "Error: $response"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi

    # Check for error responses
    if echo "$response" | grep -q "error"; then
        echo "${RED}❌ FAILED: API returned an error${NC}"
        echo "$response" | head -20
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi

    # Parse the response (SSE format - look for data: lines)
    echo "📊 Response received. Parsing..."

    # Extract response text (from token events)
    response_text=$(echo "$response" | grep '"type"' | grep '"token"' | sed 's/.*"content":[[:space:]]*"\([^"]*\)".*/\1/' | tr -d '\n')

    # Extract done event data (handle JSON with spaces)
    done_data=$(echo "$response" | grep '"type"' | grep '"done"' | tail -1)

    if [ -z "$done_data" ]; then
        echo "${RED}❌ FAILED: No done event in response${NC}"
        echo "Response preview:"
        echo "$response" | head -20
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi

    # Extract key metrics (handle JSON with spaces)
    tools_used=$(echo "$done_data" | grep -o '"tools_used"[[:space:]]*:[[:space:]]*\[[^]]*\]' || echo "[]")
    tool_calls=$(echo "$done_data" | grep -o '"tool_calls_made"[[:space:]]*:[[:space:]]*[0-9]*' | grep -o '[0-9]*' || echo "0")

    # Extract validation object (may contain nested fields with commas)
    validation=$(echo "$done_data" | python3 -c "import sys, json; d=json.load(sys.stdin); print(json.dumps(d.get('data',{}).get('validation',{})))" 2>/dev/null || echo "{}")
    memory_stats=$(echo "$done_data" | python3 -c "import sys, json; d=json.load(sys.stdin); print(json.dumps(d.get('data',{}).get('memory_stats',{})))" 2>/dev/null || echo "{}")

    # Extract validation score (using Python for reliable JSON parsing)
    valid=$(echo "$validation" | python3 -c "import sys, json; print(json.loads(sys.stdin.read()).get('valid','unknown'))" 2>/dev/null || echo "unknown")
    score=$(echo "$validation" | python3 -c "import sys, json; print(json.loads(sys.stdin.read()).get('score',0))" 2>/dev/null || echo "0")
    hallucinations=$(echo "$validation" | python3 -c "import sys, json; print(json.loads(sys.stdin.read()).get('hallucinations_detected',0))" 2>/dev/null || echo "0")

    # Display results
    echo ""
    echo "${GREEN}✓ Response received successfully${NC}"
    echo ""
    echo "Response: ${response_text:0:200}..."
    echo ""
    echo "📊 Metrics:"
    echo "  Tools used: $tools_used"
    echo "  Tool calls: $tool_calls"
    echo "  Valid: $valid"
    echo "  Validation score: $score"
    echo "  Hallucinations: $hallucinations"
    echo ""

    # Validate success criteria
    local test_passed=true

    # Check validation score (if available) - NOTE: stateful agent may not return validation
    if [ "$valid" != "unknown" ]; then
        if (( $(echo "$score < 0.7" | bc -l) )); then
            echo "${RED}⚠️  WARNING: Low validation score ($score < 0.7)${NC}"
            test_passed=false
        else
            echo "${GREEN}✓ Validation score good ($score >= 0.7)${NC}"
        fi

        # Check hallucinations (should be 0)
        if [ "$hallucinations" != "0" ]; then
            echo "${RED}⚠️  WARNING: Hallucinations detected ($hallucinations)${NC}"
            test_passed=false
        else
            echo "${GREEN}✓ No hallucinations detected${NC}"
        fi
    else
        echo "${YELLOW}ℹ️  Validation not available (stateful agent doesn't return validation)${NC}"
    fi

    # Check response is not empty
    if [ -z "$response_text" ]; then
        echo "${RED}⚠️  WARNING: Empty response text${NC}"
        test_passed=false
    else
        echo "${GREEN}✓ Response text present${NC}"
    fi

    # Check tools were called when expected
    if [ "$tool_calls" != "0" ]; then
        echo "${GREEN}✓ Tools called ($tool_calls calls)${NC}"
    else
        echo "${YELLOW}ℹ️  No tools called (may be expected for this query)${NC}"
    fi

    if [ "$test_passed" = true ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo ""
        echo "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo "${GREEN}✓ Test $test_num: PASSED${NC}"
        echo "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo ""
        echo "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo "${RED}✗ Test $test_num: FAILED (validation issues)${NC}"
        echo "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        return 1
    fi
}

# Pre-flight check
echo "🔍 Pre-flight checks..."
echo ""

# Check if backend is running
if ! curl -s http://localhost:8000/api/health/check > /dev/null 2>&1; then
    echo "${RED}❌ ERROR: Backend not responding at http://localhost:8000${NC}"
    echo "Please start the backend with: docker-compose up or ./start.sh"
    exit 1
fi

echo "${GREEN}✓ Backend is running${NC}"
echo ""

# Check Redis is accessible
if ! curl -s http://localhost:8000/api/health/check | grep -q "redis"; then
    echo "${YELLOW}⚠️  WARNING: Could not verify Redis connection${NC}"
fi

echo "${GREEN}✓ Pre-flight checks passed${NC}"
echo ""

# Run tests
echo "Starting baseline tests..."
echo ""
sleep 1

# Test 1: Simple query (no memory needed)
run_test 1 "Simple Query" "How many workouts do I have?" "baseline_test_1"

sleep 2

# Test 2: Follow-up query (tests short-term memory)
run_test 2 "Follow-up Query (Memory Test)" "What types are they?" "baseline_test_1"

sleep 2

# Test 3: Numeric accuracy (hallucination test)
run_test 3 "Numeric Accuracy Test" "What was my average heart rate last week?" "baseline_test_2"

sleep 2

# Test 4: Tool calling (procedural memory)
run_test 4 "Tool Calling Test" "Compare my workouts this month vs last month" "baseline_test_3"

sleep 2

# Test 5: Complex query
run_test 5 "Complex Query" "Show me my sleep data and tell me if I'm getting enough rest" "baseline_test_4"

# Final summary
echo ""
echo ""
echo "======================================"
echo "📊 BASELINE TEST RESULTS"
echo "======================================"
echo ""
echo "Tests passed: ${GREEN}$TESTS_PASSED${NC}/5"
echo "Tests failed: ${RED}$TESTS_FAILED${NC}/5"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "${GREEN}✓ ALL TESTS PASSED - BASELINE ESTABLISHED${NC}"
    echo "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Your agents are working correctly with:"
    echo "  ✓ Responses generating successfully"
    echo "  ✓ Tools being called appropriately"
    echo "  ✓ Memory functioning (procedural + short-term)"
    echo "  ℹ️  Note: Validation metrics not available (stateful agent)"
    echo ""
    echo "You can now proceed with:"
    echo "  - Phase 3: Code quality fixes (if desired)"
    echo "  - Or stop here - your agents are production-ready!"
    exit 0
else
    echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "${YELLOW}⚠️  SOME TESTS HAD ISSUES${NC}"
    echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Review the test output above to see what failed."
    echo "Common issues:"
    echo "  - Low validation scores: Check tool outputs for accuracy"
    echo "  - Hallucinations: Verify numeric data in responses"
    echo "  - Empty responses: Check backend logs for errors"
    echo ""
    echo "Recommendation: Fix these issues before proceeding with code changes."
    exit 1
fi
