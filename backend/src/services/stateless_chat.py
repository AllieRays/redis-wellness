"""Stateless chat service without conversation memory."""

import httpx
from fastapi import HTTPException

from src.config import get_settings


class StatelessChatService:
    """Chat service that processes messages without storing conversation history."""

    def __init__(self):
        self.settings = get_settings()

    async def chat(self, message: str) -> str:
        """
        Process a chat message without maintaining conversation history.

        Args:
            message: The user's message

        Returns:
            The AI's response

        Raises:
            HTTPException: If there's an error communicating with Ollama
        """
        try:
            # Prepare a single message for Ollama (no conversation history)
            messages = [{"role": "user", "content": message}]

            # Call Ollama
            async with httpx.AsyncClient(timeout=30.0) as client:
                ollama_response = await client.post(
                    f"{self.settings.ollama_base_url}/api/chat",
                    json={
                        "model": self.settings.ollama_model,
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
                ai_response = ollama_data.get("message", {}).get(
                    "content", "No response"
                )

            return ai_response

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
