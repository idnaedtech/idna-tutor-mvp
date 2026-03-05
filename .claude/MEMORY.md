# IDNA EdTech Project Memory

## Current Version
- **v10.0.2** deployed to Railway (commit eca1093)
- 300 tests passing (280 core + 20 P0 teaching flow tests)
- Models: gpt-4.1 (brain), gpt-4.1-mini (classifier)
- **All 5 P0 smoke tests passing on production**

## V10 Architecture (GPT-4.1 Role Change)

### Core Change: Voice Box → Teacher
- Old: 117-line rule-based DIDI_BASE with harsh labels ("ANSWER INCORRECT")
- New: ~40-line teacher persona with warm identity ("let's think differently")
- GPT-4.1 decides HOW to teach, not just rephrases scripts

### Key V10 Files
| File | Purpose |
|------|---------|
| `app/tutor/strings.py` | Centralized multilingual strings (4 languages) |
| `app/tutor/instruction_builder.py` | New DIDI_BASE, LANG_INSTRUCTIONS dict |

### V10 Patterns
- **Echo back**: Every response starts with "You said X..." or "So you're finding..."
- **Gentle wrong handling**: "Hmm, let's think differently..." NOT "incorrect"
- **Student choice**: "Would you like an example, or shall we try a question?"
- **Content bank as truth**: LLM rephrases verified content, doesn't invent

### strings.py Usage
```python
from app.tutor.strings import get_text
greeting = get_text("warmup_greeting", "english", name="Priya")
# Returns: "Hey Priya! How are you doing today? How was school?"
```
- Supports: english, hindi, hinglish, telugu
- Falls back to English for unknown languages

## P0 Teaching Loop Fixes (v10.0.1 + v10.0.2)

Database forensics on 872 sessions revealed 5 bugs. Fixed in v10.0.1, with critical persistence fix in v10.0.2.

### Bug 1: CONCEPT_REQUEST Didn't Increment teaching_turn
- **Root cause**: `state_machine.py` line 214-219 passed `teaching_turn=teaching_turn` (same value)
- **Evidence**: Sessions with confusion_count=6 but teaching_turn=0
- **Fix (v10.0.1)**: CONCEPT_REQUEST now increments teaching_turn, forces WAITING_ANSWER at turn 3
- **File**: `app/tutor/state_machine.py:214-232`
- **CRITICAL (v10.0.2)**: teaching_turn wasn't persisting to DB — see lesson #15 below

### Bug 2: Nudge Hardcoded Hindi
- **Root cause**: Non-streaming endpoint line 552 had hardcoded Hindi nudge
- **Fix**: Now checks `session.language_pref` like streaming endpoint does
- **File**: `app/routers/student.py:552`

### Bug 3: Devanagari Meta-Question Patterns Missing
- **Root cause**: Sarvam STT outputs full Devanagari (`कौन सा चैप्टर`) but patterns had mixed script
- **Fix**: Added 7 new Devanagari patterns for chapter/topic detection
- **File**: `app/tutor/preprocessing.py:159-175`

### Bug 4: Emotional Distress Not Detected
- **Root cause**: No detection for "उदास", "sad", "tired" at session start
- **Fix**: Added `detect_emotional_distress()` + `student_emotional` flag in session_ctx
- **Files**: `preprocessing.py`, `student.py` (both endpoints), `instruction_builder.py`
- **Note**: Only works on streaming endpoint (non-streaming uses v9 handler path)

### Bug 5: Response Length Exceeds Voice Limit
- **Root cause**: Content bank has full solutions, LLM reproduces verbatim
- **Fix**: Length guard — content >200 chars triggers summarization instruction
- **File**: `app/tutor/instruction_builder.py:380-388`

### Also Fixed: DIDI_NO_PRAISE/DIDI_PRAISE_OK Undefined
- These V10-deleted constants were still referenced in `_build_give_hint` and `_build_pick_next_question`
- Replaced with empty string `""` — persona handles praise/no-praise naturally

## Critical Lessons Learned

### 1. Never Bypass Verification Gates
- verify.py must show 22/22 PASS before push
- Start local server (`python -m uvicorn app.main:app --port 8000`) for endpoint tests
- Never modify pre-push hooks to use `--quick` mode to bypass failures

### 2. Always Commit After Setting Session Fields
- `session.language_pref = value` must be followed by `db.commit()`
- Both classifier path AND FSM path need commits
- Language persistence bugs often caused by missing commits

