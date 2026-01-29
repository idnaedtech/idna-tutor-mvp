# Gemini Live API - Function Schema
**IDNA EdTech Voice Integration**
**Version:** 1.0
**Date:** January 28, 2026

---

## Overview

Gemini Live handles **ASR + TTS + barge-in**, but the IDNA backend owns **truth** (FSM/Evaluator/TutorIntent).

**Key Principle:** Gemini calls ONE authoritative function per turn: `tutor_turn()`

```
┌─────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────┤
│  Gemini Live = Ears + Larynx (ASR, TTS, barge-in)           │
│  IDNA Backend = Brain (FSM, Evaluator, TutorIntent)         │
│                                                              │
│  Gemini NEVER decides correctness or next steps.            │
│  Gemini ONLY speaks what backend tells it to speak.         │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Function Definition (OpenAPI-style JSON)

Register this tool with Gemini Live session:

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "tutor_turn",
        "description": "Authoritative tutoring turn. Backend decides correctness, attempt, intent, and returns the canonical content + constraints for Gemini to speak.",
        "parameters": {
          "type": "object",
          "required": ["session_id", "event", "client_ts_ms"],
          "properties": {
            "session_id": {
              "type": "string",
              "description": "Unique session identifier"
            },
            "client_ts_ms": {
              "type": "integer",
              "description": "Client timestamp in milliseconds"
            },
            "event": {
              "type": "string",
              "enum": [
                "START_SESSION",
                "REQUEST_CHAPTER",
                "REQUEST_QUESTION",
                "SUBMIT_ANSWER",
                "INTERRUPT",
                "REPEAT",
                "END_SESSION"
              ],
              "description": "Type of event triggering this turn"
            },
            "chapter_id": {
              "type": "string",
              "description": "Chapter identifier (for REQUEST_CHAPTER)"
            },
            "question_id": {
              "type": "string",
              "description": "Current question identifier"
            },
            "student_utterance": {
              "type": "string",
              "description": "Best-effort transcript of student's speech (from Gemini ASR)"
            },
            "asr_confidence": {
              "type": "number",
              "description": "ASR confidence score 0-1"
            },
            "language": {
              "type": "string",
              "enum": ["en", "hi", "hinglish"],
              "description": "Detected or preferred language"
            },
            "telemetry": {
              "type": "object",
              "description": "Network and mode telemetry",
              "properties": {
                "rtt_ms": {
                  "type": "integer",
                  "description": "Round-trip time in milliseconds"
                },
                "packet_loss_pct": {
                  "type": "number",
                  "description": "Packet loss percentage"
                },
                "mode": {
                  "type": "string",
                  "enum": ["LIVE", "TTS", "TEXT"],
                  "description": "Current voice mode"
                }
              }
            }
          }
        }
      }
    }
  ]
}
```

---

## 2. Backend Response Contract

What `tutor_turn()` returns to Gemini:

```json
{
  "session_id": "sess_123",
  "question_id": "q_8_3_12",
  "state": "IN_QUESTION",
  "attempt_no": 2,
  "is_correct": false,

  "tutor_intent": "GUIDE_THINKING",
  "language": "hinglish",

  "voice_plan": {
    "max_sentences": 2,
    "required": ["encouragement", "one_guiding_question"],
    "forbidden": ["say_wrong", "full_solution", "grading_language"]
  },

  "canonical": {
    "question_text": "What is 2/3 + 1/4?",
    "expected_answer": "11/12",
    "hint_1": "Find a common denominator for 3 and 4.",
    "hint_2": "Convert both fractions to denominator 12.",
    "solution_steps": [
      "LCM of 3 and 4 is 12.",
      "2/3 = 8/12 and 1/4 = 3/12.",
      "8/12 + 3/12 = 11/12."
    ]
  },

  "ui": {
    "subtitle": "Hmm beta, pehle common denominator socho. 3 aur 4 ka common denominator kya hoga?",
    "show_steps": ["LCM(3,4)=?"],
    "big_question_text": "2/3 + 1/4 = ?"
  },

  "speak": {
    "text": "Hmm beta, fractions add karne se pehle common denominator chahiye. 3 aur 4 ka common denominator kya hoga?",
    "ssml": "<speak>Hmm beta,<break time='300ms'/> fractions add karne se pehle common denominator chahiye.<break time='400ms'/> 3 aur 4 ka common denominator kya hoga?</speak>"
  },

  "next_action": {
    "type": "WAIT_STUDENT"
  },

  "fallback": {
    "allowed": true,
    "recommended_mode": "LIVE"
  }
}
```

---

## 3. Response Fields Explained

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | string | Session identifier |
| `question_id` | string | Current question ID |
| `state` | string | FSM state: `IDLE`, `IN_QUESTION`, `SHOWING_HINT`, `COMPLETED` |
| `attempt_no` | int | Current attempt (1, 2, or 3) |
| `is_correct` | bool | Whether student's answer was correct |
| `tutor_intent` | string | TutorIntent enum value |
| `language` | string | Response language |

### Voice Plan (Constraints for Gemini)

| Field | Description |
|-------|-------------|
| `max_sentences` | Maximum sentences Gemini may speak |
| `required` | Elements that MUST be included |
| `forbidden` | Elements that MUST NOT be included |

### Speak (What Gemini Says)

