"""API routes for Redis-powered chat functionality."""

from fastapi import APIRouter, Path

from src.models.chat import (
    ClearSessionResponse,
    ConversationHistoryResponse,
    RedisChatMessage,
    RedisChatResponse,
    SessionInfoResponse,
)
from src.services.redis_chat import RedisChatService

router = APIRouter(prefix="/chat/redis", tags=["Redis Chat"])

# Initialize the Redis chat service
redis_chat_service = RedisChatService()


@router.post("/", response_model=RedisChatResponse)
async def redis_chat(message: RedisChatMessage):
    """
    Process a chat message with conversation memory using Redis and RedisVL.

    This endpoint maintains conversation history and context across messages
    within the same session.
    """
    response = await redis_chat_service.chat(
        message=message.message, session_id=message.session_id
    )

    return RedisChatResponse(response=response, session_id=message.session_id)


@router.get(
    "/sessions/{session_id}/history", response_model=ConversationHistoryResponse
)
async def get_conversation_history(
    session_id: str = Path(..., description="Session ID to retrieve history for"),
    limit: int = 10,
):
    """
    Retrieve conversation history for a specific session.

    Args:
        session_id: The session identifier
        limit: Maximum number of messages to retrieve (default: 10)
    """
    messages = await redis_chat_service.get_conversation_history(session_id, limit)

    return ConversationHistoryResponse(
        session_id=session_id, messages=messages, total_messages=len(messages)
    )


@router.get("/sessions/{session_id}/info", response_model=SessionInfoResponse)
async def get_session_info(
    session_id: str = Path(..., description="Session ID to get information for"),
):
    """
    Get information about a chat session.

    Returns details like message count, time-to-live, and whether the session exists.
    """
    info = redis_chat_service.get_session_info(session_id)

    return SessionInfoResponse(**info)


@router.delete("/sessions/{session_id}", response_model=ClearSessionResponse)
async def clear_session(session_id: str = Path(..., description="Session ID to clear")):
    """
    Clear all conversation history for a session.

    This permanently deletes all messages in the specified session.
    """
    success = await redis_chat_service.clear_session(session_id)

    return ClearSessionResponse(
        success=success,
        session_id=session_id,
        message="Session cleared successfully"
        if success
        else "Failed to clear session",
    )
