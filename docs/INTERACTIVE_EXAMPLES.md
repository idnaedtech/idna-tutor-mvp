# Interactive Code Examples - Try Now!

**Server Status:** 🟢 Running on http://localhost:8000
**Endpoint:** `/api/live/tutor_turn`

---

## 🎮 **Example 1: Session Start**

```bash
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo_001",
    "event": "START_SESSION",
    "client_ts_ms": 1706450000000,
    "language": "hinglish"
  }'
```

**Expected Response:**
```json
{
  "speak": {
    "text": "Namaste beta! Aaj hum math practice karenge. Ready ho?",
    "ssml": "<speak>Namaste beta!<break time=\"300ms\"/>..."
  },
  "voice_plan": {
    "max_sentences": 2,
    "required": ["greeting", "ready_prompt"],
    "forbidden": ["lengthy_intro"]
  }
}
```

**What to notice:**
- 🎯 `tutor_intent`: "SESSION_START"
- 🗣️ `language`: "hinglish" (matches request)
- 🎵 SSML has natural pauses
- ⏭️ `next_action.type`: "WAIT_STUDENT"

---

## 🎮 **Example 2: Get a Question**

```bash
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo_001",
    "event": "REQUEST_QUESTION",
    "client_ts_ms": 1706450010000,
    "language": "en"
  }'
```

**Expected Response:**
```json
{
  "question_id": "demo_q1",
  "state": "IN_QUESTION",
  "tutor_intent": "ASK_FRESH",
  "canonical": {
    "question_text": "What is 2/3 + 1/4?",
    "expected_answer": "11/12",
    "hint_1": "Find a common denominator for 3 and 4.",
    "solution_steps": [
      "LCM of 3 and 4 is 12.",
      "2/3 = 8/12 and 1/4 = 3/12.",
      "8/12 + 3/12 = 11/12."
    ]
  },
  "speak": {
    "text": "Achha beta, what is 2/3 plus 1/4? Apna time lo."
  }
}
```

**What to notice:**
- 📚 `canonical` contains all question data
- 🚫 `voice_plan.forbidden`: ["hints", "solution"]
- 💡 Hints available but NOT spoken yet

---

## 🎮 **Example 3: Submit Wrong Answer (Attempt 1)**

```bash
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo_001",
    "event": "SUBMIT_ANSWER",
    "client_ts_ms": 1706450020000,
    "student_utterance": "five by seven",
    "asr_confidence": 0.92,
    "language": "en"
  }'
```

**Expected Response:**
```json
{
  "state": "SHOWING_HINT",
  "attempt_no": 1,
  "is_correct": false,
  "tutor_intent": "GUIDE_THINKING",
  "teacher_move": "PROBE",
  "error_type": "incomplete_answer",
  "goal": "Diagnose if student knows common denominator concept",
  "voice_plan": {
    "max_sentences": 2,
    "required": ["encouragement", "one_guiding_question"],
    "forbidden": ["say_wrong", "full_solution", "multiple_questions"]
  },
  "speak": {
    "text": "Hmm beta, close but not quite. Fractions add karne se pehle common denominator chahiye. 3 aur 4 ka common denominator kya hoga?",
    "ssml": "<speak>Hmm beta,<break time=\"300ms\"/> close but not quite.<break time=\"200ms\"/> Fractions add karne se pehle common denominator chahiye.<break time=\"450ms\"/> 3 aur 4 ka common denominator kya hoga?</speak>"
  }
}
```

**What to notice:**
- ❌ `is_correct`: false
- 🎯 `teacher_move`: "PROBE" (asking diagnostic question)
- 🧠 `error_type`: "incomplete_answer"
- 🎵 SSML has thoughtful pauses (300ms, 200ms, 450ms)
- 🚫 Doesn't say "wrong" (forbidden in voice_plan)
- ✅ Asks ONE guiding question (as required)

---

## 🎮 **Example 4: Interrupt Handling**

```bash
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo_001",
    "event": "INTERRUPT",
    "client_ts_ms": 1706450025000
  }'
```

