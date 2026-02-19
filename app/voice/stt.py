"""
IDNA EdTech v7.0.1 — STT Abstraction Layer
Swap providers by changing config.STT_PROVIDER.
Default: Sarvam Saarika v2.5 (handles Hindi-English code-mixing natively).
Fallback: Groq Whisper (set STT_PROVIDER=groq_whisper).
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

import re

# Garbled text patterns: European accented chars that indicate Whisper hallucination
_GARBLE_PATTERN = re.compile(r'[àáâãäåæçèéêëìíîïñòóôõùúûüý]', re.IGNORECASE)


def _is_garbled(text: str) -> bool:
    """Detect garbled/hallucinated transcription."""
    if not text or len(text.strip()) < 3:
        return True
    if _GARBLE_PATTERN.search(text.lower()):
        return True
    return False


@dataclass
class STTResult:
    text: str
    confidence: float
    language_detected: str
    latency_ms: int
    garbled: bool = False  # True if transcription looks like noise/garbage


class STTProvider(Protocol):
    def transcribe(self, audio: bytes, language: str = "hi") -> STTResult: ...


# ─── Groq Whisper ────────────────────────────────────────────────────────────

class GroqWhisperSTT:
    """Groq-hosted Whisper large-v3-turbo. Fast, good for MVP."""

    def transcribe(self, audio: bytes, language: str = None) -> STTResult:
        # Use config default if no language specified
        if language is None:
            language = STT_DEFAULT_LANGUAGE
        start = time.perf_counter()
        try:
            # Groq Whisper uses OpenAI-compatible API
            # Force Hindi to avoid garbage transcriptions for Indian students
            files = {
                "file": ("audio.webm", io.BytesIO(audio), "audio/webm"),
                "model": (None, GROQ_WHISPER_MODEL),
                "response_format": (None, "verbose_json"),
                "language": (None, language or "hi"),  # Always force language
            }
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

            # Garble detection: non-Hindi/English chars or too short
            garbled = _is_garbled(text)
            if garbled:
                confidence = 0.0
                logger.warning(f"STT [groq]: garbled transcription detected: '{text[:50]}'")

            logger.info(
                f"STT [groq]: {elapsed}ms, conf={confidence:.2f}, "
                f"lang={detected_lang}, garbled={garbled}, text='{text[:50]}'"
            )

            return STTResult(
                text=text,
                confidence=confidence,
                language_detected=detected_lang,
                latency_ms=elapsed,
                garbled=garbled,
            )

        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            logger.error(f"STT [groq] error after {elapsed}ms: {e}")
            raise


# ─── Sarvam Saarika (Phase 2) ────────────────────────────────────────────────

class SarvamSaarikaSTT:
    """
    Sarvam Saarika v2.5 — 11 Indian languages, code-mixed speech support.
    NATIVE Hindi-English code-mixing. No phonetic mapping needed.
    """

    def transcribe(self, audio: bytes, language: str = None) -> STTResult:
        # Use config default if no language specified
        if language is None:
            language = STT_DEFAULT_LANGUAGE
        start = time.perf_counter()
        try:
            # Sarvam REST API for STT
            # Handles code-mixed Hindi-English natively
            files = {
                "file": ("audio.webm", io.BytesIO(audio), "audio/webm"),
            }
            data = {
                "model": "saarika:v2.5",
                "language_code": language,
                "with_timestamps": "false",
            }
            headers = {"api-subscription-key": SARVAM_API_KEY}

            logger.info(f"STT [saarika]: sending {len(audio)} bytes to Sarvam")

            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    SARVAM_STT_URL, files=files, data=data, headers=headers
                )
                if response.status_code != 200:
                    logger.error(f"STT [saarika] HTTP {response.status_code}: {response.text}")
                response.raise_for_status()
                result = response.json()

            elapsed = int((time.perf_counter() - start) * 1000)
            text = result.get("transcript", "").strip()
            detected = result.get("language_code", language)

            garbled = _is_garbled(text)
            confidence = 0.0 if garbled else 0.8

            logger.info(f"STT [saarika]: {elapsed}ms, lang={detected}, garbled={garbled}, text='{text[:80]}'")

            return STTResult(
                text=text,
                confidence=confidence,
                language_detected=detected,
                latency_ms=elapsed,
                garbled=garbled,
            )

        except Exception as e:
            elapsed = int((time.perf_counter() - start) * 1000)
            logger.error(f"STT [saarika] error after {elapsed}ms: {e}")
            raise


# ─── Sarvam Saaras v3 (Phase 2 alternative — 22 languages) ───────────────────

class SarvamSaarasSTT:
    """Sarvam Saaras v3 — 22 Indian languages, beats GPT-4o on benchmarks."""

    def transcribe(self, audio: bytes, language: str = None) -> STTResult:
        # Use config default if no language specified
        if language is None:
            language = STT_DEFAULT_LANGUAGE
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

            garbled = _is_garbled(text)
            confidence = 0.0 if garbled else 0.8

            logger.info(f"STT [saaras]: {elapsed}ms, lang={detected}, garbled={garbled}, text='{text[:50]}'")

            return STTResult(
                text=text,
                confidence=confidence,
                language_detected=detected,
                garbled=garbled,
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
