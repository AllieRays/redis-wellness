# Redis Wellness 🏥

> Why memory matters for personalized private wellness conversations using Redis, health data, and local AI

A **side-by-side demo** comparing **stateless chat** vs. **agentic RAG chat** powered by Redis and RedisVL. Built with FastAPI, LangGraph, and local LLMs (Ollama) - your health data never leaves your machine.

## 🎯 The Demo: Stateless vs. Memory-Powered Chat

This project demonstrates the transformative power of memory in AI conversations through a live comparison:

### Stateless Chat (No Memory)
- ❌ Forgets context between messages
- ❌ Can't answer follow-up questions
- ❌ Repeats the same information
- ❌ No conversation continuity

### Agentic RAG Chat (Redis + RedisVL)
- ✅ Remembers entire conversation history
- ✅ Understands pronouns and references ("it", "that", "then")
- ✅ Semantic memory with vector search
- ✅ Context-aware, personalized responses
- ✅ LangGraph agentic tool calling

## 🏗️ Architecture

```
                           Docker Network
┌──────────────────────────────────────────────────────────┐
│                                                           │
│  Frontend (TS+Vite) ────→ Backend (FastAPI) ───→ Redis   │
│       :3000                    :8000             :6379    │
│                                  ↓                        │
│                         LangGraph Agent                   │
│                              ↓                            │
│                           Ollama (Host)                   │
│                              :11434                       │
└───────────────────────────────────────────────────────────┘

Redis/RedisVL stores:
- Short-term memory (conversation history)
- Long-term memory (semantic vector search)
- Health data cache (7-month TTL)
```

## ✨ Key Features

### Agentic RAG with LangGraph
- **LangGraph workflow**: Stateful agent with tool calling
- **3 specialized tools**: Health data retrieval, aggregation, workouts
- **Qwen 2.5 7B**: Optimized local LLM for tool calling
- **Query classification**: Intelligent tool routing layer

### Dual Memory System (RedisVL)
- **Short-term memory**: Recent conversation (Redis LIST)
- **Long-term memory**: Semantic search (RedisVL HNSW index)
- **Vector embeddings**: `mxbai-embed-large` for semantic retrieval
- **7-month TTL**: Persistent health context

### Privacy-First
- **100% local**: Ollama LLM + Redis on your machine
- **Zero cloud APIs**: No data leaves your environment
- **Apple Health integration**: Import your own XML exports

## 🚀 Quick Start

### Prerequisites

1. **Docker & Docker Compose** - For running all services
2. **Ollama** - For local LLM inference (runs on host)

### Install Ollama & Models

```bash
# Install Ollama (macOS)
brew install ollama

# Or download from https://ollama.ai

# Start Ollama service
ollama serve

# In another terminal, pull the models
ollama pull qwen2.5:7b              # Main LLM (4.7 GB)
ollama pull mxbai-embed-large       # Embeddings (669 MB)
```

### Start Everything

**Option 1: Use the start script (recommended)**

```bash
chmod +x start.sh
./start.sh
```

**Option 2: Manual start**

```bash
docker-compose up --build
```

### Access the Application

- **Frontend UI**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs
- **RedisInsight**: http://localhost:8001

## 📊 Try the Demo

### 1. Load Health Data

Export from Apple Health (or use sample data):

```bash
# Upload your Apple Health export.xml
curl -X POST http://localhost:8000/api/health/upload \
  -F "file=@export.xml"
```

### 2. Compare Stateless vs. RAG Chat

#### Test Scenario: Follow-up Questions

**Stateless Chat** (`POST /api/chat/stateless`):
```
You: "What was my average heart rate last week?"
Bot: "87 bpm"

You: "Is that good?"
Bot: ❌ "What are you referring to?" (forgot context!)
```

**RAG Chat** (`POST /api/chat/redis`):
```
You: "What was my average heart rate last week?"
Bot: "87 bpm"

You: "Is that good?"
Bot: ✅ "87 bpm is within normal range..." (remembers "that" = heart rate!)
```

#### Test Scenario: Pronoun Resolution

**Stateless**:
```
You: "When did I last work out?"
Bot: "2 days ago - Running, 30 minutes"

You: "What was my heart rate during that?"
Bot: ❌ "During what?" (no memory!)
```

**RAG Chat**:
```
You: "When did I last work out?"
Bot: "2 days ago - Running, 30 minutes"

You: "What was my heart rate during that?"
Bot: ✅ "During your run 2 days ago, average was 145 bpm" (remembers context!)
```

### 3. Try Agentic Tool Calling

The RAG agent intelligently selects tools:

```bash
# Aggregation query → calls aggregate_metrics tool
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "What was my AVERAGE heart rate last week?"}'

# Retrieval query → calls search_health_records_by_metric tool
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me my weight in September"}'

# Workout query → calls search_workouts_and_activity tool
curl -X POST http://localhost:8000/api/chat/redis \
  -H "Content-Type: application/json" \
  -d '{"message": "When did I last work out?"}'
```

