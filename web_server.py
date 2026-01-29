"""
IDNA EdTech - Web API Backend (Production-Ready MVP)
FastAPI server for voice-first math tutor

Architecture: SINGLE ENTRY POINT
- This is the ONLY server file needed
- No gRPC, no orchestrator, no webapp.py
- Railway Procfile: web: uvicorn web_server:app --host 0.0.0.0 --port $PORT

Features:
- SQLite persistence (sessions survive restart)
- Explicit FSM (state machine with guards)
- TutorIntent layer for natural teaching behavior
- Enhanced evaluator with spoken variant support
- Timeouts on OpenAI calls
- Railway-ready ($PORT support)

Updated: January 28, 2026 - Added TutorIntent layer
"""

import os
import random
import base64
import sqlite3
import httpx
import json
import uuid
import tempfile
import asyncio
from enum import Enum
from datetime import datetime, timedelta
from contextlib import contextmanager, asynccontextmanager
from functools import lru_cache
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
from google.cloud import texttospeech

from questions import ALL_CHAPTERS, CHAPTER_NAMES
from evaluator import check_answer
from tutor_intent import (
    generate_tutor_response,
    generate_gpt_response,
    generate_step_explanation,
    wrap_in_ssml,
    is_help_request,
    TutorIntent,
    TutorVoice
)


# ============================================================
# PERFORMANCE: Cached chapter list (static data)
# ============================================================
@lru_cache(maxsize=1)
def get_chapters_cached():
    """Cache the chapters list - it's static data."""
    return [
        {"id": ch, "name": CHAPTER_NAMES[ch]}
        for ch in ALL_CHAPTERS.keys()
    ]

load_dotenv()

# ============================================================
# APP INITIALIZATION
# ============================================================

print("### IDNA EdTech MVP - Clean Architecture ###")
print("### TutorIntent Layer: ENABLED ###")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    init_database()
    print("[STARTUP] IDNA EdTech MVP ready")
    print("[STARTUP] TutorIntent layer: ENABLED")
    print(f"[STARTUP] Database: {DB_PATH}")
    print(f"[STARTUP] Static files: {'static/' if os.path.exists('static') else 'NOT FOUND'}")

    yield

    # Shutdown - cleanup temp credentials file
    global _tts_creds_file
    if _tts_creds_file and os.path.exists(_tts_creds_file.name):
        try:
            os.unlink(_tts_creds_file.name)
            print("[SHUTDOWN] Cleaned up temp credentials file")
        except Exception as e:
            print(f"[SHUTDOWN] Failed to clean up temp file: {e}")


app = FastAPI(
    title="IDNA Math Tutor API",
    description="Voice-first AI math tutor for K-10 students",
    version="1.1.0",  # Updated for TutorIntent
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
if os.path.exists("web"):
    app.mount("/web", StaticFiles(directory="web"), name="web")

# OpenAI client with timeout
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=30.0,
    max_retries=2
)

# Google Cloud TTS - handle credentials from env var JSON
_tts_client = None
_tts_creds_file = None

def get_google_tts_client():
    """Get Google TTS client, creating credentials file from env var if needed"""
    global _tts_client, _tts_creds_file

    if _tts_client:
        return _tts_client

    creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")

    if creds_json:
        try:
            # Validate it's valid JSON
            json.loads(creds_json)

            # Write to temp file
            _tts_creds_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.json',
                delete=False
            )
            _tts_creds_file.write(creds_json)
            _tts_creds_file.close()

            # Set the env var that Google client looks for
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _tts_creds_file.name
            print(f"### Google Cloud TTS: Credentials loaded from env var ###")
        except json.JSONDecodeError as e:
            print(f"### Google Cloud TTS: Invalid JSON in credentials: {e} ###")
            return None
        except Exception as e:
            print(f"### Google Cloud TTS: Error setting up credentials: {e} ###")
            return None

    try:
        _tts_client = texttospeech.TextToSpeechClient()
        print("### Google Cloud TTS: ENABLED ###")
        return _tts_client
    except Exception as e:
        print(f"### Google Cloud TTS: DISABLED ({e}) ###")
        return None


