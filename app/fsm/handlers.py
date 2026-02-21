"""
IDNA EdTech v8.0 — State Handlers

One function per state. Each handler receives:
    - session: SessionState
    - input_category: str
    - extras: dict (e.g., preferred_language from classifier)
    - text: str (student's input)

Each handler returns:
    - response_text: str (what Didi says)
    - new_state: TutorState
    - session_updates: dict (fields to update in session)

The handlers use Content Bank material per teach_material_index.
"""

import logging
from typing import Tuple, Dict, Any, Optional, Callable, Awaitable

from app.models.session import SessionState, TutorState
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
            "text": "Koi baat nahi, question try karte hain. Question se bhi seekhte hain!",
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


# ─── Language Instruction Helper ─────────────────────────────────────────────

def get_language_instruction(preferred_language: str) -> str:
    """
    Get language instruction for LLM prompt.

    EVERY LLM call MUST include this.
    """
    if preferred_language == "english":
        return "IMPORTANT: Respond in English only. Use only English. No Hindi words at all."
    elif preferred_language == "hindi":
        return "IMPORTANT: Respond in Hindi only. Use only Hindi. No English words."
    else:
        return "IMPORTANT: Respond in natural Hinglish mix (Hindi and English mixed naturally)."


# ─── State Handlers ──────────────────────────────────────────────────────────

async def handle_greeting(
    session: SessionState,
    input_category: str,
    extras: Dict[str, Any],
    text: str,
    content_bank=None,
    llm_call: Callable = None,
) -> Tuple[str, TutorState, Dict[str, Any]]:
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
        lang = extras["preferred_language"]
        if lang == "english":
            response = "Hello! Let's start learning math. I'll help you understand step by step."
        elif lang == "hindi":
            response = "नमस्ते! चलिए गणित सीखते हैं। मैं आपको step by step समझाऊंगी।"
        else:
            response = "Namaste! Chalo math shuru karte hain. Main step by step samjhaungi."
        return response, transition.next_state, session_updates

    # Handle actions
    if transition.action == "end_session":
        response = "Okay, phir milte hain! Bye!"
        return response, TutorState.SESSION_END, session_updates

    if transition.action == "ask_repeat":
        response = "Ek baar phir boliye? Aapki awaaz nahi aayi."
        return response, TutorState.GREETING, session_updates

    if transition.action == "re_greet":
        response = f"Main {session.student_name} se baat kar rahi hoon! Chalo math practice karte hain."
        return response, TutorState.GREETING, session_updates

    if transition.action == "comfort_and_stay":
        response = "Koi baat nahi, dheere dheere karenge. Aap se math seekhna bilkul easy hai!"
        return response, TutorState.GREETING, session_updates

    # Default: start teaching
    response = f"Chalo shuru karte hain, {session.student_name}! Aaj hum ek naya concept seekhenge."
    return response, TutorState.TEACHING, session_updates


