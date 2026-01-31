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
import logging
import time
from enum import Enum
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager, asynccontextmanager
from functools import lru_cache
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Any, Dict, Tuple
from dotenv import load_dotenv
from openai import OpenAI
from google.cloud import texttospeech


# ============================================================
# STRUCTURED LOGGING (PRD: session_id, student_id, latencies)
# ============================================================

class StructuredLogger:
    """
    Structured logger for production observability.

    Outputs JSON-formatted logs with context:
    - session_id: Current session identifier
    - student_id: Student identifier
    - latency_ms: Operation duration in milliseconds
    - endpoint: API endpoint being called
    - event: Type of event (request, response, error, etc.)
    """

    def __init__(self, name: str = "idna"):
        self.logger = logging.getLogger(name)
        self._setup_handler()

    def _setup_handler(self):
        """Configure JSON logging handler."""
        # Only add handler if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _format_log(self, level: str, message: str, **context) -> str:
        """Format log entry as JSON."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": level,
            "message": message,
            **context
        }
        # Remove None values
        log_entry = {k: v for k, v in log_entry.items() if v is not None}
        return json.dumps(log_entry)

    def info(self, message: str, **context):
        """Log info level message with context."""
        self.logger.info(self._format_log("INFO", message, **context))

    def warning(self, message: str, **context):
        """Log warning level message with context."""
        self.logger.warning(self._format_log("WARNING", message, **context))

    def error(self, message: str, **context):
        """Log error level message with context."""
        self.logger.error(self._format_log("ERROR", message, **context))

    def debug(self, message: str, **context):
        """Log debug level message with context."""
        self.logger.debug(self._format_log("DEBUG", message, **context))


# Global structured logger instance
slog = StructuredLogger("idna")


class Timer:
    """Context manager for timing operations."""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed_ms = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        self.elapsed_ms = round((self.end_time - self.start_time) * 1000, 2)


def log_latency(operation: str, latency_ms: float, **context):
    """Log operation latency with context."""
    slog.info(
        f"{operation} completed",
        operation=operation,
        latency_ms=latency_ms,
        **context
    )

from questions import ALL_CHAPTERS, CHAPTER_NAMES, CHAPTER_INTROS
from evaluator import check_answer, normalize_spoken_input
from tutor_intent import (
    generate_tutor_response,
    generate_gpt_response,
    generate_step_explanation,
    wrap_in_ssml,
    is_help_request,
    detect_off_topic,
    TutorIntent,
    TutorVoice
)


# ============================================================
# IDEMPOTENCY CACHE: Prevent duplicate answer submissions
# ============================================================
# Time-limited cache for idempotent answer submissions
# Key: (session_id, question_id, idempotency_key)
# Value: (response_dict, timestamp)
# TTL: 5 minutes (enough for retries, not too long to waste memory)

_idempotency_cache: Dict[str, tuple] = {}
_IDEMPOTENCY_TTL_SECONDS = 300  # 5 minutes


def _get_idempotency_key(session_id: str, question_id: str, client_key: str) -> str:
    """Generate cache key for idempotency check."""
    return f"{session_id}:{question_id}:{client_key}"


def _check_idempotency(session_id: str, question_id: str, client_key: Optional[str]) -> Optional[dict]:
    """
    Check if this request was already processed.

    Returns cached response if found and not expired, None otherwise.
    """
    if not client_key:
        return None

    cache_key = _get_idempotency_key(session_id, question_id, client_key)
    cached = _idempotency_cache.get(cache_key)

    if cached:
        response, timestamp = cached
        # Check if expired
        if time.time() - timestamp < _IDEMPOTENCY_TTL_SECONDS:
            slog.info(
                "Idempotency cache hit - returning cached response",
                event="idempotency_hit",
                session_id=session_id,
                question_id=question_id,
            )
            return response
        else:
            # Expired, remove from cache
            del _idempotency_cache[cache_key]

    return None


def _store_idempotency(session_id: str, question_id: str, client_key: Optional[str], response: dict):
    """Store response in idempotency cache."""
    if not client_key:
        return

    cache_key = _get_idempotency_key(session_id, question_id, client_key)
    _idempotency_cache[cache_key] = (response, time.time())

    # Cleanup old entries periodically (every 100 stores)
    if len(_idempotency_cache) > 100:
        _cleanup_idempotency_cache()


def _cleanup_idempotency_cache():
    """Remove expired entries from idempotency cache."""
    current_time = time.time()
    expired_keys = [
        key for key, (_, timestamp) in _idempotency_cache.items()
        if current_time - timestamp >= _IDEMPOTENCY_TTL_SECONDS
    ]
    for key in expired_keys:
        del _idempotency_cache[key]


# ============================================================
# SESSION LOCKING: Prevent race conditions
# ============================================================
# Per-session locks to ensure only one request modifies session state at a time
# Prevents issues like:
# - /question requested while /answer is still processing
# - Two /answer requests overlapping and corrupting state

_session_locks: Dict[str, asyncio.Lock] = {}
_session_locks_lock: Optional[asyncio.Lock] = None  # Initialized lazily


def _get_locks_lock() -> asyncio.Lock:
    """Get or create the lock for accessing session locks dict (lazy init)."""
    global _session_locks_lock
    if _session_locks_lock is None:
        _session_locks_lock = asyncio.Lock()
    return _session_locks_lock


async def get_session_lock(session_id: str) -> asyncio.Lock:
    """
    Get or create an asyncio Lock for a specific session.

    This ensures only one request per session can modify state at a time.
    """
    async with _get_locks_lock():
        if session_id not in _session_locks:
            _session_locks[session_id] = asyncio.Lock()
        return _session_locks[session_id]


async def cleanup_session_lock(session_id: str):
    """Remove a session's lock when session ends (optional cleanup)."""
    async with _get_locks_lock():
        if session_id in _session_locks:
            del _session_locks[session_id]


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
    db_info = f"Postgres ({DATABASE_URL[:30]}...)" if USE_POSTGRES else f"SQLite ({DB_PATH})"
    print(f"[STARTUP] Database: {db_info}")
    print(f"[STARTUP] PORT env: {os.environ.get('PORT', 'not set')}")
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


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """
    Middleware to log all API requests with latency.

    Logs:
    - endpoint: Request path
    - method: HTTP method
    - latency_ms: Request duration
    - status_code: Response status
    """
    # Skip logging for static files and health checks
    path = request.url.path
    if path.startswith("/static") or path.startswith("/web") or path in ["/health", "/healthz"]:
        return await call_next(request)

    # Extract session_id from request body if available (for POST requests)
    session_id = None
    if request.method == "POST":
        try:
            body = await request.body()
            if body:
                body_json = json.loads(body)
                session_id = body_json.get("session_id")
            # Reset body for downstream handlers
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
        except Exception:
            pass

    # Time the request
    start_time = time.perf_counter()

    # Process request
    response = await call_next(request)

    # Calculate latency
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Log the request
    slog.info(
        f"{request.method} {path}",
        event="api_request",
        endpoint=path,
        method=request.method,
        status_code=response.status_code,
        latency_ms=latency_ms,
        session_id=session_id,
    )

    return response


# Global exception handler - ensure all errors return JSON
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to ensure all errors return JSON responses.
    This prevents the frontend from getting plain text "Internal Server Error".
    """
    # Log the error
    slog.error(
        f"Unhandled exception: {str(exc)}",
        event="unhandled_exception",
        endpoint=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        error_message=str(exc)
    )

    # Return JSON response
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc) if os.getenv("DEBUG") else "An unexpected error occurred",
            "type": type(exc).__name__
        }
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
    language_code: str = "en-IN",
    voice_name: str = "en-IN-Neural2-A",
    ssml: Optional[str] = None
) -> bytes:
    """Generate natural speech using Google Cloud TTS

    Args:
        text: Plain text to speak (used if ssml is None)
        language_code: Language code (default: en-IN for Indian English)
        voice_name: Voice to use (default: en-IN-Neural2-A, warm Indian female voice)
        ssml: Optional SSML markup for natural speech

    Indian English voices (Neural2 = most natural):
    - en-IN-Neural2-A: Female - warm, friendly (DEFAULT)
    - en-IN-Neural2-D: Male - warm, clear

    US English alternatives:
    - en-US-Neural2-F: Female - warm, friendly, clear
    - en-US-Neural2-D: Male - warm, clear
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
        speaking_rate=0.92,  # Slower for warmth and Indian accent clarity
        pitch=-0.5,  # Slightly lower pitch for warmth
        volume_gain_db=3.0,  # Good volume
        effects_profile_id=["small-bluetooth-speaker-class-device"],  # Optimize for speakers
    )

    try:
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        return response.audio_content
    except Exception as e:
        # Fallback to alternative voice
        print(f"Primary voice failed, trying fallback: {e}")
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-IN",
            name="en-IN-Neural2-D",  # Male Indian voice as fallback
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
# DATABASE SETUP (SQLite for dev, Postgres for production)
# ============================================================
# Configuration:
#   - DATABASE_URL: Postgres connection string (production)
#     Example: postgres://user:pass@host:5432/dbname
#   - DATABASE_PATH: SQLite file path (development, default: idna.db)
#
# Priority: DATABASE_URL takes precedence if set
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")
DB_PATH = os.getenv("DATABASE_PATH", "idna.db")
USE_POSTGRES = DATABASE_URL is not None

