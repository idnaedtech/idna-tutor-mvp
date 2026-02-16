# IDNA EdTech: Gap Analysis
## ChatGPT Year-Long Vision (idna_edtech_structure.md) vs Claude v7.0 Codebase

---

## WHAT v7.0 GETS RIGHT (Aligned with Vision)

### ✅ Voice-First Pipeline
Vision: Student Voice → ASR → Intent Classifier → Brain Router → Teacher Policy → Memory → TTS
v7.0:   Audio → STT → Input Classifier → State Machine → Answer Checker → Instruction Builder → LLM → Enforcer → TTS
**Match.** Same pipeline, different naming. State Machine = Brain Router. Enforcer = Teacher Policy Layer.

### ✅ Teacher Behavioral Primitives
Vision defines: BREAKDOWN, PROBE, WAIT, CORRECT, REVEAL, RECAP, CHECKPOINT
v7.0 implements via instruction_builder.py:
- BREAKDOWN → teach_concept (different_example approach)
- PROBE → probe_understanding
- WAIT → WAITING_ANSWER state
- CORRECT → evaluate_answer with diagnostic
- REVEAL → give_hint → show_solution (progressive)
- RECAP → end_session summary
- CHECKPOINT → CHECKING_UNDERSTANDING state
**Match.** All primitives exist as FSM states or instruction types.

### ✅ Non-Negotiable Rules
Vision: Never shame, never rush, never skip steps, never assume comprehension
v7.0 enforcer.py: No false praise, specificity anchor, max word limit, one idea per turn
**Match.** v7.0 is stricter — enforces at code level, not just prompt level.

### ✅ Error Handling Protocol
Vision: 1) Don't say "Wrong" 2) Identify exact error 3) Explain why 4) Re-ask 5) Confirm
v7.0: answer_checker returns specific diagnostic → enforcer strips praise → 
      hint_1 → hint_2 → full_solution → follow-up question
**Match.** v7.0 adds the progressive hint system (3 levels).

