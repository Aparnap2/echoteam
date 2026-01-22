"""Ollama client wrapper with OpenAI SDK compatibility."""

from typing import Optional, AsyncGenerator
from pydantic import BaseModel
from openai import AsyncOpenAI
from app.config import settings


class OllamaClient:
    """Client for interacting with Ollama using OpenAI SDK compatibility."""

    def __init__(
        self,
        base_url: str = settings.ollama_base_url
    ):
        self.base_url = base_url
        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        """Get or create the OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=self.base_url,
                api_key="ollama"  # Ollama doesn't require a real key
            )
        return self._client

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generate text using Ollama.

        Args:
            model: Model name (e.g., 'qwen2.5-coder:3b')
            prompt: User prompt
            system: System prompt
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content or ""

    async def embed(self, model: str, text: str) -> list[float]:
        """Generate embeddings using Ollama.

        Args:
            model: Embedding model name (e.g., 'nomic-embed-text:v1.5')
            text: Text to embed

        Returns:
            List of embedding values
        """
        response = await self.client.embeddings.create(
            model=model,
            input=text
        )
        return response.data[0].embedding

    async def stream(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream text generation using Ollama.

        Args:
            model: Model name
            prompt: User prompt
            system: System prompt

        Yields:
            Text chunks as they are generated
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True
        )

        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def get_model_for_task(self, task_type: str) -> str:
        """Get the appropriate model for a task type.

        Args:
            task_type: Type of task ('coding', 'reasoning', 'embedding', 'general')

        Returns:
            Model name to use
        """
        model_mapping = {
            "coding": settings.ollama_model_coding,
            "reasoning": settings.ollama_model_reasoning,
            "embedding": settings.ollama_model_embedding,
            "general": settings.ollama_model_coding
        }
        return model_mapping.get(task_type, settings.ollama_model_coding)


# Global client instance
ollama_client = OllamaClient()


async def get_ollama_client() -> OllamaClient:
    """Dependency for getting Ollama client."""
    return ollama_client
