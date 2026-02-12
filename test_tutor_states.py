"""
IDNA Tutor — State Machine Tests (v5.0)
=========================================
Tests for tutor_states.py — pure Python, no LLM, no mocking.
Covers: all state transitions, circuit breakers, TEACH_CONCEPT (v5.0),
time limits, universal transitions, edge cases.

Run: pytest test_tutor_states.py -v
"""

import pytest
from tutor_states import State, Action, get_transition


def make_session(**overrides):
    """Helper: create a default session dict with optional overrides."""
    base = {
        "hint_count": 0,
        "idk_count": 0,
        "attempt_count": 0,
        "offtopic_streak": 0,
        "duration_minutes": 0,
        "total_questions": 10,
        "current_question_index": 0,
    }
    base.update(overrides)
    return base


# ============================================================
# UNIVERSAL TRANSITIONS (any state)
# ============================================================

class TestUniversalTransitions:
    """Transitions that should work from ANY state."""

    def test_stop_from_waiting(self):
        r = get_transition(State.WAITING_ANSWER, "STOP", make_session())
        assert r["action"] == Action.END_SESSION
        assert r["next_state"] == State.ENDED

    def test_stop_from_hinting(self):
        r = get_transition(State.HINTING, "STOP", make_session())
        assert r["action"] == Action.END_SESSION
        assert r["next_state"] == State.ENDED

    def test_stop_from_explaining(self):
        r = get_transition(State.EXPLAINING, "STOP", make_session())
        assert r["action"] == Action.END_SESSION
        assert r["next_state"] == State.ENDED

    def test_language_switch_stays_in_state(self):
        """Language switch should stay in current state."""
        for state in [State.WAITING_ANSWER, State.HINTING, State.EXPLAINING]:
            r = get_transition(state, "LANGUAGE", make_session())
            assert r["action"] == Action.SWITCH_LANGUAGE
            assert r["next_state"] == state

    def test_unsupported_language_stays_in_state(self):
        for state in [State.WAITING_ANSWER, State.HINTING, State.EXPLAINING]:
            r = get_transition(state, "LANG_UNSUPPORTED", make_session())
            assert r["action"] == Action.REJECT_LANGUAGE
            assert r["next_state"] == state

    def test_time_limit_25_min(self):
        """After 25 minutes, session must end."""
        r = get_transition(State.WAITING_ANSWER, "ANSWER", make_session(duration_minutes=25))
        assert r["action"] == Action.END_SESSION
        assert r["next_state"] == State.ENDED

    def test_time_limit_30_min(self):
        r = get_transition(State.HINTING, "ANSWER", make_session(duration_minutes=30))
        assert r["action"] == Action.END_SESSION

    def test_under_time_limit_ok(self):
        """24 minutes should NOT trigger time limit."""
        r = get_transition(State.WAITING_ANSWER, "ANSWER", make_session(duration_minutes=24))
        assert r["action"] != Action.END_SESSION

    def test_ended_state_stays_ended(self):
        r = get_transition(State.ENDED, "ANSWER", make_session())
        assert r["action"] == Action.END_SESSION
        assert r["next_state"] == State.ENDED


# ============================================================
# WAITING_ANSWER STATE
# ============================================================

class TestWaitingAnswer:

    def test_answer_triggers_judge(self):
        r = get_transition(State.WAITING_ANSWER, "ANSWER", make_session())
        assert r["action"] == Action.JUDGE_AND_RESPOND

    def test_first_idk_encourages(self):
        r = get_transition(State.WAITING_ANSWER, "IDK", make_session(idk_count=0))
        assert r["action"] == Action.ENCOURAGE
        assert r["next_state"] == State.WAITING_ANSWER

    def test_second_idk_gives_hint(self):
        r = get_transition(State.WAITING_ANSWER, "IDK", make_session(idk_count=2))
        assert r["action"] == Action.GIVE_HINT
        assert r["next_state"] == State.HINTING

    def test_third_idk_explains(self):
        """Circuit breaker: 3+ IDKs → explain solution."""
        r = get_transition(State.WAITING_ANSWER, "IDK", make_session(idk_count=3))
        assert r["action"] == Action.EXPLAIN_SOLUTION
        assert r["next_state"] == State.EXPLAINING

    def test_ack_while_waiting_reasks(self):
        """ACK when waiting for answer → re-ask the question."""
        r = get_transition(State.WAITING_ANSWER, "ACK", make_session())
        assert r["action"] == Action.RE_ASK
        assert r["next_state"] == State.WAITING_ANSWER

    def test_troll_redirects(self):
        r = get_transition(State.WAITING_ANSWER, "TROLL", make_session())
        assert r["action"] == Action.REDIRECT_TROLL

    def test_troll_streak_3_offers_exit(self):
        """3+ trolls → offer exit."""
        r = get_transition(State.WAITING_ANSWER, "TROLL", make_session(offtopic_streak=2))
        assert r["action"] == Action.OFFER_EXIT

    def test_offtopic_redirects(self):
        r = get_transition(State.WAITING_ANSWER, "OFFTOPIC", make_session())
        assert r["action"] == Action.REDIRECT_OFFTOPIC

    def test_offtopic_streak_3_offers_exit(self):
        r = get_transition(State.WAITING_ANSWER, "OFFTOPIC", make_session(offtopic_streak=2))
        assert r["action"] == Action.OFFER_EXIT

    # --- v5.0: CONCEPT_REQUEST ---
    def test_concept_request_teaches(self):
        r = get_transition(State.WAITING_ANSWER, "CONCEPT_REQUEST", make_session())
        assert r["action"] == Action.TEACH_CONCEPT
        assert r["next_state"] == State.WAITING_ANSWER

    def test_concept_request_returns_to_waiting(self):
        """After teaching concept, student should still answer the question."""
        r = get_transition(State.WAITING_ANSWER, "CONCEPT_REQUEST", make_session())
        assert r["next_state"] == State.WAITING_ANSWER


