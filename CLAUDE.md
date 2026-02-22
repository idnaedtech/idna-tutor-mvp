# IDNA EdTech — Project CLAUDE.md

> **This file is read by Claude Code on every session start.**
> **Last updated:** 2026-02-23
> **Repo:** github.com/idnaedtech/idna-tutor-mvp
> **Live:** https://idna-tutor-mvp-production.up.railway.app
> **Current version:** v8.1.0
> **Can be modified by CEO only.**

---

## 0. PRIME DIRECTIVE

You are working on a production voice tutoring platform used by real students.
**Every broken deploy = a student who can't learn.**
Read before editing. Prove before claiming done. Ask before touching files outside your scope.

---

## 1. PROJECT OVERVIEW

Voice-based AI tutor "Didi" for NCERT Class 8 Math, targeting Tier 2/3 Indian students.

| Layer | Technology | Notes |
|-------|-----------|-------|
| Didi LLM | GPT-5-mini | Teaching responses. Do not switch. |
| Classifier LLM | GPT-4o-mini | Input classification. Do not switch. |
| STT | Sarvam Saarika v2.5 | Default language from STT_DEFAULT_LANGUAGE |
| TTS | Sarvam Bulbul v3 | speaker=simran, language=hi-IN, pace=0.90 |
| Backend | FastAPI (Python 3.11) | Async endpoints |
| Database | PostgreSQL (Railway managed) | Not SQLite |
| Hosting | Railway | Auto-deploy from main |

**Do not add new dependencies without explicit permission.**
**Do not upgrade existing dependencies unless explicitly tasked.**

---

## 2. ARCHITECTURE — NON-NEGOTIABLE RULES

These rules are absolute. Violating any of them is a blocking error.

1. **FSM is frozen.** The 60-combination state machine (6 states × 10 input categories) does not change. No new states. No new input categories. No catch-all fallbacks. No "temporary" transitions.
2. **New board = data insert, zero code change.** If you are modifying FSM logic to support a new board, **STOP and ask**.
3. **bench_score gates everything.** No content serves students without a score above threshold (85 for boards, 98% for math truth, 75 for languages). Enforced at DB level.
4. **One Didi voice.** Sarvam Bulbul v3, speaker=simran, hi-IN, pace=0.90. No TTS fallback. No voice switching. Do not touch voice config.
5. **Never rewrite DIDI_PROMPT.** Append rules only. Never replace the existing prompt.
6. **Language persistence is sacred.** `preferred_language` is set by LANGUAGE_SWITCH, injected in EVERY LLM prompt. It must NEVER reset on state transitions.
7. **Phase gates are strict.** P0 → P1 → P2 → P3 → P4. No features from a later phase unless all prior phase gates have passed.
8. **Alembic for all schema changes.** No raw SQL DDL against production. Every migration must have a rollback.
9. **Don't edit MEMORY.md mid-session.**
10. **Never create `app/models/` directory.** This shadows `app/models.py`. Use `app/state/` for v8.0 modules.

---

## 3. CODEBASE STRUCTURE

```
app/
├── routers/student.py          # FastAPI endpoints (async, uses v8.0 FSM)
├── state/                      # v8.0: Session state schema
│   ├── session.py              # SessionState dataclass, TutorState enum
│   └── __init__.py
├── fsm/                        # v8.0: Complete FSM (60 state × input combos)
│   ├── transitions.py          # Transition matrix, get_transition()  [FROZEN]
│   ├── handlers.py             # Per-state handlers, handle_state()   [FROZEN]
│   └── __init__.py
├── tutor/
│   ├── input_classifier.py     # LLM classifier (GPT-4o-mini): 10 categories
│   ├── state_machine.py        # Legacy FSM (backward compat)
│   ├── instruction_builder.py  # Builds LLM prompts
│   ├── instruction_builder_v8.py # v8.0: Language-aware prompts
│   ├── llm.py                  # GPT-5-mini calls for Didi responses
│   └── enforcer.py             # Response quality enforcement
├── voice/
│   ├── stt.py                  # Sarvam Saarika v2.5 STT             [PROTECTED]
│   └── tts.py                  # Sarvam Bulbul v3 TTS (simran, hi-IN) [PROTECTED]
├── content/
│   └── ch1_square_and_cube.py  # Chapter 1: 50 questions, 20 skills
├── models.py                   # ORM models (Question, Student, Session, etc.)
web/
├── student.html                # Student-facing web UI
tests/
├── test_*.py                   # Test suite (152 tests)
├── test_integration.py         # v8.0: 27 integration tests
verify.py                       # MANDATORY verification script (22 checks)
CLAUDE.md                       # THIS FILE                           [CEO-ONLY]
IDNA_v8_ARCHITECTURE.md         # THE spec                            [READ-ONLY]
alembic/                        # Database migrations
```

