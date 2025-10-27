# Services Review: Duplication & Semantic Naming

**Date**: 2025-10-24
**Review Scope**: `/backend/src/services/`
**Purpose**: Identify duplication and improve semantic naming for Redis demo clarity

---

## 📊 Current Services Inventory

### Memory-Related Services
1. **`memory_manager.py`** (654 lines) - LEGACY, mixed concerns
2. **`episodic_memory_manager.py`** (451 lines) - NEW, user-specific events ✅
3. **`procedural_memory_manager.py`** (414 lines) - NEW, learned procedures ✅
4. **`semantic_memory_manager.py`** (439 lines) - NEW, general health knowledge ✅

### Chat Services
5. **`redis_chat.py`** (247 lines) - Stateful chat with memory
6. **`stateless_chat.py`** (68 lines) - Baseline chat without memory

### Health Data Services
7. **`redis_apple_health_manager.py`** - CRUD operations
8. **`redis_workout_indexer.py`** - Fast workout indexes

### Infrastructure
9. **`redis_connection.py`** - Connection management
10. **`embedding_cache.py`** - Embedding caching

---

## 🔴 Critical Issues Found

### Issue 1: **MASSIVE DUPLICATION in memory_manager.py**

**Problem**: `memory_manager.py` contains **ALL THREE memory types mixed together**, creating duplication with the new separate managers.

**Duplication Analysis**:

```python
# memory_manager.py (LEGACY)
class MemoryManager:
    # SHORT-TERM MEMORY (lines 118-286)
    async def get_short_term_context(...)  # ✅ UNIQUE - Keep
    async def store_short_term_message(...)  # ✅ UNIQUE - Keep
    async def get_short_term_context_token_aware(...)  # ✅ UNIQUE - Keep

    # LONG-TERM MEMORY (lines 287-512)
    async def _generate_embedding(...)  # ❌ DUPLICATED in all 3 new managers
    async def store_semantic_memory(...)  # ❌ DUPLICATED (was mixed episodic+semantic)
    async def retrieve_semantic_memory(...)  # ❌ DUPLICATED (was mixed)
    async def clear_factual_memory(...)  # ❌ DUPLICATED

    # Index: "semantic_memory_idx" (line 76)
    # Prefix: "memory:semantic:" (line 77)
    # ^ CONFLICTS with new semantic_memory_manager.py
```

vs.

```python
# NEW MANAGERS (properly separated)
episodic_memory_manager.py:
    - Index: "episodic_memory_idx"
    - Prefix: "episodic:"
    - Stores: user preferences, goals, health events

procedural_memory_manager.py:
    - Storage: Redis Hash (not vector index)
    - Prefix: "procedure:"
    - Stores: learned tool sequences

semantic_memory_manager.py:
    - Index: "semantic_knowledge_idx"
    - Prefix: "semantic:"
    - Stores: general health facts
```

---

## 🎯 Recommendations

### Priority 1: Deprecate or Refactor `memory_manager.py`

**Option A: COMPLETE REPLACEMENT (Recommended for Clean Demo)**

1. **Rename `memory_manager.py` → `short_term_memory_manager.py`**
   - Keep ONLY short-term memory methods
   - Remove all long-term/semantic memory code
   - Focus: conversation history (Redis LIST)

2. **Remove duplicate embedding generation**
   - Create shared `embedding_service.py`
   - All managers import from centralized service

3. **Create `memory_coordinator.py`** (on todo list)
   - Orchestrates all 4 memory types:
     - Short-term (conversation)
     - Episodic (user events)
     - Procedural (learned skills)
     - Semantic (general knowledge)

**Option B: LEGACY COMPATIBILITY (If existing code depends on it)**

1. **Keep `memory_manager.py` as FACADE**
   - Delegate to new managers internally
   - Maintain backward compatibility
   - Mark as deprecated

---

## 📝 Proposed Refactoring Plan

### Step 1: Extract Short-Term Memory

