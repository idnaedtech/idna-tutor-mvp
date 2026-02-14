---
name: idna-edtech-tutor
description: >
  IDNA EdTech AI voice tutor development skill. Use this skill whenever the user
  mentions IDNA, Didi tutor, voice tutoring, Learn IDNA, EdTech MVP, NCERT tutoring,
  Hindi-English voice pipeline, Sarvam TTS, Groq Whisper, agentic tutor,
  student session flow, parent voice reports, or any work related to building an
  AI-powered tutor for Indian K-10 students. Also trigger when discussing
  tutor system prompts, teaching flows, input classification, question banks,
  voice pipeline latency, Hinglish code-switching, or any NCERT subject including
  Mathematics, Science, Social Science (History, Geography, Civics, Economics),
  English, Hindi, and Sanskrit. This skill covers all NCERT Class 6-10 subjects
  with math as the current MVP focus and expansion to all subjects planned.
  Activate even for tangentially related requests like debugging FastAPI endpoints,
  improving LLM prompts for education, working with speech-to-text/text-to-speech
  pipelines in Hindi, or building curriculum-aligned content for Indian schools.
metadata:
  author: Hemant Ghosh
  version: 6.2.4
  category: edtech
  stack: python-fastapi-openai-sarvam
---

# IDNA EdTech — Voice Tutor Development Skill

## What is IDNA

IDNA EdTech builds "Didi" (दीदी), an AI-powered Hindi-English voice tutor
for Class 6-10 students in India's Tier 2/3 cities. The tutor speaks Hinglish
naturally, teaches NCERT concepts across ALL subjects with culturally relevant
Indian examples, and guides students through problems step-by-step like a
patient older sister.

**Subject Roadmap:**

| Phase | Subjects | Status |
|-------|----------|--------|
| MVP (Phase 1) | Mathematics (Class 8) | Active development |
| Phase 2 | Science (Physics, Chemistry, Biology) | Planned |
| Phase 3 | Social Science (History, Geography, Civics, Economics) | Planned |
| Phase 4 | English, Hindi, Sanskrit (Language & Literature) | Planned |
| Phase 5 | Classes 6, 7, 9, 10 expansion across all subjects | Planned |

The architecture is **subject-agnostic** — the voice pipeline (STT → LLM → TTS),
session state machine, input classifier, and teaching flow work identically
across subjects. Only the **question bank**, **teaching content**, and
**answer evaluation logic** change per subject.

## Tech Stack (Locked — Do Not Change Without Explicit Approval)

| Layer | Technology | Notes |
|-------|-----------|-------|
| LLM | GPT-4o | Multi-turn reasoning, Hinglish generation |
| STT | Groq Whisper (whisper-large-v3-turbo) | language="hi" forced |
| TTS | Sarvam Bulbul v3 | Speaker: simran, hi-IN, pace 0.90 |
| Backend | FastAPI (Python) | Async endpoints |
| Frontend | HTML/JS (single page) | Web-based voice interface |
| Database | SQLite | Session logs, student profiles |
| Hosting | Railway | Current deployment |
| Repo | github.com/idnaedtech/idna-tutor-mvp | main branch |

**Future stack (Phase 2-3, NOT for MVP):**
NVIDIA PersonaPlex 7B, Ollama/LocalAI, Asynq task queue, Milvus vector DB,
RuleGo FSM, Gorse adaptive questions, gosseract handwriting OCR,
Smol2Operator GUI agent, checkpoint-engine model updates, Memory-R1 RL memory.

## Codebase Structure

```
idna-tutor-mvp/
├── server.py              # FastAPI app, all endpoints
├── agentic_tutor.py       # Session state machine, teaching flow
├── didi_voice.py          # DIDI_PROMPT, instruction builders
├── input_classifier.py    # Classifies student input (ACK/IDK/ANSWER/etc.)
├── tutor_states.py        # State definitions and transitions
├── questions.py           # Question bank + SKILL_LESSONS
├── voice_input.py         # Whisper STT module
├── voice_output.py        # TTS module (Sarvam)
├── web/
│   └── index.html         # Student-facing web UI
├── static/
│   └── student_new.html   # Alternate UI
└── tests/
    ├── test_answer_checker.py
    ├── test_input_classifier.py
    ├── test_tutor_states.py
    └── test_regression_live.py
```

## Current Version: v6.2.4

