# IDNA Tutor Architecture v7.0 — CLAUDE CODE RULES

## OVERVIEW

Voice-first AI math tutor for CBSE Class 8 students (India). Full rewrite with deterministic state machine — Python decides flow, LLM only generates spoken words.

**Entry point:** `uvicorn app.main:app --port 8000`
**Tests:** `python -m pytest tests/test_core.py -v` (69 tests)
**Production:** Railway auto-deploys from `main` branch

## FILE STRUCTURE (v7.0)

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
│   ├── state_machine.py    → 14-state FSM. DETERMINISTIC. No LLM.
│   ├── input_classifier.py → Classify input: ACK, IDK, ANSWER, COMFORT, etc. No LLM.
│   ├── answer_checker.py   → Math evaluation. Hindi/English numbers. No LLM.
│   ├── instruction_builder.py → Build LLM prompts per state+action
│   ├── enforcer.py         → 7 rules: word limits, no false praise, etc.
│   ├── memory.py           → Skill mastery read/write, adaptive question selection
│   └── llm.py              → OpenAI GPT-4o wrapper
├── voice/
│   ├── tts.py              → Sarvam Bulbul v3 (simran voice)
│   ├── stt.py              → Groq Whisper
│   └── clean_for_tts.py    → Convert fractions, symbols for speech
├── content/
│   └── seed_questions.py   → Question bank (10 questions, Ch1 Rational Numbers)
├── ocr/                    → Homework photo extraction (scaffolded)
└── parent_engine/          → Parent voice sessions (scaffolded)

tests/
└── test_core.py            → 69 tests: answer_checker, classifier, enforcer, clean_for_tts

web/
├── login.html              → PIN entry
├── student.html            → Voice tutor UI
└── parent.html             → Parent dashboard (scaffolded)
```

## STATE MACHINE (14 States)

```
GREETING            → Welcome (pre-generated)
DISCOVERING_TOPIC   → "Aaj kya padha?"
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

### Main Flow
```
GREETING → DISCOVERING_TOPIC → CHECKING_UNDERSTANDING → TEACHING → WAITING_ANSWER
                                                                        ↓
                                                              answer_checker.check_math_answer()
                                                                        ↓
                                        [CORRECT] → NEXT_QUESTION → WAITING_ANSWER (loop)
                                        [INCORRECT] → HINT_1 → HINT_2 → FULL_SOLUTION → NEXT_QUESTION
```

## PIPELINE (student.py:process_message)

```
1. STT (Groq Whisper)           → student_text
2. input_classifier             → category (ACK, IDK, ANSWER, COMFORT, STOP, etc.)
3. state_machine.transition()   → (new_state, Action)
4. answer_checker (if ANSWER)   → Verdict (CORRECT/INCORRECT + diagnostic)
5. route_after_evaluation()     → decide HINT_1, HINT_2, or NEXT_QUESTION
6. memory.pick_next_question()  → adaptive question selection
7. instruction_builder          → LLM prompt for state+action
8. llm.generate()               → raw Didi response
9. enforcer.enforce()           → apply 7 rules, clean text
10. clean_for_tts()             → convert fractions, symbols
11. tts.synthesize()            → audio bytes
12. Save SessionTurn            → log everything
```

## ANSWER CHECKER (Deterministic, No LLM)

Handles all math answer formats:
- Fractions: `-5/9`, `2/7`, `-3/9`
- Spoken English: `minus one third`, `two over seven`
- Spoken Hindi: `minus ek tihaayi`, `do baata saat`, `aadha`
- Decimals: `0.5`, `-0.333`
- With prefix: `the answer is 2/7`, `jawab hai minus 1 by 3`
- Equivalence: `2/6` = `1/3` = `0.333...`

**Diagnostic feedback:** Sign errors, wrong numerator/denominator, close but not exact.

## ENFORCER (7 Rules)

Every LLM response passes through enforcer BEFORE TTS:

1. **LENGTH** — Max 55 words, max 2 sentences
2. **NO_FALSE_PRAISE** — No "shabash/bahut accha" unless verdict=CORRECT
3. **SPECIFICITY** — Must reference student's answer when evaluating
4. **NO_TEACH_AND_QUESTION** — Never teach AND ask in same turn
5. **LANGUAGE_MATCH** — Response language matches session language
6. **TTS_SAFETY** — No raw fractions, brackets that TTS reads literally
7. **NO_REPETITION** — Don't repeat previous Didi response verbatim

If enforcement fails 3x, returns safe fallback from `SAFE_FALLBACKS` dict.

## INPUT CATEGORIES

| Category | Examples | Priority |
|----------|----------|----------|
| STOP | "bye", "band karo" | 1 (highest) |
| COMFORT | "bahut mushkil", "I give up" | 2 |
| DISPUTE | "maine sahi bola" | 3 |
| REPEAT | "phir se bolo" | 4 |
| HOMEWORK | "homework hai" | 5 |
| SUBJECT | "math padha" (in DISCOVERING_TOPIC) | 6 |
| IDK | "pata nahi", "nahi samjha" | 7 |
| ACK | "haan", "samajh gaya" | 8 |
| CONCEPT | "explain karo", "kya hai" | 9 |
| ANSWER | numbers, fractions (in WAITING_ANSWER) | 10 |
| TROLL | short off-topic | 11 (lowest) |

