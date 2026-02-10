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
NEW (Feb 7, 2026): Agentic Tutor with Tool-Based Reasoning
OLD (Deprecated): FSM + Teacher Policy + TutorIntent
```

**Agentic Architecture (Current - February 7, 2026):**
```
Student Input → Python Evaluates → Agent Picks Tool → Guardrails Check → Execute Tool → Speech
```

1. **Python evaluates answer** (deterministic) - `evaluator.py`
2. **Agent reasons about teaching move** (LLM with tools) - picks from 6 tools
3. **Guardrails override if needed** (Python) - `guardrails.py`
4. **Tool executes and generates speech** (LLM)

**Key Principle: "Agent proposes, Python disposes"**
- LLM decides WHAT to do (teaching move)
- Python decides IF it's allowed (guardrails)
- LLM decides HOW to say it (speech generation)

**6 Teaching Tools:**
| Tool | When Used |
|------|-----------|
| `give_hint` | Wrong answer - give progressive hints |
| `praise_and_continue` | Correct answer - celebrate and next question |
| `explain_solution` | After max hints - full walkthrough |
| `encourage_attempt` | Student says "I don't know" |
| `ask_what_they_did` | Wrong answer - ask before correcting (key teacher behavior!) |
| `end_session` | Student wants to stop |

**Why This Works:**
- Feels like a real teacher because agent can choose `ask_what_they_did` before correcting
- Guardrails prevent bad moves (can't explain before 2 hints, can't skip hint levels)
- Specificity Rule enforced: every response references student's actual answer

**Entry Points:**
- `server.py` - **PRODUCTION** - Agentic server with tool-based reasoning
- `web_server.py` - Legacy FSM-based server (deprecated)

## Key Files

### New Agentic Architecture (February 7, 2026)
| File | Purpose |
|------|---------|
| `server.py` | **NEW** Clean FastAPI server using AgenticTutor |
| `agentic_tutor.py` | **NEW** Main tutor brain - tool selection, execution, speech generation |
| `tutor_tools.py` | **NEW** 6 teaching tools as OpenAI function definitions |
| `tutor_prompts.py` | **NEW** System prompt + speech generation prompts |
| `guardrails.py` | **NEW** Python rules that override agent decisions |
| `context_builder.py` | **NEW** Builds context packet for agent (includes eval result) |
| `evaluator.py` | Answer evaluation - handles fractions, words, units, spoken variants |
| `questions.py` | Question bank (ALL_CHAPTERS, CHAPTER_NAMES, SKILL_LESSONS) |
| `web/index.html` | Student learning interface (updated for new API) |

### Legacy Files (Deprecated but functional)
| File | Purpose |
|------|---------|
| `web_server.py` | Old FSM-based server with all endpoints |
| `tutor_intent.py` | Old NLG layer, teaching intents |
| `teacher_policy.py` | Old error diagnosis, teaching moves |
| `demo_tutor.py` | Single-concept demo |

### Other Files
| File | Purpose |
|------|---------|
| `static/` | Static assets |
| `.claude/settings.json` | Claude Code hooks configuration |
| `.claude/hooks/` | Auto-review hook scripts |

## Claude Code Configuration

The project includes auto-review hooks in `.claude/` that enforce code quality on every edit.

### How It Works
1. **PostToolUse Hook** (`log_modified_files.sh`): Logs every file modified by Write/Edit/MultiEdit to `.claude/_state/modified_files.log`
2. **Stop Hook** (`auto_review_gate.sh`): When Claude stops, triggers an adversarial code review agent

### Code Review Rules (Enforced Automatically)
| Rule | Description |
|------|-------------|
| No vague naming | Ban `helper/utils/manager` unless domain-accurate |
| No silent defaults | No fallback for missing data unless justified |
| Domain logic placement | Tutor logic in `tutor_core/decision_engine/policy`, NOT in API handlers |
| Separation of concerns | Evaluator must not leak into tutor response generation |
| Test coverage | If behavior changed, add/update minimal tests |

### Files
```
.claude/
├── settings.json          # Hook configuration
├── hooks/
│   ├── log_modified_files.sh   # Tracks modified files
│   └── auto_review_gate.sh     # Triggers review on stop
└── _state/                # Runtime state (gitignored)
```

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

# Run NEW agentic server (recommended)
python server.py
# Opens at http://localhost:8000

# Or run OLD FSM server (legacy)
python web_server.py
```

