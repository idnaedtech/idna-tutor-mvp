---
name: idna-edtech-tutor
description: >
  IDNA EdTech AI voice tutor skill. Trigger when user mentions IDNA, Didi tutor,
  voice tutoring, Learn IDNA, EdTech MVP, NCERT tutoring, Sarvam TTS/STT, agentic
  tutor, session flow, parent reports, IDNA-Bench, multi-board tutoring, or building
  AI tutors for Indian K-10 students. Also trigger for teaching flows, input
  classification, question banks, voice pipeline, Hinglish code-switching, content
  banks, board expansion, benchmark evaluation, NCERT/state board subjects. Covers
  all boards (CBSE, ICSE, IB, 29+ state boards), 22 languages, Classes 6-10, 12
  subjects. Activate for FastAPI debugging, LLM prompts for education, TTS/STT
  pipelines, curriculum content, schema migrations, Alembic, benchmark design,
  content factory, or IDNA-Bench layers. Also trigger for GPT-5-mini tutor prompts,
  GPT-4o-mini classifier logic, SessionState dataclass, FSM transitions/handlers,
  verify.py checks, Railway deployment issues, or any file in the app/ package.
  Do NOT trigger for generic FastAPI tutorials, general PostgreSQL questions,
  or Python coding tasks unrelated to the IDNA codebase or EdTech domain.
metadata:
  author: Hemant Ghosh
  version: 2.1.0
  category: edtech
  stack: python-fastapi-gpt5mini-gpt4omini-sarvam-postgresql-railway
  last_updated: 2026-02-27
  app_version: 8.1.5
---

# IDNA EdTech — Voice Tutor Development Skill (v2.0.0)

## 1. What is IDNA

IDNA EdTech builds "Didi" (दीदी), an AI-powered multilingual voice tutor for
Class 6-10 students across India. The tutor speaks the student's preferred language
naturally, teaches board-specific curriculum with culturally relevant Indian examples,
and guides students through problems step-by-step like a patient older sister.

India's education system: 33+ examination boards, 22 scheduled languages, 10 class
levels, 8-12 subjects per class. Realistic content matrix: 10,000-15,000 active
curriculum units.

## 2. Current Status (v8.1.5)

| Item | Status |
|------|--------|
| Version | **v8.1.5 LIVE on Railway** |
| URL | https://idna-tutor-mvp-production.up.railway.app |
| Health | /health → {"status":"ok","version":"8.1.5"} |
| Tests | **218 passing** (including 27 integration + 5 P1 regression tests) |
| Verify | **22/22 checks passing** via verify.py |
| Content | Chapter 1: 50 questions, 20 skills (Squares & Cubes) |
| P1 Bugs | **ALL 6 FIXED** (v8.1.1 - v8.1.5) |
| Phase 0 | COMPLETE — ready for Phase 1 |

## 3. Architecture Principles (NON-NEGOTIABLE)

1. **FSM = skeleton, content/board/language = parameterized flesh.** New board = DATA insert, zero CODE change.
2. **bench_score gates at database level.** Nothing reaches a student below threshold.
3. **Phase gates are strict.** P0=live test (GATE) → P1=schema evolve → P2=multi-board → P3=platform → P4=device.
4. **One Didi, always.** Sarvam Bulbul v3, speaker simran, hi-IN. No TTS fallback.

## 4. Tech Stack (v8.0.1 — Locked)

| Layer | Technology | Notes |
|-------|-----------|-------|
| Didi LLM | GPT-5-mini | Teaching responses, multi-turn reasoning |
| Classifier LLM | GPT-4o-mini | Input classification (10 categories) |
| STT | Sarvam Saarika v2.5 | Default language from STT_DEFAULT_LANGUAGE |
| TTS | Sarvam Bulbul v3 | Speaker: simran, hi-IN, pace 0.90, temp 0.7 |
| Backend | FastAPI (Python 3.11) | Async endpoints |
| Frontend | HTML/JS (single page) | web/student.html |
| Database | PostgreSQL (Railway managed) | Migrated from SQLite in v7.x |
| TTS Cache | PostgreSQL | Moved from filesystem in v7.5.2 |
| Hosting | Railway | Auto-deploy from GitHub main |

For Phase 2-4 tech stack (PersonaPlex, Milvus, Memory-R1, etc.), consult `references/stack-future.md`.

## 5. Codebase Structure