## 🧠 How Memory Works

### Short-Term Memory (Conversation History)

Recent messages stored in Redis LIST:

```python
conversation:{session_id} → [msg1, msg2, msg3...]
TTL: 7 months
```

- Last 10 messages retrieved for context
- Enables pronoun resolution ("it", "that")
- Maintains conversation flow

### Long-Term Memory (Semantic Search)

Important insights stored in RedisVL vector index:

```python
# Vector embedding stored
memory:{user_id}:{timestamp} → {
    "text": "User's BMI goal is 22",
    "embedding": [0.234, -0.123, ...],  # 1024 dimensions
    "metadata": {...}
}
```

- Semantic search via HNSW index
- Retrieves relevant past conversations
- Powers contextual recall

### Tool Calling with Query Classification

1. **Query Analysis**: Classify intent (aggregation/retrieval/workout)
2. **Tool Filtering**: Pre-select relevant tools (reduces LLM confusion)
3. **Tool Execution**: LangGraph orchestrates multi-step workflows
4. **Memory Update**: Store results in semantic memory

## 🔧 Project Structure

```
.
├── backend/
│   ├── src/
│   │   ├── agents/
│   │   │   ├── health_rag_agent.py      # LangGraph agentic workflow
│   │   │   ├── query_classifier.py      # Tool routing layer
│   │   │   ├── tool_wrappers.py         # Health data tools
│   │   │   └── memory_manager.py        # RedisVL dual memory
│   │   ├── api/
│   │   │   ├── chat_routes.py           # Stateless vs. Redis comparison
│   │   │   └── agent_routes.py          # Direct tool endpoints
│   │   ├── services/
│   │   │   ├── redis_chat.py            # RAG chat service
│   │   │   └── stateless_chat.py        # No-memory baseline
│   │   └── parsers/
│   │       └── apple_health_parser.py   # XML parsing
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── main.ts                      # Chat UI
│   │   ├── api.ts                       # Backend client
│   │   └── style.css
│   ├── Dockerfile
│   └── package.json
│
├── docs/
│   ├── QWEN_TOOL_CALLING_IMPLEMENTATION_PLAN.md
│   └── INTELLIGENT_HEALTH_TOOLS_PLAN.md
│
├── docker-compose.yml
└── start.sh
```

## 📚 API Endpoints

### Chat Endpoints (The Demo!)

- `POST /api/chat/stateless` - Stateless chat (no memory)
- `POST /api/chat/redis` - RAG chat (full memory)
- `GET /api/chat/history/{session_id}` - View conversation history
- `GET /api/chat/memory/{session_id}` - Memory statistics
- `DELETE /api/chat/session/{session_id}` - Clear session

### Demo Comparison Endpoint

- `GET /api/chat/demo/info` - Get full demo documentation

Returns:
```json
{
  "demo_title": "Apple Health RAG: Stateless vs. RedisVL Memory",
  "stateless_chat": {...},
  "redis_chat": {...},
  "comparison_scenarios": [...]
}
```

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Agent Framework** | LangGraph | Stateful agentic workflows |
| **LLM** | Qwen 2.5 7B (Ollama) | Local tool calling |
| **Embeddings** | mxbai-embed-large | Semantic vectors |
| **Memory** | Redis + RedisVL | Short + long-term memory |
| **Vector Search** | RedisVL HNSW | Semantic retrieval |
| **Backend** | FastAPI | Async Python API |
| **Frontend** | TypeScript + Vite | Modern UI |

## 🔒 Privacy & Security

- **100% local processing**: Ollama runs on your machine
- **No external APIs**: Zero data sent to cloud services
- **Your data, your control**: Redis runs locally
- **7-month TTL**: Automatic data expiration
- **Apple Health privacy**: Import your own data securely

## 📖 Learn More

### Documentation

- [Qwen Tool Calling Implementation Plan](./docs/QWEN_TOOL_CALLING_IMPLEMENTATION_PLAN.md)
- [Intelligent Health Tools Plan](./docs/INTELLIGENT_HEALTH_TOOLS_PLAN.md)

### Tech Resources

- [RedisVL Documentation](https://redisvl.com)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Ollama Documentation](https://ollama.ai)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 🐛 Troubleshooting

**Services not starting?**

```bash
# Check Docker is running
docker ps

# View logs
docker-compose logs -f backend
```

**Ollama not responding?**

```bash
# Check if Ollama is running
curl http://localhost:11434

# Check installed models
ollama list

# Pull missing models
ollama pull qwen2.5:7b
ollama pull mxbai-embed-large
```

**Tool calling not working?**

Check backend logs for classification:
```bash
docker-compose logs backend | grep "🎯 Query classified"
```

## 🤝 Contributing

This is a demo project showcasing Redis + RedisVL capabilities. Feel free to:

- Report issues
- Suggest improvements
- Share your own examples

## 📄 License

MIT

---

**Built with ❤️ to demonstrate why memory matters in AI conversations**

*A Redis + RedisVL demonstration project*
