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

**Clean Architecture with Proper Separation of Concerns:**

> **Recent Refactoring**: The project structure was recently reorganized for better separation of concerns. All files are now properly categorized into `/agents` (actual AI agents), `/services` (data layer), `/utils` (pure utilities), and `/tools` (LangChain tools). All tests have been moved to `/backend/tests/` for proper monorepo structure.

```
.
├── backend/
│   ├── src/
│   │   ├── agents/                      # AI agents for demo comparison
│   │   │   ├── stateless_agent.py       # Baseline (NO memory)
│   │   │   ├── stateful_rag_agent.py    # Redis + RedisVL (FULL memory)
│   │   │   └── __init__.py              # Agent exports
│   │   ├── services/                    # Data layer services
│   │   │   ├── redis_chat.py            # RAG chat with memory
│   │   │   ├── stateless_chat.py        # No-memory baseline
│   │   │   ├── memory_manager.py        # RedisVL dual memory
│   │   │   ├── redis_connection.py      # Redis connection management
│   │   │   ├── redis_health_tool.py     # Health data operations
│   │   │   └── health_vectorizer.py     # Embedding generation
│   │   ├── utils/                       # Pure utilities & helpers
│   │   │   ├── agent_helpers.py         # Shared agent utilities (NEW)
│   │   │   ├── query_classifier.py      # Intent classification
│   │   │   ├── numeric_validator.py     # LLM hallucination detection
│   │   │   ├── math_tools.py            # Mathematical analysis
│   │   │   ├── base.py                  # Base classes & decorators
│   │   │   ├── stats_utils.py           # Statistical calculations
│   │   │   ├── time_utils.py            # Time parsing utilities
│   │   │   └── conversion_utils.py      # Unit conversions
│   │   ├── tools/                       # LangChain tools for agents
│   │   │   ├── agent_tools.py           # Creates user-bound tools
│   │   │   ├── health_insights_tool.py  # AI-callable insights
│   │   │   └── health_parser_tool.py    # AI-callable XML parsing
│   │   ├── api/                         # HTTP API layer
│   │   │   ├── chat_routes.py           # Chat endpoints
│   │   │   ├── agent_routes.py          # Tool endpoints
│   │   │   └── routes.py                # Router aggregation
│   │   ├── models/                      # Data models
│   │   │   └── health.py                # Pydantic health models
│   │   ├── parsers/                     # Data parsers
│   │   │   └── apple_health_parser.py   # XML parsing with validation
│   │   ├── main.py                      # FastAPI application
│   │   └── config.py                    # Configuration
│   ├── tests/                           # All backend tests
│   │   ├── unit/                        # Unit tests (no dependencies)
│   │   │   ├── test_math_tools.py       # Mathematical functions
│   │   │   ├── test_numeric_validator.py # Validation logic
│   │   │   └── test_stateless_isolation.py # Pure function tests
│   │   ├── test_redis_chat_rag.py       # RAG memory integration
│   │   └── test_redis_chat_api.py       # HTTP API tests
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── main.ts                      # Side-by-side chat UI
│   │   ├── api.ts                       # Backend API client
│   │   ├── types.ts                     # TypeScript interfaces
│   │   └── style.css                    # Modern UI styling
│   ├── Dockerfile
│   └── package.json
│
├── docs/                                # Technical documentation
│   ├── QWEN_TOOL_CALLING_IMPLEMENTATION_PLAN.md
│   ├── INTELLIGENT_HEALTH_TOOLS_PLAN.md
│   └── RAG_IMPLEMENTATION.md
│
├── scripts/                             # Utility scripts
│   ├── load_health_to_redis.py         # Health data loading
│   └── parse_apple_health.py           # XML parsing scripts
│
├── demos/                               # Demo scripts
│   ├── demo_chat_comparison.py         # Chat comparison demo
│   └── demo_health_insights.py         # Health insights demo
│
├── docker-compose.yml
├── start.sh
└── WARP.md                              # Development guidance
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


----

Your data includes:
•  💪 Workouts: 154 (Traditional Strength Training on Oct 16, 14, 12, 9...)
•  ⚖️ Weight: 431 records (Latest: 136.8 lbs on Oct 19)
•  📊 BMI: 359 records
•  🚶 Steps: 25,387 records
•  ❤️ Heart Rate: 100,047 records
•  😴 Sleep: 1,195 records
•  🔥 Active Energy: 13,643 records

his IS agentic - the LLM autonomously:
•  Plans which tools to call
•  Reacts to tool results
•  Chains multiple tools together
•  Decides when it has enough info