### What's Working (DO NOT BREAK)
- Teaching flow: greet → teach concept with Indian example → "Samajh aaya?" → student ACK → read question
- Hinglish tone: natural older-sister voice, "aap" form, warm but focused
- Sarvam Bulbul v3 TTS: single voice (simran), hi-IN locked, no fallback, single API call (no chunking)
- Session state machine: GREETING → TEACHING → WAITING_ANSWER → EVALUATING
- Progressive hints: first wrong → hint, second wrong → full solution
- `clean_for_tts()`: converts fractions/symbols to speakable text
- Groq Whisper STT with `language="hi"` forced
- Full response playback (TTS cutoff fixed in v6.2.4)

### Known Bugs (Still Active)
1. **Repetition loop**: Sub-steps re-asked after student answers correctly
2. **False praise**: "Bahut accha!" said when student gave no answer or wrong answer
3. **Transcription quality**: Whisper still garbles Hindi-English mixed speech and background noise
4. **Language preference**: Student asks for English but Didi reverts to Hinglish next turn
5. **Answer parsing**: Hindi-transliterated math answers ("minus one by seven") not recognized as correct

## Session Flow Architecture

```
Student speaks → Groq Whisper (STT, language="hi")
    → Confidence check (if < 0.4: "Ek baar phir boliye?")
    → Input Classifier (ACK / IDK / ANSWER / CONCEPT_REQUEST / COMFORT / STOP)
    → State Machine (determines action based on current state + input category)
    → Instruction Builder (builds LLM prompt for this specific action)
    → GPT-4o (generates Didi's response)
    → clean_for_tts() (fraction/symbol conversion)
    → Sarvam TTS (single API call, full text)
    → Audio plays in browser
```

## Input Categories

| Category | Examples | Action |
|----------|---------|--------|
| ACK | "haan", "samajh gaya", "हां", "okay" | Advance to next step |
| IDK | "nahi samjha", "पता नहीं", "I don't know" | Reteach with different example |
| ANSWER | Any numeric/mathematical response | Evaluate correctness |
| CONCEPT_REQUEST | "explain karo", "बताइए", "what is this" | Teach concept |
| COMFORT | "you're rude", "बहुत मुश्किल", "I give up" | Comfort, no teaching |
| STOP | "bye", "band karo", "let's stop" | End session gracefully |
| TROLL | Off-topic, jokes | Brief redirect to math |

## Teaching Principles (Embedded in Didi's Personality)

1. **One idea per turn.** Never teach AND ask a question in the same turn.
2. **Show, don't tell.** Math: show equations. Science: show cause-effect. History: show timeline.
3. **Indian examples.** Roti, cricket, Diwali, monsoon, local geography — not abstract or Western examples.
4. **Respectful Hindi.** "Aap" form, "dekhiye", "sochiye". Never "tum" or casual forms.
5. **No false praise.** Never say "Bahut accha!" unless student actually gave correct answer.
6. **Sub-step tracking (math).** Once a step is confirmed correct, NEVER re-ask it.
7. **Comfort first.** If student is frustrated, acknowledge feelings before any teaching.
8. **Subject-appropriate evaluation.** Math: exact answer. Science/SST: key concept coverage. Language: grammar + meaning.

## Key Development Rules

When modifying ANY file in this codebase:

1. **Run tests after every change:**
   ```bash
   python -m pytest tests/ -v
   ```

2. **Never change the TTS voice or add fallbacks.**
   Sarvam simran is the only voice. No OpenAI TTS fallback. One Didi, always.

3. **Never rewrite the full DIDI_PROMPT.**
   Append rules, don't replace. The teaching tone is calibrated and working.

4. **Always force `language="hi"` in Whisper calls.**
   Without this, Hindi speech becomes English garbage.

5. **Keep the state machine simple.**
   States: GREETING → TEACHING → WAITING_ANSWER → EVALUATING → NEXT_QUESTION
   Don't add states without explicit approval.

6. **Commit messages follow this format:**
   `v6.X.Y: brief description of what changed`

7. **Test with actual Hindi voice input** before marking any STT change as done.

## API Endpoints Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve web interface |
| `/api/session/start` | POST | Start tutoring session |
| `/api/session/select-chapter` | POST | Select chapter |
| `/api/session/{id}/question` | GET | Get next question |
| `/api/session/answer` | POST | Submit answer, get feedback |
| `/api/session/{id}/summary` | GET | Session summary |
| `/api/speech/transcribe` | POST | STT (Groq Whisper) |
| `/api/text-to-speech` | POST | TTS (Sarvam Bulbul v3) |
| `/api/text-to-speech/stream` | POST | Streaming TTS (SSE) |

