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


class TestV1052GreetingFlow:
    """v10.5.2: Greeting waits for response, then chapter intro, then question."""

    def test_greeting_waits_for_response(self):
        """GREETING + ACK → TEACHING with chapter_intro flag (not straight to question)."""
        from app.tutor.state_machine import transition
        ctx = {"student_text": "accha tha"}
        new_state, action = transition("GREETING", "ACK", ctx)
        assert new_state == "TEACHING"
        assert action.action_type == "teach_concept"
        assert action.extra.get("chapter_intro") is True

    def test_chapter_intro_before_first_question(self):
        """chapter_intro flag produces NCERT-style intro with tile analogy."""
        from app.tutor.instruction_builder import _build_teach_concept
        from app.tutor.state_machine import Action
        action = Action("teach_concept", student_text="accha tha",
                       extra={"chapter_intro": True})
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "student_name": "Priya", "board_name": "NCERT", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING", "current_level": 2}
        q = {"target_skill": "perfect_square_identification", "id": "sq_b01",
             "question_voice": "What is 5 squared?"}
        msgs = _build_teach_concept(action, ctx, q, None, None)
        user_msg = msgs[-1]["content"]
        assert "SAY THIS" in user_msg
        assert "tile" in user_msg.lower()
        assert "Do NOT ask a math question" in user_msg or "Do NOT list squares" in user_msg

    def test_chapter_intro_hinglish(self):
        """Chapter intro in Hinglish uses tile analogy content."""
        from app.tutor.instruction_builder import _build_teach_concept
        from app.tutor.state_machine import Action
        action = Action("teach_concept", student_text="haan",
                       extra={"chapter_intro": True})
        ctx = {"language_pref": "hinglish", "chapter": "ch1_square_and_cube",
               "student_name": "Priya", "board_name": "NCERT", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING", "current_level": 2}
        msgs = _build_teach_concept(action, ctx, None, None, None)
        user_msg = msgs[-1]["content"]
        assert "tiles" in user_msg.lower()
        assert "3 times 3 equals 9" in user_msg

    def test_greeting_no_school_reference(self):
        """Greeting should say 'how was your day' not 'how was school'."""
        from app.tutor.strings import get_text
        for lang in ("english", "hindi", "hinglish", "telugu"):
            greeting = get_text("warmup_greeting", lang, name="Priya")
            assert "school" not in greeting.lower(), f"'{lang}' greeting still mentions school: {greeting}"

    def test_tts_full_text_not_first_sentence(self):
        """v10.5.2: TTS should use full enforced text, not first-sentence-only parallel result.
        Verified by checking that the parallel TTS code was removed from stream_response."""
        import inspect
        from app.routers.student import process_message_stream
        source = inspect.getsource(process_message_stream)
        assert "TTS_FULL" in source, "stream_response should log TTS_FULL"
        assert "TTS_PARALLEL_HIT" not in source, "parallel first-sentence TTS should be removed"


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


class TestV1053Fixes:
    """v10.5.3: Anti-Priya, post-comfort acknowledgment, ACK classification."""

    def test_didi_base_anti_priya_rule(self):
        """DIDI_BASE explicitly forbids using 'Priya' as a name."""
        from app.tutor.instruction_builder import DIDI_BASE
        assert "NEVER use" in DIDI_BASE
        assert "Priya" in DIDI_BASE
        assert "प्रिय" in DIDI_BASE

    def test_student_name_used_not_priya(self):
        """System prompt uses actual student name, not 'Priya' as default."""
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "student_name": "Ananya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING", "current_level": 2}
        prompt = _sys(session_context=ctx)
        assert "Ananya" in prompt
        # The anti-Priya rule should be in the prompt
        assert "NEVER" in prompt

    def test_student_name_default_when_missing(self):
        """When student_name is not in context, default to 'Student', not 'Priya'."""
        ctx = {"language_pref": "hinglish", "chapter": "ch1_square_and_cube",
               "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING", "current_level": 2}
        prompt = _sys(session_context=ctx)
        assert "Student" in prompt

    def test_post_comfort_acknowledgment_english(self):
        """Post-comfort transition includes warm acknowledgment before question."""
        from app.tutor.state_machine import Action
        from app.tutor.instruction_builder import build_prompt
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "student_name": "Priya", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "WAITING_ANSWER", "current_level": 2}
        q = {"question_voice": "What is 5 squared?", "answer": "25",
             "answer_variants": [], "hints": [], "id": "sq_b01",
             "target_skill": "perfect_square_identification"}
        action = Action("read_question", student_text="Will you teach me math?",
                        extra={"post_comfort": True, "question_first": True})
        msgs = build_prompt(action, ctx, question_data=q)
        user_msg = msgs[-1]["content"]
        assert "acknowledge" in user_msg.lower() or "comfort" in user_msg.lower()

    def test_post_comfort_acknowledgment_hindi(self):
        """Post-comfort Hindi response includes acknowledgment."""
        from app.tutor.state_machine import Action
        from app.tutor.instruction_builder import build_prompt
        ctx = {"language_pref": "hinglish", "chapter": "ch1_square_and_cube",
               "student_name": "Ravi", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "WAITING_ANSWER", "current_level": 2}
        q = {"question_voice": "5 ka square kya hai?", "answer": "25",
             "answer_variants": [], "hints": [], "id": "sq_b01",
             "target_skill": "perfect_square_identification"}
        action = Action("read_question",
                        student_text="आप मुझे मैथ्स सिखाएंगे?",
                        extra={"post_comfort": True, "question_first": True})
        msgs = build_prompt(action, ctx, question_data=q)
        user_msg = msgs[-1]["content"]
        assert "bilkul" in user_msg.lower() or "acknowledge" in user_msg.lower()

    def test_ack_classification_okay_after_that(self):
        """'okay after that' should be classified as ACK, not ANSWER."""
        from app.tutor.input_classifier import classify_student_input
        result = classify_student_input("okay after that", current_state="TEACHING")
        assert result == "ACK"

    def test_ack_classification_iske_baad(self):
        """'iske baad' should be classified as ACK."""
        from app.tutor.input_classifier import classify_student_input
        result = classify_student_input("iske baad", current_state="TEACHING")
        assert result == "ACK"

    def test_ack_classification_aage_batao(self):
        """'aage batao' should be classified as ACK."""
        from app.tutor.input_classifier import classify_student_input
        result = classify_student_input("aage batao", current_state="TEACHING")
        assert result == "ACK"

    def test_ack_classification_next_question(self):
        """'next question' should be classified as ACK in TEACHING state."""
        from app.tutor.input_classifier import classify_student_input
        result = classify_student_input("next question", current_state="TEACHING")
        assert result == "ACK"

    def test_ack_not_answer_in_teaching_state(self):
        """'okay after that' in TEACHING state must be ACK, not ANSWER."""
        from app.tutor.input_classifier import classify_student_input
        # In TEACHING state, these should never be ANSWER
        for phrase in ["okay after that", "ok next", "iske baad", "aage batao"]:
            result = classify_student_input(phrase, current_state="TEACHING")
            assert result == "ACK", f"'{phrase}' classified as {result}, expected ACK"

    def test_level_instruction_in_prompt(self):
        """System prompt includes level-appropriate instruction."""
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "student_name": "Test", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING", "current_level": 1}
        prompt = _sys(session_context=ctx)
        assert "Level 1" in prompt
        assert "multiplication" in prompt.lower()

    def test_level_3_instruction(self):
        """Level 3 instruction mentions square roots."""
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "student_name": "Test", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING", "current_level": 3}
        prompt = _sys(session_context=ctx)
        assert "Level 3" in prompt
        assert "square root" in prompt.lower()

    def test_didi_base_direct_question_rule(self):
        """DIDI_BASE includes rule for handling direct questions like 'will you teach me?'."""
        from app.tutor.instruction_builder import DIDI_BASE
        assert "teach me" in DIDI_BASE.lower()


