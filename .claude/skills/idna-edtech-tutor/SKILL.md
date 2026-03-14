---
name: idna-edtech-tutor
description: >
  IDNA EdTech AI voice tutor skill. Trigger for IDNA, Didi tutor, voice tutoring,
  Learn IDNA, EdTech MVP, NCERT tutoring, Sarvam TTS/STT, session flow, parent
  reports, IDNA-Bench, multi-board tutoring, AI tutors for Indian K-10 students,
  teaching flows, input classification, question banks, voice pipeline, Hinglish
  code-switching, content banks, board expansion, benchmark evaluation. Covers CBSE,
  ICSE, IB, 29+ state boards, 22 languages, Classes 6-10. Activate for FastAPI
  debugging, LLM education prompts, TTS/STT pipelines, curriculum content, schema
  migrations, Alembic, content factory, GPT-4.1 tutor prompts, GPT-4.1-mini
  classifier, SessionState, FSM transitions/handlers, verify.py, Railway deployment,
  or any app/ file. Do NOT trigger for generic FastAPI tutorials, general PostgreSQL
  questions, or Python unrelated to IDNA.
metadata:
  author: Hemant Ghosh
  version: 3.0.0
  category: edtech
  stack: python-fastapi-gpt41-gpt41mini-sarvam-postgresql-railway
  last_updated: 2026-03-14
  app_version: 10.6.7
---

# IDNA EdTech — Voice Tutor Development Skill (v3.0.0)

## 1. What is IDNA

IDNA EdTech builds "Didi" (दीदी), an AI-powered multilingual voice tutor for
Class 6-10 students across India. The tutor speaks the student's preferred language
naturally, teaches board-specific curriculum with culturally relevant Indian examples,
and guides students through problems step-by-step like a patient older sister.

India's education system: 33+ examination boards, 22 scheduled languages, 10 class
levels, 8-12 subjects per class. Realistic content matrix: 10,000-15,000 active
curriculum units.

## 2. Current Status (v10.6.7)

| Item | Status |
|------|--------|
| Version | **v10.6.7 LIVE on Railway** |
| URL | https://didi.idnaedtech.com |
| Health | /health → {"status":"ok","version":"10.6.7"} |
| Health Detail | /health/detail → question counts per level |
| Tests | **398 test functions** across 11 test files |
| Verify | **22/22 checks passing** via verify.py |
| Content | Ch 5-6 (Squares & Cubes): 84 questions (74 active), 20 skills |
| Question Levels | L1:10, L2:9, L3:14, L4:22, L5:19 |
| Languages | Hindi, English, Hinglish, Telugu |
| Phase | P0 smoke test PASSED. Pilot prep in progress. |

## 3. Architecture Principles (NON-NEGOTIABLE)

1. **FSM = skeleton, content/board/language = parameterized flesh.** New board = DATA insert, zero CODE change.
2. **bench_score gates at database level.** Nothing reaches a student below threshold.
3. **Phase gates are strict.** P0=live test (GATE) → P1=schema evolve → P2=multi-board → P3=platform → P4=device.
4. **One Didi, always.** Sarvam Bulbul v3, speaker simran, hi-IN. No TTS fallback.

## 4. Tech Stack (v10.6.x — Locked)

| Layer | Technology | Notes |
|-------|-----------|-------|
| Didi LLM | **GPT-4.1** | Teaching responses. 20% cheaper than GPT-4o. Better instruction following. |
| Classifier LLM | **GPT-4.1-mini** | Input classification (10 categories). Also used for inline answer eval. |
| STT | Sarvam Saarika v2.5 | Default language from STT_DEFAULT_LANGUAGE |
| TTS | Sarvam Bulbul v3 | Speaker: simran, hi-IN, pace 0.90, temp 0.7 |
| Backend | FastAPI (Python 3.11) | Async endpoints |
| Frontend | HTML/JS (single page) | web/student.html |
| Database | PostgreSQL (Railway managed) | Migrated from SQLite in v7.x |
| TTS Cache | PostgreSQL | Moved from filesystem in v7.5.2 |
| Hosting | Railway | Auto-deploy from GitHub main |
| Domain | didi.idnaedtech.com | GoDaddy → Railway |

## 5. Codebase Structure

