# End-to-End (E2E) Tests

End-to-end tests that verify the entire agent system working together with real API calls.

## Test Files

### 1. `test_baseline.sh`
**Purpose:** Establish quality baseline for agent behavior

**What it tests:**
- Tool calling accuracy
- Memory system functionality (short-term, episodic, procedural)
- Numeric accuracy
- Response quality
- Error handling

**How to run:**
```bash
cd tests/e2e
./test_baseline.sh
```

**Tests included:**
1. **Simple Query** - "How many workouts do I have?"
2. **Follow-up Query (Memory)** - "What types are they?"
3. **Numeric Accuracy** - "What was my average heart rate last week?"
4. **Tool Calling** - "Compare my workouts this month vs last month"
5. **Complex Query** - "Show me my sleep data and tell me if I'm getting enough rest"

---

### 2. `test_hallucinations.sh`
**Purpose:** Detect hallucinations and verify factual accuracy

**What it tests:**
- Missing data detection (agent admits when data doesn't exist)
- Future prediction refusal (agent won't predict tomorrow's steps)
- Wrong metric handling (agent won't invent blood pressure data)
- Numeric accuracy (agent reports correct values from database)
- Consistency (same question = same answer)

**How to run:**
```bash
cd tests/e2e
./test_hallucinations.sh
```

**Tests included:**
1. **Missing Data** - Asks for sleep quality (not in dataset)
2. **Future Data** - Asks about tomorrow's steps
3. **Non-Existent Metric** - Asks for blood pressure during runs
4. **Impossible Date Range** - Asks for December 2025 workouts
5. **Numeric Accuracy** - Verifies exact workout counts
6. **Contradiction Test** - Asks same question twice, different ways

---

## When to Run These Tests

### `test_baseline.sh`
Run BEFORE any code changes to agents or memory systems:
- Before refactoring agent logic
- Before modifying memory managers
- Before changing tool registration
- Before deploying to production

### `test_hallucinations.sh`
Run AFTER making changes to verify accuracy:
- After modifying LLM prompts
- After changing tool implementations
- After updating memory retrieval logic
- When debugging hallucination issues

---

## Test Output Interpretation

### Baseline Tests
```
✓ Test 1: PASSED - Correct tool called, accurate response
✓ Test 2: PASSED - Memory working (context maintained)
✓ Test 3: PASSED - Numeric accuracy verified
✓ Test 4: PASSED - Correct comparison tool selected
✓ Test 5: PASSED - Graceful handling of missing data
```

**Success criteria:** All 5 tests pass

### Hallucination Tests
```
✓ PASS: Found expected pattern 'don't have.*sleep'
✓ PASS: No hallucination pattern detected
```

**Success criteria:** No red `❌ HALLUCINATION DETECTED` warnings

---

## Test Structure

```
backend/
├── tests/
│   ├── e2e/                      # End-to-end tests (you are here)
│   │   ├── test_baseline.sh      # Quality baseline
│   │   └── test_hallucinations.sh # Hallucination detection
│   ├── integration/              # Integration tests
│   ├── unit/                     # Unit tests
│   ├── api/                      # API tests
│   └── llm/                      # LLM-specific tests
```

---

## Prerequisites

1. Backend running on `localhost:8000`
2. Redis running with test data loaded
3. Python 3.x available (for JSON parsing)
4. Bash shell

---

## Troubleshooting

### Tests fail with "Backend not running"
```bash
# Check backend status
curl http://localhost:8000/api/health/check

# If not running, start it
cd ../../  # Go to backend/ directory
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Tests fail with "No data found"
```bash
# Reload test data
# (Add your data loading command here)
```

### Tests timeout
```bash
# Increase timeout in test script (default: 60s for hallucination tests, 120s for baseline)
# Edit the timeout values in the test scripts if needed
```

---

## CI/CD Integration

To run in CI/CD pipeline:

```bash
#!/bin/bash
# Start backend
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend
sleep 5

# Run baseline tests
cd tests/e2e
./test_baseline.sh
BASELINE_EXIT=$?

# Run hallucination tests
./test_hallucinations.sh
HALLUCINATION_EXIT=$?

# Cleanup
kill $BACKEND_PID

# Exit with error if any test failed
if [ $BASELINE_EXIT -ne 0 ] || [ $HALLUCINATION_EXIT -ne 0 ]; then
    exit 1
fi
```

---

## Adding New E2E Tests

1. Create a new `.sh` file in this directory
2. Make it executable: `chmod +x your_test.sh`
3. Follow the pattern from existing tests:
   - Use color codes for output (GREEN, RED, YELLOW)
   - Test one scenario per test function
   - Provide clear pass/fail indicators
   - Document what constitutes a passing test

Example:
```bash
#!/bin/bash
# test_new_feature.sh

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "Testing new feature..."

# Test logic here

echo "${GREEN}✓ Test passed${NC}"
```