---

## 4. ALLOWED FILES — SCOPE CONSTRAINTS

Before every task, Claude Code must declare which files it will touch.

### Module Ownership Map

| Module | Files | Protection | Touch Without Permission? |
|--------|-------|------------|--------------------------|
| FSM Transitions | `app/fsm/transitions.py` | **FROZEN** | **NO** — ask first |
| FSM Handlers | `app/fsm/handlers.py` | **FROZEN** | **NO** — ask first |
| Session State | `app/state/session.py` | Protected | Only for documented schema extensions |
| Voice STT | `app/voice/stt.py` | Protected | Only for bugs, never config |
| Voice TTS | `app/voice/tts.py` | Protected | Only for bugs, never config |
| DIDI_PROMPT | `app/tutor/instruction_builder*.py` | Protected | **Append only, never replace** |
| API Endpoints | `app/routers/student.py` | Open | Yes, with test coverage |
| Input Classifier | `app/tutor/input_classifier.py` | Open | Yes, with test coverage |
| LLM Calls | `app/tutor/llm.py` | Open | Yes |
| Enforcer | `app/tutor/enforcer.py` | Open | Yes |
| Legacy FSM | `app/tutor/state_machine.py` | Deprecated | Only if backward compat breaks |
| Questions/Content | `app/content/` | Open | Add only, never delete questions |
| ORM Models | `app/models.py` | Open | Yes, via Alembic only |
| Tests | `tests/` | Open | Always add, **never delete** |
| Frontend | `web/student.html` | Open | Yes |
| Verify Script | `verify.py` | Protected | Only to align checks with current architecture |
| Architecture Spec | `IDNA_v8_ARCHITECTURE.md` | **READ-ONLY** | **NO** |
| This File | `CLAUDE.md` | **CEO-ONLY** | **NO** |
| Sub-agent Files | `.claude/agents/` | **READ-ONLY** | **NO** |
| Alembic Migrations | `alembic/` | Open | Yes, with rollback |

### Hard Bans

- **Never** rename files or directories
- **Never** reformat code you didn't write (no style-only diffs)
- **Never** upgrade dependencies unless explicitly tasked
- **Never** reorganize imports in files you didn't change
- **Never** move files between directories
- **Never** delete tests or questions
- **Never** run `rm -rf` on anything
- **Never** modify `.env` or environment variables without explicit permission
- **Never** create `app/models/` directory (shadows `app/models.py`)
- **Never** modify verify.py to make checks pass (only to align with architecture)
- **Never** modify sub-agent files in `.claude/agents/`
- If you believe a file outside your declared scope must change: **STOP and state why**

---

## 5. TASK PROTOCOL — HOW TO WORK

### Step 0: Pre-Flight

Before ANY edit:

```bash
python verify.py --quick
```

If anything fails, fix it first. Do not proceed with new work on a broken base.

Then you must:

1. **List the exact files** you will modify
2. **Quote the exact functions/lines** you will change
3. **State current behavior** (what happens now)
4. **State desired behavior** (what should happen after)
5. **Identify the call graph** (what calls this code, what does it call)

If you cannot do all 5, you do not understand the code well enough to edit it. Read more first.

### Step 1: Plan (No Edits Yet)

Write a step-by-step plan. Each step must specify:
- Which file
- Which function/line
- What changes
- Why

Wait for approval before proceeding.

### Step 2: Execute One Step at a Time

- Make the change for Step 1 only
- Show the diff
- Run `verify.py --quick`
- Only proceed to Step 2 after Step 1 passes

### Step 3: Prove It Works

No change is "done" without evidence. See Section 6.

---

## 6. DEFINITION OF DONE — VALIDATION REQUIREMENTS

### After Every File Change

```bash
python verify.py --quick
```

### Before Commit

```bash
# 1. All existing tests pass
python -m pytest tests/ -v

# 2. Full verify script passes (22 checks)
python verify.py

# 3. Import check — app loads without errors
python -c "from app.models import Question, Student; print('OK')"
```

### Evidence Required

You are NOT done until:

1. `verify.py` shows **ALL 22/22 PASSED** (paste complete output)
2. For server changes: actual endpoint responses (curl output)
3. For production changes: `curl /health` showing correct version
4. For v8.0 FSM-adjacent changes: reteach cap test passes (3 IDKs → WAITING_ANSWER)
5. If tests fail: debug until green. Do not claim partial success.

### Railway Deployment Awareness