async def handle_teaching(
    session: SessionState,
    input_category: str,
    extras: Dict[str, Any],
    text: str,
    content_bank=None,
    llm_call: Callable = None,
) -> Tuple[str, TutorState, Dict[str, Any]]:
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
        # Reteach SAME material in new language (do NOT increment teach_material_index)
        material = get_cb_material_for_index(
            session.current_concept_id,
            session.teach_material_index,  # Same index
            content_bank,
        )
        lang_instruction = get_language_instruction(extras["preferred_language"])
        response = f"{lang_instruction} {material['text']}"
        return response, TutorState.TEACHING, session_updates

    # Handle STOP
    if transition.action == "end_session":
        response = "Okay, phir milte hain! Aaj ke liye bye!"
        return response, TutorState.SESSION_END, session_updates

    # Handle GARBLED
    if transition.action == "ask_repeat":
        response = "Ek baar phir boliye?"
        return response, TutorState.TEACHING, session_updates

    # Handle ACK → transition to question
    if transition.action == "ask_question":
        session_updates["concept_taught"] = True
        # Get question from session
        if session.current_question:
            q_text = session.current_question.get("question_tts", "")
            response = f"Bahut accha! Ab ek sawaal hai: {q_text}"
        else:
            response = "Bahut accha! Ab ek sawaal solve karte hain."
        return response, TutorState.WAITING_ANSWER, session_updates

    # Handle IDK/REPEAT/CONCEPT_REQUEST → reteach with increment
    if transition.special == "increment_reteach":
        new_count = session.reteach_count + 1
        session_updates["reteach_count"] = new_count
        session_updates["teach_material_index"] = min(new_count, 2)

        # Check if we should force advance
        if new_count >= 3:
            # Force advance to question
            if session.current_question:
                q_text = session.current_question.get("question_tts", "")
                response = f"Koi baat nahi, question try karte hain! Sawaal ye hai: {q_text}"
            else:
                response = "Koi baat nahi, ek sawaal try karte hain!"
            return response, TutorState.WAITING_ANSWER, session_updates

        # Reteach with next material
        material = get_cb_material_for_index(
            session.current_concept_id,
            min(new_count, 2),
            content_bank,
        )
        response = f"Koi nahi, phir se samjhate hain. {material['text']} Samajh aaya?"
        return response, TutorState.TEACHING, session_updates

    # Handle COMFORT → comfort first, then continue
    if transition.special == "empathy_first":
        session_updates["empathy_given"] = True
        material = get_cb_material_for_index(
            session.current_concept_id,
            session.teach_material_index,
            content_bank,
        )
        response = f"Koi baat nahi, bahut aasan hai, dekhiye... {material['text']}"
        return response, TutorState.TEACHING, session_updates

    # Handle TROLL → redirect and continue
    if transition.action == "redirect_and_teach":
        material = get_cb_material_for_index(
            session.current_concept_id,
            session.teach_material_index,
            content_bank,
        )
        response = f"Haha! Chalo math pe focus karte hain. {material['text']}"
        return response, TutorState.TEACHING, session_updates

    # Handle premature ANSWER → need to evaluate
    if transition.special == "evaluate_answer":
        # This will be handled by the router which has access to LLM evaluator
        # Return a marker that router should evaluate
        session_updates["_needs_evaluation"] = True
        session_updates["_student_answer"] = text
        return "", TutorState.TEACHING, session_updates

    # Default: continue teaching
    material = get_cb_material_for_index(
        session.current_concept_id,
        session.teach_material_index,
        content_bank,
    )
    response = material["text"] if material["text"] else "Chalo aage badhte hain."
    return response, TutorState.TEACHING, session_updates


async def handle_waiting_answer(
    session: SessionState,
    input_category: str,
    extras: Dict[str, Any],
    text: str,
    content_bank=None,
    llm_call: Callable = None,
) -> Tuple[str, TutorState, Dict[str, Any]]:
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
            lang = extras["preferred_language"]
            if lang == "english":
                response = f"Okay, in English: {q_text}"
            else:
                response = f"Okay: {q_text}"
        else:
            response = "Okay, sawaal phir se padh rahi hoon."
        return response, TutorState.WAITING_ANSWER, session_updates

    # Handle STOP
    if transition.action == "end_session":
        response = "Okay, phir milte hain!"
        return response, TutorState.SESSION_END, session_updates

    # Handle GARBLED
    if transition.action == "ask_repeat":
        response = "Ek baar phir boliye?"
        return response, TutorState.WAITING_ANSWER, session_updates

    # Handle ACK/REPEAT → re-read question
    if transition.action in ("reread_question", "reread_in_language"):
        if session.current_question:
            q_text = session.current_question.get("question_tts", "")
            response = f"Main sawaal phir se padhti hoon: {q_text}"
        else:
            response = "Sawaal phir se padh rahi hoon."
        return response, TutorState.WAITING_ANSWER, session_updates

    # Handle IDK → give hint
    if transition.action == "give_hint":
        session_updates["hints_given"] = 1
        if session.current_question:
            q_id = session.current_question.get("question_id", "")
            hint = get_cb_hint(q_id, 0, content_bank)
            response = f"Hint: {hint}" if hint else "Sochiye, kya pattern dikh raha hai?"
        else:
            response = "Sochiye, kya pattern dikh raha hai?"
        return response, TutorState.HINT, session_updates

    # Handle CONCEPT_REQUEST → go back to teaching
    if transition.special == "reset_reteach":
        session_updates["reteach_count"] = 0
        session_updates["teach_material_index"] = 0
        response = "Haan, phir se samjhate hain concept ko."
        return response, TutorState.TEACHING, session_updates

    # Handle COMFORT → comfort then re-read
    if transition.action == "comfort_then_reread":
        if session.current_question:
            q_text = session.current_question.get("question_tts", "")
            response = f"Koi baat nahi, dheere dheere karte hain. Sawaal ye hai: {q_text}"
        else:
            response = "Koi baat nahi, aaram se sochiye."
        return response, TutorState.WAITING_ANSWER, session_updates

    # Handle TROLL → redirect
    if transition.action == "redirect_and_reread":
        if session.current_question:
            q_text = session.current_question.get("question_tts", "")
            response = f"Chalo focus karte hain! Sawaal ye hai: {q_text}"
        else:
            response = "Chalo focus karte hain sawaal pe!"
        return response, TutorState.WAITING_ANSWER, session_updates

    # Handle ANSWER → needs LLM evaluation
    if transition.special == "use_llm_evaluator":
        session_updates["_needs_evaluation"] = True
        session_updates["_student_answer"] = text
        session_updates["question_attempts"] = session.question_attempts + 1
        return "", TutorState.WAITING_ANSWER, session_updates

    # Default
    if session.current_question:
        q_text = session.current_question.get("question_tts", "")
        response = f"Sawaal ye hai: {q_text}"
    else:
        response = "Apna answer boliye."
    return response, TutorState.WAITING_ANSWER, session_updates


