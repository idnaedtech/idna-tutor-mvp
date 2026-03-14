# IDNA EdTech Project Memory

## Current Version
- **v10.6.7** deployed to Railway (domain: didi.idnaedtech.com)
- 398 test functions passing across 11 test files
- Models: GPT-4.1 (teaching), GPT-4.1-mini (classifier + inline eval)
- STT: Sarvam Saarika v2.5 | TTS: Sarvam Bulbul v3 (simran, hi-IN)
- 84 questions (74 active), 5-level system: L1:10 L2:9 L3:14 L4:22 L5:19
- Languages: Hindi, English, Hinglish, Telugu
- P0 smoke test PASSED with real student (March 14, 2026)

## V10 Architecture (GPT-4.1 Role Change)

### Core Change: Voice Box → Teacher
- Old: 117-line rule-based DIDI_BASE with harsh labels ("ANSWER INCORRECT")
- New: ~40-line teacher persona with warm identity ("let's think differently")
- GPT-4.1 decides HOW to teach, not just rephrases scripts

### Key V10 Files
| File | Purpose |
|------|---------|
| `app/tutor/strings.py` | Centralized multilingual strings (4 languages) |
| `app/tutor/instruction_builder.py` | V10 DIDI_BASE, LANG_INSTRUCTIONS dict, _lang() helper |
| `app/tutor/answer_evaluator.py` | LLM-based answer evaluation (PRIMARY path) |
| `app/tutor/memory.py` | Level-aware question picker |

## 5-Level Teaching Scaffold (v10.4.0)

- **Level 1:** Multiplication recall ("What is 3 times 3?") — 10 questions
- **Level 2:** Square/cube numbers ("What is the square of 8?") — 9 questions
- **Level 3:** Square/cube roots ("What is √49?", "What is ∛512?") — 14 questions
- **Level 4:** Patterns & properties ("Can a square end in 7?", "Is 50 a perfect square?") — 22 questions
- **Level 5:** Application/methods ("Find side of square with area 441", word problems) — 19 questions

### Level Advancement
- Start at Level 2
- 3 correct in a row → level up
- 2 wrong in a row → level down
- Session fields: `current_level`, `consecutive_correct`, `consecutive_wrong`

## Inline Answer Evaluation (v10.5.1)

- Streaming endpoint combines eval + response in ONE LLM call
- LLM outputs `[CORRECT]` or `[INCORRECT]` prefix
- Parsed in generator finally block (~line 1856 of student.py)
- CORRECT → load next question, state = WAITING_ANSWER
- INCORRECT → increment hint_level, state = HINT_1/HINT_2/FULL_SOLUTION
- Fallback to regex answer_checker if LLM doesn't follow prefix

## Telugu Support (v10.6.4)

- `_lang()` helper in instruction_builder.py — 48 uses
- Telugu pre-scan in BOTH endpoints (before classifier)
- TTS language mapping: telugu → te-IN
- `LANG_INSTRUCTIONS["telugu"]` with full Telugu script enforcement
- Triggers: "telugu", "తెలుగు", "తెలుగులో"

## Question Picker (v10.6.0, memory.py)

- `pick_next_question()` with HARD RULES:
  1. WHERE level = current_level (strict)
  2. Exclude current question + all previously answered
  3. If exhausted at level → reuse same-level (excluding current)
  4. If no questions at level → try adjacent levels (up first, then down)
- Questions upserted from ch1_square_and_cube.py on startup via `_upsert_questions()`

## Dual FSM Architecture (Tech Debt)

- **v7.3 FSM** (`state_machine.py`): Controls teaching flow, returns Action objects
- **v8.0 FSM** (`fsm/transitions.py`): Side effects only (language, empathy)
- Both run on every request in both endpoints
- v7.3 result drives action, v8.0 result drives session field updates
- Unification deferred to Phase 2

## Critical Lessons Learned

### 1. Session Field Updates Need db.commit()
- `session.X = value` does NOT persist until `db.commit()`
- BOTH endpoints: sync `db.commit()` or `await run_in_threadpool(lambda: db.commit())`
- Missing commit was root cause of teaching_turn loop bug (v10.0.2)