class TestV1054Fixes:
    """v10.5.4: Neutral day descriptions as ACK, Telugu detection, pilot students."""

    def test_theek_tha_classified_as_ack(self):
        """'theek tha' should be ACK in GREETING state, not COMFORT."""
        from app.tutor.input_classifier import classify_student_input
        result = classify_student_input("theek tha", current_state="GREETING")
        assert result == "ACK"

    def test_okay_tha_classified_as_ack(self):
        """'okay tha' should be ACK."""
        from app.tutor.input_classifier import classify_student_input
        result = classify_student_input("okay tha", current_state="GREETING")
        assert result == "ACK"

    def test_accha_tha_classified_as_ack(self):
        """'accha tha' should be ACK."""
        from app.tutor.input_classifier import classify_student_input
        result = classify_student_input("accha tha", current_state="GREETING")
        assert result == "ACK"

    def test_theek_tha_aaj_ka_din_classified_as_ack(self):
        """'theek tha aaj ka din' (my day was fine) should be ACK, not COMFORT."""
        from app.tutor.input_classifier import classify_student_input
        result = classify_student_input("theek tha aaj ka din", current_state="GREETING")
        assert result == "ACK"

    def test_fine_tha_classified_as_ack(self):
        """'fine tha' should be ACK."""
        from app.tutor.input_classifier import classify_student_input
        result = classify_student_input("fine tha", current_state="GREETING")
        assert result == "ACK"

    def test_neutral_day_batch(self):
        """Batch test: neutral day descriptions should all be ACK in GREETING."""
        from app.tutor.input_classifier import classify_student_input
        neutral_phrases = [
            "theek tha", "thik tha", "okay tha", "accha tha", "fine tha",
            "theek tha aaj ka din",
        ]
        for phrase in neutral_phrases:
            result = classify_student_input(phrase, current_state="GREETING")
            assert result == "ACK", f"'{phrase}' classified as {result}, expected ACK"

    def test_telugu_language_detection(self):
        """Telugu indicators should be detected in _detect_language_preference."""
        from app.tutor.input_classifier import _detect_language_preference
        assert _detect_language_preference("telugu lo batao") == "telugu"
        assert _detect_language_preference("telugu mein bolo") == "telugu"

    def test_pilot_students_seeder(self):
        """_seed_pilot_students creates 10 students with PINs 1001-1010."""
        from app.main import _seed_pilot_students
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing
        added = _seed_pilot_students(mock_db)
        assert added == 10
        assert mock_db.add.call_count == 10
        mock_db.commit.assert_called_once()

    def test_pilot_students_idempotent(self):
        """_seed_pilot_students skips existing students."""
        from app.main import _seed_pilot_students
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        # All students already exist
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()
        added = _seed_pilot_students(mock_db)
        assert added == 0
        assert mock_db.add.call_count == 0


