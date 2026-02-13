# IDNA Tutor Architecture v6.0.4 — CLAUDE CODE RULES

## TTS ENGINE (v6.0.4)

- **Engine:** Sarvam Bulbul v3 (api.sarvam.ai)
- **Voice:** priya (warm Indian female — configurable via SARVAM_SPEAKER)
- **Pace:** 0.90 (natural teaching pace)
- **Language:** en-IN (reads numbers in English, handles Hindi words natively)
- **No preprocessing needed** — Sarvam handles code-mixed Hinglish natively
- **NO FALLBACK** — never switch voice mid-session; retry with shorter text instead
- **API:** POST https://api.sarvam.ai/text-to-speech
- **Auth:** api-subscription-key header
- **Response:** base64 MP3 in {"audios": ["..."]}
- **Char limit:** 2000 (truncate at sentence boundary to avoid hitting 2500 limit)

## FILE STRUCTURE (6 files)

```
agentic_tutor.py      → Orchestrator. Session state + action executor.
answer_checker.py     → Deterministic answer check BEFORE LLM. NO LLM.
input_classifier.py   → Pure Python. Classifies student input. NO LLM.
tutor_states.py       → Pure Python. State machine transitions. NO LLM.
tutor_brain.py        → Pure Python. Student model + teaching plans. NO LLM.
didi_voice.py         → ALL LLM calls. Speech generation + hint selection.
```

## DATA FLOW (v6.0.1)

```
SESSION START (v6.0.1 — two-turn flow)
    ↓
start_session() → Template-based greeting (NO LLM)
  - "Namaste {name}! Aaj hum {chapter} padhenge."
  - Teach concept with real-life example (from teaching_examples dict)
  - End with "Samajh aaya?"
  - Set needs_first_question = True
    ↓
Student responds to "Samajh aaya?"
    ↓
[IF ACK] → "Bahut accha! Ab ek question try karte hain: {question}"
[IF IDK] → Re-teach with different wording, keep needs_first_question = True
[IF STOP/TROLL] → Fall through to normal flow
    ↓
NORMAL QUESTION FLOW
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
didi_voice generates speech with brain's context + CONVERSATION HISTORY
    ↓
tutor_brain.observe_interaction() → updates student model
    ↓
[TTS PREPROCESSING] preprocess_for_tts() → transliterate English terms to Hindi
    ↓
[TTS LENGTH LIMIT] Truncate at 1500 chars (sentence boundary) for Google TTS
    ↓
Response spoken to student
```

## NEW IN v6.0.1

### Teach-First Flow (v6.0)
- Didi ALWAYS teaches the concept BEFORE asking the first question
- Uses template-based greeting (no LLM) to ensure predictable output
- Teaching examples stored in `teaching_examples` dict by skill
- DIDI_PROMPT updated with "TEACHER, not quiz machine" philosophy

### Two-Turn Session Start (v6.0.1)
- **Turn 1**: Greeting + teach concept + "Samajh aaya?"
- **Turn 2**: If ACK → read question. If IDK → re-teach.
- `needs_first_question` flag tracks state between turns
- Direct returns (no LLM) for ACK/IDK to prevent LLM modification

### TTS Length Limit (v6.0.1)
- Google TTS has 5000 byte limit
- Text truncated at 1500 chars (sentence boundary) before TTS call
- Prevents TTS failures on long v6.0 greetings

### Warm Chapter Intros (v6.0)
- CHAPTER_INTROS replaced with warm Hindi teaching intros
- Example: "Aaj hum rational numbers padhenge. Ye wo numbers hain jo aap p over q mein likh sakte hain..."

### Updated DIDI_PROMPT (v6.0)
- Emphasizes teaching philosophy: "TEACHER, not quiz machine"
- Real-life Indian examples: pocket money, roti, cricket, auto-rickshaw
- Warm corrections: "Hmm, yahan thoda dhyan dein" (never "Wrong")
- Max 5 sentences per turn

## ANSWER CHECKER (v4.1 — unchanged)

Deterministic check runs BEFORE LLM to fix unreliable gpt-4o-mini judging.

```python
check_answer(student_input, answer_key, accept_also) → True/None/False
```

## KEY BEHAVIORS

### Session Start (v6.0.1)
1. `start_session()` returns template-based greeting + teaching
2. First `process_input()` checks `needs_first_question` flag
3. ACK → read question, IDK → re-teach, STOP → end session

### teach_concept (v5.0)
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

### Voice Configuration:
- **TTS**: Sarvam Bulbul v3 `priya` voice (2400 char limit, sentence truncation)
- **STT**: Groq Whisper `whisper-large-v3-turbo` with AUTO-DETECT

### Test Suite (246 tests)
- `test_answer_checker.py` — spoken math normalization, correct/partial/wrong detection
- `test_input_classifier.py` — all input categories including CONCEPT_REQUEST
- `test_tutor_states.py` — state machine transitions, circuit breakers
- `test_regression_live.py` — real session scenarios, full chain tests
- `test_api.py` — API endpoint tests (health, chapters, session, TTS)
- Run: `python -m pytest test_*.py -v`

### Dead code (do NOT import):
web_server.py, tutor_intent.py, evaluator.py, context_builder.py, tutor_prompts.py, guardrails.py

## VERIFIED TEST FLOWS (v6.0.1)

| Turn | Input | Expected Response |
|------|-------|-------------------|
| Start | — | "Namaste {name}! Aaj hum {chapter}... {teaching}... Samajh aaya?" |
| 2 | "haan" / ACK | "Bahut accha! Ab ek question try karte hain: {question}" |
| 2 | "nahi samjha" / IDK | "Koi baat nahi, let me explain again... Ab samjhe?" |
| 3+ | Correct: "minus 1 by 7" | "Bilkul sahi!" + next question (deterministic) |
| 3+ | Partial: "-1" (for -1/7) | "Numerator correct, add denominator" |
| 3+ | Wrong: "5" | LLM selects hint level |
| 3+ | Sub-answer: "minus 1" after "minus 3 plus 2?" | "Haan sahi!" + guide forward |
| Any | "what are rational numbers?" | TEACH the concept + bridge to question |
| Any | Noise: "me", "x", "." | Re-ask current question |
| Any | 3x consecutive noise | Force explain + advance |
| Any | "stop" | Session ends gracefully |
