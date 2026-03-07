# IDNA P1 Backlog

These are the 6 known bugs that must be fixed in Phase 1.
Use `/kanban p1` to auto-create cards for these.

| # | Bug | Severity | Files | Description |
|---|-----|----------|-------|-------------|
| 1 | Same-Q reload | high | `app/routers/student.py`, `app/state/session.py` | Page refresh re-serves the same question. Need to track served question IDs in SessionState and exclude from next selection. |
| 2 | HOMEWORK_HELP trap | high | `app/tutor/input_classifier.py`, `app/fsm/transitions.py`, `app/fsm/handlers.py` | Classifier doesn't handle homework help requests. Needs new input category + transitions for all 6 states. Matrix goes from 60 to 66 combos. |
| 3 | Devanagari बटा parser | medium | `app/tutor/input_classifier.py`, `app/tutor/llm.py` | Hindi fraction input ("तीन बटा सात") not parsed correctly. Need Devanagari numeral mapping and बटा → "/" conversion. |
| 4 | Empty TTS sentence | medium | `app/voice/tts.py` | Blank TTS calls waste Sarvam API quota. Add empty string check before API call. |
| 5 | Parent split()[0] bug | low | `app/models.py` or parent report logic | Parent name parsing breaks on single names (no space to split on). Use safe split with fallback. |
| 6 | Weakest-skill dead end | medium | `app/content/`, adaptive flow logic | Adaptive flow gets stuck when no weak skill is found. Need fallback to next chapter or random skill selection. |
