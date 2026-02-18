# IDNA Tutor Architecture v7.0.2 — CLAUDE CODE RULES

## OVERVIEW

Voice-first AI math tutor for CBSE Class 8 students (India). Full rewrite with deterministic state machine — Python decides flow, LLM only generates spoken words.

**Entry point:** `uvicorn app.main:app --port 8000`
**Tests:** `python -m pytest tests/ -v` (80 tests)
**Production:** https://idna-tutor-mvp-production.up.railway.app
**Test student:** PIN `1234` (name: Priya, class 8)

## FILE STRUCTURE (v7.0.1)

```
app/
├── main.py                 → FastAPI app, lifespan, question seeding
├── config.py               → All env vars, provider selection, constants
├── database.py             → SQLAlchemy engine, session factory
├── models.py               → ORM: Student, Session, SessionTurn, Question, SkillMastery
├── routers/
│   ├── auth.py             → PIN login, JWT tokens, rate limiting
│   └── student.py          → THE MAIN LOOP: STT → classify → FSM → check → LLM → enforce → TTS
├── tutor/
│   ├── state_machine.py    → 13-state FSM. DETERMINISTIC. No LLM. (DISCOVERING_TOPIC removed)
│   ├── input_classifier.py → Classify input: ACK, IDK, ANSWER, COMFORT, SILENCE, etc. No LLM.
│   ├── answer_checker.py   → Math evaluation. Hindi/English numbers. Hindi phonetic mappings. No LLM.
│   ├── instruction_builder.py → Build LLM prompts per state+action
│   ├── enforcer.py         → 7 rules: word limits (40 max), no false praise, repetition check (70%)
│   ├── memory.py           → Skill mastery read/write, adaptive question selection
│   └── llm.py              → OpenAI GPT-4o wrapper
├── voice/
│   ├── tts.py              → Sarvam Bulbul v3 (simran voice)
│   ├── stt.py              → Sarvam Saarika v2.5 (handles Hindi-English code-mixing)
│   └── clean_for_tts.py    → Convert fractions, symbols for speech
├── content/
│   ├── seed_questions.py       → Question bank master (60 questions total)
│   └── ch1_square_and_cube.py  → Chapter 1: A Square and A Cube (50 questions)
├── ocr/                    → Homework photo extraction (scaffolded)
└── parent_engine/          → Parent voice sessions (scaffolded)

tests/
├── test_core.py            → 68 tests: answer_checker, classifier, enforcer, clean_for_tts
└── test_ch1_square_cube.py → 12 tests: new chapter question bank validation

web/
├── login.html              → PIN entry
├── student.html            → Voice tutor UI (shows transcript, logs latency)
└── parent.html             → Parent dashboard (scaffolded)
```

## STATE MACHINE (13 States — MVP)

**DISCOVERING_TOPIC removed for MVP.** Math only. Subject selection via UI buttons in future.

```
GREETING            → Welcome + first question (session starts in WAITING_ANSWER)
CHECKING_UNDERSTANDING → Probe question to assess level
TEACHING            → Explain concept with Indian examples
WAITING_ANSWER      → Student attempts question
EVALUATING          → Check answer (transient state)
HINT_1              → First hint after wrong
HINT_2              → Second hint
FULL_SOLUTION       → Walk through answer
NEXT_QUESTION       → Advance to next question
HOMEWORK_HELP       → Help with photographed homework
COMFORT             → Student is frustrated
SESSION_COMPLETE    → Wrap up and summarize
DISPUTE_REPLAY      → Student challenges verdict
```

### Universal Overrides (from ANY state)
- `STOP` → SESSION_COMPLETE
- `COMFORT` → COMFORT (stay in state, address feelings)
- `REPEAT` → Re-ask current prompt
- `SILENCE` → Gentle nudge (no LLM call)

