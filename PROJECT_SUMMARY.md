# IDNA EdTech - Project Summary
## Voice-Enabled AI Math Tutor for Class 8 Students

---

# EXECUTIVE SUMMARY

**What we built:** A fully functional voice-enabled AI tutor for Class 8 Mathematics that runs in a web browser.

**Built in:** 1 day (single session)

**Developer:** Solo (Hemant Ghosh)

**Tech Stack:** Python, OpenAI GPT-4.1-mini, Sarvam Saarika STT, Sarvam Bulbul TTS, FastAPI, HTML/CSS/JS

---

# PRODUCT FEATURES (ALL WORKING)

## Core Tutoring
- ✅ 50 questions across 5 NCERT chapters
- ✅ 3-attempt hint system (progressive hints)
- ✅ AI-generated encouragement and praise
- ✅ Score tracking and session summary
- ✅ Chapter selection

## Voice Capabilities
- ✅ Voice Input: Student speaks answers (Sarvam Saarika)
- ✅ Voice Output: Tutor speaks questions and feedback (OpenAI TTS)
- ✅ Auto-submit after voice input
- ✅ Natural language understanding ("x equals 7", "the answer is seven")

## User Interface
- ✅ Beautiful web interface (browser-based)
- ✅ Mobile-responsive design
- ✅ Real-time score display
- ✅ Visual feedback (correct/incorrect/hints)

---

# TECHNICAL ARCHITECTURE

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND                            │
│              (HTML/CSS/JavaScript)                      │
│         - Web Audio API for recording                   │
│         - Fetch API for backend calls                   │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP/REST
┌─────────────────────▼───────────────────────────────────┐
│                     BACKEND                             │
│                (Python + FastAPI)                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │  Sarvam    │  │  Question   │  │   Sarvam        │ │
│  │  Saarika   │  │    Bank     │  │   Bulbul        │ │
│  │             │  │  50 items   │  │                 │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Answer    │  │   Session   │  │    OpenAI       │ │
│  │  Evaluator  │  │   Manager   │  │   GPT-4o-mini   │ │
│  │             │  │             │  │                 │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

# FILE STRUCTURE

```
idna/
├── .env                    # API keys (protected)
├── requirements.txt        # Python dependencies
├── questions.py            # Question bank (50 questions, 5 chapters)
├── tutor.py               # Text-based tutor (terminal)
├── voice_tutor.py         # Voice-enabled tutor (terminal)
├── voice_input.py         # Sarvam Saarika STT module
├── voice_output.py        # TTS module
├── web_server.py          # FastAPI backend
├── web/
│   └── index.html         # Web interface
└── SPECIFICATION.md       # Full project specification
```

---

# CHAPTERS COVERED (NCERT Class 8)

| Chapter | Questions | Topics |
|---------|-----------|--------|
| Linear Equations | 10 | Single variable, brackets, both sides |
| Rational Numbers | 10 | Add, subtract, multiply, divide fractions |
| Algebraic Expressions | 10 | Simplify, expand, evaluate |
| Mensuration | 10 | Area, perimeter, volume |
| Data Handling | 10 | Mean, median, mode, range |

---

# API ENDPOINTS

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve web interface |
| `/api/session/start` | POST | Start new tutoring session |
| `/api/session/select-chapter` | POST | Select chapter to practice |
| `/api/session/{id}/question` | GET | Get next question |
| `/api/session/answer` | POST | Submit answer, get feedback |
| `/api/session/{id}/summary` | GET | Get session summary |
| `/api/speech/transcribe` | POST | Convert speech to text |
| `/api/speech/synthesize` | POST | Convert text to speech |

---

# ANSWER EVALUATION LOGIC

The system handles various spoken answer formats:

```python
# All these are recognized as correct for answer "7":
"7"                  → ✓
"x = 7"              → ✓
"x is equal to 7"    → ✓
"the answer is 7"    → ✓
"seven"              → ✓
"it's 7"             → ✓
"I think 7"          → ✓
```

---

# SESSION FLOW

