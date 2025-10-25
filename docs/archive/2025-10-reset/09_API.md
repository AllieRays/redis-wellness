# API Reference

**Last Updated**: October 24, 2024
**Base URL**: `http://localhost:8000`

## Overview

Redis Wellness API provides endpoints for:
1. **Chat** - Stateless vs Redis RAG comparison
2. **Memory Management** - View and manage conversation history
3. **Health** - System health and dependency checks

All endpoints return JSON unless otherwise specified (streaming endpoints use Server-Sent Events).

---

## Authentication

**Current**: None (single-user demo)

**Future**: JWT tokens for multi-user deployment

---

## Chat Endpoints

### POST /api/chat/stateless

Stateless chat with NO memory - baseline for comparison.

**Features**:
- Tool calling for health data
- NO conversation history
- NO memory storage
- Each message is independent

**Request Body**:
```json
{
  "message": "What was my average heart rate last week?"
}
```

**Response**:
```json
{
  "response": "Your average heart rate last week was 87 bpm.",
  "tools_used": [
    {"name": "aggregate_metrics"}
  ],
  "tool_calls_made": 1,
  "validation": {
    "valid": true,
    "score": 1.0,
    "hallucinations_detected": 0,
    "numbers_validated": 1,
    "total_numbers": 1
  },
  "type": "stateless",
  "response_time_ms": 3245.6
}
```

**Example (curl)**:
```bash
curl -X POST http://localhost:8000/api/chat/stateless \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my average heart rate last week?"}'
```

---

### POST /api/chat/redis

Redis chat WITH full CoALA memory - production-ready.

**Features**:
- Tool calling with memory context
- Short-term memory (conversation history)
- Episodic memory (user preferences/goals)
- Procedural memory (learned tool patterns)
- Semantic memory (general health knowledge)
- 7-month conversation persistence

**Request Body**:
```json
{
  "message": "What was my average heart rate last week?",
  "session_id": "user_session_123"
}
```

**Response**:
```json
{
  "response": "Your average heart rate last week was 87 bpm.",
  "session_id": "user_session_123",
  "tools_used": [
    {"name": "aggregate_metrics"}
  ],
  "tool_calls_made": 1,
  "memory_stats": {
    "short_term_available": true,
    "episodic_hits": 0,
    "episodic_available": false,
    "semantic_hits": 1,
    "semantic_available": true,
    "procedural_available": true
  },
  "token_stats": {
    "message_count": 2,
    "token_count": 145,
    "usage_percent": 0.60,
    "is_over_threshold": false
  },
  "validation": {
    "valid": true,
    "score": 1.0,
    "hallucinations_detected": 0,
    "numbers_validated": 1,
    "total_numbers": 1
  },
  "type": "redis_with_memory",
  "response_time_ms": 3542.1
}
```

**Example (curl)**:
```bash
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What was my average heart rate last week?",
    "session_id": "demo_session"
  }'
```

**Follow-up Example**:
```bash
# First message
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What was my average heart rate last week?",
    "session_id": "demo"
  }'

# Response: "Your average was 87 bpm"

# Follow-up (memory makes this work!)
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Is that good?",
    "session_id": "demo"
  }'

# Response: "87 bpm is within the normal range..." (remembered "that" = 87 bpm)
```

---

### POST /api/chat/stateless/stream

Streaming stateless chat - tokens appear as generated.

**Response**: Server-Sent Events (SSE) stream

**Event Types**:
1. `token` - Individual token as it's generated
2. `done` - Final response with metadata
3. `error` - Error occurred

**Example (curl)**:
```bash
curl -N -X POST http://localhost:8000/api/chat/stateless/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my heart rate?"}'
```

**Response Stream**:
```
data: {"type": "token", "content": "Your"}

data: {"type": "token", "content": " average"}

data: {"type": "token", "content": " heart"}

data: {"type": "token", "content": " rate"}

data: {"type": "done", "data": {"response": "Your average heart rate...", "tools_used": [...]}}
```

---

### POST /api/chat/redis/stream

Streaming Redis chat - tokens appear as generated (with memory).

**Request Body**:
```json
{
  "message": "What was my heart rate?",
  "session_id": "demo"
}
```

**Response**: Same SSE format as stateless stream, but with memory stats in final `done` event.

---

## Memory Management Endpoints

### GET /api/chat/history/{session_id}

Get conversation history for a session.

**Parameters**:
- `session_id` (path) - Session identifier
- `limit` (query, optional) - Max messages (default: 10)