# Postgres connection pool (lazy initialized)
_pg_pool = None

if USE_POSTGRES:
    try:
        import psycopg2
        from psycopg2 import pool
        from psycopg2.extras import RealDictCursor
        print(f"[DB] Postgres mode enabled")
    except ImportError:
        print("[DB] WARNING: psycopg2 not installed, falling back to SQLite")
        USE_POSTGRES = False


def get_postgres_pool():
    """Get or create Postgres connection pool."""
    global _pg_pool
    if _pg_pool is None and USE_POSTGRES:
        _pg_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=DATABASE_URL
        )
    return _pg_pool


def init_database():
    """Initialize database tables (works with both SQLite and Postgres)."""
    if USE_POSTGRES:
        init_postgres_database()
    else:
        init_sqlite_database()


def init_sqlite_database():
    """Initialize SQLite database tables."""
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
            correct_answers INTEGER DEFAULT 0,
            current_difficulty INTEGER DEFAULT 1,
            consecutive_correct INTEGER DEFAULT 0,
            consecutive_wrong INTEGER DEFAULT 0,
            low_confidence_streak INTEGER DEFAULT 0
        )
    """)

    # Add columns to existing sessions table if they don't exist (migration)
    for col, default in [
        ("current_difficulty", 1),
        ("consecutive_correct", 0),
        ("consecutive_wrong", 0),
        ("low_confidence_streak", 0)
    ]:
        try:
            cursor.execute(f"ALTER TABLE sessions ADD COLUMN {col} INTEGER DEFAULT {default}")
        except sqlite3.OperationalError:
            pass  # Column already exists

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER DEFAULT 10,
            grade INTEGER DEFAULT 5,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            topic_tag TEXT NOT NULL,
            attempt_no INTEGER NOT NULL,
            is_correct INTEGER NOT NULL,
            hint_level_used INTEGER DEFAULT 0,
            answer_text TEXT,
            difficulty INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            -- Debug/audit fields (ChatGPT recommendation)
            raw_utterance TEXT,
            normalized_answer TEXT,
            asr_confidence REAL,
            input_mode TEXT DEFAULT 'text',
            latency_ms INTEGER,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_topic ON attempts(topic_tag, is_correct)")

    cursor.execute("SELECT COUNT(*) FROM students")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO students (name, age, grade, created_at) VALUES (?, ?, ?, ?)",
            ("Student", 10, 5, datetime.now().isoformat())
        )

    conn.commit()
    conn.close()
    print(f"[DB] SQLite initialized: {DB_PATH}")


def init_postgres_database():
    """Initialize Postgres database tables."""
    pool = get_postgres_pool()
    conn = pool.getconn()
    try:
        cursor = conn.cursor()

        # Check if sessions table has wrong schema (missing 'id' column)
        # This can happen if table was created with different schema
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'sessions' AND column_name = 'id'
        """)
        has_id_column = cursor.fetchone() is not None

        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'sessions'
            )
        """)
        table_exists = cursor.fetchone()[0]

        if table_exists and not has_id_column:
            print("[DB] Sessions table has wrong schema - recreating...")
            # Drop dependent tables first (foreign key constraints)
            cursor.execute("DROP TABLE IF EXISTS attempts CASCADE")
            cursor.execute("DROP TABLE IF EXISTS sessions CASCADE")
            conn.commit()
            print("[DB] Old tables dropped, recreating with correct schema...")

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
                correct_answers INTEGER DEFAULT 0,
                current_difficulty INTEGER DEFAULT 1,
                consecutive_correct INTEGER DEFAULT 0,
                consecutive_wrong INTEGER DEFAULT 0,
                low_confidence_streak INTEGER DEFAULT 0
            )
        """)

        # Add columns if they don't exist (Postgres migration)
        for col, default in [
            ("current_difficulty", 1),
            ("consecutive_correct", 0),
            ("consecutive_wrong", 0),
            ("low_confidence_streak", 0)
        ]:
            try:
                cursor.execute(f"""
                    ALTER TABLE sessions ADD COLUMN IF NOT EXISTS {col} INTEGER DEFAULT {default}
                """)
            except Exception:
                pass

        # Students table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER DEFAULT 10,
                grade INTEGER DEFAULT 5,
                created_at TEXT NOT NULL
            )
        """)

        # Attempts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                question_id TEXT NOT NULL,
                topic_tag TEXT NOT NULL,
                attempt_no INTEGER NOT NULL,
                is_correct INTEGER NOT NULL,
                hint_level_used INTEGER DEFAULT 0,
                answer_text TEXT,
                difficulty INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                -- Debug/audit fields (ChatGPT recommendation)
                raw_utterance TEXT,
                normalized_answer TEXT,
                asr_confidence REAL,
                input_mode TEXT DEFAULT 'text',
                latency_ms INTEGER
            )
        """)

        # Add columns to existing attempts table if they don't exist (migration)
        attempts_columns = [
            ("topic_tag", "TEXT"),
            ("raw_utterance", "TEXT"),
            ("normalized_answer", "TEXT"),
            ("asr_confidence", "REAL"),
            ("input_mode", "TEXT DEFAULT 'text'"),
            ("latency_ms", "INTEGER"),
        ]
        for col, col_type in attempts_columns:
            try:
                cursor.execute(f"ALTER TABLE attempts ADD COLUMN IF NOT EXISTS {col} {col_type}")
            except Exception:
                pass  # Column already exists or other error

        conn.commit()  # Commit column additions before creating indexes

        # Indexes (only create if columns exist)
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_attempts_topic ON attempts(topic_tag, is_correct)")
        except Exception as e:
            print(f"[DB] Index creation skipped: {e}")

        # Default student if none exists
        cursor.execute("SELECT COUNT(*) FROM students")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO students (name, age, grade, created_at) VALUES (%s, %s, %s, %s)",
                ("Student", 10, 5, datetime.now().isoformat())
            )

        conn.commit()
        print(f"[DB] Postgres initialized: {DATABASE_URL[:30]}...")
    finally:
        pool.putconn(conn)


class DatabaseConnection:
    """
    Wrapper class for database connection that works with both SQLite and Postgres.
    Provides unified interface and handles placeholder conversion.
    """
    def __init__(self, conn, is_postgres=False, pool=None):
        self.conn = conn
        self.is_postgres = is_postgres
        self.pool = pool  # For returning to pool on close

    def execute(self, query, params=None):
        """Execute query with automatic placeholder conversion."""
        if self.is_postgres and params:
            # Convert ? to %s for Postgres
            query = query.replace("?", "%s")
        cursor = self.conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor

    def commit(self):
        self.conn.commit()

    def close(self):
        if self.is_postgres and self.pool:
            self.pool.putconn(self.conn)
        else:
            self.conn.close()


@contextmanager
def get_db():
    """
    Database connection context manager.
    Works with both SQLite (dev) and Postgres (production).

    Usage:
        with get_db() as conn:
            conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    """
    if USE_POSTGRES:
        pool = get_postgres_pool()
        pg_conn = pool.getconn()
        # Use RealDictCursor for dict-like row access
        pg_conn.cursor_factory = RealDictCursor
        wrapper = DatabaseConnection(pg_conn, is_postgres=True, pool=pool)
        try:
            yield wrapper
            wrapper.commit()
        except Exception:
            pg_conn.rollback()
            raise
        finally:
            wrapper.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        wrapper = DatabaseConnection(conn, is_postgres=False)
        try:
            yield wrapper
            wrapper.commit()
        finally:
            wrapper.close()


# ============================================================
# SESSION MANAGEMENT
# ============================================================

