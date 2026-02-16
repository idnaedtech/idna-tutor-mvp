"""
IDNA EdTech v7.0 — LLM Abstraction Layer
Swap providers by changing config.LLM_PROVIDER.
Currently: OpenAI GPT-4o.
"""

import time
import logging
from typing import Protocol, Optional
from dataclasses import dataclass

from openai import OpenAI

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
    async def generate(self, messages: list[dict], **kwargs) -> LLMResult: ...


# ─── OpenAI GPT-4o ───────────────────────────────────────────────────────────

class OpenAIGPT4o:
    def __init__(self):
        self._client = OpenAI(api_key=OPENAI_API_KEY)

    def generate(
        self,
        messages: list[dict],
        max_tokens: int = LLM_MAX_TOKENS,
        temperature: float = LLM_TEMPERATURE,
    ) -> LLMResult:
        start = time.perf_counter()
        try:
            response = self._client.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            elapsed = int((time.perf_counter() - start) * 1000)
            text = response.choices[0].message.content.strip()
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
