"""
IDNA EdTech v7.0 — Student Session Router
The main interaction loop. Full pipeline:
STT → classify → state machine → answer check → instruction build → LLM → enforce → clean → TTS
"""

import logging
import time
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from app.config import (
    SESSION_TIMEOUT_MINUTES, STT_CONFIDENCE_THRESHOLD, MAX_ENFORCE_RETRIES,
    ENABLE_HOMEWORK_OCR,
)
from app.database import get_db
from app.models import Student, Session, SessionTurn, Question
from app.routers.auth import get_current_user

from app.voice.stt import get_stt, is_low_confidence
from app.voice.tts import get_tts
from app.voice.clean_for_tts import clean_for_tts

from app.tutor.input_classifier import classify_student_input
from app.tutor.state_machine import transition, route_after_evaluation, Action
from app.tutor.answer_checker import check_math_answer
from app.tutor.instruction_builder import build_prompt
from app.tutor.enforcer import enforce, get_safe_fallback
from app.tutor.llm import get_llm
from app.tutor import memory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/student", tags=["student"])


# ─── Request/Response Models ─────────────────────────────────────────────────

class SessionStartResponse(BaseModel):
    session_id: str
    greeting_text: str
    greeting_audio_b64: str
    state: str

class MessageResponse(BaseModel):
    didi_text: str
    didi_audio_b64: str
    state: str
    student_transcript: Optional[str] = None  # What Whisper heard
    question_id: Optional[str] = None
    verdict: Optional[str] = None
    diagnostic: Optional[str] = None
    # Latency metrics (ms)
    stt_ms: int = 0
    llm_ms: int = 0
    tts_ms: int = 0
    total_ms: int = 0

class SessionEndResponse(BaseModel):
    summary_text: str
    summary_audio_b64: str
    questions_attempted: int
    questions_correct: int


# ─── Session Start ───────────────────────────────────────────────────────────

