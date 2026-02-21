# IDNA v8.0 — Definitive Architecture Specification

**Author:** Claude (CTO)
**Date:** 2026-02-21
**Status:** LOCKED — Claude Code must implement exactly as written. No interpretation.

---

## Why v8.0

v7.0 through v7.5 were built feature-first: streaming, LLM eval, TTS cache, Content Bank — each bolted onto an incomplete foundation. The result: language preference breaks every session, TEACHING loops infinitely, Content Bank material never reaches the student, and every "fix" creates a new bug.

v8.0 is a foundation rewrite. Same features, proper architecture. No new capabilities — just the existing ones working correctly for 10 consecutive turns.

---

## 1. SESSION STATE SCHEMA

Every session has ONE state object. All handlers read from it and write to it. No ad-hoc variables.

```python
@dataclass
class SessionState:
    # Identity
    session_id: str
    student_name: str
    student_pin: str
    started_at: datetime

    # FSM
    current_state: TutorState = TutorState.GREETING
    previous_state: TutorState | None = None

    # Language — PERSISTS ACROSS ALL TURNS
    preferred_language: str = "hinglish"  # "hinglish" | "hindi" | "english"
    # Set by LANGUAGE_SWITCH classifier. Once set, ALL subsequent
    # LLM prompts and TTS calls use this. Never resets unless
    # student explicitly requests a different language.

    # Teaching tracking — PER CONCEPT
    current_concept_id: str | None = None     # e.g. "math_8_ch6_perfect_square"
    reteach_count: int = 0                    # How many times this concept re-explained
    teach_material_index: int = 0             # Which CB material to use next (0, 1, 2)
    concept_taught: bool = False              # True after student ACKs teaching
    empathy_given: bool = False               # True after comfort response in this state

    # Question tracking — PER QUESTION
    current_question: dict | None = None
    question_attempts: int = 0                # How many answers submitted
    hints_given: int = 0                      # 0, 1, or 2

    # Session progress
    score: int = 0
    total_questions_asked: int = 0
    total_questions_target: int = 5           # Session ends after this many
    concepts_taught: list = field(default_factory=list)
    questions_answered: list = field(default_factory=list)

    # Conversation
    conversation_history: list = field(default_factory=list)
    turn_count: int = 0
```

### Rules

1. `preferred_language` is set ONLY by LANGUAGE_SWITCH input. It NEVER resets on state transitions. It NEVER defaults back to hinglish unless the student explicitly says so.
2. `reteach_count` resets to 0 when a NEW concept starts. It does NOT reset on re-entering TEACHING for the SAME concept.
3. `empathy_given` resets to False on every state transition.
4. `teach_material_index` increments on each reteach. Maps to Content Bank material (see Section 4).

---

## 2. FSM STATES

Six states. No more, no less.

```
GREETING → TEACHING → WAITING_ANSWER → HINT → NEXT_QUESTION → SESSION_END
                ↑            |              |          |
                |            ↓              |          |
                ←———— (reteach) ————————————←          |
                ←—————————————————————————————————————←
```

### State Definitions

| State | Purpose | Didi does | Exits to |
|-------|---------|-----------|----------|
| GREETING | Welcome student | Says hello, announces chapter | TEACHING |
| TEACHING | Explain concept | Uses Content Bank material | WAITING_ANSWER (after ACK or max reteach) |
| WAITING_ANSWER | Student answers question | Reads question, waits | HINT (wrong/IDK), NEXT_QUESTION (correct), TEACHING (reteach request) |
| HINT | Give progressive hint | Hint 1, Hint 2, then full solution | WAITING_ANSWER (after hint), NEXT_QUESTION (after solution) |
| NEXT_QUESTION | Transition between questions | Praise/bridge, load next Q | TEACHING (new concept), WAITING_ANSWER (same concept), SESSION_END (done) |
| SESSION_END | Wrap up | Summary, encouragement | Terminal |

---

## 3. THE COMPLETE STATE × INPUT MATRIX

**This is the core of the architecture.** 6 states × 10 input categories = 60 combinations. Every single one is defined below. Claude Code must implement ALL of them. No gaps.

### Input Categories (from classifier)