**Expected Response:**
```json
{
  "state": "IN_QUESTION",
  "tutor_intent": "INTERRUPT_ACKNOWLEDGED",
  "voice_plan": {
    "max_sentences": 0
  },
  "speak": {
    "text": "",
    "ssml": ""
  },
  "next_action": {
    "type": "WAIT_STUDENT"
  }
}
```

**What to notice:**
- 🔇 `speak` is empty (tutor stops talking)
- 🎯 `voice_plan.max_sentences`: 0 (silence)
- 📝 Event gets logged for telemetry
- ⏭️ Waits for student to continue

---

## 🎮 **Example 5: Repeat Request**

```bash
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo_001",
    "event": "REPEAT",
    "client_ts_ms": 1706450030000,
    "language": "hi"
  }'
```

**Expected Response:**
```json
{
  "tutor_intent": "REPEAT",
  "voice_plan": {
    "max_sentences": 2,
    "required": ["original_message"],
    "forbidden": ["additional_hints"]
  },
  "speak": {
    "text": "Sure beta. What is 2/3 plus 1/4?"
  }
}
```

**What to notice:**
- 🔁 Repeats last message
- 🚫 Doesn't add extra hints (forbidden)
- 📝 TODO: Will fetch from session history (Day 3)

---

## 🎮 **Example 6: End Session**

```bash
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo_001",
    "event": "END_SESSION",
    "client_ts_ms": 1706450100000
  }'
```

**Expected Response:**
```json
{
  "state": "COMPLETED",
  "tutor_intent": "SESSION_END",
  "voice_plan": {
    "max_sentences": 2,
    "required": ["summary_praise"],
    "forbidden": ["criticism"]
  },
  "speak": {
    "text": "Bahut accha kiya aaj beta! You got 3 out of 5 correct. Kal phir milte hain!",
    "ssml": "<speak>Bahut accha kiya aaj beta!<break time=\"300ms\"/> You got 3 out of 5 correct.<break time=\"400ms\"/> Kal phir milte hain!</speak>"
  },
  "next_action": {
    "type": "END_SESSION"
  }
}
```

**What to notice:**
- 👋 `next_action.type`: "END_SESSION" (no more turns)
- 🎉 Positive closing message
- 🚫 No criticism (forbidden)
- 📊 TODO: Real performance summary (Day 3)

---

## 🎮 **Example 7: With Telemetry**

```bash
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "demo_001",
    "event": "SUBMIT_ANSWER",
    "client_ts_ms": 1706450040000,
    "student_utterance": "twelve",
    "asr_confidence": 0.85,
    "language": "en",
    "telemetry": {
      "rtt_ms": 850,
      "packet_loss_pct": 0.15,
      "mode": "LIVE"
    }
  }'
```

**Expected Response:**
```json
{
  "fallback": {
    "allowed": true,
    "recommended_mode": "LIVE"
  }
}
```

**What to notice:**
- 📊 `telemetry` included in request
- 🔄 Backend could recommend fallback if RTT > 1000ms
- 📝 Gets logged for network quality monitoring

**Future (Day 5):**
```python
if request.telemetry and request.telemetry.rtt_ms > 1000:
    response.fallback.recommended_mode = "TTS"
```

---

## 🔍 **Check the Logs**

After running these examples, check the server logs:

```bash
# Read the output file
cat C:\Users\User\AppData\Local\Temp\claude\C--Users-User\tasks\b5c2e10.output

# Or tail in real-time (if server running)
tail -f C:\Users\User\AppData\Local\Temp\claude\C--Users-User\tasks\b5c2e10.output
```

**Example Log Entry:**
```json
{
  "timestamp": "2026-02-02T08:54:53.112099Z",
  "level": "INFO",
  "message": "Live turn: SUBMIT_ANSWER",
  "event": "live_turn",
  "session_id": "demo_001",
  "live_event": "SUBMIT_ANSWER",
  "latency_ms": 1.71,
  "tutor_intent": "GUIDE_THINKING",
  "is_correct": false,
  "attempt_no": 1,
  "state": "SHOWING_HINT"
}
```

---

## 🧪 **Testing Different Languages**

