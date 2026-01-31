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

## Adaptive Difficulty (PRD)

Questions are selected based on student performance:

| Difficulty | Label | Trigger |
|------------|-------|---------|
| 1 | Easy | Start level, or after 2 wrong in a row |
| 2 | Medium | After 3 correct in a row from Easy |
| 3 | Hard | After 3 correct in a row from Medium |

Session tracks: `current_difficulty`, `consecutive_correct`, `consecutive_wrong`

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

### Session APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chapters` | GET | List available chapters |
| `/api/session/start` | POST | Start new session |
| `/api/session/chapter` | POST | Select chapter |
| `/api/session/question` | POST | Get next question |
| `/api/session/answer` | POST | Submit answer |
| `/api/session/end` | POST | End session with performance summary |
| `/api/session/{id}/attempts` | GET | Get all attempts for session |
| `/api/session/{id}/performance` | GET | Topic-level performance breakdown |

### Parent Dashboard APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard/{student_id}` | GET | Full dashboard data |
| `/api/dashboard/{student_id}/voice-report` | POST | Dashboard with TTS audio |
| `/api/dashboard/{student_id}/whatsapp-summary` | GET | WhatsApp-ready text summary |
| `/api/dashboard/{student_id}/whatsapp-summary/voice` | POST | WhatsApp summary with TTS |
| `/api/student/{student_id}/weak-topics` | GET | Topics needing practice |

### Voice APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/text-to-speech` | POST | Convert text to speech |
| `/api/speech-to-text` | POST | Convert speech to text with confidence |
| `/health` | GET | Health check |

#### STT Response Format (with confidence)
```json
{
  "text": "two by three",
  "confidence": 0.85,
  "is_low_confidence": false
}
```
Low confidence response (< 0.5):
```json
{
  "text": "um",
  "confidence": 0.3,
  "is_low_confidence": true,
  "reason": "only_filler_words",
  "retry_message": "I didn't catch that clearly. Please say your answer again."
}
```

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
- MAX 1-2 SHORT sentences (15-25 words)
- Pure English only (no Hindi - sounds odd with English TTS)
- One idea per sentence
- Warm but brief - this is spoken aloud
- Avoid robotic transitions: "Now," "Therefore," "Next,"
- Token limits: 30 (confirm), 40 (hint), 60 (explain)

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

### Adding Postgres (recommended for production)
1. In Railway dashboard → your project → "Add Service" → "Database" → "Postgres"
2. Click the Postgres service → "Variables" → copy `DATABASE_URL`
3. In your app service → "Variables" → add `DATABASE_URL` (or link it)
4. Redeploy - the app auto-detects Postgres and uses it

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

Supports both **SQLite** (development) and **Postgres** (production).

### Configuration
| Environment Variable | Purpose |
|---------------------|---------|
| `DATABASE_URL` | Postgres connection string (takes precedence) |
| `DATABASE_PATH` | SQLite file path (default: `idna.db`) |

```bash
# Development (SQLite - default)
DATABASE_PATH=idna.db

# Production (Postgres)
DATABASE_URL=postgres://user:pass@host:5432/dbname
```

On Railway: Add Postgres plugin → `DATABASE_URL` is auto-set.

### Tables
| Table | Purpose |
|-------|---------|
| `sessions` | Active and completed tutoring sessions |
| `students` | Student profiles (name, grade, age) |
| `attempts` | Every answer attempt with topic, correctness, hints used |

### Attempts Table (PRD-compliant)
Tracks each answer submission for analytics:
```sql
attempts(id, session_id, question_id, topic_tag, attempt_no,
         is_correct, hint_level_used, answer_text, difficulty, created_at)
```

### Analytics Endpoints
| Endpoint | Purpose |
|----------|---------|
| `GET /api/session/{id}/attempts` | All attempts for a session |
| `GET /api/session/{id}/performance` | Topic-level performance breakdown |
| `GET /api/student/{id}/weak-topics` | Identify topics below 60% accuracy |

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

### Structured Logging (`web_server.py`, `tutor_intent.py`)
JSON-formatted logs for production observability:

```json
{"timestamp":"2026-01-30T12:00:00Z","level":"INFO","message":"POST /api/session/answer","event":"api_request","endpoint":"/api/session/answer","method":"POST","status_code":200,"latency_ms":245.5,"session_id":"abc123"}
```

Log events include:
- `api_request`: HTTP request completed (endpoint, method, status_code, latency_ms)
- `stt_complete`: Whisper STT finished (latency_ms, audio_size_kb, confidence)
- `tts_complete`: TTS finished (provider, latency_ms, text_length)
- `gpt_complete`: GPT response generated (intent, model, latency_ms)
- `gpt_cache_hit`: GPT response served from cache (cache_type)
- `answer_evaluated`: Student answer processed (session_id, is_correct, attempt_number)

## Important Notes

- Voice-first design: UI optimized for spoken interaction
- Target audience: Tier 2/3 Indian students (Class 8)
- Evaluator handles spoken number variants ("seven" = 7, "x equals 7" = 7)
- Sessions persist across server restarts (SQLite)

## Current State (January 31, 2026)

### Deployment Status
- **Railway**: Auto-deploys from GitHub `main` branch
- **Database**: Postgres (production), SQLite (development)
- **Latest Deploy**: Fixed Postgres migration for `attempts` table columns

### Completed
- Bug fixes (7 bugs fixed)
- Questions: 100 new questions, Science subject, MCQ support
- Performance: Response caching, async DB, reduced GPT calls
- UI: New dark mode chat interface (like Claude/ChatGPT)
- Streaming text effect for tutor messages
- LLM as brain: GPT generates natural, conversational responses
- **Attempts tracking**: PRD-compliant `attempts` table records every answer
  - Topic-level performance analytics
  - Hint usage tracking
  - Weak topic identification for parent summary
  - Session end includes performance breakdown
- **WhatsApp Parent Summary**: PRD-compliant formatted summaries
  - `/api/dashboard/{id}/whatsapp-summary` - Text summary for sharing
  - Includes: time, questions, accuracy, hints, weak topics, next step
  - Bilingual support (English/Hindi)
  - Voice version available with TTS
- **Adaptive Question Selection**: PRD-compliant difficulty adjustment
  - Questions selected based on current difficulty level (1-3)
  - 3 correct in a row → increase difficulty
  - 2 wrong in a row → decrease difficulty
  - Session tracks: `current_difficulty`, `consecutive_correct`, `consecutive_wrong`
  - API responses include difficulty info
- **STT Confidence Check**: PRD-compliant voice quality handling
  - `/api/speech-to-text` returns confidence score (0.0-1.0)
  - Low confidence (< 0.5) triggers "please repeat" without counting as attempt
  - Detects: empty audio, filler words, noise, very long responses
  - `AnswerRequest` accepts `confidence` and `is_voice_input` fields
- **Postgres Support**: Production-ready database
  - Dual-database: SQLite (dev) / Postgres (prod)
  - Auto-detects from `DATABASE_URL` environment variable
  - Connection pooling for Postgres (2-10 connections)
  - Same schema, automatic placeholder conversion (?→%s)
- **Off-topic Handling**: PRD-compliant redirect behavior
  - Detects: greetings, personal questions, weather, complaints, etc.
  - Preserves math answers (numbers, fractions, spoken variants)
  - Returns redirect message without counting as attempt
  - Category-specific responses for complaints and greetings
- **Structured Logging**: PRD-compliant observability
  - JSON-formatted logs with `timestamp`, `level`, `message`, and context
  - Request middleware logs: endpoint, method, status_code, latency_ms, session_id
  - STT logging: Whisper latency, audio size, confidence, text length
  - TTS logging: provider (Google/OpenAI), latency, text length, audio size
  - GPT logging: intent, model, latency, response length, cache hits
  - Answer evaluation logging: session_id, student_id, question_id, is_correct, attempt_number