```python
# NEW: short_term_memory_manager.py
"""
Short-Term Memory Manager - Conversation history.

Stores recent conversation messages in Redis LIST for:
- Pronoun resolution
- Context continuity
- Follow-up question understanding

Storage:
- Redis LIST: health_chat_session:{session_id}
- TTL: 7 months
- Max messages: 20 (token-aware trimming)
"""

class ShortTermMemoryManager:
    """
    Manages short-term memory: recent conversation history.

    This is the "working memory" for current conversation:
    - Last 10-20 messages
    - Enables pronoun resolution ("it", "that")
    - Provides context for follow-up questions

    Separate from:
    - Episodic (user preferences/goals)
    - Procedural (learned tool sequences)
    - Semantic (general health facts)
    """

    async def get_conversation_context(
        self, user_id: str, session_id: str, limit: int = 10
    ) -> str | None:
        """Get recent conversation history."""

    async def store_message(
        self, user_id: str, session_id: str, role: str, content: str
    ) -> bool:
        """Store message in conversation history."""

    async def get_context_token_aware(
        self, user_id: str, session_id: str, limit: int = 10
    ) -> tuple[str | None, dict]:
        """Get conversation with automatic token trimming."""
```

---

### Step 2: Create Shared Embedding Service

```python
# NEW: embedding_service.py
"""
Embedding Service - Centralized embedding generation.

Provides embedding generation for all memory managers:
- Episodic memory (user events)
- Semantic memory (general facts)
- Uses embedding_cache for performance
"""

class EmbeddingService:
    """Centralized embedding generation service."""

    def __init__(self):
        self.settings = get_settings()
        self.ollama_base_url = self.settings.ollama_base_url
        self.embedding_model = self.settings.embedding_model
        self.embedding_cache = get_embedding_cache(ttl_seconds=3600)

    async def generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding with caching."""
        return await self.embedding_cache.get_or_generate(
            query=text,
            generate_fn=lambda: self._generate_uncached(text)
        )

    async def _generate_uncached(self, text: str) -> list[float] | None:
        """Generate embedding via Ollama."""
        # Implementation from existing managers

# Global instance
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """Get or create global embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
```

Then update all managers to use it:

```python
# episodic_memory_manager.py
from .embedding_service import get_embedding_service

class EpisodicMemoryManager:
    def __init__(self):
        self.embedding_service = get_embedding_service()
        # Remove duplicate _generate_embedding methods

    async def store_episodic_event(...):
        embedding = await self.embedding_service.generate_embedding(combined_text)
```

---

### Step 3: Create Memory Coordinator

