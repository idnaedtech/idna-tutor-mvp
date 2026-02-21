"""
IDNA EdTech v7.3 — Student Session State Machine
THE BRAIN. Every state, every transition, deterministic.
Python decides what happens. LLM only generates spoken words.

States (MVP flow — math only, no topic discovery):
    GREETING            → Welcome + first question (session start goes directly to WAITING_ANSWER)
    CHECKING_UNDERSTANDING → Probe questions to assess current level
    TEACHING            → Explain concept with Indian examples
    WAITING_ANSWER      → Student attempts a practice question
    EVALUATING          → Check answer correctness (transient)
    HINT_1              → First hint after wrong answer
    HINT_2              → Second hint after second wrong
    FULL_SOLUTION       → Third wrong: walk through solution
    NEXT_QUESTION       → Advance to next question (transient)
    HOMEWORK_HELP       → Help with photographed homework
    COMFORT             → Student is frustrated
    SESSION_COMPLETE    → Wrap up and summarize
    DISPUTE_REPLAY      → Student challenges Didi's verdict
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple

from app.tutor.input_classifier import StudentCategory, get_language_switch_preference
from app.tutor.answer_checker import Verdict
from app.config import (
    MAX_QUESTIONS_PER_SESSION, MAX_RETEACH_ATTEMPTS,
)


# ─── State Set ────────────────────────────────────────────────────────────────

STATES = frozenset({
    "GREETING", "CHECKING_UNDERSTANDING",
    "TEACHING", "WAITING_ANSWER", "EVALUATING",
    "HINT_1", "HINT_2", "FULL_SOLUTION", "NEXT_QUESTION",
    "HOMEWORK_HELP", "COMFORT", "SESSION_COMPLETE", "DISPUTE_REPLAY",
})
# Note: DISCOVERING_TOPIC removed for MVP (math only, topic selected at UI)


# ─── Action (what instruction_builder should generate) ────────────────────────

@dataclass
class Action:
    """Instruction for the LLM prompt builder."""
    action_type: str
    verdict: Optional[Verdict] = None
    question_id: Optional[str] = None
    reteach_count: int = 0
    hint_level: int = 0
    detected_subject: Optional[str] = None
    student_text: str = ""
    extra: dict = field(default_factory=dict)
    # v7.2.0: Teaching progression and language
    teaching_turn: int = 0  # Current teaching turn (1, 2, 3)
    language_pref: Optional[str] = None  # Set when LANGUAGE_SWITCH detected


# ─── Transition Function ─────────────────────────────────────────────────────

def transition(
    current_state: str,
    category: StudentCategory,
    ctx: dict,
) -> Tuple[str, Action]:
    """
    Deterministic state transition.

    Args:
        current_state: Current FSM state
        category: Classified student input
        ctx: Session context dict with keys:
            student_text, subject, chapter, current_question_id,
            current_hint_level, current_reteach_count,
            questions_attempted, detected_subject, resume_state

    Returns:
        (new_state, Action)
    """
    text = ctx.get("student_text", "")
    q_id = ctx.get("current_question_id")
    hint_level = ctx.get("current_hint_level", 0)
    reteach = ctx.get("current_reteach_count", 0)
    q_count = ctx.get("questions_attempted", 0)
    det_subj = ctx.get("detected_subject")

    # ── UNIVERSAL OVERRIDES (any state) ───────────────────────────────────

    if category == "STOP":
        return "SESSION_COMPLETE", Action("end_session", student_text=text)

    # v7.3.21 Fix 2: LANGUAGE_SWITCH — transition to TEACHING to re-present in new language
    if category == "LANGUAGE_SWITCH":
        pref = get_language_switch_preference(text)
        return "TEACHING", Action(
            "acknowledge_language_switch", student_text=text,
            language_pref=pref,
            extra={"new_language": pref},
        )

    if category == "COMFORT" and current_state != "COMFORT":
        return "COMFORT", Action(
            "comfort_student", student_text=text,
            extra={"resume_state": current_state},
        )

    # v7.5.3: REPEAT handling moved to state-specific for TEACHING
    # Other states: return current state with ask_repeat
    if category == "REPEAT" and current_state != "TEACHING":
        return current_state, Action("ask_repeat", student_text=text)

    # ── GREETING ──────────────────────────────────────────────────────────
    # MVP: Session starts directly in WAITING_ANSWER with first question.
    # GREETING state only used if someone manually sets it.

    if current_state == "GREETING":
        # Go directly to waiting for answer (question already picked at session start)
        return "WAITING_ANSWER", Action("read_question", student_text=text)

    # ── CHECKING_UNDERSTANDING ────────────────────────────────────────────

    if current_state == "CHECKING_UNDERSTANDING":
        if category == "ANSWER":
            return "EVALUATING", Action(
                "evaluate_answer", question_id=q_id, student_text=text,
            )
        if category in ("IDK", "CONCEPT_REQUEST"):
            return "TEACHING", Action(
                "teach_concept", student_text=text,
            )
        if category == "ACK":
            return "WAITING_ANSWER", Action(
                "read_question", student_text=text,
            )
        return "CHECKING_UNDERSTANDING", Action(
            "probe_understanding", student_text=text,
        )

    # ── TEACHING ──────────────────────────────────────────────────────────

    if current_state == "TEACHING":
        # v7.2.0: Get teaching_turn from context (BUG 1 fix)
        teaching_turn = ctx.get("teaching_turn", 0)

        # v7.5.3: REPEAT in TEACHING = student didn't understand, treat like IDK
        # This prevents infinite loop where student keeps saying unclear things
        if category == "REPEAT":
            new_turn = teaching_turn + 1
            if new_turn >= 3:
                # Max reteach (3) reached, force transition to question
                return "WAITING_ANSWER", Action(
                    "read_question", reteach_count=new_turn,
                    teaching_turn=new_turn,
                    student_text=text,
                    extra={"difficulty": "easy", "forced_transition": True, "max_reteach": True},
                )
            return "TEACHING", Action(
                "teach_concept", reteach_count=new_turn,
                teaching_turn=new_turn,
                student_text=text,
                extra={"approach": "different_example"},
            )

        if category == "ACK":
            # v7.2.0: ACK in TEACHING → reset teaching_turn, transition to WAITING_ANSWER
            return "WAITING_ANSWER", Action(
                "read_question", student_text=text,
                extra={"reset_teaching_turn": True},
            )
        if category == "IDK":
            # v7.2.0: Increment teaching_turn, force transition at turn 3 (BUG 1 fix)
            new_turn = teaching_turn + 1
            if new_turn >= 3:
                # Force transition: "Koi baat nahi, chaliye ek sawaal try karte hain"
                return "WAITING_ANSWER", Action(
                    "read_question", reteach_count=new_turn,
                    teaching_turn=new_turn,
                    student_text=text,
                    extra={"difficulty": "easy", "forced_transition": True},
                )
            return "TEACHING", Action(
                "teach_concept", reteach_count=new_turn,
                teaching_turn=new_turn,
                student_text=text,
                extra={"approach": "different_example"},
            )
        if category == "META_QUESTION":
            # v7.2.0: Handle meta questions like "any more examples?" (BUG 4 fix)
            return "TEACHING", Action(
                "answer_meta_question", reteach_count=reteach,
                teaching_turn=teaching_turn,
                student_text=text,
                extra={"meta_type": "more_examples"},
            )
        if category == "CONCEPT_REQUEST":
            return "TEACHING", Action(
                "teach_concept", reteach_count=reteach,
                teaching_turn=teaching_turn,
                student_text=text, extra={"approach": "answer_question"},
            )
        if category == "ANSWER":
            # Student blurted an answer during teaching — evaluate it
            return "EVALUATING", Action(
                "evaluate_answer", question_id=q_id, student_text=text,
            )
        return "TEACHING", Action(
            "teach_concept", student_text=text,
            teaching_turn=teaching_turn,
        )

    # ── WAITING_ANSWER ────────────────────────────────────────────────────

    if current_state == "WAITING_ANSWER":
        if category == "ANSWER":
            return "EVALUATING", Action(
                "evaluate_answer", question_id=q_id, student_text=text,
            )
        if category == "IDK":
            return "HINT_1", Action(
                "give_hint", hint_level=1, question_id=q_id,
                student_text=text,
            )
        if category == "CONCEPT_REQUEST":
            return "TEACHING", Action(
                "teach_concept", question_id=q_id,
                student_text=text, extra={"return_to": "WAITING_ANSWER"},
            )
        if category == "DISPUTE":
            return "DISPUTE_REPLAY", Action(
                "replay_heard", student_text=text,
            )
        # ACK or TROLL during answer phase → nudge
        return "WAITING_ANSWER", Action(
            "read_question", question_id=q_id,
            student_text=text, extra={"nudge": True},
        )

    # ── HINT_1 ────────────────────────────────────────────────────────────

    if current_state == "HINT_1":
        if category == "ANSWER":
            return "EVALUATING", Action(
                "evaluate_answer", question_id=q_id,
                hint_level=1, student_text=text,
            )
        if category == "IDK":
            return "HINT_2", Action(
                "give_hint", hint_level=2, question_id=q_id,
                student_text=text,
            )
        if category == "CONCEPT_REQUEST":
            # Student asking for explanation - teach, then return to question
            return "TEACHING", Action(
                "teach_concept", question_id=q_id, student_text=text,
                extra={"return_to": "HINT_1"},
            )
        return "HINT_1", Action(
            "give_hint", hint_level=1, question_id=q_id,
            student_text=text, extra={"nudge": True},
        )

    # ── HINT_2 ────────────────────────────────────────────────────────────

    if current_state == "HINT_2":
        if category == "ANSWER":
            return "EVALUATING", Action(
                "evaluate_answer", question_id=q_id,
                hint_level=2, student_text=text,
            )
        if category == "IDK":
            return "FULL_SOLUTION", Action(
                "show_solution", question_id=q_id, student_text=text,
            )
        if category == "CONCEPT_REQUEST":
            # Student asking for explanation - teach, then return to question
            return "TEACHING", Action(
                "teach_concept", question_id=q_id, student_text=text,
                extra={"return_to": "HINT_2"},
            )
        return "HINT_2", Action(
            "give_hint", hint_level=2, question_id=q_id,
            student_text=text, extra={"nudge": True},
        )

    # ── FULL_SOLUTION ─────────────────────────────────────────────────────

    if current_state == "FULL_SOLUTION":
        # After solution, always move on
        return "NEXT_QUESTION", Action(
            "pick_next_question", student_text=text,
            extra={"follow_up": True},
        )

    # ── NEXT_QUESTION ─────────────────────────────────────────────────────

    if current_state == "NEXT_QUESTION":
        if q_count >= MAX_QUESTIONS_PER_SESSION:
            return "SESSION_COMPLETE", Action(
                "end_session", student_text=text,
            )
        return "WAITING_ANSWER", Action(
            "read_question", student_text=text,
        )

    # ── HOMEWORK_HELP ─────────────────────────────────────────────────────

    if current_state == "HOMEWORK_HELP":
        if category == "ANSWER":
            return "EVALUATING", Action(
                "evaluate_answer", question_id=q_id, student_text=text,
            )
        if category == "ACK":
            return "HOMEWORK_HELP", Action(
                "read_question", student_text=text,
                extra={"source": "homework"},
            )
        return "HOMEWORK_HELP", Action(
            "acknowledge_homework", student_text=text,
        )

    # ── COMFORT ───────────────────────────────────────────────────────────

    if current_state == "COMFORT":
        resume = ctx.get("resume_state", "TEACHING")
        if category == "ACK":
            at = "read_question" if resume == "WAITING_ANSWER" else "teach_concept"
            return resume, Action(at, student_text=text, extra={"post_comfort": True})
        if category == "STOP":
            return "SESSION_COMPLETE", Action("end_session", student_text=text)
        # Still upset
        return "COMFORT", Action("comfort_student", student_text=text)

    # ── DISPUTE_REPLAY ────────────────────────────────────────────────────

    if current_state == "DISPUTE_REPLAY":
        if category == "ANSWER":
            return "EVALUATING", Action(
                "evaluate_answer", question_id=q_id,
                student_text=text, extra={"is_retry": True},
            )
        return "WAITING_ANSWER", Action(
            "read_question", question_id=q_id, student_text=text,
        )

    # ── SESSION_COMPLETE ──────────────────────────────────────────────────

    if current_state == "SESSION_COMPLETE":
        return "SESSION_COMPLETE", Action("end_session", student_text=text)

    # ── FALLBACK ──────────────────────────────────────────────────────────
    return current_state, Action("ask_repeat", student_text=text)


# ─── Post-Evaluation Router ──────────────────────────────────────────────────

def route_after_evaluation(
    verdict: Verdict,
    hint_level: int,
    questions_attempted: int,
) -> Tuple[str, str]:
    """
    After answer_checker runs, decide where to go.

    Returns:
        (next_state, action_type)
    """
    if verdict.correct:
        if questions_attempted >= MAX_QUESTIONS_PER_SESSION:
            return "SESSION_COMPLETE", "end_session"
        return "NEXT_QUESTION", "pick_next_question"

    # Incorrect — escalate hint level
    if hint_level == 0:
        return "HINT_1", "give_hint"
    elif hint_level == 1:
        return "HINT_2", "give_hint"
    else:
        return "FULL_SOLUTION", "show_solution"
