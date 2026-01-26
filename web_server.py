"""
IDNA EdTech - Web API Backend (Production-Ready MVP)
FastAPI server for voice-first math tutor

Features:
- SQLite persistence (sessions survive restart)
- Explicit FSM (state machine with guards)
- Timeouts on OpenAI calls
- Deterministic messages (no GPT in core flow)
- Railway-ready ($PORT support)
"""

import os
import random
import base64
import sqlite3
import httpx
from enum import Enum
from datetime import datetime, timedelta
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI

from questions import ALL_CHAPTERS, CHAPTER_NAMES
from evaluator import check_answer

load_dotenv()

# OpenAI client with timeout
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=30.0,  # 30 second timeout
    max_retries=2
)

app = FastAPI(title="IDNA Math Tutor API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
if os.path.exists("web"):
    app.mount("/web", StaticFiles(directory="web"), name="web")


# ============================================================
# EXPLICIT FINITE STATE MACHINE (FSM)
# ============================================================

class SessionState(str, Enum):
    """Explicit session states - no ambiguity"""
    IDLE = "idle"                    # Session created, no chapter selected
    CHAPTER_SELECTED = "chapter_selected"  # Chapter chosen, ready for questions
    WAITING_ANSWER = "waiting_answer"      # Question asked, waiting for answer
    SHOWING_HINT = "showing_hint"          # Hint shown, waiting for retry
    SHOWING_ANSWER = "showing_answer"      # Answer revealed, ready for next
    COMPLETED = "completed"                # Session ended


# Valid state transitions
VALID_TRANSITIONS = {
    SessionState.IDLE: [SessionState.CHAPTER_SELECTED, SessionState.COMPLETED],
    SessionState.CHAPTER_SELECTED: [SessionState.WAITING_ANSWER, SessionState.COMPLETED],
    SessionState.WAITING_ANSWER: [SessionState.WAITING_ANSWER, SessionState.SHOWING_HINT, SessionState.SHOWING_ANSWER, SessionState.COMPLETED],
    SessionState.SHOWING_HINT: [SessionState.WAITING_ANSWER, SessionState.SHOWING_ANSWER, SessionState.COMPLETED],
    SessionState.SHOWING_ANSWER: [SessionState.WAITING_ANSWER, SessionState.COMPLETED],
    SessionState.COMPLETED: [],  # Terminal state
}


def can_transition(current: SessionState, target: SessionState) -> bool:
    """Check if transition is allowed"""
    return target in VALID_TRANSITIONS.get(current, [])


# ============================================================
# DATABASE SETUP (SQLite)
# ============================================================

DB_PATH = "idna.db"


def init_database():
    """Initialize database tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Sessions table
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
    
    # Students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER DEFAULT 10,
            grade INTEGER DEFAULT 5,
            created_at TEXT NOT NULL
        )
    """)
    
    # Create default student if none exists
    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO students (name, age, grade, created_at) VALUES (?, ?, ?, ?)",
            ("Student", 10, 5, datetime.now().isoformat())
        )
    
    conn.commit()
    conn.close()


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


# Initialize database on startup
init_database()


# ============================================================
# SESSION MANAGEMENT (SQLite-backed)
# ============================================================

import json

