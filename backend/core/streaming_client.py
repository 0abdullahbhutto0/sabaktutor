"""
Streaming LLM Client using OpenAI SDK compatible with OpenRouter
Async version for FastAPI
"""

from typing import AsyncGenerator
from openai import AsyncOpenAI


class StreamingLLMClient:
    """OpenAI SDK-compatible async streaming client for OpenRouter."""

    def __init__(
        self,
        api_key: str,
        model: str = "openrouter/owl-alpha",
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.model = model

    async def stream_complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """Stream completion from OpenRouter."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"[Error: {str(e)}]"

    async def close(self):
        """Close the client."""
        await self._client.aclose()