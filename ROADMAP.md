# ROADMAP.md — IDNA EdTech Development Tracker

> **Read by Claude Code at every session start (via CLAUDE.md protocol).**
> **Updated by:** Claude Code (task status) + CEO (priorities/scope)
> **Last updated:** 2026-03-08

---

## P0 — Core Tutoring Loop (MUST PASS BEFORE ANYTHING ELSE)

- [x] v10 DIDI_BASE prompt — teacher persona replacing 117-line rules ✅ 2026-03-02
- [x] v10 Phase A — language injection, re_greet builder, greeting language ✅ 2026-03-02
- [x] v10 Phase B — strings.py, simplified builders, GPT-4.1 role change ✅ 2026-03-02
- [x] P0 Teaching loop fix (5 database-confirmed bugs) ✅ v10.0.2 2026-03-05
  - [x] Bug 1: CONCEPT_REQUEST increments teaching_turn (state_machine.py + db.commit fix)
  - [x] Bug 2: Non-streaming nudge respects language_pref (student.py:558)
  - [x] Bug 3: Devanagari meta-question patterns (preprocessing.py:206-220)
  - [x] Bug 4: Emotional distress detection (preprocessing.py + instruction_builder.py)
  - [x] Bug 5: Response length guard for voice (instruction_builder.py:400)
- [x] P0 Smoke test fixes (4 remaining issues) ✅ v10.0.3 2026-03-06
  - [x] Fix A: Garbled Bhojpuri/Maithili → LANG_INSTRUCTIONS prohibits regional dialects
  - [x] Fix B: Meta-question routing → 8 new patterns for chapter/topic detection
  - [x] Fix C: Confusion escalation → turn 3 asks guided question, turn 4+ offers break
  - [x] Fix D: TTS truncation + display → max 500 chars, line breaks between sentences
  - **Production v10.0.3 deployed**
- [x] P0 Language auto-detection — switch to English when student speaks English ✅ 2026-03-06
  - [x] detect_input_language() in preprocessing.py (Devanagari ratio + Hindi Roman words)
  - [x] check_language_auto_switch() — 2 consecutive English messages triggers switch
  - [x] GREETING special case — first English message switches immediately
  - [x] Integrated in BOTH streaming + non-streaming endpoints
  - [x] consecutive_english_count column + migration
  - [x] 23 new tests (323 total), verify.py 22/22
- [x] P0 Remove ib_v9 path — both endpoints use build_prompt() ✅ 2026-03-07
  - [x] Non-streaming endpoint (line 915) now uses build_prompt() from instruction_builder.py
  - [x] Removed instruction_builder_v9 import (kept file for reference)
  - [x] Live session test passed: state transitions, language auto-detect, V10 persona active
  - [x] verify.py 22/22, 323 tests passing
- [x] P0 Debug logging for meta-question routing ✅ 2026-03-07
  - [x] RAW INPUT logging at both endpoints
  - [x] META-CHECK logging inside detect_meta_question()
  - [x] META-ROUTE logging at routing decision point
  - [x] RESPONSE TO FRONTEND logging for text display debugging
  - [x] Production test: meta-questions NOW WORKING (4/4 variations pass)
- [x] P0 Pipeline audit fixes (audit-driven, evidence-based) ✅ 2026-03-07
  - [x] Fix 1: Remove "ALWAYS ECHO BACK" instruction — Didi no longer parrots "You said..."
  - [x] Fix 2: Preserve apostrophes in _normalize() — FAST_IDK matches "didn't understand"
  - [x] Fix 3: Add ANSWER_EVAL debug logging — routing after answer evaluation
  - [x] Fix 4: Add FRONTEND_SEND debug logging — text display troubleshooting
  - [x] verify.py 22/22, 323 tests passing
- [x] v10.1 Question-First Mode — radical simplification for pilot ✅ 2026-03-07
  - [x] New DIDI_BASE: practice partner persona (was: teacher monologue)
  - [x] GREETING → WAITING_ANSWER: skip teaching, go straight to question
  - [x] Fix garbled Hindi: preserve Devanagari matras in clean_for_tts()
  - [x] Fix comfort loop: exit after 2 comfort turns, accept learning intent phrases
  - [x] Telugu support: LANG_TELUGU, auto-detection, meta-question responses, greeting
  - [x] v10.1.1: Numbers display as digits (49) not words (four nine)
  - [x] v10.1.1: Hindi (Devanagari) input auto-switches hinglish→hindi
  - [x] Tests updated: 327 passing, verify.py 22/22
  - [x] **Deployed v10.1.1 to Railway**
