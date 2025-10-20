"""API routes for the wellness application."""

import json

import httpx
import redis
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.redis_routes import router as redis_router
from src.api.stateless_routes import router as stateless_router
from src.config import get_settings

router = APIRouter()

# Include the new chat routers
router.include_router(stateless_router)
router.include_router(redis_router)


# Pydantic models
class ChatMessage(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str


class HealthCheck(BaseModel):
    status: str
    redis_connected: bool
    ollama_connected: bool


def get_redis_client():
    """Get Redis client."""
    settings = get_settings()
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        decode_responses=True,
    )


async def check_ollama_connection(settings) -> bool:
    """Check if Ollama is accessible."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


async def check_redis_connection(redis_client) -> bool:
    """Check if Redis is accessible."""
    try:
        redis_client.ping()
        return True
    except Exception:
        return False


@router.get("/health/check", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    redis_client = get_redis_client()

    redis_ok = await check_redis_connection(redis_client)
    ollama_ok = await check_ollama_connection(settings)

    status = "healthy" if redis_ok and ollama_ok else "unhealthy"

    return HealthCheck(
        status=status, redis_connected=redis_ok, ollama_connected=ollama_ok
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """Chat endpoint with Ollama integration."""
    settings = get_settings()
    redis_client = get_redis_client()

    try:
        # Store user message in Redis
        conversation_key = f"conversation:{message.session_id}"
        redis_client.lpush(
            conversation_key,
            json.dumps(
                {
                    "role": "user",
                    "content": message.message,
                    "timestamp": str(redis_client.time()[0]),
                }
            ),
        )

        # Get conversation history
        history = redis_client.lrange(conversation_key, 0, 10)  # Last 10 messages
        history.reverse()  # Oldest first

        # Prepare messages for Ollama
        messages = []
        for msg in history:
            msg_data = json.loads(msg)
            messages.append({"role": msg_data["role"], "content": msg_data["content"]})

        # Call Ollama
        async with httpx.AsyncClient(timeout=30.0) as client:
            ollama_response = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": settings.ollama_model,
                    "messages": messages,
                    "stream": False,
                },
            )

            if ollama_response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Ollama error: {ollama_response.status_code}",
                )

            ollama_data = ollama_response.json()
            ai_response = ollama_data.get("message", {}).get("content", "No response")

        # Store AI response in Redis
        redis_client.lpush(
            conversation_key,
            json.dumps(
                {
                    "role": "assistant",
                    "content": ai_response,
                    "timestamp": str(redis_client.time()[0]),
                }
            ),
        )

        return ChatResponse(response=ai_response, session_id=message.session_id)

    except httpx.TimeoutException as e:
        raise HTTPException(status_code=504, detail="Ollama request timeout") from e
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503, detail=f"Ollama connection error: {str(e)}"
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        ) from e
