#!/bin/bash
# Check Ollama GPU acceleration status

echo "=== Ollama GPU Verification ==="
echo ""

# Check if Ollama is running
if pgrep -q ollama; then
    echo "✅ Ollama is running"
else
    echo "❌ Ollama is not running"
    exit 1
fi

echo ""
echo "=== Testing inference speed ==="

# Test with simple prompt
start_time=$(date +%s%N)
response=$(curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen2.5:7b",
  "prompt": "Say hello",
  "stream": false,
  "options": {
    "num_predict": 10
  }
}')
end_time=$(date +%s%N)

# Calculate duration
duration=$(echo "scale=3; ($end_time - $start_time) / 1000000000" | bc)
tokens=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('eval_count', 0))" 2>/dev/null || echo "unknown")
load_duration=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('load_duration', 0) / 1e9)" 2>/dev/null || echo "0")
eval_duration=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('eval_duration', 0) / 1e9)" 2>/dev/null || echo "0")

echo "Total time: ${duration}s"
echo "Load time: ${load_duration}s"
echo "Eval time: ${eval_duration}s"
echo "Tokens generated: $tokens"

if [ "$tokens" != "unknown" ] && [ "$tokens" != "0" ]; then
    tokens_per_sec=$(echo "scale=2; $tokens / $eval_duration" | bc)
    echo "Speed: ${tokens_per_sec} tokens/sec"
    echo ""

    # Interpret results
    if (( $(echo "$tokens_per_sec > 30" | bc -l) )); then
        echo "🚀 GOOD: GPU acceleration likely enabled (${tokens_per_sec} tok/s)"
        echo "   Expected with Apple Silicon Metal: 40-80 tok/s for 7B model"
    elif (( $(echo "$tokens_per_sec > 10" | bc -l) )); then
        echo "⚠️  MODERATE: Possible CPU fallback (${tokens_per_sec} tok/s)"
        echo "   Expected CPU-only: 8-15 tok/s for 7B model"
    else
        echo "❌ SLOW: Likely CPU-only mode (${tokens_per_sec} tok/s)"
        echo "   Check if Metal is available: system_profiler SPDisplaysDataType | grep Metal"
    fi
fi

echo ""
echo "=== System Info ==="
echo "Mac model: $(sysctl -n hw.model)"
echo "Chip: $(sysctl -n machdep.cpu.brand_string)"
system_profiler SPDisplaysDataType 2>/dev/null | grep -i "metal" | head -1

echo ""
echo "=== Running Models ==="
ollama ps
