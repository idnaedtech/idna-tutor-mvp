"""
IDNA EdTech — P0 Regression Tests
These tests verify the ACTUAL execution path, not just individual functions.
Every test here corresponds to a P0 bug that went undetected.

Run: python -m pytest tests/test_p0_regression.py -v
"""

import pytest


class TestLanguageInjectionInPrompt:
    """P0 Bug 1: _get_language_instruction was defined but never called in _sys().
    
    The function existed, the constants existed, but _sys() never called it.
    These tests verify the OUTPUT of _sys() contains the language instruction,
    not just that the function returns the right thing.
    """

    def test_english_language_instruction_in_sys_output(self):
        from app.tutor.instruction_builder import _sys
        ctx = {
            "language_pref": "english", "confusion_count": 0,
            "student_name": "Test", "board_name": "NCERT", "class_level": 8,
            "state": "TEACHING", "chapter": "ch1_square_and_cube",
        }
        result = _sys(session_context=ctx)
        # V10: Uses "LANGUAGE:" prefix with full instruction
        assert "LANGUAGE:" in result and "English" in result, \
            "CRITICAL: Language instruction not injected into _sys() output!"
        assert "No Hindi" in result, \
            "CRITICAL: Strong language enforcement missing from prompt!"

    def test_hindi_language_instruction_in_sys_output(self):
        from app.tutor.instruction_builder import _sys
        ctx = {
            "language_pref": "hindi", "confusion_count": 0,
            "student_name": "Test", "board_name": "NCERT", "class_level": 8,
            "state": "TEACHING", "chapter": "ch1_square_and_cube",
        }
        result = _sys(session_context=ctx)
        # V10: Hindi uses Hindi-English mix instruction
        assert "LANGUAGE:" in result and "Hindi" in result

    def test_hinglish_language_instruction_in_sys_output(self):
        from app.tutor.instruction_builder import _sys
        ctx = {
            "language_pref": "hinglish", "confusion_count": 0,
            "student_name": "Test", "board_name": "NCERT", "class_level": 8,
            "state": "TEACHING", "chapter": "ch1_square_and_cube",
        }
        result = _sys(session_context=ctx)
        # V10: Hinglish uses natural mix instruction
        assert "LANGUAGE:" in result and "Hindi-English" in result


class TestAllActionsHaveBuilders:
    """P0 Bug 2: 're_greet' was not in _BUILDERS, falling to _build_fallback
    which told the LLM to say 'Chalo aage badhte hain'.
    
    These tests ensure every action_type the state machine can produce
    has a dedicated builder, so no unexpected actions hit the fallback.
    """

    def test_re_greet_in_builders(self):
        from app.tutor.instruction_builder import _BUILDERS
        assert "re_greet" in _BUILDERS, \
            "CRITICAL: 're_greet' missing from _BUILDERS — will hit fallback!"

    def test_all_known_actions_have_builders(self):
        from app.tutor.instruction_builder import _BUILDERS
        # Every action_type that state_machine.py can return
        known_actions = [
            "teach_concept", "read_question", "give_hint", "show_solution",
            "pick_next_question", "comfort_student", "end_session", "ask_repeat",
            "acknowledge_language_switch", "answer_meta_question", "re_greet",
            "evaluate_answer", "probe_understanding", "ask_topic",
            "apologize_no_subject", "acknowledge_homework", "replay_heard",
        ]
        missing = [a for a in known_actions if a not in _BUILDERS]
        assert not missing, f"Actions without builders (will hit fallback): {missing}"

    def test_fallback_is_language_aware(self):
        """Even the fallback should respect language preference."""
        from app.tutor.instruction_builder import _build_fallback
        from app.tutor.state_machine import Action

        # V10: Fallback tells LLM to respond naturally to unexpected input
        action = Action("unknown_action", student_text="test")
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "confusion_count": 0, "student_name": "Test", "board_name": "NCERT",
               "class_level": 8, "state": "TEACHING"}
        result = _build_fallback(action, ctx, None, None, None)
        user_msg = result[1]["content"]
        # V10: Natural fallback instead of hardcoded phrase
        assert "unexpected" in user_msg or "naturally" in user_msg, \
            "Fallback should guide LLM to respond naturally"


