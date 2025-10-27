# Stateful Agent Architecture - Slide Deck Material

## Simplified Vertical Diagrams (For Homepage Side-by-Side)

### Stateless Architecture (Simple)

```mermaid
flowchart TB
    UI1["User Interface"]
    Router1["Intent Router<br/>(Pre-LLM)<br/>Pattern matching"]
    Simple1["Redis<br/>(Simple Queries)"]
    Loop1["Simple Tool Loop<br/>• Qwen 2.5 7B LLM<br/>• Tool calling<br/>• Response synthesis"]
    Tools1["Health Tools<br/>(3 tools)"]
    RedisData1["Redis Health Data Store"]
    Response1["Response to User"]
    Forget["❌ FORGET EVERYTHING"]

    UI1 --> Router1
    Router1 -->|"Simple"| Simple1
    Router1 -->|"Complex"| Loop1
    Simple1 --> RedisData1
    Loop1 --> Tools1
    Tools1 --> RedisData1
    RedisData1 --> Response1
    Response1 --> UI1
    Response1 --> Forget

    style UI1 fill:#fff,stroke:#6c757d,stroke-width:2px
    style Router1 fill:#f8f9fa,stroke:#333,stroke-width:2px
    style Simple1 fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Loop1 fill:#f8f9fa,stroke:#333,stroke-width:2px
    style Tools1 fill:#fff,stroke:#333,stroke-width:2px
    style RedisData1 fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Response1 fill:#f8f9fa,stroke:#333,stroke-width:2px
    style Forget fill:#fff,stroke:#dc3545,stroke-width:2px,color:#dc3545,stroke-dasharray: 5 5
```

### Stateful Architecture (Simple)

```mermaid
flowchart TB
    UI2["User Interface"]
    Router2["Intent Router<br/>(Pre-LLM)<br/>Pattern matching"]
    Simple2["Redis<br/>(Simple Queries)"]
    LangGraph["LangGraph StateGraph<br/>• Qwen 2.5 7B LLM<br/>• Tool calling loop<br/>• Response synthesis<br/>• Checkpointing (automatic)"]
    RedisVL["RedisVL<br/>Episodic + Procedural<br/>Vector Search"]
    Tools2["LLM Tools<br/>(5 total: 3 health + 2 memory)"]
    RedisData["Redis Health Data Store"]
    Response2["Response to User"]
    Store["✅ STORE MEMORY"]

    UI2 --> Router2
    Router2 -->|"Fast path"| Simple2
    Router2 -->|"Complex path"| LangGraph
    Simple2 --> Response2
    LangGraph --> Tools2
    Tools2 --> RedisVL
    Tools2 --> RedisData
    RedisVL --> Response2
    RedisData --> Response2
    Response2 --> UI2
    Response2 --> Store

    style UI2 fill:#fff,stroke:#6c757d,stroke-width:2px
    style Router2 fill:#f8f9fa,stroke:#333,stroke-width:2px
    style Simple2 fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style LangGraph fill:#f8f9fa,stroke:#333,stroke-width:2px
    style RedisVL fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Tools2 fill:#fff,stroke:#333,stroke-width:2px
    style RedisData fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Response2 fill:#f8f9fa,stroke:#333,stroke-width:2px
    style Store fill:#fff,stroke:#28a745,stroke-width:2px,color:#28a745,stroke-dasharray: 5 5
```

---

