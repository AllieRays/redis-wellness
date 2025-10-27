# Documentation Index

**Redis Wellness** - Teaching the difference between stateless and stateful AI agents using Redis, Apple Health data, and Qwen 2.5 7B.

---

## 📚 Learning Path

Follow this order for the best learning experience:

### 🚀 Phase 1: Getting Started (15 minutes)
Start here if you want to run the demo quickly.

| Doc | Status | Description | Time |
|-----|--------|-------------|------|
| [00_PREREQUISITES.md](00_PREREQUISITES.md) | ✅ Complete | Install Docker, Ollama, export health data | 5 min |
| [01_QUICKSTART.md](01_QUICKSTART.md) | ✅ Complete | Get demo running in under 5 minutes | 5 min |
| [02_THE_DEMO.md](02_THE_DEMO.md) | ✅ Complete | Side-by-side stateless vs stateful comparison | 5 min |

**After Phase 1**, you should have the demo running and understand **why** memory matters.

---

### 🤖 Phase 2: Understanding the Agents (30 minutes)
Learn how each agent works internally.

| Doc | Status | Description | Time |
|-----|--------|-------------|------|
| [03_STATELESS_AGENT.md](03_STATELESS_AGENT.md) | ✅ Complete | Baseline agent with no memory | 10 min |
| [04_STATEFUL_AGENT.md](04_STATEFUL_AGENT.md) | ✅ Complete | Redis-powered agent with memory | 15 min |
| [05_TOOLS_AND_CALLING.md](05_TOOLS_AND_CALLING.md) | 🚧 TODO | Tool catalog and autonomous calling | 5 min |

**After Phase 2**, you'll understand how tools and memory work together.

---

### 🧠 Phase 3: Memory Systems (45 minutes)
Deep dive into the four-layer memory architecture.

| Doc | Status | Description | Time |
|-----|--------|-------------|------|
| [06_MEMORY_ARCHITECTURE.md](06_MEMORY_ARCHITECTURE.md) | 🔄 Needs update | Four-layer memory system explained | 15 min |
| [07_REDIS_PATTERNS.md](07_REDIS_PATTERNS.md) | 🔄 Needs update | Redis data structures for AI agents | 20 min |
| [08_LANGGRAPH_WORKFLOW.md](08_LANGGRAPH_WORKFLOW.md) | 🚧 TODO | LangGraph StateGraph deep dive | 10 min |

**After Phase 3**, you'll understand Redis memory patterns and LangGraph orchestration.

---

### 📊 Phase 4: Data & LLM (40 minutes)
How health data flows and how Qwen makes decisions.

| Doc | Status | Description | Time |
|-----|--------|-------------|------|
| [09_APPLE_HEALTH_PIPELINE.md](09_APPLE_HEALTH_PIPELINE.md) | ✅ Complete | Import, parse, index health data | 15 min |
| [10_EXAMPLE_QUERIES.md](10_EXAMPLE_QUERIES.md) | ✅ Complete | Query examples with response comparison | 15 min |
| [11_QWEN_BEST_PRACTICES.md](11_QWEN_BEST_PRACTICES.md) | ✅ Complete | Tool calling best practices | 10 min |

**After Phase 4**, you'll know how to craft effective queries and tune Qwen.

---

### 🏗️ Phase 5: Advanced Topics (60 minutes)
Architecture decisions and extension patterns.

| Doc | Status | Description | Time |
|-----|--------|-------------|------|
| [12_AUTONOMOUS_AGENTS.md](12_AUTONOMOUS_AGENTS.md) | 🔄 Needs update | Agentic workflow patterns | 20 min |
| [13_ARCHITECTURE_DECISIONS.md](13_ARCHITECTURE_DECISIONS.md) | 🔄 Needs update | Design rationale and trade-offs | 40 min |

**After Phase 5**, you'll understand why we made key architectural choices.

---

## 📖 Supporting Documentation

These docs provide additional context but aren't part of the main learning path.

| Doc | Description |
|-----|-------------|
| [TEMPLATE.md](TEMPLATE.md) | Documentation template (all docs follow this structure) |
| [RETRIEVAL_PATTERNS_GUIDE.md](RETRIEVAL_PATTERNS_GUIDE.md) | Data retrieval patterns and strategies |
| [SERVICES.md](SERVICES.md) | Service layer documentation |
| [DOCS_PLAN.md](DOCS_PLAN.md) | Documentation reorganization plan (meta) |

---

## 🎯 Quick Navigation

### By Topic

**Agents & Memory:**
- Stateless Agent → [03_STATELESS_AGENT.md](03_STATELESS_AGENT.md)
- Stateful Agent → [04_STATEFUL_AGENT.md](04_STATEFUL_AGENT.md)
- Memory Architecture → [06_MEMORY_ARCHITECTURE.md](06_MEMORY_ARCHITECTURE.md)
- LangGraph Workflow → [08_LANGGRAPH_WORKFLOW.md](08_LANGGRAPH_WORKFLOW.md)

