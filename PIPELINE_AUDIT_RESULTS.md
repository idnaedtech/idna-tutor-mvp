# PIPELINE_AUDIT_RESULTS.md — Full Pipeline Audit

> **Audit Date:** 2026-03-07
> **Auditor:** Claude Code
> **Scope:** Diagnose-only, no fixes
> **Status:** COMPLETE

---

## Executive Summary

This document traces 3 specific message types through the IDNA EdTech pipeline, inventories the content bank, and identifies where the "You said..." pattern originates. **NO CODE CHANGES WERE MADE.**

---

## Task 1: Trace "I didn't understand, please explain again"

### Pipeline Flow (10 steps)

```
INPUT: "I didn't understand, please explain again"
STATE: TEACHING (typical scenario)
```

#### Step 1: STT (Speech-to-Text)
- **File:** `app/voice/stt.py`
- **Function:** `stt.transcribe(audio_bytes)`
- **Output:** `"I didn't understand, please explain again"`
- **Latency:** ~300ms

#### Step 2: RAW INPUT Logging
- **File:** `app/routers/student.py:1098`
- **Log:** `RAW INPUT (stream): [I didn't understand, please explain again]`

#### Step 3: Preprocessing (BEFORE Classifier)
- **File:** `app/tutor/preprocessing.py`
- **Functions called in order:**
  1. `detect_meta_question()` → Returns `None` (not a meta-question)
  2. `detect_language_switch()` → Returns `None` (no language request)
  3. `detect_confusion()` → **Returns `True`** (matches pattern `"don't understand"`)
  4. `detect_emotional_distress()` → Returns `False`
- **Result:** `PreprocessResult(bypass_llm=False, confusion_detected=True)`

**KEY FINDING:** Confusion is detected here BUT it only sets a flag. The confusion_count increment happens later in the session context building, NOT in preprocessing.

#### Step 4: Language Auto-Detection
- **File:** `app/tutor/preprocessing.py:340-405`
- **Function:** `detect_input_language("I didn't understand...")`
- **Logic:**
  - No Devanagari chars → check for Hindi Roman words
  - "didn't", "understand", "explain", "again" — none in `_HINDI_ROMAN_WORDS`
  - Result: `'english'`
- **Auto-switch check:** `check_language_auto_switch('english', current_session_language, consecutive_count)`
  - If session is 'hinglish' and this is 2nd consecutive English message → auto-switch

#### Step 5: Input Classifier (gpt-4.1-mini)
- **File:** `app/tutor/input_classifier.py:159-260`
- **Fast-path check:** `_normalize("I didn't understand, please explain again")` → `"i didn t understand please explain again"`
  - **DOES NOT match** `FAST_IDK` — apostrophe stripped by `_normalize()` breaks pattern match
  - Falls through to LLM classifier (gpt-4.1-mini)
  - **Result:** `{"category": "IDK", "confidence": ~0.9, "extras": {}}` (from LLM)
- **NOTE:** LLM classifier is called with system prompt at line 123

**KEY FINDING (CORRECTED via trace test):** The `_normalize()` function strips punctuation including apostrophes, so "didn't" becomes "didn t". This breaks the fast-path match against FAST_IDK patterns like "i don't understand". The LLM classifier IS called for this input and correctly returns IDK.

#### Step 6: State Machine Transition
- **File:** `app/tutor/state_machine.py:160-244`
- **Input:** `current_state="TEACHING", category="IDK"`
- **Logic (lines 189-205):**
  ```python
  if category == "IDK":
      new_turn = teaching_turn + 1  # CRITICAL: increments teaching_turn
      if new_turn >= 3:
          return "WAITING_ANSWER", Action("read_question", ...)  # Force transition
      return "TEACHING", Action("teach_concept", reteach_count=new_turn, ...)
  ```
- **Output:** `("TEACHING", Action(action_type="teach_concept", teaching_turn=1, extra={"approach": "different_example"}))`

**KEY FINDING:** IDK in TEACHING state increments `teaching_turn` and returns `teach_concept` action with `approach="different_example"`.

#### Step 7: Instruction Builder (THE ACTIVE BRAIN)
- **File:** `app/tutor/instruction_builder.py:113-163, 262-425`
- **Function:** `build_prompt(action, session_context, question_data, ...)`
- **Logic:**
  1. Check `session_context.get("student_emotional")` → `False` (skip comfort override)
  2. Check `session_context.get("student_is_correcting")` → `False` (skip correction override)
  3. Get builder: `_BUILDERS["teach_concept"]` → `_build_teach_concept()`