```
app/
├── routers/
│   ├── student.py              # 2,028 lines. Main orchestrator. BOTH endpoints.
│   ├── auth.py                 # Login/PIN authentication
│   └── review.py               # Session review API (/review?key=idna2026)
├── tutor/
│   ├── instruction_builder.py  # 923 lines. V10 ACTIVE BRAIN — builds ALL LLM prompts.
│   ├── state_machine.py        # 447 lines. v7.3 FSM — produces Action objects. ACTIVE.
│   ├── preprocessing.py        # 494 lines. Meta-question, language switch, confusion, Telugu.
│   ├── input_classifier.py     # 407 lines. GPT-4.1-mini classifier. 10 categories.
│   ├── answer_checker.py       # 600 lines. Deterministic regex math checker (FALLBACK).
│   ├── answer_evaluator.py     # 183 lines. LLM-based answer eval (PRIMARY). Inline eval.
│   ├── memory.py               # 298 lines. Question picker (level-aware), skill tracking.
│   ├── strings.py              # 88 lines. Centralized multilingual strings (4 languages).
│   ├── enforcer.py             # 452 lines. Output safety — length, praise, repetition.
│   ├── llm.py                  # 155 lines. OpenAI API wrapper (sync + streaming).
│   ├── instruction_builder_v8.py # DEAD CODE — kept for reference only
│   └── instruction_builder_v9.py # DEAD CODE — kept for reference only
├── fsm/
│   ├── transitions.py          # v8 FSM. SIDE EFFECTS ONLY (language, empathy).
│   └── handlers.py             # v9 handlers. Side effects only.
├── content/
│   ├── ch1_square_and_cube.py  # 2,373 lines. 84 questions, 20 skills, ChapterGraph.
│   ├── seed_questions.py       # 323 lines. Merges ch1 + 10 rational number Qs (inactive).
│   └── curriculum.py           # 144 lines. Concept/ChapterGraph models.
├── voice/
│   ├── stt.py                  # Sarvam Saarika v2.5 STT                    [PROTECTED]
│   ├── tts.py                  # Sarvam Bulbul v3 TTS (simran)              [PROTECTED]
│   ├── clean_for_tts.py        # Math→words conversion, dash→comma, TTS cleanup
│   └── tts_precache.py         # TTS caching in PostgreSQL
├── state/session.py            # SessionState dataclass (v9 adapter)
├── models.py                   # 265 lines. ORM: Question, Student, Session, SessionTurn
├── database.py                 # SQLAlchemy + PostgreSQL
├── config.py                   # LLM_MODEL=gpt-4.1, MAX_WORDS=40
└── main.py                     # 394 lines. App setup, migrations, question upsert, pilot students.

web/
├── student.html                # 1,467 lines. Student UI with SSE streaming, debug output.
├── login.html                  # PIN-based login
├── parent.html                 # Parent dashboard
└── index.html                  # Landing page

tests/                          # 398 test functions across 11 files
├── test_core.py                # 101 tests — answer checking, fractions
├── test_preprocessing.py       # 84 tests — meta-Q, language, confusion
├── test_v10_persona.py         # 75 tests — persona, strings, warm identity
├── test_integration.py         # 37 tests — FSM transitions, language
├── test_p0_language_persistence.py  # 21 tests — language detection, TTS
├── test_v750_features.py       # 20 tests — sentence splitter, enforcer
├── test_p0_teaching_flow.py    # 20 tests — teaching flow, level system
├── test_ch1_square_cube.py     # 12 tests — question bank validation
├── test_p0_regression.py       # 12 tests — P0 regression
├── test_content_bank.py        # 11 tests — content bank loader
└── test_p1_fixes.py            # 5 tests — question picking, memory

verify.py                       # 22 automated checks — run before every commit
CLAUDE.md                       # Claude Code operating rules (CEO-only)
ROADMAP.md                      # Task tracker — read at session start
```

**CRITICAL:** Do NOT create `app/models/` directory — it shadows `app/models.py`.

## 6. Key Features (v10.4.0 — v10.6.7)

### 5-Level Teaching Scaffold (v10.4.0)
- **Level 1:** Multiplication recall ("What is 3 times 3?")
- **Level 2:** Square/cube numbers ("What is the square of 4?")
- **Level 3:** Square/cube roots ("What is √49?")
- **Level 4:** Patterns & properties ("Is 50 a perfect square?", "Can a square end in 7?")
- **Level 5:** Application & methods ("Find side of square with area 441", prime factorisation)
- Assessment: First question is Level 2. 3 correct in a row → level up. 2 wrong → level down.

### Inline Answer Evaluation (v10.5.1)
- Streaming endpoint combines answer eval + response into ONE LLM call
- LLM outputs `[CORRECT]` or `[INCORRECT]` prefix
- Saves ~1.3s per answer evaluation
- Fallback to regex checker if LLM doesn't follow prefix format

### Telugu Support (v10.6.4)
- `_lang()` helper for Telugu in instruction_builder (48 uses)
- Telugu language pre-scan in both endpoints
- TTS language mapping for Telugu (te-IN)
- `LANG_INSTRUCTIONS["telugu"]` with full Telugu script enforcement

