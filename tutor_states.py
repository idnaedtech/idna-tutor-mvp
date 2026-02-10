"""
IDNA Tutor State Machine
=========================
Every session is in exactly one state at all times.
Every input causes exactly one transition.
No ambiguity. No spaghetti.

States:
  GREETING          → session just started, Didi greets + reads Q1
  WAITING_ANSWER    → question has been read, waiting for student to answer
  HINTING           → gave a hint, waiting for student to try again
  EXPLAINING        → explained the full answer, waiting for ack before moving on
  TRANSITIONING     → moving to next question
  ENDED             → session is over

Inputs (from input_classifier):
  ANSWER, IDK, ACK, TROLL, OFFTOPIC, STOP,
  LANGUAGE, LANG_UNSUPPORTED
"""

from enum import Enum


class State(str, Enum):
    GREETING = "GREETING"
    WAITING_ANSWER = "WAITING_ANSWER"
    HINTING = "HINTING"
    EXPLAINING = "EXPLAINING"
    TRANSITIONING = "TRANSITIONING"
    ENDED = "ENDED"


class Action(str, Enum):
    """What the system should do. Maps to LLM speech generation."""
    GREET_AND_ASK = "greet_and_ask"
    JUDGE_AND_RESPOND = "judge_and_respond"      # LLM judges answer + picks tool
    GIVE_HINT = "give_hint"
    EXPLAIN_SOLUTION = "explain_solution"
    ENCOURAGE = "encourage"
    MOVE_TO_NEXT = "move_to_next"                # Ack received, advance question
    REDIRECT_TROLL = "redirect_troll"
    REDIRECT_OFFTOPIC = "redirect_offtopic"
    SWITCH_LANGUAGE = "switch_language"
    REJECT_LANGUAGE = "reject_language"
    OFFER_EXIT = "offer_exit"                    # Too many trolls
    END_SESSION = "end_session"
    RE_ASK = "re_ask"                            # After hint ack, ask to try again


def get_transition(state: State, category: str, session: dict) -> dict:
    """
    Pure function. Given current state + input category + session context,
    returns: { "action": Action, "next_state": State, "meta": dict }

    No side effects. No LLM calls. Just logic.
    """
    hint_count = session.get("hint_count", 0)
    idk_count = session.get("idk_count", 0)
    attempt_count = session.get("attempt_count", 0)
    offtopic_streak = session.get("offtopic_streak", 0)
    duration = session.get("duration_minutes", 0)
    questions_left = session.get("total_questions", 0) - session.get("current_question_index", 0) - 1

    # ==============================
    # UNIVERSAL TRANSITIONS (any state)
    # ==============================

    # STOP always ends
    if category == "STOP":
        return {
            "action": Action.END_SESSION,
            "next_state": State.ENDED,
            "meta": {"reason": "student_requested"}
        }

    # Language switch — handle and stay in current state
    if category == "LANGUAGE":
        return {
            "action": Action.SWITCH_LANGUAGE,
            "next_state": state,  # Stay in current state
            "meta": {}
        }

    # Unsupported language — handle and stay
    if category == "LANG_UNSUPPORTED":
        return {
            "action": Action.REJECT_LANGUAGE,
            "next_state": state,
            "meta": {}
        }

    # Time limit check (25 min)
    if duration >= 25:
        return {
            "action": Action.END_SESSION,
            "next_state": State.ENDED,
            "meta": {"reason": "time_limit"}
        }

    # ==============================
    # STATE-SPECIFIC TRANSITIONS
    # ==============================

    if state == State.GREETING:
        # Greeting is handled by start_session, shouldn't get input here
        # If we do, treat as waiting for answer
        return _waiting_answer_transition(category, session)

    elif state == State.WAITING_ANSWER:
        return _waiting_answer_transition(category, session)

    elif state == State.HINTING:
        return _hinting_transition(category, session)

    elif state == State.EXPLAINING:
        return _explaining_transition(category, session)

    elif state == State.TRANSITIONING:
        # Same as waiting — we've moved to a new question
        return _waiting_answer_transition(category, session)

    elif state == State.ENDED:
        return {
            "action": Action.END_SESSION,
            "next_state": State.ENDED,
            "meta": {"reason": "already_ended"}
        }

    # Fallback
    return _waiting_answer_transition(category, session)