### Quick Test (Agentic Server)
```bash
# Start session
curl -X POST http://localhost:8000/api/session/start \
  -H "Content-Type: application/json" \
  -d '{"student_name": "Test", "chapter": "rational_numbers"}'

# Submit answer
curl -X POST http://localhost:8000/api/session/input \
  -H "Content-Type: application/json" \
  -d '{"session_id": "YOUR_ID", "text": "minus 1 by 7"}'
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT, Whisper |
| `GOOGLE_APPLICATION_CREDENTIALS_JSON` | Yes | Google Cloud TTS credentials (JSON string) |
| `PORT` | No | Set automatically by Railway |

## API Endpoints

### New Agentic API (server.py) - Simplified
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chapters` | GET | List available chapters |
| `/api/session/start` | POST | Start session (returns greeting + first question) |
| `/api/session/input` | POST | Process any student input (answers, stop requests, etc.) |
| `/api/session/{id}/state` | GET | Get current session state |
| `/api/text-to-speech` | POST | Convert text to speech |
| `/api/speech-to-text` | POST | Convert speech to text with confidence |
| `/health` | GET | Health check |

**Request/Response Examples:**

Start Session:
```json
// POST /api/session/start
{"student_name": "Rahul", "chapter": "rational_numbers"}

// Response
{
  "session_id": "abc123",
  "speech": "Hi Rahul! Let's practice Ch 1. Here's your first question: What is -3/7 + 2/7?",
  "state": {"score": 0, "questions_completed": 0, ...}
}
```

Process Input:
```json
// POST /api/session/input
{"session_id": "abc123", "text": "minus 1 by 7"}

// Response (correct answer)
{
  "speech": "Bohot accha! Tumne -1/7 sahi nikala. Next question: ...",
  "state": {"score": 1, "questions_completed": 1, ...}
}

// Response (wrong answer - asks before correcting!)
{
  "speech": "Tell me, what did you do to get 5?",
  "state": {"attempt_count": 1, ...}
}
```

### Legacy API (web_server.py) - Full Featured
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/session/start` | POST | Start new session |
| `/api/session/chapter` | POST | Select chapter |
| `/api/session/question` | POST | Get next question |
| `/api/session/answer` | POST | Submit answer |
| `/api/session/end` | POST | End session |
| `/api/session/{id}/attempts` | GET | Get all attempts |
| `/api/session/{id}/performance` | GET | Topic-level performance |
| `/api/dashboard/{student_id}` | GET | Parent dashboard |
| `/api/dashboard/{student_id}/whatsapp-summary` | GET | WhatsApp summary |

### Voice APIs
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/text-to-speech` | POST | Convert text to speech (Google TTS + OpenAI fallback) |
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

## Demo

Run the single-concept tutor demo to see human-like teaching behavior:

```bash
python demo_tutor.py
```

The demo teaches adding fractions with same denominator:
1. Explains the concept step by step
2. Asks one checking question
3. Evaluates the answer (handles spoken variants like "minus 1 by 7")
4. If wrong: gives corrective feedback + one retry
5. If correct: acknowledges and ends

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

## Current State (February 7, 2026)

### Agentic Tutor Implementation - NEW

**What Changed:** Complete rebuild using tool-based agentic architecture.

**Why:** Previous approaches (FSM + Teacher Policy, Full Conversational Mode) still felt like a chatbot. The tutor would immediately correct wrong answers instead of asking "what did you do?" like a real teacher.

**New Architecture:**
```
server.py → AgenticTutor → 6 Tools → Guardrails → Speech Generation
```

**Key Files Created:**
- `agentic_tutor.py` - Main tutor brain with tool execution
- `tutor_tools.py` - 6 teaching tools as OpenAI function definitions
- `tutor_prompts.py` - System prompt + speech prompts per tool
- `guardrails.py` - Python rules that override bad agent decisions
- `context_builder.py` - Builds context with eval result for agent
- `server.py` - Clean FastAPI server using AgenticTutor

**Teacher Behavior Verified:**
```
Wrong answer → "Tell me, what did you do to get 5?"  (asks before correcting!)
Correct answer → "Bohot accha! Tumne -1/7 sahi nikala." (references their work)
IDK → "Koi baat nahi... pehla step socho" (encourages without giving answer)
```

**ChatGPT's Critique (Addressed):**
- ChatGPT said "don't skip FSM, go hybrid"
- My response: I kept Python control (guardrails.py enforces rules, evaluator.py is deterministic)
- This IS hybrid: agent proposes, Python disposes