### Question Picker (v10.6.0)
- Strict level-aware: `WHERE level = current_level`
- Excludes current question + all previously answered
- Falls back to adjacent levels if current level exhausted
- Reuses same-level questions (excluding current) before adjacent

### Pilot Students (v10.6.4)
- 10 accounts seeded: PINs 1001-1010 (CBSE Class 8, English medium)
- Auto-seeded on startup via `_seed_pilot_students()` in main.py

### v10.6.7 Fixes
- Hint loop death spiral fixed (inline eval respects hint progression)
- "Solution not available" text no longer leaks to students
- "Aapne poocha"/"You asked" stripped in clean_for_tts()

## 7. FSM Architecture

### Two FSMs Running in Parallel (Tech Debt)
- **v7.3 FSM** (`app/tutor/state_machine.py`): Returns `Action` objects — drives teaching flow
- **v8.0 FSM** (`app/fsm/transitions.py`): Side effects only — language storage, empathy tracking

### States: GREETING, TEACHING, WAITING_ANSWER, HINT_1, HINT_2, FULL_SOLUTION, NEXT_QUESTION, SESSION_COMPLETE

### 10 Input Categories: ACK, IDK, REPEAT, ANSWER, LANGUAGE_SWITCH, CONCEPT_REQUEST, COMFORT, STOP, TROLL, GARBLED

### Key Transitions
```
GREETING + ACK → TEACHING
TEACHING + ACK → WAITING_ANSWER (read_question)
TEACHING + IDK → TEACHING (reteach, cap at 3)
WAITING_ANSWER + ANSWER → evaluate → HINT_1 or NEXT_QUESTION
WAITING_ANSWER + IDK → HINT_1 → HINT_2 → FULL_SOLUTION
FULL_SOLUTION + any → NEXT_QUESTION (always advance)
NEXT_QUESTION → WAITING_ANSWER or SESSION_COMPLETE
```

## 8. Voice Pipeline

```
Student speaks → Sarvam STT (~300ms) → Preprocessing (meta-Q, language, confusion)
→ Classifier (GPT-4.1-mini, fast-path 0ms or LLM 500-1800ms)
→ v7.3 FSM transition → Action object → Instruction builder → GPT-4.1 (500-4200ms)
→ clean_for_tts → Sarvam TTS (3000-7000ms) → Audio to browser
```

TTS is 65-88% of total latency. Sarvam WebSocket streaming requested but not yet enabled.

## 9. Teaching Principles

1. **One idea per turn.** Never teach AND ask a question in the same turn.
2. **Indian examples.** Roti, cricket, Diwali, monsoon, laddoo, tiles.
3. **Respectful Hindi.** "Aap" form, "dekhiye", "sochiye". Never "tum".
4. **No false praise.** Never "Bahut accha!" unless answer is actually correct.
5. **Comfort first.** If frustrated, acknowledge feelings before teaching.
6. **Language respect.** Student sets language once, ALL turns respect it.
7. **Reteach cap.** Max 3 reteaches per concept. On 4th IDK, advance.
8. **Level-appropriate.** Question difficulty matches student's current level.

## 10. Development Rules

1. **Run tests after every change:** `python -m pytest tests/ -v`
2. **Run verify.py:** 22/22 checks must pass before commit
3. **Never change TTS voice.** Sarvam simran only.
4. **Never rewrite DIDI_BASE.** Append rules, don't replace.
5. **New board = data insert, zero code change.**
6. **Alembic for all schema changes.**
7. **Commit format:** `v{major}.{minor}.{patch}: brief description`
8. **One change per commit.** Atomic. Tested. Proven.
9. **Never create app/models/ directory** (shadows app/models.py).
10. **Every `_sys()` call MUST pass `session_context=ctx, question_data=q`.**

## 11. Known Issues (v10.6.7)

| Issue | Severity | Status |
|-------|----------|--------|
| TTS latency 3-7s (Sarvam REST API) | HIGH | Waiting for Sarvam streaming access |
| GPT-4.1 rephrases question text (sq_b04 "square of 8" → "square of 4") | LOW | Needs question text verbatim enforcement |

## 12. Reference Files

| File | Contents | When to read |
|------|----------|--------------|
| `references/schema-v81.md` | v8.1.0 database schema plans | Schema evolution, multi-board |
| `references/bench-spec.md` | IDNA-Bench 7 layers, thresholds | Benchmark design, quality gating |
| `references/roadmap.md` | Phase timeline, board expansion | Planning, investor context |
| `references/stack-future.md` | Phase 2-4 tech stack | Future architecture |
| `references/teaching-flow.md` | 5-level teaching scaffold design | Level system changes |
| `references/tts-pipeline.md` | TTS optimization notes | Latency work |
