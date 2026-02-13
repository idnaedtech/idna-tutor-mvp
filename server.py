"""
IDNA Web Server - Clean Agentic Implementation
==============================================
Simple FastAPI server using the AgenticTutor.
"""

import os
import sys
import asyncio
import json
import time
import base64
import random
import tempfile
from typing import Optional

# Fix Windows console encoding for Hindi text
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import requests as http_requests  # For Sarvam TTS API calls

# Load environment variables
load_dotenv()

from agentic_tutor import AgenticTutor
from questions import CHAPTER_NAMES


# ============================================================
# Timer & Helpers
# ============================================================

class Timer:
    """Context manager for timing operations."""
    def __init__(self):
        self.start_time = None
        self.elapsed_ms = 0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = round((time.perf_counter() - self.start_time) * 1000, 2)


LOW_CONFIDENCE_MESSAGES = [
    "I didn't catch that clearly. Please say your answer again.",
    "Sorry, I couldn't hear you properly. Can you repeat that?",
    "I'm not sure I understood. Please say your answer once more.",
]


# ============================================================
# OpenAI & Google TTS & Groq STT Clients
# ============================================================

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=30.0,
    max_retries=2
)

# Groq client for Whisper STT (faster & cheaper)
groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
    timeout=30.0,
    max_retries=2
)





# ============================================================
# Sarvam TTS (Bulbul v3) — v6.0.5
# ============================================================

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
# v6.0.5: Voice warmth testing
# Test on dashboard.sarvam.ai with this text:
# "Bahut accha beta! Aapne bilkul sahi jawab diya. Minus 3 plus 2 equals minus 1.
#  Denominator same rehta hai: 7. Toh answer hai minus 1 over 7. Ab agla sawal dekhte hain."
#
# Try these speakers and pick the warmest:
#   Female: priya, kavya, neha, pooja, shreya, ishita, simran, roopa, rupali, suhani
#   Recommended to test: kavya (often warmer than priya), shreya (clear), simran (expressive)
SARVAM_SPEAKER = "priya"   # CHANGE after testing — try kavya, shreya, simran
SARVAM_PACE = 0.90


def detect_hindi_ratio(text: str) -> float:
    """Detect what fraction of text is Hindi/Devanagari vs English.
    Returns 0.0 (all English) to 1.0 (all Hindi).
    """
    import re as re_mod

    if not text:
        return 0.0

    # Count Devanagari characters (Unicode range 0900-097F)
    devanagari_chars = len(re_mod.findall(r'[\u0900-\u097F]', text))

    # Count common Hindi words written in Roman script (Hinglish)
    hindi_roman_words = [
        'aap', 'hain', 'hai', 'toh', 'kya', 'nahi', 'aur', 'yeh', 'woh',
        'mein', 'ke', 'ka', 'ki', 'ko', 'se', 'par', 'bhi', 'hum',
        'karo', 'karte', 'hota', 'dekho', 'dekhiye', 'sochiye', 'bataiye',
        'accha', 'theek', 'bilkul', 'sahi', 'samajh', 'samjha', 'samjho',
        'chaliye', 'kariye', 'suniye', 'padhenge', 'seekhte', 'beta',
        'bahut', 'agar', 'jaise', 'matlab', 'kyunki', 'isliye',
        'namaste', 'dhyan', 'galti', 'jawab', 'sawal',
    ]
    words = text.lower().split()
    if not words:
        return 0.0

    hindi_word_count = sum(1 for w in words if w.strip('.,!?') in hindi_roman_words)

    # If any Devanagari, it's definitely Hindi-heavy
    if devanagari_chars > 5:
        return 0.8

    # Ratio of Hindi words to total words
    ratio = hindi_word_count / len(words)
    return min(ratio * 2.0, 1.0)  # Scale up since many content words are English in Hinglish


