"""
IDNA EdTech v9.0 — State Handlers (LLM-Powered)

ARCHITECTURAL CHANGE from v8.0:
- Before: Handlers returned hardcoded Hindi strings
- After:  Handlers return None + "_llm_instruction" dict → router calls LLM

Each handler returns:
    - response_text: str OR None (None means "use LLM")
    - new_state: TutorState
    - session_updates: dict (includes _llm_instruction if response is None)

The handlers use Content Bank material per teach_material_index.
LLM generation happens in the router, not here.
"""

import logging
from typing import Tuple, Dict, Any, Optional, Callable

from app.state.session import SessionState, TutorState
from app.fsm.transitions import get_transition, TransitionResult

logger = logging.getLogger("idna.fsm.handlers")


# ─── Content Bank Material Getters ───────────────────────────────────────────

def get_cb_material_for_index(
    concept_id: str,
    teach_material_index: int,
    content_bank,
) -> Dict[str, Any]:
    """
    Get Content Bank material based on teach_material_index.

    Index 0: definition_tts + hook
    Index 1: analogy + examples[0]
    Index 2: examples[1] or vedic_trick + key_insight
    Index >= 3: Force advance message

    Returns dict with 'text' and 'type' keys.
    """
    if content_bank is None:
        return {"text": "", "type": "fallback"}

    concept = content_bank.get_concept(concept_id)
    if not concept:
        return {"text": "", "type": "fallback"}

    methodology = concept.get("teaching_methodology", {})
    examples = concept.get("examples", [])

    if teach_material_index == 0:
        # First teach: definition + hook
        definition = content_bank.get_definition_tts(concept_id) or ""
        hook = methodology.get("hook", "")
        text = f"{definition} {hook}".strip()
        return {"text": text, "type": "definition", "raw": {"definition": definition, "hook": hook}}

    elif teach_material_index == 1:
        # First reteach: analogy + first example
        analogy = methodology.get("analogy", "")
        example_text = ""
        if examples:
            example_text = examples[0].get("solution_tts", "")
        text = f"{analogy} {example_text}".strip()
        return {"text": text, "type": "analogy", "raw": {"analogy": analogy, "example": example_text}}

    elif teach_material_index == 2:
        # Second reteach: second example or vedic_trick
        vedic_trick = methodology.get("vedic_trick", "")
        key_insight = concept.get("key_insight", "")
        example_text = ""
        if len(examples) > 1:
            example_text = examples[1].get("solution_tts", "")

        text = f"{example_text} {vedic_trick} {key_insight}".strip()
        return {"text": text, "type": "advanced", "raw": {"vedic_trick": vedic_trick, "key_insight": key_insight}}

    else:
        # Force advance
        return {
            "text": "",
            "type": "force_advance",
        }


def get_cb_hint(question_id: str, hint_index: int, content_bank) -> str:
    """
    Get hint for a question based on hints_given.

    hints_given = 0 → hints[0] (direction hint)
    hints_given = 1 → hints[1] (step-by-step hint)
    hints_given = 2 → full_solution_tts
    """
    if content_bank is None:
        return ""

    hints = content_bank.get_hints(question_id)

    if hint_index < len(hints):
        return hints[hint_index]
    elif hint_index >= 2:
        return content_bank.get_full_solution_tts(question_id) or ""
    else:
        return ""


# ─── State Handlers ──────────────────────────────────────────────────────────