def _waiting_answer_transition(category: str, session: dict) -> dict:
    """Student is expected to answer the current question."""
    idk_count = session.get("idk_count", 0)
    hint_count = session.get("hint_count", 0)
    attempt_count = session.get("attempt_count", 0)
    offtopic_streak = session.get("offtopic_streak", 0)

    if category == "ANSWER":
        # Let LLM judge and pick tool
        return {
            "action": Action.JUDGE_AND_RESPOND,
            "next_state": State.WAITING_ANSWER,  # Will be updated based on LLM result
            "meta": {}
        }

    elif category == "IDK":
        # idk_count already incremented in agentic_tutor.py before this runs
        if idk_count >= 3:
            # Circuit breaker: explain and move on
            return {
                "action": Action.EXPLAIN_SOLUTION,
                "next_state": State.EXPLAINING,
                "meta": {"reason": "stuck_3_idks", "force": True}
            }
        elif idk_count >= 2 or hint_count >= 1:
            # Give a hint
            return {
                "action": Action.GIVE_HINT,
                "next_state": State.HINTING,
                "meta": {"hint_level": min(hint_count + 1, 2)}
            }
        else:
            # First IDK — encourage
            return {
                "action": Action.ENCOURAGE,
                "next_state": State.WAITING_ANSWER,
                "meta": {}
            }

    elif category == "ACK":
        # Ack while waiting for answer — they might be responding to nothing
        # Just re-ask the question
        return {
            "action": Action.RE_ASK,
            "next_state": State.WAITING_ANSWER,
            "meta": {}
        }

    elif category == "TROLL":
        streak = offtopic_streak + 1
        if streak >= 3:
            return {
                "action": Action.OFFER_EXIT,
                "next_state": State.WAITING_ANSWER,
                "meta": {}
            }
        return {
            "action": Action.REDIRECT_TROLL,
            "next_state": State.WAITING_ANSWER,
            "meta": {}
        }

    elif category == "OFFTOPIC":
        streak = offtopic_streak + 1
        if streak >= 3:
            return {
                "action": Action.OFFER_EXIT,
                "next_state": State.WAITING_ANSWER,
                "meta": {}
            }
        return {
            "action": Action.REDIRECT_OFFTOPIC,
            "next_state": State.WAITING_ANSWER,
            "meta": {}
        }

    # Fallback
    return {
        "action": Action.JUDGE_AND_RESPOND,
        "next_state": State.WAITING_ANSWER,
        "meta": {}
    }


def _hinting_transition(category: str, session: dict) -> dict:
    """We gave a hint, waiting for student to try again."""
    hint_count = session.get("hint_count", 0)
    idk_count = session.get("idk_count", 0)

    if category == "ANSWER":
        # They're trying again — let LLM judge
        return {
            "action": Action.JUDGE_AND_RESPOND,
            "next_state": State.WAITING_ANSWER,
            "meta": {}
        }

    elif category == "ACK":
        if hint_count >= 2:
            # They acknowledged after 2 hints — they probably get it, move on
            return {
                "action": Action.MOVE_TO_NEXT,
                "next_state": State.TRANSITIONING,
                "meta": {}
            }
        else:
            # Ack after first hint — ask them to try answering now
            return {
                "action": Action.RE_ASK,
                "next_state": State.WAITING_ANSWER,
                "meta": {"after_hint": True}
            }

    elif category == "IDK":
        # idk_count already incremented before this runs
        if idk_count >= 3 or hint_count >= 2:
            return {
                "action": Action.EXPLAIN_SOLUTION,
                "next_state": State.EXPLAINING,
                "meta": {"reason": "stuck_after_hints", "force": True}
            }
        return {
            "action": Action.GIVE_HINT,
            "next_state": State.HINTING,
            "meta": {"hint_level": min(hint_count + 1, 2)}
        }

    elif category in ("TROLL", "OFFTOPIC"):
        streak = session.get("offtopic_streak", 0) + 1
        if streak >= 3:
            return {"action": Action.OFFER_EXIT, "next_state": State.HINTING, "meta": {}}
        return {
            "action": Action.REDIRECT_TROLL if category == "TROLL" else Action.REDIRECT_OFFTOPIC,
            "next_state": State.HINTING,
            "meta": {}
        }

    return {
        "action": Action.JUDGE_AND_RESPOND,
        "next_state": State.WAITING_ANSWER,
        "meta": {}
    }


def _explaining_transition(category: str, session: dict) -> dict:
    """We explained the solution. Waiting for student to acknowledge, then we move on."""

    if category == "ACK":
        # Good — they understood. Move to next question.
        return {
            "action": Action.MOVE_TO_NEXT,
            "next_state": State.TRANSITIONING,
            "meta": {}
        }

    elif category == "IDK":
        # They're asking again after we explained — just move on
        return {
            "action": Action.MOVE_TO_NEXT,
            "next_state": State.TRANSITIONING,
            "meta": {"note": "moving_on_despite_confusion"}
        }

    elif category == "ANSWER":
        # They're trying to answer the NEXT question maybe? Or still on this one.
        # Since we explained, treat any input as "move on"
        return {
            "action": Action.MOVE_TO_NEXT,
            "next_state": State.TRANSITIONING,
            "meta": {}
        }

    elif category in ("TROLL", "OFFTOPIC"):
        # After explanation, just move on — don't loop
        return {
            "action": Action.MOVE_TO_NEXT,
            "next_state": State.TRANSITIONING,
            "meta": {}
        }

    # Default: move on
    return {
        "action": Action.MOVE_TO_NEXT,
        "next_state": State.TRANSITIONING,
        "meta": {}
    }
