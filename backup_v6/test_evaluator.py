"""
Tests for evaluator.py — evaluate_answer with common_mistakes matching.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluator import evaluate_answer, check_answer, normalize_spoken_input


# ============================================================
# Test: check_answer (existing, deterministic)
# ============================================================

def test_check_answer_correct_fraction():
    assert check_answer("-1/7", "minus 1 by 7") is True

def test_check_answer_correct_number():
    assert check_answer("7", "the answer is 7") is True

def test_check_answer_wrong():
    assert check_answer("7", "5") is False

def test_check_answer_fraction_equivalence():
    assert check_answer("1/2", "2/4") is True

def test_check_answer_yes_no():
    assert check_answer("yes", "Yes, zero is a rational number") is True

def test_check_answer_embedded_fraction():
    assert check_answer("2/3", "I'm asking you, what? Two by three.") is True

def test_check_answer_takes_last_number():
    assert check_answer("7", "first I thought 5 but now I say 7") is True


# ============================================================
# Test: evaluate_answer with common_mistakes
# ============================================================

SAMPLE_QUESTION = {
    "id": "rn_001",
    "answer": "-1/7",
    "common_mistakes": [
        {"wrong_answer": "1/7", "error_type": "sign_error", "diagnosis": "Forgot negative", "micro_hint": "Is -3 + 2 positive or negative?"},
        {"wrong_answer": "-1/14", "error_type": "fraction_addition", "diagnosis": "Added denominators", "micro_hint": "When denominators are the same, do you add them?"},
        {"wrong_answer": "5/7", "error_type": "wrong_operation", "diagnosis": "Subtracted instead of adding", "micro_hint": "The question says add."},
    ],
}


def test_evaluate_correct():
    result = evaluate_answer("-1/7", "minus 1 by 7", SAMPLE_QUESTION)
    assert result["is_correct"] is True
    assert result["feedback_tag"] == "CORRECT"
    assert result["matched_mistake"] is None


def test_evaluate_sign_error_match():
    result = evaluate_answer("-1/7", "1/7", SAMPLE_QUESTION)
    assert result["is_correct"] is False
    assert result["feedback_tag"] == "SIGN_ERROR"
    assert result["matched_mistake"] is not None
    assert result["diagnosis"] == "Forgot negative"
    assert result["micro_hint"] == "Is -3 + 2 positive or negative?"


def test_evaluate_fraction_addition_match():
    result = evaluate_answer("-1/7", "-1/14", SAMPLE_QUESTION)
    assert result["is_correct"] is False
    assert result["feedback_tag"] == "FRACTION_ADDITION"


def test_evaluate_wrong_operation_match():
    result = evaluate_answer("-1/7", "5/7", SAMPLE_QUESTION)
    assert result["is_correct"] is False
    assert result["feedback_tag"] == "WRONG_OPERATION"


def test_evaluate_no_match_unknown():
    result = evaluate_answer("-1/7", "42", SAMPLE_QUESTION)
    assert result["is_correct"] is False
    assert result["feedback_tag"] == "UNKNOWN"
    assert result["matched_mistake"] is None


def test_evaluate_empty_answer():
    result = evaluate_answer("-1/7", "", SAMPLE_QUESTION)
    assert result["is_correct"] is False
    assert result["feedback_tag"] == "NO_ANSWER"


def test_evaluate_no_common_mistakes():
    """Unenriched question — should still work via check_answer."""
    q = {"id": "old_001", "answer": "7"}
    result = evaluate_answer("7", "7", q)
    assert result["is_correct"] is True


def test_evaluate_spoken_wrong_answer():
    """Spoken variant matches common mistake after normalization."""
    result = evaluate_answer("-1/7", "1 by 7", SAMPLE_QUESTION)
    assert result["is_correct"] is False
    assert result["feedback_tag"] == "SIGN_ERROR"


# ============================================================
# Test: normalize_spoken_input edge cases
# ============================================================

def test_normalize_negative_fraction():
    assert normalize_spoken_input("minus 1 by 7") == "-1/7"

def test_normalize_duplicate_stt():
    assert normalize_spoken_input("2 by 3 2 by 3") == "2/3"

def test_normalize_decimal():
    assert normalize_spoken_input("2 point 5") == "2.5"

def test_normalize_percentage():
    assert normalize_spoken_input("50 percent") == "50%"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