async def handle_greeting(
    session: SessionState,
    input_category: str,
    extras: Dict[str, Any],
    text: str,
    content_bank=None,
    llm_call: Callable = None,
) -> Tuple[Optional[str], TutorState, Dict[str, Any]]:
    """
    Handle inputs in GREETING state.

    Possible transitions:
    - ACK/IDK/CONCEPT_REQUEST/ANSWER/TROLL → TEACHING (start learning)
    - REPEAT → GREETING (re-greet)
    - LANGUAGE_SWITCH → GREETING (re-greet in new language)
    - COMFORT → GREETING (comfort then stay)
    - STOP → SESSION_END
    - GARBLED → GREETING (ask repeat)
    """
    transition = get_transition(TutorState.GREETING, input_category)
    session_updates = {}

    # Handle language switch
    if transition.special == "store_language" and extras.get("preferred_language"):
        session_updates["preferred_language"] = extras["preferred_language"]
        session_updates["_llm_instruction"] = {
            "action": "language_switch_ack",
            "target_language": extras["preferred_language"],
            "brief_topic_context": f"we're about to learn {session.current_concept_id or 'mathematics'}",
        }
        return None, transition.next_state, session_updates

    # Handle STOP
    if transition.action == "end_session":
        session_updates["_llm_instruction"] = {
            "action": "wrap_up",
        }
        return None, TutorState.SESSION_END, session_updates

    # Handle GARBLED
    if transition.action == "ask_repeat":
        session_updates["_llm_instruction"] = {
            "action": "handle_garbled",
        }
        return None, TutorState.GREETING, session_updates

    # Handle REPEAT
    if transition.action == "re_greet":
        session_updates["_llm_instruction"] = {
            "action": "greet",
            "topic": session.current_concept_id or "mathematics",
        }
        return None, TutorState.GREETING, session_updates

    # Handle COMFORT
    if transition.action == "comfort_and_stay":
        session_updates["_llm_instruction"] = {
            "action": "comfort",
            "student_text": text,
        }
        return None, TutorState.GREETING, session_updates

    # Handle TROLL
    if transition.action == "redirect_and_teach":
        session_updates["_llm_instruction"] = {
            "action": "redirect_troll",
            "student_text": text,
            "topic": session.current_concept_id or "mathematics",
        }
        return None, TutorState.GREETING, session_updates

    # Default: start teaching (ACK, IDK, CONCEPT_REQUEST, ANSWER)
    material = get_cb_material_for_index(
        session.current_concept_id,
        session.teach_material_index,
        content_bank,
    )
    session_updates["_llm_instruction"] = {
        "action": "teach",
        "material": material.get("text", ""),
        "layer": "L1",
        "topic": session.current_concept_id or "mathematics",
    }
    return None, TutorState.TEACHING, session_updates


