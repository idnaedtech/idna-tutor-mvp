# IDNA EdTech — Project CLAUDE.md

## Project Overview

Voice-based AI tutor "Didi" for NCERT Class 8 Math, targeting Tier 2/3 Indian students.
Stack: FastAPI + GPT-5-mini (Didi) + GPT-4o-mini (classifier) + Sarvam Saarika STT + Sarvam Bulbul TTS + Railway.
Repo: github.com/idnaedtech/idna-tutor-mvp
Current version: v7.3.28-fix2  

## Architecture

```
app/
├── routers/student.py      # FastAPI endpoints (async, uses classify())
├── tutor/
│   ├── input_classifier.py # LLM classifier (GPT-4o-mini): ACK/IDK/ANSWER/CONCEPT_REQUEST/LANGUAGE_SWITCH
│   ├── state_machine.py    # FSM: GREETING → TEACHING → WAITING_ANSWER → EVALUATING → NEXT_QUESTION
│   ├── instruction_builder.py # Builds LLM prompts with conversation history
│   ├── llm.py              # GPT-5-mini calls for Didi responses
│   └── enforcer.py         # Response quality enforcement
├── voice/
│   ├── stt.py              # Sarvam Saarika v2.5 STT (uses STT_DEFAULT_LANGUAGE from config)
│   └── tts.py              # Sarvam Bulbul v3 TTS (simran, hi-IN)
├── content/
│   └── ch1_square_and_cube.py  # Chapter 1: 50 questions, 20 skills
web/
├── student.html             # Student-facing web UI
tests/
├── test_*.py                # Test suite (97 tests)
verify.py                    # MANDATORY verification script (14 checks)
```

## Hard Rules — Violations Are Blocked by Hooks

### Never modify without running verify.py
```bash
python verify.py        # Full check — MUST pass before commit/push
python verify.py --quick # Quick check — run after every file edit
```

### Never change these without CEO approval
- **TTS voice**: Sarvam Bulbul v3, speaker `simran`, language `hi-IN`, pace `0.90`
- **STT config**: Sarvam Saarika v2.5, default language from `STT_DEFAULT_LANGUAGE`
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
| `app/content/ch1_square_and_cube.py` | Questions, hints, teaching content |
| `app/tutor/state_machine.py` | Any flow or state changes |
| `app/tutor/input_classifier.py` | How student input is categorized (async classify()) |
| `app/tutor/llm.py` | Didi LLM calls (GPT-5-mini) |
| `app/voice/tts.py` | TTS, clean_for_tts() |
| `app/voice/stt.py` | STT, STT_DEFAULT_LANGUAGE |
| `app/config.py` | LLM_MODEL, STT_DEFAULT_LANGUAGE, all settings |
| `verify.py` | Understanding what's checked (read-only) |

## Common Mistakes to Avoid

1. **Saying "fixed" without proof.** The Stop hook will reject you. Show verify.py output.
2. **Editing the wrong file.** Check the architecture diagram above.
3. **Breaking existing functionality.** Run verify.py --quick after EVERY edit.
4. **Forgetting Hindi input.** Students speak Hinglish. classifier must handle Devanagari.
5. **TTS silence bug.** If TTS stops returning audio after first call, it's a connection reuse issue. Test with TWO consecutive TTS calls.
6. **Hardcoding fallback responses.** Every state × input_category combination needs a specific handler. No catch-all "Sochiye" responses.

## SUB-AGENT ENFORCEMENT SYSTEM (MANDATORY)

### Available Sub-Agents

1. **verifier** — Runs automatically on Stop. Checks verify.py + cross-file wiring. If VERIFICATION FAILED → you MUST fix before proceeding.
2. **wiring-checker** — Call BEFORE claiming architectural changes done. Usage: `Use the wiring-checker subagent to trace the request flow`
3. **pre-commit-checker** — Call before every git commit. Usage: `Use the pre-commit-checker subagent`

### Mandatory Workflow for ANY Code Change

```
1. Make the code change
2. Use the wiring-checker subagent (for multi-file changes)
3. If breaks found → FIX THEM
4. Use the pre-commit-checker subagent
5. If blocked → FIX IT
6. git add && git commit
7. If verifier FAILED → FIX IT
8. git push
```

### BANNED Actions
- NEVER say "done" without verifier/wiring-checker confirmation
- NEVER skip verification flags on any git command
- NEVER modify verify.py to make checks pass
- NEVER modify sub-agent files in .claude/agents/
- NEVER claim "wired" without showing the call site (file:line)
- NEVER skip wiring-checker for multi-file changes

### Definition of "Wired"
A component is NOT wired if it exists in a file but no other file calls it.
A component IS wired when wiring-checker shows ✅ for its step.
