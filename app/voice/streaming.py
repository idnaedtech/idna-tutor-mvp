"""
IDNA EdTech v7.5.0 — Sentence-Level TTS Streaming

Streams LLM response sentence-by-sentence, fires TTS for each sentence,
yields audio chunks for sequential playback. Target: first audio at ~3.5s.
"""

import asyncio
import re
import logging
from typing import AsyncGenerator, Tuple, Callable, Awaitable

logger = logging.getLogger("idna.streaming")

# Sentence boundary regex — splits on . ! ? and Hindi danda ।
SENTENCE_SPLIT = re.compile(r'(?<=[.!?।])\s+')


async def stream_llm_sentences(
    messages: list,
    model: str = "gpt-4o",
    api_key: str = "",
    max_tokens: int = 300,
) -> AsyncGenerator[str, None]:
    """
    Stream GPT-4o response and yield complete sentences.

    Uses OpenAI streaming API. Accumulates tokens until a sentence
    boundary is detected, then yields the complete sentence.
    """
    import openai

    client = openai.AsyncOpenAI(api_key=api_key)

    buffer = ""

    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            buffer += delta.content

            # Check if buffer contains complete sentence(s)
            parts = SENTENCE_SPLIT.split(buffer)
            if len(parts) > 1:
                # Yield all complete sentences, keep remainder in buffer
                for sentence in parts[:-1]:
                    sentence = sentence.strip()
                    if sentence:
                        logger.debug(f"Yielding sentence: {sentence[:50]}...")
                        yield sentence
                buffer = parts[-1]

    # Yield any remaining text
    if buffer.strip():
        yield buffer.strip()


async def sentence_to_audio(
    sentence: str,
    tts_func: Callable[[str, str], Awaitable[bytes]],
    lang: str = "hi-IN",
) -> Tuple[str, bytes]:
    """Convert a single sentence to TTS audio."""
    audio_bytes = await tts_func(sentence, lang)
    return sentence, audio_bytes


async def stream_pipeline(
    messages: list,
    tts_func: Callable[[str, str], Awaitable[bytes]],
    lang: str = "hi-IN",
    model: str = "gpt-4o",
    api_key: str = "",
) -> AsyncGenerator[Tuple[str, bytes], None]:
    """
    Full streaming pipeline: LLM sentences -> TTS -> yield audio chunks.

    Each yield is (sentence_text, audio_bytes) ready to send to frontend.
    """
    async for sentence in stream_llm_sentences(messages, model, api_key):
        logger.info(f"Streaming sentence: '{sentence[:50]}...'")
        try:
            text, audio = await sentence_to_audio(sentence, tts_func, lang)
            yield text, audio
        except Exception as e:
            logger.error(f"TTS failed for sentence: {e}")
            # Skip failed sentence, continue with next
            continue
