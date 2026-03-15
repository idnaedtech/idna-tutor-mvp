# IDNA EdTech Project Memory

## Current Version
- **v10.7.2** deployed to Railway (domain: didi.idnaedtech.com)
- 419 test functions passing across 12 test files
- Models: GPT-4.1 (teaching, LLM_MAX_TOKENS=250), GPT-4.1-mini (classifier + inline eval)
- STT: Sarvam Saarika v2.5 | TTS: Sarvam Bulbul v3 (simran, hi-IN)
- 84 questions (74 active), 5-level system: L1:10 L2:9 L3:14 L4:22 L5:19
- Languages: Hindi, English, Hinglish, Telugu
- P0 smoke test PASSED with real student (March 14, 2026)
- Pilot launch: March 17-18 (10 CBSE Class 8 students, Nizamabad)
- **CODE FREEZE active** — no changes until pilot data collected (2+ days)

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

## Chapter Introduction (v10.7.0)

- When `questions_attempted == 0`, TEACHING uses CHAPTER_INTRO content
- **turn_0:** NCERT tile analogy ("3 rows of 3 tiles = 9, a square!")
- **turn_1:** Square root + assessment bridge ("Let's see what you know")
- Content in `ch1_square_and_cube.py` CHAPTER_INTRO dict (4 languages)
- First question prefers square-type via `prefer_square_first=True` (not cube)
- No new FSM state — content-driven logic, not state-driven

## Teaching Quality Overhaul (v10.7.1)

Four brevity locks removed simultaneously — ALL FOUR must change together:
- **config.py:** `MAX_TEACHING_WORDS=120`, `MAX_TEACHING_SENTENCES=6` (hints stay 40/2)
- **enforcer.py:** `is_teaching` parameter — teaching not truncated at 40 words
- **student.py:** TEACHING TTS raised to 800 chars (hints stay 300), `is_teaching` flag
- **instruction_builder.py:** DIDI_BASE says 4-6 sentences for teaching, 1-2 for hints
- **Railway env:** `LLM_MAX_TOKENS=250` (was defaulting to 100)

## Gender-Aware Greetings (v10.7.2)

- Student model has `gender` field ('M' or 'F')
- Greeting: "Kaise ho" for boys, "Kaisi ho" for girls
- Debug output hidden behind `?debug=true` URL param (students see clean UI)

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

### Inline Eval State Must Respect Hint Level (v10.6.7)
- hint_level >= 3 → FULL_SOLUTION, >= 2 → HINT_2, else → HINT_1
- Blindly setting HINT_1 caused death spiral (fixed in v10.6.7)

## Telugu Support (v10.6.4)

- `_lang()` helper in instruction_builder.py — 48 uses
- Telugu pre-scan in BOTH endpoints (before classifier)
- TTS language mapping: telugu → te-IN
- `LANG_INSTRUCTIONS["telugu"]` with full Telugu script enforcement
- Triggers: "telugu", "తెలుగు", "తెలుగులో"
- Telugu meta-question patterns added in v10.6.9

## Question Picker (v10.6.0, memory.py)

- `pick_next_question()` with HARD RULES:
  1. WHERE level = current_level (strict)
  2. Exclude current question + all previously answered
  3. If exhausted at level → reuse same-level (excluding current)
  4. If no questions at level → try adjacent levels (up first, then down)
- Questions upserted from ch1_square_and_cube.py on startup via `_upsert_questions()`
- `prefer_square_first=True` on first question after chapter intro (v10.7.0)

## Dual FSM Architecture (Tech Debt)

- **v7.3 FSM** (`state_machine.py`): Controls teaching flow, returns Action objects
- **v8.0 FSM** (`fsm/transitions.py`): Side effects only (language, empathy)
- Both run on every request in both endpoints
- v7.3 result drives action, v8.0 result drives session field updates
- Unification deferred to Phase 2

## Critical Lessons Learned

### 1. Session Field Updates Need db.commit()
- `session.X = value` does NOT persist until `db.commit()`
- Missing commit was root cause of teaching_turn loop bug (v10.0.2)

### 2. Every _sys() Call Needs session_context
- `_sys(extra, session_context=ctx, question_data=q)` — no exceptions
- The #1 recurring bug pattern in the codebase

### 3. NEXT_QUESTION is Always Transient (v10.6.4)
- After FSM returns NEXT_QUESTION, immediately overwrite to WAITING_ANSWER

### 4. Four Brevity Locks Must Change Together (v10.7.1)
- config.py, enforcer.py, student.py TTS limits, instruction_builder.py prompts
- Changing only one gets overridden by the other three

### 5. Claude Code Unreliable for Doc Edits (Anti-pattern #24)
- Changes version strings, skips structural content updates
- Solution: CTO produces verified files, Hemant pastes manually

### 6. Meta-Question Keywords Must Cover All Languages (Anti-pattern #29)
- `_build_answer_meta_question()` checks keywords like "chapter", "topic"
- Missing "ncert", "textbook", "kitab" → falls to more_examples → gives laddoo examples
- Always add keywords for every supported language

### 7. Question Level Rules
- "What is X times Y?" → Level 1
- "What is the square/cube of X?" → Level 2
- "What is √X?" / "What is ∛X?" → Level 3
- "Is X a perfect square?", pattern questions → Level 4
- Word problems, prime factorisation, methods → Level 5

### 8. clean_for_tts() Rules
- Dashes → commas, fractions → words, operators → words
- Strip "You asked" / "Aapne poocha" framing (v10.6.7)

## Key File Locations

| Purpose | File | Line |
|---------|------|------|
| Session start | `student.py` | ~170 (start_session) |
| Streaming endpoint | `student.py` | ~1130 (message_stream) |
| Non-streaming endpoint | `student.py` | ~440 (message) |
| Inline eval parsing | `student.py` | ~1856 (generator finally) |
| Level advancement | `student.py` | ~807 (non-stream), ~1862 (stream) |
| V10 DIDI_BASE | `instruction_builder.py` | ~30-70 |
| Meta-Q keyword check | `instruction_builder.py` | ~753 |
| Chapter intro content | `ch1_square_and_cube.py` | ~27 (CHAPTER_INTRO dict) |
| Question picker | `memory.py` | ~127 (pick_next_question) |
| Pilot student seed | `main.py` | ~250 (_seed_pilot_students) |
| Teaching config | `config.py` | ~90 (MAX_TEACHING_WORDS etc.) |
| Debug toggle | `web/student.html` | ?debug=true URL param |
| Health detail | `main.py` | /health/detail endpoint |

## Bug Fix Patterns

### Teaching Too Short
1. Check ALL FOUR: config.py limits, enforcer.py is_teaching, student.py TTS chars, instruction_builder.py prompt
2. All four must agree — changing one gets overridden by the others

### Meta-Question Ignored
1. Check `_build_answer_meta_question()` keyword list (~line 753)
2. Missing keyword → falls to meta_type=="more_examples" → math examples instead of answering
3. Add the keyword in all languages (Hindi, English, Telugu)

### Hint Loop / Death Spiral
1. Check inline eval state override in generator finally block
2. Ensure hint_level >= 3 → FULL_SOLUTION, >= 2 → HINT_2, else → HINT_1

### Level System Issues
1. Check question level tags in ch1_square_and_cube.py
2. Verify _upsert_questions() ran (check /health/detail)
3. Check pick_next_question() level filtering in memory.py
