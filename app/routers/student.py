"""
IDNA EdTech v7.3 — Student Session Router
The main interaction loop. Full pipeline:
STT → classify → state machine → answer check → instruction build → LLM → enforce → clean → TTS

v7.1: Added streaming endpoint for sentence-level TTS (reduces perceived latency).
v7.3: Async LLM classifier, conversation history, run_in_threadpool for DB calls.
"""

import logging
import time
import base64
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm.attributes import flag_modified

from app.config import (
    SESSION_TIMEOUT_MINUTES, STT_CONFIDENCE_THRESHOLD, MAX_ENFORCE_RETRIES,
    ENABLE_HOMEWORK_OCR,
)
from app.database import get_db
from app.models import Student, Session, SessionTurn, Question
from app.routers.auth import get_current_user

from app.voice.stt import get_stt, is_low_confidence
from app.voice.tts import get_tts
from app.voice.clean_for_tts import clean_for_tts, digits_to_english_words

from app.tutor.input_classifier import classify
from openai import AsyncOpenAI
from app.config import OPENAI_API_KEY
from app.tutor.state_machine import transition, route_after_evaluation, Action
from app.tutor.answer_checker import check_math_answer
from app.tutor.instruction_builder import build_prompt
from app.tutor.enforcer import enforce, light_enforce, get_safe_fallback
from app.tutor.llm import get_llm
from app.tutor import memory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/student", tags=["student"])


def get_tts_language(session) -> str:
    """
    v7.3.19 Fix 1: Map language_pref to TTS language code.
    If student switched to English, use en-IN for TTS so numbers are spoken in English.
    """
    pref = getattr(session, 'language_pref', None) or 'hinglish'
    if pref == 'english':
        return 'en-IN'
    # For hindi and hinglish, use the session's default language (usually hi-IN)
    return session.language or 'hi-IN'


def prepare_for_tts(text: str, session) -> str:
    """
    v7.3.20: Prepare text for TTS with language-specific cleaning.
    1. Always apply clean_for_tts (math symbols → words)
    2. If language_pref is 'english', also convert digits to English words
    """
    cleaned = clean_for_tts(text)
    pref = getattr(session, 'language_pref', None) or 'hinglish'
    if pref == 'english':
        cleaned = digits_to_english_words(cleaned)
    return cleaned

# Module-level singleton for OpenAI client (Fix 3: avoid creating per request)
_openai_client: AsyncOpenAI = None

def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


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
    chapter = "ch1_square_and_cube"  # Default to new chapter (was ch1_rational_numbers)
    session = Session(
        student_id=student_id,
        session_type="student",
        subject="math",
        chapter=chapter,
        state="GREETING",
        language=student.preferred_language,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Pick first question (or weakest skill question for returning students)
    first_question = memory.pick_next_question(
        db, student_id, "math", chapter, asked_question_ids=[]
    )
    if first_question:
        session.current_question_id = first_question["id"]

    # Generate greeting WITH teaching (P0 fix: don't skip teaching)
    if first_question:
        # Get skill teaching content
        from app.content.seed_questions import SKILL_TEACHING
        skill = first_question.get("target_skill", "")
        lesson = SKILL_TEACHING.get(skill, {})

        # Get pre_teach content (new format) or teaching (old format)
        pre_teach = lesson.get("pre_teach") or lesson.get("teaching", "")

        if pre_teach:
            # Start with teaching, then ask question
            greeting_text = (
                f"Namaste {student.name}! Aaj hum {lesson.get('title_hi', lesson.get('name', 'math'))} "
                f"seekhenge. {pre_teach} Samajh aaya?"
            )
            session.state = "TEACHING"
        else:
            # No teaching content available, ask question directly (fallback)
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
        state=session.state,
    )


# ─── Main Message Handler ───────────────────────────────────────────────────