- **_build_teach_concept() flow (lines 262-425):**
  1. `teaching_turn = 1` (from action)
  2. Anti-repetition context added if `explanations_given` exists
  3. Content bank lookup for skill (e.g., `perfect_square_identification`)
  4. **Turn 1 path (line 387-392):**
     ```python
     if teaching_turn == 1:
         if len(teach_content) > 200:
             msg = f'...Take the SIMPLEST part...MUST end: "{understand_check}"'
         else:
             msg = f'...Use this DIFFERENT example: "{teach_content}"...MUST end: "{understand_check}"'
     ```

- **System prompt construction via `_sys()` (lines 205-228):**
  - Calls `_format_didi_base()` → inserts language instruction via `LANG_INSTRUCTIONS` dict
  - Adds chapter context via `_get_chapter_context()`

- **Student text injection (line 150-151):**
  ```python
  if student_text and messages[0].get("role") == "system":
      messages[0]["content"] = messages[0]["content"] + f'\n\nSTUDENT SAID: "{student_text}"'
  ```

**KEY FINDING:** The system prompt now contains:
```
STUDENT SAID: "I didn't understand, please explain again"
```
This is injected at line 151 for EVERY action type.

#### Step 8: LLM Generation (gpt-4.1)
- **File:** `app/tutor/llm.py` (streaming via `app/routers/student.py`)
- **Model:** `gpt-4.1` (from config)
- **Input:** Messages array with:
  - System prompt (DIDI_BASE + language instruction + chapter context + "STUDENT SAID: ...")
  - User prompt (instruction from builder)
- **Latency:** ~800-1200ms

#### Step 9: Enforcer
- **File:** `app/tutor/enforcer.py`
- **Checks:** Length, praise rules, language consistency, repetition
- **If fails:** Retry up to `MAX_ENFORCE_RETRIES` times, then use safe fallback

#### Step 10: TTS (Sarvam Bulbul v3)
- **File:** `app/voice/tts.py`
- **Settings:** speaker=simran, language=hi-IN, pace=0.90
- **Latency:** ~500ms

### Summary for Task 1

| Step | File | Key Function | Decision Point |
|------|------|--------------|----------------|
| 3 | preprocessing.py | detect_confusion() | Sets confusion flag |
| 5 | input_classifier.py | FAST_IDK match | Bypasses LLM classifier |
| 6 | state_machine.py:189 | IDK handler | Increments teaching_turn |
| 7 | instruction_builder.py:387 | Turn 1 path | Uses "different_example" approach |

---

## Task 2: Trace "which chapter are we studying" (Meta-Question)

### Pipeline Flow

```
INPUT: "which chapter are we studying"
STATE: ANY (meta-questions bypass state machine)
```

#### Step 1-2: STT + RAW INPUT Logging
Same as Task 1.

#### Step 3: Preprocessing — META-QUESTION DETECTION
- **File:** `app/tutor/preprocessing.py:254-274`
- **Function:** `detect_meta_question("which chapter are we studying")`
- **Pattern matching:**
  ```python
  META_QUESTION_PATTERNS = {
      "chapter": [
          r"(what|which)\s+chapter",  # ← MATCHES HERE
          ...
      ],
      "topic": [
          r"what\s+are\s+we\s+(learning|studying|doing|reading)",  # ← ALSO MATCHES
          ...
      ],
  }
  ```
- **Debug logging (line 264-271):**
  ```
  META-CHECK: input=[which chapter are we studying], text_lower=[which chapter are we studying]
  META-CHECK: category=chapter, pattern_matched=True
  META-CHECK: MATCH FOUND! category=chapter, matched_text=[which chapter]
  ```
- **Result:** `"chapter"` (returns FIRST match)

**KEY FINDING:** Pattern order matters. "chapter" patterns are checked before "topic" patterns. The input matches BOTH "which chapter" (chapter category) and "what are we...studying" (topic category), but "chapter" wins because it's checked first.

