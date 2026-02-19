"""
Tests for answer_checker.py — the hardest module.
50+ test cases covering every answer format permutation.
"""

import pytest
from app.tutor.answer_checker import check_math_answer, _parse_fraction_from_text
from fractions import Fraction


# ─── Fraction Parsing Tests ───────────────────────────────────────────────────

class TestFractionParsing:
    def test_simple_fraction(self):
        assert _parse_fraction_from_text("2/7") == Fraction(2, 7)

    def test_negative_fraction(self):
        assert _parse_fraction_from_text("-3/9") == Fraction(-3, 9)

    def test_minus_word_fraction(self):
        assert _parse_fraction_from_text("minus 1/3") == Fraction(-1, 3)

    def test_fraction_with_by(self):
        assert _parse_fraction_from_text("2 by 7") == Fraction(2, 7)

    def test_fraction_with_baata(self):
        assert _parse_fraction_from_text("5 baata 9") == Fraction(5, 9)

    def test_negative_by_fraction(self):
        assert _parse_fraction_from_text("minus 3 by 9") == Fraction(-3, 9)

    def test_hindi_number_fraction(self):
        assert _parse_fraction_from_text("teen by saat") == Fraction(3, 7)

    def test_english_word_fraction(self):
        assert _parse_fraction_from_text("two over seven") == Fraction(2, 7)

    def test_half(self):
        assert _parse_fraction_from_text("half") == Fraction(1, 2)

    def test_aadha(self):
        assert _parse_fraction_from_text("aadha") == Fraction(1, 2)

    def test_one_third(self):
        assert _parse_fraction_from_text("one third") == Fraction(1, 3)

    def test_ek_tihaayi(self):
        assert _parse_fraction_from_text("ek tihaayi") == Fraction(1, 3)

    def test_plain_number(self):
        assert _parse_fraction_from_text("7") == Fraction(7)

    def test_negative_number(self):
        assert _parse_fraction_from_text("minus 15") == Fraction(-15)

    def test_decimal(self):
        f = _parse_fraction_from_text("0.5")
        assert f == Fraction(1, 2)

    def test_negative_decimal(self):
        f = _parse_fraction_from_text("-0.333")
        assert abs(float(f) - (-1/3)) < 0.01

    def test_zero(self):
        assert _parse_fraction_from_text("0") == Fraction(0)

    def test_sunya(self):
        assert _parse_fraction_from_text("sunya") == Fraction(0)


# ─── Answer Checking Tests ────────────────────────────────────────────────────

class TestMathAnswerChecker:
    """Test check_math_answer with realistic student responses."""

    # Correct answers
    def test_exact_match(self):
        v = check_math_answer("-1/3", "-1/3")
        assert v.correct

    def test_unsimplified_correct(self):
        v = check_math_answer("-3/9", "-1/3", ["-3/9"])
        assert v.correct

    def test_simplified_correct(self):
        v = check_math_answer("-1/3", "-3/9", ["-1/3"])
        assert v.correct

    def test_english_spoken_correct(self):
        v = check_math_answer("minus one third", "-1/3")
        assert v.correct

    def test_hindi_spoken_correct(self):
        v = check_math_answer("minus ek tihaayi", "-1/3")
        assert v.correct

    def test_fraction_by_correct(self):
        v = check_math_answer("2 by 7", "2/7")
        assert v.correct

    def test_negative_by_correct(self):
        v = check_math_answer("minus 3 by 13", "-3/13")
        assert v.correct

    def test_decimal_correct(self):
        v = check_math_answer("0.5", "1/2", ["0.5"])
        assert v.correct

    def test_half_word_correct(self):
        v = check_math_answer("half", "1/2", ["half"])
        assert v.correct

    def test_aadha_correct(self):
        v = check_math_answer("aadha", "1/2", ["aadha"])
        assert v.correct

    def test_zero_correct(self):
        v = check_math_answer("0", "0", ["zero", "sunya"])
        assert v.correct

    def test_zero_sunya_correct(self):
        v = check_math_answer("sunya", "0", ["zero", "sunya"])
        assert v.correct

    def test_negative_integer_correct(self):
        v = check_math_answer("-15", "-15", ["minus 15"])
        assert v.correct

    def test_minus_word_integer_correct(self):
        v = check_math_answer("minus 15", "-15", ["minus 15"])
        assert v.correct

    def test_equivalent_fractions(self):
        v = check_math_answer("6/12", "1/2", ["6/12"])
        assert v.correct

    def test_commutative_property_answer(self):
        v = check_math_answer("commutative", "commutative", ["commutative property"])
        assert v.correct

    def test_number_line_answer(self):
        v = check_math_answer("-1 and 0", "-1 and 0", ["-1 aur 0"])
        assert v.correct

    def test_infinite_answer(self):
        v = check_math_answer("infinite", "infinite", ["anant", "infinitely many"])
        assert v.correct

    # Incorrect answers with diagnostics
    def test_sign_error(self):
        v = check_math_answer("1/3", "-1/3")
        assert not v.correct
        assert "sign" in v.diagnostic.lower()

    def test_wrong_numerator(self):
        v = check_math_answer("2/9", "-3/9")
        assert not v.correct

    def test_completely_wrong(self):
        v = check_math_answer("5", "-1/3")
        assert not v.correct

    def test_empty_answer(self):
        v = check_math_answer("", "-1/3")
        assert not v.correct

    def test_garbage_input(self):
        v = check_math_answer("asdfgh", "-1/3")
        assert not v.correct

    # Edge cases
    def test_with_prefix_words(self):
        v = check_math_answer("I think the answer is 2/7", "2/7")
        assert v.correct

    def test_jawab_prefix(self):
        v = check_math_answer("jawab hai minus 1 by 3", "-1/3")
        assert v.correct

    def test_x_equals(self):
        v = check_math_answer("x equals 7", "7")
        assert v.correct

    def test_baata_format(self):
        v = check_math_answer("5 baata 6", "5/6")
        assert v.correct


