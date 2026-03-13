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
    """Tests for v10.1 persona — question-first practice partner."""

    def test_new_prompt_no_incorrect_label(self):
        """v10.1: Prompt should not contain harsh evaluation language."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "ANSWER INCORRECT" not in prompt
        assert "No praise" not in prompt
        assert "patient" in prompt.lower()
        # v10.1: Question-first persona emphasizes warmth
        assert "warm" in prompt.lower() or "encouraging" in prompt.lower()

    def test_new_prompt_question_first(self):
        """v10.1: Prompt should emphasize asking questions, not lecturing."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "ask questions" in prompt.lower() or "don't lecture" in prompt.lower()

    def test_new_prompt_has_content_bank_truth(self):
        """v10.1: Prompt should instruct LLM to use verified content only."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "ONLY use facts from content" in prompt or "never calculate from memory" in prompt.lower()

    def test_short_response_rule(self):
        """v10.1: Prompt should enforce short responses for voice."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "2 sentences" in prompt.lower() or "short" in prompt.lower()

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
    """Tests for warm practice partner identity markers."""

    def test_prompt_has_friendly_identity(self):
        """v10.1: Prompt should describe Didi as friendly practice partner."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "friendly" in prompt.lower() or "practice partner" in prompt.lower()

    def test_prompt_has_gentle_wrong_answer_guidance(self):
        """v10.1: Wrong answers should be handled with hints."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        # Should NOT have harsh labels
        assert "ANSWER INCORRECT" not in prompt
        # Should mention hints for wrong answers
        assert "hint" in prompt.lower() or "wrong" in prompt.lower()

    def test_prompt_handles_frustration(self):
        """v10.1: Prompt should handle frustration warmly."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING"}
        prompt = _sys(session_context=ctx)
        assert "frustration" in prompt.lower() or "tired" in prompt.lower()


class TestV103Acknowledgment:
    """v10.3.0: Tests for interaction quality — acknowledgment rules."""

    def test_didi_base_has_acknowledgment_rules(self):
        """v10.3.0: DIDI_BASE must contain acknowledgment rules."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8}
        prompt = _sys(session_context=ctx)
        assert "ACKNOWLEDGMENT RULES" in prompt
        assert "ALWAYS acknowledge" in prompt
        assert "NEVER ignore" in prompt

    def test_didi_base_has_already_answered_rule(self):
        """v10.3.0: DIDI_BASE must handle 'I already answered' complaints."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8}
        prompt = _sys(session_context=ctx)
        assert "I already answered" in prompt or "I just said that" in prompt

    def test_didi_base_has_adaptive_quantity_rule(self):
        """v10.3.0: DIDI_BASE must handle 'too many' complaints."""
        ctx = {"language_pref": "english", "chapter": "ch6_squares_square_roots",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8}
        prompt = _sys(session_context=ctx)
        assert "too many" in prompt.lower()
        assert "reduce scope" in prompt.lower() or "let's just do" in prompt.lower()

    def test_evaluate_correct_acknowledges_answer(self):
        """v10.3.0: Correct answer prompt must reference student's specific answer."""
        from app.tutor.instruction_builder import build_prompt
        from app.tutor.state_machine import Action
        from app.tutor.answer_checker import Verdict
        v = Verdict(correct=True, student_parsed="625", correct_display="625",
                    verdict="CORRECT", diagnostic="Exact match")
        action = Action("evaluate_answer", verdict=v, student_text="625")
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8}
        msgs = build_prompt(action, ctx, {"target_skill": "perfect_square_identification"})
        user_msg = msgs[-1]["content"]
        assert "625" in user_msg
        assert "CORRECT" in user_msg
        assert "that's right" in user_msg.lower() or "correct" in user_msg.lower()

    def test_evaluate_wrong_acknowledges_answer(self):
        """v10.3.0: Wrong answer prompt must reference student's specific answer."""
        from app.tutor.instruction_builder import build_prompt
        from app.tutor.state_machine import Action
        from app.tutor.answer_checker import Verdict
        v = Verdict(correct=False, student_parsed="600", correct_display="625",
                    verdict="INCORRECT", diagnostic="Close but wrong")
        action = Action("evaluate_answer", verdict=v, student_text="600")
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8}
        msgs = build_prompt(action, ctx, {"target_skill": "perfect_square_identification"})
        user_msg = msgs[-1]["content"]
        assert "600" in user_msg
        assert "not quite" in user_msg.lower()
        assert "Do NOT reveal" in user_msg

    def test_hint_acknowledges_struggle(self):
        """v10.3.0: Hint prompt must acknowledge student's IDK before giving hint."""
        from app.tutor.instruction_builder import _build_give_hint
        from app.tutor.state_machine import Action
        action = Action("give_hint", hint_level=1, student_text="I don't know")
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube"}
        q = {"target_skill": "perfect_square_identification", "hints": ["Think about what number times itself gives this."],
             "question_id": "q1", "id": "q1"}
        msgs = _build_give_hint(action, ctx, q, None, None)
        user_msg = msgs[-1]["content"]
        assert "okay" in user_msg.lower() or "help" in user_msg.lower()

    def test_pick_next_question_explicit_new_question(self):
        """v10.3.0: pick_next_question prompt must emphasize this is a NEW question."""
        from app.tutor.instruction_builder import _build_pick_next_question
        from app.tutor.state_machine import Action
        action = Action("pick_next_question", student_text="625")
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube"}
        q = {"target_skill": "cube_identification", "question_voice": "What is the cube of 5?",
             "id": "q2", "question_id": "q2"}
        msgs = _build_pick_next_question(action, ctx, q, None, None)
        user_msg = msgs[-1]["content"]
        assert "NEXT question" in user_msg or "NEW question" in user_msg