class TestV1055CriticalFixes:
    """v10.5.5: 8 critical teaching quality fixes."""

    def test_telugu_instruction_is_strict(self):
        """Telugu LANG_INSTRUCTIONS must require Telugu script, not just 'Telugu-English mix'."""
        from app.tutor.instruction_builder import LANG_INSTRUCTIONS
        telugu = LANG_INSTRUCTIONS["telugu"]
        assert "MUST" in telugu
        assert "Telugu ONLY" in telugu or "Telugu script" in telugu
        assert "NEVER" in telugu or "Do NOT" in telugu

    def test_telugu_instruction_has_example(self):
        """Telugu instruction should include an example sentence."""
        from app.tutor.instruction_builder import LANG_INSTRUCTIONS
        telugu = LANG_INSTRUCTIONS["telugu"]
        assert "బాగా" in telugu or "తెలుగు" in telugu

    def test_hindi_instruction_requires_devanagari(self):
        """Hindi LANG_INSTRUCTIONS must require Devanagari script, not Roman Hindi."""
        from app.tutor.instruction_builder import LANG_INSTRUCTIONS
        hindi = LANG_INSTRUCTIONS["hindi"]
        assert "Devanagari" in hindi or "देवनागरी" in hindi
        assert "NEVER write Hindi in Roman" in hindi

    def test_hindi_instruction_has_wrong_right_example(self):
        """Hindi instruction shows wrong (Roman) vs right (Devanagari) example."""
        from app.tutor.instruction_builder import LANG_INSTRUCTIONS
        hindi = LANG_INSTRUCTIONS["hindi"]
        assert "Wrong:" in hindi
        assert "Right:" in hindi

    def test_chapter_name_includes_number(self):
        """CHAPTER_NAMES for ch1_square_and_cube must include chapter number."""
        from app.tutor.instruction_builder import CHAPTER_NAMES
        ch = CHAPTER_NAMES["ch1_square_and_cube"]
        assert "Chapter 6" in ch

    def test_meta_question_chapter_number(self):
        """Meta-question for 'which chapter number' includes chapter number in response."""
        from app.tutor.state_machine import Action
        from app.tutor.instruction_builder import build_prompt
        ctx = {"language_pref": "english", "chapter": "ch1_square_and_cube",
               "student_name": "Test", "board_name": "CBSE", "class_level": 8,
               "confusion_count": 0, "state": "TEACHING", "current_level": 2}
        q = {"question_voice": "What is 5 squared?", "answer": "25",
             "answer_variants": [], "hints": [], "id": "sq_b01",
             "target_skill": "perfect_square_identification"}
        action = Action("answer_meta_question", student_text="which chapter number is this?",
                        extra={"meta_type": "chapter_info", "return_to": ""})
        msgs = build_prompt(action, ctx, question_data=q)
        user_msg = msgs[-1]["content"]
        assert "Chapter 6" in user_msg

    def test_level_filtering_strict(self):
        """pick_next_question with level should query for that level.
        When all questions at that level are asked, it re-queries without exclusions."""
        from app.tutor.memory import pick_next_question
        from app.database import SessionLocal
        from app.models import Question

        db = SessionLocal()
        try:
            # Get all level 2 question IDs
            l2_questions = db.query(Question).filter(
                Question.level == 2,
                Question.chapter == "ch1_square_and_cube",
                Question.active == True,
            ).all()
            assert len(l2_questions) > 0, "Must have level 2 questions"

            # Ask for level 2 with all L2 IDs excluded — should still return L2 (re-query)
            all_l2_ids = [q.id for q in l2_questions]
            result = pick_next_question(
                db, "test_student", "math", "ch1_square_and_cube",
                asked_question_ids=all_l2_ids,
                current_level=2,
            )
            assert result is not None, "Should re-use L2 questions when exhausted"
            assert result["level"] == 2, f"Expected level 2, got {result['level']}"
        finally:
            db.close()

    def test_tts_uses_full_text(self):
        """Streaming endpoint uses final_tts_text (full response), not first sentence."""
        import inspect
        from app.routers.student import process_message_stream
        source = inspect.getsource(process_message_stream)
        assert "TTS_FULL" in source
        assert "final_tts_text" in source


