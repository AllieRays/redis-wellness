"""
RAG Agent Chat API - Stateless vs. Redis Memory Demo.

Demonstrates the power of RedisVL memory through side-by-side comparison:
- Stateless: Pure agent, no memory
- Redis: Full RAG with dual memory system (short-term + long-term semantic)
"""

import logging
import time
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from ..services.redis_chat import RedisChatService
from ..services.stateless_chat import StatelessChatService
from ..utils.user_config import get_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Health Chat Demo"])

# ========== Service Initialization ==========

# Initialize services (services manage agents internally)
stateless_service = StatelessChatService()
redis_service = RedisChatService()


# ========== Request/Response Models ==========


class StatelessChatRequest(BaseModel):
    """Request model for stateless chat."""

    message: str


class RedisChatRequest(BaseModel):
    """Request model for Redis chat with memory."""

    message: str
    session_id: str = "default"


class StatelessChatResponse(BaseModel):
    """Response model for stateless chat."""

    response: str
    tools_used: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls_made: int = 0
    validation: dict[str, Any] = Field(default_factory=dict)
    type: str = "stateless"
    response_time_ms: float = Field(default=0.0)  # Response latency in milliseconds


class RedisChatResponse(BaseModel):
    """Response model for Redis chat."""

    model_config = ConfigDict(use_enum_values=True)

    response: str
    session_id: str
    tools_used: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls_made: int = 0
    memory_stats: dict[str, Any] = Field(default_factory=dict)
    token_stats: dict[str, Any] = Field(
        default_factory=dict
    )  # Context window usage tracking
    validation: dict[str, Any] = Field(default_factory=dict)
    type: str = "redis_with_memory"
    response_time_ms: float = Field(default=0.0)  # Response latency in milliseconds


class ConversationMessage(BaseModel):
    """Single conversation message."""

    role: str
    content: str
    timestamp: str


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""

    session_id: str
    messages: list[ConversationMessage]
    total_messages: int


class MemoryStatsResponse(BaseModel):
    """Response model for memory statistics."""

    short_term: dict[str, Any]
    long_term: dict[str, Any]
    user_id: str
    session_id: str


class ClearSessionResponse(BaseModel):
    """Response model for session clearing."""

    success: bool
    session_id: str
    message: str


# ========== Chat Endpoints ==========


@router.post("/stateless", response_model=StatelessChatResponse)
async def stateless_chat(request: StatelessChatRequest, http_request: Request):
    """
    Stateless chat endpoint - Uses StatelessChatService.

    Features:
    - Simple tool calling
    - Health data retrieval
    - NO conversation history
    - NO semantic memory
    - Each message completely independent

    Use case: Baseline to show Redis memory value.
    """
    start_time = time.time()

    result = await stateless_service.chat(message=request.message)

    response_time_ms = (time.time() - start_time) * 1000  # Convert to milliseconds

    # Convert tools_used from list of strings to list of dicts
    tools_used = result.get("tools_used", [])
    if tools_used and isinstance(tools_used[0], str):
        tools_used = [{"name": tool} for tool in tools_used]

    return StatelessChatResponse(
        response=result["response"],
        tools_used=tools_used,
        tool_calls_made=result.get("tool_calls_made", 0),
        validation=result.get("validation", {}),
        type="stateless",
        response_time_ms=response_time_ms,
    )


@router.post("/redis")
async def redis_chat(request: RedisChatRequest, http_request: Request):
    """
    Redis chat endpoint - Uses RedisChatService with FULL memory.

    Features:
    - LangGraph workflow with memory
    - Health tool calling
    - Short-term memory (Redis LIST) - conversation history
    - Long-term memory (RedisVL semantic search)
    - Conversation persistence (7-month TTL)
    - Context-aware responses

    Use case: Showcase the power of Redis + RedisVL memory.
    """
    start_time = time.time()

    # Use RedisChatService which handles conversation storage
    result = await redis_service.chat(
        message=request.message, session_id=request.session_id
    )

    response_time_ms = (time.time() - start_time) * 1000  # Convert to milliseconds

    # Convert tools_used from list of strings to list of dicts
    tools_used = result.get("tools_used", [])
    if tools_used and isinstance(tools_used[0], str):
        tools_used = [{"name": tool} for tool in tools_used]

    # Return dict directly to ensure all fields are included
    response_dict = {
        "response": result["response"],
        "session_id": request.session_id,
        "tools_used": tools_used,
        "tool_calls_made": result.get("tool_calls_made", 0),
        "memory_stats": result.get("memory_stats", {}),
        "token_stats": result.get("token_stats", {}),
        "validation": result.get("validation", {}),
        "type": "redis_with_memory",
        "response_time_ms": response_time_ms,
    }
    print(f"\n\n=== RESPONSE DICT: {response_dict}\n\n")
    return response_dict


# ========== Memory Management Endpoints ==========


