"""
IDNA Tutor — Answer Checker Tests (v5.0)
==========================================
Tests for answer_checker.py — pure Python, no LLM, no mocking needed.
Covers: normalization, STT mishearing correction, partial answer detection,
sentence extraction, numeric equivalence, and edge cases.

Run: pytest test_answer_checker.py -v
"""

import pytest
from answer_checker import normalize_answer, check_answer, extract_math_from_sentence, normalize_answer_key


# ============================================================
# NORMALIZATION TESTS
# ============================================================

class TestNormalization:
    """Test spoken math → symbolic normalization."""

    # --- Standard spoken fractions ---
    def test_minus_x_by_y(self):
        assert normalize_answer("minus 1 by 7") == "-1/7"

    def test_minus_word_by_word(self):
        assert normalize_answer("minus one by seven") == "-1/7"

    def test_minus_x_over_y(self):
        assert normalize_answer("minus 1 over 7") == "-1/7"

    def test_negative_x_divided_by_y(self):
        assert normalize_answer("negative one divided by seven") == "-1/7"

    def test_x_by_y_positive(self):
        assert normalize_answer("3 by 7") == "3/7"

    def test_x_upon_y(self):
        assert normalize_answer("5 upon 8") == "5/8"

    # --- STT mishearing: "my" → "minus" ---
    def test_my_mishearing_digit(self):
        """Groq Whisper often transcribes 'minus' as 'my'."""
        assert normalize_answer("my 1 by 7") == "-1/7"

    def test_my_mishearing_word(self):
        assert normalize_answer("my one by seven") == "-1/7"

    def test_my_mishearing_five(self):
        assert normalize_answer("my five") == "-5"

    # --- STT mishearing: "or" → "over" ---
    def test_or_mishearing(self):
        """Groq Whisper sometimes transcribes 'over' as 'or'."""
        assert normalize_answer("1 or 7") == "1/7"

    def test_minus_or_mishearing(self):
        assert normalize_answer("minus 1 or 7") == "-1/7"

    # --- Compound fractions ---
    def test_one_half(self):
        assert normalize_answer("one half") == "1/2"

    def test_minus_one_half(self):
        assert normalize_answer("minus one half") == "-1/2"

    def test_two_thirds(self):
        assert normalize_answer("two thirds") == "2/3"

    def test_three_quarters(self):
        assert normalize_answer("three quarters") == "3/4"

    def test_one_third(self):
        assert normalize_answer("one third") == "1/3"

    # --- Word numbers → digits ---
    def test_word_seven(self):
        assert normalize_answer("seven") == "7"

    def test_word_twelve(self):
        assert normalize_answer("twelve") == "12"

    def test_word_twenty(self):
        assert normalize_answer("twenty") == "20"

    # --- Stripping prefixes ---
    def test_the_answer_is(self):
        assert normalize_answer("the answer is minus 1 by 7") == "-1/7"

    def test_answer_equals(self):
        assert normalize_answer("answer equals 5") == "5"

    def test_x_equals(self):
        assert normalize_answer("x = 5") == "5"

    def test_x_equals_fraction(self):
        assert normalize_answer("x = minus 1 by 7") == "-1/7"

    # --- Operations ---
    def test_plus(self):
        assert normalize_answer("3 plus 4") == "3+4"

    def test_times(self):
        assert normalize_answer("2 times 3") == "2*3"

    def test_into(self):
        assert normalize_answer("5 into 6") == "5*6"

    # --- Whitespace and punctuation ---
    def test_trailing_period(self):
        assert normalize_answer("7.") == "7"

    def test_leading_trailing_spaces(self):
        assert normalize_answer("  minus 1 by 7  ") == "-1/7"

    def test_trailing_comma(self):
        assert normalize_answer("7,") == "7"


# ============================================================
# CHECK_ANSWER — CORRECT (True)
# ============================================================

class TestCheckAnswerCorrect:
    """Tests where student answer should be marked correct (True)."""

    def test_exact_match(self):
        assert check_answer("-1/7", "-1/7") is True

    def test_spoken_minus_by(self):
        assert check_answer("minus 1 by 7", "-1/7") is True

    def test_spoken_words(self):
        assert check_answer("minus one by seven", "-1/7") is True

    def test_spoken_over(self):
        assert check_answer("-1 over 7", "-1/7") is True

    def test_spoken_minus_over(self):
        assert check_answer("minus 1 over 7", "-1/7") is True

    def test_numeric_equivalence_decimal(self):
        assert check_answer("0.5", "1/2") is True

    def test_numeric_equivalence_whole(self):
        assert check_answer("2", "2/1") is True

    def test_equation_format(self):
        assert check_answer("x = 5", "5") is True

    def test_equation_format_fraction(self):
        assert check_answer("x = -1/7", "-1/7") is True

    def test_sentence_answer(self):
        """Student wraps answer in a sentence."""
        assert check_answer("the answer is minus 1 by 7", "-1/7") is True

    def test_simple_integer(self):
        assert check_answer("5", "5") is True

    def test_spoken_integer(self):
        assert check_answer("five", "5") is True

    def test_positive_fraction(self):
        assert check_answer("3 by 8", "3/8") is True

    def test_accept_also(self):
        """Question bank provides additional accepted variants."""
        assert check_answer("0.333", "1/3", accept_also=["0.333"]) is True

    def test_my_mishearing_correct(self):
        """STT mishearing 'minus' as 'my' should still match."""
        assert check_answer("my 1 by 7", "-1/7") is True

    def test_or_mishearing_correct(self):
        """STT mishearing 'over' as 'or' should still match."""
        assert check_answer("minus 1 or 7", "-1/7") is True