### Deployment Status (Updated February 10, 2026)
- **Railway**: Auto-deploys from GitHub `main` branch
- **Production Server**: `server.py` (agentic tutor with 6 tools)
- **Database**: Postgres (production), SQLite (development)
- **URL**: https://idna-tutor-mvp-production.up.railway.app

**Verified Teacher Behavior in Production:**
| Input | Response |
|-------|----------|
| Wrong answer | "Tell me, what did you do to arrive at 5?" |
| Correct answer | "Bahut accha! Aapne denominator ko yaad rakha..." |
| "I don't know" | "Koi baat nahi, aap pehle step se shuru kar sakte hain" |
| Off-topic | "Hmm, let's focus on our question..." (no chatbot chat)

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

### Railway Container Shutdown Issue - FIXED (February 6, 2026)

**Problem**: Railway stops container ~5 seconds after startup despite `/health` returning 200 OK.

**Root Cause**: Startup command ran 74 tests before starting the server:
```bash
# OLD (broken):
python -m pytest tests/ -v && uvicorn web_server:app ...
```
Health check timed out while tests were running.

**Fix Applied**:
1. Removed tests from `Procfile` and `railway.toml` startup command
2. Added GitHub Actions workflow (`.github/workflows/test.yml`) for CI
3. Keep-alive task still runs as backup (pings `/health` every 30s)

```toml
# railway.toml (current - Feb 10, 2026)
startCommand = "uvicorn server:app --host 0.0.0.0 --port $PORT"
```

**Status**: ✅ FIXED - Now using agentic server (server.py) in production.

### Full Conversational Mode (February 6, 2026)

**Problem Solved:** Tutor felt scripted/robotic - responses were templated even with GPT polishing.

**Solution:** GPT now drives the conversation with full context, not predetermined moves.

**Old Approach (Deprecated):**
```
Teacher Policy → decides "PROBE" move → GPT polishes template
Result: "Tell me, what steps did you follow to solve this problem?"
```

**New Approach:**
```
GPT gets full context → generates naturally
Result: "Hmm. What did you do?"
```

