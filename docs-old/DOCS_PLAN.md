# Documentation Reorganization Plan

**Goal**: Create a cohesive, numbered documentation set that teaches stateless vs. stateful agents using Redis, Apple Health data, and Qwen 2.5 7B.

**Template**: All docs follow `template.md` format with consistent structure.

---

## Final Documentation Structure

### Phase 1: Getting Started (00-02)
- **00_PREREQUISITES.md** ✅ EXISTS - Docker, Ollama, Apple Health export
- **01_QUICKSTART.md** ✅ EXISTS - Get running in 5 minutes
- **02_THE_DEMO.md** ✅ EXISTS - Side-by-side comparison walkthrough

### Phase 2: Understanding the Agents (03-05)
- **03_STATELESS_AGENT.md** 🔄 RENAME from `STATELESS_AGENT.md`
  - How the baseline agent works (no memory)
  - Simple tool calling loop
  - Intent routing for goal CRUD
  - 3 health tools only

- **04_STATEFUL_AGENT.md** 🔄 RENAME from `STATEFUL_AGENT.md`
  - How Redis-powered agent works
  - LangGraph StateGraph workflow
  - Four-layer memory system
  - 5 tools (3 health + 2 memory)

- **05_TOOLS_AND_CALLING.md** ⭐ NEW - Consolidate tool documentation
  - All 5 tools explained (3 health + 2 memory)
  - Autonomous tool calling with Qwen
  - Tool selection patterns
  - Side-by-side: which tools each agent has
  - Real code examples from query_tools/

### Phase 3: Memory Systems (06-08)
- **06_MEMORY_ARCHITECTURE.md** 🔄 MOVE from `archive/03_MEMORY_ARCHITECTURE.md`
  - Four-layer memory (short-term, episodic, procedural, semantic)
  - CoALA framework explanation
  - Real Redis key examples
  - Memory retrieval patterns (autonomous via tools)
  - Memory storage patterns (automatic after response)

- **07_REDIS_PATTERNS.md** 🔄 MOVE from `archive/05_REDIS_PATTERNS.md`
  - Redis data structures for AI (STRING, LIST, HASH, ZSET, Vector)
  - Why Redis vs PostgreSQL/traditional DB
  - Health data storage patterns
  - Memory storage patterns (episodic, procedural, semantic)
  - RedisVL HNSW vector search
  - Real code examples from services/

- **08_LANGGRAPH_WORKFLOW.md** ⭐ NEW - LangGraph StateGraph deep dive
  - How LangGraph orchestrates the stateful agent
  - StateGraph nodes and edges
  - Checkpointing with AsyncRedisSaver
  - Message history management
  - Recursion limits and control flow
  - Real code examples from agents/stateful_rag_agent.py

### Phase 4: Data & LLM (09-11)
- **09_APPLE_HEALTH_PIPELINE.md** 🔄 RENAME from `HOW_TO_IMPORT_APPLE_HEALTH_DATA.md`
  - Export from iPhone
  - XML parsing with validation
  - Data enrichment (day_of_week, type_cleaned)
  - Redis indexing (workout:*, sleep:*, metric:*)
  - Performance optimization (O(1) lookups)
  - Real code examples from apple_health/

- **10_EXAMPLE_QUERIES.md** ⭐ NEW - Comprehensive query examples
  - **Structure**: Feature → Tool Used → Memory Type → Example Query → Response Comparison
  - Sections:
    1. Basic Health Queries (metrics, sleep, workouts)
    2. Follow-up Questions (showing memory benefit)
    3. Pronoun Resolution (that, it, those)
    4. Multi-turn Reasoning (complex conversations)
    5. Goal-based Queries (episodic memory)
    6. Pattern Learning (procedural memory)
    7. Tool Chaining Examples (multi-step queries)
  - Each query shows: stateless response vs stateful response

- **11_QWEN_BEST_PRACTICES.md** 🔄 RENAME from `08_QWEN_BEST_PRACTICES.md`
  - Temperature settings for tool calling
  - Tool description guidelines
  - System prompt design
  - Query classification patterns
  - Troubleshooting tool selection
  - Production monitoring

### Phase 5: Advanced (12-13)
- **12_AUTONOMOUS_AGENTS.md** 🔄 MOVE from `archive/04_AUTONOMOUS_AGENTS.md`
  - What is autonomous tool calling?
  - Why Qwen 2.5 7B?
  - Agentic workflow patterns
  - Tool chaining and multi-step reasoning
  - Intent routing and fast paths
  - Real code examples from agents/