- [x] v10.2.0 Definitive Fix — 6 ship-blocking bugs ✅ 2026-03-08
  - [x] Bug 1 (Answer Loop): Classifier detects answers in HINT states + number words + true/false
  - [x] Bug 2 (Text Not Rendering): Text shows FIRST before audio, never gated on playback
  - [x] Bug 3 (Garbled Hindi): Strengthened matra requirement in LANG_INSTRUCTIONS + diagnostic logging
  - [x] Bug 4 (Wrong Chapter): Updated to "Squares, Cubes and their Roots"
  - [x] Bug 5 (Apostrophe): Added no-apostrophe variants to FAST_IDK
  - [x] Bug 6 (Numbers Display): Verified v10.1.1 fix in place
  - [x] 336 tests passing, verify.py 22/22
  - [x] Smoke test 8/8 passed
  - [x] **Deployed v10.2.0 to Railway**
- [x] v10.3.0 Interaction Quality — acknowledge student, fix question loop, handle meta-questions ✅ 2026-03-11
  - [x] Change 1: DIDI_BASE acknowledgment rules (11-15) — always acknowledge before responding
  - [x] Change 2: PICK_NEXT debug logging — trace question selection in both endpoints
  - [x] Change 3: Answer evaluation prompts — explicit acknowledgment of student's specific answer
  - [x] Change 4: META_QUESTION handling in WAITING_ANSWER, HINT_1, HINT_2 states
  - [x] Change 5: Adaptive quantity — "too many" triggers scope reduction, not comfort
  - [x] 347 tests passing (11 new), verify.py 19/22 (3 = server not running)
- [ ] Live student test — clean 5-question session without loop/crash/language reset
- [ ] 10 students using Didi regularly (Nizamabad/Hyderabad)

### P0 Exit Criteria
- Student says "I don't understand" 3x → gets 3 DIFFERENT explanations
- Student says "कौन सा चैप्टर" → gets direct chapter answer
- Language stays English for ALL turns after switch (including nudges, including auto-detection)
- Student says "मैं उदास हूं" → Didi acknowledges emotion FIRST
- No response exceeds 3 sentences via TTS

---

## P1 — Foundation Refactor (After P0 passes)

- [ ] Student profiles table (cross-session memory: weak_topics, mastery_map, learning_pace)
- [ ] Class 8 content bank — remaining 15 chapters (Hindi + English + Telugu)
- [ ] Class 7 content bank — 15 chapters
- [ ] Telugu live test with real student
- [ ] PWA manifest for Android "Add to Home Screen"
- [ ] Warm-up conversation flow (2-turn warmup before teaching)
- [ ] Structured questions with sub-step evaluation
- [ ] P1 bug backlog (same-Q reload, HOMEWORK_HELP, Devanagari parser, empty TTS)

---

## P2 — Multi-Board MVP (After P1 passes)

- [ ] Schema evolution: boards, textbooks, content_units tables
- [ ] Content bank migration from flat files to PostgreSQL
- [ ] Telangana (BSETS) board content
- [ ] Maharashtra (MSBSHSE) board content
- [ ] ICSE board content
- [ ] API v1 versioning with board_id parameter
- [ ] IDNA-Bench Layer 1 (IDNA-Reason): 100 GSM8K-style problems per class

---

## P3 — Platform (After P2 passes)

- [ ] IDNA-Bench full suite (5 proprietary layers)
- [ ] Content factory (AI-generated + human-reviewed)
- [ ] Multi-language routing (language detection, code-switching)
- [ ] Parent WhatsApp voice reports
- [ ] Memory-R1 integration (RL-based long-term student memory)

---

## P4 — Infrastructure (After P3 passes)

- [ ] On-device SLM (PersonaPlex 7B or equivalent)
- [ ] BharathCloud GPU (Hyderabad P3)
- [ ] Government partnerships (IndiaAI, NCERT)
- [ ] IDNA-Bench research publication (NeurIPS/ACL)
- [ ] Full 33+ board coverage