**Tools & Retrieval:**
- Tool Catalog → [05_TOOLS_AND_CALLING.md](05_TOOLS_AND_CALLING.md)
- Example Queries → [10_EXAMPLE_QUERIES.md](10_EXAMPLE_QUERIES.md)
- Retrieval Patterns → [RETRIEVAL_PATTERNS_GUIDE.md](RETRIEVAL_PATTERNS_GUIDE.md)

**Redis & Data:**
- Redis Patterns → [07_REDIS_PATTERNS.md](07_REDIS_PATTERNS.md)
- Apple Health Pipeline → [09_APPLE_HEALTH_PIPELINE.md](09_APPLE_HEALTH_PIPELINE.md)
- Services → [SERVICES.md](SERVICES.md)

**LLM & Autonomous Agents:**
- Qwen Best Practices → [11_QWEN_BEST_PRACTICES.md](11_QWEN_BEST_PRACTICES.md)
- Autonomous Agents → [12_AUTONOMOUS_AGENTS.md](12_AUTONOMOUS_AGENTS.md)
- Architecture Decisions → [13_ARCHITECTURE_DECISIONS.md](13_ARCHITECTURE_DECISIONS.md)

---

## 📝 Documentation Status

| Status | Meaning | Count |
|--------|---------|-------|
| ✅ Complete | Production-ready, follows template | 7 |
| 🔄 Needs update | Copied from archive, needs template compliance | 4 |
| 🚧 TODO | Not yet created | 2 |

**Total docs**: 13 numbered + 4 supporting = **17 docs**

---

## 🎓 Learning Paths by Role

### **For Developers Building AI Agents:**
1. Start: [02_THE_DEMO.md](02_THE_DEMO.md)
2. Agents: [03_STATELESS_AGENT.md](03_STATELESS_AGENT.md) → [04_STATEFUL_AGENT.md](04_STATEFUL_AGENT.md)
3. Memory: [06_MEMORY_ARCHITECTURE.md](06_MEMORY_ARCHITECTURE.md) → [07_REDIS_PATTERNS.md](07_REDIS_PATTERNS.md)
4. Tools: [05_TOOLS_AND_CALLING.md](05_TOOLS_AND_CALLING.md) → [11_QWEN_BEST_PRACTICES.md](11_QWEN_BEST_PRACTICES.md)
5. Deep dive: [12_AUTONOMOUS_AGENTS.md](12_AUTONOMOUS_AGENTS.md) → [13_ARCHITECTURE_DECISIONS.md](13_ARCHITECTURE_DECISIONS.md)

### **For Learning Redis for AI:**
1. Start: [02_THE_DEMO.md](02_THE_DEMO.md)
2. Redis: [07_REDIS_PATTERNS.md](07_REDIS_PATTERNS.md)
3. Memory: [06_MEMORY_ARCHITECTURE.md](06_MEMORY_ARCHITECTURE.md)
4. Data: [09_APPLE_HEALTH_PIPELINE.md](09_APPLE_HEALTH_PIPELINE.md)
5. Examples: [10_EXAMPLE_QUERIES.md](10_EXAMPLE_QUERIES.md)

### **For Understanding Memory Systems:**
1. Start: [02_THE_DEMO.md](02_THE_DEMO.md)
2. Comparison: [03_STATELESS_AGENT.md](03_STATELESS_AGENT.md) → [04_STATEFUL_AGENT.md](04_STATEFUL_AGENT.md)
3. Architecture: [06_MEMORY_ARCHITECTURE.md](06_MEMORY_ARCHITECTURE.md)
4. Examples: [10_EXAMPLE_QUERIES.md](10_EXAMPLE_QUERIES.md)
5. Workflow: [08_LANGGRAPH_WORKFLOW.md](08_LANGGRAPH_WORKFLOW.md)

### **For Quick Demo Setup:**
1. [00_PREREQUISITES.md](00_PREREQUISITES.md) - Install everything
2. [01_QUICKSTART.md](01_QUICKSTART.md) - Run the demo
3. [10_EXAMPLE_QUERIES.md](10_EXAMPLE_QUERIES.md) - Try example queries

---

## 🔗 External Resources

### Official Documentation
- **Redis**: https://redis.io/docs
- **RedisVL**: https://redisvl.com
- **LangGraph**: https://langchain-ai.github.io/langgraph
- **Ollama**: https://ollama.ai
- **Qwen**: https://qwen.readthedocs.io

### Related Projects
- **LangChain**: https://python.langchain.com
- **FastAPI**: https://fastapi.tiangolo.com
- **Apple Health**: https://developer.apple.com/health-fitness

---

## 🤝 Contributing to Docs

All documentation follows [TEMPLATE.md](TEMPLATE.md) format:
1. **Overview** with "What You'll Learn" section
2. **Numbered sections** (2, 3, 4...)
3. **Code examples** with real file paths
4. **Related Documentation** section
5. **Key takeaway** at end

See [DOCS_PLAN.md](DOCS_PLAN.md) for reorganization plan and status.

---

**Start here**: [00_PREREQUISITES.md](00_PREREQUISITES.md) → [01_QUICKSTART.md](01_QUICKSTART.md) → [02_THE_DEMO.md](02_THE_DEMO.md)