def create_session(session_id: str, student_id: int = None) -> dict:
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute("""
            INSERT INTO sessions (id, state, started_at, updated_at, questions_asked, student_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, SessionState.IDLE.value, now, now, '[]', student_id or 1))
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
# ATTEMPT TRACKING (PRD: attempts table)
# ============================================================

def record_attempt(
    session_id: str,
    question_id: str,
    topic_tag: str,
    attempt_no: int,
    is_correct: bool,
    answer_text: str,
    hint_level_used: int = 0,
    difficulty: int = 1,
    # New debug/audit fields
    raw_utterance: Optional[str] = None,
    normalized_answer: Optional[str] = None,
    asr_confidence: Optional[float] = None,
    input_mode: str = "text",
    latency_ms: Optional[int] = None,
) -> int:
    """
    Record a student's answer attempt to the database.

    Per PRD, this enables:
    - Topic-level performance tracking
    - Hint usage analysis
    - Parent summary generation
    - Weak topic identification

    Args:
        session_id: Current session ID
        question_id: The question being answered
        topic_tag: Chapter/topic name (e.g., "rational_numbers")
        attempt_no: Which attempt this is (1, 2, or 3)
        is_correct: Whether the answer was correct
        answer_text: What the student actually answered
        hint_level_used: 0=no hint, 1=hint1, 2=hint2, 3=solution shown
        difficulty: Question difficulty (1-3)
        raw_utterance: Original STT text before normalization
        normalized_answer: Answer after evaluator normalization
        asr_confidence: STT confidence score (0.0-1.0)
        input_mode: 'voice' or 'text'
        latency_ms: Total processing time in milliseconds

    Returns:
        The attempt ID
    """
    now = datetime.now().isoformat()
    with get_db() as conn:
        if USE_POSTGRES:
            # Postgres: use RETURNING to get the inserted ID
            cursor = conn.execute("""
                INSERT INTO attempts
                (session_id, question_id, topic_tag, attempt_no, is_correct,
                 hint_level_used, answer_text, difficulty, created_at,
                 raw_utterance, normalized_answer, asr_confidence, input_mode, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
            """, (
                session_id, question_id, topic_tag, attempt_no,
                1 if is_correct else 0, hint_level_used, answer_text,
                difficulty, now,
                raw_utterance, normalized_answer, asr_confidence, input_mode, latency_ms
            ))
            result = cursor.fetchone()
            return result['id'] if result else 0
        else:
            # SQLite: use lastrowid
            cursor = conn.execute("""
                INSERT INTO attempts
                (session_id, question_id, topic_tag, attempt_no, is_correct,
                 hint_level_used, answer_text, difficulty, created_at,
                 raw_utterance, normalized_answer, asr_confidence, input_mode, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, question_id, topic_tag, attempt_no,
                1 if is_correct else 0, hint_level_used, answer_text,
                difficulty, now,
                raw_utterance, normalized_answer, asr_confidence, input_mode, latency_ms
            ))
            return cursor.lastrowid


def get_session_attempts(session_id: str) -> list:
    """Get all attempts for a session."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT * FROM attempts
            WHERE session_id = ?
            ORDER BY created_at
        """, (session_id,)).fetchall()
    return [dict(row) for row in rows]


def get_topic_performance(session_id: str) -> dict:
    """
    Get performance breakdown by topic for a session.

    Returns dict like:
    {
        "rational_numbers": {"correct": 5, "total": 8, "hint_usage": 3},
        "linear_equations": {"correct": 3, "total": 5, "hint_usage": 1},
    }
    """
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                topic_tag,
                SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct,
                COUNT(DISTINCT question_id) as total_questions,
                SUM(CASE WHEN hint_level_used > 0 THEN 1 ELSE 0 END) as hint_usage
            FROM attempts
            WHERE session_id = ?
            GROUP BY topic_tag
        """, (session_id,)).fetchall()

    return {
        row['topic_tag']: {
            "correct": row['correct'],
            "total": row['total_questions'],
            "hint_usage": row['hint_usage'],
            "accuracy": round(row['correct'] / row['total_questions'] * 100, 1) if row['total_questions'] > 0 else 0
        }
        for row in rows
    }


def get_weak_topics(student_id: int, threshold: float = 60.0) -> list:
    """
    Identify weak topics where accuracy is below threshold.

    Returns list of topic names that need attention.
    """
    with get_db() as conn:
        rows = conn.execute("""
            SELECT
                a.topic_tag,
                SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) as correct,
                COUNT(DISTINCT a.question_id) as total
            FROM attempts a
            JOIN sessions s ON a.session_id = s.id
            WHERE s.student_id = ?
            GROUP BY a.topic_tag
            HAVING total >= 3
        """, (student_id,)).fetchall()

    weak = []
    for row in rows:
        accuracy = (row['correct'] / row['total'] * 100) if row['total'] > 0 else 0
        if accuracy < threshold:
            weak.append({
                "topic": row['topic_tag'],
                "accuracy": round(accuracy, 1),
                "attempts": row['total']
            })

    # Sort by accuracy (worst first)
    return sorted(weak, key=lambda x: x['accuracy'])


# ============================================================
# PERFORMANCE: Async wrappers for database operations
# Runs sync SQLite in thread pool to avoid blocking event loop
# ============================================================

async def async_create_session(session_id: str, student_id: int = None) -> dict:
    """Async wrapper for create_session."""
    return await asyncio.to_thread(create_session, session_id, student_id)

async def async_get_session(session_id: str) -> Optional[dict]:
    """Async wrapper for get_session."""
    return await asyncio.to_thread(get_session, session_id)

async def async_update_session(session_id: str, **kwargs) -> bool:
    """Async wrapper for update_session."""
    return await asyncio.to_thread(update_session, session_id, **kwargs)

async def async_record_attempt(**kwargs) -> int:
    """Async wrapper for record_attempt."""
    return await asyncio.to_thread(lambda: record_attempt(**kwargs))

async def async_get_topic_performance(session_id: str) -> dict:
    """Async wrapper for get_topic_performance."""
    return await asyncio.to_thread(get_topic_performance, session_id)

async def async_get_weak_topics(student_id: int, threshold: float = 60.0) -> list:
    """Async wrapper for get_weak_topics."""
    return await asyncio.to_thread(get_weak_topics, student_id, threshold)


def get_student_context(student_id: int) -> dict:
    """
    Get student context for personalized tutoring.
    Returns name, weak topics, recent performance, and recommendations.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get student info
        student = cursor.execute(
            "SELECT id, name, grade FROM students WHERE id = ?", (student_id,)
        ).fetchone()

        if not student:
            return None

        student_name = student['name'] if student['name'] else "there"

        # Get weak topics (below 60% accuracy)
        weak_topics = get_weak_topics(student_id, threshold=60.0)

        # Get recent session stats (last 7 days)
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        stats = cursor.execute("""
            SELECT
                COUNT(*) as session_count,
                SUM(questions_attempted) as total_questions,
                AVG(CASE WHEN questions_attempted > 0
                    THEN CAST(questions_correct AS FLOAT) / questions_attempted * 100
                    ELSE 0 END) as avg_accuracy
            FROM sessions
            WHERE student_id = ? AND started_at > ? AND state = ?
        """, (student_id, seven_days_ago, SessionState.COMPLETED.value)).fetchone()

        # Get strong topics (above 80% accuracy)
        strong_topics = cursor.execute("""
            SELECT
                a.topic_tag,
                COUNT(*) as attempts,
                SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) as correct
            FROM attempts a
            JOIN sessions s ON a.session_id = s.id
            WHERE s.student_id = ? AND a.topic_tag IS NOT NULL
            GROUP BY a.topic_tag
            HAVING COUNT(*) >= 3 AND (SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) >= 80
        """, (student_id,)).fetchall()

        return {
            "student_id": student_id,
            "name": student_name,
            "grade": student['grade'],
            "weak_topics": weak_topics,
            "strong_topics": [t['topic_tag'] for t in strong_topics] if strong_topics else [],
            "recent_sessions": stats['session_count'] if stats else 0,
            "recent_accuracy": round(stats['avg_accuracy'], 1) if stats and stats['avg_accuracy'] else None,
            "is_returning": (stats['session_count'] or 0) > 0
        }


async def async_get_student_context(student_id: int) -> dict:
    """Async wrapper for get_student_context."""
    return await asyncio.to_thread(get_student_context, student_id)


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

# Messages for low confidence STT (PRD: Ask to repeat)
LOW_CONFIDENCE_MESSAGES = [
    "I didn't catch that clearly. Please say your answer again.",
    "Sorry, I couldn't hear you properly. Can you repeat that?",
    "I'm not sure I understood. Please say your answer once more.",
    "Could you say that again? I want to make sure I got it right.",
]

