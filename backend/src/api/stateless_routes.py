"""API routes for stateless chat functionality."""

from fastapi import APIRouter

from src.models.chat import StatelessChatMessage, StatelessChatResponse
from src.services.stateless_chat import StatelessChatService

router = APIRouter(prefix="/chat/stateless", tags=["Stateless Chat"])

# Initialize the stateless chat service
stateless_chat_service = StatelessChatService()


@router.post("/", response_model=StatelessChatResponse)
async def stateless_chat(message: StatelessChatMessage):
    """
    Process a chat message without conversation memory.

    This endpoint provides AI responses without storing or using conversation history.
    Each message is processed independently.
    """
    response = await stateless_chat_service.chat(message.message)

    return StatelessChatResponse(response=response)
