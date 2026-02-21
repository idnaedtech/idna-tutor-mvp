# IDNA EdTech — Project CLAUDE.md

## Project Overview

Voice-based AI tutor "Didi" for NCERT Class 8 Math, targeting Tier 2/3 Indian students.
Stack: FastAPI + GPT-5-mini (Didi) + GPT-4o-mini (classifier) + Sarvam Saarika STT + Sarvam Bulbul TTS + Railway.
Repo: github.com/idnaedtech/idna-tutor-mvp
Current version: v8.0.1

## Architecture

```
app/
├── routers/student.py      # FastAPI endpoints (async, uses v8.0 FSM)
├── state/                  # v8.0: Session state schema
│   ├── session.py          # SessionState dataclass, TutorState enum
│   └── __init__.py
├── fsm/                    # v8.0: Complete FSM (60 state × input combinations)
│   ├── transitions.py      # Transition matrix, get_transition()
│   ├── handlers.py         # Per-state handlers, handle_state()
│   └── __init__.py
├── tutor/
│   ├── input_classifier.py # LLM classifier (GPT-4o-mini): 10 categories
│   ├── state_machine.py    # Legacy FSM (used with v8.0 for backward compat)
│   ├── instruction_builder.py # Builds LLM prompts
│   ├── instruction_builder_v8.py # v8.0: Language-aware prompts
│   ├── llm.py              # GPT-5-mini calls for Didi responses
│   └── enforcer.py         # Response quality enforcement
├── voice/
│   ├── stt.py              # Sarvam Saarika v2.5 STT
│   └── tts.py              # Sarvam Bulbul v3 TTS (simran, hi-IN)
├── content/
│   └── ch1_square_and_cube.py  # Chapter 1: 50 questions, 20 skills
├── models.py               # ORM models (Question, Student, Session, etc.)
web/
├── student.html            # Student-facing web UI
tests/
├── test_*.py               # Test suite (152 tests)
├── test_integration.py     # v8.0: 27 integration tests
verify.py                   # MANDATORY verification script (22 checks)
```

## v8.0 Architecture Changes

### New Modules
- **app/state/session.py**: SessionState dataclass with preferred_language, reteach_count, teach_material_index
- **app/fsm/transitions.py**: Complete 60 state × input transition matrix (6 states × 10 inputs)
- **app/fsm/handlers.py**: Per-state handlers with Content Bank material injection

### v8.0 Key Features
1. **Language persistence**: preferred_language set by LANGUAGE_SWITCH, never resets
2. **Reteach cap**: After 3 IDKs/REPEATs, forces transition to WAITING_ANSWER
3. **No KeyError**: All 60 combinations defined in transition matrix
4. **Content Bank injection**: teach_material_index maps to CB material (0=definition, 1=analogy, 2=vedic_trick)

### Input Categories (10 total)
ACK, IDK, REPEAT, ANSWER, LANGUAGE_SWITCH, CONCEPT_REQUEST, COMFORT, STOP, TROLL, GARBLED

### States (6 total)
GREETING, TEACHING, WAITING_ANSWER, HINT, NEXT_QUESTION, SESSION_END

## Hard Rules — Violations Are Blocked by Hooks

### Never modify without running verify.py
```bash
python verify.py        # Full check — MUST pass before commit/push (22 checks)
python verify.py --quick # Quick check — run after every file edit
```

### Never change these without CEO approval
- **TTS voice**: Sarvam Bulbul v3, speaker simran, language hi-IN, pace 0.90
- **STT config**: Sarvam Saarika v2.5, default language from STT_DEFAULT_LANGUAGE
- **DIDI_PROMPT**: Append rules only. Never rewrite.
- **FSM states**: 6 states only. No new states.
- **Questions**: Add only. Never delete existing questions.
- **verify.py**: Can be modified ONLY to align checks with current architecture.
- **CLAUDE.md**: Can be modified by CEO only.