async def handle_teaching(
    session: SessionState,
    input_category: str,
    extras: Dict[str, Any],
    text: str,
    content_bank=None,
    llm_call: Callable = None,
) -> Tuple[Optional[str], TutorState, Dict[str, Any]]:
    """
    Handle inputs in TEACHING state.

    CRITICAL RULES:
    - IDK/REPEAT: Increment reteach_count. If >= 3, force advance to question.
    - LANGUAGE_SWITCH: Store language, reteach SAME material. Do NOT increment.
    - ACK: Student understood → ask question.
    - ANSWER: Evaluate premature answer.
    """
    transition = get_transition(TutorState.TEACHING, input_category)
    session_updates = {}

    # Handle language switch (NO reteach increment)
    if transition.special == "store_language" and extras.get("preferred_language"):
        session_updates["preferred_language"] = extras["preferred_language"]
        material = get_cb_material_for_index(
            session.current_concept_id,
            session.teach_material_index,
            content_bank,
        )
        session_updates["_llm_instruction"] = {
            "action": "language_switch_ack",
            "target_language": extras["preferred_language"],
            "brief_topic_context": f"we were learning about {session.current_concept_id or 'mathematics'}",
        }
        return None, TutorState.TEACHING, session_updates

    # Handle STOP
    if transition.action == "end_session":
        session_updates["_llm_instruction"] = {
            "action": "wrap_up",
        }
        return None, TutorState.SESSION_END, session_updates

    # Handle GARBLED
    if transition.action == "ask_repeat":
        session_updates["_llm_instruction"] = {
            "action": "handle_garbled",
        }
        return None, TutorState.TEACHING, session_updates

    # Handle ACK → transition to question
    if transition.action == "ask_question":
        session_updates["concept_taught"] = True
        if session.current_question:
            q_text = session.current_question.get("question_tts", "")
            session_updates["_llm_instruction"] = {
                "action": "ask_question",
                "question_text": q_text,
                "topic": session.current_concept_id or "mathematics",
            }
        else:
            session_updates["_llm_instruction"] = {
                "action": "ask_question",
                "question_text": "",
                "topic": session.current_concept_id or "mathematics",
            }
        return None, TutorState.WAITING_ANSWER, session_updates

    # Handle IDK/REPEAT/CONCEPT_REQUEST → reteach with increment
    if transition.special == "increment_reteach":
        new_count = session.reteach_count + 1
        session_updates["reteach_count"] = new_count
        session_updates["teach_material_index"] = min(new_count, 2)

        # Confusion escalation: at 4+, offer break
        if new_count >= 4:
            session_updates["_llm_instruction"] = {
                "action": "comfort",
                "student_text": "Student has been confused 4+ times",
            }
            return None, TutorState.TEACHING, session_updates

        # Check if we should force advance (after 3 failed attempts)
        if new_count >= 3:
            q_text = ""
            if session.current_question:
                q_text = session.current_question.get("question_tts", "")
            session_updates["_llm_instruction"] = {
                "action": "ask_question",
                "question_text": q_text,
                "topic": session.current_concept_id or "mathematics",
            }
            return None, TutorState.WAITING_ANSWER, session_updates

        # Reteach with next material
        material = get_cb_material_for_index(
            session.current_concept_id,
            min(new_count, 2),
            content_bank,
        )
        session_updates["_llm_instruction"] = {
            "action": "reteach",
            "material": material.get("text", ""),
            "confusion_count": new_count,
            "topic": session.current_concept_id or "mathematics",
        }
        return None, TutorState.TEACHING, session_updates

    # Handle COMFORT → comfort first, then continue
    if transition.special == "empathy_first":
        session_updates["empathy_given"] = True
        session_updates["_llm_instruction"] = {
            "action": "comfort",
            "student_text": text,
        }
        return None, TutorState.TEACHING, session_updates

    # Handle TROLL → redirect and continue
    if transition.action == "redirect_and_teach":
        session_updates["_llm_instruction"] = {
            "action": "redirect_troll",
            "student_text": text,
            "topic": session.current_concept_id or "mathematics",
        }
        return None, TutorState.TEACHING, session_updates

    # Handle premature ANSWER → need to evaluate
    if transition.special == "evaluate_answer":
        # This will be handled by the router which has access to LLM evaluator
        # Return a marker that router should evaluate
        session_updates["_needs_evaluation"] = True
        session_updates["_student_answer"] = text
        return None, TutorState.TEACHING, session_updates

    # Default: continue teaching with LLM
    material = get_cb_material_for_index(
        session.current_concept_id,
        session.teach_material_index,
        content_bank,
    )
    if material and material.get("text"):
        session_updates["_llm_instruction"] = {
            "action": "teach",
            "material": material["text"],
            "layer": f"L{session.teach_material_index + 1}",
            "topic": session.current_concept_id or "mathematics",
        }
        return None, TutorState.TEACHING, session_updates
    else:
        # No material available — ask a question instead of dead fallback
        if session.current_question:
            session_updates["_llm_instruction"] = {
                "action": "ask_question",
                "question_text": session.current_question.get("question_tts", ""),
                "topic": session.current_concept_id or "mathematics",
            }
            return None, TutorState.WAITING_ANSWER, session_updates
        else:
            session_updates["_llm_instruction"] = {
                "action": "greet",
                "topic": session.current_concept_id or "mathematics",
            }
            return None, TutorState.GREETING, session_updates