def google_tts(
    text: str,
    language_code: str = "en-US",
    voice_name: str = "en-US-Journey-F",
    ssml: Optional[str] = None
) -> bytes:
    """Generate warm, natural speech using Google Cloud TTS

    Args:
        text: Plain text to speak (used if ssml is None)
        language_code: Language code (default: en-US for clear American English)
        voice_name: Voice to use (default: en-US-Journey-F, most natural)
        ssml: Optional SSML markup for warmer, more natural speech

    Voice Settings (optimized for warmth, reduced nasality):
    - Speaking rate: 0.92 (slightly slower for clarity)
    - Pitch: -1.0 (slightly lower reduces nasality)
    - Effects profile: small-bluetooth-speaker (optimized for mobile)

    Best voices for natural, non-nasal sound:
    - en-US-Journey-F: Female - MOST NATURAL, like a real person
    - en-US-Journey-D: Male - very natural
    - en-US-Neural2-F: Female - natural, clear (fallback)
    """
    tts_client = get_google_tts_client()
    if tts_client is None:
        raise Exception("Google Cloud TTS not configured")

    # Use SSML if provided, otherwise use plain text
    if ssml:
        synthesis_input = texttospeech.SynthesisInput(ssml=ssml)
    else:
        synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        name=voice_name,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=0.92,  # Slightly slower for clarity and warmth
        pitch=-1.0,  # Slightly lower pitch reduces nasality
        volume_gain_db=3.0,  # Good volume for mobile
        effects_profile_id=["small-bluetooth-speaker-class-device"],  # Optimized for mobile
    )

    try:
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        return response.audio_content
    except Exception as e:
        # Fallback to Neural2 if Journey not available
        print(f"Journey voice failed, trying Neural2: {e}")
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-F",
        )
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        return response.audio_content


# ============================================================
# EXPLICIT FINITE STATE MACHINE (FSM)
# ============================================================

class SessionState(str, Enum):
    """Explicit session states - no ambiguity"""
    IDLE = "idle"
    CHAPTER_SELECTED = "chapter_selected"
    WAITING_ANSWER = "waiting_answer"
    SHOWING_HINT = "showing_hint"
    SHOWING_ANSWER = "showing_answer"
    COMPLETED = "completed"


VALID_TRANSITIONS = {
    SessionState.IDLE: [SessionState.CHAPTER_SELECTED, SessionState.COMPLETED],
    SessionState.CHAPTER_SELECTED: [SessionState.WAITING_ANSWER, SessionState.COMPLETED],
    SessionState.WAITING_ANSWER: [SessionState.WAITING_ANSWER, SessionState.SHOWING_HINT, SessionState.SHOWING_ANSWER, SessionState.COMPLETED],
    SessionState.SHOWING_HINT: [SessionState.WAITING_ANSWER, SessionState.SHOWING_ANSWER, SessionState.COMPLETED],
    SessionState.SHOWING_ANSWER: [SessionState.WAITING_ANSWER, SessionState.COMPLETED],
    SessionState.COMPLETED: [],
}


def can_transition(current: SessionState, target: SessionState) -> bool:
    return target in VALID_TRANSITIONS.get(current, [])


# ============================================================
# DATABASE SETUP (SQLite)
# ============================================================

DB_PATH = os.getenv("DATABASE_PATH", "idna.db")


def init_database():
    """Initialize database tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            student_id INTEGER DEFAULT 1,
            state TEXT NOT NULL,
            chapter TEXT,
            current_question_id TEXT,
            score INTEGER DEFAULT 0,
            total INTEGER DEFAULT 0,
            attempt_count INTEGER DEFAULT 0,
            questions_asked TEXT DEFAULT '[]',
            started_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            duration_seconds INTEGER DEFAULT 0,
            correct_answers INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER DEFAULT 10,
            grade INTEGER DEFAULT 5,
            created_at TEXT NOT NULL
        )
    """)
    
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO students (name, age, grade, created_at) VALUES (?, ?, ?, ?)",
            ("Student", 10, 5, datetime.now().isoformat())
        )
    
    conn.commit()
    conn.close()
    print(f"[DB] Initialized: {DB_PATH}")