### Commit format
```
v{major}.{minor}.{patch}: brief description
```

## Workflow

### Before starting any task
```bash
python verify.py --quick
```
If anything fails, fix it first. Do not proceed with new work on a broken base.

### After every file change
```bash
python verify.py --quick
```

### Before committing (hook enforces this automatically)
```bash
python verify.py          # Full run (22/22 checks must pass)
git add -A
git commit -m "v8.X.Y: description"
git push origin main
```

### When you think you're done
You are NOT done until:
1. python verify.py shows ALL 22/22 PASSED
2. You paste the COMPLETE verify.py output
3. For server changes: you show actual endpoint responses (curl output)
4. For production changes: confirm with curl /health showing correct version
5. For v8.0 FSM changes: test reteach cap (3 IDKs -> WAITING_ANSWER)

## Testing

```bash
python -m pytest tests/ -v          # All 152 tests
python -m pytest tests/test_integration.py -v  # v8.0 integration tests (27)
python verify.py                     # Integration verification (22 checks)
```

## Key Files to Understand Before Editing

| File | Read first if you're editing... |
|------|-------------------------------|
| app/state/session.py | SessionState, language persistence, reteach cap |
| app/fsm/transitions.py | State × input combinations, get_transition() |
| app/fsm/handlers.py | Per-state behavior, handle_state() |
| app/routers/student.py | Request pipeline, v8.0 FSM integration |
| app/tutor/state_machine.py | Legacy FSM (backward compat) |
| app/tutor/input_classifier.py | How student input is categorized |
| app/content/ch1_square_and_cube.py | Questions, hints, teaching content |
| verify.py | Understanding what's checked |

## Common Mistakes to Avoid

1. **Saying "fixed" without proof.** The Stop hook will reject you. Show verify.py output.
2. **Editing the wrong file.** Check the architecture diagram above.
3. **Breaking existing functionality.** Run verify.py --quick after EVERY edit.
4. **Forgetting Hindi input.** Students speak Hinglish. classifier must handle Devanagari.
5. **TTS silence bug.** If TTS stops returning audio after first call, connection reuse issue.
6. **Hardcoding fallback responses.** All 60 state × input combinations have defined behavior.
7. **Creating app/models/ directory.** This shadows app/models.py. Use app/state/ for v8.0 modules.
8. **Not testing production.** After push, confirm version with curl /health.

## SUB-AGENT ENFORCEMENT SYSTEM (MANDATORY)

### Available Sub-Agents

1. **verifier** — Runs automatically on Stop. Checks verify.py + cross-file wiring.
2. **wiring-checker** — Call BEFORE claiming architectural changes done.
3. **pre-commit-checker** — Call before every git commit.

### Mandatory Workflow for ANY Code Change

```
1. Make the code change
2. Use the wiring-checker subagent (for multi-file changes)
3. If breaks found -> FIX THEM
4. Use the pre-commit-checker subagent
5. If blocked -> FIX IT
6. git add && git commit
7. If verifier FAILED -> FIX IT
8. git push
9. Confirm production with curl /health
```

### BANNED Actions
- NEVER say "done" without verifier/wiring-checker confirmation
- NEVER skip verification flags on any git command
- NEVER modify verify.py to make checks pass
- NEVER modify sub-agent files in .claude/agents/
- NEVER claim "wired" without showing the call site (file:line)
- NEVER skip wiring-checker for multi-file changes
- NEVER create app/models/ directory (shadows app/models.py)
- NEVER rationalize incomplete production deployment

### Definition of "Wired"
A component is NOT wired if it exists in a file but no other file calls it.
A component IS wired when wiring-checker shows checkmark for its step.

### Definition of "Done"
- Local: verify.py shows 22/22 PASSED
- Production: curl /health returns expected version
- v8.0 FSM: Reteach cap test passes (3 IDKs -> WAITING_ANSWER)