| Category | Trigger examples |
|----------|-----------------|
| ACK | "haan", "samajh aaya", "yes", "okay", "हां" |
| IDK | "pata nahi", "nahi samjha", "I don't know", "पता नहीं" |
| REPEAT | "phir se", "dobara", "repeat please", "फिर से समझाइए" |
| ANSWER | Any numeric/mathematical response, sentence containing answer |
| LANGUAGE_SWITCH | "English mein bolo", "speak in English", "Hindi mein" |
| CONCEPT_REQUEST | "explain karo", "ye kya hai", "what is this" |
| COMFORT | "bahut mushkil", "I give up", "you're rude" |
| STOP | "bye", "band karo", "I want to stop" |
| TROLL | Off-topic nonsense, jokes |
| GARBLED | Whisper confidence < 0.4, unintelligible |

---

### GREETING × All Inputs

| Input | Action | Next State |
|-------|--------|------------|
| ACK | "Chalo shuru karte hain!" → Start teaching first concept | TEACHING |
| IDK | Treat as ACK — student is ready | TEACHING |
| REPEAT | Re-read greeting | GREETING |
| ANSWER | Ignore — no question asked yet. "Pehle concept samajhte hain!" | TEACHING |
| LANGUAGE_SWITCH | Store language. Re-greet in new language. | GREETING |
| CONCEPT_REQUEST | "Haan, abhi samjhati hoon!" | TEACHING |
| COMFORT | "Koi baat nahi, dheere dheere karenge." | GREETING |
| STOP | "Okay, phir milte hain!" | SESSION_END |
| TROLL | "Haha, chalo math pe focus karte hain!" | TEACHING |
| GARBLED | "Ek baar phir boliye?" | GREETING |

---

### TEACHING × All Inputs

| Input | Action | Next State |
|-------|--------|------------|
| ACK | Student understood. Ask the question. | WAITING_ANSWER |
| IDK | Reteach with NEXT Content Bank material (see Section 4). Increment reteach_count. If reteach_count >= 3: "Koi baat nahi, chaliye question try karte hain." → Force advance. | TEACHING (if count < 3), WAITING_ANSWER (if count >= 3) |
| REPEAT | Same as IDK — reteach with next material. Increment reteach_count. | TEACHING (if count < 3), WAITING_ANSWER (if count >= 3) |
| ANSWER | Student jumped ahead. Evaluate the answer. If correct: "Wah, bina question sune hi sahi jawab!" → next question. If wrong: "Pehle concept samajh lete hain, phir question karenge." | NEXT_QUESTION (correct) or TEACHING (wrong, continue teaching) |
| LANGUAGE_SWITCH | Store language. Reteach SAME material in new language. Do NOT increment reteach_count (language change is not a reteach). | TEACHING |
| CONCEPT_REQUEST | Same as IDK — reteach with next material. | TEACHING |
| COMFORT | Give comfort FIRST: "Koi baat nahi, bahut aasan hai, dekhiye..." THEN continue teaching. Set empathy_given=True. | TEACHING |
| STOP | End session. | SESSION_END |
| TROLL | Brief redirect, then continue teaching. | TEACHING |
| GARBLED | "Ek baar phir boliye?" | TEACHING |

---

### WAITING_ANSWER × All Inputs

| Input | Action | Next State |
|-------|--------|------------|
| ACK | Re-read the question — student may have misunderstood. "Main sawaal phir se padhti hoon..." | WAITING_ANSWER |
| IDK | Give first hint. Set hints_given=1. | HINT |
| REPEAT | Re-read the question. Do NOT count as attempt. | WAITING_ANSWER |
| ANSWER | **Use LLM evaluator** (not regex). Send answer + correct answer from CB to evaluator. If CORRECT: praise → advance. If INCORRECT: increment question_attempts. If attempts < 2: "Phir se sochiye..." stay. If attempts >= 2: give hint. If PARTIAL: "Sahi direction mein ho! [specific feedback]". If IDK-IN-ANSWER: treat as IDK → hint. | NEXT_QUESTION (correct), WAITING_ANSWER (incorrect, attempts < 2), HINT (incorrect, attempts >= 2 or IDK) |
| LANGUAGE_SWITCH | Store language. Re-read question in new language. | WAITING_ANSWER |
| CONCEPT_REQUEST | Student wants to re-learn. Go back to teaching. Reset reteach_count for this concept. | TEACHING |
| COMFORT | Comfort first, then re-read question gently. | WAITING_ANSWER |
| STOP | End session. | SESSION_END |
| TROLL | "Chalo focus karte hain! Sawaal ye hai..." re-read question. | WAITING_ANSWER |
| GARBLED | "Ek baar phir boliye?" | WAITING_ANSWER |

