# IDNA EdTech - Disaster Recovery Guide

## If Your Laptop Crashes

This guide helps you recover and continue development on a new machine.

---

## 1. What's Already Safe (Cloud)

| Item | Location | Status |
|------|----------|--------|
| Source code | GitHub repo | Auto-backed up on every push |
| Production DB | Railway Postgres | Managed by Railway |
| Environment vars | Railway dashboard | Stored securely |
| Deployment config | Railway | Auto-deploys from main branch |

---

## 2. What You Need to Backup Locally

### API Keys (store in password manager)
```
OPENAI_API_KEY=sk-...
GOOGLE_APPLICATION_CREDENTIALS_JSON={...json...}
```

### Local SQLite DB (optional - dev only)
- File: `idna.db`
- Production uses Postgres on Railway, so this is just for local dev

---

## 3. Recovery Steps on New Machine

### Step 1: Install Prerequisites
```bash
# Install Python 3.11+
# Install Git
# Install VS Code (optional)
```

### Step 2: Clone Repository
```bash
git clone https://github.com/YOUR_USERNAME/idna.git
cd idna
```

### Step 3: Setup Python Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Create .env File
```bash
# Create .env in project root with:
OPENAI_API_KEY=sk-your-key-here
GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}
```

### Step 6: Run Locally
```bash
python web_server.py
# Opens at http://localhost:8000
```

---

## 4. Railway Deployment Recovery

If you need to reconnect Railway:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to existing project
railway link

# Deploy
railway up
```

### Railway Dashboard
- URL: https://railway.app/dashboard
- Check: Variables, Postgres, Logs

---

## 5. Resuming Work with Claude Code

The `CLAUDE.md` file contains full project context. Just tell Claude:

> "Read CLAUDE.md and continue where we left off"

### Key Context in CLAUDE.md:
- Project architecture
- Recent changes and fixes
- Pending tasks
- API endpoints
- Database schema

---

## 6. Quick Backup Commands

### Daily Backup (run before shutting down)
```bash
cd C:\Users\User\Documents\idna
git add -A
git commit -m "Daily backup: $(date +%Y-%m-%d)"
git push origin main
```

### Check What's Not Committed
```bash
git status
```

### See Recent Changes
```bash
git log --oneline -10
```

---

## 7. Files Overview

| File | Purpose | Critical? |
|------|---------|-----------|
| `web_server.py` | Main FastAPI server | Yes |
| `tutor_intent.py` | GPT prompts, tutor persona | Yes |
| `evaluator.py` | Answer checking logic | Yes |
| `questions.py` | Question bank | Yes |
| `web/index.html` | Student UI | Yes |
| `CLAUDE.md` | AI assistant context | Yes |
| `.env` | API keys (not in git) | Backup separately |
| `requirements.txt` | Python dependencies | Yes |
| `Procfile` | Railway start command | Yes |
| `railway.toml` | Railway config | Yes |

---

## 8. Emergency Contacts / Resources

- **Railway Status**: https://status.railway.app
- **OpenAI Status**: https://status.openai.com
- **Google Cloud Status**: https://status.cloud.google.com
- **GitHub Repo**: https://github.com/YOUR_USERNAME/idna

---

## 9. Current State (January 30, 2026)

### Working Features:
- Voice-first math tutoring
- Whisper STT (accurate math transcription)
- Google TTS (Neural2-F voice)
- Audio barge-in (interrupt tutor)
- "Didi" tutor persona with real-world examples
- Postgres production database
- Railway auto-deployment

### Pending:
- Hindi language support
- Further tutor personality refinement
- Rate limiting

---

*Last updated: January 30, 2026*