# Messages for text fallback after multiple low confidence attempts
TEXT_FALLBACK_MESSAGES = [
    "I'm having trouble hearing you clearly. Try typing your answer instead!",
    "Voice isn't working well right now. Please type your answer in the box below.",
    "Let's switch to typing! Please type your answer.",
]

# Max low confidence attempts before suggesting text input
MAX_LOW_CONFIDENCE_STREAK = 2


def get_random_message(messages: list, **kwargs) -> str:
    msg = random.choice(messages)
    return msg.format(**kwargs) if kwargs else msg


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class SessionStartRequest(BaseModel):
    student_id: Optional[int] = None  # Existing student ID
    student_name: Optional[str] = None  # For new students or guests

class ChapterRequest(BaseModel):
    session_id: str
    chapter: str = ""

class AnswerRequest(BaseModel):
    session_id: str
    answer: str
    # PRD: STT confidence fields (optional, from speech-to-text)
    confidence: Optional[float] = None  # 0.0 to 1.0
    is_voice_input: bool = False  # True if answer came from STT
    # Idempotency: Prevent duplicate submissions on double-click/retry
    idempotency_key: Optional[str] = None  # Client-generated unique key

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


# ============================================================
# ADAPTIVE QUESTION SELECTION (PRD: Difficulty adjustment)
# ============================================================

def select_adaptive_question(
    chapter: str,
    asked_ids: list,
    current_difficulty: int = 1,
) -> Optional[dict]:
    """
    Select next question using adaptive difficulty per PRD.

    Strategy:
    - Start with questions at current_difficulty
    - If none available at current level, try adjacent levels
    - Prefer questions not yet asked

    Args:
        chapter: Chapter ID
        asked_ids: List of already-asked question IDs
        current_difficulty: Current difficulty level (1-3)

    Returns:
        Selected question dict or None if no questions available
    """
    questions = ALL_CHAPTERS.get(chapter, [])
    if not questions:
        return None

    # Filter out already-asked questions
    available = [q for q in questions if q['id'] not in asked_ids]
    if not available:
        return None

    # Group by difficulty
    by_difficulty = {1: [], 2: [], 3: []}
    for q in available:
        diff = q.get('difficulty', 1)
        if diff in by_difficulty:
            by_difficulty[diff].append(q)

    # Try to find question at current difficulty
    if by_difficulty.get(current_difficulty):
        return random.choice(by_difficulty[current_difficulty])

    # Try adjacent difficulties (prefer going down if struggling)
    search_order = []
    if current_difficulty == 1:
        search_order = [2, 3]  # Only can go up
    elif current_difficulty == 2:
        search_order = [1, 3]  # Try easier first, then harder
    else:  # current_difficulty == 3
        search_order = [2, 1]  # Go down

    for diff in search_order:
        if by_difficulty.get(diff):
            return random.choice(by_difficulty[diff])

    # Fallback: any available question
    return random.choice(available) if available else None


def adjust_difficulty(
    current_difficulty: int,
    consecutive_correct: int,
    consecutive_wrong: int,
    is_correct: bool,
) -> tuple:
    """
    Adjust difficulty based on performance per PRD.

    Rules:
    - 3 correct in a row → increase difficulty (max 3)
    - 2 wrong in a row → decrease difficulty (min 1)
    - Reset streak counters on difficulty change

    Args:
        current_difficulty: Current difficulty (1-3)
        consecutive_correct: Current correct streak
        consecutive_wrong: Current wrong streak
        is_correct: Whether current answer was correct

    Returns:
        Tuple of (new_difficulty, new_consecutive_correct, new_consecutive_wrong)
    """
    if is_correct:
        consecutive_correct += 1
        consecutive_wrong = 0

        # 3 correct in a row → increase difficulty
        if consecutive_correct >= 3 and current_difficulty < 3:
            return (current_difficulty + 1, 0, 0)
    else:
        consecutive_wrong += 1
        consecutive_correct = 0

        # 2 wrong in a row → decrease difficulty
        if consecutive_wrong >= 2 and current_difficulty > 1:
            return (current_difficulty - 1, 0, 0)

    return (current_difficulty, consecutive_correct, consecutive_wrong)


def get_difficulty_label(difficulty: int) -> str:
    """Get human-readable difficulty label."""
    labels = {1: "Easy", 2: "Medium", 3: "Hard"}
    return labels.get(difficulty, "Unknown")


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


def generate_whatsapp_summary(
    student_name: str,
    study_minutes: int,
    questions_attempted: int,
    accuracy: float,
    hint_usage_rate: float,
    weak_topics: list,
    language: str = "english"
) -> str:
    """
    Generate a WhatsApp-ready parent summary per PRD specification.

    Format (English):
    📚 IDNA Weekly Report - [Name]
    ⏱️ Time: X minutes
    📝 Questions: X attempted
    ✅ Accuracy: X%
    💡 Hint usage: X%
    ⚠️ Needs practice: Topic1, Topic2
    👉 Next step: [recommendation]

    Args:
        student_name: Student's name
        study_minutes: Total study time in minutes
        questions_attempted: Number of questions attempted
        accuracy: Accuracy percentage
        hint_usage_rate: Percentage of questions where hints were used
        weak_topics: List of topic names needing attention
        language: "english" or "hindi"

    Returns:
        WhatsApp-ready formatted string
    """
    # Determine next step recommendation based on weak topics and accuracy
    if accuracy >= 80:
        next_step_en = "Keep up the great work! Try harder questions."
        next_step_hi = "बहुत अच्छा! कठिन सवालों को आज़माएं।"
    elif accuracy >= 60:
        next_step_en = f"Practice more on {weak_topics[0] if weak_topics else 'basics'}."
        next_step_hi = f"{weak_topics[0] if weak_topics else 'बेसिक्स'} का अभ्यास करें।"
    else:
        next_step_en = f"Focus on {weak_topics[0] if weak_topics else 'fundamentals'} with hints."
        next_step_hi = f"{weak_topics[0] if weak_topics else 'मूल बातें'} पर ध्यान दें।"

    # Format weak topics (max 2)
    weak_display = ", ".join(weak_topics[:2]) if weak_topics else "None"

    if language == "hindi":
        return f"""📚 *IDNA साप्ताहिक रिपोर्ट - {student_name}*

⏱️ समय: {study_minutes} मिनट
📝 सवाल: {questions_attempted} प्रयास किए
✅ सटीकता: {accuracy}%
💡 हिंट उपयोग: {hint_usage_rate}%
⚠️ अभ्यास चाहिए: {weak_display}

👉 अगला कदम: {next_step_hi}

_IDNA EdTech द्वारा_"""
    else:
        return f"""📚 *IDNA Weekly Report - {student_name}*

⏱️ Time: {study_minutes} minutes
📝 Questions: {questions_attempted} attempted
✅ Accuracy: {accuracy}%
💡 Hint usage: {hint_usage_rate}%
⚠️ Needs practice: {weak_display}

👉 Next step: {next_step_en}

_Powered by IDNA EdTech_"""


