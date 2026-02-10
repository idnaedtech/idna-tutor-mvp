# IDNA Simplified Agentic Tutor
# ==============================
# Cherry-picked from TEACHER_SPEC + AGENTIC_SPEC
# Designed for rapid implementation

---

## CORE PRINCIPLE

```
Python DECIDES correctness + ENFORCES rules
LLM REASONS about teaching moves + GENERATES speech
```

---

## ARCHITECTURE (Simplified)

```
Student speaks
    │
    ▼
┌─────────────────────────────────────────────────┐
│  1. Whisper STT → text                          │
│  2. Python: Check off-topic/stop/idk FIRST      │
│  3. Python: If answer attempt → evaluate()      │
│  4. Build context packet (with eval result)     │
│  5. Call GPT-4o-mini with 6 tools               │
│  6. Guardrails check → override if needed       │
│  7. Execute tool → generate speech              │
│  8. TTS → student hears response                │
└─────────────────────────────────────────────────┘
```

**Key insight:** Evaluation happens BEFORE the agent call, not as a tool.
This prevents the agent from making correctness decisions.

---

## THE 6 TOOLS (Down from 11)

```python
TUTOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "give_hint",
            "description": "Give a hint. Level 1 = conceptual nudge. Level 2 = show first step. NEVER reveal the answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hint_level": {
                        "type": "integer",
                        "enum": [1, 2]
                    },
                    "what_student_got_wrong": {
                        "type": "string",
                        "description": "Specifically what the student misunderstood, referencing their answer"
                    }
                },
                "required": ["hint_level", "what_student_got_wrong"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "praise_and_continue",
            "description": "Praise correct answer with specificity, then move to next question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "what_they_did_well": {
                        "type": "string",
                        "description": "Specific thing student did right (e.g., 'found LCM quickly', 'remembered to simplify')"
                    }
                },
                "required": ["what_they_did_well"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "explain_solution",
            "description": "Walk through the full solution. ONLY after 2 hints failed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "style": {
                        "type": "string",
                        "enum": ["step_by_step", "analogy"],
                        "description": "How to explain"
                    }
                },
                "required": ["style"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "encourage_attempt",
            "description": "Student said 'I don't know' or seems stuck. Encourage without giving answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "approach": {
                        "type": "string",
                        "enum": ["break_down", "relate_to_known", "reduce_pressure"],
                        "description": "How to encourage"
                    }
                },
                "required": ["approach"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "redirect_to_question",
            "description": "Student went off-topic. Gently bring back to the math question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "style": {
                        "type": "string",
                        "enum": ["gentle", "direct"]
                    }
                },
                "required": ["style"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "end_session",
            "description": "Wrap up the tutoring session with a summary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "enum": ["completed_questions", "student_requested", "time_limit"]
                    }
                },
                "required": ["reason"]
            }
        }
    }
]
```

**What we removed:**
- `evaluate_response` → Python does this BEFORE agent call
- `ask_question` → Automatic after praise_and_continue
- `probe_understanding` → Phase 2 feature
- `transition_to_next` → Merged into praise_and_continue
- `speak_to_student` → Forces agent to use specific tools

---

## CONTEXT PACKET (What the Agent Sees)

```python
def build_context(session: dict, student_input: str, eval_result: dict) -> str:
    """
    Build context AFTER evaluation is done.
    The agent sees the result, not the correct answer.
    """
    q = session['current_question']

    # Evaluation result (computed by Python, not agent)
    if eval_result:
        eval_section = f"""
### Evaluation Result (computed by system)
- Student said: "{student_input}"
- Correct: {eval_result['correct']}
- Is off-topic: {eval_result['is_offtopic']}
- Is "I don't know": {eval_result['is_idk']}
"""
    else:
        eval_section = f"""
### Student Said
"{student_input}"
"""

    return f"""## CURRENT TEACHING SITUATION

### Session
- Student: {session['student_name']} (Class 8)
- Chapter: {session['chapter']}
- Questions done: {session['questions_completed']}/{session['total_questions']}
- Score: {session['score']}/{session['questions_completed']}

### Current Question
- Question: {q['question_text']}
- Topic: {q['topic']}
- Hints given: {session['hint_count']}/2
- Attempts: {session['attempt_count']}

{eval_section}

### Hint Directions (DO NOT reveal to student)
- Hint 1: {q['hint_1_direction']}
- Hint 2: {q['hint_2_direction']}

### Rules
- If correct → use praise_and_continue
- If wrong + hints < 2 → use give_hint
- If wrong + hints >= 2 → use explain_solution
- If "I don't know" → use encourage_attempt (NEVER give answer)
- If off-topic → use redirect_to_question
- Max 2 sentences. This is spoken aloud.
- Reference what the student specifically said.
"""
```