---

### HINT × All Inputs

| Input | Action | Next State |
|-------|--------|------------|
| ACK | Student understood hint. Re-ask the question. "Ab try karo!" | WAITING_ANSWER |
| IDK | Give next hint level. Hint 1 → Hint 2 → Full solution. After solution: "Koi baat nahi, agle sawaal mein aur accha karenge!" | HINT (if more hints), NEXT_QUESTION (after solution) |
| REPEAT | Re-read the hint. | HINT |
| ANSWER | Evaluate. If correct after hint: "Bahut accha! Hint se samajh aaya!" (slightly less praise than no-hint correct). If wrong: next hint level or solution. | NEXT_QUESTION (correct), HINT (wrong, more hints), NEXT_QUESTION (wrong, solution given) |
| LANGUAGE_SWITCH | Store language. Re-read hint in new language. | HINT |
| CONCEPT_REQUEST | Go back to teaching this concept. Reset reteach_count. | TEACHING |
| COMFORT | Comfort + simplify hint. | HINT |
| STOP | End session. | SESSION_END |
| TROLL | Redirect + re-read hint. | HINT |
| GARBLED | "Ek baar phir boliye?" | HINT |

---

### NEXT_QUESTION × All Inputs

This is a TRANSIENT state. Didi gives praise/bridge, then automatically loads next question.

| Input | Action | Next State |
|-------|--------|------------|
| (auto) | If total_questions_asked >= target: go to summary. Else: check if next Q has different concept → TEACHING. Same concept → WAITING_ANSWER. | SESSION_END or TEACHING or WAITING_ANSWER |

If student speaks during transition (before next question loads):

| Input | Action | Next State |
|-------|--------|------------|
| ACK | Proceed to next question. | (auto transition above) |
| STOP | End session. | SESSION_END |
| Any other | "Ek second, agle sawaal pe chalte hain!" → proceed. | (auto transition above) |

---

### SESSION_END × All Inputs

| Input | Action | Next State |
|-------|--------|------------|
| Any | "Session khatam ho gayi! Aaj aapne {score}/{total} sahi kiye. Kal phir milte hain!" | Terminal (no more transitions) |

---

## 4. CONTENT BANK INJECTION RULES

The Content Bank (CB) has structured material for each concept. The `teach_material_index` determines which material Didi uses on each teaching turn.

### Teaching Material Sequence (per concept)

```
Index 0 (first teach):
  → CB.definition_tts + CB.hook (if available)
  → End with "Samajh aaya?"

Index 1 (first reteach):
  → CB.teaching_methodology.analogy
  → CB.examples[0].solution_tts
  → End with "Ab samajh aaya?"

Index 2 (second reteach):
  → CB.examples[1].solution_tts (if exists)
  → CB.vedic_trick (if exists) OR CB.key_insight
  → End with "Ek baar aur try karte hain?"

Index >= 3 (force advance):
  → "Koi baat nahi, question try karte hain. Question se bhi seekhte hain!"
  → Transition to WAITING_ANSWER
```

### HINT Material Sequence

```
hints_given = 0 → Give hint from CB.hints[0] (direction hint)
hints_given = 1 → Give hint from CB.hints[1] (step-by-step hint)
hints_given = 2 → Give full solution from CB.solution_tts
                → Log: "Solution given, moving to next question"
                → Transition to NEXT_QUESTION
```

### LLM Prompt Injection

EVERY LLM call MUST include these in the system prompt:

```
1. Language instruction:
   "Respond in {session.preferred_language}."
   - "hinglish" → Mix of Hindi and English, natural Didi voice
   - "english" → Full English, warm tone, simple words
   - "hindi" → Full Hindi, Devanagari-friendly

2. Current state context:
   "Current state: {session.current_state}"
   "Student has heard this concept {session.reteach_count} times."

3. Content Bank material (for TEACHING state):
   "Use this EXACT material to teach:"
   "{CB material for current teach_material_index}"
   "Do NOT generate your own definition. Use the material above."

4. Content Bank question (for WAITING_ANSWER state):
   "The question is: {current_question.question_tts}"
   "The correct answer is: {current_question.answer}"
   "Do NOT reveal the answer."

5. Conversation history (last 6 turns max):
   "{conversation_history[-6:]}"
```

---