def create_session(session_id: str) -> dict:
    """Create new session in database"""
    now = datetime.now().isoformat()
    
    with get_db() as conn:
        conn.execute("""
            INSERT INTO sessions (id, state, started_at, updated_at, questions_asked)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, SessionState.IDLE.value, now, now, '[]'))
    
    return get_session(session_id)


def get_session(session_id: str) -> Optional[dict]:
    """Get session from database"""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
    
    if row:
        return dict(row)
    return None


def update_session(session_id: str, **kwargs) -> bool:
    """Update session fields"""
    if not kwargs:
        return False
    
    kwargs['updated_at'] = datetime.now().isoformat()
    
    # Convert lists to JSON strings
    if 'questions_asked' in kwargs and isinstance(kwargs['questions_asked'], list):
        kwargs['questions_asked'] = json.dumps(kwargs['questions_asked'])
    
    set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [session_id]
    
    with get_db() as conn:
        conn.execute(
            f"UPDATE sessions SET {set_clause} WHERE id = ?",
            values
        )
    
    return True


def transition_state(session_id: str, new_state: SessionState) -> bool:
    """Transition session to new state with validation"""
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
    """Delete session from database"""
    with get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


# ============================================================
# DETERMINISTIC MESSAGE TEMPLATES
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
    """Get random message from template list"""
    msg = random.choice(messages)
    return msg.format(**kwargs) if kwargs else msg


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class ChapterRequest(BaseModel):
    session_id: str
    chapter: str

class AnswerRequest(BaseModel):
    session_id: str
    answer: str

class TextToSpeechRequest(BaseModel):
    text: str
    voice: str = "nova"


# ============================================================
# QUESTION HELPERS
# ============================================================

def get_question_by_id(chapter: str, question_id: str) -> Optional[dict]:
    """Get question by ID from chapter"""
    questions = ALL_CHAPTERS.get(chapter, [])
    for q in questions:
        if q["id"] == question_id:
            return q
    return None


# ============================================================
# PARENT DASHBOARD FUNCTIONS
# ============================================================

def get_student_dashboard_data(student_id: int, language: str = "english"):
    """Get real dashboard data from database. Returns None if no data."""
    
    try:
        with get_db() as conn:
            # Get student info
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
            
            # Get sessions from last 7 days
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
            
            # If no completed sessions, check for any sessions
            if session_count == 0:
                any_sessions = conn.execute(
                    "SELECT COUNT(*) as cnt FROM sessions WHERE student_id = ?",
                    (student_id,)
                ).fetchone()
                if any_sessions['cnt'] == 0:
                    return None  # No data at all
            
            accuracy = round((correct / total_questions) * 100, 1) if total_questions > 0 else 0
            
            # Get daily activity
            daily_rows = conn.execute("""
                SELECT DATE(started_at) as day, COUNT(*) as sessions, 
                       COALESCE(SUM(duration_seconds), 0) as duration
                FROM sessions
                WHERE student_id = ? AND started_at > ?
                GROUP BY DATE(started_at)
                ORDER BY day
            """, (student_id, seven_days_ago)).fetchall()
            
            # Build daily activity for last 7 days
            all_days = []
            for i in range(6, -1, -1):
                day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                found = next((dict(r) for r in daily_rows if r['day'] == day), None)
                all_days.append({
                    "date": day,
                    "sessions": found['sessions'] if found else 0,
                    "duration": found['duration'] if found else 0
                })
            
            # Calculate streak
            streak = 0
            for day_data in reversed(all_days):
                if day_data['sessions'] > 0:
                    streak += 1
                else:
                    break
            
            # Generate voice message
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
    """Generate voice message in specified language (English or Hindi only)"""
    
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
# API ENDPOINTS
# ============================================================

@app.get("/")
async def root():
    """Home page"""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return FileResponse("web/index.html")


@app.get("/student")
async def student_page():
    """Student learning page"""
    return FileResponse("web/index.html")


@app.get("/parent")
async def parent_page():
    """Parent dashboard"""
    if os.path.exists("parent.html"):
        return FileResponse("parent.html")
    return JSONResponse(status_code=404, content={"error": "Parent page not found."})


@app.get("/api/chapters")
async def get_chapters():
    """Get list of available chapters"""
    return {
        "chapters": [
            {"id": ch, "name": CHAPTER_NAMES[ch]}
            for ch in ALL_CHAPTERS.keys()
        ]
    }


@app.post("/api/session/start")
async def start_session():
    """Start a new tutoring session"""
    import uuid
    session_id = str(uuid.uuid4())
    
    # Create session in database (state: IDLE)
    create_session(session_id)
    
    return {
        "session_id": session_id,
        "message": get_random_message(WELCOME_MESSAGES),
        "chapters": list(ALL_CHAPTERS.keys()),
        "state": SessionState.IDLE.value
    }


@app.post("/api/session/chapter")
async def select_chapter(request: ChapterRequest):
    """Select a chapter for practice"""
    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if request.chapter not in ALL_CHAPTERS:
        raise HTTPException(status_code=400, detail="Invalid chapter")
    
    # Validate state transition
    current_state = SessionState(session['state'])
    if current_state not in [SessionState.IDLE, SessionState.CHAPTER_SELECTED]:
        raise HTTPException(status_code=400, detail=f"Cannot select chapter in state: {current_state.value}")
    
    # Update session
    update_session(
        request.session_id,
        chapter=request.chapter,
        state=SessionState.CHAPTER_SELECTED.value
    )
    
    chapter_name = CHAPTER_NAMES[request.chapter]
    
    return {
        "message": f"Great choice! Let's practice {chapter_name}. Here comes your first question!",
        "chapter": request.chapter,
        "chapter_name": chapter_name,
        "state": SessionState.CHAPTER_SELECTED.value
    }


@app.post("/api/session/question")
async def get_question(request: ChapterRequest):
    """Get the next question"""
    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    current_state = SessionState(session['state'])
    
    # Validate state - can get question from CHAPTER_SELECTED, SHOWING_ANSWER, or WAITING_ANSWER (retry)
    valid_states = [SessionState.CHAPTER_SELECTED, SessionState.SHOWING_ANSWER, SessionState.WAITING_ANSWER]
    if current_state not in valid_states:
        raise HTTPException(status_code=400, detail=f"Cannot get question in state: {current_state.value}")
    
    chapter_questions = ALL_CHAPTERS.get(request.chapter, [])
    if not chapter_questions:
        raise HTTPException(status_code=400, detail="No questions in chapter")
    
    # Get questions already asked
    questions_asked = json.loads(session['questions_asked'] or '[]')
    
    # Get a question not yet asked
    available = [q for q in chapter_questions if q["id"] not in questions_asked]
    if not available:
        available = chapter_questions
        questions_asked = []
    
    question = random.choice(available)
    questions_asked.append(question["id"])
    
    # Update session - transition to WAITING_ANSWER
    new_total = (session['total'] or 0) + 1
    update_session(
        request.session_id,
        current_question_id=question["id"],
        attempt_count=0,
        total=new_total,
        questions_asked=questions_asked,
        state=SessionState.WAITING_ANSWER.value
    )
    
    return {
        "question_number": new_total,
        "question_text": question["text"],
        "question_id": question["id"],
        "state": SessionState.WAITING_ANSWER.value
    }


@app.post("/api/session/answer")
async def submit_answer(request: AnswerRequest):
    """Submit an answer and get feedback"""
    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    current_state = SessionState(session['state'])
    
    # Validate state
    if current_state not in [SessionState.WAITING_ANSWER, SessionState.SHOWING_HINT]:
        raise HTTPException(status_code=400, detail=f"Cannot submit answer in state: {current_state.value}")
    
    if not session['current_question_id']:
        raise HTTPException(status_code=400, detail="No active question")
    
    # Get the question
    question = get_question_by_id(session['chapter'], session['current_question_id'])
    if not question:
        raise HTTPException(status_code=400, detail="Question not found")
    
    is_correct = check_answer(question["answer"], request.answer)
    attempt_count = (session['attempt_count'] or 0) + 1
    
    if is_correct:
        new_score = (session['score'] or 0) + 1
        new_correct = (session['correct_answers'] or 0) + 1
        
        # Transition to SHOWING_ANSWER (ready for next question)
        update_session(
            request.session_id,
            score=new_score,
            correct_answers=new_correct,
            attempt_count=attempt_count,
            state=SessionState.SHOWING_ANSWER.value
        )
        
        return {
            "correct": True,
            "message": get_random_message(PRAISE_MESSAGES),
            "score": new_score,
            "total": session['total'],
            "state": SessionState.SHOWING_ANSWER.value
        }
    else:
        if attempt_count >= 3:
            # Max attempts - show answer
            update_session(
                request.session_id,
                attempt_count=attempt_count,
                state=SessionState.SHOWING_ANSWER.value
            )
            
            return {
                "correct": False,
                "show_answer": True,
                "answer": question["answer"],
                "message": f"The correct answer is {question['answer']}. Let's move on!",
                "score": session['score'],
                "total": session['total'],
                "state": SessionState.SHOWING_ANSWER.value
            }
        elif attempt_count == 2:
            # Show hint
            hint = question.get("hint", "Think carefully!")
            
            update_session(
                request.session_id,
                attempt_count=attempt_count,
                state=SessionState.SHOWING_HINT.value
            )
            
            return {
                "correct": False,
                "hint": hint,
                "message": get_random_message(HINT_MESSAGES) + hint,
                "attempts_left": 3 - attempt_count,
                "score": session['score'],
                "total": session['total'],
                "state": SessionState.SHOWING_HINT.value
            }
        else:
            # First wrong attempt - encourage retry
            update_session(
                request.session_id,
                attempt_count=attempt_count,
                state=SessionState.WAITING_ANSWER.value
            )
            
            return {
                "correct": False,
                "message": get_random_message(ENCOURAGEMENT_MESSAGES),
                "attempts_left": 3 - attempt_count,
                "score": session['score'],
                "total": session['total'],
                "state": SessionState.WAITING_ANSWER.value
            }


@app.post("/api/session/end")
async def end_session(request: ChapterRequest):
    """End the session and get summary"""
    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    score = session['score'] or 0
    total = session['total'] or 0
    
    # Calculate duration
    started_at = datetime.fromisoformat(session['started_at'])
    duration = int((datetime.now() - started_at).total_seconds())
    
    # Update session to COMPLETED
    update_session(
        request.session_id,
        state=SessionState.COMPLETED.value,
        duration_seconds=duration
    )
    
    closing = get_random_message(CLOSING_MESSAGES, score=score, total=total)
    
    return {
        "message": closing,
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
    """Get parent dashboard data - real data only"""
    
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
    """Generate voice report with timeout"""
    
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
        # OpenAI call with timeout (set in client initialization)
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
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
# VOICE ENDPOINTS (with timeouts)
# ============================================================

@app.post("/api/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """Convert speech to text using Whisper (with timeout)"""
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Whisper call (timeout set in client)
        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="en"
            )
        
        os.unlink(tmp_path)
        
        return {"text": transcript.text}
        
    except Exception as e:
        print(f"STT Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/text-to-speech")
async def text_to_speech(request: TextToSpeechRequest):
    """Convert text to speech (with timeout)"""
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice=request.voice,
            input=request.text
        )
        
        audio_base64 = base64.b64encode(response.content).decode('utf-8')
        
        return {"audio": audio_base64, "format": "mp3"}
        
    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health_check():
    """Health check for Railway"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if os.path.exists(DB_PATH) else "initializing"
    }


# ============================================================
# DEBUG ENDPOINT (remove in production)
# ============================================================

@app.get("/api/debug/sessions")
async def debug_sessions():
    """Debug: List all sessions (remove in production)"""
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
    print(f"Database: {DB_PATH}")
    print(f"FSM States: {[s.value for s in SessionState]}")
    uvicorn.run(app, host="0.0.0.0", port=port)