def get_student_weekly_stats(student_id: int) -> Optional[dict]:
    """
    Get comprehensive weekly stats for parent summary.

    Includes data from both sessions and attempts tables.
    """
    try:
        with get_db() as conn:
            # Get student info
            student_row = conn.execute(
                "SELECT * FROM students WHERE id = ?", (student_id,)
            ).fetchone()

            if not student_row:
                return None

            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()

            # Session stats
            session_stats = conn.execute("""
                SELECT
                    COALESCE(SUM(duration_seconds), 0) as total_time,
                    COALESCE(SUM(correct_answers), 0) as correct,
                    COALESCE(SUM(total), 0) as total_questions,
                    COUNT(*) as session_count
                FROM sessions
                WHERE student_id = ? AND started_at > ? AND state = ?
            """, (student_id, seven_days_ago, SessionState.COMPLETED.value)).fetchone()

            # Attempt stats (hint usage)
            attempt_stats = conn.execute("""
                SELECT
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN hint_level_used > 0 THEN 1 ELSE 0 END) as hints_used,
                    SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_attempts
                FROM attempts a
                JOIN sessions s ON a.session_id = s.id
                WHERE s.student_id = ? AND a.created_at > ?
            """, (student_id, seven_days_ago)).fetchone()

            # Weak topics from attempts
            weak_topics_rows = conn.execute("""
                SELECT
                    a.topic_tag,
                    SUM(CASE WHEN a.is_correct = 1 THEN 1 ELSE 0 END) as correct,
                    COUNT(DISTINCT a.question_id) as total
                FROM attempts a
                JOIN sessions s ON a.session_id = s.id
                WHERE s.student_id = ? AND a.created_at > ?
                GROUP BY a.topic_tag
                HAVING total >= 2
            """, (student_id, seven_days_ago)).fetchall()

            # Calculate weak topics (accuracy < 60%)
            weak_topics = []
            for row in weak_topics_rows:
                accuracy = (row['correct'] / row['total'] * 100) if row['total'] > 0 else 0
                if accuracy < 60:
                    weak_topics.append({
                        "topic": row['topic_tag'],
                        "accuracy": round(accuracy, 1)
                    })

            # Sort by accuracy (worst first) and get topic names
            weak_topics.sort(key=lambda x: x['accuracy'])
            weak_topic_names = [CHAPTER_NAMES.get(t['topic'], t['topic']) for t in weak_topics]

            # Calculate metrics
            total_time = session_stats['total_time'] or 0
            total_questions = session_stats['total_questions'] or 0
            correct = session_stats['correct'] or 0
            total_attempts = attempt_stats['total_attempts'] or 0
            hints_used = attempt_stats['hints_used'] or 0

            accuracy = round((correct / total_questions) * 100, 1) if total_questions > 0 else 0
            hint_rate = round((hints_used / total_attempts) * 100, 1) if total_attempts > 0 else 0

            return {
                "student_name": student_row['name'],
                "student_id": student_id,
                "study_minutes": total_time // 60,
                "questions_attempted": total_questions,
                "accuracy": accuracy,
                "hint_usage_rate": hint_rate,
                "weak_topics": weak_topic_names,
                "session_count": session_stats['session_count'] or 0,
            }

    except Exception as e:
        print(f"Weekly stats error: {e}")
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
async def start_session(request: SessionStartRequest = None):
    """
    Start a new tutoring session with optional personalization.

    If student_id is provided, the tutor will:
    - Greet the student by name
    - Remember their weak topics
    - Suggest chapters to practice
    """
    session_id = str(uuid.uuid4())

    # Handle None request (for backward compatibility)
    if request is None:
        request = SessionStartRequest()

    # Get student context for personalization
    student_context = None
    student_id = request.student_id
    student_name = request.student_name or "there"

    if student_id:
        student_context = await async_get_student_context(student_id)
        if student_context:
            student_name = student_context['name']

    # Create session with student_id if provided
    await async_create_session(session_id, student_id=student_id)

    # Build personalized welcome message
    if student_context and student_context['is_returning']:
        # Returning student - personalized greeting
        weak = student_context['weak_topics']
        accuracy = student_context['recent_accuracy']

        if weak:
            # Has weak topics - suggest practice
            weak_topic = weak[0] if len(weak) == 1 else f"{weak[0]} and {weak[1]}"
            welcome = f"Welcome back, {student_name}! I noticed you could use more practice on {weak_topic}. Want to work on that today, or try something else?"
        elif accuracy and accuracy >= 80:
            # Doing well - celebrate and challenge
            welcome = f"Great to see you, {student_name}! You've been doing really well lately. Ready for some new challenges?"
        else:
            # Regular returning student
            welcome = f"Hello again, {student_name}! Good to have you back. Which chapter shall we practice today?"
    else:
        # New student or guest
        if student_name and student_name != "there":
            welcome = f"Hello {student_name}! I'm your math tutor. We'll practice together and I'll help you whenever you get stuck. Pick a chapter to start!"
        else:
            welcome = "Hello! I'm your math tutor. We'll practice together and I'll help you whenever you get stuck. Pick a chapter to start!"

    welcome_ssml = wrap_in_ssml(welcome)

    # Build response with recommendations
    response = {
        "session_id": session_id,
        "message": welcome,
        "ssml": welcome_ssml,
        "chapters": list(ALL_CHAPTERS.keys()),
        "chapter_names": CHAPTER_NAMES,
        "state": SessionState.IDLE.value
    }

    # Add personalization data if available
    if student_context:
        response["student_name"] = student_name
        response["weak_topics"] = student_context['weak_topics']
        response["strong_topics"] = student_context['strong_topics']
        response["recommended_chapter"] = student_context['weak_topics'][0] if student_context['weak_topics'] else None

    return response


@app.post("/api/session/chapter")
async def select_chapter(request: ChapterRequest):
    """Select a chapter for practice with personalized introduction"""
    session = await async_get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if request.chapter not in ALL_CHAPTERS:
        raise HTTPException(status_code=400, detail="Invalid chapter")

    # Get student's history with this chapter
    student_id = session.get('student_id')
    chapter_performance = None

    if student_id:
        # Check student's past performance on this chapter
        with get_db() as conn:
            chapter_performance = conn.execute("""
                SELECT
                    COUNT(*) as attempts,
                    SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct,
                    AVG(CASE WHEN is_correct = 1 THEN 100.0 ELSE 0.0 END) as accuracy
                FROM attempts a
                JOIN sessions s ON a.session_id = s.id
                WHERE s.student_id = ? AND s.chapter = ?
            """, (student_id, request.chapter)).fetchone()

    await async_update_session(
        request.session_id,
        chapter=request.chapter,
        state=SessionState.CHAPTER_SELECTED.value,
        questions_asked=[]
    )

    # Get chapter intro for a proper teaching introduction
    chapter_name = CHAPTER_NAMES[request.chapter]
    chapter_intro = CHAPTER_INTROS.get(request.chapter, "")

    # Build personalized intro based on student's chapter history
    if chapter_performance and chapter_performance['attempts'] and chapter_performance['attempts'] > 0:
        accuracy = chapter_performance['accuracy'] or 0
        attempts = chapter_performance['attempts']

        if accuracy >= 80:
            # Student is strong in this chapter
            intro_message = f"You're doing great with this chapter! Last time you got {int(accuracy)}% right. {chapter_intro} Let's try some harder ones today."
        elif accuracy >= 50:
            # Moderate performance
            intro_message = f"Good to practice this again! {chapter_intro} Let's build on what you learned last time."
        else:
            # Needs more practice
            intro_message = f"Let's work on this together. {chapter_intro} Don't worry, I'll guide you step by step."
    else:
        # First time with this chapter
        intro_message = f"Great choice! {chapter_intro} Let's start with an easy one."

    intro_ssml = wrap_in_ssml(intro_message)

    return {
        "message": intro_message,
        "ssml": intro_ssml,
        "chapter": request.chapter,
        "chapter_name": chapter_name,
        "state": SessionState.CHAPTER_SELECTED.value
    }


