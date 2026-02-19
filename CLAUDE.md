# IDNA EdTech — Project CLAUDE.md

## Project Overview

Voice-based AI tutor "Didi" for NCERT Class 8 Math, targeting Tier 2/3 Indian students.
Stack: FastAPI + GPT-4o + Sarvam Saarika STT + Sarvam Bulbul TTS + Railway.
Repo: github.com/idnaedtech/idna-tutor-mvp

## Architecture

```
app/
├── routers/student.py      # FastAPI endpoints
├── tutor/
│   ├── agentic_tutor.py    # Session state machine, teaching flow
│   ├── didi_voice.py       # DIDI_PROMPT, instruction builders
│   ├── input_classifier.py # Classifies student input (ACK/IDK/ANSWER/COMFORT/CONCEPT_REQUEST)
│   ├── state_machine.py    # State definitions: GREETING → TEACHING → WAITING_ANSWER → EVALUATING → NEXT_QUESTION
│   ├── voice_input.py      # Sarvam Saarika v2.5 STT
│   ├── voice_output.py     # Sarvam Bulbul v3 TTS (simran, hi-IN)
│   └── enforcer.py         # Response quality enforcement
├── questions.py             # Question bank + SKILL_LESSONS
├── ch1_square_and_cube.py   # Chapter 1: 50 questions, 20 skills
web/
├── index.html               # Student-facing web UI
tests/
├── test_*.py                # Test suite
verify.py                    # MANDATORY verification script
```

## Hard Rules — Violations Are Blocked by Hooks

### Never modify without running verify.py
```bash
python verify.py        # Full check — MUST pass before commit/push
python verify.py --quick # Quick check — run after every file edit
```

### Never change these without CEO approval
- **TTS voice**: Sarvam Bulbul v3, speaker `simran`, language `hi-IN`, pace `0.90`
- **STT config**: Sarvam Saarika v2.5
- **DIDI_PROMPT**: Append rules only. Never rewrite.
- **FSM states**: GREETING → TEACHING → WAITING_ANSWER → EVALUATING → NEXT_QUESTION. No new states.
- **Questions**: Add only. Never delete existing questions.
- **verify.py**: Can be modified ONLY to align checks with current architecture (e.g., v7.3.0 LLM classifier). Do not remove or reduce checks — change what is tested, not whether it's tested.
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
python verify.py          # Full run
git add -A
git commit -m "v7.X.Y: description"
git push origin main
```

### When you think you're done
You are NOT done until:
1. `python verify.py` shows ALL ✅
2. You paste the COMPLETE verify.py output
3. For server changes: you show actual endpoint responses (curl output, not just grep)
4. For TTS changes: you show audio bytes returned (not just "should work")
5. For frontend changes: you describe what the user sees

## Testing

```bash
python -m pytest tests/ -v          # Unit tests
python verify.py                     # Integration verification
```

## Key Files to Understand Before Editing

| File | Read first if you're editing... |
|------|-------------------------------|
| `ch1_square_and_cube.py` | Questions, hints, teaching content |
| `app/tutor/state_machine.py` | Any flow or state changes |
| `app/tutor/input_classifier.py` | How student input is categorized |
| `app/tutor/didi_voice.py` | Didi's personality or teaching tone |
| `app/tutor/voice_output.py` | TTS, clean_for_tts() |
| `verify.py` | Understanding what's checked (read-only) |

## Common Mistakes to Avoid

1. **Saying "fixed" without proof.** The Stop hook will reject you. Show verify.py output.
2. **Editing the wrong file.** Check the architecture diagram above.
3. **Breaking existing functionality.** Run verify.py --quick after EVERY edit.
4. **Forgetting Hindi input.** Students speak Hinglish. classifier must handle Devanagari.
5. **TTS silence bug.** If TTS stops returning audio after first call, it's a connection reuse issue. Test with TWO consecutive TTS calls.
6. **Hardcoding fallback responses.** Every state × input_category combination needs a specific handler. No catch-all "Sochiye" responses.