async def handle_hint(
    session: SessionState,
    input_category: str,
    extras: Dict[str, Any],
    text: str,
    content_bank=None,
    llm_call: Callable = None,
) -> Tuple[str, TutorState, Dict[str, Any]]:
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
            hint = get_cb_hint(q_id, session.hints_given - 1, content_bank)
            response = f"Hint: {hint}" if hint else "Hint hai..."
        else:
            response = "Hint phir se padh rahi hoon."
        return response, TutorState.HINT, session_updates

    # Handle STOP
    if transition.action == "end_session":
        response = "Okay, phir milte hain!"
        return response, TutorState.SESSION_END, session_updates

    # Handle GARBLED
    if transition.action == "ask_repeat":
        response = "Ek baar phir boliye?"
        return response, TutorState.HINT, session_updates

    # Handle ACK → return to question
    if transition.action == "return_to_question":
        if session.current_question:
            q_text = session.current_question.get("question_tts", "")
            response = f"Ab try karo! Sawaal: {q_text}"
        else:
            response = "Ab try karo!"
        return response, TutorState.WAITING_ANSWER, session_updates

    # Handle REPEAT → re-read hint
    if transition.action == "reread_hint":
        if session.current_question:
            q_id = session.current_question.get("question_id", "")
            hint = get_cb_hint(q_id, session.hints_given - 1, content_bank)
            response = f"Hint: {hint}" if hint else "Sochiye..."
        else:
            response = "Hint phir se..."
        return response, TutorState.HINT, session_updates

    # Handle IDK → next hint level
    if transition.action == "give_next_hint":
        new_hints_given = session.hints_given + 1
        session_updates["hints_given"] = new_hints_given

        if new_hints_given >= 3:
            # Give full solution and move on
            if session.current_question:
                q_id = session.current_question.get("question_id", "")
                solution = get_cb_hint(q_id, 2, content_bank)  # Index 2 = solution
                correct = session.current_question.get("expected_answer", "")
                response = f"Koi baat nahi! Solution: {solution}. Sahi answer tha: {correct}. Agle sawaal mein aur accha karenge!"
            else:
                response = "Koi baat nahi! Agle sawaal mein aur accha karenge!"
            return response, TutorState.NEXT_QUESTION, session_updates

        # Give next hint
        if session.current_question:
            q_id = session.current_question.get("question_id", "")
            hint = get_cb_hint(q_id, new_hints_given - 1, content_bank)
            response = f"Hint {new_hints_given}: {hint}" if hint else "Ek aur hint..."
        else:
            response = f"Hint {new_hints_given}..."
        return response, TutorState.HINT, session_updates

    # Handle CONCEPT_REQUEST → go back to teaching
    if transition.special == "reset_reteach":
        session_updates["reteach_count"] = 0
        session_updates["teach_material_index"] = 0
        response = "Haan, concept phir se samjhate hain."
        return response, TutorState.TEACHING, session_updates

    # Handle COMFORT
    if transition.action == "comfort_and_simplify_hint":
        if session.current_question:
            q_id = session.current_question.get("question_id", "")
            hint = get_cb_hint(q_id, session.hints_given - 1, content_bank)
            response = f"Koi baat nahi, aaram se. Hint: {hint}"
        else:
            response = "Koi baat nahi, aaram se sochiye."
        return response, TutorState.HINT, session_updates

    # Handle TROLL
    if transition.action == "redirect_and_reread_hint":
        if session.current_question:
            q_id = session.current_question.get("question_id", "")
            hint = get_cb_hint(q_id, session.hints_given - 1, content_bank)
            response = f"Chalo focus! Hint: {hint}"
        else:
            response = "Chalo focus karte hain!"
        return response, TutorState.HINT, session_updates

    # Handle ANSWER → needs LLM evaluation
    if transition.special == "use_llm_evaluator":
        session_updates["_needs_evaluation"] = True
        session_updates["_student_answer"] = text
        session_updates["question_attempts"] = session.question_attempts + 1
        return "", TutorState.HINT, session_updates

    # Default
    return "Sochiye...", TutorState.HINT, session_updates