@app.post("/api/session/question")
async def get_next_question(request: ChapterRequest):
    """
    Get next question for the session with adaptive difficulty.

    PRD Adaptive Selection:
    - Selects questions based on current_difficulty level
    - Difficulty adjusts based on consecutive correct/wrong answers
    - Returns question with difficulty info
    """
    # Quick validation (no lock needed)
    session = await async_get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    chapter = session['chapter']
    if not chapter:
        raise HTTPException(status_code=400, detail="No chapter selected")

    questions = ALL_CHAPTERS.get(chapter, [])
    if not questions:
        raise HTTPException(status_code=400, detail="No questions available")

    # SESSION LOCK: Acquire lock to prevent race conditions with /answer
    session_lock = await get_session_lock(request.session_id)
    async with session_lock:
        # Re-fetch session inside lock (state may have changed)
        session = await async_get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        asked = json.loads(session['questions_asked'] or '[]')

        # Get current difficulty level (default to 1 = Easy)
        current_difficulty = session.get('current_difficulty') or 1

        # Use adaptive selection instead of random
        question = select_adaptive_question(
            chapter=chapter,
            asked_ids=asked,
            current_difficulty=current_difficulty,
        )

        if not question:
            # No more questions available
            closing = generate_gpt_response(TutorIntent.SESSION_END)

            return {
                "completed": True,
                "message": closing,
                "score": session['score'],
                "total": session['total']
            }

        asked.append(question['id'])
        question_number = (session['total'] or 0) + 1
        question_difficulty = question.get('difficulty', 1)

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

    # Lock released - build response
    intro_ssml = wrap_in_ssml(intro)

    return {
        "question_id": question['id'],
        "question_text": question['text'],
        "question_number": question_number,
        "intro": intro,
        "intro_ssml": intro_ssml,
        "type": question.get('type', 'text'),
        "options": question.get('options'),
        "state": SessionState.WAITING_ANSWER.value,
        # PRD: Include difficulty info
        "difficulty": question_difficulty,
        "difficulty_label": get_difficulty_label(question_difficulty),
        "target_difficulty": current_difficulty,
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
    # Quick validation checks (no lock needed)
    session = await async_get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    question = get_question_by_id(session['chapter'], session['current_question_id'])
    if not question:
        raise HTTPException(status_code=400, detail="No active question")

    # IDEMPOTENCY: Check if this exact request was already processed (no lock needed)
    # Prevents duplicate attempts on double-click or network retries
    if request.idempotency_key:
        cached_response = _check_idempotency(
            session_id=request.session_id,
            question_id=question['id'],
            client_key=request.idempotency_key,
        )
        if cached_response:
            return cached_response

    # SESSION LOCK: Acquire lock to prevent race conditions
    # This ensures only one request per session modifies state at a time
    session_lock = await get_session_lock(request.session_id)
    async with session_lock:
        # Re-fetch session inside lock (state may have changed)
        session = await async_get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        current_state = SessionState(session['state'])
        if current_state not in [SessionState.WAITING_ANSWER, SessionState.SHOWING_HINT]:
            raise HTTPException(status_code=400, detail=f"Cannot submit answer in state: {current_state.value}")

        # All session modifications happen inside this lock
        return await _process_answer(request, session, question)


async def _process_answer(request: AnswerRequest, session: dict, question: dict):
    """
    Internal function to process answer (called with session lock held).
    Extracted to keep submit_answer readable.
    """
    current_state = SessionState(session['state'])

    # PRD: Check STT confidence for voice input
    # If confidence is low, don't count as attempt - ask to repeat
    # After MAX_LOW_CONFIDENCE_STREAK failures, suggest text input
    LOW_CONFIDENCE_THRESHOLD = 0.5
    if request.is_voice_input and request.confidence is not None:
        if request.confidence < LOW_CONFIDENCE_THRESHOLD:
            # Track low confidence streak
            current_streak = (session.get('low_confidence_streak') or 0) + 1

            # Check if we should suggest text input
            if current_streak >= MAX_LOW_CONFIDENCE_STREAK:
                # Suggest text input after repeated failures
                retry_message = random.choice(TEXT_FALLBACK_MESSAGES)
                suggest_text = True
                # Reset streak after suggesting text
                new_streak = 0
            else:
                # Ask to repeat
                retry_message = random.choice(LOW_CONFIDENCE_MESSAGES)
                suggest_text = False
                new_streak = current_streak

            # Update streak in database
            await async_update_session(
                request.session_id,
                low_confidence_streak=new_streak,
            )

            retry_ssml = wrap_in_ssml(retry_message)

            return {
                "correct": False,
                "is_low_confidence": True,
                "suggest_text_input": suggest_text,
                "message": retry_message,
                "ssml": retry_ssml,
                "intent": "ask_repeat" if not suggest_text else "suggest_text",
                "score": session['score'],
                "total": session['total'],
                "attempt_count": session['attempt_count'] or 0,  # Don't increment
                "move_to_next": False,
                "state": current_state.value,
                "confidence": request.confidence,
                "low_confidence_streak": new_streak,
            }

    # Reset low confidence streak on successful voice input or text input
    if session.get('low_confidence_streak', 0) > 0:
        await async_update_session(request.session_id, low_confidence_streak=0)

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

    # PRD: Check for off-topic responses (greetings, personal questions, etc.)
    # Acknowledge briefly, redirect immediately - don't count as attempt
    off_topic_result = detect_off_topic(request.answer)
    if off_topic_result["is_off_topic"]:
        category = off_topic_result["category"]
        redirect_message = off_topic_result["redirect_message"]
        redirect_ssml = wrap_in_ssml(redirect_message)

        # SPECIAL: Handle session end request
        if category == "stop_session":
            # End the session gracefully
            await async_update_session(
                request.session_id,
                state=SessionState.COMPLETED.value,
            )
            return {
                "correct": False,
                "is_off_topic": True,
                "category": category,
                "message": redirect_message,
                "ssml": redirect_ssml,
                "intent": "session_end",
                "score": session['score'],
                "total": session['total'],
                "attempt_count": session['attempt_count'] or 0,
                "move_to_next": False,
                "completed": True,  # Signal frontend to end session
                "state": SessionState.COMPLETED.value
            }

        return {
            "correct": False,
            "is_off_topic": True,
            "category": category,
            "message": redirect_message,
            "ssml": redirect_ssml,
            "intent": "redirect_to_question",
            "score": session['score'],
            "total": session['total'],
            "attempt_count": session['attempt_count'] or 0,  # Don't increment
            "move_to_next": False,
            "state": current_state.value
        }

    # Normalize the answer for comparison and logging
    normalized_answer = normalize_spoken_input(request.answer)

    # Use enhanced evaluator (handles spoken variants like "2 by 3" → "2/3")
    is_correct = check_answer(question['answer'], request.answer)
    attempt_count = (session['attempt_count'] or 0) + 1

    # Debug logging for answer evaluation (includes byte repr for encoding issues)
    print(f"[DEBUG EVAL] Student raw: {repr(request.answer)} bytes: {request.answer.encode('utf-8')}")
    print(f"[DEBUG EVAL] Student normalized: {repr(normalized_answer)}")
    print(f"[DEBUG EVAL] Correct answer: {repr(question['answer'])} bytes: {question['answer'].encode('utf-8')}")
    print(f"[DEBUG EVAL] Result: {is_correct}")

    # Generate natural tutor response using Teacher Policy + TutorIntent layer
    # Teacher Policy diagnoses errors and chooses teaching moves
    with Timer() as tutor_timer:
        tutor_result = generate_tutor_response(
            is_correct=is_correct,
            attempt_number=attempt_count,
            question=question.get('text', ''),
            hint_1=question.get('hint', 'Think about the concept carefully.'),
            hint_2=question.get('hint_2', question.get('hint', 'Think step by step.')),
            solution=question.get('solution', f"The answer is {question['answer']}."),
            correct_answer=question['answer'],
            student_answer=request.answer,  # Pass what student actually said
            session_id=request.session_id,  # For teacher policy move tracking
        )

    # Log answer evaluation
    slog.info(
        "Answer evaluated",
        event="answer_evaluated",
        session_id=request.session_id,
        student_id=session.get('student_id'),
        question_id=question['id'],
        is_correct=is_correct,
        attempt_number=attempt_count,
        intent=tutor_result.get("intent"),
        teacher_move=tutor_result.get("teacher_move"),  # Teacher policy move
        error_type=tutor_result.get("error_type"),      # Diagnosed error
        tutor_latency_ms=tutor_timer.elapsed_ms,
        difficulty=question.get('difficulty', 1),
    )

    # Record attempt to database (PRD: attempts table)
    # hint_level_used: 0=first try, 1=after hint1, 2=after hint2, 3=solution shown
    hint_level = 0 if attempt_count == 1 else attempt_count - 1

    # Run attempt recording concurrently with other operations
    # Include debug/audit fields for debugging and analytics
    record_task = async_record_attempt(
        session_id=request.session_id,
        question_id=question['id'],
        topic_tag=session['chapter'],
        attempt_no=attempt_count,
        is_correct=is_correct,
        answer_text=request.answer,
        hint_level_used=hint_level if not is_correct else 0,
        difficulty=question.get('difficulty', 1),
        # Debug/audit fields
        raw_utterance=request.answer,  # Original input
        normalized_answer=normalized_answer,  # After normalization
        asr_confidence=request.confidence,  # STT confidence if voice input
        input_mode="voice" if request.is_voice_input else "text",
        latency_ms=round(tutor_timer.elapsed_ms),
    )

    # Get current difficulty tracking values
    current_difficulty = session.get('current_difficulty') or 1
    consecutive_correct = session.get('consecutive_correct') or 0
    consecutive_wrong = session.get('consecutive_wrong') or 0

    if is_correct:
        new_score = (session['score'] or 0) + 1
        new_correct = (session['correct_answers'] or 0) + 1

        # PRD: Adjust difficulty on correct answer (only on first attempt counts as "clean")
        # We adjust when moving to next question
        new_diff, new_consec_correct, new_consec_wrong = adjust_difficulty(
            current_difficulty=current_difficulty,
            consecutive_correct=consecutive_correct,
            consecutive_wrong=consecutive_wrong,
            is_correct=True,
        )

        # Run DB updates concurrently
        await asyncio.gather(
            record_task,
            async_update_session(
                request.session_id,
                score=new_score,
                correct_answers=new_correct,
                attempt_count=attempt_count,
                state=SessionState.SHOWING_ANSWER.value,
                current_difficulty=new_diff,
                consecutive_correct=new_consec_correct,
                consecutive_wrong=new_consec_wrong,
            )
        )

        # Check if difficulty changed
        difficulty_changed = new_diff != current_difficulty
        difficulty_message = ""
        if difficulty_changed:
            if new_diff > current_difficulty:
                difficulty_message = f" Moving up to {get_difficulty_label(new_diff)} questions!"
            else:
                difficulty_message = f" Let's try some {get_difficulty_label(new_diff)} questions."

        response = {
            "correct": True,
            "message": tutor_result["response"] + difficulty_message,
            "ssml": tutor_result.get("ssml"),
            "intent": tutor_result["intent"],
            "score": new_score,
            "total": session['total'],
            "attempt_count": attempt_count,
            "move_to_next": True,
            "state": SessionState.SHOWING_ANSWER.value,
            # PRD: Include difficulty adjustment info
            "difficulty": current_difficulty,
            "new_difficulty": new_diff,
            "difficulty_changed": difficulty_changed,
            # Teacher Policy fields
            "teacher_move": tutor_result.get("teacher_move"),
            "error_type": tutor_result.get("error_type"),
            "goal": tutor_result.get("goal"),
        }
        # Store in idempotency cache
        _store_idempotency(request.session_id, question['id'], request.idempotency_key, response)
        return response
    else:
        # Wrong answer - use TutorIntent scaffolding
        if tutor_result["move_to_next"]:
            # Attempt 3: Show solution, move on
            # PRD: Adjust difficulty on wrong answer (counts as wrong for streak)
            new_diff, new_consec_correct, new_consec_wrong = adjust_difficulty(
                current_difficulty=current_difficulty,
                consecutive_correct=consecutive_correct,
                consecutive_wrong=consecutive_wrong,
                is_correct=False,
            )

            await asyncio.gather(
                record_task,
                async_update_session(
                    request.session_id,
                    attempt_count=attempt_count,
                    state=SessionState.SHOWING_ANSWER.value,
                    current_difficulty=new_diff,
                    consecutive_correct=new_consec_correct,
                    consecutive_wrong=new_consec_wrong,
                )
            )

            # Check if difficulty changed
            difficulty_changed = new_diff != current_difficulty
            difficulty_message = ""
            if difficulty_changed and new_diff < current_difficulty:
                difficulty_message = f" Let's try some {get_difficulty_label(new_diff)} questions next."

            response = {
                "correct": False,
                "show_answer": True,
                "answer": question["answer"],
                "solution": question.get("solution", f"The answer is {question['answer']}"),
                "message": tutor_result["response"] + difficulty_message,
                "ssml": tutor_result.get("ssml"),
                "intent": tutor_result["intent"],
                "score": session['score'],
                "total": session['total'],
                "attempt_count": attempt_count,
                "move_to_next": True,
                "state": SessionState.SHOWING_ANSWER.value,
                # PRD: Include difficulty adjustment info
                "difficulty": current_difficulty,
                "new_difficulty": new_diff,
                "difficulty_changed": difficulty_changed,
                # Teacher Policy fields
                "teacher_move": tutor_result.get("teacher_move"),
                "error_type": tutor_result.get("error_type"),
                "goal": tutor_result.get("goal"),
            }
            # Store in idempotency cache
            _store_idempotency(request.session_id, question['id'], request.idempotency_key, response)
            return response
        else:
            # Attempt 1 or 2: Show hint (no difficulty adjustment yet)
            await asyncio.gather(
                record_task,
                async_update_session(
                    request.session_id,
                    attempt_count=attempt_count,
                    state=SessionState.SHOWING_HINT.value
                )
            )

            response = {
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
                "state": SessionState.SHOWING_HINT.value,
                "difficulty": current_difficulty,
                # Teacher Policy fields
                "teacher_move": tutor_result.get("teacher_move"),
                "error_type": tutor_result.get("error_type"),
                "goal": tutor_result.get("goal"),
            }
            # Store in idempotency cache
            _store_idempotency(request.session_id, question['id'], request.idempotency_key, response)
            return response


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

    # Get topic performance for summary (PRD: session summary with weak topics)
    update_task = async_update_session(
        request.session_id,
        state=SessionState.COMPLETED.value,
        duration_seconds=duration
    )
    performance_task = async_get_topic_performance(request.session_id)

    await update_task
    topic_performance = await performance_task

    # Identify weak topics from this session
    weak_topics = [
        {"topic": topic, "accuracy": data["accuracy"]}
        for topic, data in topic_performance.items()
        if data["accuracy"] < 60 and data["total"] >= 2
    ]

    # Calculate hint usage rate
    total_hints = sum(data.get("hint_usage", 0) for data in topic_performance.values())
    hint_rate = round((total_hints / total) * 100, 1) if total > 0 else 0

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
        "state": SessionState.COMPLETED.value,
        # PRD: Session summary fields
        "topic_performance": topic_performance,
        "weak_topics": weak_topics,
        "hint_usage_rate": hint_rate,
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


@app.get("/api/dashboard/{student_id}/whatsapp-summary")
async def get_whatsapp_summary(student_id: int, lang: str = "english"):
    """
    Generate WhatsApp-ready parent summary (PRD requirement).

    Returns a formatted text message suitable for WhatsApp sharing:
    - Time spent
    - Questions attempted
    - Accuracy percentage
    - Hint usage rate
    - Weak topics (top 2)
    - Next step recommendation

    Query params:
        lang: "english" (default) or "hindi"
    """
    if lang not in ["english", "hindi"]:
        lang = "english"

    # Get weekly stats with attempt data
    stats = await asyncio.to_thread(get_student_weekly_stats, student_id)

    if stats is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": "No data available",
                "message": "Student has not completed any sessions yet.",
                "message_hindi": "अभी तक कोई सत्र पूरा नहीं हुआ है।"
            }
        )

    # Generate formatted WhatsApp message
    whatsapp_text = generate_whatsapp_summary(
        student_name=stats["student_name"],
        study_minutes=stats["study_minutes"],
        questions_attempted=stats["questions_attempted"],
        accuracy=stats["accuracy"],
        hint_usage_rate=stats["hint_usage_rate"],
        weak_topics=stats["weak_topics"],
        language=lang
    )

    return {
        "success": True,
        "whatsapp_text": whatsapp_text,
        "language": lang,
        "stats": stats,
        # For easy copy-paste, also provide URL-encoded version
        "share_url": f"https://wa.me/?text={whatsapp_text.replace(' ', '%20').replace('\n', '%0A')}"
    }


