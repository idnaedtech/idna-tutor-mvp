# IDNA EdTech - Hybrid Live Voice Implementation
## 1-Week Checklist (Zero Hand-Waving)

**Version:** 1.0
**Date:** January 28, 2026
**Goal:** Integrate Gemini Live as voice layer while keeping TutorIntent as brain

---

## Pre-requisites

- [ ] Google Cloud project with Gemini API enabled
- [ ] `GOOGLE_API_KEY` environment variable set
- [ ] Current IDNA MVP working (TutorIntent + Google TTS)
- [ ] WebSocket-capable hosting (Railway supports this)

---

## Day 1: Contracts + Scaffolding

### Tasks

- [ ] Create `/api/live/tutor_turn` endpoint
- [ ] Create Pydantic models:
  - `LiveTurnRequest`
  - `LiveTurnResponse`
  - `VoicePlan`
  - `SpeakDirective`
- [ ] Implement deterministic TutorIntent selection in new endpoint
- [ ] Add per-turn structured logging

### Files to Create/Modify

```
idna-tutor-mvp/
├── models/
│   └── live_models.py      # NEW: Pydantic models
├── routes/
│   └── live_api.py         # NEW: /api/live/tutor_turn
└── web_server.py           # MODIFY: include live router
```

### Code: live_models.py

```python
from pydantic import BaseModel
from typing import Optional, List, Literal
from enum import Enum


class LiveEvent(str, Enum):
    START_SESSION = "START_SESSION"
    REQUEST_CHAPTER = "REQUEST_CHAPTER"
    REQUEST_QUESTION = "REQUEST_QUESTION"
    SUBMIT_ANSWER = "SUBMIT_ANSWER"
    INTERRUPT = "INTERRUPT"
    REPEAT = "REPEAT"
    END_SESSION = "END_SESSION"


class Telemetry(BaseModel):
    rtt_ms: Optional[int] = None
    packet_loss_pct: Optional[float] = None
    mode: Literal["LIVE", "TTS", "TEXT"] = "LIVE"


class LiveTurnRequest(BaseModel):
    session_id: str
    event: LiveEvent
    client_ts_ms: int
    chapter_id: Optional[str] = None
    question_id: Optional[str] = None
    student_utterance: Optional[str] = None
    asr_confidence: Optional[float] = None
    language: Literal["en", "hi", "hinglish"] = "en"
    telemetry: Optional[Telemetry] = None


class VoicePlan(BaseModel):
    max_sentences: int = 2
    required: List[str] = []
    forbidden: List[str] = []


class SpeakDirective(BaseModel):
    text: str
    ssml: Optional[str] = None


class NextAction(BaseModel):
    type: Literal["WAIT_STUDENT", "AUTO_CONTINUE", "END_SESSION"]


class LiveTurnResponse(BaseModel):
    session_id: str
    question_id: Optional[str] = None
    state: str
    attempt_no: int = 0
    is_correct: Optional[bool] = None
    tutor_intent: str
    language: str = "en"
    voice_plan: VoicePlan
    speak: SpeakDirective
    next_action: NextAction
```

### Done Criteria

✅ Can POST a mocked `SUBMIT_ANSWER` to `/api/live/tutor_turn`
✅ Receive valid `LiveTurnResponse` with `speak.ssml`
✅ Logs show: `session_id`, `question_id`, `attempt_no`, `intent`, `is_correct`

---

## Day 2: Browser + WebSocket Prototype

### Tasks

- [ ] Add `LIVE_MODE` toggle in UI (default: OFF)
- [ ] Implement WebSocket connection to Gemini Live
- [ ] Create UI states: `Listening` / `Thinking` / `Speaking`
- [ ] Stream microphone audio to Gemini Live
- [ ] Receive streaming audio and play in browser

### Files to Create/Modify

```
idna-tutor-mvp/
└── web/
    ├── index.html          # MODIFY: add live mode toggle
    └── js/
        └── gemini_live.js  # NEW: WebSocket + audio handling
```

### Code: gemini_live.js (Core Structure)

