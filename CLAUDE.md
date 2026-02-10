# IDNA Tutor Architecture v3.0 — CLAUDE CODE RULES

## FILE STRUCTURE (4 files replace 1)

```
agentic_tutor.py      → Orchestrator. Session state + action executor.
input_classifier.py   → Pure Python. Classifies student input. NO LLM.
tutor_states.py       → Pure Python. State machine transitions. NO LLM.
didi_voice.py         → ALL LLM calls. Speech generation + answer judging.
```

## CRITICAL RULES

### Never modify these interfaces:
- `AgenticTutor.__init__(student_name, chapter)`
- `AgenticTutor.start_session() → str`
- `AgenticTutor.process_input(text) → str`
- `AgenticTutor.get_session_state() → dict`
- `server.py` imports `AgenticTutor` from `agentic_tutor` — do NOT change this.

### Architecture rules:
- `input_classifier.py` has ZERO imports except `re`. No LLM. No OpenAI. No network.
- `tutor_states.py` has ZERO external imports. No LLM. Pure logic.
- `didi_voice.py` is the ONLY file that imports `openai`. ALL LLM calls go here.
- `agentic_tutor.py` orchestrates. It calls classifier → state machine → voice. Nothing else.

### Adding new behaviors:
1. New input type? → Add detector in `input_classifier.py`, add category to `classify()`
2. New state transition? → Add to `tutor_states.py` in the appropriate `_*_transition()` function
3. New speech pattern? → Add `build_*_instruction()` in `didi_voice.py`
4. New action? → Add to `Action` enum in `tutor_states.py`, handle in `_execute_action()` in `agentic_tutor.py`

### What NOT to do:
- Do NOT put if/elif chains in `process_input()`. Use the state machine.
- Do NOT call OpenAI from `agentic_tutor.py`. Use `didi_voice.py`.
- Do NOT classify input in `agentic_tutor.py`. Use `input_classifier.py`.
- Do NOT import from `web_server.py`, `tutor_intent.py`, `evaluator.py`, `context_builder.py`, `tutor_prompts.py` — these are DEAD CODE.

### Import chain:
```
server.py → agentic_tutor.py → input_classifier.py (pure Python)
                              → tutor_states.py (pure Python)
                              → didi_voice.py → openai, tutor_tools.py
                              → questions.py
```

### Models:
- `gpt-4o-mini` for tool calling (judging answers)
- `gpt-4o` for speech generation
- Do NOT downgrade speech to mini. Do NOT upgrade tool calling to 4o.