### MVP Flow (v7.0.1)
```
Login → "Namaste {name}! Chalo math practice karte hain. Pehla sawaal: ..." → WAITING_ANSWER
                                                                                    ↓
                                                                  answer_checker.check_math_answer()
                                                                                    ↓
                                        [CORRECT] → NEXT_QUESTION → WAITING_ANSWER (loop)
                                        [INCORRECT] → HINT_1 → HINT_2 → FULL_SOLUTION → NEXT_QUESTION
```

## PIPELINE (student.py:process_message)

```
1. STT (Sarvam Saarika)         → student_text (handles Hindi-English code-mixing)
2. input_classifier             → category (ACK, IDK, ANSWER, COMFORT, SILENCE, STOP, etc.)
3. SILENCE check                → return nudge without LLM
4. state_machine.transition()   → (new_state, Action)
5. answer_checker (if ANSWER)   → Verdict (CORRECT/INCORRECT + diagnostic)
6. route_after_evaluation()     → decide HINT_1, HINT_2, or NEXT_QUESTION
7. memory.pick_next_question()  → adaptive question selection
8. instruction_builder          → LLM prompt for state+action
9. llm.generate()               → raw Didi response
10. enforcer.enforce()          → apply 7 rules, clean text
11. clean_for_tts()             → convert fractions, symbols
12. tts.synthesize()            → audio bytes
13. Save SessionTurn            → log everything
```

## ANSWER CHECKER (Deterministic, No LLM)

Handles all math answer formats:
- Fractions: `-5/9`, `2/7`, `-3/9`
- Spoken English: `minus one third`, `two over seven`
- Spoken Hindi: `minus ek tihaayi`, `do baata saat`, `aadha`
- **Hindi phonetic of English:** `नाइन` → nine, `फाइव` → five, `बाई` → by, `माइनस` → minus
- Decimals: `0.5`, `-0.333`
- With prefix: `the answer is 2/7`, `jawab hai minus 1 by 3`
- Equivalence: `2/6` = `1/3` = `0.333...`

**Diagnostic feedback:** Sign errors, wrong numerator/denominator, close but not exact.

## ENFORCER (7 Rules)

Every LLM response passes through enforcer BEFORE TTS:

1. **LENGTH** — Max 40 words, max 2 sentences (reduced for faster TTS)
2. **NO_FALSE_PRAISE** — No "shabash/bahut accha" unless verdict=CORRECT
3. **SPECIFICITY** — Must reference student's answer when evaluating
4. **NO_TEACH_AND_QUESTION** — Never teach AND ask in same turn
5. **LANGUAGE_MATCH** — Response language matches session language
6. **TTS_SAFETY** — No raw fractions, brackets that TTS reads literally
7. **NO_REPETITION** — Don't repeat previous response (70% word overlap threshold)

If enforcement fails 3x, returns safe fallback from `SAFE_FALLBACKS` dict.

## INPUT CATEGORIES

| Category | Examples | Priority |
|----------|----------|----------|
| SILENCE | "[silence]" (from frontend timer) | 0 (handled without LLM) |
| STOP | "bye", "band karo" | 1 (highest) |
| COMFORT | "bahut mushkil", "I give up" | 2 |
| DISPUTE | "maine sahi bola" | 3 |
| REPEAT | "phir se bolo" | 4 |
| HOMEWORK | "homework hai" | 5 |
| IDK | "pata nahi", "nahi samjha" | 6 |
| ACK | "haan", "samajh gaya" | 7 |
| CONCEPT | "explain karo", "kya hai" | 8 |
| ANSWER | numbers, fractions (in WAITING_ANSWER) | 9 |
| TROLL | short off-topic | 10 (lowest) |

**Note:** SUBJECT category disabled for MVP (math only).

## API ENDPOINTS

```
POST /api/auth/student          → {pin} → {token, student_id, name}
POST /api/student/session/start → Bearer token → {session_id, greeting_text, greeting_audio_b64, state}
POST /api/student/session/message → {session_id, audio|text} → {
    didi_text, didi_audio_b64, state,
    student_transcript,  # What STT heard
    verdict, diagnostic,
    stt_ms, llm_ms, tts_ms, total_ms  # Latency metrics
}
POST /api/student/session/end   → {session_id} → {summary_text, questions_attempted, questions_correct}
GET  /health                    → {status: "ok", version: "7.0.0"}
GET  /healthz                   → same (Railway health check)
```