- **13_ARCHITECTURE_DECISIONS.md** 🔄 MOVE from `archive/06_ARCHITECTURE_DECISIONS.md`
  - Why LangGraph vs custom loops?
  - Why Redis vs PostgreSQL + Pinecone?
  - Why Ollama vs cloud APIs?
  - Why autonomous memory retrieval (tools) vs automatic injection?
  - Why simple tool loop for stateless?
  - Trade-offs and alternatives

### Supporting Docs (Unnumbered)
- **DOCS_INDEX.md** ⭐ NEW - Master table of contents
- **TEMPLATE.md** ✅ EXISTS - Documentation template
- **RETRIEVAL_PATTERNS_GUIDE.md** ✅ EXISTS - Keep as-is
- **SERVICES.md** ✅ EXISTS - Keep as-is

---

## Action Items

### Step 1: Rename Existing Docs ✅
```bash
# Rename to numbered sequence
mv docs/STATELESS_AGENT.md docs/03_STATELESS_AGENT.md
mv docs/STATEFUL_AGENT.md docs/04_STATEFUL_AGENT.md
mv docs/HOW_TO_IMPORT_APPLE_HEALTH_DATA.md docs/09_APPLE_HEALTH_PIPELINE.md
mv docs/08_QWEN_BEST_PRACTICES.md docs/11_QWEN_BEST_PRACTICES.md
```

### Step 2: Move and Update Archived Docs 📋
```bash
# Move from archive and update to template.md format
cp docs/archive/03_MEMORY_ARCHITECTURE.md docs/06_MEMORY_ARCHITECTURE.md
cp docs/archive/05_REDIS_PATTERNS.md docs/07_REDIS_PATTERNS.md
cp docs/archive/04_AUTONOMOUS_AGENTS.md docs/12_AUTONOMOUS_AGENTS.md
cp docs/archive/06_ARCHITECTURE_DECISIONS.md docs/13_ARCHITECTURE_DECISIONS.md

# Then update each to:
# - Follow template.md structure
# - Add real code examples from current codebase
# - Update Redis key patterns to match current implementation
# - Add "What You'll Learn" section
# - Add "Related Documentation" section
```

### Step 3: Create New Docs ⭐
- **05_TOOLS_AND_CALLING.md** - Tool comparison and autonomous calling
- **08_LANGGRAPH_WORKFLOW.md** - LangGraph StateGraph deep dive
- **10_EXAMPLE_QUERIES.md** - Query examples organized by feature/tool/memory
- **DOCS_INDEX.md** - Master table of contents

### Step 4: Update Cross-References 🔗
Update links in:
- `README.md` (main documentation section)
- All numbered docs (Related Documentation sections)
- `WARP.md` (if referencing docs)

### Step 5: Verify Template Compliance ✅
Check each doc has:
- `## 1. Overview` with "What You'll Learn" bullets
- Numbered sections (2, 3, 4...)
- Code examples with proper formatting
- `## N. Related Documentation` section
- `**Key takeaway:**` at end

---

## 10_EXAMPLE_QUERIES.md Structure

### Proposed Format:

