# IDNA EdTech - TutorIntent Deployment Guide

## Files to Deploy

You have **3 files** to add/replace in your repo:

| File | Action | Description |
|------|--------|-------------|
| `tutor_intent.py` | **ADD** (new file) | Natural teaching responses |
| `evaluator.py` | **REPLACE** | Handles "2 by 3" → "2/3" |
| `web_server.py` | **REPLACE** | Integrated with TutorIntent |

---

## Quick Deploy (3 Steps)

### Step 1: Copy files to your local repo

```bash
cd C:\Users\User\Documents\idna
```

Copy the 3 downloaded files into this folder.

### Step 2: Commit and push

```bash
git add tutor_intent.py evaluator.py web_server.py
git commit -m "Add TutorIntent layer for natural teaching behavior"
git push origin main
```

### Step 3: Railway auto-deploys

Railway will automatically deploy when you push. Check logs:
```bash
railway logs --tail 50
```

---

## What Changed

### TutorIntent Layer (NEW)
- Natural, warm tutor responses
- 9 teaching intents (CONFIRM_CORRECT, GUIDE_THINKING, etc.)
- Max 2 sentences per voice turn
- No robotic "Now," "Therefore" transitions

### Enhanced Evaluator
- "2 by 3" → "2/3" ✅
- "two thirds" → "2/3" ✅
- "minus 5" → "-5" ✅
- "the answer is 5" → "5" ✅
- STT duplicate fix ✅

### TTS Speed
- Changed from 1.0 to 0.85 (slower for children)

---

## Test After Deploy

```bash
# Test health
curl https://idna-tutor-mvp-production.up.railway.app/health

# Should show: "tutor_intent": "enabled"
```

---

## Example Tutor Responses

| Scenario | Old Response | New Response |
|----------|--------------|--------------|
| Correct | "Excellent! That's correct! ✅" | "Perfect! You got it right. Ready for the next question?" |
| Wrong #1 | "Not correct. Think about..." | "Close, but not exactly. Find a common denominator first." |
| Wrong #2 | "Not quite. Think step by step!" | "Let me help more. The LCD of 3 and 4 is 12. Try once more." |
| Wrong #3 | "Solution: 11/12. Let's move on." | "Let me explain. 2/3 = 8/12... Let's try the next one." |

---

*Ready to deploy!*