```javascript
class GeminiLiveClient {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.ws = null;
        this.audioContext = null;
        this.mediaRecorder = null;
        this.state = 'IDLE'; // IDLE, LISTENING, THINKING, SPEAKING
    }

    async connect() {
        const uri = `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key=${this.apiKey}`;
        
        this.ws = new WebSocket(uri);
        
        this.ws.onopen = () => {
            console.log('Gemini Live connected');
            this.sendSetup();
        };
        
        this.ws.onmessage = (event) => {
            this.handleMessage(JSON.parse(event.data));
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.fallbackToTTS();
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket closed');
        };
    }

    sendSetup() {
        const setup = {
            setup: {
                model: "models/gemini-2.5-flash-native-audio-preview",
                generation_config: {
                    response_modalities: ["AUDIO"],
                    speech_config: {
                        voice_config: {
                            prebuilt_voice_config: {
                                voice_name: "Aoede" // Warm female voice
                            }
                        }
                    }
                },
                system_instruction: {
                    parts: [{
                        text: `You are the speaking voice of the IDNA tutoring system.
                        When you receive content to speak, speak it EXACTLY.
                        Do NOT add extra words or commentary.
                        You are the VOICE, not the BRAIN.`
                    }]
                },
                tools: [{ function_declarations: [TUTOR_TURN_FUNCTION] }]
            }
        };
        this.ws.send(JSON.stringify(setup));
    }

    async startListening() {
        this.state = 'LISTENING';
        this.updateUI('🎙️ Listening...');
        
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        // Stream audio to Gemini...
    }

    handleMessage(message) {
        if (message.toolCall) {
            // Gemini wants to call tutor_turn
            this.handleToolCall(message.toolCall);
        } else if (message.serverContent?.modelTurn?.parts) {
            // Audio response from Gemini
            this.playAudio(message.serverContent.modelTurn.parts);
        }
    }

    async handleToolCall(toolCall) {
        this.state = 'THINKING';
        this.updateUI('🤔 Thinking...');
        
        // Call our backend
        const response = await fetch('/api/live/tutor_turn', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(toolCall.functionCall.args)
        });
        
        const result = await response.json();
        
        // Send SSML back to Gemini to speak
        this.ws.send(JSON.stringify({
            toolResponse: {
                functionResponses: [{
                    id: toolCall.functionCall.id,
                    response: { speak: result.speak.ssml }
                }]
            }
        }));
        
        this.state = 'SPEAKING';
        this.updateUI('🔊 Speaking...');
    }

    fallbackToTTS() {
        console.log('Falling back to Google TTS');
        // Use existing TTS implementation
    }

    updateUI(status) {
        document.getElementById('voice-status').textContent = status;
    }
}
```

### Done Criteria

✅ Voice-to-voice roundtrip works on static prompt
✅ UI shows correct state (Listening → Thinking → Speaking)
✅ Audio plays in browser from Gemini response

---

## Day 3: Function Calling Bridge

### Tasks

- [ ] Register `tutor_turn` tool in Live session
- [ ] On student speech finalization, Gemini calls `tutor_turn`
- [ ] Backend returns `speak.ssml`
- [ ] Gemini speaks ONLY that SSML/text

### Integration Flow

```
Student speaks "five by seven"
        ↓
Gemini ASR transcribes
        ↓
Gemini calls tutor_turn({
    session_id: "...",
    event: "SUBMIT_ANSWER",
    student_utterance: "five by seven"
})
        ↓
Backend evaluates → is_correct: false, attempt: 1
        ↓
Backend returns speak.ssml with GUIDE_THINKING
        ↓
Gemini speaks the SSML exactly
        ↓
Student hears warm hint, not "Wrong!"
```

### Done Criteria

✅ Student says something → backend decides intent → Gemini speaks
✅ Response has tutor tone and pauses (SSML working)
✅ Backend logs show correct intent determination

---

## Day 4: Barge-in + Interruption

### Tasks