# ─── Input Classifier Tests (v7.3.0 — LLM-based) ────────────────────────────
# Note: The sync classify_student_input() is now FAST-PATH ONLY.
# Full classification requires async classify() with OpenAI client.
# Tests marked with "fast-path" use sync function, others require async/mock.

class TestInputClassifierFastPath:
    """Test input_classifier.py fast-path (no LLM needed)."""

    def setup_method(self):
        from app.tutor.input_classifier import classify_student_input
        self.classify = classify_student_input

    # Fast-path ACK tests (single/two-word obvious inputs)
    def test_ack_haan(self):
        assert self.classify("haan") == "ACK"

    def test_ack_samajh_gaya(self):
        assert self.classify("samajh gaya") == "ACK"

    def test_ack_okay(self):
        assert self.classify("okay") == "ACK"

    def test_ack_hmm(self):
        assert self.classify("hmm") == "ACK"

    def test_ack_theek_hai(self):
        assert self.classify("theek hai") == "ACK"

    def test_ack_accha(self):
        assert self.classify("accha") == "ACK"

    # Fast-path IDK tests
    def test_idk_pata_nahi(self):
        assert self.classify("pata nahi") == "IDK"

    def test_idk_nahi_samjha(self):
        assert self.classify("nahi samjha") == "IDK"

    def test_idk_no(self):
        assert self.classify("no") == "IDK"

    # Fast-path STOP tests
    def test_stop_bye(self):
        assert self.classify("bye") == "STOP"

    def test_stop_band_karo(self):
        assert self.classify("band karo") == "STOP"

    def test_stop_bas(self):
        assert self.classify("bas") == "STOP"

    # Fast-path ANSWER tests (numeric in WAITING_ANSWER state)
    def test_answer_number(self):
        assert self.classify("49", current_state="WAITING_ANSWER") == "ANSWER"

    def test_answer_fraction(self):
        assert self.classify("2/7", current_state="WAITING_ANSWER") == "ANSWER"

    def test_haan_during_waiting_answer_is_answer(self):
        """Yes/no answers like 'haan' should be ANSWER during WAITING_ANSWER state."""
        assert self.classify("haan", current_state="WAITING_ANSWER") == "ANSWER"

    def test_yes_during_waiting_answer_is_answer(self):
        """Yes/no answers like 'yes' should be ANSWER during WAITING_ANSWER state."""
        assert self.classify("yes", current_state="WAITING_ANSWER") == "ANSWER"

    # Non-fast-path returns UNCLEAR (requires LLM)
    def test_complex_input_returns_unclear(self):
        """Complex inputs require LLM, sync function returns UNCLEAR."""
        assert self.classify("I give up") == "UNCLEAR"

    def test_language_switch_returns_unclear(self):
        """LANGUAGE_SWITCH requires LLM classification."""
        assert self.classify("can you speak in english") == "UNCLEAR"


class TestInputClassifierAsync:
    """Test async classify() function with mocked OpenAI client."""

    def test_fast_path_ack_async(self):
        """Fast-path works without client."""
        import asyncio
        from app.tutor.input_classifier import classify

        result = asyncio.run(classify("ok", "TEACHING", client=None))
        assert result["category"] == "ACK"
        assert result["confidence"] >= 0.9

    def test_fast_path_idk_async(self):
        """Fast-path IDK works without client."""
        import asyncio
        from app.tutor.input_classifier import classify

        result = asyncio.run(classify("nahi", "TEACHING", client=None))
        assert result["category"] == "IDK"

    def test_fast_path_stop_async(self):
        """Fast-path STOP works without client."""
        import asyncio
        from app.tutor.input_classifier import classify

        result = asyncio.run(classify("bye", "TEACHING", client=None))
        assert result["category"] == "STOP"

    def test_answer_in_waiting_state_async(self):
        """Numeric input in WAITING_ANSWER returns ANSWER."""
        import asyncio
        from app.tutor.input_classifier import classify

        result = asyncio.run(classify("144", "WAITING_ANSWER", client=None))
        assert result["category"] == "ANSWER"

    def test_no_client_returns_unclear(self):
        """Without client, non-fast-path returns UNCLEAR."""
        import asyncio
        from app.tutor.input_classifier import classify

        result = asyncio.run(classify("could you explain in English please", "TEACHING", client=None))
        assert result["category"] == "UNCLEAR"

    def test_silence_marker(self):
        """[silence] marker is handled."""
        import asyncio
        from app.tutor.input_classifier import classify

        result = asyncio.run(classify("[silence]", "TEACHING", client=None))
        assert result["category"] == "SILENCE"

    def test_empty_input(self):
        """Empty input returns REPEAT."""
        import asyncio
        from app.tutor.input_classifier import classify

        result = asyncio.run(classify("", "TEACHING", client=None))
        assert result["category"] == "REPEAT"


