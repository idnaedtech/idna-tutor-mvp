# P0 BUG FIX: Didi Skips Teaching, IDK Loop, Repetition

## Priority: P0 — Blocks all chapter content. Fix before any new features.

## Live Bug Report (Feb 18, 2026)

A real student tested v7.0.1 with the new Chapter 1: Square & Cube questions. Here is the exact transcript:

```
Didi: Namaste Priya! Chalo math practice karte hain. Pehla sawaal: Kya 49 ek perfect square hai?
Student: पता नहीं, आप समझाइए कौन सा चैप्टर है?
Didi: Sochiye — answer kya ho sakta hai?
Student: इस बारे में है। दिस वॉट वॉट।
Didi: Sochiye — answer kya ho sakta hai?
Student: ये किस चैप्टर के बारे में है? कौन सा चैप्टर है ये?
Didi: Sochiye — answer kya ho sakta hai?
Didi: Aap wahan ho? Koi sawaal hai toh puchiye.
Student: कुछ समझ में नहीं आया।
Didi: Sochiye — answer kya ho sakta hai?
```

## Three Bugs Identified

### BUG 1: Teaching phase skipped entirely
**What happened:** Didi jumped straight from greeting to question: "Pehla sawaal: Kya 49 ek perfect square hai?" without EVER explaining what a perfect square is.
**Expected:** GREETING → TEACHING (explain concept with Indian example) → student ACK → THEN ask question.
**Root cause:** The session start flow is not using SKILL_LESSONS pre_teach content. It's going directly from GREETING to WAITING_ANSWER, skipping the TEACHING state.

