"""
Tests for v7.5.0 features: streaming, answer evaluator, TTS precache.
"""

import pytest
import re


class TestSentenceSplitter:
    """Test sentence splitting for streaming."""

    def test_english_sentence_split(self):
        """Verify sentence splitting works for English."""
        from app.voice.streaming import SENTENCE_SPLIT

        text = "Hello. How are you? I am fine!"
        parts = SENTENCE_SPLIT.split(text)
        assert len(parts) == 3
        assert "Hello" in parts[0]
        assert "How are you" in parts[1]
        assert "I am fine" in parts[2]

    def test_hindi_danda_split(self):
        """Verify sentence splitting works for Hindi with danda."""
        from app.voice.streaming import SENTENCE_SPLIT

        text = "Yeh ek square hai। Ab agli question suniye।"
        parts = SENTENCE_SPLIT.split(text)
        assert len(parts) == 2

    def test_mixed_punctuation(self):
        """Mixed punctuation splits correctly."""
        from app.voice.streaming import SENTENCE_SPLIT

        text = "Sahi jawab! Ab agle sawaal pe chalte hain. Ready ho?"
        parts = SENTENCE_SPLIT.split(text)
        assert len(parts) == 3


class TestAnswerEvaluator:
    """Test LLM answer evaluation parsing."""

    def test_parse_valid_json(self):
        """Valid JSON parses correctly."""
        from app.tutor.answer_evaluator import parse_eval_response

        response = '{"verdict": "correct", "student_answer_extracted": "7", "feedback_hi": "Sahi jawab!", "feedback_en": "Correct!", "misconception_id": null}'
        result = parse_eval_response(response)
        assert result["verdict"] == "correct"
        assert result["student_answer_extracted"] == "7"

    def test_parse_markdown_wrapped_json(self):
        """JSON wrapped in markdown fences parses correctly."""
        from app.tutor.answer_evaluator import parse_eval_response

        response = """```json
{"verdict": "incorrect", "student_answer_extracted": "8", "feedback_hi": "Galat", "feedback_en": "Wrong"}
```"""
        result = parse_eval_response(response)
        assert result["verdict"] == "incorrect"

    def test_parse_malformed_json(self):
        """Malformed JSON returns unclear verdict."""
        from app.tutor.answer_evaluator import parse_eval_response

        result = parse_eval_response("not json at all")
        assert result["verdict"] == "unclear"
        assert result["feedback_hi"] != ""

    def test_parse_missing_fields(self):
        """Missing fields get defaults."""
        from app.tutor.answer_evaluator import parse_eval_response

        response = '{"verdict": "correct"}'
        result = parse_eval_response(response)
        assert result["verdict"] == "correct"
        assert result["student_answer_extracted"] == ""
        assert result["misconception_id"] is None

    def test_enforce_answer_eval_valid(self):
        """Enforcer passes valid eval JSON."""
        from app.tutor.answer_evaluator import enforce_answer_eval

        response = '{"verdict": "correct", "student_answer_extracted": "7", "feedback_hi": "Sahi!"}'
        passed, msg = enforce_answer_eval(response)
        assert passed is True

    def test_enforce_answer_eval_invalid(self):
        """Enforcer fails invalid JSON."""
        from app.tutor.answer_evaluator import enforce_answer_eval

        passed, msg = enforce_answer_eval("not json")
        assert passed is False
        assert "Invalid JSON" in msg


class TestTTSPrecache:
    """Test TTS precache utilities."""

    def test_cache_key_deterministic(self):
        """Same input produces same cache key."""
        from app.voice.tts_precache import get_cache_key

        key1 = get_cache_key("test text", "hi-IN")
        key2 = get_cache_key("test text", "hi-IN")
        assert key1 == key2

    def test_cache_key_differs_by_language(self):
        """Different language produces different cache key."""
        from app.voice.tts_precache import get_cache_key

        key_hi = get_cache_key("test text", "hi-IN")
        key_en = get_cache_key("test text", "en-IN")
        assert key_hi != key_en

    def test_cache_roundtrip(self, tmp_path, monkeypatch):
        """Save and retrieve from cache."""
        from app.voice import tts_precache

        # Use temp directory for cache
        monkeypatch.setattr(tts_precache, "CACHE_DIR", tmp_path)

        # Save to cache
        tts_precache.save_to_cache("test text", b"fake_audio_bytes", "hi-IN")

        # Retrieve from cache
        cached = tts_precache.get_cached_audio("test text", "hi-IN")
        assert cached == b"fake_audio_bytes"

    def test_cache_miss_returns_none(self, tmp_path, monkeypatch):
        """Cache miss returns None."""
        from app.voice import tts_precache

        monkeypatch.setattr(tts_precache, "CACHE_DIR", tmp_path)

        cached = tts_precache.get_cached_audio("nonexistent text", "hi-IN")
        assert cached is None

    def test_cache_stats(self, tmp_path, monkeypatch):
        """Cache stats reports correctly."""
        from app.voice import tts_precache

        monkeypatch.setattr(tts_precache, "CACHE_DIR", tmp_path)

        # Empty cache
        stats = tts_precache.get_cache_stats()
        assert stats["files"] == 0

        # Add a file
        tts_precache.save_to_cache("test", b"audio", "hi-IN")
        stats = tts_precache.get_cache_stats()
        assert stats["files"] == 1