- [ ] Implement `INTERRUPT` event handling
- [ ] Gemini stops audio output immediately when student speaks
- [ ] Send `INTERRUPT` to backend for telemetry
- [ ] Resume at correct FSM state

### Code: Interrupt Handling

```javascript
// In gemini_live.js
handleStudentStartedSpeaking() {
    if (this.state === 'SPEAKING') {
        // Stop current audio playback
        this.stopAudioPlayback();
        
        // Notify Gemini to stop
        this.ws.send(JSON.stringify({
            clientContent: {
                turnComplete: false,
                interrupted: true
            }
        }));
        
        // Log interrupt to backend
        fetch('/api/live/tutor_turn', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: this.sessionId,
                event: 'INTERRUPT',
                client_ts_ms: Date.now()
            })
        });
        
        this.state = 'LISTENING';
    }
}
```

### Done Criteria

✅ Student can cut tutor mid-sentence
✅ Session continues without breaking
✅ FSM state remains consistent after interrupt

---

## Day 5: 3-Tier Fallback + Resilience

### Tasks

- [ ] Detect WebSocket failure / high RTT
- [ ] Implement auto-fallback: LIVE → TTS → TEXT
- [ ] Maintain session continuity across modes
- [ ] Never show "network error" to child

### Fallback Logic

```javascript
class FallbackManager {
    constructor() {
        this.mode = 'LIVE';
        this.rttThreshold = 500; // ms
        this.failureCount = 0;
    }

    checkHealth(rtt, packetLoss) {
        if (rtt > this.rttThreshold || packetLoss > 0.1) {
            this.failureCount++;
        } else {
            this.failureCount = Math.max(0, this.failureCount - 1);
        }
        
        if (this.failureCount > 3) {
            this.downgrade();
        }
    }

    downgrade() {
        if (this.mode === 'LIVE') {
            this.mode = 'TTS';
            console.log('Downgrading to TTS mode');
        } else if (this.mode === 'TTS') {
            this.mode = 'TEXT';
            console.log('Downgrading to TEXT mode');
        }
        // Seamlessly continue session
    }

    upgrade() {
        // Try to upgrade when conditions improve
        if (this.mode === 'TEXT' && this.failureCount === 0) {
            this.mode = 'TTS';
        } else if (this.mode === 'TTS' && this.failureCount === 0) {
            this.mode = 'LIVE';
        }
    }
}
```

### Done Criteria

✅ Kill WebSocket mid-session → app continues with TTS
✅ No error message shown to student
✅ Session state preserved across mode changes

---

## Day 6: "Tutor Feel" Tuning

### Tasks

- [ ] Add per-intent SSML templates
- [ ] Implement pacing rules:
  - 700-900ms pause after questions
  - Step cadence in EXPLAIN_ONCE
- [ ] Add micro-praise rules:
  - After each correct micro-step
  - Not only final answer

### SSML Generator

```python
# ssml_generator.py

SSML_TEMPLATES = {
    "GUIDE_THINKING": {
        "en": '<speak>Hmm,<break time="300ms"/> {encouragement}<break time="200ms"/> {concept_pointer}<break time="450ms"/> {guiding_question}</speak>',
        "hi": '<speak>Hmm beta,<break time="300ms"/> {encouragement}<break time="200ms"/> {concept_pointer}<break time="450ms"/> {guiding_question}</speak>',
        "hinglish": '<speak>Hmm beta,<break time="300ms"/> {encouragement}<break time="200ms"/> {concept_pointer}<break time="450ms"/> {guiding_question}</speak>'
    },
    "EXPLAIN_ONCE": {
        "hinglish": '<speak>Koi baat nahi beta, main samjhata hoon.<break time="400ms"/> {step1}<break time="500ms"/> {step2}<break time="500ms"/> {step3}<break time="400ms"/> Samajh aaya?</speak>'
    },
    # ... other intents
}

def generate_tutor_ssml(
    intent: str,
    language: str,
    canonical: dict
) -> str:
    template = SSML_TEMPLATES.get(intent, {}).get(language, SSML_TEMPLATES[intent]["en"])
    
    return template.format(
        encouragement=get_micro_praise(language),
        concept_pointer=canonical.get("hint_1", ""),
        guiding_question=generate_guiding_question(canonical),
        step1=canonical.get("solution_steps", [""])[0],
        step2=canonical.get("solution_steps", ["", ""])[1] if len(canonical.get("solution_steps", [])) > 1 else "",
        step3=canonical.get("solution_steps", ["", "", ""])[2] if len(canonical.get("solution_steps", [])) > 2 else "",
    )
```