def sarvam_tts(text: str) -> bytes:
    """Generate speech using Sarvam Bulbul v3 TTS.

    Returns MP3 audio bytes.
    NEVER falls back to a different TTS engine — that would change Didi's voice mid-session.
    If Sarvam fails, we retry with shorter text. If still fails, raise an error.
    """
    # Sarvam v3 REST limit: 2500 chars — truncate aggressively to avoid hitting it
    if len(text) > 2000:
        truncated = text[:2000]
        last_period = max(truncated.rfind('.'), truncated.rfind('?'), truncated.rfind('!'))
        if last_period > 500:
            text = truncated[:last_period + 1]
            print(f"[TTS] Text truncated to {len(text)} chars at sentence boundary")

    # Detect language to set correct prosody
    hindi_ratio = detect_hindi_ratio(text)
    lang_code = "hi-IN" if hindi_ratio > 0.25 else "en-IN"

    payload = {
        "inputs": [text],
        "target_language_code": lang_code,
        "speaker": SARVAM_SPEAKER,
        "model": "bulbul:v3",
        "pace": SARVAM_PACE,
        "temperature": 0.7,
        "enable_preprocessing": True,
        "audio_format": "mp3",
        "sample_rate": 24000,
    }

    headers = {
        "Content-Type": "application/json",
        "api-subscription-key": SARVAM_API_KEY,
    }

    try:
        response = http_requests.post(
            SARVAM_TTS_URL,
            json=payload,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        audio_base64 = data["audios"][0]
        audio_bytes = base64.b64decode(audio_base64)
        print(f"[Sarvam TTS] OK: {len(audio_bytes)} bytes, {len(text)} chars, speaker={SARVAM_SPEAKER}, lang={lang_code}, hindi={hindi_ratio:.2f}")
        return audio_bytes

    except Exception as e:
        print(f"[Sarvam TTS] First attempt failed: {e}")

        # RETRY with shorter text — do NOT switch to a different voice
        if len(text) > 500:
            short_text = text[:500]
            last_period = max(short_text.rfind('.'), short_text.rfind('?'), short_text.rfind('!'))
            if last_period > 100:
                short_text = short_text[:last_period + 1]

            try:
                payload["inputs"] = [short_text]
                response = http_requests.post(
                    SARVAM_TTS_URL,
                    json=payload,
                    headers=headers,
                    timeout=15
                )
                response.raise_for_status()
                data = response.json()
                audio_bytes = base64.b64decode(data["audios"][0])
                print(f"[Sarvam TTS] Retry OK: {len(audio_bytes)} bytes, truncated to {len(short_text)} chars")
                return audio_bytes
            except Exception as retry_error:
                print(f"[Sarvam TTS] Retry also failed: {retry_error}")

        # Last resort: generate a short error message in Sarvam voice
        try:
            error_text = "Ek minute beta, thoda technical problem aa raha hai. Ek baar phir try karte hain."
            payload["inputs"] = [error_text]
            response = http_requests.post(
                SARVAM_TTS_URL,
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return base64.b64decode(data["audios"][0])
        except Exception:
            # Absolute last resort — raise error, don't switch voice
            raise Exception(f"Sarvam TTS failed after retries: {e}")


def estimate_stt_confidence(text: str, segments: list = None) -> dict:
    """Estimate confidence of STT transcription."""
    confidence = 0.85
    reason = None
    text_clean = text.strip().lower()

    if not text_clean:
        return {"confidence": 0.0, "is_low_confidence": True, "reason": "empty_response"}

    if len(text_clean) < 1:
        return {"confidence": 0.2, "is_low_confidence": True, "reason": "too_short"}

    noise_patterns = ["um", "uh", "hmm", "ah", "oh", "er", "like", "...", "huh", "what"]
    if text_clean in noise_patterns:
        return {"confidence": 0.3, "is_low_confidence": True, "reason": "only_filler_words"}

    if segments:
        no_speech_probs = [s.get('no_speech_prob', 0) for s in segments if 'no_speech_prob' in s]
        if no_speech_probs:
            avg_no_speech = sum(no_speech_probs) / len(no_speech_probs)
            if avg_no_speech > 0.5:
                confidence = max(0.2, 1 - avg_no_speech)
                if confidence < 0.5:
                    reason = "high_noise_probability"

    words = text_clean.split()
    if len(words) > 20:
        confidence = min(confidence, 0.6)
        if confidence < 0.5:
            reason = "response_too_long"

    return {
        "confidence": round(confidence, 2),
        "is_low_confidence": confidence < 0.5,
        "reason": reason if confidence < 0.5 else None
    }

app = FastAPI(title="IDNA EdTech Tutor")

# Active sessions (in-memory for now)
sessions: dict[str, AgenticTutor] = {}


# ============================================================
# Request/Response Models
# ============================================================

class StartSessionRequest(BaseModel):
    student_name: str = ""  # v5.0: Never default to "Student"
    chapter: str = "rational_numbers"


class InputRequest(BaseModel):
    session_id: str
    text: str


class SessionResponse(BaseModel):
    session_id: str
    speech: str
    state: dict


# ============================================================
# API Endpoints
# ============================================================

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "idna-tutor"}


@app.get("/api/chapters")
async def get_chapters():
    """List available chapters."""
    return {
        "chapters": [
            {"id": key, "name": value}
            for key, value in CHAPTER_NAMES.items()
        ]
    }


@app.post("/api/session/start")
async def start_session(request: StartSessionRequest) -> SessionResponse:
    """Start a new tutoring session."""
    import uuid

    session_id = str(uuid.uuid4())[:8]

    # Create tutor instance
    tutor = AgenticTutor(
        student_name=request.student_name,
        chapter=request.chapter
    )

    # Store session
    sessions[session_id] = tutor

    # Get opening message
    speech = await tutor.start_session()

    return SessionResponse(
        session_id=session_id,
        speech=speech,
        state=tutor.get_session_state()
    )


@app.post("/api/session/input")
async def process_input(request: InputRequest) -> SessionResponse:
    """Process student input and get tutor response."""
    tutor = sessions.get(request.session_id)

    if not tutor:
        raise HTTPException(status_code=404, detail="Session not found")

    # Process input through agentic tutor
    speech = await tutor.process_input(request.text)

    return SessionResponse(
        session_id=request.session_id,
        speech=speech,
        state=tutor.get_session_state()
    )


@app.get("/api/session/{session_id}/state")
async def get_session_state(session_id: str):
    """Get current session state."""
    tutor = sessions.get(session_id)

    if not tutor:
        raise HTTPException(status_code=404, detail="Session not found")

    return tutor.get_session_state()


# ============================================================
# Voice Endpoints (TTS & STT)
# ============================================================

class TextToSpeechRequest(BaseModel):
    text: str
    voice: str = "nova"
    ssml: Optional[str] = None


@app.post("/api/text-to-speech")
async def text_to_speech(request: TextToSpeechRequest):
    """Convert text to speech using Sarvam Bulbul v3."""
    try:
        with Timer() as tts_timer:
            audio_content = sarvam_tts(text=request.text)
            audio_base64 = base64.b64encode(audio_content).decode('utf-8')

        print(f"TTS completed in {tts_timer.elapsed_ms}ms")
        return {"audio": audio_base64, "format": "mp3"}

    except Exception as e:
        print(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """Convert speech to text using Whisper."""
    tmp_path = None
    try:
        content = await audio.read()

        if len(content) < 1000:
            return {
                "text": "",
                "confidence": 0.0,
                "is_low_confidence": True,
                "reason": "audio_too_short",
                "retry_message": random.choice(LOW_CONFIDENCE_MESSAGES)
            }

        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        def transcribe():
            with open(tmp_path, "rb") as f:
                return groq_client.audio.transcriptions.create(
                    model="whisper-large-v3-turbo",
                    file=f,
                    response_format="verbose_json"
                )

        # v4.8: Simple auto-detect (no language parameter)
        with Timer() as whisper_timer:
            transcript = await asyncio.to_thread(transcribe)

        text = transcript.text if hasattr(transcript, 'text') else str(transcript)
        segments = transcript.segments if hasattr(transcript, 'segments') else None

        confidence_result = estimate_stt_confidence(text, segments)

        print(f"STT completed in {whisper_timer.elapsed_ms}ms: '{text[:50]}...'")

        response = {
            "text": text,
            "confidence": confidence_result["confidence"],
            "is_low_confidence": confidence_result["is_low_confidence"],
        }

        if confidence_result["is_low_confidence"]:
            response["reason"] = confidence_result["reason"]
            response["retry_message"] = random.choice(LOW_CONFIDENCE_MESSAGES)

        return response

    except Exception as e:
        print(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


# ============================================================
# Static Files & Frontend
# ============================================================

# Serve static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
if os.path.exists("web"):
    app.mount("/web", StaticFiles(directory="web"), name="web")


@app.get("/")
async def root():
    """Serve the frontend."""
    if os.path.exists("web/index.html"):
        return FileResponse("web/index.html")
    return {"message": "IDNA Tutor API. Frontend not found."}


@app.get("/student")
async def student_page():
    """Student learning page - legacy route."""
    if os.path.exists("web/index.html"):
        return FileResponse("web/index.html")
    return {"message": "Frontend not found."}


# ============================================================
# Cleanup old sessions (simple)
# ============================================================

@app.on_event("startup")
async def startup():
    """Cleanup task on startup."""
    print("IDNA Agentic Tutor Server starting...")
    print(f"Available chapters: {list(CHAPTER_NAMES.keys())}")


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    print(f"Starting server on port {port}...")

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
