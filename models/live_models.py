"""
Gemini Live API - Pydantic Models
IDNA EdTech Voice Integration

Architecture:
- Gemini Live = Ears + Larynx (ASR, TTS, barge-in)
- IDNA Backend = Brain (FSM, Evaluator, TutorIntent)

Key Principle: Gemini calls ONE authoritative function per turn: tutor_turn()
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from enum import Enum


class LiveEvent(str, Enum):
    """Events that trigger a tutor turn"""
    START_SESSION = "START_SESSION"
    REQUEST_CHAPTER = "REQUEST_CHAPTER"
    REQUEST_QUESTION = "REQUEST_QUESTION"
    SUBMIT_ANSWER = "SUBMIT_ANSWER"
    INTERRUPT = "INTERRUPT"
    REPEAT = "REPEAT"
    END_SESSION = "END_SESSION"


class Telemetry(BaseModel):
    """Network and mode telemetry"""
    rtt_ms: Optional[int] = Field(None, description="Round-trip time in milliseconds")
    packet_loss_pct: Optional[float] = Field(None, description="Packet loss percentage")
    mode: Literal["LIVE", "TTS", "TEXT"] = Field("LIVE", description="Current voice mode")


class LiveTurnRequest(BaseModel):
    """Request from Gemini Live to backend"""
    session_id: str = Field(..., description="Unique session identifier")
    event: LiveEvent = Field(..., description="Type of event triggering this turn")
    client_ts_ms: int = Field(..., description="Client timestamp in milliseconds")
    chapter_id: Optional[str] = Field(None, description="Chapter identifier (for REQUEST_CHAPTER)")
    question_id: Optional[str] = Field(None, description="Current question identifier")
    student_utterance: Optional[str] = Field(None, description="Best-effort transcript of student's speech")
    asr_confidence: Optional[float] = Field(None, description="ASR confidence score 0-1")
    language: Literal["en", "hi", "hinglish"] = Field("en", description="Detected or preferred language")
    telemetry: Optional[Telemetry] = Field(None, description="Network and mode telemetry")


class VoicePlan(BaseModel):
    """Constraints for Gemini on what to speak"""
    max_sentences: int = Field(2, description="Maximum sentences Gemini may speak")
    required: List[str] = Field(default_factory=list, description="Elements that MUST be included")
    forbidden: List[str] = Field(default_factory=list, description="Elements that MUST NOT be included")


class Canonical(BaseModel):
    """Canonical content for the question"""
    question_text: str
    expected_answer: str
    hint_1: Optional[str] = None
    hint_2: Optional[str] = None
    solution_steps: List[str] = Field(default_factory=list)


class UIDirective(BaseModel):
    """UI display directives"""
    subtitle: Optional[str] = None
    show_steps: List[str] = Field(default_factory=list)
    big_question_text: Optional[str] = None


class SpeakDirective(BaseModel):
    """What Gemini should speak"""
    text: str = Field(..., description="Plain text version")
    ssml: Optional[str] = Field(None, description="SSML with pauses and prosody")


class NextAction(BaseModel):
    """What should happen after speaking"""
    type: Literal["WAIT_STUDENT", "AUTO_CONTINUE", "END_SESSION"] = Field(
        "WAIT_STUDENT",
        description="WAIT_STUDENT=wait for student to speak, AUTO_CONTINUE=immediately fetch next question, END_SESSION=session complete"
    )


class Fallback(BaseModel):
    """Fallback mode configuration"""
    allowed: bool = Field(True, description="Whether fallback is allowed")
    recommended_mode: Literal["LIVE", "TTS", "TEXT"] = Field("LIVE", description="Recommended voice mode")


class LiveTurnResponse(BaseModel):
    """Response from backend to Gemini Live"""
    session_id: str
    question_id: Optional[str] = None
    state: str = Field(..., description="FSM state: IDLE, IN_QUESTION, SHOWING_HINT, COMPLETED")
    attempt_no: int = Field(0, description="Current attempt (1, 2, or 3)")
    is_correct: Optional[bool] = Field(None, description="Whether student's answer was correct")
    tutor_intent: str = Field(..., description="TutorIntent enum value")
    language: str = Field("en", description="Response language")
    voice_plan: VoicePlan = Field(..., description="Constraints for Gemini")
    canonical: Optional[Canonical] = Field(None, description="Canonical content")
    ui: Optional[UIDirective] = Field(None, description="UI display directives")
    speak: SpeakDirective = Field(..., description="What Gemini speaks")
    next_action: NextAction = Field(default_factory=lambda: NextAction(type="WAIT_STUDENT"))
    fallback: Fallback = Field(default_factory=Fallback)

    # Additional context for debugging
    teacher_move: Optional[str] = Field(None, description="Teacher policy move (from teacher_policy.py)")
    error_type: Optional[str] = Field(None, description="Diagnosed error type")
    goal: Optional[str] = Field(None, description="Goal of this teaching turn")