@router.post("/session/start", response_model=SessionStartResponse)
def start_session(
    user: dict = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    if user.get("role") != "student":
        raise HTTPException(403, "Student access only")

    student_id = user["sub"]
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(404, "Student not found")

    # Close any open sessions for this student
    open_sessions = (
        db.query(Session)
        .filter(
            Session.student_id == student_id,
            Session.ended_at == None,
            Session.session_type == "student",
        )
        .all()
    )
    for s in open_sessions:
        s.ended_at = datetime.now(timezone.utc)
        s.state = "SESSION_COMPLETE"
    db.commit()

    # Create new session — MVP: Math only, skip topic discovery
    session = Session(
        student_id=student_id,
        session_type="student",
        subject="math",
        chapter="ch1_rational_numbers",
        state="GREETING",
        language=student.preferred_language,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Pick first question (or weakest skill question for returning students)
    first_question = memory.pick_next_question(
        db, student_id, "math", "ch1_rational_numbers", asked_question_ids=[]
    )
    if first_question:
        session.current_question_id = first_question["id"]

    # Generate greeting with first question
    if first_question:
        greeting_text = (
            f"Namaste {student.name}! Chalo math practice karte hain. "
            f"Pehla sawaal: {first_question['question_voice']}"
        )
        session.state = "WAITING_ANSWER"
    else:
        greeting_text = f"Namaste {student.name}! Chalo math practice karte hain."
        session.state = "SESSION_COMPLETE"  # No questions available

    tts = get_tts()
    tts_result = tts.synthesize(greeting_text, student.preferred_language)
    db.commit()

    # Log greeting turn
    turn = SessionTurn(
        session_id=session.id,
        turn_number=0,
        speaker="didi",
        transcript="",
        state_before="GREETING",
        state_after=session.state,
        didi_response=greeting_text,
        question_id=session.current_question_id,
        tts_latency_ms=tts_result.latency_ms,
    )
    db.add(turn)
    db.commit()

    return SessionStartResponse(
        session_id=session.id,
        greeting_text=greeting_text,
        greeting_audio_b64=base64.b64encode(tts_result.audio_bytes).decode(),
        state="DISCOVERING_TOPIC",
    )


# ─── Main Message Handler ───────────────────────────────────────────────────

@router.post("/session/message", response_model=MessageResponse)
def process_message(
    session_id: str = Form(...),
    audio: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    user: dict = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    THE MAIN LOOP.
    Accept audio or text → process through full pipeline → return audio response.
    """
    t_start = time.perf_counter()

    if user.get("role") != "student":
        raise HTTPException(403, "Student access only")

    # Load session
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    if session.ended_at:
        raise HTTPException(400, "Session already ended")

    student = db.query(Student).filter(Student.id == session.student_id).first()

    # ── Step 1: STT (if audio) ────────────────────────────────────────────
    stt_latency = 0
    if audio:
        audio_bytes = audio.file.read()
        logger.info(f"STT: received {len(audio_bytes)} bytes of audio")

        try:
            stt = get_stt()
            # Auto-detect language - students speak Hinglish (English math terms)
            # Forcing Hindi converts English words to garbage Devanagari
            stt_result = stt.transcribe(audio_bytes)  # No language = auto-detect
            stt_latency = stt_result.latency_ms
            student_text = stt_result.text
            # Log raw transcript for debugging
            logger.info(f"STT transcript: '{student_text}' (conf={stt_result.confidence:.2f}, lang={stt_result.language_detected}, {stt_latency}ms)")
        except Exception as e:
            logger.error(f"STT failed: {e}")
            return _quick_response(
                db, session,
                "Voice samajh nahi aayi. Text type karo ya phir try karo.",
                student_text="[stt error]",
                stt_latency=0,
            )

        # Low confidence → ask to repeat
        if is_low_confidence(stt_result):
            return _quick_response(
                db, session,
                "Sorry, samajh nahi aaya. Ek baar phir boliye?",
                student_text="[low confidence]",
                stt_latency=stt_latency,
            )
    elif text:
        student_text = text.strip()
    else:
        raise HTTPException(400, "Audio or text required")

    if not student_text:
        return _quick_response(
            db, session,
            "Kuch sunai nahi diya. Ek baar phir boliye?",
            student_text="[empty]",
            stt_latency=stt_latency,
        )

    # ── Step 2: Classify input ────────────────────────────────────────────
    # MVP: No topic discovery (math only). Subject detection removed.

    category = classify_student_input(
        student_text,
        current_state=session.state,
        subject=session.subject or "math",
    )
    logger.info(f"Input: '{student_text[:50]}' → category={category}, state={session.state}")

    # Handle SILENCE without LLM — just give a gentle nudge
    if category == "SILENCE":
        nudge = "Aap wahan ho? Koi sawaal hai toh puchiye."
        return _quick_response(
            db, session, nudge,
            student_text="[silence]",
            stt_latency=stt_latency,
        )

    # ── Step 3: State machine transition ──────────────────────────────────
    # Build asked questions list for this session
    asked_ids = [
        t.question_id for t in session.turns
        if t.question_id and t.verdict in ("CORRECT", "INCORRECT")
    ]

    ctx = {
        "student_text": student_text,
        "subject": session.subject or "math",
        "chapter": session.chapter or "ch1_rational_numbers",
        "current_question_id": session.current_question_id,
        "current_hint_level": session.current_hint_level,
        "current_reteach_count": session.current_reteach_count,
        "questions_attempted": session.questions_attempted,
        "questions_correct": session.questions_correct,
        "total_hints_used": session.total_hints_used,
    }

    state_before = session.state
    new_state, action = transition(session.state, category, ctx)

    # ── Step 4: Answer evaluation (if needed) ─────────────────────────────
    verdict_obj = None
    verdict_str = None
    diagnostic = None

    if action.action_type == "evaluate_answer" and session.current_question_id:
        question = db.query(Question).filter(
            Question.id == session.current_question_id
        ).first()

        if question:
            verdict_obj = check_math_answer(
                student_text,
                question.answer,
                question.answer_variants or [],
            )
            verdict_str = verdict_obj.verdict
            diagnostic = verdict_obj.diagnostic
            action.verdict = verdict_obj

            # Route based on verdict
            new_state, action.action_type = route_after_evaluation(
                verdict_obj,
                session.current_hint_level,
                session.questions_attempted + 1,
            )
            action.verdict = verdict_obj

            # Update session counters
            session.questions_attempted += 1
            if verdict_obj.correct:
                session.questions_correct += 1
                session.current_hint_level = 0
                # Update skill mastery
                memory.update_skill(
                    db, session.student_id, session.subject,
                    question.target_skill, True,
                )
            else:
                session.current_hint_level += 1
                session.total_hints_used += 1
                memory.update_skill(
                    db, session.student_id, session.subject,
                    question.target_skill, False,
                )

    # ── Step 5: Pick next question (if needed) ────────────────────────────
    question_data = None
    if action.action_type in ("read_question", "pick_next_question"):
        if session.current_question_id and action.action_type != "pick_next_question":
            # Re-read current question
            question_data = _load_question(db, session.current_question_id)
        else:
            # Pick new question
            q = memory.pick_next_question(
                db, session.student_id,
                session.subject or "math",
                session.chapter or "ch1_rational_numbers",
                asked_ids,
                difficulty_preference=action.extra.get("difficulty"),
            )
            if q:
                question_data = q
                session.current_question_id = q["id"]
                session.current_hint_level = 0
            else:
                # No more questions → end session
                new_state = "SESSION_COMPLETE"
                action = Action("end_session", student_text=student_text)
    elif action.action_type in ("give_hint", "show_solution"):
        question_data = _load_question(db, session.current_question_id)

    # ── Step 6: Build LLM prompt ──────────────────────────────────────────
    skill_data = None
    if question_data:
        skill_data = memory.get_skill(
            db, session.student_id, question_data.get("target_skill", "")
        )

    prev_response = None
    if session.turns:
        last_didi_turn = [t for t in session.turns if t.speaker == "didi"]
        if last_didi_turn:
            prev_response = last_didi_turn[-1].didi_response

    session_ctx = {
        "subject": session.subject,
        "chapter": session.chapter,
        "questions_attempted": session.questions_attempted,
        "questions_correct": session.questions_correct,
        "total_hints_used": session.total_hints_used,
    }

    messages = build_prompt(action, session_ctx, question_data, skill_data, prev_response)

    # ── Step 7: LLM generate ─────────────────────────────────────────────
    llm = get_llm()
    llm_result = llm.generate(messages)
    didi_text = llm_result.text

    # ── Step 8: Enforce ──────────────────────────────────────────────────
    for attempt in range(MAX_ENFORCE_RETRIES):
        enforce_result = enforce(
            didi_text, new_state,
            verdict=verdict_str,
            student_answer=student_text,
            language=session.language,
            previous_response=prev_response,
        )
        if enforce_result.passed:
            didi_text = enforce_result.text
            break
        # Failed — try re-prompting with stricter instructions
        didi_text = enforce_result.text  # Use partially cleaned version
        if attempt == MAX_ENFORCE_RETRIES - 1:
            didi_text = get_safe_fallback(new_state)
            logger.warning(f"Enforcer failed {MAX_ENFORCE_RETRIES}x, using fallback for {new_state}")

    # ── Step 9: Clean for TTS ────────────────────────────────────────────
    cleaned_text = clean_for_tts(didi_text)

    # ── Step 10: TTS ─────────────────────────────────────────────────────
    tts = get_tts()
    try:
        tts_result = tts.synthesize(cleaned_text, session.language)
        audio_b64 = base64.b64encode(tts_result.audio_bytes).decode()
        tts_latency = tts_result.latency_ms
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        audio_b64 = ""  # Text fallback
        tts_latency = 0

    # ── Step 11: Save turn and update session ─────────────────────────────
    turn_number = len(session.turns) + 1
    turn = SessionTurn(
        session_id=session.id,
        turn_number=turn_number,
        speaker="student",
        transcript=student_text,
        input_category=category,
        state_before=state_before,
        state_after=new_state,
        question_id=session.current_question_id,
        verdict=verdict_str,
        didi_response=didi_text,
        llm_latency_ms=llm_result.latency_ms,
        tts_latency_ms=tts_latency,
        stt_latency_ms=stt_latency,
    )
    db.add(turn)

    session.state = new_state
    db.commit()

    total_ms = int((time.perf_counter() - t_start) * 1000)
    logger.info(
        f"Turn {turn_number}: {total_ms}ms total | "
        f"STT={stt_latency}ms LLM={llm_result.latency_ms}ms TTS={tts_latency}ms | "
        f"{state_before}→{new_state} [{category}]"
    )

    return MessageResponse(
        didi_text=didi_text,
        didi_audio_b64=audio_b64,
        state=new_state,
        student_transcript=student_text,
        question_id=session.current_question_id,
        verdict=verdict_str,
        diagnostic=diagnostic,
        stt_ms=stt_latency,
        llm_ms=llm_result.latency_ms,
        tts_ms=tts_latency,
        total_ms=total_ms,
    )


# ─── Session End ─────────────────────────────────────────────────────────────

@router.post("/session/end", response_model=SessionEndResponse)
def end_session(
    session_id: str = Form(...),
    user: dict = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    # Generate summary
    summary = (
        f"Aaj aapne {session.questions_attempted} sawaal kiye, "
        f"{session.questions_correct} sahi the. "
    )
    if session.questions_attempted > 0:
        acc = session.questions_correct / session.questions_attempted * 100
        summary += f"Accuracy: {acc:.0f}%. "
    summary += "Kal phir milte hain!"

    # TTS for summary
    tts = get_tts()
    try:
        tts_result = tts.synthesize(summary, session.language)
        audio_b64 = base64.b64encode(tts_result.audio_bytes).decode()
    except Exception:
        audio_b64 = ""

    session.state = "SESSION_COMPLETE"
    session.ended_at = datetime.now(timezone.utc)
    session.summary_text = summary
    db.commit()

    return SessionEndResponse(
        summary_text=summary,
        summary_audio_b64=audio_b64,
        questions_attempted=session.questions_attempted,
        questions_correct=session.questions_correct,
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _quick_response(
    db: DBSession, session: Session, text: str,
    student_text: str = "", stt_latency: int = 0,
) -> MessageResponse:
    """Quick response without full pipeline (for low confidence, empty input)."""
    tts = get_tts()
    try:
        tts_result = tts.synthesize(clean_for_tts(text), session.language)
        audio_b64 = base64.b64encode(tts_result.audio_bytes).decode()
    except Exception:
        audio_b64 = ""

    turn = SessionTurn(
        session_id=session.id,
        turn_number=len(session.turns) + 1,
        speaker="student",
        transcript=student_text,
        state_before=session.state,
        state_after=session.state,
        didi_response=text,
        stt_latency_ms=stt_latency,
    )
    db.add(turn)
    db.commit()

    return MessageResponse(
        didi_text=text,
        didi_audio_b64=audio_b64,
        state=session.state,
    )


def _load_question(db: DBSession, question_id: Optional[str]) -> Optional[dict]:
    if not question_id:
        return None
    q = db.query(Question).filter(Question.id == question_id).first()
    if not q:
        return None
    return {
        "id": q.id, "subject": q.subject, "chapter": q.chapter,
        "question_type": q.question_type, "question_text": q.question_text,
        "question_voice": q.question_voice, "answer": q.answer,
        "answer_variants": q.answer_variants or [], "hints": q.hints or [],
        "solution": q.solution or "", "target_skill": q.target_skill,
        "difficulty": q.difficulty, "eval_method": q.eval_method,
        "key_concepts": q.key_concepts or [],
    }