async def handle_waiting_answer(
    session: SessionState,
    input_category: str,
    extras: Dict[str, Any],
    text: str,
    content_bank=None,
    llm_call: Callable = None,
) -> Tuple[Optional[str], TutorState, Dict[str, Any]]:
    """
    Handle inputs in WAITING_ANSWER state.

    CRITICAL: ANSWER inputs must use LLM evaluator.
    """
    transition = get_transition(TutorState.WAITING_ANSWER, input_category)
    session_updates = {}

    # Handle language switch
    if transition.special == "store_language" and extras.get("preferred_language"):
        session_updates["preferred_language"] = extras["preferred_language"]
        if session.current_question:
            q_text = session.current_question.get("question_tts", "")
            session_updates["_llm_instruction"] = {
                "action": "ask_question",
                "question_text": q_text,
                "topic": session.current_concept_id or "mathematics",
            }
        else:
            session_updates["_llm_instruction"] = {
                "action": "handle_garbled",
            }
        return None, TutorState.WAITING_ANSWER, session_updates

    # Handle STOP
    if transition.action == "end_session":
        session_updates["_llm_instruction"] = {
            "action": "wrap_up",
        }
        return None, TutorState.SESSION_END, session_updates

    # Handle GARBLED
    if transition.action == "ask_repeat":
        session_updates["_llm_instruction"] = {
            "action": "handle_garbled",
        }
        return None, TutorState.WAITING_ANSWER, session_updates

    # Handle ACK/REPEAT → re-read question
    if transition.action in ("reread_question", "reread_in_language"):
        if session.current_question:
            q_text = session.current_question.get("question_tts", "")
            session_updates["_llm_instruction"] = {
                "action": "ask_question",
                "question_text": q_text,
                "topic": session.current_concept_id or "mathematics",
            }
        else:
            session_updates["_llm_instruction"] = {
                "action": "handle_garbled",
            }
        return None, TutorState.WAITING_ANSWER, session_updates

    # Handle IDK → give hint
    if transition.action == "give_hint":
        session_updates["hints_given"] = 1
        if session.current_question:
            q_id = session.current_question.get("question_id", "")
            q_text = session.current_question.get("question_tts", "")
            hint = get_cb_hint(q_id, 0, content_bank)
            session_updates["_llm_instruction"] = {
                "action": "hint",
                "question_text": q_text,
                "correct_answer": session.current_question.get("expected_answer", ""),
                "hint_level": 1,
                "student_answer": "",
            }
        else:
            session_updates["_llm_instruction"] = {
                "action": "hint",
                "question_text": "",
                "hint_level": 1,
            }
        return None, TutorState.HINT, session_updates

    # Handle CONCEPT_REQUEST → go back to teaching
    if transition.special == "reset_reteach":
        session_updates["reteach_count"] = 0
        session_updates["teach_material_index"] = 0
        material = get_cb_material_for_index(
            session.current_concept_id,
            0,
            content_bank,
        )
        session_updates["_llm_instruction"] = {
            "action": "teach",
            "material": material.get("text", ""),
            "layer": "L1",
            "topic": session.current_concept_id or "mathematics",
        }
        return None, TutorState.TEACHING, session_updates

    # Handle COMFORT → comfort then re-read
    if transition.action == "comfort_then_reread":
        session_updates["_llm_instruction"] = {
            "action": "comfort",
            "student_text": text,
        }
        return None, TutorState.WAITING_ANSWER, session_updates

    # Handle TROLL → redirect
    if transition.action == "redirect_and_reread":
        session_updates["_llm_instruction"] = {
            "action": "redirect_troll",
            "student_text": text,
            "topic": session.current_concept_id or "mathematics",
        }
        return None, TutorState.WAITING_ANSWER, session_updates

    # Handle ANSWER → needs LLM evaluation
    if transition.special == "use_llm_evaluator":
        session_updates["_needs_evaluation"] = True
        session_updates["_student_answer"] = text
        session_updates["question_attempts"] = session.question_attempts + 1
        return None, TutorState.WAITING_ANSWER, session_updates

    # Default: ask question again
    if session.current_question:
        q_text = session.current_question.get("question_tts", "")
        session_updates["_llm_instruction"] = {
            "action": "ask_question",
            "question_text": q_text,
            "topic": session.current_concept_id or "mathematics",
        }
    else:
        session_updates["_llm_instruction"] = {
            "action": "handle_garbled",
        }
    return None, TutorState.WAITING_ANSWER, session_updates


