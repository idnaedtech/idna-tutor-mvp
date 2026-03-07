"""
IDNA EdTech — V10 Persona Tests

Tests for the V10 GPT-4.1 role change:
- Voice box → Teacher persona
- New DIDI_BASE with warm identity
- strings.py with Telugu support
- Content bank as truth

Run: python -m pytest tests/test_v10_persona.py -v
"""

import pytest
from app.tutor.instruction_builder import _sys


class TestV10PersonaContent:
    """Tests for V10 persona — warm teacher identity."""

    def test_new_prompt_no_incorrect_label(self):
        """v10: Prompt should not contain harsh evaluation language."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "ANSWER INCORRECT" not in prompt
        assert "No praise" not in prompt
        assert "patient" in prompt.lower()
        # v10.1: Changed from "echo back" to "respond naturally" - P0 fix 2026-03-07
        assert "respond naturally" in prompt.lower()

    def test_new_prompt_has_exam_awareness(self):
        """v10: Prompt should mention exam patterns."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "exam" in prompt.lower()

    def test_new_prompt_has_content_bank_truth(self):
        """v10: Prompt should instruct LLM to use verified content only."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "ONLY state facts from the teaching content" in prompt

    def test_confusion_count_in_prompt(self):
        """v10: Confusion count should appear in prompt."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 3, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "3 times so far" in prompt

    def test_language_instruction_in_prompt(self):
        """v10: All languages should have LANGUAGE: instruction in prompt."""
        for lang in ["english", "hindi", "hinglish", "telugu"]:
            ctx = {"language_pref": lang, "chapter": "ch6_squares_square_roots",
                   "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
                   "confusion_count": 0, "state": "TEACHING"}
            prompt = _sys(session_context=ctx)
            assert "LANGUAGE:" in prompt, f"Missing LANGUAGE: for {lang}"


class TestV10Strings:
    """Tests for strings.py centralized language strings."""

    def test_strings_telugu_coverage(self):
        """v10: All string keys should have Telugu translations."""
        from app.tutor.strings import STRINGS
        for key in STRINGS:
            assert "telugu" in STRINGS[key], f"Missing Telugu for: {key}"

    def test_strings_get_text_with_params(self):
        """v10: get_text should substitute parameters correctly."""
        from app.tutor.strings import get_text
        r = get_text("warmup_greeting", "english", name="Priya")
        assert "Priya" in r
        assert "Hey" in r

    def test_strings_fallback_to_english(self):
        """v10: Unknown language should fall back to English."""
        from app.tutor.strings import get_text
        r = get_text("warmup_greeting", "unknown_language", name="Test")
        assert "Test" in r  # falls back to English

    def test_strings_missing_key_returns_empty(self):
        """v10: Missing key should return empty string."""
        from app.tutor.strings import get_text
        r = get_text("nonexistent_key", "english")
        assert r == ""

    def test_all_strings_have_four_languages(self):
        """v10: Each string should have english, hindi, hinglish, telugu."""
        from app.tutor.strings import STRINGS
        required_langs = {"english", "hindi", "hinglish", "telugu"}
        for key, translations in STRINGS.items():
            missing = required_langs - set(translations.keys())
            assert not missing, f"Key '{key}' missing: {missing}"


class TestV10WarmIdentity:
    """Tests for warm teacher identity markers."""

    def test_prompt_has_elder_sister_identity(self):
        """v10: Prompt should describe Didi as favorite elder sister."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "elder sister" in prompt.lower() or "favorite" in prompt.lower()

    def test_prompt_has_gentle_wrong_answer_guidance(self):
        """v10: Wrong answers should be handled gently."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        # Should NOT have harsh labels
        assert "ANSWER INCORRECT" not in prompt
        # Should have gentle guidance
        assert "let's think" in prompt.lower() or "differently" in prompt.lower()

    def test_prompt_has_student_choice(self):
        """v10: Prompt should emphasize student choice."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "student drives" in prompt.lower() or "choice" in prompt.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