Claude Code runs locally. The production environment is Railway.
- CORS, websocket, auth, and environment variable bugs may not reproduce locally
- If a fix is environment-dependent, state: "This fix is local-only. Verify on Railway with: `railway logs`"
- After push, always confirm production with `curl /health`
- Never claim a deployment bug is fixed without Railway log evidence

### Test Requirements for New Code

| Change Type | Test Requirement |
|-------------|-----------------|
| Bug fix | Regression test that fails before fix, passes after |
| New endpoint | Contract test (request → expected response) |
| Schema change | Migration test + rollback test |
| FSM change | **NOT ALLOWED** without explicit permission |
| Input classifier change | Classification test with edge cases (including Devanagari) |
| Content change | Add only. Content parity test if migrating |

### Definition of "Wired"

A component is **NOT** wired if it exists in a file but no other file calls it.
A component **IS** wired when wiring-checker shows checkmark for its step.
**Never claim "wired" without showing the call site (file:line).**

---

## 7. COMMIT DISCIPLINE

### Format

```
v{major}.{minor}.{patch}: brief description
```

### Rules

- **One bug or feature per commit.** Never bundle.
- **Max 1-3 files per commit** in early stages
- **Never commit failing tests.** Run full test suite before every commit.
- **Commit message describes exactly one thing.** If you need "and" in the message, split the commit.

### Full Commit Workflow

```bash
python verify.py --quick              # After every file edit
python -m pytest tests/ -v            # Before commit
python verify.py                      # Full run — 22/22 must pass
git add -A
git commit -m "v8.X.Y: description"
git push origin main
curl https://idna-tutor-mvp-production.up.railway.app/health  # Confirm deploy
```

---

## 8. SUB-AGENT ENFORCEMENT SYSTEM (MANDATORY)

### Available Sub-Agents

1. **verifier** — Runs automatically on Stop. Checks verify.py + cross-file wiring.
2. **wiring-checker** — Call BEFORE claiming architectural changes done.
3. **pre-commit-checker** — Call before every git commit.

### Mandatory Workflow for ANY Code Change

```
1. Run verify.py --quick (pre-flight)
2. Declare allowed files (Section 4)
3. Write plan (Section 5, Step 1)
4. Make the code change (one step at a time)
5. Run verify.py --quick (post-edit)
6. Use wiring-checker subagent (for multi-file changes)
7. If breaks found → FIX THEM
8. Use pre-commit-checker subagent
9. If blocked → FIX IT
10. git add && git commit
11. If verifier FAILED → FIX IT
12. git push
13. Confirm production with curl /health
```

### Sub-Agent Rules

- NEVER say "done" without verifier/wiring-checker confirmation
- NEVER skip verification flags on any git command
- NEVER modify sub-agent files in `.claude/agents/`
- NEVER rationalize incomplete production deployment

---

## 9. FSM REFERENCE (READ-ONLY)

### 6 States

`GREETING`, `TEACHING`, `WAITING_ANSWER`, `HINT`, `NEXT_QUESTION`, `SESSION_END`

### 10 Input Categories

`ACK`, `IDK`, `REPEAT`, `ANSWER`, `LANGUAGE_SWITCH`, `CONCEPT_REQUEST`, `COMFORT`, `STOP`, `TROLL`, `GARBLED`

### v8.0 Key Features

1. **Language persistence**: preferred_language set by LANGUAGE_SWITCH, never resets
2. **Reteach cap**: After 3 IDKs/REPEATs, forces transition to WAITING_ANSWER
3. **No KeyError**: All 60 combinations defined in transition matrix
4. **Content Bank injection**: teach_material_index maps to CB material (0=definition, 1=analogy, 2=vedic_trick)

### Key Transitions (Do Not Modify)

```
GREETING → TEACHING
TEACHING + ACK → WAITING_ANSWER (via NEXT_QUESTION)
TEACHING + IDK → TEACHING (reteach, cap at 3, then force WAITING_ANSWER)
TEACHING + REPEAT → TEACHING (reteach, same cap)
WAITING_ANSWER + ANSWER → evaluate → HINT or NEXT_QUESTION
WAITING_ANSWER + IDK → HINT (hint 1 → hint 2 → full solution)
NEXT_QUESTION → TEACHING (next topic) or SESSION_END
```

---

## 10. KEY FILES TO UNDERSTAND BEFORE EDITING