## Horizontal Architecture Diagram

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'16px', 'edgeLabelBackground':'#f8f9fa'}, 'flowchart': {'rankSpacing': 80, 'nodeSpacing': 40}}}%%
flowchart LR
    UI["User Interface"]
    Router["Intent Router<br/>(Pre-LLM)<br/>Pattern matching"]
    Simple["Redis<br/>(Simple Queries)"]
    Complex["LangGraph StateGraph<br/>• Qwen 2.5 7B LLM<br/>• Tool calling loop<br/>• Response synthesis<br/>• Checkpointing (automatic)"]
    RedisVL["RedisVL<br/>Episodic + Procedural<br/>Vector Search"]
    Tools["LLM Tools<br/>(5 total: 3 health + 2 memory)"]
    RedisData["Redis Health Data"]

    UI --> Router
    Router -->|"Fast path"| Simple
    Router -->|"Complex path"| Complex
    Complex --> Tools
    Tools --> RedisVL
    Tools --> RedisData

    style UI fill:#fff,stroke:#6c757d,stroke-width:2px,color:#000
    style Router fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style Simple fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Complex fill:#f8f9fa,stroke:#333,stroke-width:2px,color:#000
    style RedisVL fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Tools fill:#fff,stroke:#333,stroke-width:2px,color:#000
    style RedisData fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
```

## Horizontal Workflow Diagram

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'16px', 'edgeLabelBackground':'#f8f9fa'}, 'flowchart': {'rankSpacing': 60, 'nodeSpacing': 30}}}%%
flowchart LR
    Query["User Query"]
    Router{"Intent Router"}
    Simple["Simple Query"]
    SimpleRedis["Redis"]
    Load["1. Load<br/>Checkpoint"]
    LLM["2. Qwen 2.5 7B<br/>(decides tools)"]
    ToolDecision{"3. More<br/>tools?"}
    Tools["4. Execute Tools<br/>(5 total)"]
    Reflect["5. Reflect"]
    StoreEpi["6. Store<br/>Episodic"]
    StoreProc["7. Store<br/>Procedural"]
    SaveCheck["8. Save<br/>Checkpoint"]
    RedisVL["RedisVL<br/>(Vector Search)"]
    RedisData["Redis<br/>(Health Data)"]
    Response["Response"]
    
    Query --> Router
    Router -->|"Fast path"| Simple
    Router -->|"Complex path"| Load
    Simple --> SimpleRedis
    SimpleRedis --> Response
    Load --> LLM
    LLM --> ToolDecision
    ToolDecision -->|"Yes"| Tools
    ToolDecision -->|"No"| Reflect
    Tools --> LLM
    Reflect --> StoreEpi
    StoreEpi --> StoreProc
    StoreProc --> SaveCheck
    Tools <--> RedisVL
    Tools <--> RedisData
    SaveCheck --> Response
    
    style Query fill:#fff,stroke:#333,stroke-width:2px
    style Router fill:#fff,stroke:#333,stroke-width:2px
    style Simple fill:#fff,stroke:#333,stroke-width:2px
    style SimpleRedis fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Load fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style LLM fill:#fff,stroke:#333,stroke-width:2px
    style ToolDecision fill:#fff,stroke:#333,stroke-width:2px
    style Tools fill:#fff,stroke:#333,stroke-width:2px
    style Reflect fill:#fff,stroke:#333,stroke-width:2px
    style StoreEpi fill:#fff,stroke:#28a745,stroke-width:2px,color:#28a745
    style StoreProc fill:#fff,stroke:#28a745,stroke-width:2px,color:#28a745
    style SaveCheck fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style RedisVL fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style RedisData fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Response fill:#fff,stroke:#333,stroke-width:2px
```

## Short-Term Memory: Redis Checkpointing (Horizontal)

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'14px'}, 'flowchart': {'rankSpacing': 50, 'nodeSpacing': 30}}}%%
flowchart LR
    User1["Q1: How many workouts?"] --> Agent1["152 workouts"]
    Agent1 --> CP1["💾 Checkpoint:1"]
    CP1 --> User2["Q2: Most common type?"]
    User2 --> Load1["📥 Load"]
    Load1 --> Agent2["Strength Training<br/>40 workouts, 26%"]
    Agent2 --> CP2["💾 Checkpoint:2"]
    
    style User1 fill:#e9ecef,stroke:#6c757d,stroke-width:2px
    style User2 fill:#e9ecef,stroke:#6c757d,stroke-width:2px
    style Agent1 fill:#f8f9fa,stroke:#495057,stroke-width:2px
    style Agent2 fill:#f8f9fa,stroke:#495057,stroke-width:2px
    style CP1 fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style CP2 fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
    style Load1 fill:#dc382d,stroke:#dc382d,stroke-width:2px,color:#fff