**System Prompt Principles (from user's tutoring script):**
- Never say "wrong" or "incorrect" - say "Hmm." or "I see."
- When wrong, ask what they did first: "Tell me, what did you do?"
- When frustrated, validate: "That's okay." then offer choice
- Max 2 sentences (spoken aloud)
- No fake praise: "Great job!", "Excellent!", "Amazing!"

**What stays deterministic:**
- Answer evaluation (math correctness via `evaluator.py`)
- Off-topic/stop detection
- Session state tracking

**New function:** `generate_conversational_response()` in `tutor_intent.py`

**Off-topic Detection Improvements:**
- Added "the end", "that's it" to stop_session phrases
- Added spam detection: "like and subscribe", "thank you for watching"
- Added gibberish detection: long text (30+ words) without math content
- Shorter, natural redirects: "Hmm?" instead of "I didn't catch that. What's your answer to the question?"

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
8. **Health check Postgres fix** (February 2, 2026): `/health` endpoint showed "initializing" on Railway
   - Was checking `os.path.exists(DB_PATH)` for SQLite file, but Railway uses Postgres
   - Fixed: `"connected" if (USE_POSTGRES or os.path.exists(DB_PATH)) else "initializing"`

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

**Voice Quality** (TTS improvements - Updated Jan 31):
- Now using Indian English: `en-IN-Neural2-A` (warm Indian female voice)
- Settings: `speaking_rate=0.92, pitch=-0.5, volume_gain_db=3.0`
- Fallback: `en-IN-Neural2-D` (Indian male voice)
- Voice is warmer, slower, natural Indian accent for target audience

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

### Personalized Tutoring (January 31, 2026)

**Problem**: Tutor acted like a quiz master - no greeting, no context, jumped straight to questions.

**Solution**: Full personalization based on student history.

**Session Start** (`/api/session/start`):
- Accepts optional `student_id` and `student_name`
- Fetches student context: name, weak topics, strong topics, recent accuracy
- Personalized greetings:
  - New student: "Hello {name}! I'm your math tutor..."
  - Returning with weak topics: "Welcome back! I noticed you could use more practice on {topic}..."
  - Returning doing well: "Great to see you! You've been doing really well..."
- Returns `weak_topics`, `strong_topics`, `recommended_chapter` in response

**Chapter Selection** (`/api/session/chapter`):
- Checks student's past performance on selected chapter
- Personalized intro based on history:
  - First time: "Great choice! {chapter_intro} Let's start easy."
  - Strong (80%+): "You're doing great! Let's try harder ones."
  - Moderate: "Good to practice this again!"
  - Needs work: "Let's work on this together. I'll guide you."

**Chapter Introductions** (`questions.py`):
- Added `CHAPTER_INTROS` dict with explanations for all 15 chapters
- Each chapter has 2-3 sentence intro explaining what student will learn

**New Request Model**:
```python
class SessionStartRequest(BaseModel):
    student_id: Optional[int] = None
    student_name: Optional[str] = None
```

**New Function** (`get_student_context`):
```python
# Returns:
{
    "name": "Rahul",
    "weak_topics": ["fractions", "equations"],
    "strong_topics": ["squares"],
    "recent_accuracy": 72.5,
    "is_returning": True
}
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
| ~~P0~~ | ~~Railway container shutdown~~ | ~~Infrastructure~~ | ✅ FIXED - Tests moved to CI, server starts immediately |
| P1 | Cost controls | Infrastructure | STT/TTS caps, max session length, max questions/session |
| P1 | Hindi language support | Feature | Needs: Hindi TTS voice, Whisper hints, evaluator variants |
| P2 | OpenAPI spec / JSON schemas | Documentation | |
| P2 | Rate limiting per student | Infrastructure | |
| P2 | Add `answer_type` to questions | Data | numeric/yes_no/mcq routing |
| P2 | Instance ID in logs | Observability | For Railway multi-replica debugging |
| P3 | Multi-subject evaluator scaffolding | Future feature | |
| P3 | Tutor behavior test suite | Testing | |

### "Teach First" Phase (February 5, 2026)

**Problem Solved:** Tutor was a quiz bot — dumped a question, waited for answer, only taught after failure.

**Solution:** Brief deterministic concept lesson before the first question of each skill.

**Flow:**
```
Before: Question → Student answers → Wrong? → React with hints
After:  Brief lesson → Question → Student answers → React
```

**Design:**
- **Deterministic lessons** — `SKILL_LESSONS` dict in `questions.py` (31 entries), no GPT calls
- **One lesson per skill per session** — derived from `questions_asked`, no DB schema changes
- **1-2 sentences** — spoken aloud via TTS, must be brief
- **Frontend chains** — lesson TTS `onComplete` → question TTS with `autoListen`

**Files:**
| File | Change |
|------|--------|
| `questions.py` | `SKILL_LESSONS` dict (31 skill → lesson mappings) |
| `tutor_intent.py` | `generate_lesson_intro()` — returns lesson + SSML or None |
| `web_server.py` | `get_next_question()` builds `skills_already_taught`, adds lesson to response |
| `web/index.html` | `getNextQuestion()` chains lesson → question TTS |
| `tests/test_teacher_policy.py` | 3 tests: new skill, repeat skill, unknown skill |

### Teacher Policy Architecture (January 31, 2026)

**Problem Solved:** Tutor felt like a quiz master (chatbot), not a real teacher.

**Solution:** Implemented ChatGPT's recommended Teacher Policy architecture with strict P0 enforcement.

**P0 Acceptance Criteria (VERIFIED):**
| Criteria | Target | Status |
|----------|--------|--------|
| Turns end with exactly ONE question | ≥80% | ✅ PASS |
| Tutor speaks ≤2 sentences before asking | 100% | ✅ PASS |
| Moves change on 3rd wrong attempt | Always | ✅ PASS |
| Planner JSON logged for every turn | Always | ✅ PASS |

**Key Concepts:**

| Concept | Description |
|---------|-------------|
| Error Taxonomy | Diagnose WHY student got it wrong (sign_error, fraction_addition, etc.) |
| Teaching Moves | Fixed menu: Probe, Hint-Step, Worked-Example, Error-Explain, Reframe, Reveal |
| TEACH → CHECK Rule | Never teach without asking a check question in the same turn |
| 2-Pass Approach | Pass 1: Planner decides move. Pass 2: GPT renders in teacher voice |
| Repetition Breaker | If same move fails twice, force a different approach |
| Max 2 Sentences | Enforced AFTER GPT polishing - question preserved at end |

**Error Types (Math):**
- `sign_error` - Got +/- wrong
- `arithmetic_slip` - Simple calculation mistake
- `fraction_addition` - Added denominators (common error)
- `common_denominator` - Forgot to find LCD
- `word_problem_translation` - Couldn't parse word problem
- `incomplete_answer` - Didn't give proper answer

**Teaching Moves:**
1. **PROBE** - Ask diagnostic question to find misunderstanding
2. **HINT_STEP** - Give smallest next step (not the answer)
3. **WORKED_EXAMPLE** - Show similar simpler example
4. **ERROR_EXPLAIN** - Name the error and fix it
5. **REFRAME** - Explain using different representation
6. **REVEAL** - Show answer after max attempts

**Escalation Ladder (per ChatGPT feedback):**
- Attempt 1: PROBE (diagnose - locate misunderstanding)
- Attempt 2: HINT_STEP (small step based on diagnosis)
- Attempt 3: WORKED_EXAMPLE (change representation)
- Attempt 4+: REVEAL (last resort, gated)

**Warmth Policy (January 31, 2026):**
Makes the tutor feel human, not like an examiner. Uses acknowledgements, NOT fake praise.

| Warmth Level | Trigger | Example Primitives |
|--------------|---------|-------------------|
| 0 (neutral) | Fast drills | (none) |
| 1 (calm) | Default/correct | "Okay.", "Right.", "Good." |
| 2 (supportive) | Wrong answer | "Okay.", "Hmm.", "Close.", "Not quite." |
| 3 (soothing) | Frustration signals | "No worries.", "It's okay.", "Let's slow down." |

**Frustration Detection (expanded):**
- 2+ consecutive wrong answers
- Giving up phrases: "idk", "i cant", "this is hard", "confusing", "skip", "dont understand"
- Long hesitation (>30s response time)

**Primitive Repetition Tracking:**
- Tracks last 3 primitives per session
- Won't repeat same phrase within 3 turns

**Banned Phrases (removed from GPT output):**
- Fake praise: "Great job", "Excellent", "Amazing", "Well done", "You're close"
- Filler: "Absolutely", "Certainly", "Of course"
- AI tells: "As an AI...", "I can help you..."

**Example Response Flow:**
```
Before: "Great effort! You're really close! Can you try again?"
After:  "Not quite. What do you find?"
```

**API Response Fields:**
```json
{
  "teacher_move": "probe",
  "error_type": "incomplete_answer",
  "goal": "Find what student doesn't understand",
  "warmth_level": 2,
  "message": "Not quite. What do you find?"
}
```

**Files:**
- `teacher_policy.py` - Error taxonomy, teaching moves, TeacherPlanner class
- `tutor_intent.py` - Updated to use teacher policy (2-pass approach)
- `web_server.py` - Passes session_id for move tracking

### Completed Items (February 7, 2026)
| Item | Type | Implementation |
|------|------|----------------|
| **Agentic Tutor** | **Architecture** | **Complete rebuild with tool-based reasoning. Agent picks from 6 tools, guardrails.py enforces rules. Key: `ask_what_they_did` tool asks before correcting.** |
| **server.py** | **New File** | **Clean FastAPI server with simplified API: `/api/session/start`, `/api/session/input`** |
| **agentic_tutor.py** | **New File** | **AgenticTutor class - evaluates, picks tool, executes, generates speech** |
| **tutor_tools.py** | **New File** | **6 teaching tools as OpenAI function definitions** |
| **tutor_prompts.py** | **New File** | **SYSTEM_PROMPT + SPEECH_PROMPTS for each tool** |
| **guardrails.py** | **New File** | **`check_guardrails()` - Python overrides agent decisions** |
| **context_builder.py** | **New File** | **`build_context()` - includes eval result so agent doesn't decide correctness** |
| **Frontend Update** | **UI** | **Simplified to use new API, single session start call, voice features preserved** |

### Completed Items (February 6, 2026)
| Item | Type | Implementation |
|------|------|----------------|
| **Full Conversational Mode** | **Architecture** | **GPT drives tutoring with full context. No predetermined moves. System prompt from user's tutoring script. `generate_conversational_response()` in tutor_intent.py. (SUPERSEDED by Agentic Tutor)** |
| **Spam/Gibberish Detection** | **Feature** | **Detects YouTube phrases ("like and subscribe"), song lyrics, random nonsense. Short natural redirects: "Hmm?" instead of templated messages.** |
| **Stop Phrase Expansion** | **Feature** | **Added "the end", "that's it", "can we stop now" to stop_session detection.** |
| **Teach First Phase** | **Architecture** | **Tutor explains concept before first question of each skill. Deterministic lessons (no GPT) from `SKILL_LESSONS` dict (31 entries). One lesson per skill per session. Frontend chains lesson TTS → question TTS.** |
| **Banned Phrase Detection** | **Validation** | **Rejects YouTube/AI hallucinations ("subscribe", "thank you for watching") in GPT output** |
| **PROBE Skip-Polish** | **Bug** | **PROBE moves now skip GPT polishing — preserves micro_check questions verbatim** |
| **Ultra-Short Messages** | **UX** | **Removed chatbot verbosity - welcome, chapter intros, and transitions now 3-8 words max** |
| **Demo Tutor Script** | **Demo** | **`demo_tutor.py` - single concept demo showing human-like teaching (explain → check → feedback → retry)** |
| **Claude Auto-Review Hooks** | **Tooling** | **PostToolUse logs modified files, Stop hook triggers adversarial code review** |
| **Health Check Postgres Fix** | **Bug** | **`/health` now correctly reports "connected" when using Postgres** |
| **Teacher Policy** | **Architecture** | **Error diagnosis + teaching moves (ChatGPT recommendation)** |
| **Warmth Policy** | **Architecture** | **Warmth levels 0-3, acknowledgements (not fake praise)** |
| **Escalation Ladder** | **Architecture** | **probe → hint_step → worked_example → reveal** |
| **Chatbot Tell Removal** | **Architecture** | **Banned phrases removed, GPT prompt constrained** |
| **Frustration Detection** | **Feature** | **Expanded phrases: "i cant", "this is hard", "confusing"** |
| **Primitive Tracking** | **Feature** | **No repeats within 3 turns per session** |
| **Railway Keep-Alive** | **Infrastructure** | **Background task pings /health every 30s to prevent auto-sleep** |
| Indian English voice | Voice | Changed TTS to `en-IN-Neural2-A` (warm Indian female), rate 0.92 |
| Stop command handling | Feature | "let's stop", "bye", "i'm done" now end session gracefully |
| Greeting flow fix | UI | Shows welcome + chapter intro before questions |
| Auto-stop recording | UI | Silence detection (1.5s) + max 8s timeout |
| Postgres CASE WHEN fix | Bug | `is_correct = 1` for Postgres boolean compatibility |
| Personalized tutoring | Feature | Student context, weak/strong topics, personalized greetings |
| Chapter introductions | Feature | `CHAPTER_INTROS` dict with explanations for all 15 chapters |
| Deprecation fix | Code | `datetime.utcnow()` → `datetime.now(timezone.utc)` in both files |
| Audio barge-in | UI | Mic click, chat click, Escape, Spacebar all stop TTS |
| UI phase states | Enhancement | LISTENING/SPEAKING/PROCESSING with pulsing dot indicator |
| Short responses | Tutor | 30-60 token limits, no Hindi mixing, pure English |
| Embedded answer extraction | Evaluator | Extracts answer from within longer sentences |
| TTS timing | UI | Waits for audio.onended before next question |
| Disaster recovery guide | Docs | DISASTER_RECOVERY.md with full backup/restore steps |
| NCERT alignment | Questions | Updated questions.py with full chapter list |
| Sequential speech | UI | Greeting + chapter intro speak separately (faster first response) |
| **Railway Startup Fix** | **Infrastructure** | **Removed tests from startup command - server starts in 2s not 30s** |
| **GitHub Actions CI** | **Infrastructure** | **Tests run on push/PR via `.github/workflows/test.yml`** |
| **Help Request Detection** | **Feature** | **Added "didn't understand", "what is X", "explain again", ". ." detection** |
| **Frustration Patterns** | **Feature** | **Regex detection for ". .", "...", punctuation-only, hesitation sounds** |
| **Repetition Prevention** | **Feature** | **Help explanations vary: 1st=steps, 2nd=reframe, 3rd=simple, 4th=reveal** |
| **Terminology Explanations** | **Feature** | **"what is p/q" → explains specific term, not whole solution** |

---

## Session Summary (February 10, 2026)

### Production Switch to Agentic Server

**Change:** Switched production from `web_server.py` (legacy FSM) to `server.py` (agentic tutor).

**Files Updated:**
- `Procfile`: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- `railway.toml`: Same startCommand change

**Bug Fixed:** Import error in `web_server.py` - removed unused `detect_warmth_level` import.

**Verified in Production:**
```
Wrong answer → "Tell me, what did you do to arrive at 5?"
Correct → "Bahut accha! Aapne denominator ko yaad rakha..."
IDK → "Koi baat nahi, aap pehle step se shuru kar sakte hain"
Off-topic → "Hmm, let's focus on our question..." (redirects, no chat)
```

**Key Behavior:** Tutor does NOT behave like a chatbot:
- Ignores off-topic questions (just redirects to math)
- Asks "what did you do?" before correcting
- Short responses (2-3 sentences max)
- Natural Hindi-English mix

---

## Session Summary (February 7, 2026)

### Agentic Tutor - Complete Rebuild

**User's Core Problem:** Tutor didn't feel like a real teacher. Even with GPT driving, responses felt templated and chatbot-like.

**Solution:** Built new agentic architecture with tool-based reasoning.

**Key Insight:** A real teacher asks "Tell me, what did you do?" BEFORE correcting. Previous implementations jumped straight to correction.

### Files Created
| File | Purpose |
|------|---------|
| `server.py` | Clean FastAPI server with simplified API |
| `agentic_tutor.py` | AgenticTutor class - the "teacher brain" |
| `tutor_tools.py` | 6 teaching tools as OpenAI function definitions |
| `tutor_prompts.py` | SYSTEM_PROMPT + SPEECH_PROMPTS per tool |
| `guardrails.py` | `check_guardrails()` - Python overrides agent decisions |
| `context_builder.py` | `build_context()` - includes eval result so agent doesn't decide correctness |

### Architecture
```
1. Python evaluates answer (deterministic)
2. Agent picks tool from 6 options (LLM with tools)
3. Guardrails check and override if needed (Python)
4. Tool executes and generates speech (LLM)
```

### 6 Teaching Tools
- `give_hint` - Progressive hints (level 1, 2, 3)
- `praise_and_continue` - Correct answer, move to next
- `explain_solution` - Full walkthrough after max hints
- `encourage_attempt` - Student says "I don't know"
- `ask_what_they_did` - Ask before correcting (KEY!)
- `end_session` - Student wants to stop

### Guardrails (Python Enforcement)
- Can't explain before 2 hints
- Can't skip hint levels
- Session time limit (30 min)
- Max attempts per question (5)
- Can't praise wrong answer

### Frontend Updated
- Simplified from multi-step to single API calls
- `/api/session/start` returns greeting + first question
- `/api/session/input` handles all student input
- Voice features preserved (Whisper STT, Google TTS)

### ChatGPT Critique Response
ChatGPT said "don't rebuild, go hybrid." But:
- I DID keep Python control (guardrails + evaluator are deterministic)
- This IS hybrid: agent proposes teaching move, Python can override
- FSM is gone, but enforcement is stronger

### Verified Teacher Behavior
```
Correct: "Bohot accha! Tumne -1/7 sahi nikala."
Wrong:   "Tell me, what did you do to get 5?"  ← KEY!
IDK:     "Koi baat nahi... pehla step socho"
```

---

## Session Summary (February 6, 2026)

### Railway Container Shutdown - FIXED

**Root Cause:** Startup command ran 74 tests before starting server. Health check timed out.

**Fix:** Removed tests from `Procfile` and `railway.toml`, added GitHub Actions CI instead.

### Help Request Improvements - FIXED

Based on real conversation showing tutor issues:

1. **Added missing help phrases:**
   - "didn't understand" (past tense was missing)
   - "what is", "what does" (terminology questions)
   - "one more time", "explain again" (repetition requests)

2. **Frustration pattern detection:**
   - `. .`, `...`, punctuation-only responses
   - Hesitation sounds (um, uh, ah)

3. **Repetition prevention:**
   - Track `help_count` per (session_id, question_id)
   - 1st help: Standard step-by-step
   - 2nd help: Reframed with analogy
   - 3rd help: Simplest terms
   - 4th+: Reveal answer, move on

4. **Terminology questions:**
   - "what is p/q" → explains p/q notation specifically
   - Built-in dictionary for: p/q, rational, numerator, denominator, etc.

### Full Conversational Mode - IMPLEMENTED

**User feedback:** Tutor still felt scripted even with GPT polishing predetermined moves.

**Solution:** Option 2 - GPT drives the conversation with minimal guardrails.

**New function:** `generate_conversational_response()` in `tutor_intent.py`

**System prompt principles:**
- Never say "wrong" - say "Hmm." or "I see."
- Ask what they did first: "Tell me, what did you do?"
- Validate feelings: "That's okay."
- Offer choices: "Try again or stop?"
- Max 2 sentences (spoken aloud)
- No fake praise

**What stays deterministic:**
- Answer evaluation (math correctness)
- Off-topic/stop detection
- Session state tracking

**Off-topic improvements:**
- Stop phrases: "the end", "that's it", "can we stop now"
- Spam detection: "like and subscribe", "thank you for watching"
- Gibberish detection: 30+ word text without math content
- Natural redirects: "Hmm?" instead of "I didn't catch that. What's your answer to the question?"

**Files changed:**
- `tutor_intent.py`: Added `generate_conversational_response()`, `CONVERSATIONAL_TUTOR_PROMPT`, `_is_gibberish()`, spam patterns
- `web_server.py`: Switched from `generate_tutor_response` to `generate_conversational_response`

---

## Session Summary (January 31, 2026 - Evening)

### What Was Done This Session

**Goal:** Make the tutor feel like a real teacher, not a chatbot (based on ChatGPT feedback).

#### 1. Warmth Policy Implementation
- Added warmth levels 0-3 (neutral → calm → supportive → soothing)
- Warmth primitives prepended to responses (e.g., "Okay.", "Not quite.", "No worries.")
- Primitives are acknowledgements, NOT fake praise

#### 2. Chatbot Tell Removal
- Banned phrases removed: "Great job", "Excellent", "You're close", "Of course"
- GPT polishing prompt updated to avoid praise phrases
- Preserves warmth primitive at start during banned phrase removal

#### 3. Escalation Ladder Fixed
- Attempt 1: PROBE (diagnose)
- Attempt 2: HINT_STEP
- Attempt 3: WORKED_EXAMPLE
- Attempt 4+: REVEAL (gated)

#### 4. Frustration Detection Expanded
- Now detects: "idk", "i cant", "this is hard", "confusing", "skip", "dont understand"
- Triggers warmth level 3 (soothing)

#### 5. Primitive Repetition Tracking
- Tracks last 3 primitives per session
- Won't repeat same phrase within 3 turns

#### 6. Railway Keep-Alive
- Background task pings /health every 30 seconds
- Prevents Railway from auto-sleeping the container

### Files Modified
| File | Changes |
|------|---------|
| `teacher_policy.py` | Warmth levels, primitives, frustration detection, banned phrases |
| `tutor_intent.py` | GPT prompt constraints, banned phrase removal |
| `web_server.py` | Keep-alive task, session_id passing, cursor fix |
| `railway.toml` | numReplicas = 1 |
| `requirements.txt` | Added aiohttp |
| `CLAUDE.md` | Full documentation |

### Git Commits (Latest)
```
dd7a551 - Document Railway keep-alive fix
43a3caa - Add keep-alive to prevent Railway auto-sleep
b76561e - Fix Railway auto-sleep: set numReplicas = 1
3a2c07c - Update CLAUDE.md with warmth policy improvements
8f846c2 - Remove chatbot tells and improve warmth policy
c69348a - Implement warmth policy for teacher-like tutoring
```

### Next Steps (For Future Sessions)
1. **Test Railway deployment** - Check if keep-alive prevents auto-sleep
2. **Demo scenarios** - Create scripted demo per ChatGPT recommendation
3. **Parent dashboard** - Simple summary screen for parents
4. **Event logging** - For student modeling and analytics
5. **Hindi language support** - If needed for target audience

### Local Testing
```bash
cd C:\Users\User\Documents\idna
python web_server.py
# Open http://localhost:8000
```

### Production URL
Check Railway dashboard for the deployed URL.

---

## Session Summary (February 4, 2026)

### What Was Done This Session

**Goal:** Remove chatbot verbosity - make tutor sound like a real teacher.

#### 1. Ultra-Short Welcome Messages
**Before:** "Hello! I'm your math tutor. We'll practice together and I'll help you whenever you get stuck. Pick a chapter to start!"
**After:** "Hi! Pick a chapter to start."

#### 2. Ultra-Short Chapter Intros
**Before:** "Today we'll work with rational numbers. These are numbers that can be written as fractions, like 3/4 or -2/5. We'll practice adding, subtracting, and comparing them."
**After:** "Rational numbers. Let's go."

#### 3. Ultra-Short Transition Messages
**Before:** "Let's work on this together. Don't worry, I'll guide you step by step."
**After:** "I'll help."

### Files Modified
| File | Changes |
|------|---------|
| `web_server.py` | Shortened welcome messages (lines 1850-1856), chapter intro templates (lines 1923-1934) |
| `questions.py` | Shortened all `CHAPTER_INTROS` to 2-5 words each |
| `CLAUDE.md` | Updated current state and completed items |

### Design Principle
Real teachers don't give long explanations upfront. They say "Let's go" and start teaching. The tutor now follows this pattern - minimal preamble, maximum action.