### Done Criteria

✅ A/B test: current vs live+ssml on 5 questions
✅ Subjective improvement obvious
✅ Pauses feel natural, not robotic

---

## Day 7: Demo Hardening + Investor Narrative

### Tasks

- [ ] Update `/health` with mode, ws_ok, db_ok
- [ ] Create "Demo Script" path with curated questions
- [ ] Create "Architecture slide" showing Brain vs Voice
- [ ] Add cost guardrails:
  - Max live minutes per session
  - Kill-switch env var

### Health Endpoint Update

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if os.path.exists(DB_PATH) else "initializing",
        "tutor_intent": "enabled",
        "voice_mode": {
            "live_available": check_gemini_live_status(),
            "tts_available": check_google_tts_status(),
            "current_mode": get_default_mode()
        },
        "cost_guardrails": {
            "max_live_minutes": int(os.getenv("MAX_LIVE_MINUTES", 10)),
            "live_enabled": os.getenv("ENABLE_LIVE_VOICE", "true") == "true"
        }
    }
```

### Demo Script Questions

```python
DEMO_QUESTIONS = [
    {
        "id": "demo_1",
        "text": "What is 1/2 + 1/4?",
        "answer": "3/4",
        "hint_1": "Find a common denominator.",
        "hint_2": "Convert 1/2 to fourths.",
        "solution_steps": [
            "1/2 equals 2/4",
            "2/4 plus 1/4 equals 3/4"
        ],
        "why_demo": "Simple fraction addition, shows step-by-step well"
    },
    # ... more demo questions that showcase the step-by-step flow
]
```

### Done Criteria

✅ One-click demo that survives bad network
✅ Shows "Gemini Live but controlled" narrative
✅ Cost guardrails prevent runaway spending
✅ Architecture slide ready for investor pitch

---

## Post-Week: Monitoring & Iteration

### Metrics to Track

| Metric | Target | Alert If |
|--------|--------|----------|
| Live mode success rate | >95% | <90% |
| Avg response latency | <500ms | >1000ms |
| Fallback triggers/day | <10% | >25% |
| Student completion rate | >80% | <60% |
| Cost per session | <$0.30 | >$0.50 |

### Next Priorities

1. Hindi language support (Week 2)
2. More subjects via SubjectPack (Week 3)
3. Parent dashboard with voice reports (Week 4)

---

## Environment Variables

```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
OPENAI_API_KEY=your_openai_key_for_whisper_fallback

# Voice Mode Control
ENABLE_LIVE_VOICE=true
MAX_LIVE_MINUTES=10
DEFAULT_VOICE_MODE=LIVE  # LIVE, TTS, or TEXT

# Fallback Thresholds
LIVE_RTT_THRESHOLD_MS=500
LIVE_PACKET_LOSS_THRESHOLD=0.1
```

---

## Git Commit Strategy

```bash
# Day 1
git commit -m "Add /api/live/tutor_turn endpoint with Pydantic models"

# Day 2
git commit -m "Add Gemini Live WebSocket client (prototype)"

# Day 3
git commit -m "Integrate function calling: Gemini → backend → voice"

# Day 4
git commit -m "Implement barge-in and interrupt handling"

# Day 5
git commit -m "Add 3-tier fallback: LIVE → TTS → TEXT"

# Day 6
git commit -m "Add SSML templates for tutor warmth"

# Day 7
git commit -m "Demo hardening + cost guardrails"
```

---

*This checklist ensures systematic implementation with clear done criteria at each stage.*