```
1. Student opens web browser → http://localhost:8000
                    ↓
2. Welcome message (spoken by AI)
                    ↓
3. Select chapter (1-5 or Random)
                    ↓
4. Question displayed + spoken
                    ↓
5. Student answers (voice or type)
                    ↓
6. If CORRECT → Praise + Next Question
   If WRONG (attempt 1-2) → Hint + Try Again
   If WRONG (attempt 3) → Show Solution + Next Question
                    ↓
7. After 5+ questions → Option to continue or end
                    ↓
8. Session Summary (score, accuracy, encouragement)
```

---

# COST ANALYSIS

## Development Cost
- Time: 1 day (8 hours)
- Developer: Solo
- External services: OpenAI API only

## Operational Cost (OpenAI API)
| Usage | Cost |
|-------|------|
| Per tutoring session (5 questions) | ~₹0.50 |
| 100 sessions/month | ~₹50 |
| 1,000 sessions/month | ~₹500 |
| 10,000 sessions/month | ~₹5,000 |

---

# WHAT'S NOT YET BUILT (Future Roadmap)

| Feature | Priority | Estimated Time |
|---------|----------|----------------|
| Parent Dashboard | High | 2-3 hours |
| More questions (100+) | Medium | 2 hours |
| Hindi language support | High | 1 week |
| Mobile app | Medium | 2-3 weeks |
| User authentication | Medium | 1 day |
| Progress persistence (database) | Medium | 1 day |
| Adaptive difficulty | Low | 1 week |
| Handwriting recognition | Low | 2 weeks |

---

# HOW TO RUN

## Prerequisites
- Python 3.11
- OpenAI API key

## Installation
```bash
cd idna
pip install -r requirements.txt
# Create .env file with: OPENAI_API_KEY=your_key_here
```

## Run Web Tutor
```bash
py -3.11 web_server.py
# Open browser: http://localhost:8000
```

## Run Terminal Tutor (with voice)
```bash
py -3.11 voice_tutor.py
```

## Run Terminal Tutor (text only)
```bash
py -3.11 tutor.py
```

---

# KEY DESIGN DECISIONS

## 1. FSM-First Architecture
- Finite State Machine controls all conversation flow
- GPT only generates natural language text
- Ensures predictable, testable behavior

## 2. Voice as Primary Input
- Designed for students who may struggle with typing
- Natural for younger students
- Handles spoken number variations

## 3. Progressive Hints
- 3 attempts per question
- Hints get more specific each time
- Full solution shown after 3 wrong attempts
- Encouragement, never criticism

## 4. Web-First Interface
- No app installation needed
- Works on any device with browser
- Easy to demo to investors

---

# VALIDATION COMPLETED

| Test | Result |
|------|--------|
| API connection | ✅ Working |
| Question loading | ✅ Working |
| Answer evaluation | ✅ Working |
| Hint system | ✅ Working |
| Voice input (Sarvam Saarika) | ✅ Working |
| Voice output (TTS) | ✅ Working |
| Web interface | ✅ Working |
| Auto-submit on voice | ✅ Working |
| Session summary | ✅ Working |

---

# DEMO SCRIPT (For Investors)

1. **Open browser** → Show professional UI
2. **Select chapter** → "Let's try Linear Equations"
3. **Answer correctly** → Show praise and score update
4. **Answer wrong** → Show hint system (don't give answer immediately)
5. **Use voice** → "Watch, the student just speaks the answer"
6. **Complete 5 questions** → Show session summary
7. **Explain scale** → "Same architecture works for Science, English, Hindi medium"

---

# CONTACT

**Founder:** Hemant Ghosh
**Project:** IDNA EdTech
**Target:** Class 8 students in Tier 2/3 cities, India
**Goal:** Make quality tutoring accessible through AI + Voice

---

# APPENDIX: Sample Question Format

```python
{
    "id": "le_001",
    "text": "Solve for x: x + 5 = 12",
    "answer": "7",
    "hint1": "Subtract 5 from both sides.",
    "hint2": "x = 12 - 5",
    "solution": "x + 5 = 12\nx = 12 - 5\nx = 7"
}
```

---

**END OF DOCUMENT**