- **Robustness Fixes** (ChatGPT gap analysis):
  - **Off-topic collision fix**: Checks for valid math answer BEFORE off-topic detection
    - "hi, it's 11 by 12" now correctly treated as answer, not off-topic
  - **Idempotency**: `/answer` endpoint supports `idempotency_key` to prevent duplicates
    - Prevents double-submit on double-click or network retries
    - 5-minute TTL cache with automatic cleanup
  - **Session locking**: Per-session asyncio locks prevent race conditions
    - Protects against overlapping `/question` and `/answer` requests
  - **Expanded attempts table**: Added debug/audit fields
    - `raw_utterance`, `normalized_answer`, `asr_confidence`, `input_mode`, `latency_ms`
  - **Low confidence streak**: Tracks consecutive low-confidence STT results
    - After 2 failures, suggests text input instead of voice
    - `suggest_text_input` flag in response

### Deployment Fixes (January 30, 2026)
Several fixes were needed for Railway deployment:
1. **Lazy asyncio.Lock init**: Can't create `asyncio.Lock()` at module level
2. **Import order**: `Dict, Tuple` must be imported before use
3. **Constant ordering**: `LOW_CONFIDENCE_MESSAGES` moved before `_process_answer`
4. **Postgres migration**: Added `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for:
   - `attempts` table: `topic_tag`, `raw_utterance`, `normalized_answer`, `asr_confidence`, `input_mode`, `latency_ms`
   - `sessions` table: `low_confidence_streak`
5. **Global exception handler**: All server errors now return JSON instead of plain text
   - Fixes "unexpected token I" error in frontend when server returns 500
   - Logs full error details (type, message, endpoint) for debugging
6. **Frontend error handling**: API function now handles both JSON and plain text errors
7. **Postgres schema mismatch**: Sessions table had wrong schema from previous deployment
   - Auto-detects missing `id` column and drops/recreates tables
   - Prevents "column does not exist" errors

### Voice & STT Improvements (January 30, 2026)

**Whisper STT Integration** (replaced browser speech recognition):
- Browser's Web Speech API was terrible at math ("- 5 - 8 / 5" instead of "-5/8")
- Now uses MediaRecorder API to capture audio as webm
- Sends audio to `/api/speech-to-text` which uses OpenAI Whisper
- Much more accurate transcription of fractions and negative numbers
- Frontend in `web/index.html`:
  ```javascript
  // MediaRecorder captures audio
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
  mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
      await sendToWhisper(audioBlob);
  };
  ```

**Voice Quality** (TTS improvements):
- Changed from `en-IN-Wavenet-A` to `en-US-Neural2-F`
- Adjusted settings: `speaking_rate=0.95, pitch=-1.0, volume_gain_db=3.0`
- Voice is now warmer and less nasal/robotic

**Answer Evaluation** (`evaluator.py`):
- Fixed negative fraction handling: "minus 1 by 7" → "-1/7"
- Added unicode minus normalization (en-dash, em-dash, minus sign → hyphen)
- Fixed space handling: "- 5 / 8" → "-5/8", "+ 5 / 8" → "5/8"
- Patterns for negative spoken fractions run BEFORE fraction conversion:
  ```python
  normalized = re.sub(r"\b(minus|negative)\s*(\d+)\s*by\s*(\d+)", r"-\2/\3", normalized)
  normalized = re.sub(r"\b(minus|negative)\s*(\d+)\s*over\s*(\d+)", r"-\2/\3", normalized)
  ```

### Tutor Personality Refinements (January 30, 2026)

**Problem**: Tutor felt robotic - responses too long, Hindi mixing sounded odd with English TTS

**Final Solution**: Strict short responses, pure English

**Current TUTOR_PERSONA** (simplified):
```python
TUTOR_PERSONA = """You are a friendly math tutor for Class 8 students in India (CBSE/NCERT).

CRITICAL RULES:
1. MAX 1-2 SHORT SENTENCES. This is spoken aloud - long responses get cut off.
2. NO Hindi words. Speak only in English.
3. Be conversational, like chatting with a student sitting next to you.
"""
```

**Token Limits** (strictly enforced):
- Confirmations: 30 tokens (was 100)
- Hints: 40 tokens (was 150)
- Explanations: 60 tokens (was 250)
- Temperature: 0.7 (was 0.9) for consistency

**Example responses**:
- Correct: "Yes! Denominators match, add the tops." (7 words)
- Hint: "Close! What's -3 plus 2?" (5 words)
- Explain: "Answer is -1/7. Add -3 and 2." (8 words)

### UI Improvements (January 30, 2026)

- **Auto-scroll fixed**: Used `requestAnimationFrame` to ensure DOM is updated before scrolling
- **Auto-listen**: Microphone automatically activates after TTS ends (300ms delay)
- **Cleaner interface**: Removed chat bubbles, avatars, and labels for distraction-free learning
- **Streamlined message display**: Direct text without decorations

### Audio Barge-in & Phase Indicators (January 30, 2026)

**Barge-in** (stop tutor when student wants to speak):
- Clicking mic button immediately stops TTS audio
- Auto-listen after TTS uses `startRecording()` which calls `stopTTS()`
- Clicking chat area while tutor speaks = stop TTS + start listening
- Pressing Escape key stops TTS and any ongoing recording
- Pressing Spacebar (when not in input) toggles voice recording

**UI Phase Indicators** (`status-bar` with pulsing dot):
- **IDLE**: No indicator
- **LISTENING**: Red pulsing dot + "Listening..."
- **SPEAKING**: Purple pulsing dot + "Speaking..."
- **PROCESSING**: Yellow pulsing dot + "Processing..."

```javascript
// Barge-in: Stop TTS immediately
function stopTTS() {
    if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
        currentAudio = null;
    }
}

