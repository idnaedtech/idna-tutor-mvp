"""
Tests for tutor_intent.py — validate_teaching_output (hallucination detection, schema validation).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tutor_intent import validate_teaching_output


# ============================================================
# Test: Hallucinated number detection
# ============================================================

def test_valid_output_with_known_numbers():
    valid, reason = validate_teaching_output(
        text="The numerators add up: -3 + 2 = -1. So the answer is -1/7. What do you get?",
        solution_steps=["Add numerators: -3 + 2 = -1", "Keep denominator: 7", "Answer: -1/7"],
        correct_answer="-1/7",
    )
    assert valid is True, f"Expected valid, got: {reason}"


def test_hallucinated_number_rejected():
    valid, reason = validate_teaching_output(
        text="The answer is 42. Try again?",
        solution_steps=["Add: -3 + 2 = -1", "Answer: -1/7"],
        correct_answer="-1/7",
    )
    assert valid is False
    assert "hallucinated_number" in reason


def test_small_digits_allowed():
    """Numbers 0-10 are always allowed (common in teaching)."""
    valid, reason = validate_teaching_output(
        text="Step 1: Find the LCM. Step 2: Convert. What do you get?",
        solution_steps=["Find LCM of 2 and 3 = 6"],
        correct_answer="-5/6",
    )
    assert valid is True


def test_numbers_from_accept_also_allowed():
    valid, reason = validate_teaching_output(
        text="You could also say 2/4 or 3/6. What's the simplest form?",
        solution_steps=["Answer: 1/2"],
        correct_answer="1/2",
        accept_also=["2/4", "3/6"],
    )
    assert valid is True


# ============================================================
# Test: Word count limit
# ============================================================

def test_too_long_rejected():
    long_text = " ".join(["word"] * 60) + "?"
    valid, reason = validate_teaching_output(
        text=long_text,
        correct_answer="7",
    )
    assert valid is False
    assert reason == "too_long"


def test_under_limit_passes():
    valid, reason = validate_teaching_output(
        text="What is -3 plus 2?",
        correct_answer="-1/7",
        solution_steps=["Add: -3 + 2 = -1"],
    )
    assert valid is True


# ============================================================
# Test: Question ending enforcement
# ============================================================

def test_teaching_move_without_question():
    valid, reason = validate_teaching_output(
        text="Think about the sign.",
        teacher_move="probe",
        correct_answer="7",
    )
    assert valid is False
    assert reason == "no_question"


def test_teaching_move_with_question():
    valid, reason = validate_teaching_output(
        text="What sign does the answer have?",
        teacher_move="probe",
        correct_answer="-1/7",
        solution_steps=["Add: -3 + 2 = -1"],
    )
    assert valid is True


def test_reveal_no_question_ok():
    """Reveal move doesn't need a question."""
    valid, reason = validate_teaching_output(
        text="The answer is -1/7.",
        teacher_move="reveal",
        correct_answer="-1/7",
        solution_steps=["Answer: -1/7"],
    )
    assert valid is True


def test_confirm_no_question_ok():
    """Confirm move doesn't need a question."""
    valid, reason = validate_teaching_output(
        text="Yes, that's correct!",
        teacher_move="confirm",
        correct_answer="7",
    )
    assert valid is True


# ============================================================
# Test: Empty output
# ============================================================

def test_empty_output_rejected():
    valid, reason = validate_teaching_output(
        text="",
        correct_answer="7",
    )
    assert valid is False
    assert reason == "empty_output"


# ============================================================
# Test: Edge cases
# ============================================================

def test_fraction_in_solution_steps():
    """Fractions from solution_steps should be allowed."""
    valid, reason = validate_teaching_output(
        text="LCM is 12. So 9/12 - 10/12 = -1/12. What do you get?",
        solution_steps=[
            "Find LCM of 4 and 6 = 12",
            "Convert: 3/4 = 9/12",
            "Convert: 5/6 = 10/12",
            "Subtract: 9/12 - 10/12 = -1/12",
        ],
        correct_answer="-1/12",
        teacher_move="hint_step",
    )
    assert valid is True


def test_no_solution_steps_lenient():
    """When no solution_steps provided, only small digits are allowed."""
    valid, reason = validate_teaching_output(
        text="Add 3 and 4. What do you get?",
        correct_answer="7",
        teacher_move="probe",
    )
    assert valid is True


# ============================================================
# Test: Banned YouTube/AI phrases (Bug 1 fix)
# ============================================================

def test_youtube_phrase_rejected():
    """GPT hallucination like 'Thank you for watching!' should be rejected."""
    valid, reason = validate_teaching_output(
        text="Thank you for watching! See you next time!",
        correct_answer="7",
    )
    assert valid is False
    assert reason == "off_topic_content"


def test_subscribe_phrase_rejected():
    """YouTube-style 'subscribe' should be rejected."""
    valid, reason = validate_teaching_output(
        text="Don't forget to subscribe for more math tips?",
        correct_answer="7",
        teacher_move="probe",
    )
    assert valid is False
    assert reason == "off_topic_content"


def test_like_and_share_rejected():
    valid, reason = validate_teaching_output(
        text="Like and share this with your friends?",
        correct_answer="7",
        teacher_move="probe",
    )
    assert valid is False
    assert reason == "off_topic_content"


def test_normal_math_not_flagged():
    """Normal math teaching should NOT be flagged as off-topic."""
    valid, reason = validate_teaching_output(
        text="What is 3 plus 4?",
        correct_answer="7",
        teacher_move="probe",
    )
    assert valid is True


# ============================================================
# Test: PROBE move not polished (Bug 3 fix)
# ============================================================

def test_probe_not_polished():
    """PROBE moves should skip GPT polishing — verified micro_check preserved."""
    from tutor_intent import _polish_teacher_response
    base = "What does additive inverse mean?"
    result = _polish_teacher_response(
        base_response=base,
        teacher_move="probe",
        error_type="",
        correct_answer="-1/7",
        student_answer="5",
    )
    assert result == base, f"PROBE should return base_response unchanged, got: {result}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
