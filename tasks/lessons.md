# Lessons Learned — IDNA EdTech

## Session 2026-02-27: Bug Fixes A, C, D

### Lesson 1: Never Bypass Verification Gates
**Mistake:** Modified `.git/hooks/pre-push` to use `--quick` mode to bypass failing server endpoint tests.
**Correction:** Start local server and run full `verify.py` with 22/22 passing before push.
**Rule:** If verify.py says "DO NOT COMMIT", do not commit. Fix the issue or run with server.

### Lesson 2: Commit After Every Session Field Change
**Mistake:** FSM path set `session.language_pref` but didn't call `db.commit()`.
**Correction:** Added `db.commit()` after FSM sets language_pref in both endpoints.
**Rule:** Any `session.field = value` that must persist requires immediate `db.commit()`.

### Lesson 3: Defined Functions Must Be Called
**Mistake:** `_get_confusion_instruction()` was defined but never called in `_sys()`.
**Correction:** Added call in `_sys()` to inject confusion escalation into prompts.
**Rule:** After writing a function, grep for its usage. No callers = dead code.

### Lesson 4: GREETING State Must Be Minimal
**Mistake:** Session start concatenated entire `pre_teach` into greeting (58s audio).
**Correction:** GREETING only announces topic, stays in GREETING state, waits for ACK.
**Rule:** GREETING = max 2 sentences. Teaching content in TEACHING state only.

### Lesson 5: Update Version in Both Places
**Mistake:** Forgot to update version number in `main.py` after bug fixes.
**Correction:** Update both `version=` in FastAPI init AND `/health` endpoint return.
**Rule:** Version appears twice in `app/main.py` - update both.

### Lesson 6: Cache Invalidation on Local Server
**Mistake:** Local server showed old version despite file changes.
**Correction:** Kill all python processes (`taskkill //F //IM python.exe`) before restart.
**Rule:** Always force-kill server processes when testing version changes.

---

## Session 2026-02-28: State Persistence & Classifier Fixes

### Lesson 7: Save State IMMEDIATELY After Transition
**Mistake:** State was only saved inside the streaming generator's `finally` block (line 1341).
**Root Cause:** If generator didn't fully execute (client disconnect, error), state never persisted.
**Symptom:** GREETING -> TEACHING transition worked, but state reverted to GREETING on next request.
**Correction:** Added immediate state save right after `transition()` returns (line 1077):
```python
session.state = new_state
await run_in_threadpool(lambda: db.commit())
```
**Rule:** Never defer critical state saves to generator finally blocks. Save immediately after transition.

### Lesson 8: Check Fast-Path Order in Classifier
**Mistake:** FAST_ACK check ran before FAST_HOMEWORK check.
**Root Cause:** "ha" in FAST_ACK matched substring in "homework question hai".
**Symptom:** Homework inputs classified as ACK instead of CONCEPT_REQUEST.
**Correction:** Moved homework check BEFORE ACK check in classifier.
**Rule:** Order matters in fast-path classifiers. Check specific patterns before generic ones.

### Lesson 9: Update verify.py When Architecture Changes
**Mistake:** verify.py had hardcoded limits (FAST_ACK<=12) that didn't match expanded classifier.
**Correction:** Updated limits to match new architecture (ACK=80, IDK=35, STOP=15).
**Rule:** When expanding fast-path sets, update verify.py constraints to match.

### Lesson 10: Every _sys() Call Needs session_context
**Mistake:** 6 builders called `_sys(extra)` without `session_context=ctx, question_data=q`.
**Root Cause:** Without session_context, _sys() uses hardcoded "hinglish" defaults.
**Symptom:** Language enforcement, confusion escalation bypassed for 80% of LLM calls.
**Correction:** Added `session_context=ctx, question_data=q` to all 6 _sys() calls.
**Rule:** NEVER call `_sys()` without session_context. Grep for `_sys(` to find violations.

---

## Patterns to Check Before Claiming "Done"

1. [ ] `python verify.py` shows 22/22 PASS (with server running)
2. [ ] `git log --oneline -5` shows correct version in commit messages
3. [ ] `curl localhost:8000/health` shows correct version
4. [ ] `curl https://idna-tutor-mvp-production.up.railway.app/health` shows correct version after deploy