class TestV103MetaQuestionInHintStates:
    """v10.3.0: Meta-questions must be answered in HINT and WAITING_ANSWER states."""

    def test_meta_question_in_waiting_answer(self):
        """v10.3.0: META_QUESTION in WAITING_ANSWER should answer, stay in WAITING_ANSWER."""
        from app.tutor.state_machine import transition
        ctx = {"student_text": "which chapter are we doing?", "current_question_id": "q1",
               "current_hint_level": 0, "current_reteach_count": 0, "questions_attempted": 1}
        new_state, action = transition("WAITING_ANSWER", "META_QUESTION", ctx)
        assert new_state == "WAITING_ANSWER"
        assert action.action_type == "answer_meta_question"
        assert action.extra.get("return_to") == "WAITING_ANSWER"

    def test_meta_question_in_hint_1(self):
        """v10.3.0: META_QUESTION in HINT_1 should answer, stay in HINT_1."""
        from app.tutor.state_machine import transition
        ctx = {"student_text": "is my answer correct?", "current_question_id": "q1",
               "current_hint_level": 1, "current_reteach_count": 0, "questions_attempted": 1}
        new_state, action = transition("HINT_1", "META_QUESTION", ctx)
        assert new_state == "HINT_1"
        assert action.action_type == "answer_meta_question"
        assert action.extra.get("return_to") == "HINT_1"

    def test_meta_question_in_hint_2(self):
        """v10.3.0: META_QUESTION in HINT_2 should answer, stay in HINT_2."""
        from app.tutor.state_machine import transition
        ctx = {"student_text": "what do you mean?", "current_question_id": "q1",
               "current_hint_level": 2, "current_reteach_count": 0, "questions_attempted": 1}
        new_state, action = transition("HINT_2", "META_QUESTION", ctx)
        assert new_state == "HINT_2"
        assert action.action_type == "answer_meta_question"
        assert action.extra.get("return_to") == "HINT_2"

    def test_meta_question_builder_steers_back(self):
        """v10.3.0: Meta-question from hint state should steer back to question."""
        from app.tutor.instruction_builder import _build_answer_meta_question
        from app.tutor.state_machine import Action
        action = Action("answer_meta_question", student_text="which chapter?",
                       extra={"return_to": "HINT_1"})
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8}
        msgs = _build_answer_meta_question(action, ctx, {"target_skill": "perfect_square_identification"}, None, None)
        user_msg = msgs[-1]["content"]
        assert "back to our question" in user_msg.lower() or "wapas" in user_msg.lower()