**Response**:
```json
{
  "session_id": "demo",
  "messages": [
    {
      "role": "user",
      "content": "What was my average heart rate?",
      "timestamp": "2024-10-24T12:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Your average heart rate last week was 87 bpm.",
      "timestamp": "2024-10-24T12:30:05Z"
    }
  ],
  "total_messages": 2
}
```

**Example**:
```bash
curl http://localhost:8000/api/chat/history/demo?limit=10
```

---

### GET /api/chat/memory/{session_id}

Get memory statistics for a session.

**Response**:
```json
{
  "short_term": {
    "message_count": 12,
    "ttl_seconds": 18143500
  },
  "long_term": {
    "memory_count": 5,
    "semantic_search_enabled": true
  },
  "user_id": "user123",
  "session_id": "demo"
}
```

**Example**:
```bash
curl http://localhost:8000/api/chat/memory/demo
```

---

### GET /api/chat/tokens/{session_id}

Get token usage statistics for context window monitoring.

**Parameters**:
- `session_id` (path) - Session identifier
- `limit` (query, optional) - Messages to check (default: 10)

**Response**:
```json
{
  "session_id": "demo",
  "token_stats": {
    "message_count": 10,
    "token_count": 2450,
    "max_tokens": 24000,
    "usage_percent": 10.2,
    "threshold_percent": 80.0,
    "is_over_threshold": false
  },
  "status": "under_threshold"
}
```

**Example**:
```bash
curl http://localhost:8000/api/chat/tokens/demo
```

---

### DELETE /api/chat/session/{session_id}

Clear all memories for a session.

**Response**:
```json
{
  "success": true,
  "session_id": "demo",
  "message": "Session cleared successfully"
}
```

**Example**:
```bash
curl -X DELETE http://localhost:8000/api/chat/session/demo
```

---

## System Endpoints

### GET /health

Comprehensive health check including dependencies.

**Response**:
```json
{
  "api": "healthy",
  "timestamp": 1729756800.123,
  "dependencies": {
    "redis": {
      "status": "healthy",
      "host": "localhost",
      "port": 6379
    },
    "ollama": {
      "status": "healthy",
      "url": "http://localhost:11434",
      "models_required": ["qwen2.5:7b", "mxbai-embed-large"],
      "models_available": ["qwen2.5:7b", "mxbai-embed-large"],
      "models_missing": []
    }
  },
  "status": "healthy"
}
```

**Status Values**:
- `healthy` - All systems operational
- `degraded` - Some dependencies unhealthy
- `unhealthy` - Critical failure

**Example**:
```bash
curl http://localhost:8000/health
```

---

### GET /

Root endpoint with system information.

**Response**:
```json
{
  "message": "Redis Wellness AI Agent",
  "version": "0.1.0",
  "features": [
    "Privacy-first health data parsing",
    "Redis-powered conversational memory",
    "RedisVL semantic search with HNSW index",
    "Dual memory system (short + long term)",
    "Local-first with Ollama (no cloud APIs)"
  ],
  "docs": "/docs"
}
```

---

### GET /api/chat/demo/info

Demo comparison information.

**Response**:
```json
{
  "demo_title": "Apple Health RAG: Stateless vs. RedisVL Memory",
  "demo_purpose": "Showcase the power of RedisVL's dual memory system",
  "stateless_chat": {
    "endpoint": "POST /api/chat/stateless",
    "features": [
      "Simple tool-calling loop",
      "9 health data retrieval tools",
      "NO conversation memory",
      "NO semantic memory",
      "Each message independent"
    ],
    "limitations": [
      "Cannot reference previous messages",
      "Cannot understand follow-up questions",
      "No personalization",
      "Repeats information"
    ]
  },
  "redis_chat": {
    "endpoint": "POST /api/chat/redis",
    "features": [
      "Full CoALA memory (4 types)",
      "Conversation history",
      "Semantic memory search",
      "Context-aware responses",
      "7-month persistence"
    ]
  }
}
```

---

## Error Handling

### Error Response Format

All errors return consistent JSON:

```json
{
  "error": "Error message description",
  "error_type": "ErrorClassName",
  "details": {
    "key": "Additional context"
  }
}
```

### Common HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid input parameters |
| 404 | Not Found | Session/resource doesn't exist |
| 500 | Server Error | Unexpected error occurred |
| 503 | Service Unavailable | Redis or Ollama unavailable |

### Example Error Response

