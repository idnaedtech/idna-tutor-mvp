# IDNA EdTech — Session Memory

> **Last updated:** 2026-02-27
> **Current version:** v8.1.5
> **Phase:** Phase 0 COMPLETE, ready for Phase 1

---

## Quick Status

```
Version:     v8.1.5 LIVE
Health:      {"status":"ok","version":"8.1.5"}
Tests:       218 passing
Verify:      22/22 checks passing
P1 Bugs:     ALL 6 FIXED
Next:        Phase 1 schema migration
```

---

## What Was Built (v7.3.14 → v8.1.5)

### Architecture (v8.0.0)
- Complete FSM rewrite with 60 state×input combinations
- SessionState dataclass — single source of truth
- Language persistence — set once, persists entire session
- Reteach cap — max 3 reteaches, then force advance
- Content Bank injection — 3-layer teaching (definition/analogy/vedic_trick)

### Voice Pipeline
- Sarvam Saarika v2.5 STT (~300ms, confidence 0.4)
- GPT-4o-mini classifier (10 input categories)
- GPT-5-mini teaching responses
- Sarvam Bulbul v3 TTS (simran, hi-IN)
- Latency target: ~2 seconds end-to-end

### Content
- Chapter 1: 50 questions, 20 skills (Squares & Cubes)
- Indian examples: roti, cricket, laddoo, tiles
- Respectful Hindi: "Aap" form, "dekhiye", "sochiye"

---

## P1 Bug Fixes (ALL COMPLETE)

| # | Bug | Fix | Version |
|---|-----|-----|---------|
| 1 | Same-Q reload on refresh | Track questions across sessions | v8.1.2 |
| 2 | HOMEWORK_HELP trap | Add classifier handling | v8.1.1 |
| 3 | Devanagari बटा parser | Fix Hindi fraction parsing | v8.1.1 |
| 4 | Empty TTS sentence | Guard before API call | v8.1.1 |
| 5 | Parent split()[0] | Guard against empty instruction | v8.1.5 |
| 6 | Weakest-skill dead end | Use SESSION_END, normalization | v8.1.5 |

---

## Commit History (Major Milestones)

```
a6f2071 v8.1.5: bump version number in main.py
4d12c90 v8.1.5: fix P1 bugs - parent split()[0] and SESSION_COMPLETE state
5761f1d v8.1.4: add skill pre-check.sh with fixed TTS speaker validation
da54ab6 v8.1.3: UX improvements - voice/text sync, typing indicator, TTS warmth
5a0122d v8.1.2: fix P1 Same-Q reload bug - track questions across sessions
c9047c5 v8.1.1: fix P1 bugs - Devanagari parser, empty TTS guard, homework detection
d404fab v8.1.0: update version in CLAUDE.md and refresh MEMORY.md
5ec1942 v8.0.0: architecture rewrite — SessionState, 60-combo FSM, 27 integration tests
```

---

## Next Phase: Phase 1 Foundation Refactor

| Task | Status |
|------|--------|
| Add `boards` table via Alembic | NOT STARTED |
| Add `textbooks` table via Alembic | NOT STARTED |
| Add `content_units` table via Alembic | NOT STARTED |
| Add `student_profiles` table via Alembic | NOT STARTED |
| Extend SessionState with board/class fields | NOT STARTED |
| Parameterize FSM content injection | NOT STARTED |
| API v1 versioning | NOT STARTED |

**Exit gate:** New board = zero code changes, only DB inserts

---

## Key Rules (Never Violate)

1. FSM is FROZEN — 60 combinations complete
2. One Didi voice — Sarvam simran only
3. Language persistence — once set, persists entire session
4. Alembic for ALL schema changes
5. Never create `app/models/` directory
6. 22/22 verify.py before any commit
7. Indian examples only — no Western references

---

## Files Changed This Session

- `app/tutor/memory.py` — Bug #5 fix (split()[0] guard)
- `app/routers/student.py` — Bug #6 fix (SESSION_END)
- `app/main.py` — Version bump to 8.1.5
- `tests/test_p1_fixes.py` — 5 regression tests (NEW)
- `.claude/skills/idna-edtech-tutor/SKILL.md` — Updated to v8.1.5
- `MEMORY.md` — This file (NEW)
