# IDNA Project Memory

## Current State (2026-02-21)

**Version**: v7.3.28-fix2
**Status**: Server running on http://localhost:8000
**Last verify.py**: PASSED (9/9 checks in quick mode)
**Questions loaded**: 60 questions, 19 skills

### Recent Changes (v7.3.22 → v7.3.28-fix2)
- v7.3.28-fix2: PostgreSQL boolean migration syntax
- v7.3.28-fix1: Chapter question now correctly shows chapter name
- v7.3.28: Three fixes — chapter context, answer flexibility, empathy cap
- v7.3.27: Fix NEXT_QUESTION state not transitioning to WAITING_ANSWER
- v7.3.26: Fix streaming endpoint missing question picker
- v7.3.25: Fix question content translation in English mode
- v7.3.24: Fix Hindi leak in English mode
- v7.3.23: Remove debug logging from v7.3.20
- v7.3.22: Chapter metadata + language persistence + math accuracy

---

## MANDATORY WORKFLOW
1. After ANY file modification, run: `python verify.py`
2. Before ANY commit, use wiring-checker subagent
3. Never use `--no-verify` flag
4. Never claim "done" without verify.py showing all checks PASSED
5. Never modify verify.py itself

## DEFINITION OF "WIRED"
A component is "wired" only if you can show:
- The call site (file:line) where it's invoked
- The import statement that brings it in
File existence alone is NOT wiring.

## TASK TRACKING
Every task's TodoWrite list MUST end with:
- Run wiring-checker subagent
- Run verify.py — confirm all checks PASSED
- Commit and push (only when user asks)
Do NOT mark task as completed until these are done.

## LINT COMMAND
The lint/verify command for this project is: `python verify.py`

## Key Endpoints
| Endpoint | URL |
|----------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Student UI | http://localhost:8000/web/student.html |