async def handle_next_question(
    session: SessionState,
    input_category: str,
    extras: Dict[str, Any],
    text: str,
    content_bank=None,
    llm_call: Callable = None,
) -> Tuple[str, TutorState, Dict[str, Any]]:
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
        response = "Okay, phir milte hain!"
        return response, TutorState.SESSION_END, session_updates

    # Check if session complete
    if session.total_questions_asked >= session.total_questions_target:
        response = f"Session khatam! Aaj aapne {session.score}/{session.total_questions_asked} sahi kiye. Bahut accha! Kal phir milte hain!"
        return response, TutorState.SESSION_END, session_updates

    # Check if CONCEPT_REQUEST → go to teaching
    if transition.action == "go_to_teaching":
        response = "Haan, concept samjhate hain."
        return response, TutorState.TEACHING, session_updates

    # Default: proceed to next question
    # The router will load the next question and determine if new concept needs teaching
    session_updates["_load_next_question"] = True
    response = "Bahut accha! Chalo agle sawaal pe!"
    return response, TutorState.WAITING_ANSWER, session_updates


async def handle_session_end(
    session: SessionState,
    input_category: str,
    extras: Dict[str, Any],
    text: str,
    content_bank=None,
    llm_call: Callable = None,
) -> Tuple[str, TutorState, Dict[str, Any]]:
    """
    Handle SESSION_END state (terminal).

    All inputs result in farewell message.
    """
    session_updates = {}

    # Handle language switch for farewell message
    lang = session.preferred_language
    if input_category == "LANGUAGE_SWITCH" and extras.get("preferred_language"):
        lang = extras["preferred_language"]
        session_updates["preferred_language"] = lang

    if lang == "english":
        response = f"Session complete! Today you got {session.score}/{session.total_questions_asked} correct. See you tomorrow!"
    elif lang == "hindi":
        response = f"Session khatam! Aaj aapne {session.score}/{session.total_questions_asked} sahi kiye. Kal milte hain!"
    else:
        response = f"Session khatam ho gayi! Aaj aapne {session.score}/{session.total_questions_asked} sahi kiye. Kal phir milte hain!"

    return response, TutorState.SESSION_END, session_updates


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
) -> Tuple[str, TutorState, Dict[str, Any]]:
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
        return "Ek baar phir boliye?", current_state, {}

    # Store language BEFORE calling handler (critical for LANGUAGE_SWITCH)
    if input_category == "LANGUAGE_SWITCH" and extras.get("preferred_language"):
        session.preferred_language = extras["preferred_language"]
        logger.info(f"v8.0: Language set to '{session.preferred_language}' BEFORE handler")

    return await handler(
        session, input_category, extras, text,
        content_bank=content_bank, llm_call=llm_call,
    )