// Called at start of recording
async function startRecording() {
    stopTTS(); // BARGE-IN
    // ... start MediaRecorder
}
```

### Evaluator Fix: Embedded Answer Extraction (January 30, 2026)

**Problem**: "I'm asking you, what? Two by three." marked WRONG (compared whole sentence to "2/3")

**Solution**: New `extract_answer_candidate()` function in `evaluator.py`:
```python
def extract_answer_candidate(text: str, expected_type: str = "numeric") -> Optional[str]:
    # Extracts fractions: -?\d+/\d+
    # Extracts integers: -?\d+
    # Extracts yes/no from sentences
    # Takes LAST match ("I said 5 but now 7" → 7)
```

**Now handles**:
- "I think it's 2/3" → extracts "2/3" ✓
- "Yes, zero is rational" → extracts "yes" ✓
- "umm let me think... minus 5" → extracts "-5" ✓

### TTS Timing Fix (January 30, 2026)

**Problem**: Audio cut off mid-sentence when moving to next question

**Cause**: `setTimeout(2500ms)` didn't wait for actual audio to finish

**Solution**: Use `audio.onended` callback instead:
```javascript
speak(message, ssml, {
    onComplete: () => getNextQuestion()  // Waits for audio to END
});
```

### Disaster Recovery Guide (January 30, 2026)

Created `DISASTER_RECOVERY.md` with:
- Git backup commands
- New machine setup steps
- Railway reconnection
- Environment variable list
- File overview

### Remaining Items
| Priority | Item | Type | Notes |
|----------|------|------|-------|
| P1 | Hindi language support | Feature | Needs: Hindi TTS voice, Whisper hints, evaluator variants |
| P2 | OpenAPI spec / JSON schemas | Documentation | |
| P2 | Rate limiting per student | Infrastructure | |
| P2 | Add `answer_type` to questions | Data | numeric/yes_no/mcq routing |
| P2 | Instance ID in logs | Observability | For Railway multi-replica debugging |
| P3 | Multi-subject evaluator scaffolding | Future feature | |
| P3 | Tutor behavior test suite | Testing | |

### Completed Items (January 31, 2026)
| Item | Type | Implementation |
|------|------|----------------|
| Deprecation fix | Code | `datetime.utcnow()` → `datetime.now(timezone.utc)` in `web_server.py` |
| Audio barge-in | UI | Mic click, chat click, Escape, Spacebar all stop TTS |
| UI phase states | Enhancement | LISTENING/SPEAKING/PROCESSING with pulsing dot indicator |
| Short responses | Tutor | 30-60 token limits, no Hindi mixing, pure English |
| Embedded answer extraction | Evaluator | Extracts answer from within longer sentences |
| TTS timing | UI | Waits for audio.onended before next question |
| Disaster recovery guide | Docs | DISASTER_RECOVERY.md with full backup/restore steps |
| NCERT alignment | Questions | Updated questions.py with full chapter list |