# ============================================================
# CHECK_ANSWER — PARTIAL (None)
# ============================================================

class TestCheckAnswerPartial:
    """Tests where student answer is partial (None) — got part right."""

    def test_numerator_only_spoken(self):
        """Student says 'minus 1' for answer '-1/7' — got numerator."""
        assert check_answer("minus 1", "-1/7") is None

    def test_numerator_only_digit(self):
        assert check_answer("-1", "-1/7") is None

    def test_missed_sign(self):
        """Student says '1/7' for answer '-1/7' — forgot negative."""
        assert check_answer("1/7", "-1/7") is None

    def test_magnitude_only(self):
        """Student says '1' for answer '-1/7' — just the absolute numerator."""
        assert check_answer("1", "-1/7") is None

    def test_spoken_numerator_word(self):
        """Student says 'minus one' for answer '-1/7'."""
        assert check_answer("minus one", "-1/7") is None

    def test_missed_sign_spoken(self):
        """Student says 'one by seven' for '-1/7'."""
        assert check_answer("one by seven", "-1/7") is None


# ============================================================
# CHECK_ANSWER — WRONG (False)
# ============================================================

class TestCheckAnswerWrong:
    """Tests where student answer is definitely wrong (False)."""

    def test_completely_wrong(self):
        assert check_answer("5", "-1/7") is False

    def test_wrong_fraction(self):
        assert check_answer("2/7", "-1/7") is False

    def test_wrong_sign_different_number(self):
        assert check_answer("-5/7", "-1/7") is False

    def test_random_text(self):
        assert check_answer("hello", "-1/7") is False

    def test_empty_string(self):
        assert check_answer("", "-1/7") is False

    def test_whitespace_only(self):
        assert check_answer("   ", "-1/7") is False

    def test_wrong_integer(self):
        assert check_answer("10", "5") is False

    def test_common_computational_error(self):
        """Student adds magnitudes instead of signed addition: -3+2 ≠ 5."""
        assert check_answer("5/7", "-1/7") is False

    def test_wrong_sign_computational(self):
        assert check_answer("-5/7", "-1/7") is False


# ============================================================
# SENTENCE EXTRACTION
# ============================================================

class TestSentenceExtraction:
    """Test extracting math from longer spoken sentences."""

    def test_answer_is_fraction(self):
        candidates = extract_math_from_sentence("the answer is minus 1 by 7")
        assert len(candidates) > 0
        # At least one candidate should normalize to -1/7
        norms = [normalize_answer(c) for c in candidates]
        assert "-1/7" in norms

    def test_answer_is_integer(self):
        candidates = extract_math_from_sentence("the answer is 5")
        assert len(candidates) > 0

    def test_fraction_in_sentence(self):
        candidates = extract_math_from_sentence("I think it is minus 3 over 7")
        assert len(candidates) > 0

    def test_slash_fraction_in_sentence(self):
        candidates = extract_math_from_sentence("so the result is -1/7")
        assert len(candidates) > 0
        norms = [normalize_answer(c) for c in candidates]
        assert "-1/7" in norms


# ============================================================
# NORMALIZE ANSWER KEY
# ============================================================

class TestNormalizeAnswerKey:
    """Test that answer keys generate all expected variants."""

    def test_fraction_generates_decimal(self):
        variants = normalize_answer_key("-1/7")
        # Should include the original and normalized forms
        assert "-1/7" in variants

    def test_half_generates_decimal(self):
        variants = normalize_answer_key("1/2")
        assert "0.5" in variants or any("0.5" in v for v in variants)

    def test_integer_answer(self):
        variants = normalize_answer_key("5")
        assert "5" in variants


# ============================================================
# EDGE CASES — FROM LIVE SESSIONS
# ============================================================

class TestLiveSessionEdgeCases:
    """Regression tests from actual student session failures."""

    def test_twelve_as_denominator_substep(self):
        """Student says '12' when asked for denominator — should be correct if answer is 12."""
        assert check_answer("12", "12") is True
        assert check_answer("twelve", "12") is True

    def test_seven_as_denominator_substep(self):
        """Student says '7' or 'seven' as denominator sub-step."""
        assert check_answer("7", "7") is True
        assert check_answer("seven", "7") is True
        assert check_answer("saat", "7") is False  # Hindi not in word_nums

    def test_minus_six_substep(self):
        """Student says 'minus six' for sub-question '2 times minus 3 kya hoga?'."""
        assert check_answer("minus six", "-6") is True
        assert check_answer("minus 6", "-6") is True
        assert check_answer("-6", "-6") is True

    def test_mine_is_mishearing(self):
        """'Mine is 1 by 2' — Whisper mishearing. Should still extract math."""
        # The 'mine' won't trigger 'my' → 'minus' because 'mine' ≠ 'my \\d'
        # But sentence extraction should find '1 by 2'
        result = check_answer("mine is 1 by 2", "1/2")
        assert result is True

    def test_additive_inverse(self):
        """Additive inverse of 5/8 is -5/8."""
        assert check_answer("minus 5 by 8", "-5/8") is True
        assert check_answer("-5/8", "-5/8") is True
        assert check_answer("minus five by eight", "-5/8") is True

    def test_whisper_garbled_not_crash(self):
        """Garbled Whisper output shouldn't crash the checker."""
        assert check_answer("foreign", "-1/7") is False
        assert check_answer("well period", "-1/7") is False
        assert check_answer(".", "-1/7") is False
        assert check_answer("x", "-1/7") is False
        assert check_answer("me", "-1/7") is False