## 5. LANGUAGE PERSISTENCE — THE COMPLETE RULE

This is the #1 recurring bug. Here is the definitive rule:

```
WHEN classifier returns LANGUAGE_SWITCH:
    session.preferred_language = extras['preferred_language']
    Log: "Language set to {preferred_language}"

WHEN building ANY LLM prompt (regardless of input category):
    system_prompt += f"\n\nIMPORTANT: Respond in {session.preferred_language}."
    if session.preferred_language == "english":
        system_prompt += " Use only English. No Hindi words at all."
    elif session.preferred_language == "hindi":
        system_prompt += " Use only Hindi. No English words."
    else:
        system_prompt += " Use natural Hinglish mix."

WHEN calling TTS:
    if session.preferred_language == "english":
        tts_language = "en-IN"
    else:
        tts_language = "hi-IN"

NEVER:
    - Reset preferred_language on state transition
    - Default to hinglish on non-LANGUAGE_SWITCH turns
    - Ignore preferred_language in prompt building
```

---

## 6. ERROR HANDLING — EVERY FAILURE PATH

### STT Failure
- Sarvam returns error or timeout → "Ek baar phir boliye? Aapki awaaz nahi aayi."
- Stay in current state. Do not transition.

### LLM Failure
- GPT-4o returns error or timeout → Use fallback response for current state:
  - GREETING: "Namaste! Chalo math practice karte hain."
  - TEACHING: Re-read last CB material without LLM generation.
  - WAITING_ANSWER: "Main sawaal phir se padhti hoon." + re-read question.
  - HINT: Read CB hint directly without LLM paraphrase.
- Stay in current state. Do not transition.

### TTS Failure
- Sarvam returns error → Send text-only response to frontend.
- Frontend shows text and plays no audio.
- Stay in current state.

### LLM Evaluator Failure
- Evaluator returns invalid JSON or error → Fall back to regex matching.
- If regex also fails → Treat as IDK: "Main samajh nahi paayi, ek baar phir boliye?"
- Stay in WAITING_ANSWER.

### Streaming Failure
- Stream breaks midway → Send accumulated text as final response.
- new_state MUST be initialized before try block (fix from v7.5.2).

### Container Restart
- TTS cache in Postgres (not filesystem). Survives restarts.
- Session state in Postgres. Survives restarts.
- Precache checks existing entries before regenerating.

---

## 7. INTEGRATION TESTS — MANDATORY BEFORE SHIP

These 15 tests simulate real multi-turn conversations. ALL must pass.

```python
# Test 1: Language persists across turns
# Set English → say REPEAT → verify response is in English
# Set English → say IDK → verify response is in English
# Set English → answer wrong → verify hint is in English

# Test 2: Reteach caps at 3
# Say IDK 4 times in TEACHING → verify 4th time advances to question
# Verify teach_material_index went 0 → 1 → 2 → forced advance

# Test 3: Content Bank material appears in teaching
# Start session → verify first teaching turn contains CB.definition_tts
# Say IDK → verify second turn contains CB.teaching_methodology.analogy
# Say IDK → verify third turn contains CB.examples[1] or vedic_trick

# Test 4: LLM evaluator extracts answer from sentence
# Send "Haan, answer is 7" → verify CORRECT
# Send "saat" → verify evaluated (not regex failure)
# Send "I think it's forty-nine" → verify evaluated

# Test 5: Full 5-question session completes
# ACK through teaching → answer 5 questions → verify SESSION_END
# Verify score is correct
# Verify session summary is generated

# Test 6: Hint progression
# Answer wrong twice → verify hint 1
# Answer wrong again → verify hint 2
# Say IDK → verify full solution → next question

# Test 7: COMFORT before teaching continues
# In TEACHING, say "bahut mushkil hai" → verify comfort response
# Then verify teaching continues (not stuck)

# Test 8: LANGUAGE_SWITCH does not count as reteach
# In TEACHING, say "speak English" → verify reteach_count unchanged
# Say "I don't understand" → verify reteach_count = 1 (not 2)

# Test 9: CONCEPT_REQUEST from WAITING_ANSWER goes back to TEACHING
# In WAITING_ANSWER, say "explain karo" → verify state = TEACHING
# Verify reteach_count reset for this concept

# Test 10: STOP from any state ends session
# In GREETING, say "bye" → SESSION_END
# In TEACHING, say "band karo" → SESSION_END
# In WAITING_ANSWER, say "stop" → SESSION_END

# Test 11: Streaming endpoint handles all input categories
# Send ACK to streaming endpoint → no crash
# Send REPEAT to streaming endpoint → no crash
# Send LANGUAGE_SWITCH → no crash

# Test 12: TTS cache persists across simulated restart
# Cache a TTS entry → "restart" (clear in-memory) → verify DB still has it

# Test 13: Fallback on LLM failure
# Mock GPT-4o timeout → verify fallback response delivered
# Verify state does NOT transition on failure

# Test 14: Garbled input handling
# Send low-confidence STT → verify "phir boliye" response
# Verify state unchanged

# Test 15: Session state persistence
# Start session → set language → answer 2 questions
# Reload session from DB → verify all state preserved
```