**Key change:** Evaluation result is IN the context. Agent doesn't decide correctness — it's told.

---

## SYSTEM PROMPT (Concise)

```python
SYSTEM_PROMPT = """You are Didi, a warm Indian math teacher tutoring a Class 8 student.

TEACHING STYLE:
- You LEAD. Student doesn't control the lesson.
- You NEVER give answers easily. Hints first, always.
- You reference what the student SPECIFICALLY said.
- You use Hindi-English naturally: "Bahut accha!", "Chalo next question"

VOICE RULES:
- Max 2 sentences (this is spoken aloud)
- No formatting (no bullets, bold, or headers)
- Use contractions (let's, you're, that's)

DECISION RULES:
- Look at the Evaluation Result in the context
- If correct → praise_and_continue
- If wrong → give_hint (level based on hint count)
- If stuck after 2 hints → explain_solution
- If "I don't know" → encourage_attempt
- If off-topic → redirect_to_question

BANNED:
- "Great job!" (too generic)
- "Incorrect" or "Wrong" (too harsh)
- Revealing answer in hints
"""
```

---

## GUARDRAILS (Python Overrides)

```python
def check_guardrails(tool_name: str, args: dict, session: dict) -> dict:
    """
    Override agent decisions that violate rules.
    Returns: {"blocked": bool, "override_tool": str, "override_args": dict}
    """
    result = {"blocked": False, "override_tool": None, "override_args": None}

    # GUARDRAIL 1: Can't explain without hints first
    if tool_name == "explain_solution" and session['hint_count'] < 2:
        result["blocked"] = True
        result["override_tool"] = "give_hint"
        result["override_args"] = {
            "hint_level": session['hint_count'] + 1,
            "what_student_got_wrong": "Need to give hint before explanation"
        }

    # GUARDRAIL 2: Can't skip hint level 1
    if tool_name == "give_hint" and args.get("hint_level") == 2 and session['hint_count'] == 0:
        args["hint_level"] = 1

    # GUARDRAIL 3: Session time limit (25 min)
    if session['duration_minutes'] >= 25 and tool_name != "end_session":
        result["blocked"] = True
        result["override_tool"] = "end_session"
        result["override_args"] = {"reason": "time_limit"}

    # GUARDRAIL 4: Max 5 attempts per question
    if session['attempt_count'] >= 5 and tool_name not in ["explain_solution", "end_session", "praise_and_continue"]:
        result["blocked"] = True
        result["override_tool"] = "explain_solution"
        result["override_args"] = {"style": "step_by_step"}

    return result
```

---

## THE MAIN LOOP

