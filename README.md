# Redis Wellness 🧠💾

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/typescript-5.6+-blue.svg)](https://www.typescriptlang.org/)
[![Redis](https://img.shields.io/badge/redis-7.0+-red.svg)](https://redis.io/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Privacy](https://img.shields.io/badge/privacy-100%25%20local-success.svg)](#privacy)

> **Can AI agents be intelligent without memory?**

This project compares **Stateless** and **Stateful (Redis-powered)** AI agents using **Apple Health data**, showing how memory changes the way an agent understands and responds over time.

Built with **FastAPI**, **TypeScript**, **Redis**, **RedisVL**, and **Ollama (Qwen 2.5 7B)**, all running **100% locally** for privacy.  
🔒 *Your health data never leaves your machine.*

---

## 🛠️ Tech Stack

- **AI/LLM:** Ollama (Qwen 2.5 7B) + LangChain + LangGraph
- **Vector Search:** **RedisVL** (HNSW index, 1024-dim embeddings via mxbai-embed-large)
- **Memory:** **Redis Stack** (checkpointing, indexes)
- **Data:** Apple Health data export and uploaded to Redis
- **Backend:** FastAPI + Python 3.11
- **Frontend:** TypeScript + Vite + Server-Sent Events (SSE)
- **Deployment:** Docker + Docker Compose
- **Privacy:** 100% local processing - no external APIs

---

## 🖼️ Side-by-Side Comparison

![Side-by-side chat interface showing stateless vs stateful agents](docs/images/homepage.png)

*Left: Stateless agent with no memory. Right: Stateful agent powered by Redis.*

---

## 📊 Core Architecture

| Component | Stateless Agent | Stateful Agent | Technology |
|-----------|-----------------|----------------|------------|
| **LLM** | Qwen 2.5 7B | Qwen 2.5 7B | Ollama (local) |
| **Orchestration** | Simple tool loop | LangGraph StateGraph | LangGraph |
| **Short-term Memory** | None | Conversation history | Redis checkpointing |
| **Episodic Memory** | None | User goals & facts | RedisVL vector search |
| **Procedural Memory** | None | Tool usage patterns | RedisVL vector search |
| **Health Data** | Redis (read-only) | Redis (read-only) | Redis Hashes |
| **Tools** | 3 (health only) | 5 (3 health + 2 memory) | LangChain |

**Health Tools (both agents):** `get_health_metrics`, `get_sleep_analysis`, `get_workout_data`  
**Memory Tools (stateful only):** `get_my_goals`, `get_tool_suggestions`

---

## 🎯 The Difference

### Stateless Agent (No Memory)

```mermaid
flowchart TB
    UI["User Interface"]
    Router["Intent Router<br/>(Pre-LLM)<br/>Pattern matching"]

    Simple["Redis<br/>(Simple Queries)"]
    SimpleLoop["Simple Tool Loop<br/>• Qwen 2.5 7B LLM<br/>• Tool calling<br/>• Response synthesis"]

    Tools["Health Tools<br/>(3 tools)"]
    RedisData["Redis Health Data Store"]
    Response["Response to User"]
    Forget["❌ FORGET EVERYTHING"]

    UI --> Router
    Router -->|"Simple"| Simple
    Router -->|"Complex"| SimpleLoop
    Simple --> RedisData
    SimpleLoop --> Tools
    Tools --> RedisData
    RedisData --> Response
    Response --> UI
    Response --> Forget

    style UI fill:#fff,stroke:#6c757d,stroke-width:2px,color:#000
    style Router fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style Simple fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style SimpleLoop fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style Tools fill:#fff,stroke:#333,stroke-width:2px,color:#000
    style RedisData fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Response fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style Forget fill:#fff,stroke:#dc3545,stroke-width:2px,color:#dc3545,stroke-dasharray: 5 5
```

### Stateful Agent (With Memory)

```mermaid
flowchart TB
    UI["User Interface"]
    Router["Intent Router<br/>(Pre-LLM)<br/>Pattern matching"]
    Simple["Redis<br/>(Simple Queries)"]
    Complex["LangGraph StateGraph<br/>• Qwen 2.5 7B LLM<br/>• Tool calling loop<br/>• Response synthesis"]
    RedisShort["Redis Short-term<br/>Checkpointing"]
    RedisVL["RedisVL<br/>Episodic + Procedural<br/>Vector Search"]
    Tools["LLM Tools<br/>(5 total: 3 health + 2 memory)"]
    Response["Response to User"]
    Store["✅ STORE MEMORY"]

    UI --> Router
    Router -->|"Fast path"| Simple
    Router -->|"Complex path"| Complex
    Simple --> Response
    Complex --> RedisShort
    Complex --> RedisVL
    Complex --> Tools
    Tools --> Response
    Response --> UI
    Response --> Store

    style UI fill:#fff,stroke:#6c757d,stroke-width:2px,color:#000
    style Router fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style Simple fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Complex fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style RedisShort fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style RedisVL fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Tools fill:#fff,stroke:#333,stroke-width:2px,color:#000
    style Response fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style Store fill:#fff,stroke:#28a745,stroke-width:2px,color:#28a745,stroke-dasharray: 5 5
```

**Key difference:** Redis memory enables follow-up questions, goal recall, and pattern learning.

**[📖 See detailed comparison →](docs/05_STATELESS_VS_STATEFUL_COMPARISON.md)**

---

## 🚀 Quick Start

**Prerequisites:**
- Docker & Docker Compose
- Ollama with models: `ollama pull qwen2.5:7b` and `ollama pull mxbai-embed-large`
- Apple Health export in `apple_health_export/export.xml`

**[📖 Detailed prerequisites →](docs/01_PREREQUISITES.md)**

```bash
# 1. Start services
make up

# 2. Import Apple Health data
make import

# 3. Open http://localhost:3000
```

**Try it:**
- Ask both agents: *"How many workouts do I have?"* → Both answer correctly ✅
- Follow up: *"What's the most common type?"*
  - ❌ Stateless: *"What are you referring to?"*
  - ✅ Stateful: *"Traditional Strength Training (40 workouts, 26%)\"*

**[📖 Full setup guide →](docs/02_QUICKSTART.md)**

---

## 📚 Documentation

**Getting Started:**

1. [Prerequisites](docs/01_PREREQUISITES.md) - Docker, Ollama, Apple Health export
2. [Quickstart](docs/02_QUICKSTART.md) - Running in 5 minutes

**Agent Architecture:**

3. [Stateless Agent](docs/03_STATELESS_AGENT.md) - Simple tool loop without memory
4. [Stateful Agent](docs/04_STATEFUL_AGENT.md) - LangGraph with four-layer memory
5. [Stateless vs Stateful Comparison](docs/05_STATELESS_VS_STATEFUL_COMPARISON.md) - Side-by-side breakdown

**Core Concepts:**

6. [Agentic RAG](docs/06_AGENTIC_RAG.md) - Autonomous tool calling
7. [Apple Health Data Import](docs/07_HOW_TO_IMPORT_APPLE_HEALTH_DATA.md) - Data pipeline
8. [Qwen Best Practices](docs/08_QWEN_BEST_PRACTICES.md) - Tool calling optimization
9. [Example Queries](docs/09_EXAMPLE_QUERIES.md) - Try these to see memory in action

**Memory Systems:**

10. [Memory Architecture](docs/10_MEMORY_ARCHITECTURE.md) - Four-layer memory system
11. [Redis Patterns](docs/11_REDIS_PATTERNS.md) - Data structures for AI agents
12. [LangGraph Checkpointing](docs/12_LANGGRAPH_CHECKPOINTING.md) - Conversation state

**Reference:**

13. [Tools, Services & Utils](docs/13_TOOLS_SERVICES_UTILS_REFERENCE.md) - Complete code reference

---

## 🤝 Contributing

This is a demo project showcasing Redis + RedisVL for AI agent memory. Feel free to:
- Open issues for bugs or questions
- Submit PRs for improvements
- Use as reference for your own projects

---

## 📄 License

MIT License - See [LICENSE](LICENSE)

---

**Built to showcase Redis + RedisVL for intelligent AI agents** 🧠💾
