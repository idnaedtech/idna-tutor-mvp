# CLAUDE.md - Project Guide for Claude Code

## Project Overview

**IDNA EdTech** is a voice-first AI math tutor for CBSE Class 8 students in India. It uses OpenAI (GPT-4o-mini, Whisper STT) and Google Cloud TTS to provide an interactive, spoken tutoring experience.

## Tech Stack

- **Backend:** Python 3.11, FastAPI, Pydantic
- **AI/ML:** OpenAI GPT-4o-mini, Whisper (STT), Google Cloud TTS
- **Database:** SQLite (session persistence)
- **Frontend:** HTML/CSS/JavaScript (vanilla)
- **Deployment:** Railway (Procfile + railway.toml)

## Architecture

```
Brain = FSM (flow control) + Evaluator (deterministic)
LLM = Language layer ONLY (phrasing, not judging)
TutorIntent = Teaching micro-behaviors
```

**Single Entry Point:** `web_server.py` is the only server file. No gRPC, no orchestrator.

## Key Files

| File | Purpose |
|------|---------|
| `web_server.py` | Main FastAPI app - FSM, API endpoints, TTS/STT integration |
| `tutor_intent.py` | Natural language generation, teaching intents, voice pacing |
| `questions.py` | Question bank (ALL_CHAPTERS, CHAPTER_NAMES) |
| `evaluator.py` | Answer evaluation - handles fractions, words, units, spoken variants |
| `subject_pack.py` | Subject pack management |
| `web/index.html` | Student learning interface |
| `static/` | Static assets |

## FSM States

```
IDLE → CHAPTER_SELECTED → WAITING_ANSWER → SHOWING_HINT → SHOWING_ANSWER → COMPLETED
```

## TutorIntent Types

- `ASK_FRESH` - Present new question
- `CONFIRM_CORRECT` - Celebrate right answer
- `GUIDE_THINKING` - Hint 1 (Socratic nudge)
- More intents in `tutor_intent.py`

## Development Setup

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Add: OPENAI_API_KEY=sk-...
# Add: GOOGLE_APPLICATION_CREDENTIALS_JSON=... (for Google TTS)

# Run server
python web_server.py
# Opens at http://localhost:8000
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT, Whisper |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | Yes | Google Cloud TTS credentials (JSON string) |
| `PORT` | No | Set automatically by Railway |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chapters` | GET | List available chapters |
| `/api/session/start` | POST | Start new session |
| `/api/session/chapter` | POST | Select chapter |
| `/api/session/question` | POST | Get next question |
| `/api/session/answer` | POST | Submit answer |
| `/api/session/end` | POST | End session |
| `/api/text-to-speech` | POST | Convert text to speech |
| `/api/speech-to-text` | POST | Convert speech to text |
| `/health` | GET | Health check |

## Code Patterns

### Imports from local modules
```python
from questions import ALL_CHAPTERS, CHAPTER_NAMES
from evaluator import check_answer
from tutor_intent import generate_tutor_response, TutorIntent, TutorVoice
```

### OpenAI client initialization
```python
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=30.0,
    max_retries=2
)
```

### TutorIntent voice principles
- Max 2 sentences per turn (voice pacing)
- One idea per sentence
- Warm, encouraging tone
- Casual Hindi words allowed: "accha", "haan", "theek", "sahi"
- Avoid robotic transitions: "Now," "Therefore," "Next,"

## Testing

```bash
python test_api.py
```

## Deployment (Railway)

```bash
railway login
railway init
railway variables set OPENAI_API_KEY=sk-...
railway up
```

## Common Tasks

### Adding new questions
Edit `questions.py` - follow the existing question format:
```python
{
    "id": "chapter_001",
    "text": "Question text here",
    "answer": "correct_answer",
    "hint": "Hint to help the student",
    "solution": "Step-by-step solution explanation",
    "difficulty": 1  # 1-3 scale
}
```

### Modifying tutor personality
Edit `TUTOR_PERSONA` in `tutor_intent.py`.

### Adding new FSM states
Modify the `SessionState` enum and transition logic in `web_server.py`.

## Database

SQLite database (`idna.db`) stores sessions. Schema managed in `web_server.py`.

## Performance Optimizations

The codebase includes several performance optimizations:

### Response Caching (`tutor_intent.py`)
- **Pre-cached responses**: Common intents (SESSION_START, SESSION_END, MOVE_ON, CONFIRM_CORRECT) use pre-generated responses instead of GPT calls
- **GPT response cache**: Time-based cache (5 min TTL) for question-specific GPT responses
- **SSML caching**: LRU cache (256 entries) for SSML generation with time-bucketed seeds

### Async Database (`web_server.py`)
- **Thread pool execution**: SQLite operations run via `asyncio.to_thread()` to avoid blocking the event loop
- **Async wrappers**: `async_get_session()`, `async_update_session()`, `async_create_session()`

### API Optimizations
- **Cached chapters list**: Static data cached with `@lru_cache`
- **Reduced GPT calls**: Move-on transitions use cached responses (saves 1 GPT call per question)
- **Reduced timeouts**: OpenAI client uses 15s timeout with 1 retry (fail fast, use fallback)

### Voice Endpoint Improvements
- **STT temp file cleanup**: Always cleaned up in `finally` block
- **Concurrent operations**: DB updates and GPT calls run concurrently where possible

## Important Notes

- Voice-first design: UI optimized for spoken interaction
- Target audience: Tier 2/3 Indian students (Class 8)
- Evaluator handles spoken number variants ("seven" = 7, "x equals 7" = 7)
- Sessions persist across server restarts (SQLite)