---

## 8. FILES TO CHANGE

This is a REWRITE of the session management layer, not a patch.

| File | Action | What changes |
|------|--------|-------------|
| `app/models/session.py` (NEW) | Create | SessionState dataclass from Section 1 |
| `app/fsm/transitions.py` (NEW) | Create | Complete state × input matrix from Section 3 |
| `app/fsm/handlers.py` (NEW) | Create | One handler function per state |
| `app/tutor/instruction_builder.py` | Rewrite | Language injection, CB material injection per Section 4-5 |
| `app/tutor/answer_evaluator.py` | Keep | Already working from v7.5 |
| `app/routers/student.py` | Rewrite | Use new FSM, SessionState, handlers |
| `app/voice/tts_precache.py` | Keep | Already uses Postgres from v7.5.2 |
| `app/voice/streaming.py` | Keep | Already working from v7.5.2 |
| `tests/test_integration.py` (NEW) | Create | All 15 integration tests from Section 7 |
| `verify.py` | Update | Add checks 19-21 (language field, reteach cap, integration tests) |

### Files NOT to touch
- `app/voice/stt.py` — STT pipeline is stable
- `app/voice/tts.py` — TTS pipeline is stable
- `web/` — Frontend is stable
- Content Bank JSON — Content is complete

---

## 9. DEPLOYMENT SEQUENCE

```
Step 1: Create SessionState dataclass (app/models/session.py)
Step 2: Create transition matrix (app/fsm/transitions.py)
Step 3: Create state handlers (app/fsm/handlers.py)
Step 4: Rewrite instruction_builder with language + CB injection
Step 5: Rewrite student router to use new FSM
Step 6: Write all 15 integration tests
Step 7: Run verify.py — all checks must pass
Step 8: Run integration tests — all 15 must pass
Step 9: Run full test suite — all tests must pass
Step 10: Manual test: set English once, do 5 turns, verify all English
Step 11: Manual test: say IDK 4 times, verify advances to question
Step 12: Manual test: full 5-question session, verify completion
Step 13: Commit as v8.0.0
Step 14: Deploy to Railway
Step 15: Live test with student
```

### Commit message
```
v8.0.0: architecture rewrite — session state schema, complete FSM 
transition matrix (60 combinations), language persistence, reteach 
cap, Content Bank injection, 15 integration tests
```

---

## 10. WHAT THIS FIXES

| Bug | Root cause | How v8.0 fixes it |
|-----|-----------|-------------------|
| Language resets every turn | preferred_language not in session state | SessionState.preferred_language persists, injected in EVERY prompt |
| Infinite TEACHING loop | No reteach counter | reteach_count caps at 3, forces advance |
| Content Bank not appearing | instruction_builder doesn't inject CB | Mandatory CB injection per teach_material_index |
| Streaming crash on ACK/REPEAT | new_state uninitialized | Proper handler for every state × input (no gaps) |
| Enforcer fails 3x every time | Regex checking natural language answers | LLM evaluator is primary, regex is fallback only |
| "Sochiye" catch-all | Missing handlers for many state × input combos | All 60 combinations defined — no catch-all |
| Different examples not used on reteach | No material progression tracking | teach_material_index increments per reteach |

---

## FINAL NOTE TO CLAUDE CODE

This document defines EXACTLY what to build. There are 60 state × input combinations. All 60 are specified. There are 15 integration tests. All 15 must pass. There is one session state schema. Use it everywhere.

Do not add features. Do not "improve" the design. Do not combine files. Do not skip tests. Implement what is written, test what is specified, ship what passes.

The student sets English once. Didi speaks English for the rest of the session. That is the bar.