```python
class SimplifiedAgenticTutor:
    def __init__(self, student_name: str, chapter: str):
        self.client = openai.OpenAI()
        self.session = self._init_session(student_name, chapter)

    async def process_input(self, student_input: str) -> str:
        """
        Main entry point. Returns text to speak.
        """
        # Step 1: Pre-checks (Python, not agent)
        student_input = student_input.strip()

        # Check for stop request
        if self._is_stop_request(student_input):
            return await self._handle_end_session("student_requested")

        # Check for off-topic (but not if it contains a number)
        is_offtopic = self._is_offtopic(student_input)

        # Check for IDK
        is_idk = self._is_idk(student_input)

        # Step 2: Evaluate answer (Python, not agent)
        eval_result = None
        if not is_offtopic and not is_idk and student_input:
            eval_result = evaluate_answer(
                student_input,
                self.session['current_question']['answer'],
                self.session['current_question']['answer_type']
            )
            eval_result['is_offtopic'] = False
            eval_result['is_idk'] = False
            self.session['attempt_count'] += 1
        elif is_offtopic:
            eval_result = {'correct': False, 'is_offtopic': True, 'is_idk': False}
        elif is_idk:
            eval_result = {'correct': False, 'is_offtopic': False, 'is_idk': True}

        # Step 3: Build context with eval result
        context = build_context(self.session, student_input, eval_result)

        # Step 4: Call agent
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context}
            ],
            tools=TUTOR_TOOLS,
            tool_choice="required",
            max_tokens=150,
            temperature=0.7
        )

        # Step 5: Process tool call
        tool_call = response.choices[0].message.tool_calls[0]
        tool_name = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments)

        # Step 6: Apply guardrails
        guardrail = check_guardrails(tool_name, tool_args, self.session)
        if guardrail["blocked"]:
            tool_name = guardrail["override_tool"]
            tool_args = guardrail["override_args"]

        # Step 7: Execute tool
        speech = await self._execute_tool(tool_name, tool_args, student_input, eval_result)

        # Step 8: Update history
        self.session['history'].append({
            "student": student_input,
            "teacher": speech,
            "tool": tool_name
        })

        return speech

    async def _execute_tool(self, tool_name: str, args: dict, student_input: str, eval_result: dict) -> str:
        """Execute the tool and generate speech."""

        if tool_name == "give_hint":
            return await self._give_hint(args, student_input)

        elif tool_name == "praise_and_continue":
            return await self._praise_and_continue(args, student_input)

        elif tool_name == "explain_solution":
            return await self._explain_solution(args)

        elif tool_name == "encourage_attempt":
            return await self._encourage_attempt(args)

        elif tool_name == "redirect_to_question":
            return await self._redirect(args)

        elif tool_name == "end_session":
            return await self._handle_end_session(args.get("reason", "completed"))

        return "Let's continue with our question."

    async def _give_hint(self, args: dict, student_input: str) -> str:
        """Generate a hint without revealing the answer."""
        level = args.get("hint_level", 1)
        misconception = args.get("what_student_got_wrong", "")
        q = self.session['current_question']

        self.session['hint_count'] = max(self.session['hint_count'], level)

        speech = self._generate_speech(
            f"You are a math teacher giving a hint. Student said: '{student_input}'. "
            f"Their misconception: {misconception}. "
            f"Hint direction: {q[f'hint_{level}_direction']}. "
            f"Give a level {level} hint. Reference their specific answer. "
            f"Do NOT reveal the answer. Max 2 sentences."
        )
        return speech

    async def _praise_and_continue(self, args: dict, student_input: str) -> str:
        """Praise and move to next question."""
        strength = args.get("what_they_did_well", "good thinking")

        # Update score
        self.session['score'] += 1
        self.session['questions_completed'] += 1

        # Generate praise
        praise = self._generate_speech(
            f"Student answered: '{student_input}'. "
            f"They did well: {strength}. "
            f"Give brief specific praise (1 sentence). No generic 'Great job!'."
        )

        # Move to next question
        self.session['current_question_index'] += 1
        if self.session['current_question_index'] < len(self.session['questions']):
            self.session['current_question'] = self.session['questions'][self.session['current_question_index']]
            self.session['hint_count'] = 0
            self.session['attempt_count'] = 0

            next_q = self.session['current_question']['question_text']
            return f"{praise} Chalo, next question. {next_q}"
        else:
            return await self._handle_end_session("completed_questions")

    async def _explain_solution(self, args: dict) -> str:
        """Full solution walkthrough."""
        q = self.session['current_question']
        style = args.get("style", "step_by_step")

        self.session['questions_completed'] += 1

        speech = self._generate_speech(
            f"Explain the solution to: {q['question_text']}. "
            f"Answer: {q['answer']}. "
            f"Steps: {q['solution_steps']}. "
            f"Style: {style}. Be kind. Max 4 sentences."
        )

        # Move to next
        self.session['current_question_index'] += 1
        if self.session['current_question_index'] < len(self.session['questions']):
            self.session['current_question'] = self.session['questions'][self.session['current_question_index']]
            self.session['hint_count'] = 0
            self.session['attempt_count'] = 0
            next_q = self.session['current_question']['question_text']
            return f"{speech} Chalo, let's try another. {next_q}"
        else:
            return await self._handle_end_session("completed_questions")

    async def _encourage_attempt(self, args: dict) -> str:
        """Encourage student who said IDK."""
        approach = args.get("approach", "break_down")
        q = self.session['current_question']

        speech = self._generate_speech(
            f"Student said they don't know. Question: {q['question_text']}. "
            f"Approach: {approach}. "
            f"Encourage them to try. Do NOT give the answer. "
            f"Max 2 sentences."
        )
        return speech

    async def _redirect(self, args: dict) -> str:
        """Redirect off-topic student."""
        style = args.get("style", "gentle")
        q = self.session['current_question']

        speech = self._generate_speech(
            f"Student went off-topic. Redirect {style}ly back to: {q['question_text']}. "
            f"Max 2 sentences."
        )
        return speech

    async def _handle_end_session(self, reason: str) -> str:
        """End session with summary."""
        s = self.session
        speech = self._generate_speech(
            f"End tutoring session. Reason: {reason}. "
            f"Score: {s['score']}/{s['questions_completed']}. "
            f"Duration: {s['duration_minutes']} minutes. "
            f"Give warm summary. 2-3 sentences."
        )
        return speech

    def _generate_speech(self, instruction: str) -> str:
        """Generate spoken words via LLM."""
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Generate natural spoken Hindi-English teacher speech. No formatting. Short sentences."},
                {"role": "user", "content": instruction}
            ],
            max_tokens=80,
            temperature=0.7
        )
        text = response.choices[0].message.content.strip()
        # Remove any formatting
        text = text.replace("*", "").replace("#", "").replace("- ", "")
        return text

    def _is_stop_request(self, text: str) -> bool:
        stop_phrases = ["stop", "bye", "quit", "end", "done", "that's it", "the end"]
        return any(p in text.lower() for p in stop_phrases)

    def _is_offtopic(self, text: str) -> bool:
        # Don't mark as off-topic if it contains numbers
        if any(c.isdigit() for c in text):
            return False
        offtopic = ["who are you", "what is your name", "tell me a joke", "play a game", "sing"]
        return any(p in text.lower() for p in offtopic)

    def _is_idk(self, text: str) -> bool:
        idk = ["i don't know", "idk", "no idea", "tell me", "skip", "i cant", "nahi pata"]
        return any(p in text.lower() for p in idk)

    def _init_session(self, student_name: str, chapter: str) -> dict:
        questions = load_questions_for_chapter(chapter)
        return {
            "student_name": student_name,
            "chapter": chapter,
            "questions": questions,
            "current_question": questions[0],
            "current_question_index": 0,
            "total_questions": len(questions),
            "questions_completed": 0,
            "score": 0,
            "hint_count": 0,
            "attempt_count": 0,
            "history": [],
            "duration_minutes": 0,
            "start_time": time.time()
        }

    async def start_session(self) -> str:
        """Initial greeting + first question."""
        q = self.session['current_question']
        return f"Hi {self.session['student_name']}! Let's practice {self.session['chapter']}. Here's your first question: {q['question_text']}"
```