```markdown
# Example Queries: Stateless vs Stateful Comparison

## 1. Basic Health Queries

### Query: "What was my average heart rate last week?"

| Aspect | Details |
|--------|---------|
| **Feature** | Health metric retrieval with statistics |
| **Tool Used** | `get_health_metrics` |
| **Memory Type** | None (stateless) / Short-term (stateful) |
| **Stateless Response** | "Your average heart rate last week was 72 bpm." |
| **Stateful Response** | "Your average heart rate last week was 72 bpm. This is consistent with your baseline from the previous week." |
| **Key Difference** | Stateful can reference previous context |

---

## 2. Follow-up Questions

### Initial Query: "How many workouts do I have?"

| Aspect | Details |
|--------|---------|
| **Tool Used** | `get_workout_data` |
| **Stateless Response** | "You have 154 workouts recorded." |
| **Stateful Response** | "You have 154 workouts recorded." |

### Follow-up: "What's the most common type?"

| Aspect | Details |
|--------|---------|
| **Memory Type** | None / Short-term checkpointing |
| **Stateless Response** | ❌ "What are you referring to? Please provide more context." |
| **Stateful Response** | ✅ "Traditional Strength Training is your most common workout type (40 workouts, 26% of total)." |
| **Key Difference** | Stateful remembers "workouts" from previous turn |

---

## 3. Pronoun Resolution

### Initial: "When was my last cycling workout?"
### Follow-up: "How long was it?"

| Aspect | Details |
|--------|---------|
| **Memory Type** | Short-term checkpointing |
| **Stateless Response** | ❌ "How long was what? Please specify." |
| **Stateful Response** | ✅ "Your last cycling workout on October 17th was 45 minutes long." |
| **Pronoun Resolved** | "it" → "last cycling workout on October 17th" |

---

## 4. Goal-Based Queries (Episodic Memory)

### Query: "Am I on track for my weight goal?"

| Aspect | Details |
|--------|---------|
| **Tool Used (Stateless)** | `get_health_metrics` only |
| **Tool Used (Stateful)** | `get_my_goals` (retrieves from RedisVL) → `get_health_metrics` |
| **Memory Type** | None / Episodic (RedisVL vector search) |
| **Stateless Response** | ❌ "I don't have information about your goals. What is your target weight?" |
| **Stateful Response** | ✅ "Your goal is 125 lbs by December. Current weight: 136.8 lbs. You've lost 8.2 lbs since September - great progress!" |
| **Redis Key** | `episodic:wellness_user:goal:1729962000` |
| **How Retrieved** | LLM calls `get_my_goals` tool autonomously |

---

## 5. Pattern Learning (Procedural Memory)

### Query: "Compare my activity this month vs last month"

| Aspect | Details |
|--------|---------|
| **Tool Used (First Time)** | `get_workout_data` + `get_health_metrics` |
| **Tool Used (After Learning)** | `get_tool_suggestions` (retrieves pattern) → same tools but faster |
| **Memory Type** | None / Procedural (learned workflow) |
| **Stateless Performance** | 2.8s (figures out tools each time) |
| **Stateful Performance (1st)** | 2.8s (same as stateless) |
| **Stateful Performance (2nd+)** | 1.9s (retrieves successful pattern) |
| **Redis Key** | `procedural:pattern:1729962000` |
| **How Retrieved** | LLM calls `get_tool_suggestions` tool if query is similar |

---

## 6. Multi-Turn Reasoning

### Conversation Flow

**Turn 1**: "What was my heart rate during workouts last week?"
**Turn 2**: "How does that compare to this week?"
**Turn 3**: "Is the trend concerning?"

| Agent | Turn 3 Response |
|-------|----------------|
| **Stateless** | ❌ "I need context. What trend are you referring to?" |
| **Stateful** | ✅ "Your average workout heart rate increased from 142 bpm last week to 156 bpm this week. This 10% increase isn't concerning if you intensified your workouts, which your data shows (cycling replaced walking). If intensity didn't change, consider recovery." |

**Memory Used**:
- Short-term: All 3 conversation turns
- Episodic: User's heart rate goals (if set)
- Procedural: Similar comparison queries

---

## 7. Tool Chaining Examples

### Query: "Show me my workout pattern and tell me if I'm improving"

**Stateless Agent**:
1. ❌ Calls `get_workout_data` → lists workouts
2. ❌ Stops (no memory to chain to next tool)
3. Response: "Here are your workouts: [list]. What would you like to know?"

**Stateful Agent**:
1. ✅ Calls `get_workout_data` (pattern analysis)
2. ✅ Sees pattern result, autonomously calls `get_workout_progress` (improvement tracking)
3. ✅ Calls `get_my_goals` (checks if improvement aligns with goals)
4. Response: "You work out most on Fridays (24 workouts). Your frequency increased 50% this month vs last month, which aligns with your goal of 3x/week."

**Key Difference**: Stateful agent chains tools autonomously based on context.
```

---

## Checklist Before Completion

- [ ] All docs renamed to numbered sequence
- [ ] All archived docs moved and updated
- [ ] All new docs created (05, 08, 10, DOCS_INDEX)
- [ ] All docs follow template.md format
- [ ] All cross-references updated
- [ ] README.md documentation section updated
- [ ] Code examples use real paths from codebase
- [ ] Redis key patterns match current implementation
- [ ] Example queries show both stateless and stateful responses

---

## Timeline Estimate

- **Step 1 (Rename)**: 5 minutes
- **Step 2 (Move/Update)**: 2-3 hours (4 docs to update)
- **Step 3 (Create New)**: 3-4 hours (4 new docs)
- **Step 4 (Cross-references)**: 30 minutes
- **Step 5 (Verify)**: 1 hour

**Total**: ~7-9 hours of focused work

---

**Next Action**: Execute Step 1 (Rename existing docs)