### ✅ Parent-Centric Reporting
Vision: Voice summaries, weak area mapping, behavioral insights, emotional not statistical
v7.0: Parent voice sessions, mastery-to-narrative translation, native language reports
**Match.** v7.0 adds parent INSTRUCTION state (parent can direct Didi's focus).

### ✅ Multilingual Support
Vision: 13+ Indian languages, code-mixed, detect preferred language
v7.0: 11 languages in config (Sarvam Bulbul v3), student language ≠ parent language
**Match.** v7.0 handles the critical parent/student language split.

### ✅ Phased Execution
Vision: "Validate one grade, one subject, one language before scaling"
v7.0: Class 8, Math, Chapter 1 Rational Numbers, Hinglish. Feature flags for Science/Hindi.
**Match.** This was the hardest lesson from the vision doc.

### ✅ Positioning
Vision: "AI tuition REPLACEMENT, not homework helper, not chatbot"
v7.0: State machine enforces structured teaching flow, not free-form chat
**Match.**

---

## CRITICAL GAPS: What the Vision Has That v7.0 Does NOT

### ❌ GAP 1: Brain Router / Mode Switching
**Vision (§3.2, §5.2):** Brain Router decides between 6+ modes:
- Concept explanation mode
- Step-by-step solving mode  
- Revision mode
- Exam practice mode
- Doubt clarification mode
- Parent summary mode
- Language switch mode

**v7.0 current:** Single mode — linear teaching flow (greet → discover → teach → question → evaluate).
No exam practice mode. No revision mode. No doubt clarification as a distinct mode.

**Impact:** HIGH. A student who comes back saying "kal jo padha tha revise karna hai" has 
no dedicated path. The state machine would route them through DISCOVERING_TOPIC again.

**Fix needed:** Add session modes:
- FRESH_LEARNING (current default)
- REVISION (revisit previously taught concepts, skip teaching, go to questions)
- EXAM_PRACTICE (timed questions, no hints, exam conditions)
- DOUBT_CLEARING (student asks specific conceptual question)
These should be selectable at session start or via voice command mid-session.

---

### ❌ GAP 2: Pedagogical Learning Loop (8-Step Constructivist Cycle)
**Vision (§4, §4.2, §6):** Each concept must follow:
1. Activate prior knowledge
2. Introduce simple case
3. Guided student attempt
4. Error diagnosis
5. Reinforcement
6. Generalization
7. Practice variation
8. Micro-assessment

**v7.0 current:** Simplified to: Teach → Question → Evaluate → Hint/Solution → Next.
Missing: Activation (step 1), Generalization (step 6), Practice Variation (step 7).

**Impact:** MEDIUM-HIGH. Without activation, Didi jumps into teaching without checking 
what the student already knows. Without generalization, students memorize procedure 
without understanding the underlying principle. Without practice variation, students 
only see one type of problem per skill.

**Fix needed:** 
- Add ACTIVATION sub-state before TEACHING: "Aapko pata hai fractions kya hote hain?"
- After correct answer, add GENERALIZATION: "Toh iska matlab yeh hai ki same denominator
  wale fractions add karna easy hai — sirf numerators add karo"
- After generalization, pick a VARIATION question (different numbers, same concept)
  before moving to new skill

---

### ❌ GAP 3: Student Persona Detection & Adaptation
**Vision (§5):** Three personas with different teaching strategies:
- Persona 1: Weak English (most common) → hybrid, short sentences, more encouragement
- Persona 2: Average performer → timed exercises, error analytics, increasing complexity
- Persona 3: High achiever → Olympiad-style, "why" explanations, concept deep dive

**v7.0 current:** Single teaching approach for all students. 
mastery_score tracks skill level but doesn't change TEACHING STYLE.

**Impact:** MEDIUM. A high-achieving student gets the same slow, step-by-step treatment 
as a struggling student. Boredom → disengagement.

**Fix needed:** Add persona detection to memory.py:
- After 5 sessions, classify student as BEGINNER / AVERAGE / ADVANCED based on:
  - Accuracy rate (< 40% = beginner, 40-70% = average, > 70% = advanced)
  - Hint usage rate
  - Speed of answering
- Pass persona to instruction_builder → adjust prompt templates:
  - BEGINNER: shorter sentences, more Hindi, more encouragement, frequent checkpoints
  - AVERAGE: standard Hinglish, medium pacing, regular practice
  - ADVANCED: more English, faster pacing, "why" questions, skip basic teaching

---

### ❌ GAP 4: Regional Behavior Modulation
**Vision (§4.1-4.5, Document 2):** Detailed behavioral tuning per region:
- Hindi Belt: slow pace, Hindi-English mix, daily-life objects, reassuring
- Telangana/AP: English-first with Telugu fallback, structured logical, medium pace
- Tamil Nadu: short sentences, linear logical, strict accuracy, neutral tone
- West Bengal: concept-heavy, "why" explanations, analytical
- Maharashtra Urban: direct, efficient, exam-strategy aware
- Rural Tier-2/3: very short sentences, very slow, very gentle, native-first

**v7.0 current:** One behavior profile. Hinglish for all students.
Regional cultural examples in instruction_builder.py only mention roti/cricket/Diwali.

**Impact:** MEDIUM for MVP (pilot is Nizamabad only), HIGH for scale.

**Fix needed (Phase 2):**
- Add region field to student profile (auto-detected from parent's language or manually set)
- Create regional behavior profiles in a config dict:
  region_profiles = {
    "hindi_belt": {pace: "slow", lang_mix: "hindi-heavy", encouragement: "high", examples: "roti,cricket"},
    "telangana": {pace: "medium", lang_mix: "english-first", encouragement: "moderate", examples: "idli,biryani"},
    ...
  }
- Pass regional profile to instruction_builder → modify system prompt accordingly

---

### ❌ GAP 5: Cultural Example Adaptation by Region
**Vision (§10):**
- Fractions: roti (North), idli/dosa (South), fish curry (Bengal), mango (universal)
- Physics: bus, auto, cycle — not abstract vehicles

**v7.0 current:** Only "roti, cricket, Diwali, monsoon" in instruction_builder.py DIDI_BASE.
No regional example switching.

**Impact:** LOW for Nizamabad pilot, MEDIUM for scale.

**Fix needed:** Example bank per region in content layer, selected based on student.region.

---

### ❌ GAP 6: Confidence Calibration System
**Vision (§9):** Detect hesitation markers, repeated confusion, overconfidence without understanding.
Increase scaffolding if confusion persists. Increase difficulty if mastery consistent.

**v7.0 current:** skill_mastery.mastery_score tracks accuracy but not:
- Hesitation (time between question and answer)
- Repeated confusion on same concept
- Overconfidence (answers fast but wrong)
- Confidence trend over time

**Impact:** MEDIUM. Without this, Didi can't distinguish between "student is thinking" 
and "student is stuck". Can't detect when a student answers quickly but incorrectly 
(overconfidence pattern).

**Fix needed:**
- Track answer_time_seconds in session_turns table
- Add confidence_trend to skill_mastery (rolling average of [correct + fast] vs [incorrect + slow])
- Use confidence_trend in instruction_builder to adjust tone:
  - Low confidence + low accuracy → extra encouragement, simpler questions
  - High confidence + low accuracy → slow down, recheck fundamentals
  - High confidence + high accuracy → increase difficulty

---

### ❌ GAP 7: WAIT Primitive (Silence Handling)
**Vision (§4.3):** WAIT — pause for student participation before proceeding.
When student is silent: 1) Simplify 2) Give hint 3) Ask easier sub-question