```
app/
├── routers/student.py          # FastAPI endpoints (async, v8.0 FSM)
├── state/session.py            # SessionState dataclass, TutorState enum
├── fsm/transitions.py          # 60-combo transition matrix
├── fsm/handlers.py             # Per-state handlers
├── tutor/input_classifier.py   # GPT-4o-mini classifier: 10 categories
├── tutor/llm.py                # GPT-5-mini Didi calls
├── tutor/instruction_builder_v8.py # Language-aware prompt builder
├── tutor/enforcer.py           # Response quality enforcement
├── voice/stt.py                # Sarvam Saarika v2.5 STT
├── voice/tts.py                # Sarvam Bulbul v3 TTS
├── content/ch1_square_and_cube.py  # Chapter 1: 50 questions, 20 skills
├── models.py                   # ORM models (Question, Student, Session)
web/student.html                # Student-facing web UI
tests/test_*.py                 # 152 tests
verify.py                       # 22 automated checks
CLAUDE.md                       # Claude Code operating rules
IDNA_v8_ARCHITECTURE.md         # THE architecture spec
alembic/                        # Database migrations
```

**CRITICAL:** Do NOT create `app/models/` directory — it shadows `app/models.py`.

## 6. FSM Architecture (60-Combination Matrix)

### 6 States
`GREETING`, `TEACHING`, `WAITING_ANSWER`, `HINT`, `NEXT_QUESTION`, `SESSION_END`

### 10 Input Categories
`ACK`, `IDK`, `REPEAT`, `ANSWER`, `LANGUAGE_SWITCH`, `CONCEPT_REQUEST`, `COMFORT`, `STOP`, `TROLL`, `GARBLED`

### Key Transitions
```
GREETING → TEACHING
TEACHING + ACK → WAITING_ANSWER (via NEXT_QUESTION)
TEACHING + IDK → TEACHING (reteach, cap at 3, then force WAITING_ANSWER)
TEACHING + REPEAT → TEACHING (reteach, same cap)
WAITING_ANSWER + ANSWER → evaluate → HINT or NEXT_QUESTION
WAITING_ANSWER + IDK → HINT (hint 1 → hint 2 → full solution)
NEXT_QUESTION → TEACHING (next topic) or SESSION_END
```

### v8.0 Key Features
1. **Language persistence**: preferred_language set by LANGUAGE_SWITCH, never resets
2. **Reteach cap**: After 3 IDKs/REPEATs, forces transition to WAITING_ANSWER
3. **No KeyError**: All 60 combinations defined in transition matrix
4. **Content Bank injection**: teach_material_index → 0=definition, 1=analogy, 2=vedic_trick

## 7. Voice Pipeline

```
Student speaks
  → Sarvam Saarika v2.5 STT (~300ms)
  → Confidence check (threshold 0.4)
  → Input Classifier (GPT-4o-mini, 10 categories)
  → FSM (state + input → action via transitions.py)
  → Instruction Builder v8 (language-aware LLM prompt)
  → GPT-5-mini (~800-1200ms)
  → clean_for_tts()
  → Sarvam TTS (single call, max 2000 chars)
  → Audio plays in browser
```

### clean_for_tts() Rules
| Input | Output |
|-------|--------|
| `-3/7` | `minus 3 by 7` |
| `2/3` | `2 by 3` |
| `+` → `plus`, `-` → `minus`, `×` → `multiplied by`, `=` → `equals` |
| Strip markdown formatting |

### Hallucination Detection (STT)
Reject: "Thank you for watching", "Subscribe", "[Music]", "[Applause]",
"(silence)", only punctuation, text < 2 chars, confidence < 0.4

## 8. Teaching Principles (Embedded in Didi's Personality)

1. **One idea per turn.** Never teach AND ask a question in the same turn.
2. **Show, don't tell.** Math: show equations. Science: cause-effect.
3. **Indian examples.** Roti, cricket, Diwali, monsoon, laddoo, tiles — not Western.
4. **Respectful Hindi.** "Aap" form, "dekhiye", "sochiye". Never "tum" or casual.
5. **No false praise.** Never say "Bahut accha!" unless answer is actually correct.
6. **Sub-step tracking (math).** Once confirmed correct, NEVER re-ask.
7. **Comfort first.** If frustrated, acknowledge feelings before any teaching.
8. **Board-appropriate evaluation.** CBSE notation vs state board notation.
9. **Language respect.** Student sets language once, ALL turns respect it.
10. **Reteach cap.** Max 3 reteaches per concept. On 4th IDK, advance to question.

## 9. P1 Backlog (ALL FIXED in v8.1.x)

