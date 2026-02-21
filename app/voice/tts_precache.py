"""
IDNA EdTech v7.5.0 — TTS Pre-Cache

Pre-generates and caches TTS audio for all Content Bank text.
Eliminates TTS wait for known text (questions, hints, solutions).
"""

import hashlib
import asyncio
import logging
from pathlib import Path
from typing import Optional, Callable, Awaitable, Dict, Any

logger = logging.getLogger("idna.tts_precache")

# Cache directory - created at runtime
CACHE_DIR = Path(__file__).parent.parent.parent / "tts_cache"


def get_cache_key(text: str, lang: str = "hi-IN") -> str:
    """Generate cache key from text + language."""
    content = f"{lang}:{text}"
    return hashlib.md5(content.encode()).hexdigest()


def get_cached_audio(text: str, lang: str = "hi-IN") -> Optional[bytes]:
    """Check if TTS audio is already cached."""
    key = get_cache_key(text, lang)
    cache_path = CACHE_DIR / f"{key}.mp3"
    if cache_path.exists():
        return cache_path.read_bytes()
    return None


def save_to_cache(text: str, audio_bytes: bytes, lang: str = "hi-IN") -> None:
    """Save TTS audio to cache."""
    CACHE_DIR.mkdir(exist_ok=True)
    key = get_cache_key(text, lang)
    cache_path = CACHE_DIR / f"{key}.mp3"
    cache_path.write_bytes(audio_bytes)
    logger.debug(f"Cached TTS: {key} ({len(audio_bytes)} bytes)")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    if not CACHE_DIR.exists():
        return {"exists": False, "files": 0, "size_mb": 0}

    files = list(CACHE_DIR.glob("*.mp3"))
    total_size = sum(f.stat().st_size for f in files)
    return {
        "exists": True,
        "files": len(files),
        "size_mb": round(total_size / (1024 * 1024), 2),
    }


async def precache_content_bank(
    content_bank,
    tts_func: Callable[[str, str], Awaitable[bytes]],
    languages: list = None,
) -> Dict[str, int]:
    """
    Pre-generate TTS audio for all content bank text.
    Call this once at startup or deploy.

    Caches: definitions, questions, hints, solutions,
    teaching hooks, misconception corrections.

    Args:
        content_bank: ContentBank instance
        tts_func: Async TTS function (text, lang) -> audio_bytes
        languages: List of languages to cache (default: ["hi-IN"])

    Returns:
        Stats dict with total/cached/generated/failed counts
    """
    if languages is None:
        languages = ["hi-IN"]

    stats = {"total": 0, "cached": 0, "generated": 0, "failed": 0}
    CACHE_DIR.mkdir(exist_ok=True)

    # Get all concepts
    all_concepts = []
    for chapter_key in content_bank._chapters.keys():
        all_concepts.extend(content_bank.get_chapter_concepts(chapter_key))

    logger.info(f"TTS precache starting: {len(all_concepts)} concepts, {languages} languages")

    for concept in all_concepts:
        texts_to_cache = []

        # Definition TTS
        if concept.get("definition_tts"):
            for lang in languages:
                texts_to_cache.append((lang, concept["definition_tts"]))

        # Teaching methodology
        methodology = concept.get("teaching_methodology", {})
        if methodology.get("hook"):
            for lang in languages:
                texts_to_cache.append((lang, methodology["hook"]))
        if methodology.get("analogy"):
            for lang in languages:
                texts_to_cache.append((lang, methodology["analogy"]))

        # Examples
        for ex in concept.get("examples", []):
            if ex.get("solution_tts"):
                for lang in languages:
                    texts_to_cache.append((lang, ex["solution_tts"]))

        # Misconceptions
        for mc in concept.get("misconceptions", []):
            if mc.get("correction_tts"):
                for lang in languages:
                    texts_to_cache.append((lang, mc["correction_tts"]))

        # Questions, hints, solutions
        for q in concept.get("questions", []):
            if q.get("question_tts"):
                for lang in languages:
                    texts_to_cache.append((lang, q["question_tts"]))

            # Hints (may not have _tts suffix, cache anyway)
            for hint in q.get("hints", []):
                if isinstance(hint, str):
                    for lang in languages:
                        texts_to_cache.append((lang, hint))

            if q.get("full_solution_tts"):
                for lang in languages:
                    texts_to_cache.append((lang, q["full_solution_tts"]))

        # Generate missing audio
        for lang, text in texts_to_cache:
            if not text or not text.strip():
                continue

            stats["total"] += 1

            if get_cached_audio(text, lang):
                stats["cached"] += 1
                continue

            try:
                audio = await tts_func(text, lang)
                if audio:
                    save_to_cache(text, audio, lang)
                    stats["generated"] += 1
                else:
                    stats["failed"] += 1
                # Rate limit: don't hammer Sarvam API
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"TTS precache failed for '{text[:40]}...': {e}")
                stats["failed"] += 1

    logger.info(f"TTS precache complete: {stats}")
    return stats


async def get_or_generate_audio(
    text: str,
    lang: str,
    tts_func: Callable[[str, str], Awaitable[bytes]],
) -> Optional[bytes]:
    """
    Get cached audio or generate and cache it.

    Args:
        text: Text to synthesize
        lang: Language code (e.g., "hi-IN")
        tts_func: Async TTS function (text, lang) -> audio_bytes

    Returns:
        Audio bytes or None if failed
    """
    # Check cache first
    cached = get_cached_audio(text, lang)
    if cached:
        logger.debug(f"TTS cache hit: {len(cached)} bytes")
        return cached

    # Generate and cache
    try:
        audio = await tts_func(text, lang)
        if audio:
            save_to_cache(text, audio, lang)
            logger.debug(f"TTS cache miss, generated: {len(audio)} bytes")
        return audio
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        return None
