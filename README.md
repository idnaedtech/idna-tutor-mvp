# IDNA Didi v7.0 — AI Voice Tutor

**Class 8 NCERT Math tutor. Voice-first. Hinglish. Runs on any smartphone.**

## Quick Start (Local)

### 1. Prerequisites
- Python 3.11+
- Docker (for Postgres) OR just use SQLite for quick testing
- API keys: OpenAI, Groq, Sarvam

### 2. Setup
```bash
cd idna-tutor-v7

# Copy env template and fill in your API keys
cp .env.example .env
# Edit .env with your actual keys

# Install Python deps
pip install -r requirements.txt

# Run (SQLite mode — no Docker needed for testing)
uvicorn app.main:app --reload --port 8000
```

### 3. Open in browser
- Login: http://localhost:8000
- Student: http://localhost:8000/student (after login)
- Parent: http://localhost:8000/parent (after login)

### 4. Create test student
```bash
# Open Python shell
python -c "
from app.database import SessionLocal, init_db
from app.models import Student, Parent
init_db()
db = SessionLocal()

# Create student
s = Student(name='Nandini', pin='1234', class_level=8, preferred_language='hi-IN')
db.add(s)
db.commit()
db.refresh(s)

# Create parent
p = Parent(student_id=s.id, name='Hemant', pin='5678', language='te-IN')
db.add(p)
db.commit()

print(f'Student PIN: 1234')
print(f'Parent PIN: 5678')
db.close()
"
```

### 5. Test
- Open http://localhost:8000
- Enter PIN: 1234
- Tap mic and say "aaj math padha"
- Didi will start teaching Rational Numbers

## Production (Docker)
```bash
docker-compose up --build
```

## Production (Railway)
```bash
# Push to GitHub, connect to Railway
# Set env vars in Railway dashboard
# Deploy
```

## Architecture

```
Student speaks → Groq Whisper (STT) → Input Classifier → State Machine
→ Answer Checker → Instruction Builder → GPT-4o → Enforcer → Clean for TTS
→ Sarvam Bulbul v3 (TTS) → Student hears Didi
```

## File Structure

```
app/
├── config.py              # All env vars, constants
├── database.py            # SQLAlchemy engine, sessions
├── models.py              # ORM: Students, Parents, Sessions, Questions, Skills
├── main.py                # FastAPI app, startup, seed data
├── routers/
│   ├── auth.py            # PIN login, JWT, rate limiting
│   └── student.py         # THE MAIN LOOP: STT→classify→FSM→LLM→enforce→TTS
├── tutor/
│   ├── state_machine.py   # 14 states, deterministic transitions
│   ├── input_classifier.py # Hindi/English/Hinglish intent detection
│   ├── answer_checker.py  # Deterministic math checking, no LLM
│   ├── instruction_builder.py # Didi's personality, prompt templates
│   ├── enforcer.py        # 7 rules: word limit, no false praise, etc.
│   ├── llm.py             # OpenAI abstraction (swappable)
│   └── memory.py          # Skill mastery read/write, adaptive questions
├── voice/
│   ├── stt.py             # Groq Whisper / Sarvam Saarika / Saaras
│   ├── tts.py             # Sarvam Bulbul v3, caching
│   └── clean_for_tts.py   # Symbol→word conversion for TTS
├── content/
│   └── seed_questions.py  # 25 questions, Ch1 Rational Numbers
web/
├── login.html             # 4-digit PIN entry
├── student.html           # WhatsApp-style voice chat
└── parent.html            # Dashboard (basic)
tests/
└── test_core.py           # 69 tests for answer checker, classifier, enforcer
```

## Tests
```bash
pytest tests/ -v
```

## API Keys Needed
- **OPENAI_API_KEY**: For GPT-4o (Didi's brain)
- **GROQ_API_KEY**: For Whisper STT (speech recognition)
- **SARVAM_API_KEY**: For Bulbul v3 TTS (Didi's voice)
