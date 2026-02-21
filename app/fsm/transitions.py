"""
IDNA EdTech v8.0 — Complete State × Input Transition Matrix

6 states × 10 input categories = 60 combinations.
Every single one is defined. No gaps. No KeyError possible.

This is the core of the v8.0 architecture.
"""

from dataclasses import dataclass
from typing import Optional
from app.state.session import TutorState


# ─── Input Categories (from classifier) ─────────────────────────────────────

INPUT_CATEGORIES = frozenset({
    "ACK",              # "haan", "samajh aaya", "yes", "okay"
    "IDK",              # "pata nahi", "nahi samjha", "I don't know"
    "REPEAT",           # "phir se", "dobara", "repeat please"
    "ANSWER",           # Any numeric/mathematical response
    "LANGUAGE_SWITCH",  # "English mein bolo", "Hindi mein"
    "CONCEPT_REQUEST",  # "explain karo", "ye kya hai"
    "COMFORT",          # "bahut mushkil", "I give up"
    "STOP",             # "bye", "band karo"
    "TROLL",            # Off-topic nonsense
    "GARBLED",          # Low confidence STT
})


@dataclass
class TransitionResult:
    """
    Result of a state transition lookup.

    next_state: Where to go next
    action: What the handler should do
    handler_name: Which handler function to call
    special: Any special flags (e.g., "store_language", "increment_reteach")
    """
    next_state: TutorState
    action: str
    handler_name: str
    special: Optional[str] = None


# ─── The Complete Transition Matrix ──────────────────────────────────────────

