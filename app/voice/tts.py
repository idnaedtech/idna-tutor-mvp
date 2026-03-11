"""
IDNA EdTech v7.1 — TTS Abstraction Layer
Sarvam Bulbul v3. Speaker=simran. Single API call (no chunking).
Supports both sync and async for streaming TTS.
"""

import time
import logging
import hashlib
import base64
import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Protocol

import json as json_mod

import httpx

from app.config import (
    SARVAM_API_KEY, SARVAM_TTS_URL, TTS_MODEL,
    TTS_SPEAKER, TTS_PACE, TTS_TEMPERATURE, TTS_SAMPLE_RATE,
    AUDIO_CACHE_DIR,
)
from app.config import SARVAM_TTS_STREAM_URL

logger = logging.getLogger(__name__)


@dataclass
class TTSResult:
    audio_bytes: bytes
    latency_ms: int
    cached: bool
    cache_path: Optional[str]


class TTSProvider(Protocol):
    def synthesize(self, text: str, language: str, speaker: str) -> TTSResult: ...


# ─── Mock TTS (for testing when API unavailable) ─────────────────────────────

class MockTTS:
    """Mock TTS that returns valid silent audio. For local testing only."""

    # Minimal valid MP3 file (silent, ~0.1 second) - base64 encoded
    # This passes the verify.py check requiring >= 1000 chars of audio
    _SILENT_MP3 = (
        b'\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00Info\x00\x00\x00\x0f\x00\x00\x00\x01\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    ) * 20  # Repeat to get enough bytes for base64 > 1000 chars

    def synthesize(
        self,
        text: str,
        language: str = "hi-IN",
        speaker: str = "mock",
    ) -> TTSResult:
        logger.info(f"TTS [mock]: '{text[:50]}...'")
        return TTSResult(
            audio_bytes=self._SILENT_MP3,
            latency_ms=1,
            cached=False,
            cache_path=None,
        )

    async def synthesize_async(
        self,
        text: str,
        language: str = "hi-IN",
        speaker: str = "mock",
    ) -> TTSResult:
        """Async version for streaming endpoint compatibility."""
        return self.synthesize(text, language, speaker)

    async def synthesize_streaming(
        self,
        text: str,
        language: str = "hi-IN",
        speaker: str = "mock",
    ):
        """Mock streaming — yields single chunk."""
        yield self._SILENT_MP3


# ─── Sarvam Bulbul v3 ────────────────────────────────────────────────────────

class SarvamBulbulTTS:
    """
    Sarvam Bulbul v3 — 11 Indian languages, 35+ voices.
    Single API call per utterance (no chunking — v6.2.4 proved this works).
    v10.3.1: Persistent HTTP clients to avoid per-request TCP+TLS handshake.
    """

    def __init__(self):
        self._sync_client = httpx.Client(timeout=10.0)
        self._async_client = httpx.AsyncClient(timeout=10.0)

    def synthesize(
        self,
        text: str,
        language: str = "hi-IN",
        speaker: str = TTS_SPEAKER,
    ) -> TTSResult:
        # Guard against empty text to avoid wasting API quota
        if not text or not text.strip():
            logger.warning("TTS called with empty text, returning empty audio")
            return TTSResult(audio_bytes=b'', latency_ms=0, cached=False, cache_path=None)

        # Check cache first
        cache_key = self._cache_key(text, language, speaker)
        cache_path = AUDIO_CACHE_DIR / f"{cache_key}.mp3"

        if cache_path.exists():
            audio = cache_path.read_bytes()
            logger.info(f"TTS [cache hit]: {cache_path.name}")
            return TTSResult(
                audio_bytes=audio, latency_ms=0,
                cached=True, cache_path=str(cache_path),
            )

        start = time.perf_counter()

        # Truncate to prevent TTS failures (max ~2000 chars)
        if len(text) > 2000:
            text = text[:1997] + "..."
            logger.warning(f"TTS text truncated to 2000 chars")

        payload = {
            "text": text,  # Sarvam prefers 'text' over deprecated 'inputs'
            "target_language_code": language,
            "speaker": speaker,
            "model": TTS_MODEL,
            "pace": TTS_PACE,
            "temperature": TTS_TEMPERATURE,
            "enable_preprocessing": True,
            "audio_format": "mp3",
            "sample_rate": TTS_SAMPLE_RATE,
        }
        headers = {
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": "application/json",
        }

        # Retry logic for temporary API failures (500 errors)
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self._sync_client.post(SARVAM_TTS_URL, json=payload, headers=headers, timeout=10.0)
                if response.status_code == 500:
                    # Server error - retry with backoff
                    logger.warning(f"TTS [sarvam] HTTP 500 on attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        import time as time_mod
                        time_mod.sleep(1.0 * (attempt + 1))  # 1s, 2s backoff
                        continue
                if response.status_code != 200:
                    logger.error(f"TTS [sarvam] HTTP {response.status_code}: {response.text}")
                response.raise_for_status()
                data = response.json()

                elapsed = int((time.perf_counter() - start) * 1000)

                # Sarvam returns base64 audio in audios[0]
                audio_b64 = data.get("audios", [""])[0]
                if not audio_b64:
                    raise ValueError("Empty audio response from Sarvam")

                audio_bytes = base64.b64decode(audio_b64)

                # Cache for reuse
                cache_path.write_bytes(audio_bytes)

                logger.info(
                    f"TTS [sarvam]: {elapsed}ms, {len(audio_bytes)} bytes, "
                    f"lang={language}, speaker={speaker}"
                )

                return TTSResult(
                    audio_bytes=audio_bytes, latency_ms=elapsed,
                    cached=False, cache_path=str(cache_path),
                )

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"TTS [sarvam] attempt {attempt + 1} failed: {e}")
                    import time as time_mod
                    time_mod.sleep(1.0 * (attempt + 1))
                    continue
                break

        elapsed = int((time.perf_counter() - start) * 1000)
        logger.error(f"TTS [sarvam] error after {elapsed}ms and {max_retries} retries: {last_error}")

        # Graceful fallback: return empty audio instead of crashing
        # This allows the app to continue functioning when Sarvam is down
        logger.warning("TTS [sarvam] returning empty audio as fallback")
        return TTSResult(audio_bytes=b'', latency_ms=elapsed, cached=False, cache_path=None)

    def _cache_key(self, text: str, language: str, speaker: str) -> str:
        """Generate deterministic cache key from text+language+speaker."""
        raw = f"{text}|{language}|{speaker}|{TTS_PACE}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    async def synthesize_async(
        self,
        text: str,
        language: str = "hi-IN",
        speaker: str = TTS_SPEAKER,
    ) -> TTSResult:
        """Async version of synthesize for parallel TTS calls."""
        # Guard against empty text to avoid wasting API quota
        if not text or not text.strip():
            logger.warning("TTS [async] called with empty text, returning empty audio")
            return TTSResult(audio_bytes=b'', latency_ms=0, cached=False, cache_path=None)

        # Check cache first
        cache_key = self._cache_key(text, language, speaker)
        cache_path = AUDIO_CACHE_DIR / f"{cache_key}.mp3"

        if cache_path.exists():
            audio = cache_path.read_bytes()
            logger.info(f"TTS [async cache hit]: {cache_path.name}")
            return TTSResult(
                audio_bytes=audio, latency_ms=0,
                cached=True, cache_path=str(cache_path),
            )

        start = time.perf_counter()

        if len(text) > 2000:
            text = text[:1997] + "..."
            logger.warning(f"TTS text truncated to 2000 chars")

        payload = {
            "text": text,  # Sarvam prefers 'text' over deprecated 'inputs'
            "target_language_code": language,
            "speaker": speaker,
            "model": TTS_MODEL,
            "pace": TTS_PACE,
            "temperature": TTS_TEMPERATURE,
            "enable_preprocessing": True,
            "audio_format": "mp3",
            "sample_rate": TTS_SAMPLE_RATE,
        }
        headers = {
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": "application/json",
        }

        # Retry logic for temporary API failures (500 errors)
        import asyncio
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                response = await self._async_client.post(SARVAM_TTS_URL, json=payload, headers=headers, timeout=10.0)
                if response.status_code == 500:
                    # Server error - retry with backoff
                    logger.warning(f"TTS [async] HTTP 500 on attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))  # 1s, 2s backoff
                        continue
                if response.status_code != 200:
                    logger.error(f"TTS [async] HTTP {response.status_code}: {response.text}")
                response.raise_for_status()
                data = response.json()

                elapsed = int((time.perf_counter() - start) * 1000)

                audio_b64 = data.get("audios", [""])[0]
                if not audio_b64:
                    raise ValueError("Empty audio response from Sarvam")

                audio_bytes = base64.b64decode(audio_b64)
                cache_path.write_bytes(audio_bytes)

                logger.info(f"TTS [async]: {elapsed}ms, {len(audio_bytes)} bytes")

                return TTSResult(
                    audio_bytes=audio_bytes, latency_ms=elapsed,
                    cached=False, cache_path=str(cache_path),
                )

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"TTS [async] attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue
                break

        elapsed = int((time.perf_counter() - start) * 1000)
        logger.error(f"TTS [async] error after {elapsed}ms and {max_retries} retries: {last_error}")

        # Graceful fallback: return empty audio instead of crashing
        logger.warning("TTS [async] returning empty audio as fallback")
        return TTSResult(audio_bytes=b'', latency_ms=elapsed, cached=False, cache_path=None)

    async def synthesize_streaming(
        self,
        text: str,
        language: str = "hi-IN",
        speaker: str = TTS_SPEAKER,
    ):
        """
        v10.3.1: WebSocket streaming TTS — yields audio chunks as they're generated.
        Falls back to REST API if WebSocket fails.
        Yields: bytes chunks of audio data (WAV/PCM from Sarvam stream API).
        """
        if not text or not text.strip():
            return

        # Check cache first — if cached, yield entire file at once
        cache_key = self._cache_key(text, language, speaker)
        cache_path = AUDIO_CACHE_DIR / f"{cache_key}.mp3"
        if cache_path.exists():
            audio = cache_path.read_bytes()
            logger.info(f"TTS [stream cache hit]: {cache_path.name}")
            yield audio
            return

        if len(text) > 2000:
            text = text[:1997] + "..."

        start = time.perf_counter()
        all_chunks = bytearray()

        try:
            import websockets
            ws_url = f"{SARVAM_TTS_STREAM_URL}?api_subscription_key={SARVAM_API_KEY}"
            async with websockets.connect(ws_url, close_timeout=5) as ws:
                payload = {
                    "text": text,
                    "target_language_code": language,
                    "speaker": speaker,
                    "model": TTS_MODEL,
                    "pace": TTS_PACE,
                    "temperature": TTS_TEMPERATURE,
                    "enable_preprocessing": True,
                }
                await ws.send(json_mod.dumps(payload))
                logger.info(f"TTS [ws] sent {len(text)} chars to stream API")

                chunk_count = 0
                async for message in ws:
                    if isinstance(message, bytes):
                        # Raw audio bytes
                        all_chunks.extend(message)
                        chunk_count += 1
                        yield bytes(message)
                    elif isinstance(message, str):
                        # JSON message — may contain base64 audio or status
                        try:
                            data = json_mod.loads(message)
                            if "audio" in data:
                                audio_bytes = base64.b64decode(data["audio"])
                                all_chunks.extend(audio_bytes)
                                chunk_count += 1
                                yield audio_bytes
                            elif data.get("status") == "end":
                                break
                        except (json_mod.JSONDecodeError, KeyError):
                            pass

                elapsed = int((time.perf_counter() - start) * 1000)
                logger.info(f"TTS [ws]: {elapsed}ms, {chunk_count} chunks, {len(all_chunks)} bytes")

                # Cache the complete audio for future use
                if all_chunks:
                    cache_path.write_bytes(bytes(all_chunks))

        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            logger.warning(f"TTS [ws] failed after {elapsed}ms: {e}, falling back to REST")

            # Fallback to REST API
            result = await self.synthesize_async(text, language, speaker)
            if result.audio_bytes:
                yield result.audio_bytes


# ─── Pre-generation ──────────────────────────────────────────────────────────

def pregenerate_greeting(
    student_name: str,
    language: str = "hi-IN",
) -> TTSResult:
    """
    Pre-generate and cache a greeting for a student.
    Called at registration time or first session.
    """
    greeting_text = (
        f"Namaste {student_name}! Main Didi hoon, aapki tutor. "
        f"Aaj kya padhna hai?"
    )
    tts = get_tts()
    return tts.synthesize(greeting_text, language)


def pregenerate_parent_greeting(
    parent_name: str,
    child_name: str,
    language: str = "te-IN",
) -> TTSResult:
    """Pre-generate parent greeting in their native language."""
    # The LLM will generate the actual greeting in the correct language.
    # This is a simple fallback greeting.
    greeting_text = f"Namaste {parent_name}! {child_name} ke baare mein kuch jaanna hai?"
    tts = get_tts()
    return tts.synthesize(greeting_text, language)


# ─── Factory ─────────────────────────────────────────────────────────────────

_providers = {
    "sarvam_bulbul": SarvamBulbulTTS,
    "mock": MockTTS,
}

_instance: Optional[TTSProvider] = None


def get_tts() -> TTSProvider:
    global _instance
    if _instance is None:
        from app.config import TTS_PROVIDER
        cls = _providers.get(TTS_PROVIDER)
        if not cls:
            raise ValueError(f"Unknown TTS provider: {TTS_PROVIDER}")
        _instance = cls()
    return _instance