class TestV1060CriticalFixes:
    """v10.6.0: Fix question picker, TTS cutoff, Telugu, Roman Hindi."""

    def test_question_picker_excludes_current(self):
        """pick_next_question must accept current_question_id and exclude it."""
        import inspect
        from app.tutor.memory import pick_next_question
        sig = inspect.signature(pick_next_question)
        assert "current_question_id" in sig.parameters

    def test_question_picker_real_db_exclusion(self):
        """pick_next_question returns different question when current is excluded."""
        from app.database import SessionLocal
        from app.tutor.memory import pick_next_question
        db = SessionLocal()
        try:
            # Pick first question
            q1 = pick_next_question(db, "test", "math", "ch1_square_and_cube", [], current_level=2)
            if q1 is None:
                pytest.skip("No questions in DB")
            # Pick second question excluding first
            q2 = pick_next_question(db, "test", "math", "ch1_square_and_cube", [],
                                     current_level=2, current_question_id=q1["id"])
            if q2 is not None:
                assert q2["id"] != q1["id"], "Picker returned same question as current"
        finally:
            db.close()

    def test_question_picker_logs_picked(self):
        """pick_next_question must log QUESTION_PICKED."""
        import inspect
        from app.tutor import memory
        source = inspect.getsource(memory.pick_next_question)
        assert "QUESTION_PICKED" in source

    def test_tts_uses_preloaded_language(self):
        """Streaming endpoint must use pre-loaded TTS language, not session ORM object."""
        import inspect
        from app.routers import student
        source = inspect.getsource(student)
        # Should have _tts_language pre-loaded before generator
        assert "_tts_language = get_tts_language(session)" in source
        # Inside generator, should use _tts_language not get_tts_language(session)
        assert "tts_lang = _tts_language" in source

    def test_tts_prepare_avoids_session_in_generator(self):
        """Generator must not call prepare_for_tts(text, session) — session may be detached."""
        import inspect
        from app.routers import student
        source = inspect.getsource(student)
        # The generator should use _session_language_for_tts (pre-loaded value)
        assert "_session_language_for_tts" in source

    def test_telugu_triggers_in_prescan(self):
        """Language pre-scan must include Telugu triggers in both endpoints."""
        import inspect
        from app.routers import student
        source = inspect.getsource(student)
        # Telugu triggers should appear in both streaming and non-streaming pre-scan
        assert source.count("_telugu_triggers") >= 2
        assert "telugu mein" in source
        assert "speak telugu" in source

    def test_hinglish_devanagari_instruction(self):
        """Hinglish LANG_INSTRUCTIONS must require Devanagari for Hindi words."""
        from app.tutor.instruction_builder import LANG_INSTRUCTIONS
        hinglish = LANG_INSTRUCTIONS["hinglish"]
        assert "Devanagari" in hinglish or "देवनागरी" in hinglish
        assert "Roman Hindi" in hinglish or "garbled" in hinglish

    def test_telugu_lang_instruction_strict(self):
        """Telugu LANG_INSTRUCTIONS must be strict Telugu-only."""
        from app.tutor.instruction_builder import LANG_INSTRUCTIONS
        telugu = LANG_INSTRUCTIONS["telugu"]
        assert "Telugu ONLY" in telugu
        assert "MUST" in telugu
        assert "Hindi" in telugu  # Must mention not to use Hindi

    def test_picker_all_callers_pass_current_question_id(self):
        """Mid-session pick_next_question calls must pass current_question_id."""
        import inspect
        from app.routers import student
        source = inspect.getsource(student)
        import re
        # 4 total calls: 1 at session start (no current_question_id needed), 3 mid-session (must have it)
        calls = re.findall(r'memory\.pick_next_question\(', source)
        current_q_args = re.findall(r'current_question_id=', source)
        assert len(calls) == 4, f"Expected 4 pick_next_question calls, found {len(calls)}"
        assert len(current_q_args) >= 3, f"Expected >= 3 calls with current_question_id, found {len(current_q_args)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