@contextmanager
def get_db():
    """Database connection context manager"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ============================================================
# SESSION MANAGEMENT
# ============================================================

def create_session(session_id: str) -> dict:
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO sessions (id, state, started_at, updated_at, questions_asked)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, SessionState.IDLE.value, now, now, '[]'))
    return get_session(session_id)


def get_session(session_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
    return dict(row) if row else None


def update_session(session_id: str, **kwargs) -> bool:
    if not kwargs:
        return False

    kwargs['updated_at'] = datetime.now().isoformat()

    if 'questions_asked' in kwargs and isinstance(kwargs['questions_asked'], list):
        kwargs['questions_asked'] = json.dumps(kwargs['questions_asked'])

    set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [session_id]

    with get_db() as conn:
        conn.execute(f"UPDATE sessions SET {set_clause} WHERE id = ?", values)
    return True


def transition_state(session_id: str, new_state: SessionState) -> bool:
    session = get_session(session_id)
    if not session:
        return False

    current = SessionState(session['state'])
    if not can_transition(current, new_state):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state transition: {current.value} -> {new_state.value}"
        )

    update_session(session_id, state=new_state.value)
    return True


def delete_session(session_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


# ============================================================
# PERFORMANCE: Async wrappers for database operations
# Runs sync SQLite in thread pool to avoid blocking event loop
# ============================================================

async def async_create_session(session_id: str) -> dict:
    """Async wrapper for create_session."""
    return await asyncio.to_thread(create_session, session_id)

async def async_get_session(session_id: str) -> Optional[dict]:
    """Async wrapper for get_session."""
    return await asyncio.to_thread(get_session, session_id)

async def async_update_session(session_id: str, **kwargs) -> bool:
    """Async wrapper for update_session."""
    return await asyncio.to_thread(update_session, session_id, **kwargs)


# ============================================================
# MESSAGE TEMPLATES (Legacy - kept for backward compatibility)
# ============================================================

WELCOME_MESSAGES = [
    "Welcome! Ready to practice math? Let's go! 🎯",
    "Hi there! Let's make math fun today! 📚",
    "Hello! Time to become a math champion! 🏆",
]

PRAISE_MESSAGES = [
    "Excellent! That's correct! ✅",
    "Great job! You got it! 🌟",
    "Perfect! Well done! 👏",
    "Awesome! Keep it up! 💪",
    "Brilliant! You're doing great! ⭐",
]

ENCOURAGEMENT_MESSAGES = [
    "Not quite. Try again! You can do it! 💪",
    "Almost there! Give it another shot! 🎯",
    "Keep trying! You're learning! 📚",
]

HINT_MESSAGES = [
    "Here's a hint to help you: ",
    "Let me give you a clue: ",
    "Think about this: ",
]

CLOSING_MESSAGES = [
    "Great session! You answered {score} out of {total} correctly. Keep practicing! 🎓",
    "Well done! Score: {score}/{total}. See you next time! 👋",
    "Good effort! {score}/{total} correct. Practice makes perfect! 💪",
]


def get_random_message(messages: list, **kwargs) -> str:
    msg = random.choice(messages)
    return msg.format(**kwargs) if kwargs else msg


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class ChapterRequest(BaseModel):
    session_id: str
    chapter: str = ""

class AnswerRequest(BaseModel):
    session_id: str
    answer: str

class TextToSpeechRequest(BaseModel):
    text: str
    voice: str = "nova"
    ssml: Optional[str] = None  # Optional SSML for warmer voice


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_question_by_id(chapter: str, question_id: str) -> Optional[dict]:
    questions = ALL_CHAPTERS.get(chapter, [])
    for q in questions:
        if q["id"] == question_id:
            return q
    return None


def get_student_dashboard_data(student_id: int, language: str = "english"):
    """Get real dashboard data from database"""
    try:
        with get_db() as conn:
            student_row = conn.execute(
                "SELECT * FROM students WHERE id = ?", (student_id,)
            ).fetchone()
            
            if not student_row:
                return None
            
            student = {
                "id": student_row['id'],
                "name": student_row['name'],
                "age": student_row['age'],
                "grade": student_row['grade'],
                "current_subject": "math",
                "preferred_language": language
            }
            
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            
            stats = conn.execute("""
                SELECT 
                    COALESCE(SUM(duration_seconds), 0) as total_time,
                    COALESCE(SUM(correct_answers), 0) as correct,
                    COALESCE(SUM(total), 0) as total_questions,
                    COUNT(*) as session_count
                FROM sessions 
                WHERE student_id = ? AND started_at > ? AND state = ?
            """, (student_id, seven_days_ago, SessionState.COMPLETED.value)).fetchone()
            
            total_time = stats['total_time'] or 0
            correct = stats['correct'] or 0
            total_questions = stats['total_questions'] or 1
            session_count = stats['session_count'] or 0
            
            if session_count == 0:
                any_sessions = conn.execute(
                    "SELECT COUNT(*) as cnt FROM sessions WHERE student_id = ?",
                    (student_id,)
                ).fetchone()
                if any_sessions['cnt'] == 0:
                    return None
            
            accuracy = round((correct / total_questions) * 100, 1) if total_questions > 0 else 0
            
            daily_rows = conn.execute("""
                SELECT DATE(started_at) as day, COUNT(*) as sessions, 
                       COALESCE(SUM(duration_seconds), 0) as duration
                FROM sessions
                WHERE student_id = ? AND started_at > ?
                GROUP BY DATE(started_at)
                ORDER BY day
            """, (student_id, seven_days_ago)).fetchall()
            
            all_days = []
            for i in range(6, -1, -1):
                day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                found = next((dict(r) for r in daily_rows if r['day'] == day), None)
                all_days.append({
                    "date": day,
                    "sessions": found['sessions'] if found else 0,
                    "duration": found['duration'] if found else 0
                })
            
            streak = 0
            for day_data in reversed(all_days):
                if day_data['sessions'] > 0:
                    streak += 1
                else:
                    break
            
            voice_message = generate_voice_message(
                student['name'], total_time // 60, accuracy, language
            )
            
            return {
                "student": student,
                "dashboard": {
                    "total_study_time_minutes": total_time // 60,
                    "average_accuracy": accuracy,
                    "sessions_completed": session_count,
                    "streak_days": streak,
                    "subjects_time": [{"subject": "math", "time": total_time}],
                    "topics_mastered": [],
                    "topics_needing_attention": [],
                    "recent_achievements": [],
                    "daily_activity": all_days
                },
                "voice_message": voice_message
            }
            
    except Exception as e:
        print(f"Dashboard error: {e}")
        return None


def generate_voice_message(name: str, study_minutes: int, accuracy: float, language: str = "english") -> str:
    if language == "hindi":
        if accuracy >= 70:
            return f"नमस्ते! {name} बहुत अच्छा कर रहा है! इस हफ्ते उन्होंने {study_minutes} मिनट पढ़ाई की और {accuracy}% सही जवाब दिए। आपको गर्व होना चाहिए!"
        elif accuracy >= 50:
            return f"नमस्ते! {name} अच्छी प्रगति कर रहा है। {study_minutes} मिनट पढ़ाई की और {accuracy}% accuracy। थोड़ी और मेहनत से वो और बेहतर करेंगे!"
        else:
            return f"नमस्ते! {name} मेहनत कर रहा है। {study_minutes} मिनट पढ़ाई की। साथ मिलकर हम उनका आत्मविश्वास बढ़ाएंगे।"
    else:
        if accuracy >= 70:
            return f"Hello! {name} is doing wonderfully! This week, they studied for {study_minutes} minutes with {accuracy}% accuracy. You should be proud!"
        elif accuracy >= 50:
            return f"Hello! {name} is making progress. They studied {study_minutes} minutes with {accuracy}% accuracy. Keep encouraging them!"
        else:
            return f"Hello! {name} is working hard. They practiced for {study_minutes} minutes. Every step forward is progress!"


# ============================================================
# HEALTH CHECK ENDPOINTS (Railway requires /healthz)
# ============================================================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if os.path.exists(DB_PATH) else "initializing",
        "tutor_intent": "enabled",
        "tts_provider": "google" if get_google_tts_client() else "openai"
    }


@app.get("/healthz")
async def healthz():
    """Railway health check endpoint"""
    return {"status": "ok"}


# ============================================================
# PAGE ROUTES (Serve static HTML)
# ============================================================

@app.get("/")
async def root():
    """Home page - serve static/index.html"""
    return FileResponse("static/index.html")


@app.get("/student")
async def student_page():
    """Student learning page - practice screen"""
    return FileResponse("web/index.html")


@app.get("/parent")
async def parent_page():
    """Parent dashboard page"""
    if os.path.exists("static/parent.html"):
        return FileResponse("static/parent.html")
    # Fallback to homepage if parent.html doesn't exist yet
    return FileResponse("static/index.html")


# ============================================================
# SESSION API ENDPOINTS
# ============================================================

@app.get("/api/chapters")
async def get_chapters():
    """Get list of available chapters (cached for performance)"""
    return {"chapters": get_chapters_cached()}


@app.post("/api/session/start")
async def start_session():
    """Start a new tutoring session"""
    session_id = str(uuid.uuid4())

    # Run DB operation and GPT call concurrently for better performance
    await async_create_session(session_id)

    # Use cached welcome responses (no GPT call needed)
    welcome = generate_gpt_response(TutorIntent.SESSION_START)
    welcome_ssml = wrap_in_ssml(welcome)

    return {
        "session_id": session_id,
        "message": welcome,
        "ssml": welcome_ssml,
        "chapters": list(ALL_CHAPTERS.keys()),
        "state": SessionState.IDLE.value
    }


@app.post("/api/session/chapter")
async def select_chapter(request: ChapterRequest):
    """Select a chapter for practice"""
    session = await async_get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if request.chapter not in ALL_CHAPTERS:
        raise HTTPException(status_code=400, detail="Invalid chapter")

    await async_update_session(
        request.session_id,
        chapter=request.chapter,
        state=SessionState.CHAPTER_SELECTED.value,
        questions_asked=[]
    )

    return {
        "message": f"Great! Let's practice {CHAPTER_NAMES[request.chapter]}!",
        "chapter": request.chapter,
        "state": SessionState.CHAPTER_SELECTED.value
    }


@app.post("/api/session/question")
async def get_next_question(request: ChapterRequest):
    """Get next question for the session with natural TutorIntent introduction"""
    session = await async_get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    chapter = session['chapter']
    if not chapter:
        raise HTTPException(status_code=400, detail="No chapter selected")

    questions = ALL_CHAPTERS.get(chapter, [])
    if not questions:
        raise HTTPException(status_code=400, detail="No questions available")

    asked = json.loads(session['questions_asked'] or '[]')
    available = [q for q in questions if q['id'] not in asked]

    if not available:
        # Use cached session end response (no GPT call)
        closing = generate_gpt_response(TutorIntent.SESSION_END)

        return {
            "completed": True,
            "message": closing,
            "score": session['score'],
            "total": session['total']
        }

    question = random.choice(available)
    asked.append(question['id'])
    question_number = (session['total'] or 0) + 1

    # Run DB update and GPT call concurrently
    update_task = async_update_session(
        request.session_id,
        current_question_id=question['id'],
        questions_asked=asked,
        total=question_number,
        attempt_count=0,
        state=SessionState.WAITING_ANSWER.value
    )

    # Generate intro (may use cache for common patterns)
    intro = generate_gpt_response(
        intent=TutorIntent.ASK_FRESH,
        question=question['text']
    )

    # Await the DB update
    await update_task

    intro_ssml = wrap_in_ssml(intro)

    return {
        "question_id": question['id'],
        "question_text": question['text'],
        "question_number": question_number,
        "intro": intro,
        "intro_ssml": intro_ssml,
        "type": question.get('type', 'text'),
        "options": question.get('options'),
        "state": SessionState.WAITING_ANSWER.value
    }


@app.post("/api/session/answer")
async def submit_answer(request: AnswerRequest):
    """
    Submit answer for current question.

    Uses TutorIntent layer for natural, human-like responses.

    FSM Transitions → TutorIntent Mapping:
    - Correct answer → CONFIRM_CORRECT + MOVE_ON
    - Wrong attempt 1 → GUIDE_THINKING (Socratic hint)
    - Wrong attempt 2 → NUDGE_CORRECTION (direct hint)
    - Wrong attempt 3 → EXPLAIN_ONCE (show solution) + MOVE_ON
    """
    session = await async_get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    current_state = SessionState(session['state'])
    if current_state not in [SessionState.WAITING_ANSWER, SessionState.SHOWING_HINT]:
        raise HTTPException(status_code=400, detail=f"Cannot submit answer in state: {current_state.value}")

    question = get_question_by_id(session['chapter'], session['current_question_id'])
    if not question:
        raise HTTPException(status_code=400, detail="No active question")

    # Check if student is asking for help (not submitting an answer)
    if is_help_request(request.answer):
        # Generate step-by-step explanation
        help_result = generate_step_explanation(
            question=question.get('text', ''),
            solution=question.get('solution', f"The answer is {question['answer']}"),
            correct_answer=question['answer'],
        )

        return {
            "correct": False,
            "is_help": True,
            "message": help_result["response"],
            "ssml": help_result.get("ssml"),
            "intent": help_result["intent"],
            "score": session['score'],
            "total": session['total'],
            "attempt_count": session['attempt_count'] or 0,  # Don't increment for help
            "move_to_next": False,
            "state": current_state.value
        }

    # Use enhanced evaluator (handles spoken variants like "2 by 3" → "2/3")
    is_correct = check_answer(question['answer'], request.answer)
    attempt_count = (session['attempt_count'] or 0) + 1

    # Generate natural tutor response using TutorIntent layer
    tutor_result = generate_tutor_response(
        is_correct=is_correct,
        attempt_number=attempt_count,
        question=question.get('text', ''),
        hint_1=question.get('hint', 'Think about the concept carefully.'),
        hint_2=question.get('hint_2', question.get('hint', 'Think step by step.')),
        solution=question.get('solution', f"The answer is {question['answer']}."),
        correct_answer=question['answer'],
        student_answer=request.answer,  # Pass what student actually said
    )

    if is_correct:
        new_score = (session['score'] or 0) + 1
        new_correct = (session['correct_answers'] or 0) + 1

        await async_update_session(
            request.session_id,
            score=new_score,
            correct_answers=new_correct,
            attempt_count=attempt_count,
            state=SessionState.SHOWING_ANSWER.value
        )

        return {
            "correct": True,
            "message": tutor_result["response"],
            "ssml": tutor_result.get("ssml"),
            "intent": tutor_result["intent"],
            "score": new_score,
            "total": session['total'],
            "attempt_count": attempt_count,
            "move_to_next": True,
            "state": SessionState.SHOWING_ANSWER.value
        }
    else:
        # Wrong answer - use TutorIntent scaffolding
        if tutor_result["move_to_next"]:
            # Attempt 3: Show solution, move on
            await async_update_session(
                request.session_id,
                attempt_count=attempt_count,
                state=SessionState.SHOWING_ANSWER.value
            )

            return {
                "correct": False,
                "show_answer": True,
                "answer": question["answer"],
                "solution": question.get("solution", f"The answer is {question['answer']}"),
                "message": tutor_result["response"],
                "ssml": tutor_result.get("ssml"),
                "intent": tutor_result["intent"],
                "score": session['score'],
                "total": session['total'],
                "attempt_count": attempt_count,
                "move_to_next": True,
                "state": SessionState.SHOWING_ANSWER.value
            }
        else:
            # Attempt 1 or 2: Show hint
            await async_update_session(
                request.session_id,
                attempt_count=attempt_count,
                state=SessionState.SHOWING_HINT.value
            )

            return {
                "correct": False,
                "message": tutor_result["response"],
                "ssml": tutor_result.get("ssml"),
                "hint": tutor_result.get("response"),  # For steps area
                "intent": tutor_result["intent"],
                "hint_level": attempt_count,
                "attempts_left": 3 - attempt_count,
                "score": session['score'],
                "total": session['total'],
                "attempt_count": attempt_count,
                "move_to_next": False,
                "state": SessionState.SHOWING_HINT.value
            }


@app.post("/api/session/end")
async def end_session(request: ChapterRequest):
    """End the session and get summary"""
    session = await async_get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    score = session['score'] or 0
    total = session['total'] or 0

    started_at = datetime.fromisoformat(session['started_at'])
    duration = int((datetime.now() - started_at).total_seconds())

    await async_update_session(
        request.session_id,
        state=SessionState.COMPLETED.value,
        duration_seconds=duration
    )
    
    # Use GPT for warm, encouraging closing
    closing = generate_gpt_response(TutorIntent.SESSION_END)
    full_message = f"{closing} You got {score} out of {total} correct!"
    closing_ssml = wrap_in_ssml(full_message)

    return {
        "message": full_message,
        "ssml": closing_ssml,
        "score": score,
        "total": total,
        "accuracy": round((score/total)*100, 1) if total > 0 else 0,
        "duration_seconds": duration,
        "state": SessionState.COMPLETED.value
    }


# ============================================================
# PARENT DASHBOARD API
# ============================================================

@app.get("/api/dashboard/{student_id}")
async def get_dashboard(student_id: int, lang: str = "english"):
    """Get parent dashboard data"""
    if lang not in ["english", "hindi"]:
        lang = "english"
    
    data = get_student_dashboard_data(student_id, lang)
    
    if data is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": "No data available",
                "message": "Student has not started learning yet.",
                "message_hindi": "अभी तक कोई डेटा नहीं है।"
            }
        )
    
    return data


@app.post("/api/dashboard/{student_id}/voice-report")
async def generate_voice_report(student_id: int, lang: str = "english"):
    """Generate voice report with TTS"""
    if lang not in ["english", "hindi"]:
        lang = "english"
    
    data = get_student_dashboard_data(student_id, lang)
    
    if data is None:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "No data available"}
        )
    
    voice_text = data["voice_message"]

    try:
        # Use Google Cloud TTS (clearer, louder voice)
        if get_google_tts_client():
            audio_content = google_tts(voice_text)
            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        else:
            # Fallback to OpenAI TTS
            response = client.audio.speech.create(
                model="tts-1",
                voice="nova",
                speed=0.85,
                input=voice_text
            )
            audio_base64 = base64.b64encode(response.content).decode('utf-8')

        return {
            "success": True,
            "audio": audio_base64,
            "text": voice_text,
            "language": lang
        }

    except Exception as e:
        print(f"TTS Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "text": voice_text
        }


# ============================================================
# VOICE ENDPOINTS
# ============================================================

@app.post("/api/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """Convert speech to text using Whisper"""
    tmp_path = None
    try:
        # Read audio content
        content = await audio.read()

        # Write to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Run Whisper transcription in thread pool (sync API)
        def transcribe():
            with open(tmp_path, "rb") as f:
                return client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="en"
                )

        transcript = await asyncio.to_thread(transcribe)

        return {"text": transcript.text}

    except Exception as e:
        print(f"STT Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Always clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


@app.post("/api/text-to-speech")
async def text_to_speech(request: TextToSpeechRequest):
    """Convert text to speech using Google Cloud TTS (clearer voice)

    Supports SSML for warmer, more natural voice with pauses and emphasis.
    If ssml is provided and Google TTS is available, uses SSML.
    Falls back to plain text for OpenAI TTS.
    """
    try:
        # Use Google Cloud TTS (clearer, louder voice, supports SSML)
        if get_google_tts_client():
            audio_content = google_tts(
                text=request.text,
                ssml=request.ssml  # Pass SSML if provided
            )
            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        else:
            # Fallback to OpenAI TTS (doesn't support SSML, use plain text)
            response = client.audio.speech.create(
                model="tts-1",
                voice=request.voice,
                speed=0.85,
                input=request.text
            )
            audio_base64 = base64.b64encode(response.content).decode('utf-8')

        return {"audio": audio_base64, "format": "mp3"}

    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# DEBUG ENDPOINT (remove in production)
# ============================================================

@app.get("/api/debug/sessions")
async def debug_sessions():
    """Debug: List all sessions"""
    with get_db() as conn:
        rows = conn.execute("SELECT id, state, score, total, started_at FROM sessions LIMIT 20").fetchall()
    return {"sessions": [dict(r) for r in rows]}




# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting IDNA EdTech server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