@router.get("/history/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(session_id: str, limit: int = 10):
    """
    Get conversation history (short-term memory).

    Retrieves recent messages from Redis conversation history.
    Only available for Redis chat (stateless chat has no history).
    """
    # Get conversation history from Redis service
    messages = await redis_service.get_conversation_history(session_id, limit=limit)

    conversation_messages = [
        ConversationMessage(
            role=msg["role"],
            content=msg["content"],
            timestamp=msg.get("timestamp", ""),
        )
        for msg in messages
    ]

    return ConversationHistoryResponse(
        session_id=session_id,
        messages=conversation_messages,
        total_messages=len(conversation_messages),
    )


@router.get("/memory/{session_id}", response_model=MemoryStatsResponse)
async def get_memory_stats(session_id: str):
    """
    Get memory statistics for a session.

    Shows:
    - Short-term memory: Message count, TTL
    - Long-term memory: Semantic memory count
    """
    stats = await redis_service.get_memory_stats(session_id)

    return MemoryStatsResponse(
        short_term=stats.get("short_term", {}),
        long_term=stats.get("long_term", {}),
        user_id=stats.get("user_id", "unknown"),
        session_id=stats.get("session_id", session_id),
    )


@router.get("/tokens/{session_id}")
async def get_token_usage(session_id: str, limit: int = 10):
    """
    Get token usage statistics for a session's context.

    Shows:
    - Current token count
    - Maximum token limit
    - Usage percentage
    - Whether trimming is needed

    Useful for monitoring context window usage and detecting when
    automatic trimming will occur.
    """
    user_id = get_user_id()  # Single user configuration
    (
        context_str,
        token_stats,
    ) = await redis_service.memory_manager.get_short_term_context_token_aware(
        user_id, session_id, limit=limit
    )

    return {
        "session_id": session_id,
        "token_stats": token_stats,
        "status": "over_threshold"
        if token_stats.get("is_over_threshold")
        else "under_threshold",
    }


@router.delete("/session/{session_id}", response_model=ClearSessionResponse)
async def clear_session(session_id: str):
    """
    Clear all memories for a session.

    Clears both short-term and long-term memories.
    """
    success = await redis_service.clear_session(session_id)

    return ClearSessionResponse(
        success=success,
        session_id=session_id,
        message=("Session cleared successfully" if success else "Session clear failed"),
    )


# ========== Demo Information Endpoint ==========


@router.get("/demo/info")
async def get_demo_info():
    """
    Get information about the RAG demo.

    Explains the comparison between stateless and Redis memory.
    """
    return {
        "demo_title": "Apple Health RAG: Stateless vs. RedisVL Memory",
        "demo_purpose": "Showcase the power of RedisVL's dual memory system",
        "stateless_chat": {
            "endpoint": "POST /api/chat/stateless",
            "features": [
                "LangGraph agent with tool calling",
                "5 health data retrieval tools",
                "NO conversation memory",
                "NO semantic memory",
                "Each message independent",
            ],
            "limitations": [
                "Cannot reference previous messages",
                "Cannot understand follow-up questions",
                "No personalization",
                "Repeats information",
            ],
        },
        "redis_chat": {
            "endpoint": "POST /api/chat/redis",
            "features": [
                "LangGraph agent with tool calling",
                "5 health data retrieval tools",
                "Short-term memory (last 10 messages)",
                "Long-term semantic memory (RedisVL)",
                "Context-aware responses",
                "7-month TTL for memories",
            ],
            "memory_system": {
                "short_term": "Recent conversation (Redis LIST)",
                "long_term": "Semantic search (RedisVL HNSW index)",
                "embedding_model": "mxbai-embed-large",
                "vector_dimensions": 1024,
            },
        },
        "comparison_scenarios": [
            {
                "scenario": "Follow-up question",
                "messages": ["What's my BMI?", "Is that good?"],
                "stateless_result": "Doesn't know what 'that' refers to",
                "redis_result": "Knows 'that' = BMI from previous message",
            },
            {
                "scenario": "Repeated question",
                "messages": ["When did I last work out?", "When did I last work out?"],
                "stateless_result": "Same response both times",
                "redis_result": "Can reference previous answer",
            },
            {
                "scenario": "Semantic retrieval",
                "messages": ["My weight goal is 130 lbs", "(later) What's my goal?"],
                "stateless_result": "Doesn't remember goal",
                "redis_result": "Retrieves goal from semantic memory",
            },
        ],
        "endpoints": {
            "stateless_chat": "POST /api/chat/stateless",
            "redis_chat": "POST /api/chat/redis",
            "conversation_history": "GET /api/chat/history/{session_id}",
            "memory_stats": "GET /api/chat/memory/{session_id}",
            "clear_session": "DELETE /api/chat/session/{session_id}",
            "demo_info": "GET /api/chat/demo/info",
        },
        "tech_stack": {
            "agent": "LangGraph with tool calling",
            "llm": "Ollama (local inference)",
            "embedding": "Ollama mxbai-embed-large (1024-dim)",
            "vector_search": "RedisVL with HNSW index",
            "memory_storage": "Redis with 7-month TTL",
            "backend": "FastAPI + Python 3.11",
            "frontend": "TypeScript + Vite",
        },
    }
