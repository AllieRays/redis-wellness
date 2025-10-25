#!/bin/bash

# Hallucination Detection Test Suite
# Tests agent responses for factual accuracy and hallucination prevention

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_URL="http://localhost:8000/api/chat/stateful/stream"

echo "======================================="
echo "🧪 HALLUCINATION DETECTION TEST SUITE"
echo "======================================="
echo ""

# Test helper function
run_hallucination_test() {
    local test_num=$1
    local test_name=$2
    local query=$3
    local session_id=$4
    local expected_pattern=$5
    local hallucination_pattern=$6

    echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "${YELLOW}Test $test_num: $test_name${NC}"
    echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo "Query: \"$query\""
    echo "Session: $session_id"
    echo ""

    # Send request
    echo "📡 Sending request..."
    response=$(curl -s -X POST "$BACKEND_URL" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$query\", \"session_id\": \"$session_id\"}")

    # Extract done event
    done_data=$(echo "$response" | grep '"type"' | grep '"done"' | tail -1)

    if [ -z "$done_data" ]; then
        echo "${RED}❌ FAILED: No response received${NC}"
        echo "$response"
        echo ""
        return 1
    fi

    # Extract response text
    response_text=$(echo "$done_data" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('data', {}).get('response', ''))
except:
    pass
" 2>/dev/null)

    echo "${GREEN}✓ Response received${NC}"
    echo ""
    echo "Response: ${response_text:0:200}..."
    echo ""

    # Check for expected pattern
    if [ -n "$expected_pattern" ]; then
        if echo "$response_text" | grep -iq "$expected_pattern"; then
            echo "${GREEN}✓ PASS: Found expected pattern '$expected_pattern'${NC}"
        else
            echo "${YELLOW}⚠️  WARNING: Expected pattern '$expected_pattern' not found${NC}"
        fi
    fi

    # Check for hallucination pattern
    if [ -n "$hallucination_pattern" ]; then
        if echo "$response_text" | grep -iq "$hallucination_pattern"; then
            echo "${RED}❌ HALLUCINATION DETECTED: Found pattern '$hallucination_pattern'${NC}"
            echo "${RED}   This suggests the agent is making up data!${NC}"
        else
            echo "${GREEN}✓ PASS: No hallucination pattern detected${NC}"
        fi
    fi

    echo ""
    sleep 2
}

# ============================================
# TEST 1: Missing Data Detection
# ============================================
run_hallucination_test \
    1 \
    "Missing Data - Sleep Quality" \
    "What was my sleep quality score last night?" \
    "hallucination_missing_data" \
    "don't have.*sleep\|no sleep data" \
    "sleep score.*[0-9]"

# ============================================
# TEST 2: Future Data Prediction
# ============================================
run_hallucination_test \
    2 \
    "Future Data Prediction" \
    "How many steps will I take tomorrow?" \
    "hallucination_future" \
    "can't predict\|don't have future\|historical data only" \
    "you will\|you'll take.*[0-9].*steps"

# ============================================
# TEST 3: Non-Existent Metric
# ============================================
run_hallucination_test \
    3 \
    "Non-Existent Metric" \
    "What was my blood pressure during my last run?" \
    "hallucination_wrong_metric" \
    "don't have.*blood pressure\|no blood pressure" \
    "[0-9]{2,3}/[0-9]{2,3}.*mmHg"

# ============================================
# TEST 4: Impossible Date Range
# ============================================
run_hallucination_test \
    4 \
    "Impossible Date Range" \
    "How many workouts did I do in December 2025?" \
    "hallucination_future_date" \
    "future date\|don't have data.*December 2025" \
    "[0-9]+.*workouts.*December 2025"

# ============================================
# TEST 5: Numeric Accuracy (Ground Truth)
# ============================================
echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${YELLOW}Test 5: Numeric Accuracy (Ground Truth)${NC}"
echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "Query: 'How many workouts do I have in October?'"
echo "Session: hallucination_numeric"
echo ""
echo "📡 Sending request..."

response=$(curl -s -X POST "$BACKEND_URL" \
    -H "Content-Type: application/json" \
    -d '{"message": "How many workouts do I have in October?", "session_id": "hallucination_numeric"}')

done_data=$(echo "$response" | grep '"type"' | grep '"done"' | tail -1)
response_text=$(echo "$done_data" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('data', {}).get('response', ''))
except:
    pass
" 2>/dev/null)

echo "${GREEN}✓ Response received${NC}"
echo ""
echo "Response: ${response_text:0:200}..."
echo ""
echo "${YELLOW}📋 MANUAL VERIFICATION REQUIRED:${NC}"
echo "1. Check the actual workout count in your database"
echo "2. Compare to the agent's answer"
echo "3. If numbers don't match = HALLUCINATION"
echo ""