# ─── Enforcer Tests ───────────────────────────────────────────────────────────

# ─── State Machine Tests (v7.2.0) ───────────────────────────────────────────

class TestStateMachine:
    """Test state_machine.py transitions including v7.2.0 changes."""

    def setup_method(self):
        from app.tutor.state_machine import transition
        self.transition = transition

    def test_ack_in_teaching_transitions_to_waiting_answer(self):
        """BUG 1: ACK in TEACHING should transition to WAITING_ANSWER."""
        ctx = {"student_text": "ab samajh aaya", "teaching_turn": 0}
        new_state, action = self.transition("TEACHING", "ACK", ctx)
        assert new_state == "WAITING_ANSWER"
        assert action.action_type == "read_question"

    def test_idk_in_teaching_increments_turn(self):
        """BUG 1: IDK in TEACHING should increment teaching_turn."""
        ctx = {"student_text": "nahi samjha", "teaching_turn": 0}
        new_state, action = self.transition("TEACHING", "IDK", ctx)
        assert new_state == "TEACHING"
        assert action.teaching_turn == 1

    def test_idk_at_turn_3_forces_transition(self):
        """BUG 1: At teaching_turn=3, should force transition to WAITING_ANSWER."""
        ctx = {"student_text": "nahi samjha", "teaching_turn": 2}
        new_state, action = self.transition("TEACHING", "IDK", ctx)
        assert new_state == "WAITING_ANSWER"
        assert action.extra.get("forced_transition") == True

    def test_language_switch_stays_in_current_state(self):
        """BUG 2: LANGUAGE_SWITCH should stay in current state."""
        ctx = {"student_text": "can you speak in english"}
        new_state, action = self.transition("TEACHING", "LANGUAGE_SWITCH", ctx)
        assert new_state == "TEACHING"
        assert action.action_type == "acknowledge_language_switch"
        assert action.language_pref == "english"

    def test_language_switch_from_waiting_answer(self):
        """BUG 2: LANGUAGE_SWITCH should work from any state."""
        ctx = {"student_text": "hindi mein bolo"}
        new_state, action = self.transition("WAITING_ANSWER", "LANGUAGE_SWITCH", ctx)
        assert new_state == "WAITING_ANSWER"
        assert action.language_pref == "hindi"

    def test_meta_question_in_teaching(self):
        """BUG 4: META_QUESTION in TEACHING should be handled."""
        ctx = {"student_text": "any more examples?", "teaching_turn": 1}
        new_state, action = self.transition("TEACHING", "META_QUESTION", ctx)
        assert new_state == "TEACHING"
        assert action.action_type == "answer_meta_question"


class TestEnforcer:
    """Test enforcer.py rules."""

    def setup_method(self):
        from app.tutor.enforcer import enforce
        self.enforce = enforce

    def test_passes_good_response(self):
        r = self.enforce("Bahut achha! Aapne sahi kaha minus ek tihaayi.", "EVALUATING", verdict="CORRECT")
        assert r.passed

    def test_blocks_false_praise(self):
        r = self.enforce("Shabash! Bahut accha kiya!", "EVALUATING", verdict="INCORRECT")
        assert not r.passed or "FALSE_PRAISE" in r.violations or "shabash" not in r.text.lower()

    def test_catches_long_response(self):
        long_text = " ".join(["word"] * 70)
        r = self.enforce(long_text, "TEACHING")
        assert len(r.text.split()) <= 55

    def test_catches_repetition(self):
        prev = "Chalo agle question pe chalte hain."
        r = self.enforce("Chalo agle question pe chalte hain.", "NEXT_QUESTION", previous_response=prev)
        assert "REPETITION" in r.violations


# ─── Clean for TTS Tests ─────────────────────────────────────────────────────

class TestCleanForTTS:
    def setup_method(self):
        from app.voice.clean_for_tts import clean_for_tts
        self.clean = clean_for_tts

    def test_fraction_conversion(self):
        assert "by" in self.clean("-5/9 + 2/9")

    def test_equals_conversion(self):
        assert "equals" in self.clean("x = 7")

    def test_percentage(self):
        assert "percent" in self.clean("85%")

    def test_parentheses_removed(self):
        result = self.clean("(a + b)")
        assert "(" not in result
        assert ")" not in result

    def test_chapter_abbreviation(self):
        assert "Chapter" in self.clean("Ch. 1")