async def handle_hint(
    session: SessionState,
    input_category: str,
    extras: Dict[str, Any],
    text: str,
    content_bank=None,
    llm_call: Callable = None,
) -> Tuple[Optional[str], TutorState, Dict[str, Any]]:
    """
    Handle inputs in HINT state.

    Hint progression:
    - hints_given=0 → Hint 1
    - hints_given=1 → Hint 2
    - hints_given=2 → Full solution → NEXT_QUESTION
    """
    transition = get_transition(TutorState.HINT, input_category)
    session_updates = {}

    # Handle language switch
    if transition.special == "store_language" and extras.get("preferred_language"):
        session_updates["preferred_language"] = extras["preferred_language"]
        if session.current_question:
            q_id = session.current_question.get("question_id", "")
            q_text = session.current_question.get("question_tts", "")
            hint = get_cb_hint(q_id, session.hints_given - 1, content_bank)
            session_updates["_llm_instruction"] = {
                "action": "hint",
                "question_text": q_text,
                "hint_level": session.hints_given,
            }
        else:
            session_updates["_llm_instruction"] = {
                "action": "handle_garbled",
            }
        return None, TutorState.HINT, session_updates

    # Handle STOP
    if transition.action == "end_session":
        session_updates["_llm_instruction"] = {
            "action": "wrap_up",
        }
        return None, TutorState.SESSION_END, session_updates

    # Handle GARBLED
    if transition.action == "ask_repeat":
        session_updates["_llm_instruction"] = {
            "action": "handle_garbled",
        }
        return None, TutorState.HINT, session_updates

    # Handle ACK → return to question
    if transition.action == "return_to_question":
        if session.current_question:
            q_text = session.current_question.get("question_tts", "")
            session_updates["_llm_instruction"] = {
                "action": "ask_question",
                "question_text": q_text,
                "topic": session.current_concept_id or "mathematics",
            }
        else:
            session_updates["_llm_instruction"] = {
                "action": "handle_garbled",
            }
        return None, TutorState.WAITING_ANSWER, session_updates

    # Handle REPEAT → re-read hint
    if transition.action == "reread_hint":
        if session.current_question:
            q_id = session.current_question.get("question_id", "")
            q_text = session.current_question.get("question_tts", "")
            hint = get_cb_hint(q_id, session.hints_given - 1, content_bank)
            session_updates["_llm_instruction"] = {
                "action": "hint",
                "question_text": q_text,
                "hint_level": session.hints_given,
            }
        else:
            session_updates["_llm_instruction"] = {
                "action": "handle_garbled",
            }
        return None, TutorState.HINT, session_updates

    # Handle IDK → next hint level
    if transition.action == "give_next_hint":
        new_hints_given = session.hints_given + 1
        session_updates["hints_given"] = new_hints_given

        if new_hints_given >= 3:
            # Give full solution and move on
            if session.current_question:
                q_id = session.current_question.get("question_id", "")
                solution = get_cb_hint(q_id, 2, content_bank)
                correct = session.current_question.get("expected_answer", "")
                # Reveal answer via teach action
                session_updates["_llm_instruction"] = {
                    "action": "teach",
                    "material": f"The answer is {correct}. {solution}",
                    "layer": "answer_reveal",
                    "topic": session.current_concept_id or "mathematics",
                }
            else:
                session_updates["_llm_instruction"] = {
                    "action": "wrap_up",
                }
            return None, TutorState.NEXT_QUESTION, session_updates

        # Give next hint
        if session.current_question:
            q_id = session.current_question.get("question_id", "")
            q_text = session.current_question.get("question_tts", "")
            hint = get_cb_hint(q_id, new_hints_given - 1, content_bank)
            session_updates["_llm_instruction"] = {
                "action": "hint",
                "question_text": q_text,
                "correct_answer": session.current_question.get("expected_answer", ""),
                "hint_level": new_hints_given,
            }
        else:
            session_updates["_llm_instruction"] = {
                "action": "handle_garbled",
            }
        return None, TutorState.HINT, session_updates

    # Handle CONCEPT_REQUEST → go back to teaching
    if transition.special == "reset_reteach":
        session_updates["reteach_count"] = 0
        session_updates["teach_material_index"] = 0
        material = get_cb_material_for_index(
            session.current_concept_id,
            0,
            content_bank,
        )
        session_updates["_llm_instruction"] = {
            "action": "teach",
            "material": material.get("text", ""),
            "layer": "L1",
            "topic": session.current_concept_id or "mathematics",
        }
        return None, TutorState.TEACHING, session_updates

    # Handle COMFORT
    if transition.action == "comfort_and_simplify_hint":
        session_updates["_llm_instruction"] = {
            "action": "comfort",
            "student_text": text,
        }
        return None, TutorState.HINT, session_updates

    # Handle TROLL
    if transition.action == "redirect_and_reread_hint":
        session_updates["_llm_instruction"] = {
            "action": "redirect_troll",
            "student_text": text,
            "topic": session.current_concept_id or "mathematics",
        }
        return None, TutorState.HINT, session_updates

    # Handle ANSWER → needs LLM evaluation
    if transition.special == "use_llm_evaluator":
        session_updates["_needs_evaluation"] = True
        session_updates["_student_answer"] = text
        session_updates["question_attempts"] = session.question_attempts + 1
        return None, TutorState.HINT, session_updates

    # Default
    session_updates["_llm_instruction"] = {
        "action": "hint",
        "question_text": session.current_question.get("question_tts", "") if session.current_question else "",
        "hint_level": session.hints_given,
    }
    return None, TutorState.HINT, session_updates


