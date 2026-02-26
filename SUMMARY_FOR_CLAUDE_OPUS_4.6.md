# IDNA EdTech — Summary Report for Claude Opus 4.6

**Generated:** 2026-02-27 | **By:** Claude Opus 4.5 | **Version:** 8.1.5

---

## TL;DR

```
Project:     IDNA EdTech "Didi" — Voice AI tutor for Indian K-10 students
Version:     v8.1.5 LIVE on Railway
Status:      Phase 0 COMPLETE, ready for Phase 1
Tests:       218 passing
Verify:      22/22 checks passing
P1 Bugs:     ALL 6 FIXED
Production:  https://idna-tutor-mvp-production.up.railway.app
Health:      {"status":"ok","version":"8.1.5"}
```

---

## 1. What is IDNA

**Didi** (दीदी = "older sister") is an AI voice tutor that:
- Speaks Hindi/Hinglish/English naturally
- Teaches NCERT Class 8 Math step-by-step
- Uses Indian examples (roti, cricket, laddoo)
- Targets Tier 2/3 students across 33 education boards

**Vision:** India's education AI infrastructure — 22 languages, 33 boards, Classes 6-10.

---

## 2. Tech Stack (Locked — Do Not Change)

| Component | Technology | Notes |
|-----------|-----------|-------|
| Teaching LLM | GPT-5-mini | Main responses |
| Classifier | GPT-4o-mini | 10 input categories |
| STT | Sarvam Saarika v2.5 | ~300ms, threshold 0.4 |
| TTS | Sarvam Bulbul v3 | **simran, hi-IN ONLY** |
| Backend | FastAPI Python 3.11 | Async |
| Database | PostgreSQL | Railway managed |
| Hosting | Railway | Auto-deploy from main |

---

## 3. Architecture

### FSM (60 Combinations — FROZEN)
```
6 States:  GREETING → TEACHING → WAITING_ANSWER → HINT → NEXT_QUESTION → SESSION_END
10 Inputs: ACK, IDK, REPEAT, ANSWER, LANGUAGE_SWITCH, CONCEPT_REQUEST, COMFORT, STOP, TROLL, GARBLED
```

### Voice Pipeline (~2s latency)
```
Student speaks → STT (300ms) → Classifier → FSM → LLM (1200ms) → TTS (500ms) → Audio
```

### Key Files
```
app/state/session.py        # SessionState dataclass
app/fsm/transitions.py      # 60-combo matrix [FROZEN]
app/fsm/handlers.py         # State handlers [FROZEN]
app/tutor/input_classifier.py
app/tutor/llm.py
app/voice/stt.py            # [PROTECTED]
app/voice/tts.py            # [PROTECTED]
verify.py                   # 22 mandatory checks
```

---

## 4. Current Verification Status

```
[PASS] ALL 22/22 CHECKS PASSED

 1. ch1_square_and_cube.py exists           ✓
 2. Question bank loads (50 questions)      ✓
 3. All skills have pre_teach               ✓
 4. Hindi IDK in classifier                 ✓
 5. No Sochiye catch-all                    ✓
 6. clean_for_tts handles math symbols      ✓
 7. Server imports cleanly                  ✓
 8. TTS returns audio                       ✓
 9. TTS works on second call                ✓
10. Session loads Square & Cube             ✓
11. pytest passes (218 tests)               ✓
12. Audio playback in HTML                  ✓
13. Mic button or VAD present               ✓
14. No uninitialized vars                   ✓
15. No ephemeral filesystem writes          ✓
16. All API calls have timeout              ✓
17. Streaming handles LLM failures          ✓
18. SessionState has preferred_language     ✓
19. Reteach counter caps at 3               ✓
20. All 60 state x input defined            ✓
21. Integration tests pass (27 tests)       ✓
22. All checks complete                     ✓
```

---

## 5. P1 Bugs (ALL FIXED)

| # | Bug | Root Cause | Fix | Version |
|---|-----|-----------|-----|---------|
| 1 | Same-Q reload | Questions not tracked across sessions | Track in DB | v8.1.2 |
| 2 | HOMEWORK_HELP trap | Missing classifier category | Add handling | v8.1.1 |
| 3 | Devanagari parser | Hindi fractions not parsed | Fix regex | v8.1.1 |
| 4 | Empty TTS | Blank strings hit API | Guard check | v8.1.1 |
| 5 | Parent split()[0] | Empty instruction crashes | Guard check | v8.1.5 |
| 6 | Weakest-skill dead end | Invalid SESSION_COMPLETE state | Use SESSION_END | v8.1.5 |

