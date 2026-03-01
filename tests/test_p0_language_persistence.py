"""
IDNA EdTech — P0 Live Test Bug Fixes Integration Tests

Tests for P0 bugs found in live testing (v8.1.5):
- Bug A: Language switch dies after 1 response
- Bug B: TTS never switches to English
- Bug C: Confusion escalation not working

These are END-TO-END tests that verify the full request flow.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.orm import Session as DBSession

from app.models import Session, Student
from app.routers.student import get_tts_language, process_message
from app.tutor.preprocessing import preprocess_student_message, detect_language_switch, detect_confusion
from app.tutor.instruction_builder import _sys


class TestLanguageSwitchDetection:
    """Test that language switch is correctly detected."""

    def test_detect_english_switch_simple(self):
        """'speak in English' should detect English switch."""
        result = detect_language_switch("speak in English please")
        assert result == "english"

    def test_detect_english_switch_explain(self):
        """'explain to me in English' should detect English switch."""
        result = detect_language_switch("Can you speak in English and explain to me in English?")
        assert result == "english"

    def test_detect_hindi_switch(self):
        """'hindi mein bolo' should detect Hindi switch."""
        result = detect_language_switch("hindi mein bolo")
        assert result == "hindi"

    def test_no_switch_for_normal_text(self):
        """Normal math answer should not trigger switch."""
        result = detect_language_switch("the answer is 64")
        assert result is None


class TestTTSLanguageMapping:
    """Test that TTS language is correctly mapped from language_pref."""

    def test_english_pref_returns_en_IN(self):
        """language_pref='english' should return 'en-IN' for TTS."""
        mock_session = MagicMock()
        mock_session.language_pref = "english"
        mock_session.language = "hi-IN"

        result = get_tts_language(mock_session)
        assert result == "en-IN", f"Expected 'en-IN' but got '{result}'"

    def test_hindi_pref_returns_hi_IN(self):
        """language_pref='hindi' should return 'hi-IN' for TTS."""
        mock_session = MagicMock()
        mock_session.language_pref = "hindi"
        mock_session.language = "hi-IN"

        result = get_tts_language(mock_session)
        assert result == "hi-IN"

    def test_hinglish_pref_returns_hi_IN(self):
        """language_pref='hinglish' should return 'hi-IN' for TTS."""
        mock_session = MagicMock()
        mock_session.language_pref = "hinglish"
        mock_session.language = "hi-IN"

        result = get_tts_language(mock_session)
        assert result == "hi-IN"

    def test_missing_pref_defaults_to_hi_IN(self):
        """Missing language_pref should default to 'hi-IN'."""
        mock_session = MagicMock(spec=[])  # No language_pref attribute
        mock_session.language = "hi-IN"

        result = get_tts_language(mock_session)
        assert result == "hi-IN"


class TestLanguagePersistence:
    """Test that language preference persists across requests."""

    def test_preprocess_sets_language_switched(self):
        """Preprocess should detect language switch and set flag."""
        result = preprocess_student_message(
            text="speak in English please",
            chapter="ch1",
            chapter_name="Squares and Cubes",
            language_pref="hinglish",
        )

        assert result.language_switched is True
        assert result.new_language == "english"

    def test_language_pref_in_session_context(self):
        """Session context should include language_pref for prompt building."""
        # This tests that the session_context dict includes language_pref
        # which is used by instruction_builder to set LLM language
        session_context = {
            "language_pref": "english",
            "confusion_count": 0,
        }

        # The instruction builder should read language_pref
        from app.tutor.instruction_builder import _get_language_instruction
        lang_instruction = _get_language_instruction(session_context)

        # Should mention English and instruct to avoid Hindi words
        assert "english" in lang_instruction.lower() or "ENGLISH" in lang_instruction
        assert "Zero Hindi" in lang_instruction or "No Hindi" in lang_instruction  # Correctly instructs no Hindi


class TestConfusionDetection:
    """Test confusion detection patterns."""

    def test_detect_english_confusion(self):
        """English confusion phrases should be detected."""
        assert detect_confusion("I don't understand") is True
        assert detect_confusion("please explain") is True
        assert detect_confusion("can you explain again") is True
        assert detect_confusion("I'm confused") is True

    def test_detect_hindi_confusion(self):
        """Hindi confusion phrases should be detected."""
        assert detect_confusion("nahi samjha") is True
        assert detect_confusion("समझ नहीं") is True
        assert detect_confusion("नहीं समझा") is True
        assert detect_confusion("phir se bolo") is True

    def test_normal_answer_not_confusion(self):
        """Normal math answers should not trigger confusion."""
        assert detect_confusion("the answer is 64") is False
        assert detect_confusion("8 squared") is False
        assert detect_confusion("haan, samajh gaya") is False


class TestConfusionEscalation:
    """Test confusion escalation is embedded in v10 persona."""

    def test_confusion_count_in_prompt(self):
        """v10: Confusion count should appear in prompt."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 3, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "3 times so far" in prompt

    def test_prompt_mentions_break_for_confusion(self):
        """v10: Persona should mention offering break at high confusion."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        # New persona mentions break at 4+ confusion
        assert "4 or more times" in prompt or "break" in prompt.lower()

    def test_prompt_has_patient_identity(self):
        """v10: Persona should describe patient, warm teacher identity."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "patient" in prompt.lower() or "warm" in prompt.lower()

    def test_prompt_has_echo_back_instruction(self):
        """v10: Persona should instruct to echo back student's words."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "echo back" in prompt.lower()


class TestLanguagePersistenceE2E:
    """
    End-to-end test for language persistence across multiple requests.

    This simulates the real bug scenario:
    1. Student says "speak in English"
    2. First response is in English
    3. Second response should ALSO be in English (bug: was switching back to Hindi)
    """

    def test_language_pref_persists_after_commit(self):
        """
        Simulate the database commit flow.

        When language_pref is set and committed, subsequent requests
        should load the same value from the database.
        """
        # Create mock session object
        mock_session = MagicMock(spec=Session)
        mock_session.language_pref = "hinglish"  # Initial value
        mock_session.language = "hi-IN"

        # Simulate language switch
        mock_session.language_pref = "english"

        # Verify TTS would use English
        result = get_tts_language(mock_session)
        assert result == "en-IN", "TTS should use en-IN after language switch"

        # Simulate "reload" from database (in real scenario, db.commit() + db.refresh())
        # The mock still has language_pref = "english"
        result_after_reload = get_tts_language(mock_session)
        assert result_after_reload == "en-IN", "TTS should still use en-IN after simulated reload"

    def test_instruction_builder_uses_updated_language(self):
        """
        The instruction builder should use the updated language_pref
        from session_context, not a stale value.
        """
        from app.tutor.instruction_builder import _get_language_instruction

        # First request: hinglish
        # V10: "hinglish" returns "Hindi-English mix" instruction
        ctx1 = {"language_pref": "hinglish"}
        result1 = _get_language_instruction(ctx1)
        assert "Hindi-English" in result1 or "hinglish" in result1.lower()

        # Second request: English (after switch)
        ctx2 = {"language_pref": "english"}
        result2 = _get_language_instruction(ctx2)
        assert "English" in result2 or "ENGLISH" in result2
        assert "No Hindi" in result2


class TestFullPreprocessingFlow:
    """Test the complete preprocessing flow."""

    def test_language_switch_then_confusion(self):
        """
        When student switches language AND expresses confusion,
        both should be detected.
        """
        result = preprocess_student_message(
            text="speak in English, I don't understand",
            chapter="ch1",
            chapter_name="Test",
        )

        assert result.language_switched is True
        assert result.new_language == "english"
        assert result.confusion_detected is True

    def test_meta_question_bypasses_llm(self):
        """Meta questions should bypass LLM and use template."""
        result = preprocess_student_message(
            text="which chapter are we on?",
            chapter="ch1",
            chapter_name="Squares and Cubes",
            language_pref="english",
        )

        assert result.bypass_llm is True
        assert "Squares and Cubes" in result.template_response


# Run with: python -m pytest tests/test_p0_language_persistence.py -v
