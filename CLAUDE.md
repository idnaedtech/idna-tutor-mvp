# CLAUDE.md — IDNA EdTech Operating Rules

> **This file is read by Claude Code on every session start.**
> **Last updated:** 2026-03-05
> **Repo:** github.com/idnaedtech/idna-tutor-mvp
> **Live:** https://idna-tutor-mvp-production.up.railway.app
> **Current version:** v10.0.2
> **Can be modified by CEO only.**

---

## 0. SESSION START PROTOCOL (DO THIS FIRST)

1. **Read `ROADMAP.md`** — know what's in progress, what's blocked, what's next
2. **Read this file** — know the rules, architecture, and red lines
3. **Do NOT start work that isn't on the roadmap** without asking CEO first
4. **When completing a task**, update ROADMAP.md: `[ ]` → `[x]` with date
5. **When starting a task**, update ROADMAP.md: `[ ]` → `[-]` with date

---

## 0.1 PRIME DIRECTIVE

You are working on a production voice tutoring platform used by real Indian students.
**Every broken deploy = a student who can't learn.**
Read before editing. Prove before claiming done. Ask before touching files outside your scope.

---

## 1. PROJECT OVERVIEW

Voice-based AI tutor "Didi" (दीदी) for NCERT Class 8 Math, targeting Tier 2/3 Indian students.
Didi is an encouraging elder-sister figure who teaches through voice conversation.

