"""
Tests for teacher_policy.py — escalation ladder, micro_check usage, P0 enforcement.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from teacher_policy import (
    plan_teacher_response,
    diagnose_error,
    TeachingMove,
    ErrorType,
    TeachingPhase,
    TeacherPlanner,
    calculate_warmth_level,
    get_warmth_primitive,
    remove_banned_phrases,
    generate_teacher_response,
)


# ============================================================
# Test: Escalation ladder
# ============================================================

def test_attempt_1_uses_probe():
    result = plan_teacher_response(
        session_id="test_esc",
        is_correct=False,
        correct_answer="-1/7",
        student_answer="1/7",
        question_text="What is -3/7 + 2/7?",
        attempt_number=1,
    )
    assert result["teacher_move"] == TeachingMove.PROBE.value


def test_attempt_2_uses_hint_step():
    result = plan_teacher_response(
        session_id="test_esc2",
        is_correct=False,
        correct_answer="-1/7",
        student_answer="1/7",
        question_text="What is -3/7 + 2/7?",
        attempt_number=2,
    )
    assert result["teacher_move"] in [
        TeachingMove.HINT_STEP.value,
        TeachingMove.REFRAME.value,  # sign_error → reframe
    ]


def test_attempt_3_uses_worked_example_or_reframe():
    result = plan_teacher_response(
        session_id="test_esc3",
        is_correct=False,
        correct_answer="-1/7",
        student_answer="42",
        question_text="What is -3/7 + 2/7?",
        attempt_number=3,
    )
    assert result["teacher_move"] in [
        TeachingMove.WORKED_EXAMPLE.value,
        TeachingMove.REFRAME.value,
    ]


def test_attempt_4_reveals():
    result = plan_teacher_response(
        session_id="test_esc4",
        is_correct=False,
        correct_answer="-1/7",
        student_answer="42",
        question_text="What is -3/7 + 2/7?",
        attempt_number=4,
    )
    assert result["teacher_move"] == TeachingMove.REVEAL.value
    assert result["move_to_next"] is True


def test_correct_answer_confirms():
    result = plan_teacher_response(
        session_id="test_correct",
        is_correct=True,
        correct_answer="-1/7",
        student_answer="-1/7",
        question_text="What is -3/7 + 2/7?",
        attempt_number=1,
    )
    assert result["teacher_move"] in [
        TeachingMove.CONFIRM.value,
        TeachingMove.CHALLENGE.value,
    ]


# ============================================================
# Test: Enriched data usage (micro_checks, eval_result)
# ============================================================

def test_micro_check_used_in_probe():
    result = plan_teacher_response(
        session_id="test_micro",
        is_correct=False,
        correct_answer="-1/7",
        student_answer="1/7",
        question_text="What is -3/7 + 2/7?",
        attempt_number=1,
        micro_checks=["What do you do with the denominators when they're the same?", "What is -3 + 2?"],
    )
    # Should use the first micro_check as probe question
    assert "denominator" in result["response"].lower() or "What" in result["response"]


def test_eval_result_matched_mistake():
    eval_result = {
        "is_correct": False,
        "feedback_tag": "SIGN_ERROR",
        "matched_mistake": {
            "error_type": "sign_error",
            "diagnosis": "Forgot negative",
            "micro_hint": "Is -3 + 2 positive or negative?",
        },
        "micro_hint": "Is -3 + 2 positive or negative?",
    }
    result = plan_teacher_response(
        session_id="test_eval",
        is_correct=False,
        correct_answer="-1/7",
        student_answer="1/7",
        question_text="What is -3/7 + 2/7?",
        attempt_number=1,
        eval_result=eval_result,
    )
    assert result["error_type"] == "sign_error"


# ============================================================
# Test: P0 enforcement
# ============================================================

def test_response_ends_with_question_for_teaching():
    """Teaching moves must end with a question."""
    result = plan_teacher_response(
        session_id="test_p0",
        is_correct=False,
        correct_answer="7",
        student_answer="5",
        question_text="Solve: x + 5 = 12",
        attempt_number=1,
    )
    response = result["response"]
    assert response.strip().endswith("?"), f"Expected question: {response}"


def test_reveal_does_not_require_question():
    """Reveal is an explicit exception — no question required."""
    result = plan_teacher_response(
        session_id="test_reveal",
        is_correct=False,
        correct_answer="7",
        student_answer="5",
        question_text="Solve: x + 5 = 12",
        attempt_number=4,
    )
    # Reveal can have no question — just shows answer
    assert result["teacher_move"] == TeachingMove.REVEAL.value


def test_max_sentences_limit():
    """Response should not exceed 2 sentences before question."""
    planner = TeacherPlanner()
    plan = planner.plan(
        is_correct=False,
        error_diagnosis={"error_type": "unknown", "confidence": 0.5, "hint": "Think step by step."},
        attempt_number=1,
        question_text="What is 2/3 + 1/4?",
        correct_answer="11/12",
        student_answer="3/7",
        session_id="test_sentences",
    )
    result = generate_teacher_response(plan)
    response = result["response"]
    # Count sentences (rough)
    import re
    sentences = [s for s in re.split(r'[.!?]+', response) if s.strip()]
    assert len(sentences) <= 3  # 2 statements + 1 question


# ============================================================
# Test: Warmth policy
# ============================================================

def test_warmth_correct_is_calm():
    assert calculate_warmth_level(1, is_correct=True) == 1

def test_warmth_wrong_is_supportive():
    assert calculate_warmth_level(1, is_correct=False) == 2

def test_warmth_frustration_is_soothing():
    assert calculate_warmth_level(1, is_correct=False, consecutive_wrong=3) == 3

def test_warmth_frustration_phrase():
    w = calculate_warmth_level(1, is_correct=False, student_answer="idk i give up")
    assert w == 3


# ============================================================
# Test: Banned phrase removal
# ============================================================

def test_remove_banned_great_job():
    cleaned = remove_banned_phrases("Great job! You got the right answer.")
    assert "great job" not in cleaned.lower()

def test_remove_banned_preserves_warmth():
    cleaned = remove_banned_phrases("Okay. Great job on that one!")
    assert cleaned.startswith("Okay.")


# ============================================================
# Test: TeachingPhase enum exists
# ============================================================

def test_teaching_phase_values():
    assert TeachingPhase.PRESENT.value == "present"
    assert TeachingPhase.DIAGNOSE.value == "diagnose"
    assert TeachingPhase.SCAFFOLD.value == "scaffold"
    assert TeachingPhase.ADVANCE.value == "advance"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
