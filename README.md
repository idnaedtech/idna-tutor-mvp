# IDNA EdTech - Voice-First AI Math Tutor

Voice-based math tutoring system for CBSE Class 8 students.

## Features

- ✅ **SQLite Persistence** - Sessions survive restart
- ✅ **Explicit FSM** - 6 states with guards
- ✅ **OpenAI TTS** - Natural voice output
- ✅ **CBSE Class 8** - 10 chapters, 100 questions
- ✅ **Parent Dashboard** - Voice-first reports
- ✅ **Evaluator v2** - Handles fractions, words, units

## Quick Deploy to Railway

### Option 1: Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Set environment variable
railway variables set OPENAI_API_KEY=sk-your-key-here

# Deploy
railway up
```

### Option 2: GitHub + Railway

1. Push this folder to a GitHub repo
2. Go to [railway.app](https://railway.app)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repo
5. Add `OPENAI_API_KEY` in Variables tab
6. Deploy!

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for TTS/STT |
| `PORT` | No | Set automatically by Railway |

## Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run server
python web_server.py
```

Open http://localhost:8000

## Project Structure

```
idna-railway/
├── web_server.py      # Main FastAPI app (FSM + API)
├── questions.py       # CBSE Class 8 question bank
├── evaluator.py       # Answer evaluation logic
├── requirements.txt   # Python dependencies
├── Procfile          # Railway/Heroku start command
├── railway.json      # Railway config
├── index.html        # Home page
├── parent.html       # Parent dashboard
└── web/
    └── index.html    # Student learning interface
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chapters` | GET | List available chapters |
| `/api/session/start` | POST | Start new session |
| `/api/session/chapter` | POST | Select chapter |
| `/api/session/question` | POST | Get next question |
| `/api/session/answer` | POST | Submit answer |
| `/api/session/end` | POST | End session |
| `/api/dashboard/{id}` | GET | Get parent dashboard |
| `/api/dashboard/{id}/voice-report` | POST | Generate voice report |
| `/api/text-to-speech` | POST | Convert text to speech |
| `/api/speech-to-text` | POST | Convert speech to text |
| `/health` | GET | Health check |

## FSM States

```
IDLE → CHAPTER_SELECTED → WAITING_ANSWER → SHOWING_HINT → SHOWING_ANSWER → COMPLETED
```

---

Made with ❤️ for Indian Students by IDNA EdTech
