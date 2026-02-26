# IDNA EdTech — Claude Opus 4.6 Handoff Report

> **Generated:** 2026-02-27
> **By:** Claude Opus 4.5
> **For:** Claude Opus 4.6 (incoming sessions)
> **Repository:** github.com/idnaedtech/idna-tutor-mvp

---

## Executive Summary

IDNA EdTech "Didi" is a **production voice tutoring platform** for Indian K-10 students. Version **8.1.5** is deployed and stable with all Phase 0 requirements met and all P1 bugs fixed. The project is ready to begin **Phase 1: Foundation Refactor**.

---

## Current State (Verified)

| Metric | Value | Evidence |
|--------|-------|----------|
| Version | **v8.1.5** | `curl /health` → `{"status":"ok","version":"8.1.5"}` |
| Tests | **218 passing** | `pytest tests/ -v` |
| Verification | **22/22 checks** | `python verify.py` |
| P1 Bugs | **ALL 6 FIXED** | Commits v8.1.1 - v8.1.5 |
| Production | **LIVE** | https://idna-tutor-mvp-production.up.railway.app |

---

## Architecture Overview

### Tech Stack (Locked)
| Layer | Technology |
|-------|-----------|
| Teaching LLM | GPT-5-mini |
| Classifier LLM | GPT-4o-mini (10 categories) |
| STT | Sarvam Saarika v2.5 |
| TTS | Sarvam Bulbul v3 (simran, hi-IN) |
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL (Railway) |

### FSM Architecture
- **6 States:** GREETING, TEACHING, WAITING_ANSWER, HINT, NEXT_QUESTION, SESSION_END
- **10 Input Categories:** ACK, IDK, REPEAT, ANSWER, LANGUAGE_SWITCH, CONCEPT_REQUEST, COMFORT, STOP, TROLL, GARBLED
- **60 Combinations:** All defined, no gaps, no KeyError

### Key Files
```
app/
├── routers/student.py          # FastAPI endpoints
├── state/session.py            # SessionState dataclass
├── fsm/transitions.py          # 60-combo matrix [FROZEN]
├── fsm/handlers.py             # State handlers [FROZEN]
├── tutor/input_classifier.py   # GPT-4o-mini classifier
├── tutor/llm.py                # GPT-5-mini teaching
├── voice/stt.py                # Sarvam STT [PROTECTED]
├── voice/tts.py                # Sarvam TTS [PROTECTED]
├── content/ch1_square_and_cube.py  # 50 questions, 20 skills
tests/
├── test_*.py                   # 218 tests
verify.py                       # 22 checks
```

---

## What Was Built (v7.3.14 → v8.1.5)

### Phase 0 Achievements
1. **v8.0.0 Architecture Rewrite** — SessionState, 60-combo FSM, language persistence
2. **Voice Pipeline** — STT → Classifier → FSM → LLM → TTS (~2s latency)
3. **Content Bank** — Chapter 1: 50 questions, 3-layer teaching
4. **Test Suite** — 218 tests including 27 integration + 5 regression tests
5. **22 Verification Checks** — All passing

### P1 Bug Fixes (Complete)
| # | Bug | Fix Version |
|---|-----|-------------|
| 1 | Same-Q reload on refresh | v8.1.2 |
| 2 | HOMEWORK_HELP trap | v8.1.1 |
| 3 | Devanagari बटा parser | v8.1.1 |
| 4 | Empty TTS sentence | v8.1.1 |
| 5 | Parent split()[0] | v8.1.5 |
| 6 | Weakest-skill dead end | v8.1.5 |

---

## Non-Negotiable Rules

**NEVER violate these:**

1. **FSM is FROZEN** — 60 combinations complete, no modifications
2. **One Didi voice** — Sarvam Bulbul v3, simran, hi-IN only
3. **Language persistence** — once set, persists entire session
4. **Reteach cap** — max 3 reteaches, then force advance
5. **Indian examples only** — roti, cricket, laddoo (never Western)
6. **Respectful Hindi** — "Aap" form, "dekhiye" (never "tum")
7. **Alembic for ALL schema changes**
8. **Never create `app/models/` directory** (shadows `app/models.py`)
9. **22/22 verify.py before any commit**
10. **Never rewrite DIDI_PROMPT** — append only

---

## Next Phase: Phase 1 Foundation Refactor

### Tasks (NOT STARTED)
1. Add `boards` table via Alembic
2. Add `textbooks` table via Alembic
3. Add `content_units` table via Alembic
4. Add `student_profiles` table via Alembic
5. Extend SessionState with board/class fields
6. Parameterize FSM content injection (DB queries replace flat files)
7. API v1 versioning (`/api/v1/session/start` with `board_id`)

### Exit Gate
**New board = zero code changes, only DB inserts**

### Reference Files
- `references/schema-v81.md` — Database schema design
- `references/roadmap.md` — Phase timeline
- `references/bench-spec.md` — IDNA-Bench quality gating
- `references/stack-future.md` — Phase 2-4 tech stack

---

## Session Startup Protocol

On EVERY new session:
1. Read `MEMORY.md` — current state
2. Read `tasks/todo.md` (if exists) — pending work
3. Run `python verify.py --quick` — confirm green
4. Check `git log --oneline -5` — recent changes
5. THEN proceed with user's request

---

## Development Commands

```bash
# Pre-flight
python verify.py --quick

# Full test suite
python -m pytest tests/ -v

# Full verification (22 checks)
python verify.py

# Commit format
git commit -m "v{major}.{minor}.{patch}: brief description"

# Confirm production
curl https://idna-tutor-mvp-production.up.railway.app/health
```

---

## Skills Available

| Skill | Purpose |
|-------|---------|
| `idna-edtech-tutor` | Core IDNA development |
| `idna-kanban` | Task pipeline automation |
| `ship` | PR workflow to production |
| `deslop` | Clean AI code artifacts |
| `audit-project` | Multi-agent code review |
| `drift-detect` | Realign plans with code |
| `enhance` | Analyze for best-practice gaps |
| `perf` | Performance investigation |
| `sync-docs` | Sync documentation with code |

---

## Final Verification

```
============================================================
  [PASS] ALL 22/22 CHECKS PASSED -- safe to commit
============================================================

Tests: 218 passed
Production: {"status":"ok","version":"8.1.5"}
P1 Bugs: 0 remaining
Phase: Ready for Phase 1
```

---

*Report generated by Claude Opus 4.5 on 2026-02-27*
*All claims verified with actual command output*