| # | Bug | Fix Version | Status |
|---|-----|-------------|--------|
| 1 | Same-Q reload | v8.1.2 | FIXED |
| 2 | HOMEWORK_HELP trap | v8.1.1 | FIXED |
| 3 | Devanagari बटा parser | v8.1.1 | FIXED |
| 4 | Empty TTS sentence | v8.1.1 | FIXED |
| 5 | Parent split()[0] bug | v8.1.5 | FIXED |
| 6 | Weakest-skill dead end | v8.1.5 | FIXED |

## 10. Development Rules

1. **Run tests after every change:** `python -m pytest tests/ -v`
2. **Run verify.py:** 22/22 checks must pass before commit
3. **Never change TTS voice.** Sarvam simran only.
4. **Never rewrite DIDI_PROMPT.** Append rules, don't replace.
5. **New board = data insert, zero code change.**
6. **Alembic for all schema changes.**
7. **Commit format:** `v{major}.{minor}.{patch}: brief description`
8. **One change per commit.** Atomic. Tested. Proven.
9. **Don't edit MEMORY.md mid-session.**
10. **Don't create app/models/ directory** (shadows app/models.py).

## 11. Troubleshooting

### Sarvam TTS returns empty/silent audio
1. Check if `clean_for_tts()` output is empty string — P1 bug #4
2. Verify text length ≤ 2000 chars (Sarvam limit)
3. Check API key validity in Railway env vars
4. Never switch to a different TTS provider — fix the input

### Railway deploy fails
1. Check `railway logs` for Python import errors
2. Verify `requirements.txt` matches local env
3. Check PostgreSQL connection string in Railway dashboard
4. Confirm health endpoint responds: `/health`

### SessionState KeyError
1. This should NOT happen in v8.0 — all 60 combos are defined
2. If it does: check `app/fsm/transitions.py` for the missing (state, input) pair
3. Run `python -m pytest tests/test_integration.py -v` to catch gaps

### STT returns hallucinated text
1. Check hallucination detection list in `app/voice/stt.py`
2. Verify confidence threshold is 0.4
3. Add new hallucination patterns to the reject list, don't lower threshold

### LLM response doesn't follow language preference
1. Check `preferred_language` in SessionState — it should persist across turns
2. Verify `instruction_builder_v8.py` injects the language into the prompt
3. Never reset language mid-session — only LANGUAGE_SWITCH input changes it

## 12. Examples

**Example 1: Fix a voice pipeline bug**
User: "The TTS is returning empty audio for some responses"
Claude should:
1. Check `app/voice/tts.py` for empty string handling
2. Check `clean_for_tts()` output in the pipeline
3. Run `python -m pytest tests/ -k tts -v`
4. Never change TTS voice or provider settings

**Example 2: Add content for a new chapter**
User: "Create content bank for Chapter 2 Linear Equations"
Claude should:
1. Follow the pattern in `app/content/ch1_square_and_cube.py`
2. Include questions, skills, and teaching material at 3 layers (definition, analogy, vedic_trick)
3. Use Indian examples (roti, cricket, tiles)
4. Verify content integrates with FSM content injection

**Example 3: Debug FSM transition**
User: "Student says IDK 5 times and the session loops forever"
Claude should:
1. Check reteach cap logic in `app/fsm/handlers.py`
2. Verify transition matrix in `app/fsm/transitions.py` for (TEACHING, IDK) after cap
3. Run integration tests: `python -m pytest tests/test_integration.py -v`
4. The cap is 3 — on 4th IDK, must force WAITING_ANSWER

**Example 4: Database schema change**
User: "Add a new column to the students table"
Claude should:
1. Create Alembic migration: `alembic revision --autogenerate -m "description"`
2. Update `app/models.py` (NOT create app/models/ directory)
3. Run migration: `alembic upgrade head`
4. Update tests, run verify.py
5. For v8.1.0 schema plans, consult `references/schema-v81.md`

## 13. Reference Files

For detailed specifications beyond the core skill, consult these references as needed:

| File | Contents | When to read |
|------|----------|--------------|
| `references/schema-v81.md` | v8.1.0 database schema: boards, textbooks, content_units, student_profiles tables | Schema evolution, multi-board work |
| `references/bench-spec.md` | IDNA-Bench 7 layers, thresholds, content factory pipeline | Benchmark design, quality gating |
| `references/roadmap.md` | Phase timeline, board expansion tiers, 22 languages, strategic positioning | Planning, investor context, government partnerships |
| `references/stack-future.md` | Phase 2-4 tech: PersonaPlex, Milvus, Memory-R1, Ollama, on-device SLM | Future architecture decisions |