### 3. V10 Deleted Functions (Don't Import!)
- `_get_confusion_instruction()` - deleted in V10, confusion embedded in persona
- `DIDI_NO_PRAISE`, `DIDI_PRAISE_OK` - deleted, natural handling now
- `LANG_ENGLISH`, `LANG_HINDI`, `LANG_HINGLISH` - replaced by `LANG_INSTRUCTIONS` dict

### 4. GREETING State Flow (v9.0.6+)
- GREETING accepts ALL engagement signals, not just ACK
- Only STOP, COMFORT, LANGUAGE_SWITCH, REPEAT stay in GREETING
- Everything else (ACK, IDK, CONCEPT_REQUEST, ANSWER, TROLL, GARBLED, UNCLEAR) → TEACHING
- Teaching content delivered in TEACHING state, not GREETING

### 5. Version Bump Checklist
- Update `app/main.py` in THREE places: `version=`, `/health` endpoint, and startup log
- Kill cached python processes before testing (`taskkill //F //IM python.exe`)
- Wait ~60s for Railway deployment after push

### 6. Dual FSM Architecture (CRITICAL)
- **Two FSMs run in parallel** — this is tech debt, not design
- `app/tutor/state_machine.py` (v7.3) — controls actual state transitions
- `app/fsm/transitions.py` (v8.0) — used by handlers, has fallback logic
- Non-streaming endpoint: v8.0 handler overrides state at line 790
- **Both must be updated** when fixing GREETING transitions

### 7. Language Pre-Scan (v9.0.7+)
- Language switch triggers checked BEFORE classifier runs
- Set in both streaming AND non-streaming endpoints
- Triggers: "english", "hindi", "इंग्लिश", "हिंदी", etc.
- Prevents classifier from picking wrong category for "teach me in English"

### 8. v8.0 FSM Fallback (v9.0.8+)
- Unknown categories (like UNCLEAR) fall back to GARBLED by default
- GREETING + GARBLED → stays in GREETING (trap!)
- Fix: GREETING + unknown → map to ACK → transitions to TEACHING

### 9. Arithmetic Guardrail (v9.0.10)
- LLMs hallucinate math (e.g., "8²=74") when computing from memory
- Fix: Inject verified data into system prompt via `_build_teach_concept()`
- `_VERIFIED_SQUARES` dict has pre-computed values for each skill_key
- Arithmetic rule in `_sys()` tells LLM to NEVER compute from memory

### 10. Correction Detection (v9.0.10)
- Student saying "that's wrong"/"galat" must trigger special handling
- Correction triggers detected in student.py (both endpoints)
- `session_ctx["student_is_correcting"]` flag set
- `build_prompt()` intercepts before regular builder → apology + recalculation
- Language-aware: English apology vs Hindi apology based on `language_pref`

### 11. V10 Language Format Change
- Old format: `"LANGUAGE SETTING: english"` with `"Zero Hindi words"`
- New format: `"LANGUAGE: Respond ENTIRELY in English. No Hindi words."`
- Tests must check for `"LANGUAGE:"` not `"LANGUAGE SETTING:"`
- `LANG_INSTRUCTIONS` dict has full instruction for each language

### 12. V10 Content Bank as Truth
- `_build_teach_concept()` now says "Rephrase" not "Teach"
- When content is missing, log warning + use `get_text("no_content_available")`
- LLM rephrases verified content, doesn't invent new math facts
- Verified squares/cubes still injected via `_VERIFIED_SQUARES` dict

### 13. CONCEPT_REQUEST Must Increment teaching_turn (v10.0.1)
- Classifier returns CONCEPT_REQUEST for "I didn't understand, explain"
- Previously teaching_turn stayed at 0 → Turn 0 content repeated forever
- Fix: CONCEPT_REQUEST increments like IDK/REPEAT, forces WAITING_ANSWER at turn 3
- Database evidence: sessions with confusion_count=6 but teaching_turn=0

### 14. Emotional Distress Detection (v10.0.1)
- Patterns: उदास, sad, tired, bad day, mood kharab, etc.
- `detect_emotional_distress()` in preprocessing.py
- `session_ctx["student_emotional"]` flag passed to build_prompt()
- build_prompt() intercepts BEFORE regular builder → comfort response
- Only works on streaming endpoint (dual-pipeline tech debt)

### 15. Session Field Updates Need Immediate db.commit() (v10.0.2)
- **Critical pattern**: Setting `session.X = value` does NOT persist until `db.commit()`
- **Bug example**: teaching_turn was set at line 1303 but commit was at line 1284 (BEFORE the update)
- **Fix**: Add `db.commit()` immediately after ANY session field update
- **Affected fields**: teaching_turn, language_pref, confusion_count, state, etc.
- **Both endpoints**: Non-streaming (sync `db.commit()`) and streaming (`await run_in_threadpool(lambda: db.commit())`)