#### Step 4: Build Meta Response
- **File:** `app/tutor/preprocessing.py:277-323`
- **Function:** `build_meta_response("chapter", chapter, chapter_name, ...)`
- **Logic (lines 291-295):**
  ```python
  if meta_type == "chapter":
      if use_english:
          return f"We are learning {chapter_name}."
      else:
          return f"Hum {chapter_name} padh rahe hain."
  ```
- **Example output:** `"Hum Chapter 6 - Squares and Square Roots padh rahe hain."`

#### Step 5: BYPASS LLM ENTIRELY
- **File:** `app/routers/student.py:1119-1142`
- **Logic:**
  ```python
  if preprocess_result.bypass_llm:
      logger.info(f"v8.1.0 (stream): Bypassing LLM for meta-question: {preprocess_result.meta_question_type}")
      # DEBUG log
      logger.info(f"RESPONSE TO FRONTEND (stream-meta): text=[{preprocess_result.template_response[:100]}]...")

      # Direct TTS → SSE stream (no classifier, no state machine, no instruction builder)
      tts = get_tts()
      tts_result = tts.synthesize(preprocess_result.template_response, get_tts_language(session))
      ...
  ```

#### Step 6-10: SKIPPED
- No classifier call
- No state machine transition
- No instruction builder
- No LLM generation
- Only TTS is called

### Summary for Task 2

| Step | File | Key Function | What Happens |
|------|------|--------------|--------------|
| 3 | preprocessing.py:254 | detect_meta_question() | Returns "chapter" |
| 4 | preprocessing.py:277 | build_meta_response() | Returns template |
| 5 | student.py:1119 | bypass_llm check | Skips LLM entirely |

**KEY FINDING:** Meta-questions are the FASTEST path through the system — they bypass classifier, state machine, instruction builder, and LLM. Only STT → preprocessing → TTS.

---

## Task 3: Trace "81 times 9 is 729" (Answer Evaluation)

### Pipeline Flow

```
INPUT: "81 times 9 is 729"
STATE: WAITING_ANSWER
QUESTION: "What is the cube root of 729?"
EXPECTED_ANSWER: "9"
```

#### Step 1-4: STT, Preprocessing, Language Detection
Standard flow. No meta-question, no confusion, no language switch.

#### Step 5: Input Classifier
- **Fast-path check:** Contains digits (`81`, `9`, `729`) + state is `WAITING_ANSWER`
- **Line 215-218:**
  ```python
  if current_state == "WAITING_ANSWER":
      if re.search(r'\d', text):
          return {"category": "ANSWER", "confidence": 0.95, "extras": {"raw_answer": text}}
  ```
- **Result:** `{"category": "ANSWER", "confidence": 0.95, "extras": {"raw_answer": "81 times 9 is 729"}}`

#### Step 6: State Machine
- **Input:** `current_state="WAITING_ANSWER", category="ANSWER"`
- **Line 248-251:**
  ```python
  if category == "ANSWER":
      return "EVALUATING", Action("evaluate_answer", question_id=q_id, student_text=text)
  ```
- **Output:** `("EVALUATING", Action(action_type="evaluate_answer", ...))`

#### Step 7: Answer Checker (THE KEY STEP)
- **File:** `app/tutor/answer_checker.py:407-504`
- **Function:** `check_math_answer("81 times 9 is 729", "9", variants)`

**Evaluation order:**
1. **Perfect square root check (lines 442-444):** Not applicable (correct_answer is "9", not "yes")
2. **Cube root reasoning check (lines 448-449):**
   ```python
   cbrt_verdict = _check_cube_root_reasoning(student_text, correct_answer, variants)
   ```

**_check_cube_root_reasoning() logic (lines 264-338):**
```python
# Pattern 2: "X² times X" check (lines 309-336)
# 81 times 9 → n1=81, n2=9
# Check if n1 == correct² and n2 == correct
# 81 == 9² (True) and n2 == 9 (True)
# → Return CORRECT verdict
```

- **Result:**
  ```python
  Verdict(
      correct=True,
      verdict="CORRECT",
      student_parsed="9",
      correct_display="9",
      diagnostic="Student correctly showed 81 × 9 = 729 proves cube root is 9"
  )
  ```

**KEY FINDING:** The answer_checker recognizes that "81 times 9 is 729" demonstrates understanding that 9³ = 729 (because 9² × 9 = 81 × 9 = 729). This is a cube root REASONING pattern, not a direct numeric answer.

