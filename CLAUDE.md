# IDNA Tutor Architecture v5.0 — CLAUDE CODE RULES

## FILE STRUCTURE (6 files)

```
agentic_tutor.py      → Orchestrator. Session state + action executor.
answer_checker.py     → Deterministic answer check BEFORE LLM. NO LLM.
input_classifier.py   → Pure Python. Classifies student input. NO LLM.
tutor_states.py       → Pure Python. State machine transitions. NO LLM.
tutor_brain.py        → Pure Python. Student model + teaching plans. NO LLM.
didi_voice.py         → ALL LLM calls. Speech generation + hint selection.
```

## DATA FLOW (v5.0)

```
Student speaks
    ↓
input_classifier.classify() → category (ANSWER, IDK, ACK, TROLL, CONCEPT_REQUEST, etc.)
    ↓
tutor_states.get_transition(state, category) → action + next_state
    ↓
[IF ANSWER] answer_checker.check_answer() → True/None/False
  - True  → CORRECT, bypass LLM, force praise_and_continue
  - None  → PARTIAL, bypass LLM, force guide_partial_answer
  - False → Check sub-question answer (v4.4)
    ↓
[IF WRONG] _check_sub_question_answer() → True/False
  - True  → SUB-ANSWER CORRECT, acknowledge + guide to next step
  - False → WRONG, pass to LLM for hint selection
    ↓
[IF CONCEPT_REQUEST] → teach_concept tool (v5.0)
  - Pause current question
  - Teach prerequisite concept with real-life example
  - Bridge back to current question
  - Return to WAITING_ANSWER state
    ↓
tutor_brain enriches:
  - get_context_packet() → injected into every LLM call
  - get_pre_teach_instruction() → pre-teach before question if needed
  - get_enhanced_hint() → better hint based on student model
    ↓
didi_voice generates speech with brain's context + CONVERSATION HISTORY (v5.0)
    ↓
tutor_brain.observe_interaction() → updates student model
    ↓
[TTS PREPROCESSING] preprocess_for_tts() → transliterate English terms to Hindi (v5.0)
    ↓
Response spoken to student
```

## NEW IN v5.0

### teach_concept tool
- Triggered by CONCEPT_REQUEST classification
- Student asks "what are rational numbers?", "samjhao kya hota hai"
- Pauses current question, teaches the concept, bridges back
- NEVER ignore a student asking about a concept. ALWAYS teach it.

### Conversation history in all LLM calls
- EVERY call to didi_voice includes last 4 turns of conversation history
- This ensures Didi connects to what the student has been saying
- If student asked something twice, Didi should notice and address it

### TTS preprocessing
- preprocess_for_tts() transliterates English math terms to Hindi Devanagari
- Runs BEFORE Google TTS call
- Fixes "t" and "g" English phonetic pronunciation

### Student name fix
- NEVER default to "Student"
- Empty name → omit name entirely
- Real name → use 2-3 times per session

## ANSWER CHECKER (v4.1 — unchanged)

Deterministic check runs BEFORE LLM to fix unreliable gpt-4o-mini judging.

```python
check_answer(student_input, answer_key, accept_also) → True/None/False
```

## KEY BEHAVIORS

### teach_concept (v5.0 — NEW)
- Triggered when student asks about a concept (CONCEPT_REQUEST category)
- Uses teach_concept tool in LLM
- Teaches with real-life example, not just definition
- Bridges back to current question
- Resets attempt count by 1 (teaching is not a failed attempt)

### ask_what_they_did Limit
- First wrong answer: asks "Tell me, what did you do?"
- Second wrong answer: gives hint (does NOT ask again)

### Noise Filter (v4.12)
- After 3+ consecutive unclear inputs, forces explain and advances question

### Never Paraphrase (v4.11)
- Use student's EXACT words when quoting them

## CRITICAL RULES

### Never modify these public interfaces:
- `AgenticTutor.__init__(student_name, chapter)`
- `AgenticTutor.start_session() → str`
- `AgenticTutor.process_input(text) → str`
- `AgenticTutor.get_session_state() → dict`
- server.py import of AgenticTutor — do NOT break this

### Architecture rules:
- `answer_checker.py` — ZERO imports except `re`. No LLM.
- `input_classifier.py` — ZERO imports except `re`. No LLM.
- `tutor_states.py` — ZERO external imports. No LLM.
- `tutor_brain.py` — ZERO external imports. No LLM.
- `didi_voice.py` — ONLY file that imports `openai`.
- `agentic_tutor.py` — Orchestrates. checker → classifier → states → brain → voice.

### Models:
- `gpt-4o` for BOTH tool calling AND speech generation

### Voice Configuration (v5.0):
- **TTS**: Google Cloud `en-IN-Journey-F` with preprocess_for_tts() Hindi transliteration
- **STT**: Groq Whisper `whisper-large-v3-turbo` with AUTO-DETECT

### Dead code (do NOT import):
web_server.py, tutor_intent.py, evaluator.py, context_builder.py, tutor_prompts.py, guardrails.py

## VERIFIED TEST FLOWS (v5.0)

| Input | Expected Response |
|-------|-------------------|
| Correct: "minus 1 by 7" | "Bilkul sahi!" + next question (deterministic) |
| Partial: "-1" (for -1/7) | "Numerator correct, add denominator" |
| Wrong: "5" | LLM selects hint level |
| Sub-answer: "minus 1" after "minus 3 plus 2?" | "Haan sahi!" + guide forward |
| "what are rational numbers?" | TEACH the concept + bridge to question (v5.0) |
| "samjhao kya hota hai" | TEACH the concept (v5.0) |
| "you should explain to me" | TEACH the concept (v5.0) |
| Noise: "me", "x", "." | Re-ask current question |
| 3x consecutive noise | Force explain + advance |
| "stop" | Session ends gracefully |
| Empty name / "Student" | Omit name, don't say "Student" |