| Layer | Technology | Notes |
|-------|-----------|-------|
| Teaching LLM | gpt-4.1 | Better instruction following (38.3% MultiChallenge vs gpt-4o's 27.8%). 20% cheaper than gpt-4o. |
| Classifier LLM | gpt-4.1-mini | Input classification. 10 categories. gpt-5-mini rejected temperature param (reasoning model). |
| STT | Sarvam Saarika v2.5 | Default language from STT_DEFAULT_LANGUAGE |
| TTS | Sarvam Bulbul v3 | speaker=simran, language=hi-IN, pace=0.90 |
| Backend | FastAPI (Python 3.11) | Async endpoints |
| Database | PostgreSQL (Railway managed) | Not SQLite. Alembic for all migrations. |
| Hosting | Railway (3 services) | Auto-deploy from main |

**Do not add new dependencies without explicit permission.**
**Do not upgrade existing dependencies unless explicitly tasked.**

---

## 2. CRITICAL ARCHITECTURE KNOWLEDGE

### The Dual Pipeline (UNDERSTAND THIS FIRST)

There are TWO parallel pipelines. Both run on every request. This is tech debt, not design.

```
STREAMING (PRIMARY — used by voice frontend):
  /api/student/session/message-stream
  └── Preprocessing (meta-question, language switch, confusion detection)
  └── Input Classifier (gpt-4.1-mini)
  └── v7.3 state_machine.transition() → Action object
  └── v7.3 instruction_builder.build_prompt() → LLM messages  ← THE ACTIVE BRAIN
  └── gpt-4.1 (streaming) → enforcer checks → TTS streaming → SSE

NON-STREAMING (SECONDARY — text input fallback):
  /api/student/session/message
  └── Same preprocessing
  └── Same classifier
  └── v9 handlers.handle_state() → _llm_instruction
  └── v9 instruction_builder_v9.build() → LLM messages
  └── gpt-4.1 (sync) → enforcer checks → TTS sync → JSON
```

**Both endpoints also run the v8 FSM (`get_transition()`) for side effects only** (language storage, empathy tracking). The v8 FSM does NOT control routing — it's a logger.

### What This Means for You

- **If fixing voice/teaching behavior:** Edit `app/tutor/instruction_builder.py` (v7.3)
- **If fixing text input behavior:** Edit `app/tutor/instruction_builder_v9.py` (v9)
- **If fixing state transitions:** Edit `app/tutor/state_machine.py` (v7.3, both endpoints)
- **Do NOT edit** `app/fsm/handlers.py` or `app/fsm/transitions.py` for teaching behavior — they are side-effect-only for the streaming pipeline

---

## 3. NON-NEGOTIABLE RULES

These rules are absolute. Violating any of them is a blocking error.

1. **FSM skeleton is stable.** The v7.3 state machine (6 states × 10 input categories) does not get new states or input categories without explicit permission.
2. **New board = data insert, zero code change.** The FSM is the skeleton, content/board/language are parameterized flesh.
3. **bench_score gates everything.** No content serves students without a score above threshold (85 for boards, 98% for math truth, 75 for languages).
4. **One Didi voice.** Sarvam Bulbul v3, speaker=simran, hi-IN, pace=0.90. No TTS fallback. No voice switching.
5. **V10 persona is canonical.** The V10 DIDI_BASE (~40 lines) is the teacher persona. Don't revert to rule-based format.
6. **Language persistence is sacred.** `session.language_pref` is set by preprocessing language switch detection and injected in EVERY LLM prompt. It must NEVER reset on state transitions.
7. **Every `_sys()` call MUST pass `session_context=ctx, question_data=q`.** Calling `_sys()` without session_context bypasses ALL language enforcement, confusion escalation, and student context. This was the P0 root cause bug.
8. **Phase gates are strict.** P0 → P1 → P2 → P3 → P4. No features from a later phase unless all prior phase gates have passed.
9. **Alembic for all schema changes.** No raw SQL DDL against production. Every migration must have a rollback.
10. **Never create `app/models/` directory.** This shadows `app/models.py` and breaks imports.

---

## 4. CODEBASE STRUCTURE

### Active Code (what actually runs)

```
app/
├── routers/
│   └── student.py              # 1,469 lines. Main router, both endpoints, session mgmt.
│                                # THIS IS THE MAIN ORCHESTRATOR.
├── tutor/
│   ├── instruction_builder.py  # V10 ACTIVE BRAIN — builds ALL LLM prompts
│   │                           # for streaming endpoint. MOST CRITICAL FILE.
│   │                           # V10: New DIDI_BASE persona, LANG_INSTRUCTIONS dict
│   ├── strings.py              # V10: Centralized multilingual strings (4 languages)
│   ├── instruction_builder_v9.py # v9 brain for non-streaming endpoint.
│   ├── state_machine.py        # v7.3 FSM — produces Action objects. ACTIVE.
│   ├── preprocessing.py        # Meta-question, language switch, confusion detectors.
│   ├── input_classifier.py     # gpt-4.1-mini classifier. 10 categories.
│   ├── enforcer.py             # Output safety — length, praise, repetition.
│   ├── llm.py                  # OpenAI API wrapper (sync + streaming).
│   ├── answer_checker.py       # Regex-based math answer checking.
│   ├── answer_evaluator.py     # LLM-based answer evaluation.
│   └── memory.py               # Question selection, skill tracking.
├── fsm/
│   ├── transitions.py          # 447 lines. v8 FSM. SIDE EFFECTS ONLY (language, empathy).
│   │                           # Does NOT control teaching flow for streaming endpoint.
│   └── handlers.py             # 811 lines. v9 handlers for non-streaming only.
├── state/
│   └── session.py              # 186 lines. SessionState dataclass (v9 adapter).
├── voice/
│   ├── stt.py                  # 255 lines. Sarvam Saarika v2.5 STT.       [PROTECTED]
│   ├── tts.py                  # 343 lines. Sarvam Bulbul v3 TTS (simran). [PROTECTED]
│   ├── clean_for_tts.py        # 176 lines. Math→words conversion.
│   └── tts_precache.py         # 210 lines. TTS caching.
├── content/
│   ├── seed_questions.py       # 313 lines. 60+ questions, Hinglish only.
│   ├── ch1_square_and_cube.py  # 1,968 lines. Chapter metadata + concepts.
│   └── curriculum.py           # 144 lines. Concept/ChapterGraph models.
├── models.py                   # 256 lines. ORM models (Question, Student, Session, etc.)
├── database.py                 # 143 lines. SQLAlchemy + PostgreSQL.
├── config.py                   # 131 lines. LLM_MODEL=gpt-4.1 (Railway env var), MAX_WORDS=40.
└── main.py                     # 270 lines. App setup, migrations, seeding.

content_bank/
├── loader.py                   # 258 lines. JSON content bank loader.
└── math_8_ch6.json             # ~80KB. Content bank data.

web/
└── student.html                # Student-facing web UI.

tests/
├── test_core.py                # Answer checking, fractions
├── test_integration.py         # FSM transitions, language
├── test_preprocessing.py       # Meta-Q, language, confusion detectors
├── test_p0_language_persistence.py  # Language detection, TTS
├── test_p0_regression.py       # P0 regression — prompt trace tests
├── test_v10_persona.py         # V10: Persona, strings.py, warm teacher identity
├── test_content_bank.py        # Content bank loader
├── test_v750_features.py       # Sentence splitter, enforcer
├── test_p1_fixes.py            # Question picking, memory
└── test_ch1_square_cube.py     # Question bank validation
    # Total: 280 tests. ALL must pass before any commit.

alembic/                        # Database migrations
```

### Dead Code (DO NOT EDIT, DO NOT IMPORT)

| File | Why Dead |
|------|----------|
| `app/tutor/instruction_builder_v8.py` | Never imported by anything. 278 lines of waste. |
| `app/voice/streaming.py` | Never imported. Streaming is inline in student.py. |
| `app/parent_engine/__init__.py` | Empty placeholder. |
| `app/ocr/__init__.py` | Empty placeholder. |

**If you find yourself editing any of these files, STOP. You are editing dead code.**

---

## 5. THE VOICE PIPELINE (Actual Flow)

```
Student speaks into browser mic
  → Frontend sends audio to /api/student/session/message-stream
  → Sarvam Saarika v2.5 STT (~300ms) → transcribed text
  → Confidence check (threshold 0.4)
  → Preprocessing layer (runs BEFORE classifier):
      1. Meta-question detector → bypass LLM if matched
      2. Language switch detector → update session.language_pref in DB
      3. Confusion detector → increment session.confusion_count
  → Input Classifier (gpt-4.1-mini → 10 categories)
  → v7.3 state_machine.transition(state, category) → Action object
  → v8 get_transition() runs for SIDE EFFECTS ONLY (language store, empathy)
  → v7.3 instruction_builder.build_prompt(action, ctx, ...) → LLM messages
      └── _sys(extra, session_context=ctx, question_data=q) ← MUST have session_context
      └── V10: Language via LANG_INSTRUCTIONS dict (embedded in DIDI_BASE)
      └── V10: Confusion handling embedded in teacher persona
      └── Chapter context injected via _get_chapter_context()
  → gpt-4.1 streaming (~800-1200ms)
  → enforcer.py checks (length, praise rules, language)
  → clean_for_tts() → math symbols to words
  → Sarvam Bulbul v3 TTS (simran, hi-IN, ~500ms)
  → SSE stream to frontend → audio plays

Latency budget: STT(300ms) + Classify(200ms) + LLM(1200ms) + TTS(500ms) ≈ 2.2s
```

---

## 6. FILE PROTECTION LEVELS

| Protection | Meaning | Files |
|-----------|---------|-------|
| **CEO-ONLY** | Only Hemant modifies. Never touch. | `CLAUDE.md` |
| **PROTECTED** | Bug fixes only, never config changes | `voice/stt.py`, `voice/tts.py` |
| **ACTIVE BRAIN** | Edit carefully — every `_sys()` call needs `session_context` | `instruction_builder.py` |
| **ACTIVE** | Edit with test coverage | `state_machine.py`, `preprocessing.py`, `student.py` |
| **OPEN** | Edit freely with tests | `enforcer.py`, `llm.py`, `content/`, `models.py`, `tests/` |
| **DEAD** | Do not edit, do not import | `instruction_builder_v8.py`, `voice/streaming.py` |

### Hard Bans

- **Never** rename files or directories
- **Never** reformat code you didn't write (no style-only diffs)
- **Never** upgrade dependencies unless explicitly tasked
- **Never** delete tests or questions
- **Never** run `rm -rf` on anything
- **Never** modify `.env` or environment variables without explicit permission
- **Never** create `app/models/` directory (shadows `app/models.py`)
- **Never** call `_sys()` without `session_context=ctx` — this is the #1 bug pattern
- **Never** edit dead code files thinking they're active
- If you believe a file outside your declared scope must change: **STOP and state why**

---

## 7. TASK PROTOCOL

### Pre-Flight (Before ANY Edit)

```bash
python -m pytest tests/ -v          # Know what's green
git log --oneline -5                # Know recent changes
```

### Plan Before Execute

Before editing, state:
1. **Which files** you will modify
2. **Which functions/lines** you will change
3. **Current behavior** (what happens now)
4. **Desired behavior** (what should happen after)
5. **Call graph** (what calls this code, what does it call)

If you cannot do all 5, you don't understand the code well enough. Read more first.

### Execute One Step at a Time

- Make one change
- Run `python -m pytest tests/ -v`
- If tests fail, fix before proceeding
- Never bundle unrelated changes

### Prove It Works

No change is "done" without:
1. All 280 tests passing (paste output)
2. For server changes: curl output showing correct behavior
3. For production: `curl /health` showing correct version
4. For instruction_builder changes: verify `LANGUAGE:` appears in build_prompt output (V10 format)

---

## 8. COMMIT DISCIPLINE

### Format

```
v{major}.{minor}.{patch}: brief description
```

### Rules

- **One bug or feature per commit.** Never bundle.
- **Never commit failing tests.**
- **Commit message describes exactly one thing.** If you need "and", split the commit.

### Workflow

```bash
python -m pytest tests/ -v            # All tests pass
git add -A
git commit -m "v9.0.X: description"
git push origin main
# Wait for Railway deploy
curl https://idna-tutor-mvp-production.up.railway.app/health  # Confirm
```

---

## 9. THE instruction_builder.py CONTRACT (V10)

This is the most critical file. V10 transformed it from rule-based to teacher persona.

### V10 Architecture Change

**Old (pre-V10):** 117-line rule-based DIDI_BASE with harsh labels ("ANSWER INCORRECT")
**New (V10):** ~40-line teacher persona with warm identity ("let's think differently")

Key V10 changes:
- `DIDI_BASE` is now a warm teacher persona with `{language_instruction}` placeholder
- `LANG_INSTRUCTIONS` dict replaces `LANG_ENGLISH`/`LANG_HINDI`/`LANG_HINGLISH` constants
- `_get_confusion_instruction()` DELETED — confusion handling embedded in persona
- `_build_fallback()` now tells LLM to respond naturally, no hardcoded Hindi
- `_build_teach_concept()` says "Rephrase" not "Teach" — content bank as truth

### _sys() Function — V10 Version

```python
def _sys(extra="", session_context: dict = None, question_data: dict = None):
    if session_context:        # ← CORRECT PATH: real student data
        base = _format_didi_base(session_context, question_data)
        # V10: Language instruction is INSIDE DIDI_BASE via {language_instruction}
        # V10: Confusion handling is EMBEDDED in persona, no separate function
    else:                      # ← DANGER: hardcoded "hinglish" defaults
        base = DIDI_BASE.format(...)
```

**RULE: Every builder that calls `_sys()` MUST pass `session_context=ctx, question_data=q`.**

### Language Flow (V10)

```
Student says "speak in English"
  → preprocessing.py detects language switch
  → session.language_pref = "english" (saved to DB)
  → session_ctx["language_pref"] = "english"
  → build_prompt() → builder calls _sys(extra, session_context=ctx, ...)
  → _format_didi_base() → LANG_INSTRUCTIONS["english"]
  → System prompt contains: "LANGUAGE: Respond ENTIRELY in English. No Hindi words."
  → gpt-4.1 follows instruction → responds in English
```

### strings.py (V10)

Centralized multilingual strings. Adding a new language = adding dict entries only.

```python
from app.tutor.strings import get_text
greeting = get_text("warmup_greeting", "english", name="Priya")
# Returns: "Hey Priya! How are you doing today? How was school?"
```

Supports: english, hindi, hinglish, telugu. Falls back to English for unknown.

### Correction Detection Flow (v9.0.10)

```
Student says "that's wrong" or "galat"
  → student.py detects correction trigger in _correction_triggers list
  → _is_correction = True
  → session_ctx["student_is_correcting"] = True
  → session_ctx["student_text"] = original student input
  → build_prompt() intercepts BEFORE regular builder
  → Returns apology + recalculation prompt in correct language
  → LLM apologizes and fixes the math error
```

If correction is ignored, student loses trust in Didi.

### Arithmetic Guardrail (v9.0.10)

```
_sys() injects this rule into EVERY system prompt:
  "ARITHMETIC RULE: NEVER calculate or enumerate mathematical facts from memory.
   If you list squares, cubes, or any computed values, use ONLY the content provided."

_build_teach_concept() injects verified data for math skills:
  "⚠️ USE ONLY THESE VERIFIED VALUES: 1²=1, 2²=4, 3²=9, 4²=16, 5²=25..."
```

Prevents hallucinations like "8²=74". LLMs cannot reliably compute arithmetic.

---

## 10. ACTIVE BUGS (P0 — DATABASE CONFIRMED, 2026-03-05)

These 5 bugs were confirmed by analyzing 872 sessions in the production database.
Fix these BEFORE any other work. See ROADMAP.md for current status.

| # | Bug | Root Cause | File(s) |
|---|-----|-----------|---------|
| 1 | **Same explanation repeats 6x** | CONCEPT_REQUEST in TEACHING doesn't increment teaching_turn. Only IDK does. Sessions e4e3d030 (cc=6,tt=0) and 1560f98f (cc=7,tt=0) prove this. | `state_machine.py` line 214-219 |
| 2 | **Nudge always Hindi** | Non-streaming SILENCE handler (line 552) hardcodes Hindi. Streaming endpoint (line 1205) checks language_pref correctly. | `student.py` line 552 |
| 3 | **Devanagari meta-question fails** | "कौन सा चैप्टर" (full Devanagari) doesn't match regex. Only `कौनसा chapter` (mixed script) matches. Sarvam STT outputs full Devanagari. | `preprocessing.py` line 159-166 |
| 4 | **Emotional distress ignored at session start** | "मैं बहुत उदास हूं" gets classified as ACK. No COMFORT fast-path. GREETING sends all non-COMFORT to TEACHING. | `input_classifier.py`, `preprocessing.py` |
| 5 | **Response too long for voice** | Content bank definition for prime factorization is full worked solution. LLM reproduces verbatim. No length guard in _build_teach_concept. | `instruction_builder.py` line 380 |

### Post-P0 (Fix after live retest passes)

| # | Issue | Impact | File(s) |
|---|-------|--------|---------|
| 6 | Non-streaming endpoint has 5 hardcoded Hindi messages | Low — voice uses streaming | `student.py` |
| 7 | All content in seed_questions.py is Hinglish only | Medium — English quality suffers | `seed_questions.py` |
| 8 | Dual pipeline tech debt — every change requires checking two code paths | High — slows all future work | `student.py` |
| 9 | Dead code: `instruction_builder_v8.py`, `voice/streaming.py` | Low — just noise | Delete safely |

### Original P1 Bugs (from v8.0 era)

| # | Bug | File(s) |
|---|-----|---------|
| 10 | Same-Q reload on page refresh | `student.py` |
| 11 | HOMEWORK_HELP trap missing in classifier | `input_classifier.py` |
| 12 | Devanagari बटा parser broken | `input_classifier.py` |
| 13 | Empty TTS sentence wastes API | `tts.py` |
| 14 | Parent split()[0] bug on single names | `student.py` |
| 15 | Weakest-skill dead end | `handlers.py` |

---

## 11. PHASE GATES

| Phase | Goal | Gate Criteria | Status |
|-------|------|--------------|--------|
| **P0** | Core tutoring loop works | Full session without crash/loop/language reset | **IN PROGRESS — live retest pending** |
| **P1** | Schema evolution | Multi-board DB, content migration, API v1 | Blocked on P0 |
| **P2** | Multi-board MVP | CBSE + Telangana + Maharashtra + ICSE | Blocked on P1 |
| **P3** | Platform | Content factory, IDNA-Bench, 22 languages | Blocked on P2 |
| **P4** | Infrastructure | On-device tablets, government partnerships | Blocked on P3 |

**Do NOT work on Phase N+1 features until Phase N gate passes.**

---

## 12. v7.3 FSM REFERENCE

### 6 States

`GREETING`, `TEACHING`, `WAITING_ANSWER`, `HINT`, `NEXT_QUESTION`, `SESSION_END`

### 10 Input Categories

`ACK`, `IDK`, `REPEAT`, `ANSWER`, `LANGUAGE_SWITCH`, `CONCEPT_REQUEST`, `COMFORT`, `STOP`, `TROLL`, `GARBLED`

### Key Transitions

```
GREETING + ACK → TEACHING (teach_concept)
GREETING + other → GREETING (re_greet)
TEACHING + ACK → WAITING_ANSWER (read_question)
TEACHING + IDK → TEACHING (teach_concept with reteach, cap at 3)
TEACHING + CONCEPT_REQUEST → TEACHING (teach_concept, MUST increment teaching_turn)
WAITING_ANSWER + ANSWER → evaluate → HINT or NEXT_QUESTION
WAITING_ANSWER + IDK → HINT (hint 1 → hint 2 → show_solution)
NEXT_QUESTION → TEACHING (next topic) or SESSION_END
```

### Key Features

- **Language persistence:** session.language_pref set by preprocessing, never resets on transitions
- **Reteach cap:** After 3 IDKs/REPEATs/CONCEPT_REQUESTs in TEACHING, forces transition to WAITING_ANSWER
- **Confusion count:** Tracked in session.confusion_count, escalation protocol in system prompt
- **Content Bank:** teach_material_index maps to CB material (0=definition, 1=analogy, 2=vedic_trick)

### CRITICAL BUG (database-confirmed, 2026-03-05)

**CONCEPT_REQUEST during TEACHING must increment teaching_turn.** Database evidence:
session e4e3d030 had confusion_count=6 but teaching_turn=0. The classifier returns
CONCEPT_REQUEST for phrases like "I didn't understand, can you explain in English?"
because "explain" outweighs "didn't understand" in LLM classification. Without the
increment, teaching_turn stays 0 forever and Turn 0 content repeats verbatim.

---

## 13. CONTENT RULES

- **Indian examples only.** Roti, cricket, Diwali, monsoon, laddoo, tiles — not Western.
- **Three teaching layers per topic:** definition → analogy → vedic_trick.
- **Respectful Hindi.** "Aap" form, "dekhiye", "sochiye". Never "tum" or casual.
- **No false praise.** Never say "Bahut accha!" unless the answer is actually correct.
- **Voice-optimized.** Max 3 sentences teaching, 2 sentences feedback. No bullets, no markdown.
- **Say "times" not "×", "equals" not "=".** TTS reads symbols poorly.

---

## 14. ANTI-PATTERNS — INSTANT REJECTION

If you catch yourself doing any of these, stop immediately:

1. **Calling `_sys()` without `session_context=ctx`** — bypasses all language/student context
2. **Adding a new action_type to state_machine.py without a matching builder in `_BUILDERS`** — hits fallback
3. **Editing `instruction_builder_v8.py`** — it's dead code, never imported
4. **Editing `voice/streaming.py`** — it's dead code, never imported
5. **"Improving" code style** in files you weren't asked to touch
6. **Adding try/except that swallows errors silently** — log or raise, never pass
7. **Resetting `session.language_pref`** anywhere in any transition
8. **Adding a new TTS voice or fallback** — one Didi, always
9. **Writing SQL DDL directly** instead of using Alembic
10. **Claiming "done" without test output** — paste the actual results
11. **Editing multiple unrelated things in one commit** — atomic only
12. **Hardcoding Hindi strings** without checking language_pref first — this includes nudge/silence messages
13. **Editing v8 FSM files** (`transitions.py`, `handlers.py`) for streaming behavior — they're side-effect-only
14. **Creating `app/models/` directory** — shadows `app/models.py`, breaks imports
15. **Letting LLM compute math from memory** — use verified data injection (`_VERIFIED_SQUARES` in `_build_teach_concept`)
16. **Ignoring student corrections** — "that's wrong"/"galat" must trigger apology handler in `build_prompt()`
17. **Importing deleted V10 functions** — `_get_confusion_instruction()`, `LANG_ENGLISH`, `DIDI_NO_PRAISE` are gone
18. **Reverting to rule-based DIDI_BASE** — V10 uses ~40-line teacher persona, not 117-line rules
19. **Using old language format in tests** — check for `"LANGUAGE:"` not `"LANGUAGE SETTING:"`
20. **Passing teaching_turn unchanged on CONCEPT_REQUEST in TEACHING** — MUST increment, same as IDK (P0 Bug #1)
21. **Passing content bank material verbatim to LLM for voice** — if teach_content > 200 chars, add "summarize in 2 sentences" instruction
22. **Setting session fields without db.commit()** — teaching_turn, language_pref, confusion_count MUST be followed by db.commit() or value is lost between requests (P0 Bug #1 root cause in v10.0.2)

---

## 15. DEPLOYMENT

- Railway auto-deploys from `main` branch on GitHub
- Health check: `GET /health` → `{"status":"ok","version":"..."}`
- Environment variables are set in Railway dashboard — **never hardcode secrets**
- If deploy fails, check Railway build logs first
- TTS cache is in PostgreSQL — survives container restarts
- **Always run full test suite before pushing to main**
- **Always confirm production with `curl /health` after push**

---

## 16. REFERENCE DOCUMENTS

| Document | Purpose | Location |
|----------|---------|----------|
| HANDOFF.md | Master reference — full architecture, root cause analysis, next steps | CEO's files |
| FULL_CODEBASE_AUDIT.md | 15,049-line audit with dead code map | CEO's files |
| IDNA_CTO_Architecture_Roadmap_v1 | Phase 0→4 roadmap, schema evolution plan | Claude Project |
| IDNA_BENCH_v1_Specification | 7-layer, 31-benchmark evaluation framework | Claude Project |
| didi_system_prompt_v8_1.md | Didi personality and rules spec | Claude Project |

---

## 17. THE FOUR RULES

If you remember nothing else:

1. **Read ROADMAP.md first.** Know what you're supposed to be working on.
2. **Every `_sys()` call needs `session_context=ctx`.** No exceptions. Ever.
3. **No "done" without all tests passing.** Paste the actual pytest output.
4. **One change per commit.** Atomic. Tested. Proven.