### 2. Inline Eval State Must Respect Hint Level (v10.6.7)
- Generator finally block must check current_hint_level for INCORRECT
- hint_level >= 3 → FULL_SOLUTION, >= 2 → HINT_2, else → HINT_1
- Blindly setting HINT_1 caused death spiral (fixed in v10.6.7)

### 3. Every _sys() Call Needs session_context
- `_sys(extra, session_context=ctx, question_data=q)` — no exceptions
- Without session_context: bypasses language enforcement, student context
- The #1 recurring bug pattern in the codebase

### 4. NEXT_QUESTION is Always Transient (v10.6.4)
- After FSM returns NEXT_QUESTION, immediately overwrite to WAITING_ANSWER
- Prevents double-answer bug where student's answer applies to old question
- Applied in BOTH endpoints (~line 1076 and ~line 1811)

### 5. V10 Deleted Functions (Don't Import!)
- `_get_confusion_instruction()` — deleted, embedded in persona
- `DIDI_NO_PRAISE`, `DIDI_PRAISE_OK` — deleted, natural handling
- `LANG_ENGLISH`, `LANG_HINDI`, `LANG_HINGLISH` — replaced by `LANG_INSTRUCTIONS` dict

### 6. Question Level Rules
- "What is X times Y?" → Level 1
- "What is the square/cube of X?" → Level 2
- "What is √X?" / "What is ∛X?" → Level 3
- "Is X a perfect square?", pattern questions, units digit → Level 4
- Word problems, prime factorisation, methods → Level 5

### 7. clean_for_tts() Rules
- Dashes → commas (global): `" - "` → `", "`
- Fractions: `-3/7` → `minus 3 by 7`
- Operators: `+` → plus, `-` → minus, `×` → multiplied by, `=` → equals
- Strip markdown formatting
- v10.6.7: strips "You asked" / "Aapne poocha" framing

### 8. Content Bank Structure
- Questions in `ch1_square_and_cube.py` (flat Python, not DB yet)
- Each question: id, question (hi), question_en, answer, hints, accept_patterns, level, target_skill
- 29 of 74 questions missing solution/explanation field — auto-generates from answer+hints (v10.6.7)
- Migration to PostgreSQL content_units table planned for Phase 1

## Key File Locations

| Purpose | File | Line |
|---------|------|------|
| Session start | `student.py` | ~170 (start_session) |
| Streaming endpoint | `student.py` | ~1130 (message_stream) |
| Non-streaming endpoint | `student.py` | ~440 (message) |
| Inline eval parsing | `student.py` | ~1856 (generator finally) |
| Level advancement | `student.py` | ~807 (non-stream), ~1862 (stream) |
| NEXT_QUESTION transient | `student.py` | ~1076 and ~1811 |
| V10 DIDI_BASE | `instruction_builder.py` | ~30-70 |
| LANG_INSTRUCTIONS | `instruction_builder.py` | ~72-120 |
| Telugu _lang() | `instruction_builder.py` | throughout (48 uses) |
| Question picker | `memory.py` | ~127 (pick_next_question) |
| Question upsert | `main.py` | ~200 (_upsert_questions) |
| Pilot student seed | `main.py` | ~250 (_seed_pilot_students) |
| Debug output | `student.py` | ~1060 (classifier/verdict/state line) |
| Health detail | `main.py` | /health/detail endpoint |

## Bug Fix Patterns

### Hint Loop / Death Spiral
1. Check inline eval state override in generator finally block
2. Ensure FULL_SOLUTION → NEXT_QUESTION for all inputs (state_machine.py ~339)
3. Check current_hint_level vs state assignment

### Level System Issues
1. Check question level tags in ch1_square_and_cube.py
2. Verify _upsert_questions() ran on production (check /health/detail)
3. Check pick_next_question() level filtering in memory.py

### Language Not Working
1. Check preprocessing language pre-scan (both endpoints)
2. Check LANG_INSTRUCTIONS dict has the language
3. Check get_tts_language() mapping in student.py
4. Verify db.commit() after language_pref change

### "Solution not available" Leak
1. Check instruction_builder.py ~619 and ~833
2. Question missing both solution AND explanation fields
3. Fix: auto-generate from answer + hints (done in v10.6.7)
