# IDNA Tutor Architecture v3.1 — CLAUDE CODE RULES

## FILE STRUCTURE (5 files)

```
agentic_tutor.py      → Orchestrator. Session state + action executor.
input_classifier.py   → Pure Python. Classifies student input. NO LLM.
tutor_states.py       → Pure Python. State machine transitions. NO LLM.
tutor_brain.py        → Pure Python. Student model + teaching plans. NO LLM.
didi_voice.py         → ALL LLM calls. Speech generation + answer judging.
```

## DATA FLOW

```
Student speaks
    ↓
input_classifier.classify() → category (ANSWER, IDK, ACK, TROLL, etc.)
    ↓
tutor_states.get_transition(state, category) → action + next_state
    ↓
tutor_brain enriches:
  - get_context_packet() → injected into every LLM call
  - get_pre_teach_instruction() → pre-teach before question if needed
  - get_enhanced_hint() → better hint based on student model
  - override ask_what_they_did → teach concept if student needs it
    ↓
didi_voice generates speech with brain's context
    ↓
tutor_brain.observe_interaction() → updates student model
    ↓
Response spoken to student
```

## BRAIN INTEGRATION POINTS

1. `start_session`: Brain plans for Q1. Pre-teaches if needed.
2. `process_input` step 5: Brain enriches action with context packet
3. `process_input` step 6: Brain observes what happened
4. `_execute_action`: Context packet injected into all LLM calls
5. `_advance_question`: Brain plans for next question
6. `_end_speech`: Brain generates session summary

## CRITICAL RULES

### Never modify these public interfaces:
- `AgenticTutor.__init__(student_name, chapter)`
- `AgenticTutor.start_session() → str`
- `AgenticTutor.process_input(text) → str`
- `AgenticTutor.get_session_state() → dict`
- `server.py` imports AgenticTutor — do NOT change server.py

### Architecture rules:
- `input_classifier.py` — ZERO imports except `re`. No LLM.
- `tutor_states.py` — ZERO external imports. No LLM.
- `tutor_brain.py` — ZERO external imports. No LLM. Pure reasoning.
- `didi_voice.py` — ONLY file that imports `openai`.
- `agentic_tutor.py` — Orchestrates. classifier → states → brain → voice.

### Models:
- `gpt-4o-mini` for tool calling (judging answers)
- `gpt-4o` for speech generation

### Dead code (do NOT import):
web_server.py, tutor_intent.py, evaluator.py, context_builder.py, tutor_prompts.py
