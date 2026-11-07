"""Ollama HTTP client for local LLM inference.

Two modes: generate() blocks until the full answer is ready (good for
programmatic use), stream() yields tokens as they arrive (good for UIs,
where time-to-first-token matters more than total latency).
"""

import json
from collections.abc import AsyncIterator

import httpx

from src.config import get_settings

class OllamaClient:
    def __init__(self, host: str | None = None, model: str | None = None):
        settings = get_settings().ollama
        self.host = host or settings.host
        self.model = model or settings.model
        self.url = f"{self.host}/api/generate"

    async def generate(self, prompt: str, system: str, temperature: float = 0.2) -> str:
        """Generate a response from the LLM for a given prompt."""
        async with httpx.AsyncClient(timeout=12000) as client:
            response = await client.post(
                self.url,
                json={
                    "model": self.model,
                    "system": system,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": temperature}
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["response"]

    async def stream(self, prompt: str, system: str, temperature: float = 0.2) -> AsyncIterator[str]:
        """Stream tokens from the LLM as they arrive."""
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                self.url,
                headers={"Content-Type": "application/json"},
                json={
                    "prompt": prompt,
                    "model": self.model,
                    "system": system,
                    "stream": True,
                    "options": {"temperature": temperature}
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if(chunk.get("response")):
                        yield chunk["response"]
                    if(chunk.get("done")):
                        break