# ============================================================
# HINTING STATE
# ============================================================

class TestHinting:

    def test_answer_after_hint(self):
        r = get_transition(State.HINTING, "ANSWER", make_session(hint_count=1))
        assert r["action"] == Action.JUDGE_AND_RESPOND

    def test_ack_after_first_hint_reasks(self):
        """After first hint, ACK → re-ask to try answering."""
        r = get_transition(State.HINTING, "ACK", make_session(hint_count=0))
        assert r["action"] == Action.RE_ASK

    def test_ack_after_two_hints_moves_on(self):
        """After 2 hints, ACK → move to next question."""
        r = get_transition(State.HINTING, "ACK", make_session(hint_count=2))
        assert r["action"] == Action.MOVE_TO_NEXT
        assert r["next_state"] == State.TRANSITIONING

    def test_idk_after_hints_explains(self):
        """IDK after 2 hints → explain solution."""
        r = get_transition(State.HINTING, "IDK", make_session(idk_count=1, hint_count=2))
        assert r["action"] == Action.EXPLAIN_SOLUTION
        assert r["next_state"] == State.EXPLAINING

    def test_idk_gives_more_hints(self):
        """IDK with hint_count < 2 → give another hint."""
        r = get_transition(State.HINTING, "IDK", make_session(idk_count=1, hint_count=0))
        assert r["action"] == Action.GIVE_HINT

    # --- v5.0: CONCEPT_REQUEST from HINTING ---
    def test_concept_request_from_hinting(self):
        r = get_transition(State.HINTING, "CONCEPT_REQUEST", make_session())
        assert r["action"] == Action.TEACH_CONCEPT
        assert r["next_state"] == State.WAITING_ANSWER


# ============================================================
# EXPLAINING STATE
# ============================================================

class TestExplaining:

    def test_ack_after_explain_moves_on(self):
        r = get_transition(State.EXPLAINING, "ACK", make_session())
        assert r["action"] == Action.MOVE_TO_NEXT
        assert r["next_state"] == State.TRANSITIONING

    def test_idk_after_explain_moves_on(self):
        """Even if confused after explanation, move on."""
        r = get_transition(State.EXPLAINING, "IDK", make_session())
        assert r["action"] == Action.MOVE_TO_NEXT

    def test_answer_after_explain_moves_on(self):
        """Any answer after explaining → treat as move on."""
        r = get_transition(State.EXPLAINING, "ANSWER", make_session())
        assert r["action"] == Action.MOVE_TO_NEXT

    def test_troll_after_explain_moves_on(self):
        r = get_transition(State.EXPLAINING, "TROLL", make_session())
        assert r["action"] == Action.MOVE_TO_NEXT

    # --- v5.0: CONCEPT_REQUEST from EXPLAINING ---
    def test_concept_request_from_explaining(self):
        r = get_transition(State.EXPLAINING, "CONCEPT_REQUEST", make_session())
        assert r["action"] == Action.TEACH_CONCEPT
        assert r["next_state"] == State.WAITING_ANSWER


# ============================================================
# TRANSITIONING STATE
# ============================================================

class TestTransitioning:
    def test_answer_in_transitioning(self):
        """Transitioning uses same logic as waiting_answer."""
        r = get_transition(State.TRANSITIONING, "ANSWER", make_session())
        assert r["action"] == Action.JUDGE_AND_RESPOND