@router.post("/session/message", response_model=MessageResponse)
async def process_message(
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

    # Load session (wrapped in threadpool to avoid blocking event loop)
    session = await run_in_threadpool(
        lambda: db.query(Session).filter(Session.id == session_id).first()
    )
    if not session:
        raise HTTPException(404, "Session not found")
    if session.ended_at:
        raise HTTPException(400, "Session already ended")

    student = await run_in_threadpool(
        lambda: db.query(Student).filter(Student.id == session.student_id).first()
    )

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

        # Garbled transcription → ask to repeat (skip classifier)
        if stt_result.garbled:
            return _quick_response(
                db, session,
                "Ek baar phir boliye?",
                student_text="[garbled]",
                stt_latency=stt_latency,
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

    # v7.3.0: Use async LLM classifier (module-level singleton)
    classify_result = await classify(
        student_text,
        current_state=session.state,
        subject=session.subject or "math",
        client=get_openai_client(),
    )
    category = classify_result["category"]
    logger.info(f"CLASSIFIER: text='{student_text[:50]}' → category={category}, extras={classify_result.get('extras', {})}")
    # Handle LANGUAGE_SWITCH preference from classifier
    if category == "LANGUAGE_SWITCH" and classify_result.get("extras", {}).get("preferred_language"):
        session.language_pref = classify_result["extras"]["preferred_language"]
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
        "chapter": session.chapter or "ch1_square_and_cube",
        "current_question_id": session.current_question_id,
        "current_hint_level": session.current_hint_level,
        "current_reteach_count": session.current_reteach_count,
        "questions_attempted": session.questions_attempted,
        "questions_correct": session.questions_correct,
        "total_hints_used": session.total_hints_used,
        # v7.2.0: Teaching progression fields
        "teaching_turn": session.teaching_turn or 0,
        "explanations_given": session.explanations_given or [],
        "language_pref": session.language_pref or "hinglish",
    }

    state_before = session.state
    new_state, action = transition(session.state, category, ctx)

    # ── Step 4: Answer evaluation (if needed) ─────────────────────────────
    verdict_obj = None
    verdict_str = None
    diagnostic = None

    if action.action_type == "evaluate_answer" and session.current_question_id:
        question = await run_in_threadpool(
            lambda: db.query(Question).filter(
                Question.id == session.current_question_id
            ).first()
        )

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
            # Add current question to asked_ids to avoid repeating it
            if session.current_question_id and session.current_question_id not in asked_ids:
                asked_ids.append(session.current_question_id)
            # Pick new question
            q = memory.pick_next_question(
                db, session.student_id,
                session.subject or "math",
                session.chapter or "ch1_square_and_cube",
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
    elif action.action_type in ("give_hint", "show_solution", "teach_concept"):
        # Load question for hints, solutions, and teaching (to get skill info)
        if session.current_question_id:
            question_data = _load_question(db, session.current_question_id)

    # ── Step 6: Build LLM prompt ──────────────────────────────────────────
    skill_data = None
    if question_data:
        skill_data = memory.get_skill(
            db, session.student_id, question_data.get("target_skill", "")
        )

    prev_response = None
    if session.turns:
        # Every turn has didi_response - get the most recent one
        prev_response = session.turns[-1].didi_response

    # v7.2.0: Update session fields based on action
    if action.language_pref:
        session.language_pref = action.language_pref
    if action.extra.get("reset_teaching_turn"):
        session.teaching_turn = 0
        session.explanations_given = []
    elif action.teaching_turn > 0:
        session.teaching_turn = action.teaching_turn

    session_ctx = {
        "subject": session.subject,
        "chapter": session.chapter,
        "questions_attempted": session.questions_attempted,
        "questions_correct": session.questions_correct,
        "total_hints_used": session.total_hints_used,
        # v7.2.0: Include language preference for prompt injection
        "language_pref": session.language_pref or "hinglish",
        "explanations_given": session.explanations_given or [],
    }

    # v7.3.0: Record student input to conversation history
    if session.conversation_history is None:
        session.conversation_history = []
    session.conversation_history.append({"role": "user", "content": student_text})
    flag_modified(session, "conversation_history")

    messages = build_prompt(action, session_ctx, question_data, skill_data, prev_response, session.conversation_history)

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
            language=get_tts_language(session),
            previous_response=prev_response,
        )
        if enforce_result.passed:
            didi_text = enforce_result.text
            break
        # Failed — try re-prompting with stricter instructions
        didi_text = enforce_result.text  # Use partially cleaned version
        if attempt == MAX_ENFORCE_RETRIES - 1:
            # v7.3.21 Fix 3: Pass language_pref for language-aware fallbacks
            didi_text = get_safe_fallback(new_state, prev_response, session.language_pref or "hinglish")
            logger.warning(f"Enforcer failed {MAX_ENFORCE_RETRIES}x, using fallback for {new_state}")

    # v7.3.0: Record Didi's response to conversation history
    session.conversation_history.append({"role": "assistant", "content": didi_text})
    flag_modified(session, "conversation_history")

    # ── Step 9: Clean for TTS ────────────────────────────────────────────
    cleaned_text = prepare_for_tts(didi_text, session)

    # ── Step 10: TTS ─────────────────────────────────────────────────────
    tts = get_tts()
    try:
        tts_result = tts.synthesize(cleaned_text, get_tts_language(session))
        audio_b64 = base64.b64encode(tts_result.audio_bytes).decode()
        tts_latency = tts_result.latency_ms
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        audio_b64 = ""  # Text fallback
        tts_latency = 0

    # ── Step 11: Save turns and update session ─────────────────────────────
    # Fix 5: Create separate turns for student input and didi response
    turn_base = len(session.turns) + 1
    student_turn = SessionTurn(
        session_id=session.id,
        turn_number=turn_base,
        speaker="student",
        transcript=student_text,
        input_category=category,
        state_before=state_before,
        state_after=new_state,
        question_id=session.current_question_id,
        verdict=verdict_str,
        stt_latency_ms=stt_latency,
    )
    await run_in_threadpool(lambda: db.add(student_turn))

    didi_turn = SessionTurn(
        session_id=session.id,
        turn_number=turn_base + 1,
        speaker="didi",
        state_before=state_before,
        state_after=new_state,
        question_id=session.current_question_id,
        didi_response=didi_text,
        llm_latency_ms=llm_result.latency_ms,
        tts_latency_ms=tts_latency,
    )
    await run_in_threadpool(lambda: db.add(didi_turn))

    session.state = new_state
    await run_in_threadpool(lambda: db.commit())

    total_ms = int((time.perf_counter() - t_start) * 1000)
    logger.info(
        f"Turn {turn_base}: {total_ms}ms total | "
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


# ─── Streaming Response (v7.1) ────────────────────────────────────────────────

@router.post("/session/message-stream")
async def process_message_stream(
    request: Request,
    user: dict = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    v7.1 Streaming endpoint: LLM streams → sentence-level TTS → SSE to frontend.
    Reduces perceived latency from ~10s to ~3s by starting audio playback earlier.
    """
    if user.get("role") != "student":
        raise HTTPException(403, "Student access only")

    # Parse request body
    body = await request.json()
    session_id = body.get("session_id")
    audio_b64 = body.get("audio")
    text_input = body.get("text")

    session = await run_in_threadpool(
        lambda: db.query(Session).filter(Session.id == session_id).first()
    )
    if not session:
        raise HTTPException(404, "Session not found")

    student = await run_in_threadpool(
        lambda: db.query(Student).filter(Student.id == session.student_id).first()
    )
    state_before = session.state

    # ── STT ──
    stt_latency = 0
    stt_garbled = False
    if audio_b64:
        audio_bytes = base64.b64decode(audio_b64)
        stt = get_stt()
        stt_result = stt.transcribe(audio_bytes)
        student_text = stt_result.text
        stt_latency = stt_result.latency_ms
        stt_garbled = stt_result.garbled
    else:
        student_text = text_input or ""

    # Handle garbled transcription
    if stt_garbled:
        nudge = "Ek baar phir boliye?"
        tts = get_tts()
        tts_result = tts.synthesize(nudge, get_tts_language(session))
        audio_chunk = base64.b64encode(tts_result.audio_bytes).decode()

        # Fix 4: Update conversation_history for early returns
        if session.conversation_history is None:
            session.conversation_history = []
        session.conversation_history.append({"role": "user", "content": "[garbled]"})
        session.conversation_history.append({"role": "assistant", "content": nudge})
        flag_modified(session, "conversation_history")
        await run_in_threadpool(lambda: db.commit())

        async def garbled_stream():
            yield f"data: {json.dumps({'type': 'audio_chunk', 'index': 0, 'audio': audio_chunk, 'is_last': True})}\n\n"
            yield f"data: {json.dumps({'type': 'text', 'content': nudge})}\n\n"
            yield f"data: {json.dumps({'type': 'transcript', 'content': '[garbled]'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'state': session.state})}\n\n"

        return StreamingResponse(garbled_stream(), media_type="text/event-stream")

    # ── Classify ──
    # v7.3.0: Use async LLM classifier (module-level singleton)
    classify_result = await classify(
        student_text,
        current_state=session.state,
        subject=session.subject or "math",
        client=get_openai_client(),
    )
    category = classify_result["category"]
    logger.info(f"CLASSIFIER: text='{student_text[:50]}' → category={category}, extras={classify_result.get('extras', {})}")
    # Handle LANGUAGE_SWITCH preference from classifier (Break 4 fix)
    if category == "LANGUAGE_SWITCH" and classify_result.get("extras", {}).get("preferred_language"):
        session.language_pref = classify_result["extras"]["preferred_language"]

    # Handle silence without LLM
    if category == "SILENCE":
        nudge = "Aap wahan ho? Koi sawaal hai toh puchiye."
        tts = get_tts()
        tts_result = tts.synthesize(nudge, get_tts_language(session))
        audio_chunk = base64.b64encode(tts_result.audio_bytes).decode()

        # Fix 4: Update conversation_history for early returns
        if session.conversation_history is None:
            session.conversation_history = []
        session.conversation_history.append({"role": "user", "content": "[silence]"})
        session.conversation_history.append({"role": "assistant", "content": nudge})
        flag_modified(session, "conversation_history")
        await run_in_threadpool(lambda: db.commit())

        async def silence_stream():
            yield f"data: {json.dumps({'type': 'audio_chunk', 'index': 0, 'audio': audio_chunk, 'is_last': True})}\n\n"
            yield f"data: {json.dumps({'type': 'text', 'content': nudge})}\n\n"
            yield f"data: {json.dumps({'type': 'transcript', 'content': '[silence]'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'state': session.state})}\n\n"

        return StreamingResponse(silence_stream(), media_type="text/event-stream")

    # ── State transition ──
    question_data = None
    if session.current_question_id:
        question_data = _load_question(db, session.current_question_id)

    # Build context for state machine (same as non-streaming endpoint)
    ctx = {
        "student_text": student_text,
        "subject": session.subject or "math",
        "chapter": session.chapter or "ch1_square_and_cube",
        "current_question_id": session.current_question_id,
        "current_hint_level": session.current_hint_level,
        "current_reteach_count": session.current_reteach_count,
        "questions_attempted": session.questions_attempted,
        "questions_correct": session.questions_correct,
        "total_hints_used": session.total_hints_used,
        # v7.2.0: Teaching progression fields
        "teaching_turn": session.teaching_turn or 0,
        "explanations_given": session.explanations_given or [],
        "language_pref": session.language_pref or "hinglish",
    }
    new_state, action = transition(session.state, category, ctx)

    # ── Answer check (if ANSWER) ──
    verdict = None
    verdict_str = None
    if action.action_type == "evaluate_answer" and session.current_question_id:
        question = await run_in_threadpool(
            lambda: db.query(Question).filter(
                Question.id == session.current_question_id
            ).first()
        )
        if question:
            verdict = check_math_answer(
                student_text,
                question.answer,
                question.answer_variants or [],
            )
            verdict_str = verdict.verdict
            # Route based on verdict
            new_state, action.action_type = route_after_evaluation(
                verdict,
                session.current_hint_level,
                session.questions_attempted + 1,
            )
            action.verdict = verdict

            # v7.3.26: Update session counters (same as non-streaming)
            session.questions_attempted += 1
            if verdict.correct:
                session.questions_correct += 1
                session.current_hint_level = 0
            else:
                session.current_hint_level += 1
                session.total_hints_used += 1

    # v7.3.26: Pick next question (if needed) — CRITICAL FIX
    # This was missing, causing correct answers to not advance to next question
    if action.action_type in ("read_question", "pick_next_question"):
        if session.current_question_id and action.action_type != "pick_next_question":
            # Re-read current question
            question_data = _load_question(db, session.current_question_id)
        else:
            # Add current question to asked_ids to avoid repeating it
            asked_ids = [
                t.question_id for t in session.turns
                if t.question_id and t.verdict in ("CORRECT", "INCORRECT")
            ]
            if session.current_question_id and session.current_question_id not in asked_ids:
                asked_ids.append(session.current_question_id)
            # Pick new question
            q = memory.pick_next_question(
                db, session.student_id,
                session.subject or "math",
                session.chapter or "ch1_square_and_cube",
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
    elif action.action_type in ("give_hint", "show_solution", "teach_concept"):
        # Load question for hints, solutions, and teaching
        if session.current_question_id:
            question_data = _load_question(db, session.current_question_id)

    # ── Build prompt ──
    # v7.3.22 Fix 2: Include language_pref in session_ctx for streaming endpoint
    session_ctx = {
        "subject": session.subject,
        "chapter": session.chapter,
        "questions_attempted": session.questions_attempted,
        "questions_correct": session.questions_correct,
        "language_pref": session.language_pref or "hinglish",
    }
    prev_response = session.turns[-1].didi_response if session.turns else None

    # v7.3.0: Record student input to conversation history
    if session.conversation_history is None:
        session.conversation_history = []
    session.conversation_history.append({"role": "user", "content": student_text})
    flag_modified(session, "conversation_history")

    messages = build_prompt(action, session_ctx, question_data, None, prev_response, session.conversation_history)

    # ── Streaming LLM + TTS ──
    llm = get_llm()
    tts = get_tts()

    async def stream_response():
        """SSE: stream audio chunks as sentences complete."""
        full_text = ""
        sentence_index = 0
        cancelled = False

        # Fix 2: Wrap in try/finally to persist state on cancellation
        try:
            async for sentence in llm.generate_streaming(messages):
                # Clean for TTS (v7.3.20: includes digits→words for English)
                cleaned = prepare_for_tts(sentence, session)

                # v7.3.16 Fix 2: Light enforce per chunk (only banned phrases)
                # Do NOT run full enforce() here — it breaks length/sentence rules mid-stream
                cleaned = light_enforce(cleaned, verdict=verdict_str)
                full_text += " " + cleaned

                # Generate TTS for this sentence
                try:
                    tts_result = await tts.synthesize_async(cleaned, get_tts_language(session))
                    audio_chunk = base64.b64encode(tts_result.audio_bytes).decode()

                    # Stream audio chunk to frontend
                    yield f"data: {json.dumps({'type': 'audio_chunk', 'index': sentence_index, 'audio': audio_chunk, 'is_last': False})}\n\n"
                    sentence_index += 1
                except Exception as e:
                    logger.error(f"TTS error for sentence: {e}")

            # Mark last chunk
            if sentence_index > 0:
                yield f"data: {json.dumps({'type': 'last_chunk'})}\n\n"

            # v7.3.16 Fix 2: Run full enforce() on complete text at end
            full_text = full_text.strip()
            enforce_result = enforce(
                full_text, new_state,
                verdict=verdict_str,
                student_answer=student_text,
                language=get_tts_language(session),
                previous_response=prev_response,
            )
            full_text = enforce_result.text

            # Send full text and metadata
            yield f"data: {json.dumps({'type': 'text', 'content': full_text})}\n\n"
            yield f"data: {json.dumps({'type': 'transcript', 'content': student_text})}\n\n"
            yield f"data: {json.dumps({'type': 'verdict', 'value': verdict_str, 'diagnostic': verdict.diagnostic if verdict else None})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'state': new_state})}\n\n"

        except asyncio.CancelledError:
            # Fix 2: Handle cancellation gracefully - persist partial state
            cancelled = True
            logger.info(f"Stream cancelled after {sentence_index} sentences, persisting partial state")

        finally:
            # Fix 2: Always persist state in finally block
            full_text = full_text.strip()

            # Record Didi's response to conversation history (even if partial)
            if full_text:
                session.conversation_history.append({"role": "assistant", "content": full_text})
                flag_modified(session, "conversation_history")

            # Fix 5: Create separate turns for student and didi
            turn_base = len(session.turns) + 1
            student_turn = SessionTurn(
                session_id=session.id,
                turn_number=turn_base,
                speaker="student",
                transcript=student_text,
                input_category=category,
                state_before=state_before,
                state_after=new_state,
                question_id=session.current_question_id,
                verdict=verdict_str,
                stt_latency_ms=stt_latency,
            )
            await run_in_threadpool(lambda: db.add(student_turn))

            if full_text:
                didi_turn = SessionTurn(
                    session_id=session.id,
                    turn_number=turn_base + 1,
                    speaker="didi",
                    state_before=state_before,
                    state_after=new_state,
                    question_id=session.current_question_id,
                    didi_response=full_text,
                )
                await run_in_threadpool(lambda: db.add(didi_turn))

            session.state = new_state
            await run_in_threadpool(lambda: db.commit())

            if cancelled:
                raise asyncio.CancelledError()

    return StreamingResponse(stream_response(), media_type="text/event-stream")


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
        tts_result = tts.synthesize(summary, get_tts_language(session))
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
        tts_result = tts.synthesize(prepare_for_tts(text, session), get_tts_language(session))
        audio_b64 = base64.b64encode(tts_result.audio_bytes).decode()
    except Exception:
        audio_b64 = ""

    # Fix 1: Update conversation_history before commit
    if session.conversation_history is None:
        session.conversation_history = []
    session.conversation_history.append({"role": "user", "content": student_text})
    session.conversation_history.append({"role": "assistant", "content": text})
    flag_modified(session, "conversation_history")

    # Fix 5: Create separate turns for student input and didi response
    student_turn = SessionTurn(
        session_id=session.id,
        turn_number=len(session.turns) + 1,
        speaker="student",
        transcript=student_text,
        state_before=session.state,
        state_after=session.state,
        stt_latency_ms=stt_latency,
    )
    db.add(student_turn)

    didi_turn = SessionTurn(
        session_id=session.id,
        turn_number=len(session.turns) + 2,
        speaker="didi",
        state_before=session.state,
        state_after=session.state,
        didi_response=text,
    )
    db.add(didi_turn)
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
