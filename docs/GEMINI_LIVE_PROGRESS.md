# Gemini Live Integration Progress

**Started:** February 2, 2026
**Status:** Day 1 Complete ✅
**Architecture:** Brain (Backend) + Voice (Gemini Live)

---

## ✅ Day 1: Contracts and Scaffolding (COMPLETE)

**Duration:** ~1 hour
**Commit:** `7773c4a` - "Day 1: Add Gemini Live contracts and scaffolding"

### What Was Built

#### 1. Pydantic Models (`models/live_models.py`)
Created comprehensive type-safe models for Gemini Live API:

- **LiveEvent** - Enum with 7 event types:
  - START_SESSION, REQUEST_CHAPTER, REQUEST_QUESTION
  - SUBMIT_ANSWER, INTERRUPT, REPEAT, END_SESSION

- **LiveTurnRequest** - Input from Gemini Live:
  - session_id, event, client_ts_ms
  - student_utterance, asr_confidence, language
  - telemetry (rtt_ms, packet_loss_pct, mode)

- **LiveTurnResponse** - Output to Gemini Live:
  - session_id, question_id, state, attempt_no
  - tutor_intent, voice_plan, canonical, speak
  - teacher_move, error_type, goal (debugging)

- **Supporting Models**:
  - VoicePlan (max_sentences, required, forbidden)
  - SpeakDirective (text, ssml)
  - NextAction (WAIT_STUDENT, AUTO_CONTINUE, END_SESSION)
  - Canonical (question_text, hints, solution_steps)

#### 2. Live API Router (`routes/live_api.py`)
Single authoritative endpoint: `POST /api/live/tutor_turn`

**Event Handlers:**
- `handle_start_session()` - Welcome message with greeting
- `handle_select_chapter()` - Chapter selection confirmation
- `handle_get_question()` - Deliver next question
- `handle_submit_answer()` - Core tutoring logic (mock for now)
- `handle_interrupt()` - Student barge-in handling
- `handle_repeat()` - Repeat last message
- `handle_end_session()` - Session summary and goodbye

**Structured Logging:**
- JSON-formatted logs with latencies
- Tracks: session_id, intent, is_correct, attempt_no
- Logs every turn for observability

#### 3. Integration (`web_server.py`)
- Added import: `from routes.live_api import router as live_router`
- Included router: `app.include_router(live_router)`
- New endpoint available: `/api/live/tutor_turn`

### Done Criteria Met ✅

| Criteria | Status | Evidence |
|----------|--------|----------|
| Can POST SUBMIT_ANSWER to /api/live/tutor_turn | ✅ | `curl` tests successful |
| Receive valid LiveTurnResponse with speak.ssml | ✅ | SSML with pauses returned |
| Logs show session_id, question_id, attempt_no | ✅ | Structured JSON logs working |

### Test Results

```bash
# Test 1: START_SESSION
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -d '{"session_id":"test_123","event":"START_SESSION","client_ts_ms":1706450000000}'
# Response: "Namaste beta! Aaj hum math practice karenge. Ready ho?"

# Test 2: REQUEST_QUESTION
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -d '{"session_id":"test_123","event":"REQUEST_QUESTION","client_ts_ms":1706450000000}'
# Response: Question with SSML, canonical content, voice_plan

# Test 3: SUBMIT_ANSWER (wrong answer)
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -d '{"session_id":"test_123","event":"SUBMIT_ANSWER","student_utterance":"five by seven"}'
# Response: GUIDE_THINKING intent with hint, attempt_no=1, is_correct=false
```

### Latency Metrics

```
Endpoint: POST /api/live/tutor_turn
Average latency: 5.44ms
- First call: 13.32ms (cold start)
- Subsequent: 1.29ms, 1.71ms
```

---

## 📋 Remaining Work

### Day 2: Browser WebSocket Prototype (Next)
- Add LIVE_MODE toggle in UI
- Implement WebSocket connection to Gemini Live
- Stream microphone audio to Gemini
- Create UI states: Listening → Thinking → Speaking
- Play streaming audio in browser

**Estimated Time:** 4-6 hours

### Day 3: Function Calling Bridge
- Register `tutor_turn` tool in Gemini Live session
- Wire Gemini ASR → tutor_turn → Gemini TTS
- Ensure Gemini speaks ONLY backend-provided SSML

**Estimated Time:** 3-4 hours

### Day 4: Barge-in + Interruption
- Natural interruption when student speaks
- FSM state preservation across interrupts

**Estimated Time:** 2-3 hours

### Day 5: 3-Tier Fallback
- Auto-fallback: LIVE → TTS → TEXT
- No error messages shown to child

**Estimated Time:** 3-4 hours

### Day 6: Tutor Feel Tuning
- Per-intent SSML templates
- Pacing rules (700-900ms pauses)
- Micro-praise after correct steps

**Estimated Time:** 2-3 hours

### Day 7: Demo Hardening
- Cost guardrails (max minutes, kill-switch)
- Demo script with curated questions
- Architecture slide for investors

**Estimated Time:** 2-3 hours

---

## 🎯 Architecture Principle

```
┌─────────────────────────────────────────┐
│  Gemini Live = Ears + Larynx            │
│  (ASR, TTS, barge-in)                   │
│                                         │
│  IDNA Backend = Brain                   │
│  (FSM, Evaluator, TutorIntent)          │
│                                         │
│  Gemini NEVER decides correctness       │
│  Backend ALWAYS controls the flow       │
└─────────────────────────────────────────┘
```

**Key Principle:** ONE authoritative function: `tutor_turn()`

---

## 📊 Current State

**Server Status:** 🟢 Running on http://localhost:8000
**Endpoints:** 21 total (20 existing + 1 new Live API)
**Database:** SQLite with 51 sessions, 1 student
**Git:** Clean working tree, all changes committed

---

## 🚀 Next Steps

1. **Day 2 Implementation** - Browser WebSocket client
2. **Environment Setup** - Add `GOOGLE_API_KEY` for Gemini Live
3. **Frontend Work** - Create `web/gemini_live.js` client
4. **Testing** - Voice-to-voice roundtrip

---

**Note:** All mock responses in Day 1 will be replaced with real FSM/Evaluator/TutorIntent logic in Day 3+ as we integrate deeper with existing backend.