# ============================================================
# CIRCUIT BREAKER COMBINATIONS
# ============================================================

class TestCircuitBreakers:
    """Test that circuit breakers fire correctly."""

    def test_idk_circuit_breaker(self):
        """3 IDKs → force explain."""
        r = get_transition(State.WAITING_ANSWER, "IDK", make_session(idk_count=3))
        assert r["action"] == Action.EXPLAIN_SOLUTION
        assert r["meta"].get("force") is True

    def test_idk_after_hints_circuit_breaker(self):
        """3 IDKs after hints → explain."""
        r = get_transition(State.HINTING, "IDK", make_session(idk_count=3, hint_count=1))
        assert r["action"] == Action.EXPLAIN_SOLUTION

    def test_troll_circuit_breaker(self):
        """3 trolls → offer exit."""
        r = get_transition(State.WAITING_ANSWER, "TROLL", make_session(offtopic_streak=2))
        assert r["action"] == Action.OFFER_EXIT

    def test_offtopic_circuit_breaker(self):
        """3 off-topics → offer exit."""
        r = get_transition(State.WAITING_ANSWER, "OFFTOPIC", make_session(offtopic_streak=2))
        assert r["action"] == Action.OFFER_EXIT


# ============================================================
# TEACH_CONCEPT ACTION EXISTS
# ============================================================

class TestTeachConceptAction:
    """Verify TEACH_CONCEPT is a valid action in the enum."""

    def test_action_exists(self):
        assert hasattr(Action, "TEACH_CONCEPT")
        assert Action.TEACH_CONCEPT == "teach_concept"

    def test_concept_request_from_all_active_states(self):
        """CONCEPT_REQUEST should return TEACH_CONCEPT from all active states."""
        active_states = [State.WAITING_ANSWER, State.HINTING, State.EXPLAINING]
        for state in active_states:
            r = get_transition(state, "CONCEPT_REQUEST", make_session())
            assert r["action"] == Action.TEACH_CONCEPT, \
                f"CONCEPT_REQUEST in {state} returned {r['action']}, expected TEACH_CONCEPT"

    def test_concept_request_always_returns_to_waiting(self):
        """After teaching, student should be in WAITING_ANSWER to try the question."""
        for state in [State.WAITING_ANSWER, State.HINTING, State.EXPLAINING]:
            r = get_transition(state, "CONCEPT_REQUEST", make_session())
            assert r["next_state"] == State.WAITING_ANSWER, \
                f"CONCEPT_REQUEST in {state} next_state={r['next_state']}, expected WAITING_ANSWER"


# ============================================================
# REGRESSION: LIVE SESSION SCENARIOS
# ============================================================

class TestLiveSessionScenarios:
    """End-to-end state transition sequences from real sessions."""

    def test_student_asks_concept_while_waiting(self):
        """Student: 'what are rational numbers?' while waiting for answer."""
        session = make_session()
        r = get_transition(State.WAITING_ANSWER, "CONCEPT_REQUEST", session)
        assert r["action"] == Action.TEACH_CONCEPT
        # After teaching, student gets another chance
        assert r["next_state"] == State.WAITING_ANSWER

    def test_student_gives_up_gradually(self):
        """IDK → encourage → IDK → hint → IDK → explain."""
        session = make_session(idk_count=0)
        r1 = get_transition(State.WAITING_ANSWER, "IDK", session)
        assert r1["action"] == Action.ENCOURAGE

        session["idk_count"] = 2
        r2 = get_transition(State.WAITING_ANSWER, "IDK", session)
        assert r2["action"] == Action.GIVE_HINT

        session["idk_count"] = 3
        r3 = get_transition(State.WAITING_ANSWER, "IDK", session)
        assert r3["action"] == Action.EXPLAIN_SOLUTION

    def test_student_trolls_then_stops(self):
        """Troll 3x → offer exit → then STOP ends it."""
        session = make_session(offtopic_streak=2)
        r1 = get_transition(State.WAITING_ANSWER, "TROLL", session)
        assert r1["action"] == Action.OFFER_EXIT

        r2 = get_transition(State.WAITING_ANSWER, "STOP", session)
        assert r2["action"] == Action.END_SESSION

    def test_bye_always_ends_immediately(self):
        """'bye' should end session from ANY state, regardless of context."""
        for state in [State.WAITING_ANSWER, State.HINTING, State.EXPLAINING, State.TRANSITIONING]:
            r = get_transition(state, "STOP", make_session())
            assert r["action"] == Action.END_SESSION
            assert r["next_state"] == State.ENDED
