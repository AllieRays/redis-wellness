"""
RAG Agent Chat API - Stateless vs. Redis Memory Demo.

Demonstrates the power of RedisVL memory through side-by-side comparison:
- Stateless: Pure agent, no memory
- Redis: Full RAG with dual memory system (short-term + long-term semantic)
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.redis_chat import redis_chat_service
from ..services.stateless_chat import stateless_chat_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Health Chat Demo"])


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
    validation: dict[str, Any] = {}
    type: str = "stateless"


class RedisChatResponse(BaseModel):
    """Response model for Redis chat."""

    response: str
    session_id: str
    tools_used: list[dict[str, Any]] = []
    tool_calls_made: int = 0
    memory_stats: dict[str, Any] = {}
    validation: dict[str, Any] = {}
    type: str = "redis_with_memory"


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
async def stateless_chat(request: StatelessChatRequest):
    """
    Stateless chat endpoint - NO memory system.

    Features:
    - Same LangGraph agent
    - Same tool calling
    - NO conversation history
    - NO semantic memory
    - Each message completely independent

    Use case: Show what happens without RedisVL memory.
    """
    try:
        result = await stateless_chat_service.chat(request.message)

        # Handle both string and dict responses
        if isinstance(result, dict):
            return StatelessChatResponse(
                response=result["response"],
                validation=result.get("validation", {}),
                type="stateless",
            )
        else:
            # Legacy string response
            return StatelessChatResponse(
                response=result, validation={}, type="stateless"
            )

    except Exception as e:
        logger.error(f"Stateless chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/redis", response_model=RedisChatResponse)
async def redis_chat(request: RedisChatRequest):
    """
    Redis chat endpoint - FULL memory system.

    Features:
    - LangGraph agent with tool calling
    - Short-term memory (last 10 messages)
    - Long-term memory (RedisVL semantic search)
    - Conversation persistence (7-month TTL)
    - Context-aware responses

    Use case: Showcase the power of RedisVL memory.
    """
    try:
        result = await redis_chat_service.chat(
            message=request.message, session_id=request.session_id
        )

        return RedisChatResponse(
            response=result["response"],
            session_id=result["session_id"],
            tools_used=result.get("tools_used", []),
            tool_calls_made=result.get("tool_calls_made", 0),
            memory_stats=result.get("memory_stats", {}),
            validation=result.get("validation", {}),
            type=result.get("type", "redis_with_memory"),
        )

    except Exception as e:
        logger.error(f"Redis chat failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========== Memory Management Endpoints ==========


@router.get("/history/{session_id}", response_model=ConversationHistoryResponse)
async def get_conversation_history(session_id: str, limit: int = 10):
    """
    Get conversation history (short-term memory).

    Only available for Redis chat.
    """
    try:
        messages = await redis_chat_service.get_conversation_history(
            session_id=session_id, limit=limit
        )

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

    except Exception as e:
        logger.error(f"History retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/{session_id}", response_model=MemoryStatsResponse)
async def get_memory_stats(session_id: str):
    """
    Get memory statistics for a session.

    Shows:
    - Short-term memory: Message count, TTL
    - Long-term memory: Semantic memory count
    """
    try:
        stats = await redis_chat_service.get_memory_stats(session_id)

        return MemoryStatsResponse(
            short_term=stats.get("short_term", {}),
            long_term=stats.get("long_term", {}),
            user_id=stats.get("user_id", "unknown"),
            session_id=stats.get("session_id", session_id),
        )

    except Exception as e:
        logger.error(f"Memory stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}", response_model=ClearSessionResponse)
async def clear_session(session_id: str):
    """
    Clear all memories for a session.

    Clears both short-term and long-term memories.
    """
    try:
        success = await redis_chat_service.clear_session(session_id)

        return ClearSessionResponse(
            success=success,
            session_id=session_id,
            message=(
                "Session cleared successfully" if success else "Session clear failed"
            ),
        )

    except Exception as e:
        logger.error(f"Session clear failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
                "embedding_model": "all-MiniLM-L6-v2",
                "vector_dimensions": 384,
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
            "embedding": "SentenceTransformers (all-MiniLM-L6-v2)",
            "vector_search": "RedisVL with HNSW index",
            "memory_storage": "Redis with 7-month TTL",
            "backend": "FastAPI + Python 3.11",
            "frontend": "TypeScript + Vite",
        },
    }