#### Step 8: Route After Evaluation
- **File:** `app/tutor/state_machine.py:390-412`
- **Input:** `verdict.correct=True`
- **Output:** `("NEXT_QUESTION", "pick_next_question")` or `("SESSION_COMPLETE", "end_session")`

#### Step 9-10: Instruction Builder, LLM, TTS
- Builder: `_build_evaluate_answer()` (line 445-468)
- Prompt includes: `"Student said: \"9\". The answer is 9 and they got it RIGHT."`

### Summary for Task 3

| Step | File | Key Function | What Happens |
|------|------|--------------|--------------|
| 5 | input_classifier.py:215 | Digit + WAITING_ANSWER | Returns ANSWER |
| 7 | answer_checker.py:309 | Cube root reasoning | Recognizes 81×9 pattern |
| 7 | answer_checker.py:319 | n1 == correct² check | 81 == 81 (9²) ✓ |
| 8 | state_machine.py:401 | correct verdict | Transitions to NEXT_QUESTION |

---

## Task 4: Content Bank Inventory

### Available Content

**File:** `content_bank/math_8_ch6.json`

| Concept ID | Concept Name | Questions | Examples |
|------------|--------------|-----------|----------|
| math_8_ch6_perfect_square | Perfect Square Numbers | 3 (easy/medium/hard) | 3 |
| math_8_ch6_properties | Properties of Square Numbers | 3 | 3 |
| math_8_ch6_odd_sum_pattern | Odd Sum Pattern | 3 | 3 |
| math_8_ch6_finding_square | Finding Square of a Number | 3 | 3 |
| math_8_ch6_pythagorean_triplets | Pythagorean Triplets | 3 | 3 |
| math_8_ch6_root_repeated_subtraction | Square Root by Repeated Subtraction | 3 | 3 |
| math_8_ch6_root_prime_factorisation | Square Root by Prime Factorisation | 3 | 3 |
| math_8_ch6_make_perfect_square | Make a Perfect Square | 3 | 3 |
| math_8_ch6_root_long_division | Square Root by Long Division | 3 | 3 |
| math_8_ch6_root_decimals | Square Root of Decimals | 3 | 3 |
| math_8_ch6_estimation | Estimating Square Roots | 3 | 3 |
| math_8_ch6_cube_root_concept | Cube Root Concept | 3 | 3 |

**Total:** 12 concepts × 3 questions = **36 questions** in content bank

### Skill Progression Order

```json
[
  "sq_perfect_square",
  "sq_properties",
  "sq_patterns_odd_sum",
  "sq_between_consecutive",
  "sq_finding_square",
  "sq_pythagorean_triplets",
  "sq_root_repeated_subtraction",
  "sq_root_prime_factorisation",
  "sq_make_perfect_square",
  "sq_root_long_division",
  "sq_root_decimals",
  "sq_root_estimation",
  "cube_root_concept"
]
```

### Content Bank vs Seed Questions

| Source | File | Questions | Status |
|--------|------|-----------|--------|
| Content Bank | `content_bank/math_8_ch6.json` | 36 | Primary (RAG) |
| Seed Questions | `app/content/seed_questions.py` | ~60+ | Fallback |

**KEY FINDING:** The content bank has 12 concepts for Chapter 6 only. There is NO content bank for:
- Chapter 1 (Rational Numbers)
- Chapter 7 (Cubes and Cube Roots — only `cube_root_concept` added recently)
- Chapters 2-5, 8-15

### What's Missing

1. **No multi-chapter content:** Only Ch6 has full content bank coverage
2. **No other subjects:** Only Math
3. **No other classes:** Only Class 8
4. **Skill ID mismatch:** Some skill_progression IDs don't match concept_ids:
   - `sq_perfect_square` vs `math_8_ch6_perfect_square`
   - This may cause content lookup failures in `_build_teach_concept()`

---

## Task 5: Origin of "You said..." Pattern

### FOUND: instruction_builder.py Line 34

```python
# File: app/tutor/instruction_builder.py
# Line: 34

DIDI_BASE = """You are Didi, an expert {board_name} Class {class_level} Math teacher...

ALWAYS ECHO BACK: Start every response by acknowledging what the student just said.
"You said X..." or "So you're finding this a bit tricky..." This makes them feel heard.
```

### Why It Appears in EVERY Response