class TestInlineEval:
    """v10.5.1: Inline eval — combined answer eval + response in single LLM call."""

    def test_inline_eval_prompt_correct_path(self):
        """Inline eval prompt includes [CORRECT] instruction with next question."""
        from app.tutor.instruction_builder import build_inline_eval_prompt
        ctx = {"language_pref": "hinglish", "chapter": "ch1_square_and_cube",
               "student_name": "Priya", "board_name": "NCERT", "class_level": 8,
               "confusion_count": 0, "state": "WAITING_ANSWER", "current_level": 2}
        q = {"question_voice": "5 ka square kitna hai?", "answer": "25",
             "answer_variants": ["twenty five"], "hints": ["5 times 5"],
             "id": "sq_b01", "target_skill": "perfect_square_identification"}
        next_q = {"question_voice": "7 ka square kitna hai?", "id": "sq_b02"}
        msgs, is_end = build_inline_eval_prompt(ctx, q, "25", 0, next_q, 3)
        assert msgs is not None
        user_msg = msgs[-1]["content"]
        assert "[CORRECT]" in user_msg
        assert "[INCORRECT]" in user_msg
        assert "25" in user_msg  # Expected answer
        assert "7 ka square" in user_msg  # Next question
        assert not is_end

    def test_inline_eval_prompt_incorrect_hint(self):
        """Inline eval prompt includes hint for incorrect path."""
        from app.tutor.instruction_builder import build_inline_eval_prompt
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "student_name": "Priya", "board_name": "NCERT", "class_level": 8,
               "confusion_count": 0, "state": "WAITING_ANSWER", "current_level": 2}
        q = {"question_voice": "What is 5 squared?", "answer": "25",
             "answer_variants": [], "hints": ["5 times 5 = ?"],
             "id": "sq_b01", "target_skill": "perfect_square_identification"}
        msgs, _ = build_inline_eval_prompt(ctx, q, "35", 0, None, 3)
        user_msg = msgs[-1]["content"]
        assert "5 times 5" in user_msg  # Hint text

    def test_inline_eval_prompt_show_solution(self):
        """Inline eval prompt shows solution when hint_level >= 2."""
        from app.tutor.instruction_builder import build_inline_eval_prompt
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "student_name": "Priya", "board_name": "NCERT", "class_level": 8,
               "confusion_count": 0, "state": "HINT_2", "current_level": 2}
        q = {"question_voice": "What is 5 squared?", "answer": "25",
             "answer_variants": [], "hints": ["5 times 5"],
             "solution": "5 squared = 5 × 5 = 25",
             "id": "sq_b01", "target_skill": "perfect_square_identification"}
        msgs, _ = build_inline_eval_prompt(ctx, q, "35", 2, None, 3)
        user_msg = msgs[-1]["content"]
        assert "solution" in user_msg.lower() or "25" in user_msg

    def test_inline_eval_prompt_session_end(self):
        """Inline eval prompt handles session end (max questions reached)."""
        from app.tutor.instruction_builder import build_inline_eval_prompt
        from app.config import MAX_QUESTIONS_PER_SESSION
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "student_name": "Priya", "board_name": "NCERT", "class_level": 8,
               "confusion_count": 0, "state": "WAITING_ANSWER", "current_level": 2}
        q = {"question_voice": "What is 5 squared?", "answer": "25",
             "answer_variants": [], "hints": [], "id": "sq_b01",
             "target_skill": "perfect_square_identification"}
        msgs, is_end = build_inline_eval_prompt(
            ctx, q, "25", 0, None, MAX_QUESTIONS_PER_SESSION - 1)
        assert is_end

    def test_inline_eval_prompt_no_next_question(self):
        """Inline eval prompt handles no next question available."""
        from app.tutor.instruction_builder import build_inline_eval_prompt
        ctx = {"language_pref": "hinglish", "chapter": "ch1_square_and_cube",
               "student_name": "Priya", "board_name": "NCERT", "class_level": 8,
               "confusion_count": 0, "state": "WAITING_ANSWER", "current_level": 2}
        q = {"question_voice": "5 ka square?", "answer": "25",
             "answer_variants": [], "hints": [], "id": "sq_b01",
             "target_skill": "perfect_square_identification"}
        msgs, is_end = build_inline_eval_prompt(ctx, q, "25", 0, None, 3)
        assert is_end  # No next question = session end
        user_msg = msgs[-1]["content"]
        assert "done" in user_msg.lower() or "ho gaye" in user_msg.lower()

    def test_inline_eval_prompt_returns_none_without_question(self):
        """Inline eval returns None if no question data provided."""
        from app.tutor.instruction_builder import build_inline_eval_prompt
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube"}
        msgs, is_end = build_inline_eval_prompt(ctx, None, "25", 0, None, 3)
        assert msgs is None

    def test_inline_eval_sys_prompt_has_session_context(self):
        """Inline eval system prompt uses _sys() with session_context (rule #7)."""
        from app.tutor.instruction_builder import build_inline_eval_prompt
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "student_name": "Priya", "board_name": "NCERT", "class_level": 8,
               "confusion_count": 0, "state": "WAITING_ANSWER", "current_level": 3}
        q = {"question_voice": "What is 5 squared?", "answer": "25",
             "answer_variants": [], "hints": [], "id": "sq_b01",
             "target_skill": "perfect_square_identification"}
        msgs, _ = build_inline_eval_prompt(ctx, q, "25", 0, None, 3)
        sys_msg = msgs[0]["content"]
        assert "Priya" in sys_msg
        assert "LANGUAGE:" in sys_msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