## Key File Locations

| Purpose | File |
|---------|------|
| Session start | `app/routers/student.py:170` (start_session) |
| Language mapping | `app/routers/student.py:91` (get_tts_language) |
| V10 greeting | `app/routers/student.py:236` (uses strings.py) |
| Centralized strings | `app/tutor/strings.py` (STRINGS dict, get_text) |
| V10 DIDI_BASE | `app/tutor/instruction_builder.py:30-70` |
| LANG_INSTRUCTIONS | `app/tutor/instruction_builder.py:72-77` |
| v8.0 FSM transitions | `app/fsm/transitions.py` |
| v7.3 state machine | `app/tutor/state_machine.py` |
| Verified squares data | `app/tutor/instruction_builder.py:271-277` (_build_teach_concept) |
| V10 persona tests | `tests/test_v10_persona.py` |
| P0 teaching flow tests | `tests/test_p0_teaching_flow.py` |
| Emotional distress detector | `app/tutor/preprocessing.py:156-187` |

## Bug Fix Patterns

### Language Not Persisting
1. Check classifier path has `db.commit()` after setting `language_pref`
2. Check FSM path has `db.commit()` after setting `language_pref`
3. Both paths must commit independently

### GREETING State Trap
1. Check v7.3 state_machine.py GREETING handler accepts category
2. Check v8.0 fsm/transitions.py has fallback for unknown categories
3. For GREETING: unknown should map to ACK (→ TEACHING), not GARBLED (→ GREETING)

### State Not Transitioning
1. Non-streaming: handler_state overrides new_state at line 790
2. Streaming: state saved immediately after transition() at line 1077+
3. Check which FSM is actually controlling the flow

### LLM Hallucinating Math (v9.0.10)
1. LLMs compute from memory and make errors (e.g., "8²=74")
2. Fix: Never let LLM compute — inject verified data via `_VERIFIED_SQUARES`
3. Add arithmetic guardrail to system prompt via `_sys()`
4. Student correction triggers must be handled immediately in `build_prompt()`

### Student Correction Ignored
1. "That's wrong" / "galat" must be detected in student.py
2. `_is_correction` flag must propagate to `session_ctx["student_is_correcting"]`
3. `build_prompt()` must check this flag BEFORE calling regular builder
4. Response must be language-aware apology + recalculation

### V10 Test Failures After Format Change
1. Check tests import correct functions (not deleted ones)
2. Update assertions: `"LANGUAGE:"` not `"LANGUAGE SETTING:"`
3. Confusion handling is in persona, not separate function
4. Check for `"No Hindi"` not `"Zero Hindi words"`

### Adding New Language to V10
1. Add entries to `STRINGS` dict in `app/tutor/strings.py`
2. Add language to `LANG_INSTRUCTIONS` dict in `instruction_builder.py`
3. Add to `LANG_NORMALIZE` dict in `student.py` (greeting)
4. Run `test_v10_persona.py` to verify coverage

### Teaching Loop Infinite (v10.0.1)
1. Check if category increments teaching_turn in state_machine.py
2. CONCEPT_REQUEST, IDK, REPEAT should ALL increment teaching_turn
3. At teaching_turn >= 3, must force transition to WAITING_ANSWER
4. Database evidence: high confusion_count but teaching_turn=0 = bug

### Emotional Distress Not Acknowledged
1. Check `detect_emotional_distress()` patterns in preprocessing.py
2. Check `preprocess_result.emotional_distress` is set
3. Check `_student_emotional` flag is set in BOTH endpoints
4. Check `session_ctx["student_emotional"]` is passed to build_prompt()
5. Check build_prompt() intercepts BEFORE regular builder

### 15. teaching_turn Not Persisting (v10.0.2 CRITICAL)
- **Symptom**: FSM correctly increments teaching_turn but value resets to 0 on next request
- **Root cause**: `db.commit()` at line 1284 happened BEFORE teaching_turn was set (lines 1299-1304)
- **Fix**: Added `db.commit()` immediately after setting `session.teaching_turn` in BOTH endpoints
- **Files**: `app/routers/student.py:761-763` (non-streaming), `:1302-1305` (streaming)
- **Pattern**: ANY session field update must be followed by `db.commit()` to persist
- **Verification**: Smoke test must show state transition to WAITING_ANSWER after 3 IDKs