```

## Short-Term Memory: Redis Checkpointing (Vertical)

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'15px'}, 'flowchart': {'rankSpacing': 60, 'nodeSpacing': 40}}}%%
flowchart TD
    User1["👤 Turn 1: How many steps<br/>did I take this month?"]
    Agent1["🤖 45,230 steps in October"]
    CP1["💾 Save to Redis<br/>Checkpoint:1"]
    User2["👤 Turn 2: Compare that<br/>to April"]
    Load["📥 Load from Redis<br/>(sees 'October' + '45,230')"]
    Agent2["🤖 April: 38,150 steps<br/>18.5% increase from April"]
    CP2["💾 Save to Redis<br/>Checkpoint:2"]
    
    User1 --> Agent1
    Agent1 --> CP1
    CP1 --> User2
    User2 --> Load
    Load --> Agent2
    Agent2 --> CP2
    
    style User1 fill:#f5f5f5,stroke:#333,stroke-width:2px
    style User2 fill:#f5f5f5,stroke:#333,stroke-width:2px
    style Agent1 fill:#f5f5f5,stroke:#333,stroke-width:2px
    style Agent2 fill:#f5f5f5,stroke:#333,stroke-width:2px
    style CP1 fill:#DC382C,stroke:#DC382C,stroke-width:2px,color:#fff
    style Load fill:#DC382C,stroke:#DC382C,stroke-width:2px,color:#fff
    style CP2 fill:#DC382C,stroke:#DC382C,stroke-width:2px,color:#fff
```

### How It Works
1. **After each turn**: Agent state saved to Redis as checkpoint
2. **Before next turn**: Checkpoint loaded, conversation context restored
3. **Key pattern**: `langgraph:checkpoint:{session_id}:{step}`
4. **Storage**: Redis LIST structure via LangGraph AsyncRedisSaver
5. **TTL**: 7 months (210 days)

### Without Checkpointing (Stateless)
- ❌ User: "What's the most common type?" → Agent: "What are you referring to?"
- ❌ Each turn is isolated, no conversation memory

### With Checkpointing (Stateful)
- ✅ User: "What's the most common type?" → Agent answers using context
- ✅ Agent remembers: previous question, previous response, conversation flow

---

## Key Points for Slides

### Architecture Components
1. **Intent Router**: Pre-LLM pattern matching for simple queries (<100ms)
2. **LangGraph**: Orchestrates LLM → tools → memory → response workflow
3. **Memory Layer**: Redis checkpointing + RedisVL vector search
4. **Tool Layer**: 5 LLM-callable tools (3 health + 2 memory)

### Memory Architecture
- **Short-term** (session): Conversation context for follow-ups
- **Episodic** (permanent): User goals and preferences
- **Procedural** (permanent): Learned tool-calling patterns
- **Semantic** (optional): Health knowledge base

### Performance Metrics
- Intent router: <100ms
- First turn: ~2.8s (0.5s checkpoint + 2.3s LLM)
- Follow-up: ~1.9s (context already loaded)
- Memory overhead: ~170 KB per user

### Comparison: Stateless vs. Stateful

| Without Redis | With Redis + LangGraph |
|---------------|------------------------|
| ❌ Forgets conversation | ✅ Checkpointing loads conversation automatically |
| ❌ Can't answer follow-ups | ✅ Understands "that", "it", "them" references |
| ❌ Doesn't know user goals | ✅ Vector search retrieves goals semantically |
| ❌ Repeats mistakes | ✅ Learns successful tool-calling patterns |

### Technologies Stack
- **Qwen 2.5 7B**: Function-calling LLM (via Ollama)
- **Ollama Embeddings**: mxbai-embed-large (1024-dim vectors)
- **LangGraph**: StateGraph workflow with Redis checkpointing
- **Redis**: Short-term conversation history + structured health data
- **RedisVL**: Vector search for episodic + procedural memory
