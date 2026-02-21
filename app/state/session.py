"""
IDNA EdTech v8.0 — Session State Schema

Every session has ONE state object. All handlers read from it and write to it.
No ad-hoc variables. This is the single source of truth for session data.

Persistence Rules:
- preferred_language: Set ONLY by LANGUAGE_SWITCH. NEVER resets on state transitions.
- reteach_count: Resets to 0 when a NEW concept starts. Does NOT reset on re-entering TEACHING.
- empathy_given: Resets to False on every state transition.
- teach_material_index: Increments on each reteach. Maps to Content Bank material.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TutorState(str, Enum):
    """Six states. No more, no less."""
    GREETING = "GREETING"
    TEACHING = "TEACHING"
    WAITING_ANSWER = "WAITING_ANSWER"
    HINT = "HINT"
    NEXT_QUESTION = "NEXT_QUESTION"
    SESSION_END = "SESSION_END"


@dataclass
class SessionState:
    """
    Complete session state for v8.0 architecture.

    This dataclass contains ALL session data. Handlers receive this object,
    read from it, and return updates to it. No external state variables.
    """
    # ─── Identity ────────────────────────────────────────────────────────────
    session_id: str
    student_name: str
    student_pin: str
    started_at: datetime = field(default_factory=datetime.now)

    # ─── FSM ─────────────────────────────────────────────────────────────────
    current_state: TutorState = TutorState.GREETING
    previous_state: Optional[TutorState] = None

    # ─── Language — PERSISTS ACROSS ALL TURNS ────────────────────────────────
    # Set by LANGUAGE_SWITCH classifier. Once set, ALL subsequent LLM prompts
    # and TTS calls use this. Never resets unless student explicitly requests
    # a different language.
    preferred_language: str = "hinglish"  # "hinglish" | "hindi" | "english"

    # ─── Teaching tracking — PER CONCEPT ─────────────────────────────────────
    current_concept_id: Optional[str] = None  # e.g. "math_8_ch6_perfect_square"
    reteach_count: int = 0                    # How many times this concept re-explained
    teach_material_index: int = 0             # Which CB material to use next (0, 1, 2)
    concept_taught: bool = False              # True after student ACKs teaching
    empathy_given: bool = False               # True after comfort response in this state

    # ─── Question tracking — PER QUESTION ────────────────────────────────────
    current_question: Optional[dict] = None
    question_attempts: int = 0                # How many answers submitted
    hints_given: int = 0                      # 0, 1, or 2

    # ─── Session progress ────────────────────────────────────────────────────
    score: int = 0
    total_questions_asked: int = 0
    total_questions_target: int = 5           # Session ends after this many
    concepts_taught: list = field(default_factory=list)
    questions_answered: list = field(default_factory=list)

    # ─── Conversation ────────────────────────────────────────────────────────
    conversation_history: list = field(default_factory=list)
    turn_count: int = 0

    def transition_to(self, new_state: TutorState) -> None:
        """
        Transition to a new state. Handles state-transition side effects.

        - Saves previous_state
        - Resets empathy_given (per v8.0 spec)
        """
        self.previous_state = self.current_state
        self.current_state = new_state
        self.empathy_given = False  # Reset on every state transition

    def reset_for_new_concept(self, concept_id: str) -> None:
        """
        Reset teaching counters for a new concept.

        Called when starting to teach a different concept.
        """
        self.current_concept_id = concept_id
        self.reteach_count = 0
        self.teach_material_index = 0
        self.concept_taught = False

    def reset_for_new_question(self, question: dict) -> None:
        """
        Reset question tracking for a new question.
        """
        self.current_question = question
        self.question_attempts = 0
        self.hints_given = 0
        self.total_questions_asked += 1

    def increment_reteach(self) -> int:
        """
        Increment reteach counter and teach_material_index.

        Returns new reteach_count for convenience.
        """
        self.reteach_count += 1
        self.teach_material_index = min(self.reteach_count, 2)  # Cap at index 2
        return self.reteach_count

    def add_to_history(self, role: str, content: str) -> None:
        """Add a turn to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "turn": self.turn_count,
        })
        if role == "user":
            self.turn_count += 1

    def get_recent_history(self, max_turns: int = 6) -> list:
        """Get last N turns of conversation history."""
        return self.conversation_history[-max_turns * 2:]  # *2 for user+assistant pairs

    def to_dict(self) -> dict:
        """Serialize to dictionary for storage/logging."""
        return {
            "session_id": self.session_id,
            "student_name": self.student_name,
            "student_pin": self.student_pin,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "current_state": self.current_state.value if isinstance(self.current_state, TutorState) else self.current_state,
            "previous_state": self.previous_state.value if isinstance(self.previous_state, TutorState) else self.previous_state,
            "preferred_language": self.preferred_language,
            "current_concept_id": self.current_concept_id,
            "reteach_count": self.reteach_count,
            "teach_material_index": self.teach_material_index,
            "concept_taught": self.concept_taught,
            "empathy_given": self.empathy_given,
            "current_question": self.current_question,
            "question_attempts": self.question_attempts,
            "hints_given": self.hints_given,
            "score": self.score,
            "total_questions_asked": self.total_questions_asked,
            "total_questions_target": self.total_questions_target,
            "turn_count": self.turn_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SessionState":
        """Deserialize from dictionary."""
        state = cls(
            session_id=data["session_id"],
            student_name=data["student_name"],
            student_pin=data["student_pin"],
        )
        if data.get("started_at"):
            state.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("current_state"):
            state.current_state = TutorState(data["current_state"])
        if data.get("previous_state"):
            state.previous_state = TutorState(data["previous_state"])
        state.preferred_language = data.get("preferred_language", "hinglish")
        state.current_concept_id = data.get("current_concept_id")
        state.reteach_count = data.get("reteach_count", 0)
        state.teach_material_index = data.get("teach_material_index", 0)
        state.concept_taught = data.get("concept_taught", False)
        state.empathy_given = data.get("empathy_given", False)
        state.current_question = data.get("current_question")
        state.question_attempts = data.get("question_attempts", 0)
        state.hints_given = data.get("hints_given", 0)
        state.score = data.get("score", 0)
        state.total_questions_asked = data.get("total_questions_asked", 0)
        state.total_questions_target = data.get("total_questions_target", 5)
        state.turn_count = data.get("turn_count", 0)
        state.concepts_taught = data.get("concepts_taught", [])
        state.questions_answered = data.get("questions_answered", [])
        state.conversation_history = data.get("conversation_history", [])
        return state