---

## 6. Commit History

```
6d08dac v8.1.5: add MEMORY.md, Claude Opus handoff report, update SKILL.md
a6f2071 v8.1.5: bump version number in main.py
4d12c90 v8.1.5: fix P1 bugs - parent split()[0] and SESSION_COMPLETE state
5761f1d v8.1.4: add skill pre-check.sh with fixed TTS speaker validation
da54ab6 v8.1.3: UX improvements - voice/text sync, typing indicator, TTS warmth
5a0122d v8.1.2: fix P1 Same-Q reload bug - track questions across sessions
c9047c5 v8.1.1: fix P1 bugs - Devanagari parser, empty TTS guard, homework detection
5ec1942 v8.0.0: architecture rewrite — SessionState, 60-combo FSM, 27 integration tests
```

---

## 7. Non-Negotiable Rules

| Rule | Consequence of Violation |
|------|-------------------------|
| FSM is FROZEN | Entire architecture breaks |
| One Didi voice (simran) | TTS inconsistency |
| Language persists entire session | Student confusion |
| Reteach cap = 3 | Infinite loops |
| Indian examples only | Cultural mismatch |
| "Aap" form Hindi | Disrespectful tone |
| Alembic for schema changes | DB corruption risk |
| Never create `app/models/` | Import shadowing |
| 22/22 verify before commit | Production bugs |
| Never rewrite DIDI_PROMPT | Behavior regression |

---

## 8. Next Phase: Phase 1 Foundation Refactor

### Tasks (NOT STARTED)
1. `boards` table via Alembic
2. `textbooks` table via Alembic
3. `content_units` table via Alembic
4. `student_profiles` table via Alembic
5. Extend SessionState with board/class fields
6. Parameterize FSM content injection
7. API v1 versioning

### Exit Gate
**New board = zero code changes, only DB inserts**

### Reference Files
| File | Use When |
|------|----------|
| `references/schema-v81.md` | Schema work |
| `references/roadmap.md` | Planning |
| `references/bench-spec.md` | Quality gating |
| `references/stack-future.md` | Future tech decisions |

---

## 9. Session Startup Protocol

```bash
# 1. Check current state
cat MEMORY.md

# 2. Verify codebase health
python verify.py --quick

# 3. Check recent changes
git log --oneline -5

# 4. Confirm production
curl https://idna-tutor-mvp-production.up.railway.app/health

# 5. THEN proceed with task
```

---

## 10. Commands Reference

```bash
# Development
python verify.py --quick          # Fast pre-edit check
python verify.py                  # Full 22 checks (before commit)
python -m pytest tests/ -v        # Run all 218 tests

# Git
git commit -m "v{x}.{y}.{z}: description"   # Commit format
git push origin main                         # Triggers Railway deploy

# Production
curl https://idna-tutor-mvp-production.up.railway.app/health
```

---

## 11. Skills Available

| Skill | Trigger | Purpose |
|-------|---------|---------|
| `idna-edtech-tutor` | `/idna` | Core development |
| `idna-kanban` | `/kanban` | Task automation |
| `ship` | `/ship` | PR to production |
| `deslop` | `/deslop` | Clean AI artifacts |
| `audit-project` | `/audit` | Code review |
| `drift-detect` | `/drift-detect` | Plan alignment |
| `enhance` | `/enhance` | Best practices |
| `sync-docs` | `/sync-docs` | Doc updates |

---

## 12. Key Contacts & Resources

| Resource | Location |
|----------|----------|
| Repository | github.com/idnaedtech/idna-tutor-mvp |
| Production | https://idna-tutor-mvp-production.up.railway.app |
| Architecture Spec | `IDNA_v8_ARCHITECTURE.md` |
| Project Rules | `CLAUDE.md` (root) |
| Session Memory | `MEMORY.md` |
| Skill Definition | `.claude/skills/idna-edtech-tutor/SKILL.md` |

---

## Final State

```
┌─────────────────────────────────────────────────────────┐
│  IDNA EdTech v8.1.5                                     │
├─────────────────────────────────────────────────────────┤
│  verify.py:     22/22 PASSED                            │
│  Tests:         218 passed                              │
│  Production:    {"status":"ok","version":"8.1.5"}       │
│  P1 Bugs:       0 remaining                             │
│  Phase:         Ready for Phase 1                       │
└─────────────────────────────────────────────────────────┘
```

---

*Report verified with actual command output on 2026-02-27*
*Generated by Claude Opus 4.5 for Claude Opus 4.6 handoff*