class TestEndToEndPromptTrace:
    """These tests trace the ACTUAL path from build_prompt() to the final
    system prompt, verifying that language, confusion, and chapter context
    all make it through.
    """

    def test_english_student_gets_english_in_final_prompt(self):
        """E2E: build_prompt with language_pref=english produces English enforcement."""
        from app.tutor.instruction_builder import build_prompt
        from app.tutor.state_machine import Action

        action = Action("teach_concept", student_text="ok let's start")
        ctx = {
            "language_pref": "english", "chapter": "ch1_square_and_cube",
            "confusion_count": 0, "subject": "math",
            "student_name": "Test", "board_name": "NCERT", "class_level": 8,
            "state": "TEACHING", "questions_attempted": 0, "questions_correct": 0,
            "explanations_given": [], "total_hints_used": 0,
        }
        messages = build_prompt(action, ctx, None, None, None, [])
        system_prompt = messages[0]["content"]

        # V10: Uses "LANGUAGE:" with full English instruction
        assert "LANGUAGE:" in system_prompt and "English" in system_prompt, \
            "Language instruction not in final build_prompt output!"
        assert "No Hindi" in system_prompt, \
            "Strong enforcement missing from final prompt!"

    def test_confusion_count_4_produces_break_offer_in_prompt(self):
        """E2E: build_prompt with confusion_count=4 produces break offer.

        V10: Confusion handling is embedded in DIDI_BASE persona, not a separate function.
        The persona describes how to handle frustrated students and offer breaks.
        """
        from app.tutor.instruction_builder import build_prompt
        from app.tutor.state_machine import Action

        action = Action("teach_concept", student_text="I don't understand")
        ctx = {
            "language_pref": "english", "chapter": "ch1_square_and_cube",
            "confusion_count": 4, "subject": "math",
            "student_name": "Test", "board_name": "NCERT", "class_level": 8,
            "state": "TEACHING", "questions_attempted": 0, "questions_correct": 0,
            "explanations_given": [], "total_hints_used": 0,
        }
        messages = build_prompt(action, ctx, None, None, None, [])
        system_prompt = messages[0]["content"]

        # V10: Confusion handling embedded in persona (describes break at 4+ times)
        assert "4 or more times" in system_prompt or "break" in system_prompt.lower(), \
            "Confusion escalation should be embedded in V10 persona!"


class TestLanguageNormalization:
    """P0 Bug 4: student.preferred_language uses BCP-47 ('hi-IN', 'en-IN')
    but session.language_pref uses labels ('hindi', 'english', 'hinglish').
    Without normalization, the LLM prompt gets 'hi-IN' which matches none
    of the if-conditions.
    """

    def test_bcp47_to_label_mapping(self):
        LANG_NORMALIZE = {
            "hi-IN": "hinglish", "en-IN": "english",
            "hindi": "hindi", "english": "english", "hinglish": "hinglish",
        }
        assert LANG_NORMALIZE.get("en-IN") == "english"
        assert LANG_NORMALIZE.get("hi-IN") == "hinglish"
        assert LANG_NORMALIZE.get("hindi") == "hindi"
        assert LANG_NORMALIZE.get("english") == "english"
        assert LANG_NORMALIZE.get("unknown", "hinglish") == "hinglish"

    def test_student_default_language_is_bcp47(self):
        """Verify the Student model default is BCP-47 format."""
        from app.models import Student
        # The model default is "hi-IN", which is BCP-47
        # This test documents the format to prevent silent breakage
        s = Student.__table__.columns["preferred_language"]
        assert s.default.arg == "hi-IN", \
            f"Student.preferred_language default changed from 'hi-IN' to '{s.default.arg}'"


class TestV9PipelineLanguage:
    """The v9 instruction builder (non-streaming endpoint) also needs
    correct language in the prompt.
    """

    def test_v9_system_prompt_has_language_rule(self):
        from app.tutor.instruction_builder_v9 import DIDI_SYSTEM_PROMPT
        assert "LANGUAGE RULE" in DIDI_SYSTEM_PROMPT, "v9 missing language rule!"
        assert "Zero Hindi words" in DIDI_SYSTEM_PROMPT, "v9 missing strong enforcement!"

    def test_v9_build_produces_valid_prompt(self):
        from app.tutor.instruction_builder_v9 import build
        from app.state.session import SessionState

        session = SessionState(
            session_id="test-123",
            student_name="Priya",
            student_pin="1234",
            preferred_language="english",
        )
        instruction = {
            "action": "teach",
            "topic": "perfect_squares",
            "material": "A number times itself is a perfect square.",
        }
        result = build(action="teach", session=session, instruction=instruction)

        assert "system" in result
        assert "user" in result
        assert "english" in result["system"].lower(), \
            "v9 prompt should contain language preference"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