```json
{
  "error": "Redis connection timeout",
  "error_type": "InfrastructureError",
  "details": {
    "operation": "get_conversation_history",
    "session_id": "demo"
  }
}
```

---

## Response Models

### Tools Used Format

```json
{
  "tools_used": [
    {"name": "aggregate_metrics"},
    {"name": "search_workouts_and_activity"}
  ]
}
```

### Validation Format

```json
{
  "validation": {
    "valid": true,
    "score": 1.0,
    "hallucinations_detected": 0,
    "numbers_validated": 2,
    "total_numbers": 2,
    "hallucinations": []
  }
}
```

### Memory Stats Format

```json
{
  "memory_stats": {
    "short_term_available": true,
    "episodic_hits": 2,
    "episodic_available": true,
    "semantic_hits": 1,
    "semantic_available": true,
    "procedural_available": true
  }
}
```

---

## Rate Limiting

**Current**: None (demo application)

**Future**: Per-user limits for production

---

## Interactive Documentation

### Swagger UI

**URL**: http://localhost:8000/docs

Interactive API testing interface with:
- Request/response examples
- Try it out functionality
- Schema definitions

### ReDoc

**URL**: http://localhost:8000/redoc

Alternative documentation interface with:
- Clean layout
- Searchable endpoints
- Downloadable OpenAPI spec

---

## Client Examples

### Python

```python
import httpx
import asyncio

async def chat_with_memory(message: str, session_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/chat/redis",
            json={
                "message": message,
                "session_id": session_id
            }
        )
        return response.json()

# Usage
result = asyncio.run(chat_with_memory(
    "What was my average heart rate?",
    "my_session"
))
print(result["response"])
```

### JavaScript (Fetch)

```javascript
async function chatWithMemory(message, sessionId) {
  const response = await fetch('http://localhost:8000/api/chat/redis', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: message,
      session_id: sessionId
    })
  });

  return await response.json();
}

// Usage
const result = await chatWithMemory(
  "What was my average heart rate?",
  "my_session"
);
console.log(result.response);
```

### JavaScript (Streaming)

```javascript
async function chatWithMemoryStreaming(message, sessionId) {
  const response = await fetch('http://localhost:8000/api/chat/redis/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: message,
      session_id: sessionId
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const {done, value} = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));

        if (data.type === 'token') {
          process.stdout.write(data.content);
        } else if (data.type === 'done') {
          console.log('\n\nMetadata:', data.data);
        }
      }
    }
  }
}
```

### cURL Examples

```bash
# Stateless chat
curl -X POST http://localhost:8000/api/chat/stateless \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my heart rate?"}'

# Redis chat with memory
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What was my heart rate?",
    "session_id": "demo"
  }'

# Get history
curl http://localhost:8000/api/chat/history/demo

# Get memory stats
curl http://localhost:8000/api/chat/memory/demo

# Clear session
curl -X DELETE http://localhost:8000/api/chat/session/demo

# Health check
curl http://localhost:8000/health
```

---

## Performance Considerations

### Response Times (Average)

| Endpoint | Avg Response Time | Notes |
|----------|------------------|-------|
| `/api/chat/stateless` | 3-5 seconds | Tool execution + LLM |
| `/api/chat/redis` | 3-8 seconds | +50ms for memory retrieval |
| `/api/chat/history` | <10ms | Redis LIST read |
| `/api/chat/memory` | <50ms | Stats aggregation |
| `/health` | <100ms | Dependency checks |

### Optimization Tips

1. **Use streaming** for better UX (tokens appear immediately)
2. **Session IDs** should be consistent per user (enables memory)
3. **Limit history** queries to 10 messages (faster, sufficient context)
4. **Monitor token usage** to detect context window issues

---

## Troubleshooting

### Issue: 503 Service Unavailable

**Cause**: Redis or Ollama not running

**Solution**:
```bash
# Check health endpoint
curl http://localhost:8000/health

# Start Redis
docker-compose up -d redis

# Start Ollama
ollama serve
```

### Issue: Empty Response

**Cause**: No health data loaded

**Solution**:
```bash
# Upload health data
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@export.xml"
```

### Issue: Memory Not Working

**Cause**: Different session IDs used

**Solution**: Use consistent `session_id` across requests

---

## See Also

- **Architecture**: `docs/03_ARCHITECTURE.md`
- **Development**: `docs/06_DEVELOPMENT.md`
- **Testing**: `docs/07_TESTING.md`
- **Demo Guide**: `docs/12_DEMO_GUIDE.md`

---

**Last Updated**: October 24, 2024
