# IDNA Project Memory

## Current State (2026-02-23)

**Version**: v8.1.0
**Status**: Production running on Railway
**Production URL**: https://idna-tutor-mvp-production.up.railway.app
**Last verify.py**: PASSED (22/22 checks)
**Questions loaded**: 50 questions, 20 skills
**Tests**: 203 passed

### Recent Changes (v8.0.1 → v8.1.0)

- v8.1.0: Update CLAUDE.md with comprehensive project guidelines
- v8.1.0: Fix Content Bank template translation for English mode
- v8.1.0: Fix P0 bugs — datetime mismatch and legacy state normalization
- v8.1.0: Add auto-migration on startup for production DB
- v8.0.1: Architecture rewrite with v8.0 FSM

### P0 Bugs Fixed (2026-02-23)

| Bug | Issue | Fix |
|-----|-------|-----|
| Language persistence | Student asked for English 4x, Didi reverted to Hindi | Added `translate_instruction` to Content Bank reteach prompts |
| Datetime crash | `TypeError: can't subtract offset-naive and offset-aware datetimes` | Normalize timezone before subtraction |
| Legacy state crash | `ValueError: 'HINT_1' is not a valid TutorState` | Added `_normalize_state()` mapper |
| Meta-questions | "which chapter" ignored | Meta-question detector + direct response |
| Confusion loop | Same analogies repeated 5+ times | Content Bank escalation with varied material |

### v8.0 Architecture

- **6 States**: GREETING, TEACHING, WAITING_ANSWER, HINT, NEXT_QUESTION, SESSION_END
- **10 Input Categories**: ACK, IDK, REPEAT, ANSWER, LANGUAGE_SWITCH, CONCEPT_REQUEST, COMFORT, STOP, TROLL, GARBLED
- **60 Transitions**: Complete state × input matrix (no KeyError possible)
- **Language persistence**: preferred_language set by LANGUAGE_SWITCH, injected in EVERY prompt
- **Reteach cap**: After 3 IDKs/REPEATs, forces transition to WAITING_ANSWER

---

## MANDATORY WORKFLOW

1. Before ANY edit: `python verify.py --quick`
2. After ANY file modification: `python verify.py --quick`
3. Before ANY commit: `python verify.py` (full 22 checks)
4. Use wiring-checker subagent for multi-file changes
5. Never use `--no-verify` flag
6. Never claim "done" without verify.py showing 22/22 PASSED
7. After push: confirm production with `curl /health`

## DEFINITION OF "WIRED"

A component is "wired" only if you can show:
- The call site (file:line) where it's invoked
- The import statement that brings it in
File existence alone is NOT wiring.

## DEFINITION OF "DONE"

- Local: verify.py shows 22/22 PASSED
- Production: curl /health returns expected version
- v8.0 FSM: Reteach cap test passes (3 IDKs → WAITING_ANSWER)
- Language: 9+ turns all in requested language

## LINT COMMAND

The lint/verify command for this project is: `python verify.py`

## Key Endpoints

| Endpoint | Local | Production |
|----------|-------|------------|
| Health | http://localhost:8000/health | https://idna-tutor-mvp-production.up.railway.app/health |
| API Docs | http://localhost:8000/docs | — |
| Student UI | http://localhost:8000/ | https://idna-tutor-mvp-production.up.railway.app/ |

## Protected Files (Do Not Modify Without Permission)

- `app/fsm/transitions.py` — FROZEN
- `app/fsm/handlers.py` — FROZEN
- `app/voice/stt.py` — Protected
- `app/voice/tts.py` — Protected
- `CLAUDE.md` — CEO only
- `.claude/agents/` — Read-only