### BUG 2: IDK input not triggering reteach
**What happened:** Student said "पता नहीं, आप समझाइए" (I don't know, please explain) — textbook IDK. Didi responded with "Sochiye — answer kya ho sakta hai?" which is a WAITING_ANSWER nudge.
**Expected:** IDK in WAITING_ANSWER should trigger → give hint (first time) or reteach concept (if no teaching happened yet).
**Root cause:** Either input_classifier is not classifying "पता नहीं, आप समझाइए" as IDK, OR the state machine handler for IDK in WAITING_ANSWER state is broken/missing.

### BUG 3: Stuck in repetition loop  
**What happened:** Every student input gets the same response: "Sochiye — answer kya ho sakta hai?" — five times in a row.
**Expected:** After 2 failed attempts, Didi should give hint. After "कुछ समझ में नहीं आया" (didn't understand anything), Didi should comfort + explain.
**Root cause:** The state machine is stuck in WAITING_ANSWER and not differentiating between input categories. It seems to be using a single fallback response for all unrecognized inputs.

---

## Fix Instructions

### Fix 1: Force TEACHING state before first question

In `agentic_tutor.py`, find the function that starts a session or serves the first question. The flow MUST be:

```
Session Start:
1. GREETING → Didi says "Namaste! Aaj hum [chapter] padhenge."
2. Transition to TEACHING state
3. TEACHING → Load pre_teach from SKILL_LESSONS for the first question's target_skill
4. Didi teaches the concept using pre_teach text + Indian example
5. Didi ends with "Samajh aaya?"
6. WAIT for student response
7. If ACK → transition to WAITING_ANSWER, ask the question
8. If IDK → reteach with different example (use key_insight or indian_example from SKILL_LESSONS)
9. If ACK after reteach → NOW ask the question
```

The critical change: **There must be a TEACHING turn between greeting and first question.** The question bank file `ch1_square_and_cube.py` has SKILL_LESSONS with these fields for every skill:
- `pre_teach` — primary explanation in Hinglish
- `indian_example` — relatable example  
- `key_insight` — the core "aha" moment
- `common_errors` — what students typically get wrong

Use `pre_teach` for first teach. If student says IDK, use `indian_example` or `key_insight` for reteach.

Here is the logic that MUST exist:

```python
async def start_question_flow(session, question):
    """Start the teaching + question flow for a new question."""
    skill = question.get("target_skill")
    lesson = SKILL_LESSONS.get(skill, {})
    
    # Phase 1: TEACH the concept first
    pre_teach = lesson.get("pre_teach", "")
    indian_example = lesson.get("indian_example", "")
    
    if pre_teach:
        # Build instruction for LLM to teach this concept
        teach_instruction = (
            f"Teach the student this concept in Hinglish (aap form, warm tone):\n"
            f"{pre_teach}\n"
            f"Use this Indian example: {indian_example}\n"
            f"End with: 'Samajh aaya?'\n"
            f"Do NOT ask any question yet. Only teach."
        )
        session.state = "TEACHING"
        session.pending_question = question
        return teach_instruction  # Send to LLM, play response
    else:
        # No lesson available, ask question directly (fallback)
        session.state = "WAITING_ANSWER"
        return build_question_instruction(question)
```

And the handler for student response during TEACHING:

```python
async def handle_teaching_response(session, student_input, input_category):
    """Handle student response while in TEACHING state."""
    if input_category == "ACK":
        # Student understood. Now ask the question.
        session.state = "WAITING_ANSWER"
        question = session.pending_question
        return build_question_instruction(question)
    
    elif input_category in ("IDK", "CONCEPT_REQUEST"):
        # Student didn't understand. Reteach with different approach.
        skill = session.pending_question.get("target_skill")
        lesson = SKILL_LESSONS.get(skill, {})
        
        # Use a different explanation than pre_teach
        reteach_text = lesson.get("key_insight") or lesson.get("indian_example") or lesson.get("pre_teach")
        reteach_instruction = (
            f"The student didn't understand. Explain again differently:\n"
            f"{reteach_text}\n"
            f"Use a simpler example. End with: 'Ab samajh aaya?'\n"
            f"Do NOT ask any question yet."
        )
        session.state = "TEACHING"  # Stay in TEACHING
        return reteach_instruction
    
    elif input_category == "COMFORT":
        # Student is frustrated/confused
        comfort_instruction = (
            f"The student is confused or frustrated. First comfort them:\n"
            f"'Koi baat nahi, hum aaram se samjhenge.'\n"
            f"Then briefly re-explain the concept in the simplest possible way.\n"
            f"End with: 'Ab try karte hain?'"
        )
        session.state = "TEACHING"
        return comfort_instruction
    
    else:
        # Any other input during TEACHING — gently redirect to the teaching
        return (
            f"The student said something off-topic during teaching. "
            f"Gently bring them back: 'Haan haan, pehle yeh concept samajh lete hain.' "
            f"Then continue the explanation. End with 'Samajh aaya?'"
        )
```

### Fix 2: Fix IDK handling in WAITING_ANSWER state

Find the handler for WAITING_ANSWER state. When input_category is IDK, it must NOT respond with "Sochiye — answer kya ho sakta hai?" It must give the first hint.

```python
async def handle_waiting_answer(session, student_input, input_category):
    """Handle student response while in WAITING_ANSWER state."""
    question = session.current_question
    
    if input_category == "ANSWER":
        # Check the answer...
        return handle_answer_check(session, student_input, question)
    
    elif input_category == "IDK":
        # Student doesn't know. Give hint based on attempt count.
        hints = question.get("hints", [])
        attempt = session.hint_count  # Track how many hints given
        
        if attempt == 0 and len(hints) > 0:
            session.hint_count = 1
            hint_instruction = (
                f"Student said they don't know. Give this hint:\n"
                f"'{hints[0]}'\n"
                f"Then ask them to try again."
            )
            return hint_instruction
        
        elif attempt == 1 and len(hints) > 1:
            session.hint_count = 2
            hint_instruction = (
                f"Student still doesn't know after first hint. Give second hint:\n"
                f"'{hints[1]}'\n"
                f"Then ask them to try once more."
            )
            return hint_instruction
        
        else:
            # Max hints given. Reveal answer and move on.
            explanation = question.get("explanation", question["answer"])
            reveal_instruction = (
                f"Student couldn't answer after hints. Reveal the answer gently:\n"
                f"'Koi baat nahi! Answer hai: {question['answer']}. "
                f"{explanation}'\n"
                f"Then say: 'Chalo agle question pe chalte hain.'"
            )
            session.state = "NEXT_QUESTION"
            return reveal_instruction
    
    elif input_category == "CONCEPT_REQUEST":
        # Student wants the concept explained again
        skill = question.get("target_skill")
        lesson = SKILL_LESSONS.get(skill, {})
        pre_teach = lesson.get("pre_teach", "")
        reteach_instruction = (
            f"Student wants the concept re-explained. Teach briefly:\n"
            f"{pre_teach}\n"
            f"Then ask the question again."
        )
        return reteach_instruction
    
    elif input_category == "COMFORT":
        comfort_instruction = (
            f"Student is frustrated. Comfort first:\n"
            f"'Arey tension mat lo! Yeh thoda tricky hai par hum saath mein karenge.'\n"
            f"Then give the first hint: '{question.get('hints', [''])[0]}'"
        )
        return comfort_instruction
    
    elif input_category == "STOP":
        return handle_session_end(session)
    
    else:
        # TROLL or unrecognized — gentle redirect
        return (
            f"Student said something off-topic. Gently redirect:\n"
            f"'Haan, chalo sawaal pe wapas aate hain.'\n"
            f"Repeat the question: '{question['question']}'"
        )
```

### Fix 3: Fix input_classifier for Hindi IDK phrases

In `input_classifier.py`, verify these Hindi phrases are in the IDK category:

```python
IDK_PHRASES = [
    # Existing English
    "i don't know", "no idea", "not sure", "idk",
    # Hindi — CRITICAL: these must be present
    "पता नहीं",           # pata nahi
    "नहीं पता",           # nahi pata
    "समझ में नहीं आया",    # samajh mein nahi aaya
    "कुछ समझ में नहीं आया", # kuch samajh mein nahi aaya
    "नहीं समझा",          # nahi samjha
    "मुझे नहीं पता",       # mujhe nahi pata
    "मालूम नहीं",          # maloom nahi
    "pata nahi",
    "nahi pata",
    "samajh nahi aaya",
    "nahi samjha",
    "maloom nahi",
]

CONCEPT_REQUEST_PHRASES = [
    # Hindi — CRITICAL
    "आप समझाइए",         # aap samjhaiye
    "समझाइए",            # samjhaiye
    "बताइए",             # bataiye
    "यह क्या है",         # yeh kya hai
    "कौन सा चैप्टर",      # kaunsa chapter
    "aap samjhaiye",
    "samjhaiye",
    "bataiye",
    "explain karo",
    "explain please",
    "what is this",
]
```

**Important:** The student's message "पता नहीं, आप समझाइए कौन सा चैप्टर है?" contains BOTH IDK ("पता नहीं") AND CONCEPT_REQUEST ("आप समझाइए"). The classifier should detect both. If it can only return one, IDK should take priority since it triggers the teaching/hint flow.

Also add these COMFORT phrases if not present:

```python
COMFORT_PHRASES = [
    "कुछ समझ में नहीं आया",  # kuch samajh mein nahi aaya
    "बहुत मुश्किल",         # bahut mushkil
    "मुझसे नहीं होगा",      # mujhse nahi hoga
    "छोड़ दो",             # chhod do
    "I give up",
    "too hard",
    "can't do this",
]
```

### Fix 4: Reset hint_count per question

Make sure `session.hint_count` resets to 0 when a new question is served. Otherwise the hint system accumulates across questions.

```python
def serve_next_question(session):
    """Load next question and reset tracking."""
    session.current_question = get_next_question(session)
    session.hint_count = 0
    session.attempt_count = 0
    session.pending_question = session.current_question
```

### Fix 5: Remove or fix the hardcoded fallback

Search the codebase for the exact string:
```
"Sochiye — answer kya ho sakta hai?"
```

This is being used as a catch-all fallback when the state machine doesn't know what to do. It should NEVER be the default. Replace it with proper category-based handling as shown above. If it's used as a timeout/silence handler, that's acceptable only after 30+ seconds of silence, not as a response to actual student input.

Also search for:
```
"Aap wahan ho? Koi sawaal hai toh puchiye."
```

This is a silence/inactivity prompt. It should only trigger after genuine inactivity (no input for 30+ seconds), NOT after the student has just spoken.

---

## Testing

### Test 1: Teaching before question
```
Start session with Chapter 1: Square & Cube
EXPECTED: Didi greets, then TEACHES what a perfect square is
EXPECTED: Didi ends teaching with "Samajh aaya?"
EXPECTED: Only after student ACK, Didi asks the question
```

### Test 2: IDK during question
```
Didi: "Kya 49 ek perfect square hai?"
Student: "पता नहीं"
EXPECTED: Didi gives Hint 1 from question bank, NOT "Sochiye"
Student: "अभी भी नहीं पता"
EXPECTED: Didi gives Hint 2
Student: "नहीं हो रहा"
EXPECTED: Didi reveals answer gently and moves to next question
```

### Test 3: Concept request during question
```
Didi: "Kya 49 ek perfect square hai?"
Student: "पहले बताइए perfect square क्या होता है?"
EXPECTED: Didi explains the concept (from SKILL_LESSONS pre_teach)
EXPECTED: Then re-asks the question
```

### Test 4: Comfort during question
```
Didi: "Kya 49 ek perfect square hai?"
Student: "कुछ समझ में नहीं आया"
EXPECTED: Didi comforts first ("Koi baat nahi!")
EXPECTED: Then gives a hint, NOT "Sochiye"
```

### Test 5: No repetition
```
Any sequence of 3+ student messages should NEVER get the same Didi response.
Especially: "Sochiye — answer kya ho sakta hai?" must not appear twice in a row.
```

---

## Run Order

1. Fix `input_classifier.py` first (5 min) — add missing Hindi phrases
2. Fix `agentic_tutor.py` (30 min) — teaching flow + IDK handling + hint progression
3. Fix fallback strings — remove hardcoded "Sochiye" catch-all
4. Run tests: `python -m pytest tests/ -v`
5. Manual test with the exact transcript above — must not reproduce
6. Commit: `v7.0.3: P0 fix — teaching before question, IDK hint flow, remove repetition loop`
7. Push and deploy

## DO NOT

- Do NOT add new FSM states. Use existing GREETING → TEACHING → WAITING_ANSWER → EVALUATING.
- Do NOT rewrite DIDI_PROMPT. Append rules only.
- Do NOT change TTS voice or STT config.
- Do NOT remove existing questions or skill lessons.
- Do NOT change the session start greeting format — just add teaching AFTER it.