@app.post("/api/dashboard/{student_id}/whatsapp-summary/voice")
async def get_whatsapp_summary_voice(student_id: int, lang: str = "english"):
    """
    Generate WhatsApp summary with TTS audio.

    Same as /whatsapp-summary but includes audio version for parents
    who prefer listening over reading.
    """
    if lang not in ["english", "hindi"]:
        lang = "english"

    stats = await asyncio.to_thread(get_student_weekly_stats, student_id)

    if stats is None:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "No data available"}
        )

    # Generate summary text
    whatsapp_text = generate_whatsapp_summary(
        student_name=stats["student_name"],
        study_minutes=stats["study_minutes"],
        questions_attempted=stats["questions_attempted"],
        accuracy=stats["accuracy"],
        hint_usage_rate=stats["hint_usage_rate"],
        weak_topics=stats["weak_topics"],
        language=lang
    )

    # Create voice-friendly version (remove emojis and markdown)
    voice_text = whatsapp_text.replace("*", "").replace("_", "")
    voice_text = voice_text.replace("📚", "").replace("⏱️", "")
    voice_text = voice_text.replace("📝", "").replace("✅", "")
    voice_text = voice_text.replace("💡", "").replace("⚠️", "")
    voice_text = voice_text.replace("👉", "").strip()

    try:
        if get_google_tts_client():
            audio_content = google_tts(voice_text)
            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        else:
            response = client.audio.speech.create(
                model="tts-1",
                voice="nova",
                speed=0.85,
                input=voice_text
            )
            audio_base64 = base64.b64encode(response.content).decode('utf-8')

        return {
            "success": True,
            "whatsapp_text": whatsapp_text,
            "audio": audio_base64,
            "language": lang,
            "stats": stats
        }

    except Exception as e:
        print(f"TTS Error: {e}")
        return {
            "success": False,
            "error": str(e),
            "whatsapp_text": whatsapp_text,
            "stats": stats
        }


# ============================================================
# VOICE ENDPOINTS
# ============================================================