### English Mode
```bash
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -H "Content-Type: application/json" \
  -d '{"session_id":"lang_test","event":"START_SESSION","client_ts_ms":1706450000000,"language":"en"}' \
  | jq '.speak.text'
```

### Hindi Mode
```bash
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -H "Content-Type: application/json" \
  -d '{"session_id":"lang_test","event":"START_SESSION","client_ts_ms":1706450000000,"language":"hi"}' \
  | jq '.speak.text'
```

### Hinglish Mode (Default)
```bash
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -H "Content-Type: application/json" \
  -d '{"session_id":"lang_test","event":"START_SESSION","client_ts_ms":1706450000000,"language":"hinglish"}' \
  | jq '.speak.text'
```

---

## 🎯 **Interactive Testing Script**

Save this as `test_live_api.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api/live/tutor_turn"
SESSION_ID="test_$(date +%s)"

echo "🚀 Testing Live API with session: $SESSION_ID"
echo ""

# Test 1: Start Session
echo "📝 Test 1: START_SESSION"
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"event\":\"START_SESSION\",\"client_ts_ms\":1706450000000}" \
  | jq '.tutor_intent, .speak.text'
echo ""

# Test 2: Request Question
echo "📝 Test 2: REQUEST_QUESTION"
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"event\":\"REQUEST_QUESTION\",\"client_ts_ms\":1706450010000}" \
  | jq '.question_id, .canonical.question_text'
echo ""

# Test 3: Wrong Answer
echo "📝 Test 3: SUBMIT_ANSWER (wrong)"
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"event\":\"SUBMIT_ANSWER\",\"client_ts_ms\":1706450020000,\"student_utterance\":\"5/7\"}" \
  | jq '.is_correct, .attempt_no, .teacher_move'
echo ""

# Test 4: End Session
echo "📝 Test 4: END_SESSION"
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION_ID\",\"event\":\"END_SESSION\",\"client_ts_ms\":1706450100000}" \
  | jq '.state, .next_action.type'
echo ""

echo "✅ All tests complete!"
```

---

## 📊 **Performance Testing**

Test latency with multiple requests:

```bash
for i in {1..10}; do
  START=$(date +%s%N)
  curl -s -X POST http://localhost:8000/api/live/tutor_turn \
    -H "Content-Type: application/json" \
    -d '{"session_id":"perf_test","event":"REQUEST_QUESTION","client_ts_ms":1706450000000}' \
    > /dev/null
  END=$(date +%s%N)
  DURATION=$((($END - $START) / 1000000))
  echo "Request $i: ${DURATION}ms"
done
```

**Expected Output:**
```
Request 1: 15ms  (cold start)
Request 2: 2ms
Request 3: 2ms
Request 4: 2ms
...
```

---

## 🚨 **Error Testing**

### Test 1: Invalid Event
```bash
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -H "Content-Type: application/json" \
  -d '{"session_id":"error_test","event":"INVALID_EVENT","client_ts_ms":1706450000000}'
```

**Expected:** 422 Unprocessable Entity

### Test 2: Missing Required Field
```bash
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -H "Content-Type: application/json" \
  -d '{"event":"START_SESSION","client_ts_ms":1706450000000}'
```

**Expected:** 422 with message about missing `session_id`

### Test 3: Wrong Type
```bash
curl -X POST http://localhost:8000/api/live/tutor_turn \
  -H "Content-Type: application/json" \
  -d '{"session_id":"test","event":"START_SESSION","client_ts_ms":"not_a_number"}'
```

**Expected:** 422 with type error

---

## 🎓 **What to Learn From These Examples**

1. **Type Safety:** Pydantic catches all invalid inputs
2. **Structured Responses:** Every field has a purpose
3. **SSML Prosody:** Natural pauses make tutor sound human
4. **Teacher Policy:** Diagnostic moves (PROBE, HINT, REVEAL)
5. **Voice Plan:** Backend controls what Gemini can/can't say
6. **Latency:** Sub-2ms responses (before real logic added)
7. **Logging:** Every turn tracked with full context

---

**Try these examples now! The server is running and ready.** 🚀
