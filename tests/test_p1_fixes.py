"""
IDNA EdTech — P1 Bug Fix Regression Tests

Tests for P1 bugs fixed in v8.1.5:
- Bug #5: Parent split()[0] on empty instruction
- Bug #6: Weakest-skill dead end (SESSION_COMPLETE → SESSION_END)
"""

import pytest
from unittest.mock import MagicMock, patch


class TestParentInstructionSplitBug:
    """
    Bug #5: Parent instruction split()[0] raises IndexError on empty string.

    Fix: Guard against empty instruction before calling split()[0].
    Location: app/tutor/memory.py line 171
    """

    def test_empty_instruction_does_not_crash(self):
        """Empty parent instruction should not raise IndexError."""
        from app.tutor import memory

        # Mock database session
        db = MagicMock()

        # Mock parent instruction with empty string
        mock_instruction = MagicMock()
        mock_instruction.instruction = ""
        mock_instruction.fulfilled = False

        # Mock the query to return our empty instruction
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_instruction

        # Mock base query for questions
        mock_question = MagicMock()
        mock_question.id = "q1"
        mock_question.subject = "math"
        mock_question.chapter = "ch1"
        mock_question.question_type = "numeric"
        mock_question.question_text = "Test"
        mock_question.question_voice = "Test"
        mock_question.answer = "42"
        mock_question.answer_variants = []
        mock_question.key_concepts = []
        mock_question.eval_method = "exact"
        mock_question.hints = []
        mock_question.solution = ""
        mock_question.target_skill = "test_skill"
        mock_question.difficulty = 1
        mock_question.active = True

        # This should NOT raise IndexError
        try:
            result = memory.pick_next_question(
                db, "student1", "math", "ch1", asked_question_ids=[]
            )
            # If we get here without exception, the fix works
            assert True
        except IndexError:
            pytest.fail("Empty parent instruction caused IndexError - bug #5 not fixed")

    def test_whitespace_instruction_does_not_crash(self):
        """Whitespace-only parent instruction should not raise IndexError."""
        from app.tutor import memory

        db = MagicMock()

        mock_instruction = MagicMock()
        mock_instruction.instruction = "   \t\n   "  # Whitespace only
        mock_instruction.fulfilled = False

        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_instruction

        try:
            result = memory.pick_next_question(
                db, "student1", "math", "ch1", asked_question_ids=[]
            )
            assert True
        except IndexError:
            pytest.fail("Whitespace parent instruction caused IndexError - bug #5 not fixed")


class TestSessionCompleteStateBug:
    """
    Bug #6: SESSION_COMPLETE is not a valid TutorState.

    Fix: Use SESSION_END instead of SESSION_COMPLETE.
    Location: app/routers/student.py line 258
    """

    def test_session_end_is_valid_state(self):
        """SESSION_END should be a valid TutorState."""
        from app.state.session import TutorState

        # This should not raise ValueError
        state = TutorState("SESSION_END")
        assert state == TutorState.SESSION_END

    def test_session_complete_is_not_valid_state(self):
        """SESSION_COMPLETE should NOT be a valid TutorState."""
        from app.state.session import TutorState

        with pytest.raises(ValueError):
            TutorState("SESSION_COMPLETE")

    def test_session_complete_normalizes_to_session_end(self):
        """Verify SESSION_COMPLETE is normalized to SESSION_END via legacy mapping."""
        from app.routers.student import _normalize_state
        from app.state.session import TutorState

        # Legacy SESSION_COMPLETE should normalize to SESSION_END
        result = _normalize_state("SESSION_COMPLETE")
        assert result == TutorState.SESSION_END

        # Direct SESSION_END should work too
        result = _normalize_state("SESSION_END")
        assert result == TutorState.SESSION_END
