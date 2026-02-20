# IDNA EdTech - Complete Project Specification
## Version 1.0 | Date: January 2025

---

# SECTION 1: PROJECT OVERVIEW

## 1.1 Vision
AI-powered voice-based tutor for K-12 students in India, starting with Class 8 Mathematics.

## 1.2 Target Users
- **Primary**: Class 8 students in Tier 2/3 cities, India
- **Secondary**: Parents (progress tracking)
- **Language**: English-first (Hindi support later)

## 1.3 Key Differentiators
- Voice-based interaction (speak, don't type)
- FSM-controlled logic (reliable, predictable)
- GPT for natural language only (not decision making)
- Multilingual support (future)
- Parent voice reports (future)

---

# SECTION 2: MVP SCOPE (Locked)

## 2.1 Subject Coverage
| Subject | Chapters | Questions |
|---------|----------|-----------|
| Mathematics | 5 | 50 |

## 2.2 Chapters (Class 8 NCERT)
1. Linear Equations in One Variable
2. Rational Numbers
3. Algebraic Expressions and Identities
4. Mensuration
5. Data Handling

## 2.3 Features - MVP
| Feature | Priority | Status |
|---------|----------|--------|
| Text-based Q&A | P0 | ✅ DONE |
| Question bank (50 questions) | P0 | ✅ DONE |
| 3-attempt hint system | P0 | ✅ DONE |
| AI-generated encouragement | P0 | ✅ DONE |
| Chapter selection | P0 | ✅ DONE |
| Voice input (Sarvam Saarika) | P0 | ✅ DONE |
| Voice output (TTS) | P0 | ⏳ PENDING |
| Web interface | P1 | ⏳ PENDING |
| Parent dashboard | P2 | ⏳ PENDING |

## 2.4 Features - NOT in MVP
- Handwriting evaluation
- Multiple languages
- Adaptive difficulty
- Gamification
- Mobile app
- Offline mode

---

# SECTION 3: TECHNICAL ARCHITECTURE

## 3.1 Core Principle
**FSM-First Architecture**
- FSM (Finite State Machine) controls ALL conversation flow
- GPT generates text only, never makes decisions
- Deterministic, testable, reliable

## 3.2 Component Stack
```
┌─────────────────────────────────────────────────┐
│                   FRONTEND                      │
│         (Web Interface - HTML/JS)               │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────┐
│                   BACKEND                        │
│              (Python/FastAPI)                    │
├─────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │   Sarvam    │  │     FSM     │  │ Sarvam  │ │
│  │  Saarika    │  │   (Logic)   │  │ Bulbul  │ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
├─────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐              │
│  │  Question   │  │   OpenAI    │              │
│  │    Bank     │  │  GPT-4o-mini│              │
│  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────┘
```

## 3.3 FSM States
```
GREETING
    ↓
SELECT_CHAPTER
    ↓
ASK_QUESTION
    ↓
WAIT_ANSWER
    ↓
EVALUATE
    ↓ (correct)      ↓ (wrong, attempts < 3)
QUESTION_COMPLETE   GIVE_HINT
    ↓                   ↓
    ↓               WAIT_ANSWER
    ↓                   
    ↓ (wrong, attempts = 3)
    ↓               
SHOW_SOLUTION
    ↓
QUESTION_COMPLETE
    ↓
[Loop to ASK_QUESTION or SESSION_SUMMARY]
    ↓
END
```

## 3.4 Data Flow
```
Student speaks → Sarvam Saarika (STT) → Text
    ↓
Text → FSM (decides action)
    ↓
FSM → GPT (generates response text)
    ↓
Response → TTS → Audio
    ↓
Audio → Student hears
```

## 3.5 APIs Used
| Service | Purpose | Model/Version |
|---------|---------|---------------|
| OpenAI | Text generation | gpt-4.1-mini |
| Sarvam | Speech-to-text | Saarika v2.5 |
| Sarvam | Text-to-speech | Bulbul v3 |

## 3.6 Future Considerations (Post-MVP)
- Sarvam AI for Indic languages (Saarika ASR, Bulbul TTS)
- IndiaAI GPU credits for self-hosting
- Memory-R1 style RL memory for personalization

---

# SECTION 4: FILE STRUCTURE

```
idna/
├── .env                    # API keys (not in git)
├── .env.template           # Template for .env
├── requirements.txt        # Python dependencies
├── questions.py            # Question bank (50 questions)
├── tutor.py               # Main tutor application
├── fsm.py                 # Finite State Machine (to integrate)
├── voice_input.py         # Sarvam Saarika STT integration
├── voice_output.py        # TTS integration (to build)
├── web/                   # Web interface (to build)
│   ├── index.html
│   ├── style.css
│   └── app.js
└── tests/                 # Test files
    └── test_questions.py
```

---

# SECTION 5: QUESTION BANK STRUCTURE

## 5.1 Question Format
```python
{
    "id": "le_001",           # Unique identifier
    "text": "Solve for x...", # Question text
    "answer": "7",            # Correct answer
    "hint1": "First hint",    # Gentle nudge
    "hint2": "Stronger hint", # More help
    "solution": "Step by step" # Full solution
}
```

## 5.2 Answer Checking
- Handles variations: "7", "x=7", "x = 7"
- Handles fractions: "2/3" = "4/6"
- Case insensitive
- Strips whitespace and units

---

# SECTION 6: SESSION FLOW

## 6.1 Tutor Behavior
1. Welcome student
2. Let student choose chapter (or random)
3. Ask question
4. Wait for answer
5. If correct: Praise, next question
6. If wrong (attempt 1-2): Give hint, try again
7. If wrong (attempt 3): Show solution, encourage
8. After 5 questions: Ask to continue or end
9. Show session summary

## 6.2 Commands
- `quit` - End session
- `change` - Switch chapter

---

# SECTION 7: COST ESTIMATES

## 7.1 API Costs (GPT-4o-mini)
| Usage | Cost |
|-------|------|
| Per session (5 questions) | ~₹0.50 |
| 100 sessions/month | ~₹50 |
| 1000 sessions/month | ~₹500 |

## 7.2 Infrastructure (MVP)
| Service | Cost |
|---------|------|
| Railway (hosting) | $5-20/month |
| Domain | ₹500-1000/year |
| Total MVP monthly | ~₹2,000-3,000 |

---

# SECTION 8: TIMELINE

## 8.1 6-Week MVP Plan
| Week | Focus | Deliverable |
|------|-------|-------------|
| 1 | Core + Questions | ✅ DONE - Working text tutor |
| 2 | Voice Input | Sarvam Saarika integration |
| 3 | Voice Output | TTS integration |
| 4 | Web Interface | Browser-based tutor |
| 5 | Parent View | Basic progress dashboard |
| 6 | Polish + Demo | Investor-ready demo |

## 8.2 Current Status
- Week 1: ✅ COMPLETE
- Week 2: 🔄 IN PROGRESS

---

# SECTION 9: DEVELOPMENT SETUP

## 9.1 Prerequisites
- Python 3.11+
- OpenAI API key
- pip

## 9.2 Installation
```bash
cd idna
pip install -r requirements.txt
copy .env.template .env
# Edit .env and add your API key
python tutor.py
```

---

# SECTION 10: FUTURE ROADMAP (Post-MVP)

## 10.1 Phase 2: Pilot (Month 2-3)
- Add Science chapter
- Add English chapter
- Basic parent login
- 50 pilot students

## 10.2 Phase 3: Scale (Month 4-6)
- Sarvam AI integration (Hindi)
- Mobile-friendly web
- Full parent dashboard
- School partnerships (B2B)

## 10.3 Phase 4: Product (Month 6+)
- Dedicated mobile app
- Offline support
- Handwriting evaluation
- Adaptive learning

---

# SECTION 11: BHU PLATFORM (PARKED)

## 11.1 Concept Summary
- Collective consciousness/meditation platform
- Fire ceremony as focal point
- Not religious - universal
- Digital temple without calling it temple
- For: money, health, relationships, peace

## 11.2 Key Decisions Made
- Use flame (not just stone) as focal point - universal symbol
- Not VR - mobile/web based
- You perform fire ritual, participants join digitally
- Seva-based revenue model
- Target validation: 21-day WhatsApp pilot

## 11.3 Status
- **PARKED** - Return after IDNA MVP ships
- Full documentation preserved in this conversation

---

# SECTION 12: KEY CONTACTS & RESOURCES

## 12.1 APIs
- OpenAI: https://platform.openai.com
- Sarvam AI: https://sarvam.ai (future)
- IndiaAI: https://indiaai.gov.in (future)

## 12.2 Documentation
- Sarvam AI: https://docs.sarvam.ai
- Sarvam Saarika STT: https://docs.sarvam.ai/api-reference-docs/speech-to-text
- Sarvam Bulbul TTS: https://docs.sarvam.ai/api-reference-docs/text-to-speech

---

# SECTION 13: REVISION HISTORY

| Date | Version | Changes |
|------|---------|---------|
| Jan 2025 | 1.0 | Initial specification |

---

**END OF SPECIFICATION**