```python
# NEW: memory_coordinator.py
"""
Memory Coordinator - Orchestrates all memory systems.

Coordinates 4 types of memory:
1. Short-term: Conversation history (working memory)
2. Episodic: User-specific events (preferences, goals)
3. Procedural: Learned tool sequences (skills)
4. Semantic: General health knowledge (facts)

Based on Redis AI Agent Memory architecture.
"""

from dataclasses import dataclass
from typing import Any

from .short_term_memory_manager import get_short_term_memory_manager
from .episodic_memory_manager import get_episodic_memory_manager
from .procedural_memory_manager import get_procedural_memory_manager
from .semantic_memory_manager import get_semantic_memory_manager


@dataclass
class MemoryContext:
    """Complete memory context from all systems."""
    short_term: str | None = None
    episodic: str | None = None
    procedural: dict | None = None
    semantic: str | None = None

    # Metadata
    episodic_hits: int = 0
    semantic_hits: int = 0
    procedural_confidence: float = 0.0


class MemoryCoordinator:
    """
    Coordinates all memory systems for AI agent.

    Provides unified interface for:
    - Memory retrieval (all types)
    - Memory storage (all types)
    - Memory clearing (all types)
    - Memory statistics (all types)
    """

    def __init__(self):
        self.short_term = get_short_term_memory_manager()
        self.episodic = get_episodic_memory_manager()
        self.procedural = get_procedural_memory_manager()
        self.semantic = get_semantic_memory_manager()

    async def retrieve_all_context(
        self,
        user_id: str,
        session_id: str,
        query: str,
        include_procedural_hint: bool = True
    ) -> MemoryContext:
        """
        Retrieve context from all memory systems.

        Args:
            user_id: User identifier
            session_id: Session identifier
            query: Current query for semantic search
            include_procedural_hint: Whether to suggest tool sequence

        Returns:
            Complete memory context from all systems
        """
        context = MemoryContext()

        # 1. Short-term: Recent conversation
        context.short_term = await self.short_term.get_conversation_context(
            user_id, session_id
        )

        # 2. Episodic: User preferences, goals, events
        episodic_result = await self.episodic.retrieve_episodic_memories(
            user_id, query, top_k=3
        )
        context.episodic = episodic_result.get("context")
        context.episodic_hits = episodic_result.get("hits", 0)

        # 3. Semantic: General health knowledge
        semantic_result = await self.semantic.retrieve_semantic_knowledge(
            query, top_k=3
        )
        context.semantic = semantic_result.get("context")
        context.semantic_hits = semantic_result.get("hits", 0)

        # 4. Procedural: Suggest tool sequence if available
        if include_procedural_hint:
            context.procedural = await self.procedural.suggest_procedure(
                user_id, query
            )
            if context.procedural:
                context.procedural_confidence = context.procedural.get("confidence", 0.0)

        return context

    async def store_interaction(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        assistant_response: str,
        tools_used: list[str] | None = None,
        execution_time_ms: float = 0.0,
        success_score: float = 1.0
    ) -> dict[str, bool]:
        """
        Store interaction in all relevant memory systems.

        Automatically:
        - Stores in short-term (conversation)
        - Stores in episodic (if contains user preferences/goals)
        - Records in procedural (if tools were used)

        Args:
            user_id: User identifier
            session_id: Session identifier
            user_message: User's message
            assistant_response: Agent's response
            tools_used: List of tools called
            execution_time_ms: Total execution time
            success_score: Success rating (0-1)

        Returns:
            Dict indicating which systems stored successfully
        """
        results = {}

        # 1. Short-term: Always store
        results["short_term"] = await self.short_term.store_message(
            user_id, session_id, "user", user_message
        )
        results["short_term"] &= await self.short_term.store_message(
            user_id, session_id, "assistant", assistant_response
        )

        # 2. Episodic: Extract and store user-specific facts
        # TODO: Add fact extraction here (Phase 2)
        results["episodic"] = True  # Placeholder

        # 3. Procedural: Record tool sequence if tools were used
        if tools_used:
            results["procedural"] = await self.procedural.record_procedure(
                user_id=user_id,
                query=user_message,
                tool_sequence=tools_used,
                execution_time_ms=execution_time_ms,
                success_score=success_score
            )
        else:
            results["procedural"] = True  # No tools used, skip

        # 4. Semantic: Not stored per-interaction (pre-populated knowledge base)
        results["semantic"] = True

        return results

    async def get_memory_stats(
        self, user_id: str, session_id: str
    ) -> dict[str, Any]:
        """Get statistics from all memory systems."""
        return {
            "short_term": {
                # Stats from short_term_memory_manager
            },
            "episodic": {
                # Stats from episodic_memory_manager
            },
            "procedural": await self.procedural.get_procedure_stats(user_id),
            "semantic": {
                # General stats from semantic_memory_manager
            }
        }

    async def clear_all_memories(
        self, user_id: str, session_id: str | None = None
    ) -> dict[str, Any]:
        """Clear all memories for user (optionally scoped to session)."""
        # Implementation
        pass


# Global coordinator instance
_memory_coordinator = None

def get_memory_coordinator() -> MemoryCoordinator:
    """Get or create global memory coordinator."""
    global _memory_coordinator
    if _memory_coordinator is None:
        _memory_coordinator = MemoryCoordinator()
    return _memory_coordinator
```

---

## 📋 Semantic Naming Improvements

### Current vs. Proposed Names

| Current Name | Issue | Proposed Name | Rationale |
|-------------|-------|---------------|-----------|
| `memory_manager.py` | Too generic, mixed concerns | `short_term_memory_manager.py` OR delete | Specific to conversation history |
| `redis_chat.py` | Vague | `stateful_chat_service.py` | Emphasizes memory/state |
| `stateless_chat.py` | ✅ Good | Keep as-is | Clear contrast with stateful |
| `redis_apple_health_manager.py` | ✅ Good | Keep as-is | Clear domain |
| `redis_workout_indexer.py` | ✅ Good | Keep as-is | Clear purpose |
| `redis_connection.py` | ✅ Good | Keep as-is | Infrastructure |
| `embedding_cache.py` | ✅ Good | Keep as-is | Clear function |

### NEW Files Needed

| File | Purpose | Priority |
|------|---------|----------|
| `short_term_memory_manager.py` | Conversation history only | 🔴 High |
| `embedding_service.py` | Centralized embedding generation | 🔴 High |
| `memory_coordinator.py` | Orchestrate all 4 memory types | 🔴 High |
| `fact_extractor.py` | Extract facts from conversations | 🟡 Medium |

