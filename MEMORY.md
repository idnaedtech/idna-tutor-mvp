# IDNA EdTech — Session Memory

> **Last updated:** 2026-03-14
> **Current version:** v10.6.7
> **Phase:** P0 smoke test PASSED. Pilot prep in progress.

---

## Quick Status

```
Version:     v10.6.7 LIVE on Railway
Domain:      didi.idnaedtech.com
Health:      {"status":"ok","version":"10.6.7"}
Tests:       398 test functions, 11 test files
Verify:      22/22 checks passing
Content:     84 questions (74 active), L1:10 L2:9 L3:14 L4:22 L5:19
Languages:   Hindi, English, Hinglish, Telugu
LLMs:        GPT-4.1 (teaching) + GPT-4.1-mini (classifier + inline eval)
Next:        Pilot launch (10 students, Nizamabad)
```

---

## What's Built (v10.x Series Summary)

### v10.0.x — V10 Persona + P0 Bug Fixes (2026-03-02 to 03-07)
- V10 DIDI_BASE: warm teacher persona replacing 117-line rules
- GPT-4.1 as teaching LLM (was GPT-5-mini, then GPT-4o)
- 5 database-confirmed P0 bugs fixed (teaching_turn, nudge, Devanagari, distress, length)
- Language auto-detection (2 consecutive English → auto-switch)
- Unified pipeline: both endpoints use instruction_builder.py build_prompt()
- ib_v9 removed from active path

### v10.1.x — v10.3.x — Interaction Quality (2026-03-07 to 03-11)
- Question-first mode (radical simplification for pilot)
- Answer evaluation: LLM-based primary + deterministic regex fallback
- Acknowledgment rules, meta-question routing, adaptive quantity
- Debug output system in chat UI (classifier, verdict, state, latency)
- Session review API (/review?key=idna2026)

### v10.4.0 — 5-Level Teaching Scaffold (2026-03-11)
- Level 1: Multiplication recall → Level 5: Application/methods
- First question = Level 2. 3 correct → level up. 2 wrong → level down.
- current_level, consecutive_correct, consecutive_wrong tracked per session

### v10.5.x — Performance + Inline Eval (2026-03-11 to 03-12)
- Parallel first-sentence TTS optimization
- Inline answer evaluation: combine eval + response in one LLM call
- [CORRECT]/[INCORRECT] prefix parsing with regex fallback

### v10.6.x — Production Hardening (2026-03-12 to 03-14)
- v10.6.0: Level-aware question picker (strict WHERE level = current_level)
- v10.6.4: Telugu support (_lang helper, TTS mapping, language pre-scan)
- v10.6.4: Pilot student accounts (PINs 1001-1010)
- v10.6.4: NEXT_QUESTION always transient (double-answer fix)
- v10.6.5: Polish fixes (solution fallback, dash→comma, thinking indicator)
- v10.6.6: Question level audit (12 questions retagged from student test data)
- v10.6.7: Hint loop death spiral fix, solution leak fix, aapne-poocha stripping

---

## Real Student Test Results (v10.6.5, March 14)

Idhant (Class 8 CBSE) completed full session. Findings:
- Level system works: L2 questions → 3 correct → level up → L3 questions
- Double-answer fix works: no repeated questions
- sq_e04 served at wrong level (L3 instead of L4) → fixed in v10.6.6
- Hint loop death spiral on cb_e03 → fixed in v10.6.7
- TTS latency 3-7s is the #1 UX barrier (waiting on Sarvam streaming)

---

## Architecture (Dual Pipeline — Tech Debt)

Two FSMs run in parallel:
- **v7.3 FSM** (state_machine.py): Drives actual teaching flow, returns Action objects
- **v8.0 FSM** (fsm/transitions.py): Side effects only (language, empathy)

Both endpoints use the same instruction_builder.py build_prompt().

---

## Key Rules (Never Violate)

1. FSM is skeleton — new board = data insert, zero code change
2. One Didi voice — Sarvam simran only
3. Language persistence — once set, persists entire session
4. Every `_sys()` call needs `session_context=ctx, question_data=q`
5. Alembic for ALL schema changes
6. Never create `app/models/` directory
7. 22/22 verify.py + all tests pass before any commit
8. One change per commit, atomic, tested

---

## Next Actions (Ordered)

1. v10.6.8: Update all reference docs to v10.6.x reality
2. Phase 1 memory persistence: student_profiles table
3. Pilot launch: 10 students, Nizamabad tuition center
4. Content expansion: NCERT Ch 5-6 gap analysis ready (34 new questions drafted)