async def handle_next_question(
    session: SessionState,
    input_category: str,
    extras: Dict[str, Any],
    text: str,
    content_bank=None,
    llm_call: Callable = None,
) -> Tuple[Optional[str], TutorState, Dict[str, Any]]:
    """
    Handle NEXT_QUESTION state (transient).

    Auto-transitions based on:
    - total_questions_asked >= target → SESSION_END
    - Next question has different concept → TEACHING
    - Same concept → WAITING_ANSWER
    """
    transition = get_transition(TutorState.NEXT_QUESTION, input_category)
    session_updates = {}

    # Handle language switch
    if transition.special == "store_language" and extras.get("preferred_language"):
        session_updates["preferred_language"] = extras["preferred_language"]

    # Handle STOP
    if transition.action == "end_session":
        session_updates["_llm_instruction"] = {
            "action": "wrap_up",
        }
        return None, TutorState.SESSION_END, session_updates

    # Check if session complete
    if session.total_questions_asked >= session.total_questions_target:
        session_updates["_llm_instruction"] = {
            "action": "wrap_up",
            "questions_attempted": session.total_questions_asked,
            "questions_correct": session.score,
        }
        return None, TutorState.SESSION_END, session_updates

    # Check if CONCEPT_REQUEST → go to teaching
    if transition.action == "go_to_teaching":
        material = get_cb_material_for_index(
            session.current_concept_id,
            0,
            content_bank,
        )
        session_updates["_llm_instruction"] = {
            "action": "teach",
            "material": material.get("text", ""),
            "layer": "L1",
            "topic": session.current_concept_id or "mathematics",
        }
        return None, TutorState.TEACHING, session_updates

    # Default: proceed to next question
    session_updates["_load_next_question"] = True
    # Router will handle loading next question and then calling ask_question
    session_updates["_llm_instruction"] = {
        "action": "correct_feedback",
        "question_text": session.current_question.get("question_tts", "") if session.current_question else "",
        "student_answer": text,
    }
    return None, TutorState.WAITING_ANSWER, session_updates


async def handle_session_end(
    session: SessionState,
    input_category: str,
    extras: Dict[str, Any],
    text: str,
    content_bank=None,
    llm_call: Callable = None,
) -> Tuple[Optional[str], TutorState, Dict[str, Any]]:
    """
    Handle SESSION_END state (terminal).

    All inputs result in farewell message.
    """
    session_updates = {}

    # Handle language switch for farewell message
    if input_category == "LANGUAGE_SWITCH" and extras.get("preferred_language"):
        session_updates["preferred_language"] = extras["preferred_language"]

    session_updates["_llm_instruction"] = {
        "action": "wrap_up",
        "questions_attempted": session.total_questions_asked,
        "questions_correct": session.score,
    }

    return None, TutorState.SESSION_END, session_updates


# ─── Main Handler Dispatcher ─────────────────────────────────────────────────

HANDLERS = {
    TutorState.GREETING: handle_greeting,
    TutorState.TEACHING: handle_teaching,
    TutorState.WAITING_ANSWER: handle_waiting_answer,
    TutorState.HINT: handle_hint,
    TutorState.NEXT_QUESTION: handle_next_question,
    TutorState.SESSION_END: handle_session_end,
}


async def handle_state(
    session: SessionState,
    input_category: str,
    extras: Dict[str, Any],
    text: str,
    content_bank=None,
    llm_call: Callable = None,
) -> Tuple[Optional[str], TutorState, Dict[str, Any]]:
    """
    Main entry point for state handling.

    Dispatches to the appropriate state handler.
    """
    current_state = session.current_state

    # Ensure state is TutorState enum
    if isinstance(current_state, str):
        current_state = TutorState(current_state)

    handler = HANDLERS.get(current_state)
    if handler is None:
        logger.error(f"No handler for state {current_state}")
        return None, current_state, {"_llm_instruction": {"action": "handle_garbled"}}

    # Store language BEFORE calling handler (critical for LANGUAGE_SWITCH)
    if input_category == "LANGUAGE_SWITCH" and extras.get("preferred_language"):
        session.preferred_language = extras["preferred_language"]
        logger.info(f"v9.0: Language set to '{session.preferred_language}' BEFORE handler")

    return await handler(
        session, input_category, extras, text,
        content_bank=content_bank, llm_call=llm_call,
    )