| File | Read first if you're editing... |
|------|-------------------------------|
| `app/state/session.py` | SessionState, language persistence, reteach cap |
| `app/fsm/transitions.py` | State × input combinations, get_transition() |
| `app/fsm/handlers.py` | Per-state behavior, handle_state() |
| `app/routers/student.py` | Request pipeline, v8.0 FSM integration |
| `app/tutor/state_machine.py` | Legacy FSM (backward compat) |
| `app/tutor/input_classifier.py` | How student input is categorized |
| `app/content/ch1_square_and_cube.py` | Questions, hints, teaching content |
| `verify.py` | Understanding what's checked |
| `IDNA_v8_ARCHITECTURE.md` | THE spec — read for any architectural question |

---

## 11. P1 BACKLOG — CURRENT BUGS

Fix in Phase 1, Week 4. Each must have a regression test.

| # | Bug | File(s) Likely Involved | Constraint |
|---|-----|------------------------|------------|
| 1 | Same-Q reload: page refresh re-serves same question | `app/routers/student.py`, `app/content/` | Don't touch FSM |
| 2 | HOMEWORK_HELP trap: classifier doesn't handle it | `app/tutor/input_classifier.py` | Add handling, don't modify existing 10 categories |
| 3 | Devanagari बटा parser: Hindi fraction input broken | `app/tutor/input_classifier.py` or answer parsing | Test with actual Hindi strings |
| 4 | Empty TTS sentence: blank calls waste API quota | `app/voice/tts.py` | Guard before API call |
| 5 | Parent split()[0] bug: breaks on single names | `app/routers/student.py` or parent report code | Edge case fix only |
| 6 | Weakest-skill dead end: adaptive flow stuck | `app/fsm/handlers.py` | Fallback only, don't restructure flow |

---

## 12. ANTI-PATTERNS — THINGS THAT BREAK THIS REPO

If you catch yourself doing any of these, stop immediately:

1. **"Improving" code style** in files you weren't asked to touch
2. **Adding try/except that swallows errors silently** — log or raise, never pass
3. **Changing FSM transitions** to "handle edge cases" — the 60-combo matrix is complete
4. **Resetting `preferred_language`** anywhere in any transition
5. **Adding a new TTS voice or fallback** — one Didi, always
6. **Writing SQL DDL directly** instead of using Alembic
7. **Claiming "done" without verify.py output** — show the logs
8. **Editing multiple unrelated things in one commit** — atomic only
9. **Creating `app/models/` directory** — shadows `app/models.py`, breaks imports
10. **Refactoring "while you're in there"** — never bundle cleanup with fixes
11. **Hardcoding fallback responses** — all 60 state × input combos have defined behavior
12. **Saying "fixed" without proof** — the Stop hook will reject you

---

## 13. VOICE PIPELINE — DO NOT BREAK

```
Student speaks
  → Sarvam Saarika v2.5 STT (~300ms)
  → Confidence check (threshold 0.4)
  → Input Classifier (GPT-4o-mini, 10 categories)
  → FSM (state + input → action via transitions.py)
  → Instruction Builder v8 (language-aware LLM prompt)
  → GPT-5-mini (~800-1200ms)
  → clean_for_tts()
  → Sarvam TTS (single call, max 2000 chars)
  → Audio plays in browser
```

**Latency budget:** STT(300ms) + Classifier + LLM(1200ms) + TTS(500ms) ≈ 2s target.
If your change adds latency, flag it.

**Known issue — TTS silence bug:** If TTS stops returning audio after first call → connection reuse issue. Do not ignore.

---

## 14. HOOKS CONFIGURATION

| Hook | Trigger | Action | Failure |
|------|---------|--------|---------|
| PreToolUse | `git commit` | `verify.py --quick` | exit 2 = BLOCK commit |
| PreToolUse | `git push` | `verify.py` (full) | exit 2 = BLOCK push |
| PreToolUse | `rm -rf` | HARD BLOCK | Always blocked |
| PostToolUse | Bash commands | Log to `.claude/bash-commands.log` | — |
| Stop | "done" claim | Verifier sub-agent reviews for proof | Rejects without evidence |

---

## 15. DEPLOYMENT NOTES

- Railway auto-deploys from `main` branch on GitHub
- Health check: `GET /health` → `{"status":"ok","version":"8.1.0"}`
- Environment variables are set in Railway dashboard — **never hardcode secrets**
- If deploy fails, check Railway build logs first
- TTS cache is in PostgreSQL — survives container restarts
- **Always run `verify.py` before pushing to main**
- **Always confirm production with `curl /health` after push**

---

## 16. SUMMARY — THE THREE RULES

If you remember nothing else:

1. **Allowed files only.** Declare scope before editing. Ask permission for protected/frozen files.
2. **No "done" without evidence.** Paste verify.py output (22/22), curl output, test logs.
3. **One change per commit.** Atomic. Tested. Proven.
