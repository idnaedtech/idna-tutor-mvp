"""
IDNA EdTech v7.5.2 — TTS Pre-Cache (PostgreSQL)

Pre-generates and caches TTS audio for all Content Bank text.
Stores in PostgreSQL instead of ephemeral filesystem.
Survives Railway container restarts.
"""

import hashlib
import asyncio
import logging
from typing import Optional, Callable, Awaitable, Dict, Any

from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger("idna.tts_precache")


def get_cache_key(text: str, lang: str = "hi-IN") -> str:
    """Generate cache key from text + language."""
    content = f"{lang}:{text}"
    return hashlib.md5(content.encode()).hexdigest()


def get_text_hash(text: str) -> str:
    """Generate hash of text for verification."""
    return hashlib.sha256(text.encode()).hexdigest()[:32]


def get_cached_audio_db(db: DBSession, text: str, lang: str = "hi-IN") -> Optional[bytes]:
    """Check if TTS audio is cached in database."""
    from app.models import TTSCache

    key = get_cache_key(text, lang)
    entry = db.query(TTSCache).filter(TTSCache.cache_key == key).first()
    if entry:
        return entry.audio_bytes
    return None


def save_to_cache_db(db: DBSession, text: str, audio_bytes: bytes, lang: str = "hi-IN") -> None:
    """Save TTS audio to database cache."""
    from app.models import TTSCache

    key = get_cache_key(text, lang)
    text_hash = get_text_hash(text)

    # Upsert: update if exists, insert if not
    existing = db.query(TTSCache).filter(TTSCache.cache_key == key).first()
    if existing:
        existing.audio_bytes = audio_bytes
        existing.text_hash = text_hash
    else:
        entry = TTSCache(
            cache_key=key,
            audio_bytes=audio_bytes,
            text_hash=text_hash,
            lang=lang,
        )
        db.add(entry)
    db.commit()
    logger.debug(f"Cached TTS to DB: {key} ({len(audio_bytes)} bytes)")


def get_cache_stats_db(db: DBSession) -> Dict[str, Any]:
    """Get cache statistics from database."""
    from app.models import TTSCache
    from sqlalchemy import func

    count = db.query(func.count(TTSCache.cache_key)).scalar() or 0
    total_size = db.query(func.sum(func.length(TTSCache.audio_bytes))).scalar() or 0

    return {
        "exists": True,
        "files": count,
        "size_mb": round(total_size / (1024 * 1024), 2) if total_size else 0,
    }


async def precache_content_bank(
    content_bank,
    tts_func: Callable[[str, str], Awaitable[bytes]],
    db: DBSession,
    languages: list = None,
) -> Dict[str, int]:
    """
    Pre-generate TTS audio for all content bank text.
    Stores in PostgreSQL for persistence across container restarts.

    v7.5.2: Rate-limited to 2s between calls, skips if already cached.
    """
    from app.models import TTSCache

    if languages is None:
        languages = ["hi-IN"]

    stats = {"total": 0, "cached": 0, "generated": 0, "failed": 0}

    # Get all concepts
    all_concepts = []
    for chapter_key in content_bank._chapters.keys():
        all_concepts.extend(content_bank.get_chapter_concepts(chapter_key))

    # Collect all texts to cache
    texts_to_cache = []
    for concept in all_concepts:
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

            for hint in q.get("hints", []):
                if isinstance(hint, str):
                    for lang in languages:
                        texts_to_cache.append((lang, hint))

            if q.get("full_solution_tts"):
                for lang in languages:
                    texts_to_cache.append((lang, q["full_solution_tts"]))

    # Remove empty texts and duplicates
    texts_to_cache = [(lang, text) for lang, text in texts_to_cache if text and text.strip()]
    unique_texts = list(set(texts_to_cache))
    stats["total"] = len(unique_texts)

    # Check how many are already cached
    for lang, text in unique_texts:
        key = get_cache_key(text, lang)
        if db.query(TTSCache).filter(TTSCache.cache_key == key).first():
            stats["cached"] += 1

    to_generate = stats["total"] - stats["cached"]

    if to_generate == 0:
        logger.info(f"TTS precache: all {stats['total']} entries cached, skipping")
        return stats

    logger.info(f"TTS precache: {stats['cached']} cached, {to_generate} to generate")

    # Generate missing audio with rate limiting
    for lang, text in unique_texts:
        key = get_cache_key(text, lang)

        # Skip if already cached
        if db.query(TTSCache).filter(TTSCache.cache_key == key).first():
            continue

        try:
            audio = await tts_func(text, lang)
            if audio:
                save_to_cache_db(db, text, audio, lang)
                stats["generated"] += 1
            else:
                stats["failed"] += 1

            # v7.5.2: Rate limit 2s to avoid overwhelming Sarvam
            await asyncio.sleep(2.0)
        except Exception as e:
            logger.error(f"TTS precache failed for '{text[:40]}...': {e}")
            stats["failed"] += 1
            # Continue even on failure
            await asyncio.sleep(2.0)

    logger.info(f"TTS precache complete: {stats}")
    return stats


# Legacy functions for backward compatibility (filesystem-based)
# These are no longer used but kept to avoid import errors

def get_cache_stats() -> Dict[str, Any]:
    """Legacy: Get cache stats (deprecated, use get_cache_stats_db)."""
    return {"exists": False, "files": 0, "size_mb": 0}


def get_cached_audio(text: str, lang: str = "hi-IN") -> Optional[bytes]:
    """Legacy: Filesystem cache (deprecated, use get_cached_audio_db)."""
    return None


def save_to_cache(text: str, audio_bytes: bytes, lang: str = "hi-IN") -> None:
    """Legacy: Filesystem cache (deprecated, use save_to_cache_db)."""
    pass