---

## FILES TO CREATE

```
idna/
├── agentic_tutor.py      # SimplifiedAgenticTutor class (above)
├── tutor_tools.py        # TUTOR_TOOLS list
├── tutor_prompts.py      # SYSTEM_PROMPT
├── guardrails.py         # check_guardrails()
├── context_builder.py    # build_context()
├── evaluator.py          # KEEP existing (answer checking)
├── questions.py          # KEEP existing (update format if needed)
├── web_server.py         # UPDATE to use SimplifiedAgenticTutor
└── web/index.html        # KEEP existing
```

---

## WHAT WE KEPT

- Evaluation in Python (not LLM)
- Guardrails layer
- Context packet with full situation
- tool_choice="required"
- Specificity rule (reference student's answer)
- Hindi-English code-mixing

## WHAT WE SIMPLIFIED

- 6 tools instead of 11
- No separate TEACHER_SPEC phase
- Evaluation happens BEFORE agent call
- praise_and_continue auto-advances to next question
- No probe_understanding (Phase 2)
- No complex state machine

---

## TESTING CHECKLIST

- [ ] Correct answer → praise + next question
- [ ] Wrong answer → hint 1 (answer not revealed)
- [ ] Wrong again → hint 2 (first step only)
- [ ] Wrong after 2 hints → explain full solution
- [ ] "I don't know" → encouragement (never answer)
- [ ] Off-topic → gentle redirect
- [ ] Stop request → session summary
- [ ] Guardrail blocks explain_solution before 2 hints
- [ ] Speech references student's specific answer
- [ ] Max 2 sentences per response
- [ ] No formatting in output