## VOICE CONFIGURATION

### STT (Sarvam Saarika v2.5) — DEFAULT
- **Model:** saarika:v2.5
- **API:** https://api.sarvam.ai/speech-to-text
- **Language:** hi-IN (handles Hindi-English code-mixing natively)
- **Key feature:** Native code-mixed speech support — no phonetic mapping needed
- **Fallback:** Set `STT_PROVIDER=groq_whisper` if Sarvam has issues

### TTS (Sarvam Bulbul v3)
- **Speaker:** simran (warm Indian female) — DO NOT CHANGE
- **Language:** hi-IN (LOCKED — never switch mid-session)
- **Pace:** 0.90
- **Temperature:** 0.6
- **Char limit:** 2000 (truncate longer text)
- **Single call** — no chunking (v6.2.4 lesson)
- **Payload keys:** `sample_rate` (not speech_sample_rate), `audio_format: "mp3"`

### LLM (OpenAI)
- **Model:** gpt-4o
- **Max tokens:** 200
- **Temperature:** 0.3

## DATABASE MODELS

```
students        → id, name, pin, class_level, preferred_language
sessions        → id, student_id, state, subject, chapter, questions_attempted, questions_correct
session_turns   → id, session_id, turn_number, transcript, category, state_before, state_after, verdict
skill_mastery   → id, student_id, skill_key, mastery_score, attempts, correct
question_bank   → id, subject, chapter, question_text, question_voice, answer, answer_variants, hints
```

## ENVIRONMENT VARIABLES

```bash
# Required
OPENAI_API_KEY=sk-...
SARVAM_API_KEY=sk_...      # Used for BOTH TTS and STT

# Optional (has defaults)
GROQ_API_KEY=gsk_...       # Only if using groq_whisper STT

# Database (default: SQLite)
DATABASE_URL=sqlite:///idna.db

# Provider selection
STT_PROVIDER=sarvam_saarika  # DEFAULT. Options: sarvam_saarika | groq_whisper | sarvam_saaras
TTS_PROVIDER=sarvam_bulbul   # Options: sarvam_bulbul | mock (for testing)
LLM_PROVIDER=openai_gpt4o

# JWT
JWT_SECRET=change-in-production

# Database reset (use ONCE for schema migrations, then remove)
RESET_DATABASE=true  # DANGER: drops all tables on startup
```

## ARCHITECTURE RULES

### Module Boundaries (NO LLM except llm.py)
- `state_machine.py` — Pure Python. Deterministic transitions.
- `input_classifier.py` — Pure Python. Phrase matching only.
- `answer_checker.py` — Pure Python. Fraction math + Hindi phonetic mappings.
- `enforcer.py` — Pure Python. Rule application.
- `instruction_builder.py` — Builds prompts, doesn't call LLM.
- `llm.py` — ONLY file that calls OpenAI.

### Never Modify
- `app/main.py` lifespan (startup/shutdown)
- `app/routers/student.py` pipeline order
- TTS speaker (simran) — user requirement

## TEST SUITE (80 tests)

```bash
python -m pytest tests/ -v
```

| Test Class | Coverage |
|------------|----------|
| TestFractionParsing | 18 tests — Hindi/English numbers, fractions |
| TestMathAnswerChecker | 27 tests — correct, incorrect, diagnostics |
| TestInputClassifier | 14 tests — all categories |
| TestEnforcer | 4 tests — rules enforcement |
| TestCleanForTTS | 5 tests — fraction/symbol conversion |
| TestQuestionBank | 10 tests — Ch1 Square & Cube question bank |
| TestAnswerCheckerRules | 2 tests — Hindi numbers, TTS conversions |

## VERIFIED FLOWS (v7.0.1 MVP)

