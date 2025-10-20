"""Pydantic models for chat endpoints."""

from pydantic import BaseModel


class StatelessChatMessage(BaseModel):
    """Request model for stateless chat."""

    message: str


class StatelessChatResponse(BaseModel):
    """Response model for stateless chat."""

    response: str
    type: str = "stateless"


class RedisChatMessage(BaseModel):
    """Request model for Redis-powered chat."""

    message: str
    session_id: str = "default"


class RedisChatResponse(BaseModel):
    """Response model for Redis-powered chat."""

    response: str
    session_id: str
    type: str = "redis"


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history."""

    session_id: str
    messages: list[dict]
    total_messages: int


class SessionInfoResponse(BaseModel):
    """Response model for session information."""

    session_id: str
    message_count: int
    ttl_seconds: int
    exists: bool


class ClearSessionResponse(BaseModel):
    """Response model for clearing a session."""

    success: bool
    session_id: str
    message: str
