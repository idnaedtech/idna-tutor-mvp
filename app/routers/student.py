"""
IDNA EdTech v8.0 — Student Session Router
The main interaction loop. Full pipeline:
STT → classify → state machine → answer check → instruction build → LLM → enforce → clean → TTS

v7.1: Added streaming endpoint for sentence-level TTS (reduces perceived latency).
v7.3: Async LLM classifier, conversation history, run_in_threadpool for DB calls.
v8.0: Complete FSM rewrite with SessionState, 60 state×input transitions, per-state handlers.
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
from app.database import get_db, SessionLocal
from app.models import Student, Session, SessionTurn, Question
from app.routers.auth import get_current_user

from app.voice.stt import get_stt, is_low_confidence
from app.voice.tts import get_tts
from app.voice.clean_for_tts import clean_for_tts, digits_to_english_words

from app.tutor.input_classifier import classify
from openai import AsyncOpenAI
from app.config import OPENAI_API_KEY
# v8.0: Import new FSM modules
from app.state.session import SessionState, TutorState
from app.fsm.transitions import get_transition
from app.fsm.handlers import handle_state
# Keep old imports for backward compatibility during transition
from app.tutor.state_machine import transition, route_after_evaluation, Action
from app.tutor.answer_checker import check_math_answer, Verdict
from app.tutor.answer_evaluator import evaluate_answer
from app.tutor.instruction_builder import build_prompt, build_inline_eval_prompt, CHAPTER_NAMES
# instruction_builder_v9 removed — both endpoints now use build_prompt() from instruction_builder.py
from app.tutor.preprocessing import preprocess_student_message, detect_input_language, check_language_auto_switch
from content_bank.loader import get_content_bank
from app.tutor.enforcer import enforce, light_enforce, get_safe_fallback
from app.tutor.llm import get_llm
from app.tutor import memory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/student", tags=["student"])


# v8.1.0: Normalize legacy state names to v8.0 TutorState values
def _normalize_state(state_str: str) -> TutorState:
    """Map legacy state names to v8.0 TutorState enum.

    Legacy FSM uses: HINT_1, HINT_2, FULL_SOLUTION, SESSION_COMPLETE, etc.
    v8.0 FSM uses: HINT, SESSION_END, etc.
    """
    # Direct mapping for states that exist in both
    try:
        return TutorState(state_str)
    except ValueError:
        pass

    # Map legacy states to v8.0 states
    legacy_mapping = {
        "HINT_1": TutorState.HINT,
        "HINT_2": TutorState.HINT,
        "FULL_SOLUTION": TutorState.HINT,
        "SESSION_COMPLETE": TutorState.SESSION_END,
        "WRAP_UP": TutorState.SESSION_END,
        "EVALUATING": TutorState.WAITING_ANSWER,  # Evaluation happens during WAITING_ANSWER
    }

    if state_str in legacy_mapping:
        return legacy_mapping[state_str]

    # Default fallback - shouldn't happen
    logger.warning(f"Unknown state '{state_str}', defaulting to TEACHING")
    return TutorState.TEACHING


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
    3. P0 FIX: Truncate to MAX_TTS_CHARS (500) at sentence boundary for Sarvam Bulbul
    """
    cleaned = clean_for_tts(text)
    pref = getattr(session, 'language_pref', None) or 'hinglish'
    if pref == 'english':
        cleaned = digits_to_english_words(cleaned)
    
    # P0 FIX: TTS truncation - Sarvam Bulbul handles max ~500 chars well
    MAX_TTS_CHARS = 500
    if len(cleaned) > MAX_TTS_CHARS:
        truncated = cleaned[:MAX_TTS_CHARS]
        # Find last complete sentence (period, Hindi danda, question mark, exclamation)
        last_period = max(
            truncated.rfind('. '),
            truncated.rfind('। '),
            truncated.rfind('? '),
            truncated.rfind('! '),
        )
        if last_period > MAX_TTS_CHARS // 2:  # Only truncate if we keep more than half
            cleaned = truncated[:last_period + 1].strip()
    return cleaned


def format_for_display(text: str) -> str:
    """
    P0 FIX: Format response text for readable display in chat.
    Adds line breaks between sentences for voice-friendly reading.
    """
    # Replace sentence endings with line breaks for readability
    display = text.replace(". ", "." + chr(10)).replace("। ", "।" + chr(10))
    display = display.replace("? ", "?" + chr(10)).replace("! ", "!" + chr(10))
    return display


# Module-level singleton for OpenAI client (Fix 3: avoid creating per request)
_openai_client: AsyncOpenAI = None

def get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _openai_client