## API ENDPOINTS

```
POST /api/auth/student          → {pin} → {token, student_id, name}
POST /api/student/session/start → Bearer token → {session_id, greeting_text, greeting_audio_b64}
POST /api/student/session/message → {session_id, audio|text} → {didi_text, didi_audio_b64, state, verdict}
POST /api/student/session/end   → {session_id} → {summary_text, questions_attempted, questions_correct}
GET  /health                    → {status: "ok", version: "7.0.0"}
```

## VOICE CONFIGURATION

### TTS (Sarvam Bulbul v3)
- **Speaker:** simran (warm Indian female)
- **Language:** hi-IN (LOCKED — never switch mid-session)
- **Pace:** 0.90
- **Char limit:** 2000 (truncate longer text)
- **Single call** — no chunking (v6.2.4 lesson)

### STT (Groq Whisper)
- **Model:** whisper-large-v3-turbo
- **Language:** hi (force Hindi to avoid English garbage)
- **Confidence threshold:** 0.4

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
GROQ_API_KEY=gsk_...
SARVAM_API_KEY=sk_...

# Database (default: SQLite)
DATABASE_URL=sqlite:///idna.db

# Provider selection
STT_PROVIDER=groq_whisper    # or: sarvam_saarika
TTS_PROVIDER=sarvam_bulbul   # or: mock (for testing)
LLM_PROVIDER=openai_gpt4o

# JWT
JWT_SECRET=change-in-production
```

## ARCHITECTURE RULES

### Module Boundaries (NO LLM except llm.py)
- `state_machine.py` — Pure Python. Deterministic transitions.
- `input_classifier.py` — Pure Python. Phrase matching only.
- `answer_checker.py` — Pure Python. Fraction math, no external imports.
- `enforcer.py` — Pure Python. Rule application.
- `instruction_builder.py` — Builds prompts, doesn't call LLM.
- `llm.py` — ONLY file that calls OpenAI.

### Never Modify
- `app/main.py` lifespan (startup/shutdown)
- `app/routers/student.py` pipeline order
- `app/tutor/state_machine.py` state names (frontend depends on them)

## TEST SUITE (69 tests)

```bash
python -m pytest tests/test_core.py -v
```

| Test Class | Coverage |
|------------|----------|
| TestFractionParsing | 18 tests — Hindi/English numbers, fractions |
| TestMathAnswerChecker | 27 tests — correct, incorrect, diagnostics |
| TestInputClassifier | 15 tests — all categories |
| TestEnforcer | 4 tests — rules enforcement |
| TestCleanForTTS | 5 tests — fraction/symbol conversion |

## VERIFIED FLOWS

| Turn | Input | State Transition | Response |
|------|-------|------------------|----------|
| Start | — | GREETING → DISCOVERING_TOPIC | "Namaste {name}! Aaj school kaisa raha?" |
| 1 | "math padha" | DISCOVERING_TOPIC → CHECKING_UNDERSTANDING | Probe question |
| 2 | "haan" | CHECKING_UNDERSTANDING → WAITING_ANSWER | Read question |
| 3 | "minus 5 by 9" (correct) | WAITING_ANSWER → NEXT_QUESTION | "Bilkul sahi!" + next |
| 3 | "3" (wrong) | WAITING_ANSWER → HINT_1 | Diagnostic + hint |
| 4 | "pata nahi" | HINT_1 → HINT_2 | Second hint |
| 5 | "pata nahi" | HINT_2 → FULL_SOLUTION | Walk through solution |
| Any | "bahut mushkil" | → COMFORT | "Koi baat nahi..." |
| Any | "bye" | → SESSION_COMPLETE | Summary + goodbye |

## LESSONS LEARNED (Preserved from v6)

- Never concatenate MP3 files — browsers stop at second header
- Lock hi-IN always — switching sounds like different person
- Clean fractions before TTS — "-3/7" becomes garbled
- Always address emotional feedback FIRST before continuing
- Never say "Bahut accha!" unless student actually answered correctly
- Include conversation history in ALL LLM calls
- Real teachers ask "what did you do?" before correcting (but only once)
- Keep LLM responses short (< 400 chars) for natural speech
- Use Whisper AUTO-DETECT for STT, NOT forced language

## GAP ANALYSIS (Phase 2 Features)

See `GAP_ANALYSIS.md` for vision alignment. Key gaps for future:
- P0: Silence handling (15s timeout → nudge)
- P1: Full 8-step learning loop (activation, generalization, variation)
- P1: Session modes (revision, exam practice)
- P2: Student persona detection (beginner/average/advanced)
- P2: Confidence calibration (hesitation, overconfidence)
- P3: Regional behavior profiles (Hindi Belt, Telangana, etc.)