TRANSITIONS: dict[tuple[TutorState, str], TransitionResult] = {
    # ═══════════════════════════════════════════════════════════════════════
    # GREETING × All Inputs
    # ═══════════════════════════════════════════════════════════════════════
    (TutorState.GREETING, "ACK"): TransitionResult(
        next_state=TutorState.TEACHING,
        action="start_teaching",
        handler_name="handle_greeting",
    ),
    (TutorState.GREETING, "IDK"): TransitionResult(
        next_state=TutorState.TEACHING,
        action="start_teaching",
        handler_name="handle_greeting",
        special="treat_as_ack",
    ),
    (TutorState.GREETING, "REPEAT"): TransitionResult(
        next_state=TutorState.GREETING,
        action="re_greet",
        handler_name="handle_greeting",
    ),
    (TutorState.GREETING, "ANSWER"): TransitionResult(
        next_state=TutorState.TEACHING,
        action="redirect_to_teaching",
        handler_name="handle_greeting",
        special="ignore_answer",
    ),
    (TutorState.GREETING, "LANGUAGE_SWITCH"): TransitionResult(
        next_state=TutorState.GREETING,
        action="re_greet_in_language",
        handler_name="handle_greeting",
        special="store_language",
    ),
    (TutorState.GREETING, "CONCEPT_REQUEST"): TransitionResult(
        next_state=TutorState.TEACHING,
        action="start_teaching",
        handler_name="handle_greeting",
    ),
    (TutorState.GREETING, "COMFORT"): TransitionResult(
        next_state=TutorState.GREETING,
        action="comfort_and_stay",
        handler_name="handle_greeting",
    ),
    (TutorState.GREETING, "STOP"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="end_session",
        handler_name="handle_greeting",
    ),
    (TutorState.GREETING, "TROLL"): TransitionResult(
        next_state=TutorState.TEACHING,
        action="redirect_to_teaching",
        handler_name="handle_greeting",
    ),
    (TutorState.GREETING, "GARBLED"): TransitionResult(
        next_state=TutorState.GREETING,
        action="ask_repeat",
        handler_name="handle_greeting",
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # TEACHING × All Inputs
    # ═══════════════════════════════════════════════════════════════════════
    (TutorState.TEACHING, "ACK"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="ask_question",
        handler_name="handle_teaching",
    ),
    (TutorState.TEACHING, "IDK"): TransitionResult(
        next_state=TutorState.TEACHING,  # May change to WAITING_ANSWER if reteach_count >= 3
        action="reteach",
        handler_name="handle_teaching",
        special="increment_reteach",
    ),
    (TutorState.TEACHING, "REPEAT"): TransitionResult(
        next_state=TutorState.TEACHING,  # May change to WAITING_ANSWER if reteach_count >= 3
        action="reteach",
        handler_name="handle_teaching",
        special="increment_reteach",
    ),
    (TutorState.TEACHING, "ANSWER"): TransitionResult(
        next_state=TutorState.NEXT_QUESTION,  # If correct; handler decides
        action="evaluate_premature_answer",
        handler_name="handle_teaching",
        special="evaluate_answer",
    ),
    (TutorState.TEACHING, "LANGUAGE_SWITCH"): TransitionResult(
        next_state=TutorState.TEACHING,
        action="reteach_in_language",
        handler_name="handle_teaching",
        special="store_language",  # Do NOT increment reteach_count
    ),
    (TutorState.TEACHING, "CONCEPT_REQUEST"): TransitionResult(
        next_state=TutorState.TEACHING,
        action="reteach",
        handler_name="handle_teaching",
        special="increment_reteach",
    ),
    (TutorState.TEACHING, "COMFORT"): TransitionResult(
        next_state=TutorState.TEACHING,
        action="comfort_then_teach",
        handler_name="handle_teaching",
        special="empathy_first",
    ),
    (TutorState.TEACHING, "STOP"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="end_session",
        handler_name="handle_teaching",
    ),
    (TutorState.TEACHING, "TROLL"): TransitionResult(
        next_state=TutorState.TEACHING,
        action="redirect_and_teach",
        handler_name="handle_teaching",
    ),
    (TutorState.TEACHING, "GARBLED"): TransitionResult(
        next_state=TutorState.TEACHING,
        action="ask_repeat",
        handler_name="handle_teaching",
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # WAITING_ANSWER × All Inputs
    # ═══════════════════════════════════════════════════════════════════════
    (TutorState.WAITING_ANSWER, "ACK"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="reread_question",
        handler_name="handle_waiting_answer",
    ),
    (TutorState.WAITING_ANSWER, "IDK"): TransitionResult(
        next_state=TutorState.HINT,
        action="give_hint",
        handler_name="handle_waiting_answer",
    ),
    (TutorState.WAITING_ANSWER, "REPEAT"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="reread_question",
        handler_name="handle_waiting_answer",
    ),
    (TutorState.WAITING_ANSWER, "ANSWER"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,  # Handler decides based on correctness
        action="evaluate_answer",
        handler_name="handle_waiting_answer",
        special="use_llm_evaluator",
    ),
    (TutorState.WAITING_ANSWER, "LANGUAGE_SWITCH"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="reread_in_language",
        handler_name="handle_waiting_answer",
        special="store_language",
    ),
    (TutorState.WAITING_ANSWER, "CONCEPT_REQUEST"): TransitionResult(
        next_state=TutorState.TEACHING,
        action="go_back_to_teaching",
        handler_name="handle_waiting_answer",
        special="reset_reteach",
    ),
    (TutorState.WAITING_ANSWER, "COMFORT"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="comfort_then_reread",
        handler_name="handle_waiting_answer",
    ),
    (TutorState.WAITING_ANSWER, "STOP"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="end_session",
        handler_name="handle_waiting_answer",
    ),
    (TutorState.WAITING_ANSWER, "TROLL"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="redirect_and_reread",
        handler_name="handle_waiting_answer",
    ),
    (TutorState.WAITING_ANSWER, "GARBLED"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="ask_repeat",
        handler_name="handle_waiting_answer",
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # HINT × All Inputs
    # ═══════════════════════════════════════════════════════════════════════
    (TutorState.HINT, "ACK"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="return_to_question",
        handler_name="handle_hint",
    ),
    (TutorState.HINT, "IDK"): TransitionResult(
        next_state=TutorState.HINT,  # May go to NEXT_QUESTION after solution
        action="give_next_hint",
        handler_name="handle_hint",
    ),
    (TutorState.HINT, "REPEAT"): TransitionResult(
        next_state=TutorState.HINT,
        action="reread_hint",
        handler_name="handle_hint",
    ),
    (TutorState.HINT, "ANSWER"): TransitionResult(
        next_state=TutorState.HINT,  # Handler decides based on correctness
        action="evaluate_answer",
        handler_name="handle_hint",
        special="use_llm_evaluator",
    ),
    (TutorState.HINT, "LANGUAGE_SWITCH"): TransitionResult(
        next_state=TutorState.HINT,
        action="reread_hint_in_language",
        handler_name="handle_hint",
        special="store_language",
    ),
    (TutorState.HINT, "CONCEPT_REQUEST"): TransitionResult(
        next_state=TutorState.TEACHING,
        action="go_back_to_teaching",
        handler_name="handle_hint",
        special="reset_reteach",
    ),
    (TutorState.HINT, "COMFORT"): TransitionResult(
        next_state=TutorState.HINT,
        action="comfort_and_simplify_hint",
        handler_name="handle_hint",
    ),
    (TutorState.HINT, "STOP"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="end_session",
        handler_name="handle_hint",
    ),
    (TutorState.HINT, "TROLL"): TransitionResult(
        next_state=TutorState.HINT,
        action="redirect_and_reread_hint",
        handler_name="handle_hint",
    ),
    (TutorState.HINT, "GARBLED"): TransitionResult(
        next_state=TutorState.HINT,
        action="ask_repeat",
        handler_name="handle_hint",
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # NEXT_QUESTION × All Inputs (Transient state)
    # ═══════════════════════════════════════════════════════════════════════
    (TutorState.NEXT_QUESTION, "ACK"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,  # Handler checks if new concept → TEACHING
        action="proceed_to_next",
        handler_name="handle_next_question",
    ),
    (TutorState.NEXT_QUESTION, "IDK"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="proceed_to_next",
        handler_name="handle_next_question",
    ),
    (TutorState.NEXT_QUESTION, "REPEAT"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="proceed_to_next",
        handler_name="handle_next_question",
    ),
    (TutorState.NEXT_QUESTION, "ANSWER"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="proceed_to_next",
        handler_name="handle_next_question",
    ),
    (TutorState.NEXT_QUESTION, "LANGUAGE_SWITCH"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="proceed_in_language",
        handler_name="handle_next_question",
        special="store_language",
    ),
    (TutorState.NEXT_QUESTION, "CONCEPT_REQUEST"): TransitionResult(
        next_state=TutorState.TEACHING,
        action="go_to_teaching",
        handler_name="handle_next_question",
    ),
    (TutorState.NEXT_QUESTION, "COMFORT"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="comfort_and_proceed",
        handler_name="handle_next_question",
    ),
    (TutorState.NEXT_QUESTION, "STOP"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="end_session",
        handler_name="handle_next_question",
    ),
    (TutorState.NEXT_QUESTION, "TROLL"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="proceed_to_next",
        handler_name="handle_next_question",
    ),
    (TutorState.NEXT_QUESTION, "GARBLED"): TransitionResult(
        next_state=TutorState.WAITING_ANSWER,
        action="proceed_to_next",
        handler_name="handle_next_question",
    ),

    # ═══════════════════════════════════════════════════════════════════════
    # SESSION_END × All Inputs (Terminal state)
    # ═══════════════════════════════════════════════════════════════════════
    (TutorState.SESSION_END, "ACK"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="farewell",
        handler_name="handle_session_end",
    ),
    (TutorState.SESSION_END, "IDK"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="farewell",
        handler_name="handle_session_end",
    ),
    (TutorState.SESSION_END, "REPEAT"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="farewell",
        handler_name="handle_session_end",
    ),
    (TutorState.SESSION_END, "ANSWER"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="farewell",
        handler_name="handle_session_end",
    ),
    (TutorState.SESSION_END, "LANGUAGE_SWITCH"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="farewell",
        handler_name="handle_session_end",
    ),
    (TutorState.SESSION_END, "CONCEPT_REQUEST"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="farewell",
        handler_name="handle_session_end",
    ),
    (TutorState.SESSION_END, "COMFORT"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="farewell",
        handler_name="handle_session_end",
    ),
    (TutorState.SESSION_END, "STOP"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="farewell",
        handler_name="handle_session_end",
    ),
    (TutorState.SESSION_END, "TROLL"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="farewell",
        handler_name="handle_session_end",
    ),
    (TutorState.SESSION_END, "GARBLED"): TransitionResult(
        next_state=TutorState.SESSION_END,
        action="farewell",
        handler_name="handle_session_end",
    ),
}


def get_transition(state: TutorState, input_category: str) -> TransitionResult:
    """
    Get the transition result for a state × input combination.

    This function is guaranteed to never raise KeyError because all 60
    combinations are defined in the TRANSITIONS dict.

    Args:
        state: Current TutorState
        input_category: Classified input category

    Returns:
        TransitionResult with next_state, action, handler_name, and special flags
    """
    # Normalize category to uppercase
    category = input_category.upper() if isinstance(input_category, str) else input_category

    # Ensure state is TutorState enum
    if isinstance(state, str):
        state = TutorState(state)

    # Lookup — guaranteed to exist
    key = (state, category)
    if key in TRANSITIONS:
        return TRANSITIONS[key]

    # Fallback for unknown categories (should never happen with proper classifier)
    # Map to GARBLED to handle gracefully
    return TRANSITIONS[(state, "GARBLED")]


def validate_matrix_completeness() -> bool:
    """
    Verify that all 60 state × input combinations are defined.

    Returns True if complete, raises AssertionError if not.
    """
    states = list(TutorState)
    categories = list(INPUT_CATEGORIES)

    missing = []
    for state in states:
        for category in categories:
            if (state, category) not in TRANSITIONS:
                missing.append((state.value, category))

    if missing:
        raise AssertionError(f"Missing transitions: {missing}")

    expected = len(states) * len(categories)
    actual = len(TRANSITIONS)

    if actual != expected:
        raise AssertionError(f"Expected {expected} transitions, got {actual}")

    return True
