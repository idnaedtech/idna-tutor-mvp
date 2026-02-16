"""
IDNA EdTech v7.0 — STT Abstraction Layer
Swap providers by changing config.STT_PROVIDER.
Currently: Groq Whisper (whisper-large-v3-turbo).
Future: Sarvam Saarika v2.5 or Saaras v3.
"""

import io
import time
import logging
from dataclasses import dataclass
from typing import Optional, Protocol

import httpx

from app.config import (
    STT_PROVIDER, STT_CONFIDENCE_THRESHOLD, STT_DEFAULT_LANGUAGE,
    GROQ_API_KEY, GROQ_WHISPER_MODEL, GROQ_STT_URL,
    SARVAM_API_KEY, SARVAM_STT_URL,
)

logger = logging.getLogger(__name__)


@dataclass
class STTResult:
    text: str
    confidence: float
    language_detected: str
    latency_ms: int


class STTProvider(Protocol):
    def transcribe(self, audio: bytes, language: str = "hi") -> STTResult: ...


# ─── Groq Whisper ────────────────────────────────────────────────────────────

class GroqWhisperSTT:
    """Groq-hosted Whisper large-v3-turbo. Fast, good for MVP."""

    def transcribe(self, audio: bytes, language: str = None) -> STTResult:
        start = time.perf_counter()
        try:
            # Groq Whisper uses OpenAI-compatible API
            # If language is None/empty, Whisper auto-detects (better for Hinglish)
            files = {
                "file": ("audio.webm", io.BytesIO(audio), "audio/webm"),
                "model": (None, GROQ_WHISPER_MODEL),
                "response_format": (None, "verbose_json"),
            }
            # Only add language if explicitly specified (None = auto-detect)
            if language:
                files["language"] = (None, language)
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

            with httpx.Client(timeout=30.0) as client:
                response = client.post(GROQ_STT_URL, files=files, headers=headers)
                response.raise_for_status()
                data = response.json()

            elapsed = int((time.perf_counter() - start) * 1000)
            text = data.get("text", "").strip()

            # Whisper verbose_json includes segments with avg_logprob
            segments = data.get("segments", [])
            if segments:
                avg_prob = sum(
                    s.get("avg_logprob", -1.0) for s in segments
                ) / len(segments)
                # Convert log probability to 0-1 confidence
                import math
                confidence = math.exp(avg_prob)
            else:
                confidence = 0.5  # Default if no segments

            detected_lang = data.get("language", language)

            logger.info(
                f"STT [groq]: {elapsed}ms, conf={confidence:.2f}, "
                f"lang={detected_lang}, text='{text[:50]}'"
            )

            return STTResult(
                text=text,
                confidence=confidence,
                language_detected=detected_lang,
                latency_ms=elapsed,
            )

        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            logger.error(f"STT [groq] error after {elapsed}ms: {e}")
            raise


# ─── Sarvam Saarika (Phase 2) ────────────────────────────────────────────────

class SarvamSaarikaSTT:
    """Sarvam Saarika v2.5 — 11 Indian languages, code-mixed speech support."""

    def transcribe(self, audio: bytes, language: str = "hi-IN") -> STTResult:
        start = time.perf_counter()
        try:
            # Sarvam REST API for STT
            files = {
                "file": ("audio.webm", io.BytesIO(audio), "audio/webm"),
            }
            data = {
                "model": "saarika:v2.5",
                "language_code": language,
                "with_timestamps": "false",
            }
            headers = {"api-subscription-key": SARVAM_API_KEY}

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    SARVAM_STT_URL, files=files, data=data, headers=headers
                )
                response.raise_for_status()
                result = response.json()

            elapsed = int((time.perf_counter() - start) * 1000)
            text = result.get("transcript", "").strip()
            detected = result.get("language_code", language)

            logger.info(f"STT [saarika]: {elapsed}ms, lang={detected}, text='{text[:50]}'")

            return STTResult(
                text=text,
                confidence=0.7,  # Saarika doesn't return confidence; default
                language_detected=detected,
                latency_ms=elapsed,
            )

        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            logger.error(f"STT [saarika] error after {elapsed}ms: {e}")
            raise


# ─── Sarvam Saaras v3 (Phase 2 alternative — 22 languages) ───────────────────

class SarvamSaarasSTT:
    """Sarvam Saaras v3 — 22 Indian languages, beats GPT-4o on benchmarks."""

    def transcribe(self, audio: bytes, language: str = "hi-IN") -> STTResult:
        start = time.perf_counter()
        try:
            files = {
                "file": ("audio.webm", io.BytesIO(audio), "audio/webm"),
            }
            data = {
                "model": "saaras:v3",
                "language_code": language,
                "mode": "transcribe",
                "with_timestamps": "false",
            }
            headers = {"api-subscription-key": SARVAM_API_KEY}

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    SARVAM_STT_URL, files=files, data=data, headers=headers
                )
                response.raise_for_status()
                result = response.json()

            elapsed = int((time.perf_counter() - start) * 1000)
            text = result.get("transcript", "").strip()
            detected = result.get("language_code", language)

            logger.info(f"STT [saaras]: {elapsed}ms, lang={detected}, text='{text[:50]}'")

            return STTResult(
                text=text,
                confidence=0.8,
                language_detected=detected,
                latency_ms=elapsed,
            )

        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            logger.error(f"STT [saaras] error after {elapsed}ms: {e}")
            raise


# ─── Factory ─────────────────────────────────────────────────────────────────

_providers = {
    "groq_whisper": GroqWhisperSTT,
    "sarvam_saarika": SarvamSaarikaSTT,
    "sarvam_saaras": SarvamSaarasSTT,
}

_instance: Optional[STTProvider] = None


def get_stt() -> STTProvider:
    global _instance
    if _instance is None:
        cls = _providers.get(STT_PROVIDER)
        if not cls:
            raise ValueError(f"Unknown STT provider: {STT_PROVIDER}")
        _instance = cls()
    return _instance


def is_low_confidence(result: STTResult) -> bool:
    """Check if STT result is below confidence threshold."""
    return result.confidence < STT_CONFIDENCE_THRESHOLD