| Field | Description |
|-------|-------------|
| `text` | Plain text version |
| `ssml` | SSML with pauses and prosody |

**Rule:** Gemini speaks `speak.ssml` exactly. No improvisation.

### Next Action

| Type | Description |
|------|-------------|
| `WAIT_STUDENT` | Wait for student to speak |
| `AUTO_CONTINUE` | Immediately fetch next question |
| `END_SESSION` | Session complete |

---

## 4. Backend Endpoint

Implement ONE HTTP endpoint that Gemini calls:

```
POST /api/live/tutor_turn
Content-Type: application/json
```

### Internal Routing

This endpoint internally routes to existing logic:

```python
@app.post("/api/live/tutor_turn")
async def live_tutor_turn(request: LiveTurnRequest) -> LiveTurnResponse:
    """
    Single entry point for Gemini Live function calls.
    Routes to existing FSM/Evaluator/TutorIntent logic.
    """
    
    if request.event == "START_SESSION":
        return handle_start_session(request)
    
    elif request.event == "REQUEST_CHAPTER":
        return handle_select_chapter(request)
    
    elif request.event == "REQUEST_QUESTION":
        return handle_get_question(request)
    
    elif request.event == "SUBMIT_ANSWER":
        return handle_submit_answer(request)
    
    elif request.event == "INTERRUPT":
        return handle_interrupt(request)
    
    elif request.event == "REPEAT":
        return handle_repeat(request)
    
    elif request.event == "END_SESSION":
        return handle_end_session(request)
    
    else:
        raise HTTPException(400, f"Unknown event: {request.event}")
```

---

## 5. Safety Rails (Server-Side Enforcement)

### MUST Enforce

1. **Backend sets `tutor_intent`** - Gemini never decides
2. **Backend sets `is_correct`** - Gemini never evaluates
3. **Backend sets `attempt_no`** - Gemini never counts
4. **Backend generates `speak.ssml`** - with sentence limits
5. **Gemini speaks ONLY `speak.ssml`** - no improvisation

### System Prompt for Gemini

```
You are the speaking voice of the IDNA tutoring system.

RULES:
1. When you receive a tutor_turn response, speak EXACTLY the speak.ssml content.
2. Do NOT add extra words, explanations, or commentary.
3. Do NOT decide if an answer is correct or incorrect.
4. Do NOT give hints unless they are in the speak.ssml.
5. Follow the voice_plan constraints strictly.
6. Wait for the student after speaking (next_action).

You are the VOICE, not the BRAIN.
```

---

## 6. Example Flow

### Student says wrong answer (Attempt 1)

**Gemini calls:**
```json
{
  "session_id": "sess_123",
  "event": "SUBMIT_ANSWER",
  "client_ts_ms": 1706450000000,
  "student_utterance": "five by seven",
  "asr_confidence": 0.92,
  "language": "en"
}
```

**Backend returns:**
```json
{
  "session_id": "sess_123",
  "question_id": "q_8_3_12",
  "state": "SHOWING_HINT",
  "attempt_no": 1,
  "is_correct": false,
  "tutor_intent": "GUIDE_THINKING",
  "language": "hinglish",
  "voice_plan": {
    "max_sentences": 2,
    "required": ["encouragement", "one_guiding_question"],
    "forbidden": ["say_wrong", "full_solution"]
  },
  "speak": {
    "ssml": "<speak>Hmm beta,<break time='300ms'/> fractions add karne se pehle common denominator chahiye.<break time='400ms'/> 3 aur 4 ka common denominator kya hoga?</speak>"
  },
  "next_action": { "type": "WAIT_STUDENT" }
}
```

**Gemini speaks:** The SSML exactly, then waits for student.

---

## 7. Why Only One Function?

| Reason | Benefit |
|--------|---------|
| Prevents Gemini from "deciding" flows | Backend stays in control |
| Simplifies observability | One turn = one log record |
| Easier debugging | Single point of truth |
| Consistent behavior | No multi-function state issues |

---

## 8. Pydantic Models (Python)

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


class Canonical(BaseModel):
    question_text: str
    expected_answer: str
    hint_1: Optional[str] = None
    hint_2: Optional[str] = None
    solution_steps: List[str] = []


class UIDirective(BaseModel):
    subtitle: Optional[str] = None
    show_steps: List[str] = []
    big_question_text: Optional[str] = None


class SpeakDirective(BaseModel):
    text: str
    ssml: Optional[str] = None


class NextAction(BaseModel):
    type: Literal["WAIT_STUDENT", "AUTO_CONTINUE", "END_SESSION"]


class Fallback(BaseModel):
    allowed: bool = True
    recommended_mode: Literal["LIVE", "TTS", "TEXT"] = "LIVE"


class LiveTurnResponse(BaseModel):
    session_id: str
    question_id: Optional[str] = None
    state: str
    attempt_no: int = 0
    is_correct: Optional[bool] = None
    tutor_intent: str
    language: str = "en"
    voice_plan: VoicePlan
    canonical: Optional[Canonical] = None
    ui: Optional[UIDirective] = None
    speak: SpeakDirective
    next_action: NextAction
    fallback: Fallback = Fallback()
```

---

*This schema ensures Gemini Live provides natural voice while IDNA backend maintains full control over tutoring logic.*
