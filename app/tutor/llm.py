"""
IDNA EdTech v7.1 — LLM Abstraction Layer
Supports both sync and async streaming for sentence-level TTS.
"""

import time
import re
import logging
import asyncio
from typing import Protocol, Optional, AsyncGenerator
from dataclasses import dataclass

from openai import OpenAI, AsyncOpenAI

from app.config import (
    OPENAI_API_KEY, LLM_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE,
    LLM_PROVIDER,
)

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    text: str
    latency_ms: int
    model: str
    usage: dict


class LLMProvider(Protocol):
    def generate(self, messages: list[dict], **kwargs) -> LLMResult: ...


# ─── OpenAI GPT-4o ───────────────────────────────────────────────────────────

class OpenAIGPT4o:
    def __init__(self):
        self._client = OpenAI(api_key=OPENAI_API_KEY)
        self._async_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

    def generate(
        self,
        messages: list[dict],
        max_tokens: int = LLM_MAX_TOKENS,
        temperature: float = LLM_TEMPERATURE,
    ) -> LLMResult:
        """Synchronous generation (existing behavior)."""
        start = time.perf_counter()
        try:
            response = self._client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            elapsed = int((time.perf_counter() - start) * 1000)
            content = response.choices[0].message.content
            text = (content or "").strip()
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
            logger.info(f"LLM response: {elapsed}ms, {usage['total_tokens']} tokens")
            return LLMResult(text=text, latency_ms=elapsed, model=LLM_MODEL, usage=usage)
        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            logger.error(f"LLM error after {elapsed}ms: {e}")
            raise

    async def generate_streaming(
        self,
        messages: list[dict],
        max_tokens: int = LLM_MAX_TOKENS,
        temperature: float = LLM_TEMPERATURE,
    ) -> AsyncGenerator[str, None]:
        """
        Async streaming generation — yields complete sentences.
        Used for sentence-level TTS to reduce perceived latency.
        """
        buffer = ""

        try:
            stream = await self._async_client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                buffer += delta

                # Yield complete sentences
                while True:
                    # Find sentence boundary (. ? ! but not abbreviations)
                    match = self._find_sentence_boundary(buffer)
                    if match:
                        sentence = buffer[:match].strip()
                        buffer = buffer[match:].strip()
                        if sentence:
                            yield sentence
                    else:
                        break

            # Yield remaining buffer
            if buffer.strip():
                yield buffer.strip()

        except Exception as e:
            logger.error(f"LLM streaming error: {e}")
            if buffer.strip():
                yield buffer.strip()

    def _find_sentence_boundary(self, text: str) -> Optional[int]:
        """Find the end of the first complete sentence."""
        # Match sentence-ending punctuation
        # Avoid splitting on: Dr. Mr. Rs. etc.
        for i, char in enumerate(text):
            if char in '.?!।' and i > 0:
                # Check it's not an abbreviation
                before = text[:i].strip()
                if before and len(before) > 2:
                    # Not an abbreviation if previous char is lowercase
                    # or if it's a question/exclamation mark
                    if char in '?!।' or (before[-1].islower() or before[-1].isdigit()):
                        return i + 1
        return None


# ─── Provider Factory ────────────────────────────────────────────────────────

_providers = {
    "openai_gpt4o": OpenAIGPT4o,
}

_instance: Optional[OpenAIGPT4o] = None


def get_llm() -> OpenAIGPT4o:
    """Get the configured LLM provider (singleton)."""
    global _instance
    if _instance is None:
        provider_cls = _providers.get(LLM_PROVIDER)
        if not provider_cls:
            raise ValueError(f"Unknown LLM provider: {LLM_PROVIDER}")
        _instance = provider_cls()
    return _instance