| Turn | Input | State Transition | Response |
|------|-------|------------------|----------|
| Start | — | GREETING → WAITING_ANSWER | "Namaste {name}! Chalo math practice. Pehla sawaal: ..." |
| 1 | "minus 5 by 9" (correct) | WAITING_ANSWER → NEXT_QUESTION | "Bilkul sahi!" + next question |
| 1 | "3" (wrong) | WAITING_ANSWER → HINT_1 | Diagnostic + hint |
| 2 | "pata nahi" | HINT_1 → HINT_2 | Second hint |
| 3 | "pata nahi" | HINT_2 → FULL_SOLUTION | Walk through solution |
| Any | "bahut mushkil" | → COMFORT | "Koi baat nahi..." |
| Any | "bye" | → SESSION_COMPLETE | Summary + goodbye |
| 15s silence | "[silence]" | Stay in state | "Aap wahan ho?" (no LLM) |

## LESSONS LEARNED

### Core Principles
- Never concatenate MP3 files — browsers stop at second header
- Lock hi-IN always — switching sounds like different person
- Clean fractions before TTS — "-3/7" becomes garbled
- Always address emotional feedback FIRST before continuing
- Never say "Bahut accha!" unless student actually answered correctly
- Keep LLM responses short (< 40 words) for faster TTS

### v7.0 Deployment (Feb 16, 2026)
- Railway needs `/healthz` endpoint (not just `/health`)
- Sarvam TTS payload: use `sample_rate` not `speech_sample_rate`
- Sarvam TTS payload: include `audio_format: "mp3"` and `temperature`
- PostgreSQL schema reset: use `DROP SCHEMA public CASCADE` (not drop_all)
- railway.toml startCommand needs `sh -c '...'` for $PORT expansion
- Procfile must match entry point: `uvicorn app.main:app`
- Seed test student on fresh database for testing

### v7.0.1 STT Fix (Feb 16, 2026)
- **Whisper can't handle Hinglish** — forces everything to one language
- **Sarvam Saarika handles code-mixed speech natively** — permanent fix
- "minus five by nine" transcribes correctly without phonetic mapping
- Keep Groq Whisper as fallback option

### v7.0.1 MVP Simplification (Feb 16, 2026)
- **Removed DISCOVERING_TOPIC** — MVP has only math, no need to ask
- Session starts directly with first question → faster time-to-value
- Subject selection will be UI buttons when Science/Hindi added
- Voice-based subject detection unreliable with Hindi/Devanagari

### Windows Development (Feb 18, 2026)
- **Python 3.14 has compatibility issues** — pydantic-core, psycopg2 fail to build
- **Use Python 3.11 explicitly:** `py -3.11 -m uvicorn app.main:app --port 8000`
- **Install deps with:** `py -3.11 -m pip install -r requirements.txt`
- Bash paths need quotes: `cd "C:/Users/User/Documents/idna"`

### v7.0.2 Content Expansion (Feb 18, 2026)
- **Added Chapter 1: A Square and A Cube** (Ganita Prakash 2025 syllabus)
- 50 new questions (easy: 16, medium: 21, hard: 13)
- 20 skill lessons with Hindi teaching content
- Added Hindi number words: ekkees (21), baees (22), tees (30), sau (100), hazaar (1000)
- TTS now handles √ (square root), ∛ (cube root), ² (ka square), ³ (ka cube)
- Total questions: 60 (10 rational numbers + 50 squares/cubes)

## GAP ANALYSIS (Phase 2 Features)

See `GAP_ANALYSIS.md` for vision alignment. Key gaps for future:
- P0: ~~Silence handling~~ ✅ Done (SILENCE category)
- P1: Full 8-step learning loop (activation, generalization, variation)
- P1: Session modes (revision, exam practice)
- P2: Student persona detection (beginner/average/advanced)
- P2: Confidence calibration (hesitation, overconfidence)
- P3: Regional behavior profiles (Hindi Belt, Telangana, etc.)