---

## 🗑️ Files to Delete/Refactor

### Option 1: Clean Break (Recommended)
- ❌ **DELETE** `memory_manager.py` entirely
- ✅ **CREATE** `short_term_memory_manager.py` (conversation only)
- ✅ **CREATE** `embedding_service.py` (shared embeddings)
- ✅ **CREATE** `memory_coordinator.py` (orchestration)

### Option 2: Backward Compatible
- ⚠️ **KEEP** `memory_manager.py` as deprecated facade
- ✅ **CREATE** new managers as above
- 📝 Add deprecation warnings

---

## 🔧 Implementation Steps

### Phase 1: Extract Shared Services (Day 1)
1. ✅ Create `embedding_service.py`
2. ✅ Refactor episodic/semantic managers to use it
3. ✅ Remove duplicate `_generate_embedding` methods

### Phase 2: Create Coordinators (Day 2)
4. ✅ Create `short_term_memory_manager.py`
5. ✅ Create `memory_coordinator.py`
6. ✅ Update `redis_chat.py` to use coordinator

### Phase 3: Cleanup Legacy (Day 3)
7. ❌ Delete `memory_manager.py` (or deprecate)
8. ✅ Update all imports
9. ✅ Run full test suite

### Phase 4: Documentation (Day 3)
10. ✅ Update WARP.md with new architecture
11. ✅ Update README.md with memory types
12. ✅ Add architecture diagrams

---

## 📊 Code Duplication Analysis

### Embedding Generation (Duplicated 3x)

**Currently in**:
- `episodic_memory_manager.py` (lines 133-161)
- `procedural_memory_manager.py` - NOT needed (uses Redis Hash)
- `semantic_memory_manager.py` (lines 124-152)

**Fix**: Extract to `embedding_service.py` → **Save ~60 lines of duplicate code**

---

### Redis Connection Pattern (Consistent ✅)

All services properly use `RedisConnectionManager`:
```python
with self.redis_manager.get_connection() as redis_client:
    # Operations
```

**Status**: ✅ No duplication, good pattern

---

### Index Initialization Pattern (Similar but distinct)

Each memory manager has similar index setup:
```python
def _initialize_xxx_index(self):
    schema = IndexSchema.from_dict({...})
    self.index = SearchIndex(schema=schema)
    self.index.connect(redis_url)
    self.index.create(overwrite=False)
```

**Status**: ⚠️ Could extract to helper, but schemas differ enough that duplication is acceptable

---

## 🎯 Final Recommendations

### For Redis Demo Clarity

**1. Rename for Semantic Clarity**:
```
services/
├── memory/  (NEW folder)
│   ├── short_term_memory_manager.py    # Conversation history
│   ├── episodic_memory_manager.py       # User events ✅
│   ├── procedural_memory_manager.py     # Learned skills ✅
│   ├── semantic_memory_manager.py       # General facts ✅
│   ├── embedding_service.py             # Shared embeddings
│   └── memory_coordinator.py            # Orchestration
├── chat/  (NEW folder)
│   ├── stateful_chat_service.py         # With memory
│   └── stateless_chat_service.py        # Without memory
└── health/  (NEW folder)
    ├── apple_health_manager.py
    └── workout_indexer.py
```

**2. Delete Legacy**:
- ❌ `memory_manager.py` - Replace with 4 separate managers

**3. Create Missing Pieces**:
- ✅ `embedding_service.py`
- ✅ `short_term_memory_manager.py`
- ✅ `memory_coordinator.py`

---

## 📈 Benefits of Refactoring

1. **Clear Demo**: Each file name explains its purpose
2. **No Duplication**: Shared embedding service
3. **CoALA Compliant**: Episodic/Procedural/Semantic separation
4. **Easy to Explain**: "Here's episodic memory, here's procedural memory"
5. **Maintainable**: Single responsibility per file

---

## ⚠️ Migration Path

### For Existing Code Using `MemoryManager`

```python
# OLD CODE
from .services.memory_manager import get_memory_manager
memory_manager = get_memory_manager()
await memory_manager.get_short_term_context(...)

# NEW CODE
from .services.memory_coordinator import get_memory_coordinator
coordinator = get_memory_coordinator()
context = await coordinator.retrieve_all_context(...)
```

---

**Status**: Ready for implementation. Recommend **Option 1 (Clean Break)** for demo clarity.