async def llm_call_for_eval(messages: list, max_tokens: int = 150) -> str:
    """v7.5.0: Async LLM call wrapper for answer evaluation."""
    client = get_openai_client()
    response = await client.chat.completions.create(
        model="gpt-4.1-mini",  # v10.2.0 Fix 1d: Better model for answer evaluation
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.1,  # Low temp for consistent evaluation
    )
    return response.choices[0].message.content


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
    # v10.3.0: Debug info for chat UI (temporary)
    debug: Optional[dict] = None

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

    # P1 fix: Get questions already answered by this student (across ALL sessions)
    # This prevents serving the same question on page refresh
    prev_answered = (
        db.query(SessionTurn.question_id)
        .join(Session)
        .filter(
            Session.student_id == student_id,
            SessionTurn.question_id.isnot(None),
            SessionTurn.verdict.in_(("CORRECT", "INCORRECT")),
        )
        .distinct()
        .all()
    )
    asked_question_ids = [q[0] for q in prev_answered]

    # v10.4.0: Start at Level 2 for assessment
    # Pick first question at Level 2 — if student gets it right, stay L2; if wrong, drop to L1
    first_question = memory.pick_next_question(
        db, student_id, "math", chapter, asked_question_ids=asked_question_ids,
        current_level=session.current_level,
    )
    if first_question:
        session.current_question_id = first_question["id"]

    # Generate greeting ONLY — teaching happens in TEACHING state after ACK
    # Bug D fix: GREETING must be max 2 sentences, no teaching content
    # V10: Use strings.py for centralized language strings
    from app.tutor.strings import get_text

    # Normalize BCP-47 codes to label format
    lang_raw = student.preferred_language or "hi-IN"
    LANG_NORMALIZE = {
        "hi-IN": "hinglish", "en-IN": "english",
        "hindi": "hindi", "english": "english", "hinglish": "hinglish",
        "telugu": "telugu", "te-IN": "telugu",  # v10.1: Telugu support with BCP-47
    }
    lang = LANG_NORMALIZE.get(lang_raw, "hinglish")

    if first_question:
        # Get skill teaching content for topic announcement only
        from app.content.seed_questions import SKILL_TEACHING
        skill = first_question.get("target_skill", "")
        lesson = SKILL_TEACHING.get(skill, {})

        # GREETING: announce topic only, wait for ACK before teaching
        topic_name = lesson.get("title_hi") or lesson.get("name", "math")
        topic_name_en = lesson.get("name") or lesson.get("title_hi", "math")
        topic_for_greeting = topic_name_en if lang == "english" else topic_name

        # v10.5.2: Warm greeting ONLY — no topic, no question. Wait for student response.
        # Chapter intro comes in next turn (GREETING→TEACHING via chapter_intro flag)
        greeting_text = get_text("warmup_greeting", lang, name=student.name)

        # Stay in GREETING — FSM will transition to TEACHING on ACK
        session.state = "GREETING"
        # P0 FIX: Initialize language_pref from student preference (normalized)
        session.language_pref = lang if lang in ("english", "hindi", "hinglish", "telugu") else "hinglish"
    else:
        # V10: Session end greeting from centralized strings
        # Note: session_end template has {correct} and {total} params, but we don't have them here
        # Fall back to a simple completion message
        if lang == "english":
            greeting_text = f"Hello {student.name}! You've completed all questions in this chapter. Great work! New questions coming tomorrow."
        else:
            greeting_text = f"Namaste {student.name}! Aapne is chapter ke saare sawaal kar liye hain. Bahut accha! Kal naye sawaal milenge."
        session.state = "SESSION_END"  # No questions available
        session.language_pref = lang if lang in ("english", "hindi", "hinglish", "telugu") else "hinglish"

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

    # DEBUG: RAW INPUT logging (P0 debug)
    logger.info(f"RAW INPUT (non-stream): [{student_text}]")

    # ── Step 1.5: Preprocessing (v8.1.0 P0 fixes) ─────────────────────────
    # Order: meta-question (bypass LLM) → language switch → confusion → LLM
    chapter_name = CHAPTER_NAMES.get(session.chapter or "", session.chapter or "")
    current_skill = ""
    if session.current_question_id:
        q_data = _load_question(db, session.current_question_id)
        current_skill = q_data.get("target_skill", "") if q_data else ""

    preprocess_result = preprocess_student_message(
        text=student_text,
        chapter=session.chapter or "",
        chapter_name=chapter_name,
        subject=session.subject or "math",
        current_skill=current_skill,
        language_pref=session.language_pref or "hinglish",
    )

    # DEBUG: META-ROUTE logging (P0 debug)
    logger.info(f"META-ROUTE (non-stream): detected={preprocess_result.meta_question_type}, bypass_llm={preprocess_result.bypass_llm}, template=[{preprocess_result.template_response[:50] if preprocess_result.template_response else 'None'}]")

    # Meta-question: bypass LLM entirely
    if preprocess_result.bypass_llm:
        logger.info(f"v8.1.0: Bypassing LLM for meta-question: {preprocess_result.meta_question_type}")
        return _quick_response(
            db, session,
            preprocess_result.template_response,
            student_text=student_text,
            stt_latency=stt_latency,
        )

    # Language switch: update session preference AND commit immediately
    # P0 Bug A fix: Language must persist across requests
    if preprocess_result.language_switched:
        session.language_pref = preprocess_result.new_language
        db.commit()  # P0 fix: Commit immediately so next request sees the change
        logger.info(f"P0 FIX: Language switched to '{session.language_pref}' and COMMITTED to DB")

    # Confusion: increment counter
    if preprocess_result.confusion_detected:
        session.confusion_count = (session.confusion_count or 0) + 1
        logger.info(f"v8.1.0: Confusion detected, count now {session.confusion_count}")

    # P0 FIX: Emotional distress detection — flag for LLM to acknowledge emotion first
    _student_emotional = False
    if preprocess_result.emotional_distress:
        _student_emotional = True
        logger.info(f"P0 FIX: Emotional distress detected, flagging for LLM")

    # === LANGUAGE AUTO-DETECTION (P0 fix) ===
    # Detects student's input language and auto-switches if they consistently speak English.
    # Works ALONGSIDE the explicit switch detector (preprocessing) and language pre-scan.
    _detected_lang = detect_input_language(student_text)
    _consecutive_english = getattr(session, 'consecutive_english_count', 0) or 0

    # Special case: first student message in GREETING sets language immediately
    if session.state == 'GREETING' and _detected_lang == 'english' and session.language_pref != 'english':
        session.language_pref = 'english'
        session.consecutive_english_count = 1
        db.commit()
        logger.info(f"LANGUAGE AUTO-DETECT: first message in GREETING is English, switched immediately")
    else:
        _should_switch, _new_lang, _updated_count = check_language_auto_switch(
            detected_language=_detected_lang,
            current_session_language=session.language_pref or 'hinglish',
            consecutive_english_count=_consecutive_english,
        )
        session.consecutive_english_count = _updated_count
        if _should_switch:
            session.language_pref = _new_lang
            db.commit()
            logger.info(f"LANGUAGE AUTO-DETECT: switched to {_new_lang} (consecutive={_updated_count})")
        elif _updated_count != _consecutive_english:
            db.commit()  # Persist counter change
    # === END LANGUAGE AUTO-DETECTION ===

    # === LANGUAGE PRE-SCAN (runs on every message) ===
    # Detects language switch requests BEFORE classification.
    # Uses intent patterns, not bare keywords, to avoid false positives.
    # Example false positive: "Why are you speaking in Hindi?" contains "Hindi"
    # but the student wants ENGLISH, not Hindi.
    _text_lower = student_text.lower()

    # English triggers: student wants English
    _english_triggers = [
        "in english", "speak english", "teach english", "english mein",
        "english please", "english me", "talk english", "explain english",
        "respond english", "switch to english", "change to english",
        "can you speak english", "can you teach english",
        "इंग्लिश में", "अंग्रेजी में", "इंग्लिश में बोलो",
        "अंग्रेजी में बोलो", "अंग्रेजी में बात करो",
    ]
    # Also catch: "Why are you speaking in Hindi?" = wants English (complaining about Hindi)
    _complaining_about_hindi = [
        "why hindi", "why in hindi", "why are you speaking hindi",
        "why are you speaking in hindi", "stop speaking hindi",
        "don't speak hindi", "dont speak hindi", "not in hindi",
        "no hindi", "stop hindi", "I said english",
        "हिंदी में क्यों", "हिंदी क्यों",
    ]
    # Hindi triggers: student explicitly WANTS Hindi (intent to switch TO Hindi)
    _hindi_intent_triggers = [
        "speak hindi", "speak in hindi", "talk in hindi",
        "in hindi please", "hindi mein bolo", "hindi me bolo",
        "switch to hindi", "change to hindi", "teach in hindi",
        "hindi mein samjhao", "hindi mein baat karo",
        "हिंदी में बोलो", "हिंदी में समझाओ", "हिंदी में बात करो",
    ]

    _switched = False
    # Check English triggers first
    for trigger in _english_triggers:
        if trigger in _text_lower:
            session.language_pref = "english"
            db.commit()
            logger.info(f"LANGUAGE PRE-SCAN: switched to english (trigger: {trigger})")
            _switched = True
            break

    # Check complaints about Hindi (= wants English)
    if not _switched:
        for trigger in _complaining_about_hindi:
            if trigger in _text_lower:
                session.language_pref = "english"
                db.commit()
                logger.info(f"LANGUAGE PRE-SCAN: switched to english (complaint: {trigger})")
                _switched = True
                break

    # Check Hindi intent triggers LAST (requires explicit intent)
    if not _switched:
        for trigger in _hindi_intent_triggers:
            if trigger in _text_lower:
                session.language_pref = "hindi"
                db.commit()
                logger.info(f"LANGUAGE PRE-SCAN: switched to hindi (trigger: {trigger})")
                _switched = True
                break
    # === END LANGUAGE PRE-SCAN ===

    # === CORRECTION DETECTION (runs on every message) ===
    # Detects when student corrects Didi's math error.
    # Sets a flag so instruction builder acknowledges the correction.
    _correction_triggers = [
        "that's wrong", "thats wrong", "that is wrong",
        "you're wrong", "youre wrong", "you are wrong",
        "wrong answer", "galat", "गलत",
        "that's not right", "not right", "not correct",
        "check again", "check karo", "check kijiye",
        "चेक कीजिए", "चेक करो", "गलत है",
        "nahi", "74 nahi", "that's not",
    ]
    # Pattern: student says "[X] nahi, [Y] hota hai" = correction
    _is_correction = False
    for trigger in _correction_triggers:
        if trigger in _text_lower:
            _is_correction = True
            break
    # Also detect pattern: "X nahi" or "X नहीं" followed by a number
    import re as _re
    if not _is_correction and _re.search(r'\d+\s*(nahi|नहीं|nhi|wrong|galat)', _text_lower):
        _is_correction = True
    if not _is_correction and _re.search(r'(nahi|नहीं|nhi|wrong|galat)\s*.*\d+', _text_lower):
        _is_correction = True

    if _is_correction:
        logger.info(f"CORRECTION DETECTED: student correcting Didi's math")
    # === END CORRECTION DETECTION ===

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
    # P0 Bug A fix: Commit language change immediately
    if category == "LANGUAGE_SWITCH" and classify_result.get("extras", {}).get("preferred_language"):
        session.language_pref = classify_result["extras"]["preferred_language"]
        db.commit()  # P0 fix: Persist language change
        logger.info(f"P0 FIX: Classifier set language to '{session.language_pref}' and COMMITTED")

    # v7.3.28 Fix 3: Empathy one turn max
    # If we already gave empathy, force next message to be ACK and go to TEACHING
    if getattr(session, 'empathy_given', False) and category == "COMFORT":
        category = "ACK"
        logger.info(f"v7.3.28: empathy_given=True, overriding COMFORT → ACK")

    logger.info(f"Input: '{student_text[:50]}' → category={category}, state={session.state}")

    # Handle SILENCE without LLM — just give a gentle nudge
    if category == "SILENCE":
        # P0 FIX: Nudge must respect language preference (was hardcoded Hindi)
        pref = session.language_pref or "hinglish"
        if pref == "english":
            nudge = "Are you there? Feel free to ask any question."
        else:
            nudge = "Aap wahan ho? Koi sawaal hai toh puchiye."
        return _quick_response(
            db, session, nudge,
            student_text="[silence]",
            stt_latency=stt_latency,
        )

    # ── Step 3: State machine transition (v8.0 FSM) ────────────────────────
    # Build asked questions list for this session
    asked_ids = [
        t.question_id for t in session.turns
        if t.question_id and t.verdict in ("CORRECT", "INCORRECT")
    ]

    # v8.0: Build context for old state machine (backward compat)
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
        "teaching_turn": session.teaching_turn or 0,
        "explanations_given": session.explanations_given or [],
        "language_pref": session.language_pref or "hinglish",
    }

    state_before = session.state

    # v8.0: Get transition from new FSM
    transition_result = get_transition(_normalize_state(session.state), category)
    logger.info(f"v8.0: {session.state} × {category} → {transition_result.next_state.value} (action={transition_result.action})")

    # v8.0: CRITICAL - Store language BEFORE calling handler
    # Bug A fix: Ensure commit happens here too (classifier may have already done it)
    extras = classify_result.get("extras", {})
    if transition_result.special == "store_language" and extras.get("preferred_language"):
        session.language_pref = extras["preferred_language"]
        db.commit()  # Bug A fix: Persist immediately
        logger.info(f"v8.0: Language set to '{session.language_pref}' BEFORE handler and COMMITTED")

    # Use old transition for Action object (for backward compat with answer eval)
    new_state, action = transition(session.state, category, ctx)

    # v8.0: Track empathy state based on new transition
    if transition_result.next_state == TutorState.TEACHING:
        session.empathy_given = False
        logger.info("v8.0: Entering TEACHING, resetting empathy_given=False")
    elif transition_result.special == "empathy_first":
        session.empathy_given = True
        logger.info("v8.0: Empathy given, setting empathy_given=True")

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
            # v7.5.0: Use LLM-based answer evaluation with Content Bank context
            try:
                cb = get_content_bank()
                # Get misconceptions from content bank if available
                misconceptions = []
                if question.target_skill:
                    misconceptions = cb.get_misconceptions(question.target_skill)

                eval_result = await evaluate_answer(
                    question_text=question.question_voice or question.question_text,
                    expected_answer=question.answer,
                    acceptable_alternates=question.answer_variants or [],
                    misconceptions=misconceptions,
                    student_response=student_text,
                    llm_call_func=llm_call_for_eval,
                )

                # Convert LLM eval result to Verdict object for compatibility
                verdict_map = {
                    "correct": ("CORRECT", True),
                    "incorrect": ("INCORRECT", False),
                    "partial": ("PARTIAL", False),
                    "idk": ("INCORRECT", False),
                    "unclear": ("INCORRECT", False),
                }
                v_str, v_correct = verdict_map.get(eval_result["verdict"], ("INCORRECT", False))

                verdict_obj = Verdict(
                    correct=v_correct,
                    verdict=v_str,
                    student_parsed=eval_result.get("student_answer_extracted", ""),
                    correct_display=question.answer,
                    diagnostic=eval_result.get("feedback_hi", ""),
                )
                verdict_str = v_str
                diagnostic = eval_result.get("feedback_hi", "")

                logger.info(f"v7.5.0 LLM eval: '{student_text[:30]}' -> {v_str} (extracted: {eval_result.get('student_answer_extracted')})")

            except Exception as e:
                # Fallback to regex-based checker if LLM eval fails
                logger.warning(f"v7.5.0 LLM eval failed, using fallback: {e}")
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

            # DEBUG: Answer evaluation routing (P0 debug 2026-03-07)
            logger.info(f"ANSWER_EVAL: student=[{student_text[:50]}], correct={verdict_obj.correct}, "
                       f"state_before={state_before}, hint_level={session.current_hint_level}, "
                       f"new_state={new_state}, action={action.action_type}")

            # Update session counters
            session.questions_attempted += 1
            if verdict_obj.correct:
                session.questions_correct += 1
                session.current_hint_level = 0
                # v8.1.0: Reset confusion_count on correct answer
                session.confusion_count = 0
                # v10.4.0: Level advancement — 3 correct in a row → advance
                session.consecutive_correct += 1
                session.consecutive_wrong = 0
                if session.consecutive_correct >= 3 and session.current_level < 5:
                    session.current_level += 1
                    session.consecutive_correct = 0
                    logger.info(f"LEVEL_UP: student advanced to Level {session.current_level}")
                # Update skill mastery
                memory.update_skill(
                    db, session.student_id, session.subject,
                    question.target_skill, True,
                )
            else:
                session.current_hint_level += 1
                session.total_hints_used += 1
                # v10.4.0: Level drop — 2 wrong in a row → drop back
                session.consecutive_wrong += 1
                session.consecutive_correct = 0
                if session.consecutive_wrong >= 2 and session.current_level > 1:
                    session.current_level -= 1
                    session.consecutive_wrong = 0
                    logger.info(f"LEVEL_DOWN: student dropped to Level {session.current_level}")
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
            logger.info(f"PICK_NEXT: current_q={session.current_question_id}, asked_ids={asked_ids}, level={session.current_level}")
            q = memory.pick_next_question(
                db, session.student_id,
                session.subject or "math",
                session.chapter or "ch1_square_and_cube",
                asked_ids,
                difficulty_preference=action.extra.get("difficulty"),
                current_level=session.current_level,
            )
            if q:
                question_data = q
                logger.info(f"PICK_NEXT: selected new q={q['id']} (was {session.current_question_id})")
                session.current_question_id = q["id"]
                session.current_hint_level = 0
            else:
                # No more questions → end session
                new_state = "SESSION_COMPLETE"
                action = Action("end_session", student_text=student_text)
    elif action.action_type in ("give_hint", "show_solution", "teach_concept", "answer_meta_question"):
        # Load question for hints, solutions, teaching, and meta-questions (to get skill info)
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
        db.commit()  # P0 FIX: Persist teaching_turn
        logger.info(f"v8.0: Teaching turn set to {action.teaching_turn} and COMMITTED")

    # v8.1.0: Calculate session duration (handle both naive and aware datetimes)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if session.started_at:
        started = session.started_at
        # Handle naive datetimes from old DB records
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        duration_minutes = int((now - started).total_seconds() / 60)
    else:
        duration_minutes = 0

    session_ctx = {
        "subject": session.subject,
        "chapter": session.chapter,
        "questions_attempted": session.questions_attempted,
        "questions_correct": session.questions_correct,
        "total_hints_used": session.total_hints_used,
        # v7.2.0: Include language preference for prompt injection
        "language_pref": session.language_pref or "hinglish",
        "explanations_given": session.explanations_given or [],
        # v8.1.0: Include confusion count for escalation protocol
        "confusion_count": session.confusion_count or 0,
        # v8.1.0: Additional context for system prompt
        "student_name": session.student.name if session.student else "Student",
        "class_level": session.student.class_level if session.student else 8,
        "board_name": session.board_name or "NCERT",
        "state": session.state,
        "topics_covered": session.topics_covered or [],
        "session_duration_minutes": duration_minutes,
        # P0 Bug A: Flag for correction detection
        "student_is_correcting": _is_correction,
        "student_text": student_text,
        # P0 FIX: Flag for emotional distress detection
        "student_emotional": _student_emotional,
        # v10.4.0: Level-aware teaching
        "current_level": session.current_level or 2,
    }

    # v7.3.0: Record student input to conversation history
    if session.conversation_history is None:
        session.conversation_history = []
    session.conversation_history.append({"role": "user", "content": student_text})
    flag_modified(session, "conversation_history")

    # ── v9.0: Use handle_state for session updates ────────
    # Create SessionState adapter from DB session for handle_state
    from app.state.session import SessionState as SS, TutorState as TS
    session_state = SS(
        session_id=str(session.id),
        student_name=session.student.name if session.student else "Student",
        student_pin="",
        current_state=TS(_normalize_state(session.state).value),
        preferred_language=session.language_pref or "hinglish",
        current_concept_id=session.current_concept_id or session.chapter or "ch1_square_and_cube",
        reteach_count=session.current_reteach_count or 0,
        teach_material_index=session.teaching_turn or 0,
        current_question=question_data,
        hints_given=session.current_hint_level or 0,
        score=session.questions_correct or 0,
        total_questions_asked=session.questions_attempted or 0,
    )

    # Get content bank for material lookup
    cb = None
    try:
        cb = get_content_bank()
    except Exception:
        pass

    # Call handle_state to get _llm_instruction
    extras = classify_result.get("extras", {})
    handler_response, handler_state, handler_updates = await handle_state(
        session_state, category, extras, student_text,
        content_bank=cb, llm_call=None,
    )

    # Check if handler wants LLM to generate response
    if handler_response is None and "_llm_instruction" in handler_updates:
        # Apply session updates from handler (except internal keys)
        for key, val in handler_updates.items():
            if key.startswith("_"):
                continue
            field_map = {
                "preferred_language": "language_pref",
                "reteach_count": "current_reteach_count",
                "teach_material_index": "teaching_turn",
                "hints_given": "current_hint_level",
            }
            db_field = field_map.get(key, key)
            if hasattr(session, db_field):
                setattr(session, db_field, val)

        # Update state from handler
        new_state = handler_state.value if hasattr(handler_state, 'value') else str(handler_state)

    # Use build_prompt() from instruction_builder.py (V10 active brain)
    # Same as streaming endpoint — all P0 fixes, language auto-detection, dialect prohibition
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

    # v10.3.1: Hard truncate TTS text to reduce latency (display keeps full text)
    MAX_TTS_CHARS = 150
    if len(cleaned_text) > MAX_TTS_CHARS:
        truncated = cleaned_text[:MAX_TTS_CHARS]
        last_end = max(
            truncated.rfind('. '),
            truncated.rfind('। '),
            truncated.rfind('? '),
            truncated.rfind('! '),
        )
        if last_end > 50:
            cleaned_text = truncated[:last_end + 1]
        logger.info(f"TTS_TRUNCATED (non-stream): {len(didi_text)} → {len(cleaned_text)} chars")

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

    # v7.3.26 Fix: NEXT_QUESTION is transient - after asking, state becomes WAITING_ANSWER
    # Without this, the next turn would re-read the question instead of evaluating the answer
    if new_state == "NEXT_QUESTION" and action.action_type == "pick_next_question":
        new_state = "WAITING_ANSWER"

    session.state = new_state
    await run_in_threadpool(lambda: db.commit())

    total_ms = int((time.perf_counter() - t_start) * 1000)
    logger.info(
        f"Turn {turn_base}: {total_ms}ms total | "
        f"STT={stt_latency}ms LLM={llm_result.latency_ms}ms TTS={tts_latency}ms | "
        f"{state_before}→{new_state} [{category}]"
    )

    # P0 FIX: Format text for readable display (line breaks between sentences)
    display_text = format_for_display(didi_text)
    
    return MessageResponse(
        didi_text=display_text,
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
        debug={
            "classifier": category,
            "verdict": verdict_str,
            "state_before": state_before,
            "state_after": new_state,
            "question_id": session.current_question_id,
        },
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
        pref = session.language_pref or "hinglish"
        nudge = "Could you say that again?" if pref == "english" else "Ek baar phir boliye?"
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

    # DEBUG: RAW INPUT logging (P0 debug)
    logger.info(f"RAW INPUT (stream): [{student_text}]")

    # ── Preprocessing (v8.1.0 P0 fixes) ──
    chapter_name = CHAPTER_NAMES.get(session.chapter or "", session.chapter or "")
    current_skill = ""
    if session.current_question_id:
        q_data = _load_question(db, session.current_question_id)
        current_skill = q_data.get("target_skill", "") if q_data else ""

    preprocess_result = preprocess_student_message(
        text=student_text,
        chapter=session.chapter or "",
        chapter_name=chapter_name,
        subject=session.subject or "math",
        current_skill=current_skill,
        language_pref=session.language_pref or "hinglish",
    )

    # DEBUG: META-ROUTE logging (P0 debug)
    logger.info(f"META-ROUTE (stream): detected={preprocess_result.meta_question_type}, bypass_llm={preprocess_result.bypass_llm}, template=[{preprocess_result.template_response[:50] if preprocess_result.template_response else 'None'}]")

    # Meta-question: bypass LLM entirely
    if preprocess_result.bypass_llm:
        logger.info(f"v8.1.0 (stream): Bypassing LLM for meta-question: {preprocess_result.meta_question_type}")
        # DEBUG: Log response to frontend (P0 debug)
        logger.info(f"RESPONSE TO FRONTEND (stream-meta): text=[{preprocess_result.template_response[:100] if preprocess_result.template_response else 'EMPTY'}], len={len(preprocess_result.template_response) if preprocess_result.template_response else 0}")

        tts = get_tts()
        # v10.5.2: Meta-question TTS — 200 char limit (was 150, too short for explanations)
        meta_tts_text = prepare_for_tts(preprocess_result.template_response, session)
        if len(meta_tts_text) > 200:
            trunc = meta_tts_text[:200]
            last_end = max(trunc.rfind('. '), trunc.rfind('। '), trunc.rfind('? '), trunc.rfind('! '))
            if last_end > 50:
                meta_tts_text = trunc[:last_end + 1]
        tts_result = tts.synthesize(meta_tts_text, get_tts_language(session))
        audio_chunk = base64.b64encode(tts_result.audio_bytes).decode()

        if session.conversation_history is None:
            session.conversation_history = []
        session.conversation_history.append({"role": "user", "content": student_text})
        session.conversation_history.append({"role": "assistant", "content": preprocess_result.template_response})
        flag_modified(session, "conversation_history")
        await run_in_threadpool(lambda: db.commit())

        current_state = session.state  # Capture before generator to avoid DetachedInstanceError

        async def meta_stream():
            # v10.5.2: Text BEFORE audio (same as main response path)
            yield f"data: {json.dumps({'type': 'text', 'content': preprocess_result.template_response})}\n\n"
            yield f"data: {json.dumps({'type': 'audio_chunk', 'index': 0, 'audio': audio_chunk, 'is_last': True})}\n\n"
            yield f"data: {json.dumps({'type': 'transcript', 'content': student_text})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'state': current_state})}\n\n"

        return StreamingResponse(meta_stream(), media_type="text/event-stream")

    # Language switch: update session preference AND commit immediately
    # P0 Bug A fix: Language must persist across requests
    if preprocess_result.language_switched:
        session.language_pref = preprocess_result.new_language
        await run_in_threadpool(lambda: db.commit())  # P0 fix: Commit immediately
        logger.info(f"P0 FIX (stream): Language switched to '{session.language_pref}' and COMMITTED to DB")

    # Confusion: increment counter
    if preprocess_result.confusion_detected:
        session.confusion_count = (session.confusion_count or 0) + 1
        logger.info(f"v8.1.0 (stream): Confusion detected, count now {session.confusion_count}")

    # P0 FIX: Emotional distress detection — flag for LLM to acknowledge emotion first
    _student_emotional = False
    if preprocess_result.emotional_distress:
        _student_emotional = True
        logger.info(f"P0 FIX (stream): Emotional distress detected, flagging for LLM")

    # === LANGUAGE AUTO-DETECTION (P0 fix) ===
    _detected_lang = detect_input_language(student_text)
    _consecutive_english = getattr(session, 'consecutive_english_count', 0) or 0

    # Special case: first student message in GREETING sets language immediately
    if session.state == 'GREETING' and _detected_lang == 'english' and session.language_pref != 'english':
        session.language_pref = 'english'
        session.consecutive_english_count = 1
        await run_in_threadpool(lambda: db.commit())
        logger.info(f"LANGUAGE AUTO-DETECT (stream): first message in GREETING is English, switched immediately")
    else:
        _should_switch, _new_lang, _updated_count = check_language_auto_switch(
            detected_language=_detected_lang,
            current_session_language=session.language_pref or 'hinglish',
            consecutive_english_count=_consecutive_english,
        )
        session.consecutive_english_count = _updated_count
        if _should_switch:
            session.language_pref = _new_lang
            await run_in_threadpool(lambda: db.commit())
            logger.info(f"LANGUAGE AUTO-DETECT (stream): switched to {_new_lang} (consecutive={_updated_count})")
        elif _updated_count != _consecutive_english:
            await run_in_threadpool(lambda: db.commit())  # Persist counter change
    # === END LANGUAGE AUTO-DETECTION ===

    # === LANGUAGE PRE-SCAN (runs on every message) ===
    # Detects language switch requests BEFORE classification.
    # Uses intent patterns, not bare keywords, to avoid false positives.
    # Example false positive: "Why are you speaking in Hindi?" contains "Hindi"
    # but the student wants ENGLISH, not Hindi.
    _text_lower = student_text.lower()

    # English triggers: student wants English
    _english_triggers = [
        "in english", "speak english", "teach english", "english mein",
        "english please", "english me", "talk english", "explain english",
        "respond english", "switch to english", "change to english",
        "can you speak english", "can you teach english",
        "इंग्लिश में", "अंग्रेजी में", "इंग्लिश में बोलो",
        "अंग्रेजी में बोलो", "अंग्रेजी में बात करो",
    ]
    # Also catch: "Why are you speaking in Hindi?" = wants English (complaining about Hindi)
    _complaining_about_hindi = [
        "why hindi", "why in hindi", "why are you speaking hindi",
        "why are you speaking in hindi", "stop speaking hindi",
        "don't speak hindi", "dont speak hindi", "not in hindi",
        "no hindi", "stop hindi", "I said english",
        "हिंदी में क्यों", "हिंदी क्यों",
    ]
    # Hindi triggers: student explicitly WANTS Hindi (intent to switch TO Hindi)
    _hindi_intent_triggers = [
        "speak hindi", "speak in hindi", "talk in hindi",
        "in hindi please", "hindi mein bolo", "hindi me bolo",
        "switch to hindi", "change to hindi", "teach in hindi",
        "hindi mein samjhao", "hindi mein baat karo",
        "हिंदी में बोलो", "हिंदी में समझाओ", "हिंदी में बात करो",
    ]

    _switched = False
    # Check English triggers first
    for trigger in _english_triggers:
        if trigger in _text_lower:
            session.language_pref = "english"
            await run_in_threadpool(lambda: db.commit())
            logger.info(f"LANGUAGE PRE-SCAN (stream): switched to english (trigger: {trigger})")
            _switched = True
            break

    # Check complaints about Hindi (= wants English)
    if not _switched:
        for trigger in _complaining_about_hindi:
            if trigger in _text_lower:
                session.language_pref = "english"
                await run_in_threadpool(lambda: db.commit())
                logger.info(f"LANGUAGE PRE-SCAN (stream): switched to english (complaint: {trigger})")
                _switched = True
                break

    # Check Hindi intent triggers LAST (requires explicit intent)
    if not _switched:
        for trigger in _hindi_intent_triggers:
            if trigger in _text_lower:
                session.language_pref = "hindi"
                await run_in_threadpool(lambda: db.commit())
                logger.info(f"LANGUAGE PRE-SCAN (stream): switched to hindi (trigger: {trigger})")
                _switched = True
                break
    # === END LANGUAGE PRE-SCAN ===

    # === CORRECTION DETECTION (runs on every message) ===
    # Detects when student corrects Didi's math error.
    # Sets a flag so instruction builder acknowledges the correction.
    _correction_triggers = [
        "that's wrong", "thats wrong", "that is wrong",
        "you're wrong", "youre wrong", "you are wrong",
        "wrong answer", "galat", "गलत",
        "that's not right", "not right", "not correct",
        "check again", "check karo", "check kijiye",
        "चेक कीजिए", "चेक करो", "गलत है",
        "nahi", "74 nahi", "that's not",
    ]
    # Pattern: student says "[X] nahi, [Y] hota hai" = correction
    _is_correction = False
    for trigger in _correction_triggers:
        if trigger in _text_lower:
            _is_correction = True
            break
    # Also detect pattern: "X nahi" or "X नहीं" followed by a number
    import re as _re
    if not _is_correction and _re.search(r'\d+\s*(nahi|नहीं|nhi|wrong|galat)', _text_lower):
        _is_correction = True
    if not _is_correction and _re.search(r'(nahi|नहीं|nhi|wrong|galat)\s*.*\d+', _text_lower):
        _is_correction = True

    if _is_correction:
        logger.info(f"CORRECTION DETECTED (stream): student correcting Didi's math")
    # === END CORRECTION DETECTION ===

    # ── Classify ──
    # v7.3.0: Use async LLM classifier (module-level singleton)
    t_classify = time.perf_counter()
    classify_result = await classify(
        student_text,
        current_state=session.state,
        subject=session.subject or "math",
        client=get_openai_client(),
    )
    classifier_ms = int((time.perf_counter() - t_classify) * 1000)
    category = classify_result["category"]
    logger.info(f"CLASSIFIER: text='{student_text[:50]}' → category={category}, extras={classify_result.get('extras', {})}")
    # Handle LANGUAGE_SWITCH preference from classifier (Break 4 fix)
    # P0 Bug A fix: Commit language change immediately
    if category == "LANGUAGE_SWITCH" and classify_result.get("extras", {}).get("preferred_language"):
        session.language_pref = classify_result["extras"]["preferred_language"]
        await run_in_threadpool(lambda: db.commit())  # P0 fix: Persist language change
        logger.info(f"P0 FIX (stream): Classifier set language to '{session.language_pref}' and COMMITTED")

    # v7.3.28 Fix 3: Empathy one turn max (streaming endpoint)
    # If we already gave empathy, force next message to be ACK and go to TEACHING
    if getattr(session, 'empathy_given', False) and category == "COMFORT":
        category = "ACK"
        logger.info(f"v7.3.28: empathy_given=True, overriding COMFORT → ACK")

    # Handle silence without LLM
    if category == "SILENCE":
        pref = session.language_pref or "hinglish"
        nudge = "Are you there? Feel free to ask any question." if pref == "english" else "Aap wahan ho? Koi sawaal hai toh puchiye."
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

    # ── State transition (v8.0 FSM) ──
    question_data = None
    if session.current_question_id:
        question_data = _load_question(db, session.current_question_id)

    # v8.0: Build context for old state machine (backward compat)
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
        "teaching_turn": session.teaching_turn or 0,
        "explanations_given": session.explanations_given or [],
        "language_pref": session.language_pref or "hinglish",
    }

    # v8.0: Get transition from new FSM
    transition_result = get_transition(_normalize_state(session.state), category)
    logger.info(f"v8.0 (stream): {session.state} × {category} → {transition_result.next_state.value}")

    # v8.0: CRITICAL - Store language BEFORE calling handler
    # Bug A fix: Ensure commit happens here too (classifier may have already done it)
    extras = classify_result.get("extras", {})
    if transition_result.special == "store_language" and extras.get("preferred_language"):
        session.language_pref = extras["preferred_language"]
        await run_in_threadpool(lambda: db.commit())  # Bug A fix: Persist immediately
        logger.info(f"v8.0 (stream): Language set to '{session.language_pref}' BEFORE handler and COMMITTED")

    # Use old transition for Action object (backward compat with answer eval)
    new_state, action = transition(session.state, category, ctx)

    # P0 FIX: Save state IMMEDIATELY after transition, not inside generator
    # This ensures state persists even if generator doesn't fully execute
    session.state = new_state
    await run_in_threadpool(lambda: db.commit())
    logger.info(f"P0 FIX (stream): State saved immediately: {session.state}")

    # v8.0: Track empathy state based on new transition
    if transition_result.next_state == TutorState.TEACHING:
        session.empathy_given = False
        logger.info("v8.0: Entering TEACHING, resetting empathy_given=False")
    elif transition_result.special == "empathy_first":
        session.empathy_given = True
        logger.info("v8.0: Empathy given, setting empathy_given=True")

    # v8.0: Update session fields from action
    if action.language_pref:
        session.language_pref = action.language_pref
        logger.info(f"v8.0: Language preference set to '{action.language_pref}'")
    if action.extra.get("reset_teaching_turn"):
        session.teaching_turn = 0
        session.explanations_given = []
    elif action.teaching_turn > 0:
        session.teaching_turn = action.teaching_turn
        await run_in_threadpool(lambda: db.commit())  # P0 FIX: Persist teaching_turn
        logger.info(f"v8.0: Teaching turn set to {action.teaching_turn} and COMMITTED")

    # ── Answer check (if ANSWER) ──
    verdict = None
    verdict_str = None
    eval_ms = 0
    _use_inline_eval = False
    _inline_eval_next_q = None
    _inline_eval_is_session_end = False
    _inline_eval_hint_level = 0
    _inline_eval_correct_display = ""
    if action.action_type == "evaluate_answer" and session.current_question_id:
        # v10.5.1: Inline eval — skip separate eval LLM call, combine into teaching call
        _use_inline_eval = True
        _inline_eval_hint_level = session.current_hint_level
        _inline_eval_correct_display = question_data.get("answer", "") if question_data else ""

        # Pre-load next question for correct path
        asked_ids = [
            t.question_id for t in session.turns
            if t.question_id and t.verdict in ("CORRECT", "INCORRECT")
        ]
        if session.current_question_id and session.current_question_id not in asked_ids:
            asked_ids.append(session.current_question_id)
        _inline_eval_next_q = memory.pick_next_question(
            db, session.student_id,
            session.subject or "math",
            session.chapter or "ch1_square_and_cube",
            asked_ids,
            difficulty_preference=action.extra.get("difficulty"),
            current_level=session.current_level,
        )
        if _inline_eval_next_q:
            logger.info(f"INLINE_EVAL_PRELOAD: next_q={_inline_eval_next_q['id']} for correct path")
        else:
            logger.info("INLINE_EVAL_PRELOAD: no next question available")

    # v7.3.26: Pick next question (if needed) — for non-eval actions
    if not _use_inline_eval:
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
                logger.info(f"PICK_NEXT (stream): current_q={session.current_question_id}, asked_ids={asked_ids}, level={session.current_level}")
                q = memory.pick_next_question(
                    db, session.student_id,
                    session.subject or "math",
                    session.chapter or "ch1_square_and_cube",
                    asked_ids,
                    difficulty_preference=action.extra.get("difficulty"),
                    current_level=session.current_level,
                )
                if q:
                    question_data = q
                    logger.info(f"PICK_NEXT (stream): selected new q={q['id']} (was {session.current_question_id})")
                    session.current_question_id = q["id"]
                    session.current_hint_level = 0
                else:
                    # No more questions → end session
                    new_state = "SESSION_COMPLETE"
                    action = Action("end_session", student_text=student_text)
        elif action.action_type in ("give_hint", "show_solution", "teach_concept", "answer_meta_question"):
            # Load question for hints, solutions, teaching, and meta-questions
            if session.current_question_id:
                question_data = _load_question(db, session.current_question_id)

    # v10.3.1: Persist all session field updates (counters, question_id, hint_level)
    # BEFORE the generator starts. The generator uses fresh_db which would overwrite.
    await run_in_threadpool(lambda: db.commit())

    # ── Build prompt ──
    # v7.3.22 Fix 2: Include language_pref in session_ctx for streaming endpoint
    # v8.1.0: Include confusion_count and full context for escalation protocol
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    if session.started_at:
        started = session.started_at
        # Handle naive datetimes from old DB records
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        duration_minutes = int((now - started).total_seconds() / 60)
    else:
        duration_minutes = 0

    session_ctx = {
        "subject": session.subject,
        "chapter": session.chapter,
        "questions_attempted": session.questions_attempted,
        "questions_correct": session.questions_correct,
        "language_pref": session.language_pref or "hinglish",
        "confusion_count": session.confusion_count or 0,
        # v8.1.0: Additional context for system prompt
        "student_name": session.student.name if session.student else "Student",
        "class_level": session.student.class_level if session.student else 8,
        "board_name": session.board_name or "NCERT",
        "state": session.state,
        "topics_covered": session.topics_covered or [],
        "session_duration_minutes": duration_minutes,
        # P0 Bug A: Flag for correction detection
        "student_is_correcting": _is_correction,
        "student_text": student_text,
        # P0 FIX: Flag for emotional distress detection
        "student_emotional": _student_emotional,
        # v10.4.0: Level-aware teaching
        "current_level": session.current_level or 2,
    }
    prev_response = session.turns[-1].didi_response if session.turns else None

    # v7.3.0: Record student input to conversation history
    if session.conversation_history is None:
        session.conversation_history = []
    session.conversation_history.append({"role": "user", "content": student_text})
    flag_modified(session, "conversation_history")

    # v10.5.1: Use inline eval prompt if answer is being evaluated
    if _use_inline_eval:
        inline_messages, _inline_eval_is_session_end = build_inline_eval_prompt(
            session_ctx, question_data, student_text,
            session.current_hint_level,
            _inline_eval_next_q,
            session.questions_attempted,
        )
        if inline_messages:
            messages = inline_messages
            logger.info(f"INLINE_EVAL: using combined eval+respond prompt (hint_level={session.current_hint_level})")
        else:
            # Fallback if inline eval can't build prompt
            _use_inline_eval = False
            messages = build_prompt(action, session_ctx, question_data, None, prev_response, session.conversation_history)
    else:
        messages = build_prompt(action, session_ctx, question_data, None, prev_response, session.conversation_history)

    # ── Streaming LLM + TTS ──
    llm = get_llm()
    tts = get_tts()

    # === Pre-load session values before generator (prevents DetachedInstanceError) ===
    # The generator runs AFTER FastAPI closes the DB session dependency.
    # Any lazy-loaded SQLAlchemy attributes accessed inside the generator will fail.
    # Pre-load everything we need into local variables.
    _session_id = session.id
    _session_language_pref = session.language_pref
    _session_current_question_id = session.current_question_id
    _session_turns_count = len(session.turns) if session.turns else 0
    _session_conversation_history = list(session.conversation_history) if session.conversation_history else []
    # v10.5.1: Pre-load inline eval data for generator
    _inline_eval_next_q_id = _inline_eval_next_q["id"] if _inline_eval_next_q else None
    _session_questions_attempted = session.questions_attempted or 0
    # === END Pre-load ===

    async def stream_response():
        """SSE: collect LLM response with parallel TTS, stream to frontend."""
        nonlocal new_state, verdict, verdict_str  # v7.5.2 + v10.5.1
        full_text = ""  # TTS-cleaned text (for turn logging)
        display_text_raw = ""  # v10.1 FIX Issue 3: Original LLM text (for display with digits)
        cancelled = False

        # Fix 2: Wrap in try/finally to persist state on cancellation
        llm_ms = 0
        tts_ms = 0
        try:
            t_llm = time.perf_counter()
            tts_lang = get_tts_language(session)
            tts_inst = get_tts()

            # v10.5.2: State-dependent TTS char limits
            # TEACHING needs room to explain, GREETING should be short
            if state_before == "TEACHING":
                MAX_TTS_CHARS = 350
            elif state_before in ("WAITING_ANSWER", "HINT_1", "HINT_2", "FULL_SOLUTION"):
                MAX_TTS_CHARS = 200
            else:
                MAX_TTS_CHARS = 150

            async for sentence in llm.generate_streaming(messages):
                display_text_raw += " " + sentence

            llm_ms = int((time.perf_counter() - t_llm) * 1000)

            display_text_raw = display_text_raw.strip()
            logger.info(f"RAW_LLM_OUTPUT: [{display_text_raw[:200] if display_text_raw else 'EMPTY'}]")

            # v10.5.1: Parse verdict from inline eval LLM output
            if _use_inline_eval:
                _parsed_correct = None
                if display_text_raw.startswith("[CORRECT]"):
                    _parsed_correct = True
                    display_text_raw = display_text_raw[len("[CORRECT]"):].strip()
                elif display_text_raw.startswith("[INCORRECT]"):
                    _parsed_correct = False
                    display_text_raw = display_text_raw[len("[INCORRECT]"):].strip()
                else:
                    # LLM didn't follow prefix instruction — fallback to regex checker
                    fallback_verdict = check_math_answer(
                        student_text, _inline_eval_correct_display,
                        question_data.get("answer_variants", []) if question_data else [],
                    )
                    _parsed_correct = fallback_verdict.correct
                    logger.warning(f"INLINE_EVAL_FALLBACK: no tag found, regex says {'CORRECT' if _parsed_correct else 'INCORRECT'}")

                verdict_str = "CORRECT" if _parsed_correct else "INCORRECT"
                verdict = Verdict(
                    correct=_parsed_correct,
                    verdict=verdict_str,
                    student_parsed=student_text,
                    correct_display=_inline_eval_correct_display,
                    diagnostic="",
                )

                # Route state based on parsed verdict
                new_state, _ = route_after_evaluation(
                    verdict, _inline_eval_hint_level,
                    _session_questions_attempted + 1,
                )
                logger.info(f"INLINE_EVAL_PARSED: verdict={verdict_str}, new_state={new_state}, "
                           f"hint_level={_inline_eval_hint_level}")

            # Enforce on display text (keeps digits for frontend)
            enforce_result = enforce(
                display_text_raw, new_state,
                verdict=verdict_str,
                student_answer=student_text,
                language=tts_lang,
                previous_response=prev_response,
            )
            display_text_final = enforce_result.text
            display_text = format_for_display(display_text_final)
            logger.info(f"AFTER_FORMAT_DISPLAY: [{display_text[:200] if display_text else 'EMPTY'}]")

            # v10.3.1: Send text to frontend FIRST (don't wait for audio)
            yield f"data: {json.dumps({'type': 'text', 'content': display_text})}\n\n"

            # Prepare final TTS text from enforced output
            final_tts_text = prepare_for_tts(display_text_final, session)
            if len(final_tts_text) > MAX_TTS_CHARS:
                trunc = final_tts_text[:MAX_TTS_CHARS]
                last_end = max(
                    trunc.rfind('. '), trunc.rfind('। '),
                    trunc.rfind('? '), trunc.rfind('! '),
                )
                if last_end > 50:
                    final_tts_text = trunc[:last_end + 1]
                logger.info(f"TTS_TRUNCATED: {len(display_text_final)} → {len(final_tts_text)} chars")

            full_text = final_tts_text  # For turn logging
            logger.info(f"TTS_TEXT: [{full_text[:200] if full_text else 'EMPTY'}]")

            # v10.5.2: Always TTS the full enforced response (not first sentence only)
            try:
                t_tts = time.perf_counter()
                tts_result = await tts_inst.synthesize_async(final_tts_text, tts_lang)
                tts_ms = int((time.perf_counter() - t_tts) * 1000)
                logger.info(f"TTS_FULL: {tts_ms}ms, {len(final_tts_text)} chars")
                if tts_result.audio_bytes:
                    audio_chunk = base64.b64encode(tts_result.audio_bytes).decode()
                    yield f"data: {json.dumps({'type': 'audio_chunk', 'index': 0, 'audio': audio_chunk, 'is_last': True})}\n\n"
            except Exception as e:
                logger.error(f"TTS error: {e}")

            # Send metadata
            yield f"data: {json.dumps({'type': 'transcript', 'content': student_text})}\n\n"
            yield f"data: {json.dumps({'type': 'verdict', 'value': verdict_str, 'diagnostic': verdict.diagnostic if verdict else None})}\n\n"
            total_ms = classifier_ms + eval_ms + llm_ms + tts_ms
            yield f"data: {json.dumps({'type': 'debug', 'classifier': category, 'verdict': verdict_str, 'state_before': state_before, 'state_after': new_state, 'question_id': _session_current_question_id, 'level': session.current_level, 'classifier_ms': classifier_ms, 'eval_ms': eval_ms, 'llm_ms': llm_ms, 'tts_ms': tts_ms, 'total_ms': total_ms})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'state': new_state})}\n\n"

        except asyncio.CancelledError:
            # Fix 2: Handle cancellation gracefully - persist partial state
            cancelled = True
            logger.info(f"Stream cancelled, persisting partial state")

        finally:
            # Fix: Use fresh DB session to avoid DetachedInstanceError
            # The original `db` session from FastAPI dependency may be closed by now.
            full_text = full_text.strip()

            # v7.3.26 Fix: NEXT_QUESTION is transient - after asking, state becomes WAITING_ANSWER
            if new_state == "NEXT_QUESTION" and action.action_type == "pick_next_question":
                new_state = "WAITING_ANSWER"

            # Get fresh DB session for final writes
            fresh_db = SessionLocal()
            try:
                fresh_session = fresh_db.query(Session).filter(Session.id == _session_id).first()
                if fresh_session:
                    # Update conversation history
                    if full_text:
                        if fresh_session.conversation_history is None:
                            fresh_session.conversation_history = []
                        fresh_session.conversation_history.append({"role": "assistant", "content": full_text})
                        flag_modified(fresh_session, "conversation_history")

                    # Create separate turns for student and didi
                    turn_base = _session_turns_count + 1
                    student_turn = SessionTurn(
                        session_id=_session_id,
                        turn_number=turn_base,
                        speaker="student",
                        transcript=student_text,
                        input_category=category,
                        state_before=state_before,
                        state_after=new_state,
                        question_id=_session_current_question_id,
                        verdict=verdict_str,
                        stt_latency_ms=stt_latency,
                    )
                    fresh_db.add(student_turn)

                    if full_text:
                        didi_turn = SessionTurn(
                            session_id=_session_id,
                            turn_number=turn_base + 1,
                            speaker="didi",
                            state_before=state_before,
                            state_after=new_state,
                            question_id=_session_current_question_id,
                            didi_response=full_text,
                        )
                        fresh_db.add(didi_turn)

                    # v10.5.1: Update session counters for inline eval
                    # These were deferred because verdict wasn't known until LLM output was parsed
                    if _use_inline_eval and verdict is not None:
                        fresh_session.questions_attempted = (fresh_session.questions_attempted or 0) + 1
                        if verdict.correct:
                            fresh_session.questions_correct = (fresh_session.questions_correct or 0) + 1
                            fresh_session.current_hint_level = 0
                            fresh_session.confusion_count = 0
                            fresh_session.consecutive_correct = (fresh_session.consecutive_correct or 0) + 1
                            fresh_session.consecutive_wrong = 0
                            if fresh_session.consecutive_correct >= 3 and (fresh_session.current_level or 2) < 5:
                                fresh_session.current_level = (fresh_session.current_level or 2) + 1
                                fresh_session.consecutive_correct = 0
                                logger.info(f"LEVEL_UP (inline_eval): student advanced to Level {fresh_session.current_level}")
                            # Update question to next question
                            if _inline_eval_next_q_id:
                                fresh_session.current_question_id = _inline_eval_next_q_id
                                fresh_session.current_hint_level = 0
                            elif _inline_eval_is_session_end:
                                new_state = "SESSION_COMPLETE"
                        else:
                            fresh_session.current_hint_level = (fresh_session.current_hint_level or 0) + 1
                            fresh_session.total_hints_used = (fresh_session.total_hints_used or 0) + 1
                            fresh_session.consecutive_wrong = (fresh_session.consecutive_wrong or 0) + 1
                            fresh_session.consecutive_correct = 0
                            if fresh_session.consecutive_wrong >= 2 and (fresh_session.current_level or 2) > 1:
                                fresh_session.current_level = (fresh_session.current_level or 2) - 1
                                fresh_session.consecutive_wrong = 0
                                logger.info(f"LEVEL_DOWN (inline_eval): student dropped to Level {fresh_session.current_level}")

                    fresh_session.state = new_state
                    fresh_db.commit()
            except Exception as e:
                logger.error(f"Error saving session in generator finally: {e}")
                fresh_db.rollback()
            finally:
                fresh_db.close()

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

    # P0 FIX: Language-aware summary
    pref = session.language_pref or "hinglish"
    if pref == "english":
        summary = (
            f"Today you attempted {session.questions_attempted} questions, "
            f"{session.questions_correct} were correct. "
        )
        if session.questions_attempted > 0:
            acc = session.questions_correct / session.questions_attempted * 100
            summary += f"Accuracy: {acc:.0f}%. "
        summary += "See you tomorrow!"
    else:
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
    # DEBUG: Log response to frontend (P0 debug)
    logger.info(f"RESPONSE TO FRONTEND (quick): text=[{text[:100] if text else 'EMPTY'}], len={len(text) if text else 0}")

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