**v7.0 current:** No silence detection. If student doesn't speak, nothing happens.
DESIGN_DECISIONS.md mentions 15-second timeout but it's not implemented.

**Impact:** HIGH. A student who is thinking gets no support. A student who is confused 
gets no prompt. In voice-first, silence is data — it must be handled.

**Fix needed:**
- Frontend: detect 15s silence → send "SILENCE" event to backend
- Backend: classify as IDK-equivalent → give gentle nudge:
  "Kuch sochiye... hint chahiye?"
- 30s silence → more direct: "Koi baat nahi, ek hint deti hoon"
- 60s total → pause session gracefully

---

### ❌ GAP 8: Board-Agnostic Curriculum Mapping
**Vision (§3.1, §6):** 
Core Concept Layer → Topic Layer → Chapter Layer → Board-Specific Variation → Grade Depth

v7.0: Hardcoded to CBSE Class 8 NCERT. question_bank has chapter field but no board field.

**Impact:** LOW for MVP (CBSE only), HIGH for ICSE/State Board expansion.

**Fix needed (Phase 2):**
- Add board field to question_bank and students tables
- Create concept-level abstraction: concept "fractions" exists independent of board
- Board-specific layer maps concepts to chapter numbers and question styles
- State Board students get same concepts, different chapter references

---

### ❌ GAP 9: Exam Practice Mode
**Vision (§3.2, §5.2):** Exam practice as a distinct Brain Router mode.
- Timed questions
- No hints
- Exam-like conditions
- Performance feedback

**v7.0 current:** Only teaching mode. No exam simulation.

**Impact:** LOW for initial MVP, MEDIUM after first month (students will ask for exam practice).

**Fix needed:** Add EXAM_PRACTICE session type:
- Timer per question
- No hints available
- Strict evaluation
- Score at end with comparison to previous attempts
- "Mock test" feel

---

### ❌ GAP 10: Accent & Speech Handling
**Vision (§9):** "Never misinterpret pronunciation as ignorance. Confirm unclear speech gently."

**v7.0 current:** Low STT confidence → "Ek baar phir boliye?" 
But doesn't handle regional accent patterns. Doesn't confirm numerical answers 
("Mujhe 'teen' suna — aapne 3 bola ya 13?")