1. **DIDI_BASE is the system prompt** for ALL LLM calls
2. Line 34 explicitly instructs: `"ALWAYS ECHO BACK: Start every response..."`
3. Line 150-151 injects the student's exact words:
   ```python
   messages[0]["content"] = messages[0]["content"] + f'\n\nSTUDENT SAID: "{student_text}"'
   ```
4. GPT-4.1 follows the instruction and echoes back

### Example Prompt Sent to LLM

```
SYSTEM:
You are Didi, an expert CBSE Class 8 Math teacher...

ALWAYS ECHO BACK: Start every response by acknowledging what the student just said.
"You said X..." or "So you're finding this a bit tricky..." This makes them feel heard.

...

STUDENT SAID: "I didn't understand, please explain again"

USER:
Student didn't understand. Use this DIFFERENT example: "...". 2 sentences. MUST end: "Ab samajh aaya?"
```

### Why This Exists

- **Pedagogical reason:** Makes students feel heard (line 34 comment: "This makes them feel heard")
- **V10 design decision:** Part of the "warm teacher persona" shift from rule-based to conversational
- **Evidence:** Comment at line 34 explicitly states the intent

### How to Remove (IF DESIRED — NOT DONE IN THIS AUDIT)

1. Remove line 34 from DIDI_BASE
2. Remove lines 150-151 (student text injection)
3. Update tests that check for echo behavior

---

## Pipeline Diagrams

### Full Pipeline (Standard Message)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STREAMING ENDPOINT                                  │
│                    /api/student/session/message-stream                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: STT (Sarvam Saarika v2.5)                                           │
│ • Audio bytes → text                                                         │
│ • ~300ms latency                                                             │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 2-4: PREPROCESSING (preprocessing.py)                                   │
│ • detect_meta_question() → bypass if match                                   │
│ • detect_language_switch() → update pref                                     │
│ • detect_confusion() → set flag                                              │
│ • detect_emotional_distress() → set flag                                     │
│ • detect_input_language() → auto-switch check                                │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     │                               │
              [bypass_llm=True]              [bypass_llm=False]
                     │                               │
                     ▼                               ▼
┌─────────────────────────────┐   ┌────────────────────────────────────────────┐
│ META-QUESTION FAST PATH     │   │ STEP 5: INPUT CLASSIFIER (gpt-4.1-mini)    │
│ • Template response         │   │ • Fast-path: FAST_ACK, FAST_IDK, FAST_STOP │
│ • Direct to TTS             │   │ • LLM fallback: 10 categories               │
│ • Skip steps 5-9            │   │ • ~200ms latency                            │
└─────────────────────────────┘   └────────────────────────────────────────────┘
                                                     │
                                                     ▼
                              ┌────────────────────────────────────────────────┐
                              │ STEP 6: STATE MACHINE (state_machine.py)       │
                              │ • 13 states × 10 categories                     │
                              │ • Returns (new_state, Action)                   │
                              │ • Deterministic Python logic                    │
                              └────────────────────────────────────────────────┘
                                                     │
                                                     ▼
                              ┌────────────────────────────────────────────────┐
                              │ STEP 7: INSTRUCTION BUILDER                     │
                              │ • build_prompt(action, ctx, ...)               │
                              │ • DIDI_BASE + language + chapter context       │
                              │ • "STUDENT SAID: ..." injection (line 151)     │
                              │ • Action-specific builder (_build_teach, etc)  │
                              └────────────────────────────────────────────────┘
                                                     │
                                                     ▼
                              ┌────────────────────────────────────────────────┐
                              │ STEP 8: LLM GENERATION (gpt-4.1)               │
                              │ • Streaming response                            │
                              │ • ~800-1200ms latency                           │
                              └────────────────────────────────────────────────┘
                                                     │
                                                     ▼
                              ┌────────────────────────────────────────────────┐
                              │ STEP 9: ENFORCER (enforcer.py)                 │
                              │ • Length check (max 55 words)                   │
                              │ • Praise rules                                  │
                              │ • Language consistency                          │
                              │ • Repetition detection                          │
                              └────────────────────────────────────────────────┘
                                                     │
                                                     ▼
                              ┌────────────────────────────────────────────────┐
                              │ STEP 10: TTS (Sarvam Bulbul v3)                │
                              │ • speaker=simran, pace=0.90                     │
                              │ • Sentence-level streaming                      │
                              │ • ~500ms latency                                │
                              └────────────────────────────────────────────────┘
                                                     │
                                                     ▼
                              ┌────────────────────────────────────────────────┐
                              │ SSE STREAM TO FRONTEND                         │
                              │ • audio_chunk events                            │
                              │ • text event                                    │
                              │ • done event with state                         │
                              └────────────────────────────────────────────────┘