## NCERT Content Scope

### MVP: Mathematics Class 8

**Chapter 1: Rational Numbers (परिमेय संख्याएँ)** — Currently implemented
- Adding/subtracting/multiplying/dividing fractions
- Additive & multiplicative inverse
- Properties (closure, commutative, associative, distributive)
- Number line representation

**Remaining Math Chapters** — To be built
- Ch 2: Linear Equations in One Variable
- Ch 3: Understanding Quadrilaterals
- Ch 4: Data Handling
- Ch 5: Squares and Square Roots
- Ch 6: Cubes and Cube Roots
- Ch 7: Comparing Quantities
- Ch 8: Algebraic Expressions and Identities
- Ch 9: Mensuration
- Ch 10-16: Remaining chapters

### Future Subjects — Architecture Notes

All subjects use the same pipeline. Subject-specific differences:

| Subject | Answer Type | Evaluation Method | Teaching Style |
|---------|------------|-------------------|---------------|
| Math | Numeric/expression | Exact match + equivalence check | Step-by-step solving |
| Science | Conceptual + numeric | Keyword matching + LLM evaluation | Explain → experiment analogy → verify |
| Social Science | Descriptive | LLM semantic evaluation | Story/narrative → key facts → connect |
| English | Text/grammar | LLM evaluation + rule-based grammar | Read → discuss → practice |
| Hindi/Sanskrit | Text/grammar | LLM evaluation | Similar to English, Hindi-medium |

**Key architecture decisions for multi-subject:**
- `questions.py` → split into `questions/{subject}/{chapter}.py`
- `input_classifier.py` → subject-aware (math answers vs descriptive answers)
- `answer_checker.py` → pluggable evaluators per subject type
- `SKILL_LESSONS` → organized by `{subject}_{chapter}_{skill}`
- SubStepTracker → math-only; other subjects use LLM-based evaluation

## Common Tasks & How To Do Them

### Adding a new question to the bank
Edit `questions.py`. Follow existing format:
```python
{
    "id": "rat_add_6",
    "chapter": "ch1_rational_numbers",
    "type": "fraction_add_same_denom",
    "question": "What is -5/9 + 2/9?",
    "answer": "-3/9",
    "simplified_answer": "-1/3",
    "hints": ["Denominator same hai, sirf numerators add karo", "Minus 5 plus 2 kitna hota hai?"],
    "target_skill": "addition_same_denom",
}
```

### Adding a new teaching concept
Edit `questions.py` → `SKILL_LESSONS` dict. Add the skill key and teaching text.
Then add pre-teach text in `agentic_tutor.py` → `start_session()`.

### Debugging voice pipeline issues
1. Check Groq Whisper response: log `result["text"]` and `result["confidence"]`
2. Check Sarvam TTS: log response time and audio length
3. Check `clean_for_tts()`: print before/after to verify fraction conversion
4. Check frontend: browser console for audio playback errors

### Deploying to Railway
```bash
git add -A
git commit -m "v6.X.Y: description"
git push origin main
# Railway auto-deploys from main branch
```

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| No voice output | TTS text too long (>2500 chars) | Check `sarvam_tts()` truncation at 2000 chars |
| Hindi transcribed as English | `language` param missing in Whisper | Force `language="hi"` |
| "Bahut accha!" after wrong answer | LLM ignoring verdict | Check VERDICT tag in instruction |
| Same step re-asked | SubStepTracker not marking done | Check `mark_current_done()` call |
| Student speaks English, Didi replies Hindi | No language preference tracking | Add session-level language pref |
| Hindi math answer not recognized | Answer checker only handles digits | Add transliterated number parsing |
| Session crashes | SQLite lock | Check concurrent session handling |
| Didi speaks English | Sarvam language set wrong | Verify `hi-IN` in TTS payload |

## For Detailed Reference

- `references/teaching-flow.md` — Full state machine diagram and transition rules
- `references/question-bank-format.md` — Question JSON schema and examples
- `references/tts-pipeline.md` — Streaming TTS architecture and latency breakdown
- `references/classifier-phrases.md` — All classifier categories with Hindi/English phrases