**Impact:** MEDIUM. Nizamabad students will have Telugu-accented Hindi. 
Whisper may garble this.

**Fix needed:**
- Context-aware number disambiguation (already in DESIGN_DECISIONS.md but not coded)
- When STT confidence is 0.4-0.6 (marginal), repeat back what was heard before evaluating:
  "Mujhe aisa laga aapne [X] bola. Sahi hai?"

---

## WHAT v7.0 HAS THAT THE VISION DOESN'T MENTION

### ➕ DISPUTE_REPLAY State
v7.0 handles student challenging Didi's verdict ("maine sahi bola").
Vision doc doesn't mention this. Good addition — STT errors are real.

### ➕ Response Enforcer (7 Rules, Code-Level)
v7.0 enforces word count, false praise, specificity, teach+question split, 
language match, TTS safety, repetition — all in Python, not prompts.
Vision mentions "Teacher Policy Layer" but doesn't specify enforcement mechanism.
v7.0's enforcer is more robust.

### ➕ Parent INSTRUCTION State
v7.0: Parent can tell Didi "kal fractions pe zyada dhyan dena" and it biases next session.
Vision mentions parent reporting but not parent-driven teaching directives.
This is a moat feature.

### ➕ Provider Abstraction (swap STT/TTS/LLM via config)
v7.0: One line to swap Groq Whisper → Sarvam Saaras.
Vision mentions providers but doesn't specify abstraction layer.

### ➕ Homework OCR Integration
v7.0: Student photographs homework → GPT-4o Vision extracts questions.
Vision mentions "doubt clarification" but not homework photo capture.

### ➕ Answer Variants (Hindi spoken numbers)
v7.0: "minus ek tihaayi" = -1/3, "sunya" = 0, "aadha" = 1/2
Vision doesn't go into this level of implementation detail.

---

## PRIORITY FIX ORDER (What to add to v7.0 next)

| Priority | Gap | Impact | Effort | When |
|----------|-----|--------|--------|------|
| P0 | GAP 7: Silence handling | HIGH | LOW (frontend event) | Week 1 |
| P1 | GAP 2: Full 8-step learning loop | HIGH | MEDIUM | Week 2-3 |
| P1 | GAP 1: Session modes (revision/exam) | HIGH | MEDIUM | Week 3-4 |
| P2 | GAP 3: Student persona detection | MEDIUM | MEDIUM | Month 2 |
| P2 | GAP 6: Confidence calibration | MEDIUM | LOW | Month 2 |
| P2 | GAP 10: Accent handling | MEDIUM | LOW | Month 2 |
| P3 | GAP 4: Regional behavior profiles | MEDIUM | MEDIUM | Phase 2 |
| P3 | GAP 5: Regional example bank | LOW | LOW | Phase 2 |
| P3 | GAP 9: Exam practice mode | LOW-MED | MEDIUM | Phase 2 |
| P4 | GAP 8: Board-agnostic curriculum | LOW (MVP) | HIGH | Phase 3 |

---

## SUMMARY

The vision document is strategically brilliant. It captures India's educational reality 
at a depth that most EdTech companies miss entirely. The regional behavior modulation, 
student persona framework, and insistence on "teacher behavior > model size" are exactly right.

v7.0 implements the operational core correctly:
- Voice pipeline ✅
- State machine (Brain Router) ✅
- Answer checking (deterministic math) ✅
- Response enforcement (Teacher Policy Layer) ✅
- Parent voice layer ✅
- Phased execution ✅

The 10 gaps are real but ordered. P0 (silence handling) and P1 (learning loop, session modes) 
should be addressed before the pilot. P2-P4 are Phase 2+ improvements that become critical 
at scale but don't block the Nizamabad 50-student pilot.

The biggest philosophical alignment: both documents agree that 
**behavioral correctness matters more than model sophistication.**
v7.0's enforcer.py is the code manifestation of that principle.