sleep 2

# ============================================
# TEST 6: Contradiction Test
# ============================================
echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo "${YELLOW}Test 6: Contradiction Test${NC}"
echo "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Question 1
echo "Question 1: 'How many calories did I burn this week?'"
response1=$(curl -s -X POST "$BACKEND_URL" \
    -H "Content-Type: application/json" \
    -d '{"message": "How many calories did I burn this week?", "session_id": "hallucination_contradiction"}')

done1=$(echo "$response1" | grep '"type"' | grep '"done"' | tail -1)
text1=$(echo "$done1" | python3 -c "
import sys, json, re
try:
    line = sys.stdin.read().strip()
    if line.startswith('data: '):
        line = line[6:]  # Remove 'data: ' prefix from streaming response
    data = json.loads(line)
    text = data.get('data', {}).get('response', '')
    # Extract numbers
    numbers = re.findall(r'\d+(?:\.\d+)?', text)
    print(f'Response 1: {text[:200]}')
    print(f'Numbers found: {numbers}')
except Exception as e:
    print(f'Parse error: {e}')
" 2>/dev/null)

echo "$text1"
echo ""

sleep 3

# Question 2 (same data, different phrasing)
echo "Question 2: 'What was my total active energy this week?'"
response2=$(curl -s -X POST "$BACKEND_URL" \
    -H "Content-Type: application/json" \
    -d '{"message": "What was my total active energy this week?", "session_id": "hallucination_contradiction"}')

done2=$(echo "$response2" | grep '"type"' | grep '"done"' | tail -1)
text2=$(echo "$done2" | python3 -c "
import sys, json, re
try:
    line = sys.stdin.read().strip()
    if line.startswith('data: '):
        line = line[6:]  # Remove 'data: ' prefix from streaming response
    data = json.loads(line)
    text = data.get('data', {}).get('response', '')
    numbers = re.findall(r'\d+(?:\.\d+)?', text)
    print(f'Response 2: {text[:200]}')
    print(f'Numbers found: {numbers}')
except Exception as e:
    print(f'Parse error: {e}')
" 2>/dev/null)

echo "$text2"
echo ""

# Check for numeric consistency between two questions asking for the same data
nums1=$(echo "$text1" | grep -o "Numbers found: \[.*\]" | grep -o "[0-9]\+")
nums2=$(echo "$text2" | grep -o "Numbers found: \[.*\]" | grep -o "[0-9]\+")

# Check if both responses have numbers
if [ -n "$nums1" ] && [ -n "$nums2" ]; then
    # Both have numbers - check if they're consistent
    if [ "$nums1" != "$nums2" ]; then
        echo "${RED}❌ HALLUCINATION DETECTED: Inconsistent numbers for same question${NC}"
        echo "${RED}   Question 1 numbers: $nums1${NC}"
        echo "${RED}   Question 2 numbers: $nums2${NC}"
    else
        echo "${GREEN}✓ PASS: Consistent numeric responses${NC}"
    fi
elif echo "$text1$text2" | grep -qi "don't have.*data\|no data\|not available"; then
    # Agent claims data doesn't exist
    echo "${YELLOW}⚠️  SKIPPED: Agent reports no calorie/energy data available${NC}"
    echo "${YELLOW}   This likely means test data is not loaded into Redis${NC}"
    echo "${YELLOW}   Run './test_data_validation.sh' first to verify data is loaded${NC}"
else
    # No numbers found but also didn't claim missing data - check for hallucination
    echo "${YELLOW}⚠️  WARNING: No numeric values found in responses${NC}"
    echo "${YELLOW}📋 MANUAL VERIFICATION: Review responses above for hallucinations${NC}"
fi
echo ""

# ============================================
# FINAL SUMMARY
# ============================================
echo "======================================="
echo "📊 HALLUCINATION TEST SUMMARY"
echo "======================================="
echo ""
echo "Tests completed. Review results above."
echo ""
echo "${YELLOW}Manual verification steps:${NC}"
echo "1. Check Test 5 numeric accuracy against your database"
echo "2. Verify Test 6 contradiction check shows consistent numbers"
echo "3. Review any ${RED}❌ HALLUCINATION DETECTED${NC} warnings"
echo ""
echo "🎯 Your agents are hallucination-free if:"
echo "  ✓ They admit when data is missing"
echo "  ✓ They refuse to predict the future"
echo "  ✓ They report accurate numbers from your database"
echo "  ✓ They give consistent answers to the same question"
echo ""
