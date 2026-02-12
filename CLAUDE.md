# IDNA Tutor Architecture v4.11 — CLAUDE CODE RULES

## FILE STRUCTURE (6 files)

```
agentic_tutor.py      → Orchestrator. Session state + action executor.
answer_checker.py     → Deterministic answer check BEFORE LLM. NO LLM.
input_classifier.py   → Pure Python. Classifies student input. NO LLM.
tutor_states.py       → Pure Python. State machine transitions. NO LLM.
tutor_brain.py        → Pure Python. Student model + teaching plans. NO LLM.
didi_voice.py         → ALL LLM calls. Speech generation + hint selection.
```

## DATA FLOW

```
Student speaks
    ↓
input_classifier.classify() → category (ANSWER, IDK, ACK, TROLL, etc.)
    ↓
tutor_states.get_transition(state, category) → action + next_state
    ↓
[IF ANSWER] answer_checker.check_answer() → True/None/False
  - True  → CORRECT, bypass LLM, force praise_and_continue
  - None  → PARTIAL, bypass LLM, force guide_partial_answer
  - False → Check sub-question answer (v4.4)
    ↓
[IF WRONG] _check_sub_question_answer() → True/False  (v4.4)
  - True  → SUB-ANSWER CORRECT, acknowledge + guide to next step
  - False → WRONG, pass to LLM for hint selection
    ↓
tutor_brain enriches:
  - get_context_packet() → injected into every LLM call
  - get_pre_teach_instruction() → pre-teach before question if needed
  - get_enhanced_hint() → better hint based on student model
    ↓
didi_voice generates speech with brain's context
    ↓
tutor_brain.observe_interaction() → updates student model
    ↓
Response spoken to student
```

## ANSWER CHECKER (v4.1)

Deterministic check runs BEFORE LLM to fix unreliable gpt-4o-mini judging.

```python
check_answer(student_input, answer_key, accept_also) → True/None/False
```

Handles spoken math:
- "minus 1 by 7" → "-1/7"
- "minus one over seven" → "-1/7"
- "x = 5" → "5"
- Numeric equivalence: "0.5" matches "1/2"

## SUB-QUESTION DETECTION (v4.4)

Deterministic check for scaffolding sub-question answers. Prevents infinite loops.

```python
_check_sub_question_answer(didi_response, student_input) → True/False
```

Detects when student correctly answers a sub-question Didi asked:
- "minus 3 plus 2 kya hoga?" + "minus 1" → True (acknowledged, move to next step)
- "2 times minus 3 kya hoga?" + "minus six" → True
- "minus 3 aur 2 ka addition?" + "minus one" → True

Patterns recognized:
- Addition: "X plus Y", "X aur Y ka addition"
- Multiplication: "X times Y", "X multiplied by Y"
- Hindi question markers: "kya hoga", "kya hota hai", "batao"

## BRAIN INTEGRATION POINTS

1. `start_session`: Brain plans for Q1. Pre-teaches if needed.
2. `process_input` step 5: Brain enriches action with context packet
3. `process_input` step 6: Brain observes what happened
4. `_execute_action`: Context packet injected into all LLM calls
5. `_advance_question`: Brain plans for next question
6. `_end_speech`: Brain generates session summary

## KEY BEHAVIORS

### ask_what_they_did Limit
- First wrong answer: asks "Tell me, what did you do?"
- Second wrong answer: gives hint (does NOT ask again)
- Implementation: `_count_action_in_history("ask_what_they_did") >= 1` triggers override
- History stores actual LLM tool via `session["last_tool"]`, not state machine action

### IDK Detection
Triggers IDK category:
- "I don't know", "help me", "explain"
- "how can I use", "daily life", "real life example", "where do we use this"

### Brain Overrides
Brain can override ask_what_they_did when:
1. `needs_concept_teaching` is True → teach concept instead
2. Already asked once → give hint instead
3. `frustration_signals >= 2` → just help, don't question

### Noise Filter (v4.11)
- Detects ambient noise/TV audio via `is_nonsensical()` in classifier
- Re-asks CURRENT question via `_current_question_text()`, not from history
- Does NOT penalize student for background noise

### Never Paraphrase (v4.11)
- Didi must use student's EXACT words when quoting them
- WRONG: "Aapne kaha 9 over 7" (student said "9 by 7")
- RIGHT: "Aapne kaha 9 by 7" (exact quote)

## CRITICAL RULES

### Never modify these public interfaces:
- `AgenticTutor.__init__(student_name, chapter)`
- `AgenticTutor.start_session() → str`
- `AgenticTutor.process_input(text) → str`
- `AgenticTutor.get_session_state() → dict`
- `server.py` imports AgenticTutor — do NOT change server.py

### Architecture rules:
- `answer_checker.py` — ZERO imports except `re`. No LLM. Deterministic.
- `input_classifier.py` — ZERO imports except `re`. No LLM.
- `tutor_states.py` — ZERO external imports. No LLM.
- `tutor_brain.py` — ZERO external imports. No LLM. Pure reasoning.
- `didi_voice.py` — ONLY file that imports `openai`.
- `agentic_tutor.py` — Orchestrates. checker → classifier → states → brain → voice.

### Models:
- `gpt-4o-mini` for hint selection (wrong answers only)
- `gpt-4o` for speech generation

### Voice Configuration (v4.8):
- **TTS**: Google Cloud `en-IN-Journey-F` (natural Indian English female)
  - Fallback: `en-IN-Journey-D`
  - DO NOT use hi-IN voices (robotic with English words)
- **STT**: Groq Whisper `whisper-large-v3-turbo` with AUTO-DETECT
  - NO language parameter (let Whisper detect Hindi/English/Hinglish)
  - DO NOT force language="hi" (causes codec errors and misrecognition)

### Dead code (do NOT import):
web_server.py, tutor_intent.py, evaluator.py, context_builder.py, tutor_prompts.py, guardrails.py

## VERIFIED TEST FLOWS (February 12, 2026)

| Input | Expected Response |
|-------|-------------------|
| Correct: "minus 1 by 7" | "Bilkul sahi!" + next question (deterministic) |
| Correct: "-1/7" | Same as above |
| Partial: "-1" (for -1/7) | "Numerator correct, add denominator" |
| Wrong: "5" | LLM selects hint level |
| Sub-answer: "minus 1" after "minus 3 plus 2?" | "Haan sahi!" + guide to next step (v4.4) |
| Sub-answer: "minus six" after "2 times minus 3?" | "Haan sahi!" + guide forward (v4.4) |
| "how can I use in daily life" | Classified as IDK, encouragement |
| "nahi aata" (Hindi IDK) | Classified as IDK, encouragement (v4.3) |
| Noise: "me", "x", "rueldo" | Re-ask CURRENT question (v4.11) |
| "stop" | Session ends gracefully |

## HISTORY TRACKING

History entries store:
```python
{
    "student": str,      # student input
    "teacher": str,      # tutor response
    "action": str,       # actual LLM tool used (e.g., "ask_what_they_did")
    "category": str      # input category (e.g., "ANSWER")
}
```

Important: `action` is the LLM tool (from `session["last_tool"]`), NOT the state machine action.
