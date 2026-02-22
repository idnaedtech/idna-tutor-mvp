"""
IDNA EdTech v7.3 — ORM Models
Every table from the tech spec. UUID primary keys. Proper relationships.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime, JSON, LargeBinary,
    ForeignKey, Index, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _uuid() -> str:
    return str(uuid.uuid4())

def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Students ────────────────────────────────────────────────────────────────

class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(100))
    pin: Mapped[str] = mapped_column(String(4), unique=True, index=True)
    class_level: Mapped[int] = mapped_column(Integer, default=8)
    preferred_language: Mapped[str] = mapped_column(String(10), default="hi-IN")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    # Relationships
    parent: Mapped[Optional["Parent"]] = relationship(back_populates="student", uselist=False)
    sessions: Mapped[list["Session"]] = relationship(back_populates="student")
    skills: Mapped[list["SkillMastery"]] = relationship(back_populates="student")


# ─── Parents ─────────────────────────────────────────────────────────────────

class Parent(Base):
    __tablename__ = "parents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id"), unique=True
    )
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    pin: Mapped[str] = mapped_column(String(4), unique=True, index=True)
    language: Mapped[str] = mapped_column(String(10), default="hi-IN")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="parent")


# ─── Sessions ────────────────────────────────────────────────────────────────

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id"), index=True
    )
    session_type: Mapped[str] = mapped_column(
        String(10), default="student"
    )  # "student" | "parent"
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    chapter: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    state: Mapped[str] = mapped_column(String(30), default="GREETING")
    language: Mapped[str] = mapped_column(String(10), default="hi-IN")

    # Running counters (updated each turn, no need to COUNT turns)
    questions_attempted: Mapped[int] = mapped_column(Integer, default=0)
    questions_correct: Mapped[int] = mapped_column(Integer, default=0)
    total_hints_used: Mapped[int] = mapped_column(Integer, default=0)

    # Current question tracking
    current_question_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current_hint_level: Mapped[int] = mapped_column(Integer, default=0)
    current_reteach_count: Mapped[int] = mapped_column(Integer, default=0)

    # v7.2.0: Teaching progression tracking (BUG 1/3 fix)
    teaching_turn: Mapped[int] = mapped_column(Integer, default=0)  # Resets per concept
    explanations_given: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of explanations

    # v7.2.0: Language preference persistence (BUG 2 fix)
    language_pref: Mapped[str] = mapped_column(String(10), default="hinglish")  # hinglish/english/hindi

    # v7.3.28: Empathy one-turn-max flag (Fix 3)
    empathy_given: Mapped[bool] = mapped_column(Boolean, default=False)

    # v8.1.0: Confusion escalation counter (P0 Bug 2 fix)
    # Increments when student expresses confusion. Resets on correct answer or new topic.
    confusion_count: Mapped[int] = mapped_column(Integer, default=0)

    # v8.1.0: Board and topics tracking (P0 Bug 3 fix)
    board_name: Mapped[str] = mapped_column(String(20), default="NCERT")
    topics_covered: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # List of skill names covered

    # v7.3.0: Conversation history for multi-turn context (CHANGE 2)
    conversation_history: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # [{"role": "user"|"assistant", "content": str}]

    # v7.3.0: Concept graph tracking (CHANGE 3)
    current_concept_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Position in concept graph
    concept_mastery: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # {concept_id: True/False}

    # Session summary (generated at end)
    summary_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary_audio_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    parent_summary_audio_url: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="sessions")
    turns: Mapped[list["SessionTurn"]] = relationship(
        back_populates="session", order_by="SessionTurn.turn_number"
    )

    # Indexes
    __table_args__ = (
        Index("ix_sessions_student_started", "student_id", "started_at"),
    )


# ─── Session Turns ───────────────────────────────────────────────────────────

class SessionTurn(Base):
    __tablename__ = "session_turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), index=True
    )
    turn_number: Mapped[int] = mapped_column(Integer)
    speaker: Mapped[str] = mapped_column(String(10))  # "student" | "didi" | "parent"
    transcript: Mapped[str] = mapped_column(Text, default="")
    input_category: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    state_before: Mapped[str] = mapped_column(String(30))
    state_after: Mapped[str] = mapped_column(String(30))
    question_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    verdict: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    didi_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tts_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stt_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="turns")


# ─── Skill Mastery ───────────────────────────────────────────────────────────

class SkillMastery(Base):
    __tablename__ = "skill_mastery"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id"), index=True
    )
    subject: Mapped[str] = mapped_column(String(20))
    skill_key: Mapped[str] = mapped_column(String(50))
    mastery_score: Mapped[float] = mapped_column(Float, default=0.0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    last_attempted: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    teaching_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="skills")

    # Composite unique: one row per student per skill
    __table_args__ = (
        Index("ix_skill_student_skill", "student_id", "skill_key", unique=True),
    )


# ─── Question Bank ───────────────────────────────────────────────────────────

class Question(Base):
    __tablename__ = "question_bank"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    subject: Mapped[str] = mapped_column(String(20), index=True)
    chapter: Mapped[str] = mapped_column(String(50), index=True)
    class_level: Mapped[int] = mapped_column(Integer, default=8)
    question_type: Mapped[str] = mapped_column(String(30))
    question_text: Mapped[str] = mapped_column(Text)
    question_voice: Mapped[str] = mapped_column(Text)  # TTS-safe version
    answer: Mapped[str] = mapped_column(Text)
    answer_variants: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    key_concepts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    eval_method: Mapped[str] = mapped_column(String(20), default="exact")
    hints: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    solution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_skill: Mapped[str] = mapped_column(String(50))
    difficulty: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


# ─── Parent Instructions ─────────────────────────────────────────────────────

class ParentInstruction(Base):
    """When a parent tells Didi to focus on something, it's stored here.
    The next student session checks for pending instructions."""
    __tablename__ = "parent_instructions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id"), index=True
    )
    instruction: Mapped[str] = mapped_column(Text)
    fulfilled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# ─── Login Attempts (Rate Limiting) ──────────────────────────────────────────

class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    pin: Mapped[str] = mapped_column(String(4), index=True)
    success: Mapped[bool] = mapped_column(Boolean)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# ─── TTS Cache (v7.5.2) ─────────────────────────────────────────────────────

class TTSCache(Base):
    """
    v7.5.2: Store TTS audio in PostgreSQL instead of ephemeral filesystem.
    Survives Railway container restarts.
    """
    __tablename__ = "tts_cache"

    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    audio_bytes: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    lang: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
