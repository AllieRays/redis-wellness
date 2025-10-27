# Token-Aware Context Management

## Overview

**Token-aware context management** automatically manages conversation history to prevent exceeding the LLM's context window. When a conversation approaches the token limit, old messages are automatically removed while keeping recent messages for context.

## Why It Matters

### The Problem
```
Long conversation (100 messages)
    ↓
20,000+ tokens
    ↓
Qwen 2.5 7B context window: ~32,768 tokens
    ↓
But safely use only ~24,000 (75% margin)
    ↓
Risk of:
  • Truncated responses
  • Lost context
  • LLM confusion
  • Silent degradation
```

### The Solution
```
Automatic trimming keeps recent messages
    ↓
Stay under 24,000 token threshold
    ↓
Oldest messages removed first
    ↓
Latest context preserved
    ↓
Reliable, consistent responses
```

## How It Works

### 1. Token Counting
Uses `tiktoken` (OpenAI's tokenizer) to accurately count tokens:
```python
from src.utils.token_manager import get_token_manager

token_manager = get_token_manager()

# Count tokens in a single message
tokens = token_manager.count_tokens("What's my heart rate?")  # ~5 tokens

# Count tokens in full conversation
messages = [
    {"role": "user", "content": "What's my heart rate?"},
    {"role": "assistant", "content": "Your HR is 72 bpm."},
]
total = token_manager.count_message_tokens(messages)  # ~40 tokens
```

### 2. Automatic Trimming
When conversation exceeds threshold, trim automatically:
```python
# Get context with automatic trimming
context_str, token_stats = await memory_manager.get_short_term_context_token_aware(
    user_id="user123",
    session_id="session456",
    limit=20  # Try to get up to 20 messages
)

# Returns:
# - context_str: Trimmed conversation (under token limit)
# - token_stats: Usage statistics
```

### 3. Trimming Strategy
- **Removes oldest messages first** (chronologically)
- **Keeps most recent messages** (for context awareness)
- **Preserves at least 2 messages** (min_messages_to_keep)
- **Logs trim events** (for debugging)

Example:
```
Original: 50 messages, 25,000 tokens
Threshold: 19,200 tokens (80% of 24,000)

Action: Remove oldest 40 messages
Result: 10 messages, 18,500 tokens ✅ Under threshold
```

## Configuration

Set in `.env` or `config.py`:

```python
# Maximum tokens to use (75% of 32k context)
max_context_tokens: int = 24000

# Trigger trimming at 80% of max
token_usage_threshold: float = 0.8

# Always keep minimum recent messages
min_messages_to_keep: int = 2
```

### Why These Defaults?
- **24,000 tokens**: Conservative limit (75% of 32k) leaves room for:
  - System prompt
  - User message
  - Tool outputs
  - Response generation
- **80% threshold**: Trim before hitting hard limit
- **Min 2 messages**: Enough context for follow-up questions

## API Usage

### 1. Chat Response Includes Token Stats
```bash
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "What is my heart rate?", "session_id": "demo"}'
```

Response includes:
```json
{
  "response": "Your average heart rate is 72 bpm.",
  "token_stats": {
    "message_count": 8,
    "token_count": 3204,
    "max_tokens": 24000,
    "usage_percent": 13.4,
    "threshold_percent": 16.8,
    "is_over_threshold": false
  }
}
```

### 2. Check Token Usage (Without Chat)
```bash
curl http://localhost:8000/api/chat/tokens/demo?limit=20
```

Response:
```json
{
  "session_id": "demo",
  "token_stats": {
    "message_count": 20,
    "token_count": 19234,
    "max_tokens": 24000,
    "usage_percent": 80.1,
    "threshold_percent": 100.1,
    "is_over_threshold": true
  },
  "status": "over_threshold"
}
```

### 3. Get Memory Stats (Includes Token Info)
```bash
curl http://localhost:8000/api/chat/memory/demo
```

## Implementation Details

### TokenManager Class

Located in `src/utils/token_manager.py`:

```python
class TokenManager:
    def __init__(self):
        # Initialize with settings
        self.max_tokens = 24000
        self.threshold = 19200  # 80% of max

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken"""

    def count_message_tokens(self, messages: list) -> int:
        """Count tokens in conversation"""

    def should_trim(self, token_count: int) -> bool:
        """Check if trimming needed"""

    def trim_messages(self, messages: list) -> tuple:
        """Trim messages, return (trimmed, original_tokens, trimmed_tokens)"""

    def get_usage_stats(self, messages: list) -> dict:
        """Get usage statistics"""
```

### Integration Points

1. **MemoryManager** (`memory_manager.py`):
   ```python
   async def get_short_term_context_token_aware(
       self, user_id: str, session_id: str, limit: int
   ) -> tuple[str | None, dict]:
       # Uses TokenManager to trim messages
   ```

2. **RedisChatService** (`redis_chat.py`):
   ```python
   async def chat(self, message: str, session_id: str):
       # Calls token-aware context retrieval
       # Includes token_stats in response
   ```

3. **Chat API** (`chat_routes.py`):
   ```python
   # New endpoint: /api/chat/tokens/{session_id}
   # Response model updated: token_stats added
   ```

## Demo & Testing

### Run the Demo Script
```bash
cd backend
python test_token_management.py
```

Output:
```
====================================================================
TOKEN-AWARE CONTEXT MANAGEMENT DEMO
====================================================================

📊 Configuration:
   Max context tokens: 24000
   Trim threshold: 19200 tokens (80.0%)
   Min messages to keep: 2

📝 Sample conversation (10 messages):
   1. USER: What is my average heart rate?...
   2. ASSISTANT: Your average heart rate over the last week was 72 bpm...
   ...

🔢 Token count: 2845 / 24000
   Usage: 11.9%
   Trimming needed: NO

📈 Usage Statistics:
   Message count: 10
   Token count: 2845
   Usage: 11.9% of max
   Threshold usage: 14.8% of threshold
   Over threshold: False

📊 SIMULATION: Conversation Growing Over Time
====================================================================
   Message  1:   289 tokens ( 1.2%) 🟢
   Message  2:   612 tokens ( 2.6%) 🟢
   Message  3:   895 tokens ( 3.7%) 🟢
   ...
   Message 10:  2845 tokens (11.9%) 🟢

✅ Demo complete!
```

### Unit Tests
Tests in `backend/tests/unit/test_token_manager.py`:
```bash
uv run pytest tests/unit/test_token_manager.py -v
```

Tests cover:
- Token counting accuracy
- Trimming logic
- Threshold detection
- Edge cases (empty messages, single message, etc.)

## Monitoring

### Log Events
Token manager logs important events:
```
INFO Trimming messages: 25000 tokens > 19200 limit. Keeping 2 most recent messages.
INFO Trimmed to 8 messages (18500 tokens)
WARNING Reached minimum message limit (2). Still using 3200 tokens.
```

### Token Usage Metrics
- Available in every chat response
- Accessible via `/api/chat/tokens/{session_id}`
- Track usage over time:
  ```bash
  # Before: 50% usage
  # After 10 more messages: 75% usage
  # After 20 more messages: Trimmed back to 40%
  ```

## Performance Impact

### Overhead
- Token counting: ~1-5ms per conversation
- Trimming: ~2-10ms (only when needed)
- Negligible compared to LLM latency (1-5 seconds)

### Benefits
- Prevents context window overflow
- Improves response reliability
- Enables longer conversations
- No data loss (messages stored in Redis)

## Troubleshooting

### Messages Getting Trimmed Too Aggressively
**Problem**: Conversation trimmed when it shouldn't be
**Solution**: Increase `max_context_tokens` or decrease `token_usage_threshold`

```python
# config.py
max_context_tokens: int = 28000  # More generous
token_usage_threshold: float = 0.9  # Trim at 90% instead of 80%
```

### "Still using X tokens" Warning
**Problem**: Even with minimum messages, over threshold
**Solution**: This is normal for very long individual messages. Increases `min_messages_to_keep` to at least 3-5.

### Token Count Seems Wrong
**Problem**: Count doesn't match expectations
**Solution**: Verify with demo script and check if `tiktoken` is installed:
```bash
pip install tiktoken
python test_token_management.py
```

## Best Practices

✅ **DO:**
- Monitor token_stats in responses
- Set conservative limits (leave margin)
- Test with expected conversation length
- Use demo script to validate behavior

❌ **DON'T:**
- Set max_context_tokens too high (risk overflow)
- Set min_messages_to_keep too high (defeats purpose)
- Ignore token_stats warnings
- Assume exact token counts (use ~)

## Future Enhancements

Potential improvements:
1. **Adaptive trimming**: Adjust threshold based on user behavior
2. **Message prioritization**: Keep important messages (e.g., health goals)
3. **Compression**: Summarize old messages instead of deleting
4. **Token budgeting**: Reserve tokens for tools/responses
5. **Analytics**: Track token usage patterns

## References

- OpenAI tokenizer: https://github.com/openai/tiktoken
- Token counting guide: https://platform.openai.com/docs/guides/tokens
- Qwen context window: https://huggingface.co/Qwen/Qwen2.5-7B
- RedisVL memory: https://docs.redisvl.com/

---

**Last Updated**: October 2025
**Status**: ✅ Implemented and tested