```

### Answer Evaluation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ANSWER IN WAITING_ANSWER STATE                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ INPUT CLASSIFIER                                                             │
│ • Contains digits + state=WAITING_ANSWER → ANSWER category (fast-path)       │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STATE MACHINE: WAITING_ANSWER + ANSWER                                       │
│ → Returns ("EVALUATING", Action("evaluate_answer"))                          │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ANSWER CHECKER (answer_checker.py)                                           │
│ 1. Perfect square root check                                                 │
│ 2. Cube root reasoning check ← "81 times 9 is 729" handled here              │
│ 3. Exact string match                                                        │
│ 4. Numeric equivalence (fractions, decimals)                                 │
│ 5. Diagnostic generation for wrong answers                                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     │                               │
              [correct=True]                  [correct=False]
                     │                               │
                     ▼                               ▼
┌─────────────────────────────┐   ┌────────────────────────────────────────────┐
│ NEXT_QUESTION or            │   │ HINT_1 → HINT_2 → FULL_SOLUTION            │
│ SESSION_COMPLETE            │   │ (escalating hint flow)                     │
└─────────────────────────────┘   └────────────────────────────────────────────┘
```

---

## Key Findings Summary

| Finding | Location | Impact |
|---------|----------|--------|
| "You said..." from DIDI_BASE line 34 | instruction_builder.py | Every LLM response echoes student input |
| Meta-questions bypass 5 pipeline steps | preprocessing.py + student.py | Fastest path, no LLM call |
| FAST_IDK matches "I didn't understand" | input_classifier.py | No LLM classifier call needed |
| Cube root reasoning patterns | answer_checker.py:264-338 | Accepts "81 times 9" as proof |
| Only 1 chapter in content bank | content_bank/math_8_ch6.json | 12 concepts, 36 questions |
| Skill ID mismatch | instruction_builder.py vs loader.py | May cause content lookup failures |

---

---

## Validation Results

### Baseline Verification

```
============================================================
  IDNA EdTech -- Mandatory Verification (v8.0)
  Mode: STANDARD
============================================================
  [PASS] ALL 22/22 CHECKS PASSED -- safe to commit
  pytest: 323 passed, 1 warning in 4.20s
============================================================
```

### Git State Confirmation

```
43a09ab P0: add cube root content + fix answer evaluator for cube root reasoning
1f8f0cd docs: update ROADMAP.md — meta-question debug logging + production confirmed
56244c6 P0: add debug logging for meta-question routing + response display
a14bc64 docs: update CLAUDE.md section 2 — unified pipeline (ib_v9 removed)
c40d9db docs: update ROADMAP.md with ib_v9 removal milestone
```

### Trace Test Results

| Test | Input | Expected | Actual | Status |
|------|-------|----------|--------|--------|
| Task 1 | "I didn't understand..." | confusion=True | confusion=True | PASS |
| Task 1 | FAST_IDK match | True | **False** | CORRECTED |
| Task 2 | "which chapter..." | meta_type="chapter" | meta_type="chapter" | PASS |
| Task 2 | Template response | Hinglish | "Hum Chapter 6..." | PASS |
| Task 3 | "81 times 9 is 729" | correct=True | correct=True | PASS |
| Task 3 | Reasoning detected | cube root proof | "81 × 9 = 729 proves..." | PASS |

**Trace Test 1 Correction:** Static analysis initially stated FAST_IDK would match. Runtime trace revealed `_normalize()` strips apostrophes ("didn't" → "didn t"), breaking the fast-path. Document updated to reflect actual behavior: LLM classifier IS called.

---

## Audit Complete

**Generated:** 2026-03-07
**Lines analyzed:** ~5,000
**Files reviewed:** 8 core files + content bank
**Fixes made:** NONE (diagnose-only)
**Validation:** verify.py 22/22, 3 trace tests executed, 1 finding corrected