def estimate_stt_confidence(text: str, segments: list = None) -> dict:
    """
    Estimate confidence of STT transcription.

    Uses multiple heuristics since Whisper doesn't provide direct confidence:
    1. Text length (very short = likely noise/unclear)
    2. Segment no_speech_prob (if available from verbose mode)
    3. Pattern detection (filler words, repeated text)

    Returns:
        dict with:
        - confidence: 0.0 to 1.0
        - is_low_confidence: True if below threshold
        - reason: Why confidence is low (if applicable)
    """
    # Thresholds
    LOW_CONFIDENCE_THRESHOLD = 0.5
    MIN_ANSWER_LENGTH = 1

    # Default confidence
    confidence = 0.85
    reason = None

    text_clean = text.strip().lower()

    # Check 1: Empty or very short
    if not text_clean:
        return {
            "confidence": 0.0,
            "is_low_confidence": True,
            "reason": "empty_response"
        }

    if len(text_clean) < MIN_ANSWER_LENGTH:
        return {
            "confidence": 0.2,
            "is_low_confidence": True,
            "reason": "too_short"
        }

    # Check 2: Only noise/filler words
    noise_patterns = [
        "um", "uh", "hmm", "ah", "oh", "er", "like",
        "you know", "i mean", "so", "well",
        "...", "huh", "what", "sorry"
    ]
    if text_clean in noise_patterns or all(word in noise_patterns for word in text_clean.split()):
        return {
            "confidence": 0.3,
            "is_low_confidence": True,
            "reason": "only_filler_words"
        }

    # Check 3: Segment-level no_speech_prob (if verbose mode)
    if segments:
        no_speech_probs = [s.get('no_speech_prob', 0) for s in segments if 'no_speech_prob' in s]
        if no_speech_probs:
            avg_no_speech = sum(no_speech_probs) / len(no_speech_probs)
            if avg_no_speech > 0.5:
                confidence = max(0.2, 1 - avg_no_speech)
                if confidence < LOW_CONFIDENCE_THRESHOLD:
                    reason = "high_noise_probability"

    # Check 4: Very long rambling response (likely not an answer)
    words = text_clean.split()
    if len(words) > 20:
        # Long responses are suspicious for math answers
        confidence = min(confidence, 0.6)
        if confidence < LOW_CONFIDENCE_THRESHOLD:
            reason = "response_too_long"

    # Check 5: Repeated text (STT duplication bug)
    if len(words) >= 4 and len(words) % 2 == 0:
        mid = len(words) // 2
        if words[:mid] == words[mid:]:
            # Detected duplication, but answer is likely valid
            confidence = 0.7  # Still acceptable but flag it

    is_low = confidence < LOW_CONFIDENCE_THRESHOLD

    return {
        "confidence": round(confidence, 2),
        "is_low_confidence": is_low,
        "reason": reason if is_low else None
    }


@app.post("/api/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """
    Convert speech to text using Whisper with confidence estimation.

    PRD: Returns confidence score to detect unclear speech.
    Low confidence responses should not count as attempts.

    Returns:
        - text: Transcribed text
        - confidence: 0.0 to 1.0
        - is_low_confidence: True if below threshold
        - reason: Why confidence is low (if applicable)
    """
    tmp_path = None
    try:
        # Read audio content
        content = await audio.read()
        audio_size_kb = len(content) / 1024

        # Check minimum audio size (very short = likely noise)
        if len(content) < 1000:  # Less than 1KB
            slog.info(
                "STT rejected: audio too short",
                event="stt_rejected",
                reason="audio_too_short",
                audio_size_kb=round(audio_size_kb, 2),
            )
            return {
                "text": "",
                "confidence": 0.0,
                "is_low_confidence": True,
                "reason": "audio_too_short",
                "retry_message": random.choice(LOW_CONFIDENCE_MESSAGES)
            }

        # Write to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Run Whisper transcription with verbose output for segment data
        def transcribe():
            with open(tmp_path, "rb") as f:
                return client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    language="en",
                    response_format="verbose_json"  # Get segment-level data
                )

        # Time the Whisper API call
        with Timer() as whisper_timer:
            transcript = await asyncio.to_thread(transcribe)

        # Extract text and segments
        text = transcript.text if hasattr(transcript, 'text') else str(transcript)
        segments = transcript.segments if hasattr(transcript, 'segments') else None

        # Estimate confidence
        confidence_result = estimate_stt_confidence(text, segments)

        # Log STT completion with details
        slog.info(
            "Whisper STT completed",
            event="stt_complete",
            latency_ms=whisper_timer.elapsed_ms,
            audio_size_kb=round(audio_size_kb, 2),
            text_length=len(text),
            confidence=confidence_result["confidence"],
            is_low_confidence=confidence_result["is_low_confidence"],
        )

        response = {
            "text": text,
            "confidence": confidence_result["confidence"],
            "is_low_confidence": confidence_result["is_low_confidence"],
        }

        # Add reason and retry message if low confidence
        if confidence_result["is_low_confidence"]:
            response["reason"] = confidence_result["reason"]
            response["retry_message"] = random.choice(LOW_CONFIDENCE_MESSAGES)

        return response

    except Exception as e:
        slog.error(
            f"STT error: {str(e)}",
            event="stt_error",
            error_type=type(e).__name__,
            error_message=str(e),
        )
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
        text_length = len(request.text)
        provider = "google" if get_google_tts_client() else "openai"

        # Use Google Cloud TTS (clearer, louder voice, supports SSML)
        with Timer() as tts_timer:
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

        # Log TTS completion
        audio_size_kb = len(audio_base64) * 3 / 4 / 1024  # Approximate decoded size
        slog.info(
            "TTS completed",
            event="tts_complete",
            provider=provider,
            latency_ms=tts_timer.elapsed_ms,
            text_length=text_length,
            audio_size_kb=round(audio_size_kb, 2),
            has_ssml=request.ssml is not None,
        )

        return {"audio": audio_base64, "format": "mp3"}

    except Exception as e:
        slog.error(
            f"TTS error: {str(e)}",
            event="tts_error",
            provider=provider if 'provider' in dir() else "unknown",
            error_type=type(e).__name__,
            error_message=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ATTEMPTS & PERFORMANCE ENDPOINTS (PRD: Topic-level tracking)
# ============================================================

@app.get("/api/session/{session_id}/attempts")
async def get_session_attempts_endpoint(session_id: str):
    """
    Get all attempts for a session.

    Returns list of attempts with:
    - question_id, topic_tag, attempt_no
    - is_correct, hint_level_used
    - answer_text, difficulty
    - created_at
    """
    session = await async_get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    attempts = await asyncio.to_thread(get_session_attempts, session_id)
    return {
        "session_id": session_id,
        "attempts": attempts,
        "total_attempts": len(attempts)
    }


@app.get("/api/session/{session_id}/performance")
async def get_session_performance(session_id: str):
    """
    Get topic-level performance breakdown for a session.

    Returns performance by topic:
    - correct count, total questions
    - hint usage, accuracy percentage
    """
    session = await async_get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    performance = await async_get_topic_performance(session_id)
    return {
        "session_id": session_id,
        "performance": performance,
        "chapter": session.get('chapter'),
        "overall_score": session.get('score', 0),
        "overall_total": session.get('total', 0)
    }


@app.get("/api/student/{student_id}/weak-topics")
async def get_student_weak_topics(student_id: int, threshold: float = 60.0):
    """
    Identify weak topics for a student (PRD: Parent summary).

    Topics with accuracy below threshold (default 60%) are flagged.

    Returns list of weak topics sorted by accuracy (worst first):
    - topic name
    - accuracy percentage
    - number of attempts
    """
    weak_topics = await async_get_weak_topics(student_id, threshold)

    # Map topic tags to readable names
    from questions import CHAPTER_NAMES
    for topic in weak_topics:
        topic['name'] = CHAPTER_NAMES.get(topic['topic'], topic['topic'])

    return {
        "student_id": student_id,
        "weak_topics": weak_topics,
        "threshold": threshold,
        "recommendation": weak_topics[0]['name'] if weak_topics else None
    }


# ============================================================
# DEBUG ENDPOINT (remove in production)
# ============================================================

@app.get("/api/debug/sessions")
async def debug_sessions():
    """Debug: List all sessions"""
    with get_db() as conn:
        rows = conn.execute("SELECT id, state, score, total, started_at FROM sessions LIMIT 20").fetchall()
    return {"sessions": [dict(r) for r in rows]}


@app.get("/api/debug/attempts")
async def debug_attempts():
    """Debug: List recent attempts"""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, session_id, question_id, topic_tag, attempt_no,
                   is_correct, hint_level_used, answer_text, created_at
            FROM attempts
            ORDER BY created_at DESC
            LIMIT 50
        """).fetchall()
    return {"attempts": [dict(r) for r in rows]}




# ============================================================
# RUN SERVER
# ============================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting IDNA EdTech server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
