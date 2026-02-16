"""
IDNA EdTech v7.0 — TTS Abstraction Layer
Sarvam Bulbul v3. Speaker=simran. Single API call (no chunking).
Language switches based on who's in session (student vs parent).
"""

import time
import logging
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Protocol

import httpx

from app.config import (
    SARVAM_API_KEY, SARVAM_TTS_URL, TTS_MODEL,
    TTS_SPEAKER, TTS_PACE, TTS_TEMPERATURE, TTS_SAMPLE_RATE,
    AUDIO_CACHE_DIR,
)

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
    """Mock TTS that returns empty audio. For local testing only."""

    def synthesize(
        self,
        text: str,
        language: str = "hi-IN",
        speaker: str = "mock",
    ) -> TTSResult:
        logger.info(f"TTS [mock]: '{text[:50]}...'")
        # Return minimal valid MP3 header (silent audio)
        # This is just a placeholder - browser will play nothing but won't error
        return TTSResult(
            audio_bytes=b'',
            latency_ms=0,
            cached=False,
            cache_path=None,
        )


# ─── Sarvam Bulbul v3 ────────────────────────────────────────────────────────

class SarvamBulbulTTS:
    """
    Sarvam Bulbul v3 — 11 Indian languages, 35+ voices.
    Single API call per utterance (no chunking — v6.2.4 proved this works).
    """

    def synthesize(
        self,
        text: str,
        language: str = "hi-IN",
        speaker: str = TTS_SPEAKER,
    ) -> TTSResult:
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
        try:
            # Truncate to prevent TTS failures (max ~2000 chars)
            if len(text) > 2000:
                text = text[:1997] + "..."
                logger.warning(f"TTS text truncated to 2000 chars")

            payload = {
                "inputs": [text],
                "target_language_code": language,
                "speaker": speaker,
                "pitch": 0,
                "pace": TTS_PACE,
                "loudness": 1.5,
                "speech_sample_rate": TTS_SAMPLE_RATE,
                "enable_preprocessing": True,
                "model": TTS_MODEL,
            }
            headers = {
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            }

            with httpx.Client(timeout=30.0) as client:
                response = client.post(SARVAM_TTS_URL, json=payload, headers=headers)
                if response.status_code != 200:
                    logger.error(f"TTS [sarvam] HTTP {response.status_code}: {response.text}")
                response.raise_for_status()
                data = response.json()

            elapsed = int((time.perf_counter() - start) * 1000)

            # Sarvam returns base64 audio in audios[0]
            import base64
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
            elapsed = int((time.perf_counter() - start) * 1000)
            logger.error(f"TTS [sarvam] error after {elapsed}ms: {e}")
            raise

    def _cache_key(self, text: str, language: str, speaker: str) -> str:
        """Generate deterministic cache key from text+language+speaker."""
        raw = f"{text}|{language}|{speaker}|{TTS_PACE}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


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
