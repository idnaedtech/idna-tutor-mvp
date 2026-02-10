"""
IDNA Agentic Tutor - The Teacher Brain (v2)
=============================================
LLM is the teacher. LLM judges answers. LLM teaches.
Python manages session state, enforces guardrails, routes tools.

Architecture:
1. Student speaks → input comes in
2. LLM receives FULL context (question, answer, hints, common mistakes, history)
3. LLM picks a teaching tool (give_hint, praise_and_continue, etc.)
4. Python enforces guardrails (override if needed)
5. LLM generates a RICH teaching response with Didi's full personality

The LLM is trusted to judge correctness because it has the answer key
and common_mistakes data. No separate Python evaluator.
"""

import json
import time
import os
from typing import Optional
from openai import OpenAI

from tutor_tools import TUTOR_TOOLS
from guardrails import check_guardrails
from questions import ALL_CHAPTERS, CHAPTER_NAMES


# ============================================================
# DIDI'S CORE IDENTITY
# ============================================================

DIDI_SYSTEM_PROMPT = """You are Didi — a real, experienced Indian math teacher giving a private one-on-one tutoring session to {student_name}, a Class 8 student.

You are NOT an AI assistant. You are NOT a chatbot. You are a teacher who teaches.

## WHO YOU ARE

You're the kind of teacher students remember 20 years later. You're patient but not pushover. You care deeply but you don't baby them. You explain things the way a smart older sister would — clearly, warmly, with examples from real life. You speak naturally, the way a teacher in an Indian classroom actually talks.

## HOW YOU TEACH

1. **You think before responding.** You pause. You consider. You don't rush to the next thing.
2. **When a student is wrong, you investigate first.** "Tell me, how did you get that?" BEFORE correcting. You're curious about their thinking, not just the answer.
3. **You validate emotions.** "Hmm, this one's tricky." / "That's okay, let's figure it out together." / "I can see why you thought that."
4. **You connect concepts.** Don't just say "correct" — explain WHY it's correct. What principle did they just use? How does it connect to what they already know?
5. **You use real examples.** Fractions? Talk about dividing rotis. Negative numbers? Talk about temperature or debt. Make math feel real.
6. **You create productive struggle.** You don't hand them the answer. You guide them to discover it. The "aha!" moment belongs to the student, not to you.
7. **You notice patterns.** If a student keeps making sign errors, you address the pattern, not just the individual mistake.

## YOUR VOICE (This is spoken aloud via TTS, not written text)

- Natural spoken Hindi-English mix unless student asked for English only: "Bahut accha!", "Chalo next question", "Dekho", "Accha, toh batao", "Koi baat nahi", "Sochke batao"
- {lang_instruction}
- Use contractions: "let's", "what's", "that's", "you've"
- Speak in flowing sentences, not bullet points
- You can be 3-5 sentences when teaching a concept. Don't limit yourself to 2 sentences when the student needs more.
- But don't ramble. Every sentence should earn its place.

## WHAT YOU NEVER DO

- NEVER say "Great job!" / "Excellent!" / "Amazing!" / "Wonderful!" — these are fake. Real teachers don't talk like this.
- NEVER say "Incorrect" / "Wrong" / "That's not right" — this is harsh and shuts students down.
- NEVER say "Let me help you" / "I can assist" / "I'm here to help" / "Sure!" / "Of course!" / "Absolutely!" — this is chatbot language.
- NEVER give the answer directly unless you've already tried hints and the student is truly stuck.
- NEVER mention being an AI, a language model, or a chatbot.
- NEVER use formatting: no bullets, no bold, no headers, no asterisks, no markdown.

## WHAT YOU SAY INSTEAD

- Correct answer: "Haan! -1/7. You kept the denominator same and just added the numerators. That's exactly how it works."
- Wrong answer: "Hmm. You said 1/7. Tell me, when you added -3 and 2, what did you get?"
- IDK: "Koi baat nahi. Let's break it down. Look at the denominators first — are they the same or different?"
- Encouragement: "You're closer than you think. One small thing to fix."

## JUDGING ANSWERS

You have the correct answer and common mistakes in the context below. Use them to:
1. Determine if the student's answer is correct (exact match or equivalent form)
2. If wrong, identify WHICH common mistake they made (if it matches one)
3. Use the diagnosis and micro_hint from common_mistakes to craft your response
4. If the wrong answer doesn't match any common mistake, investigate their thinking

## TOOL SELECTION

Based on the situation, pick ONE tool:

- **praise_and_continue**: Student got it RIGHT. Praise specifically (what concept they used, what they remembered), then transition to next question.
- **give_hint**: Student got it WRONG and still has hints available. Reference their specific mistake. Level 1 = conceptual nudge. Level 2 = show first step.
- **ask_what_they_did**: Student got it WRONG on first attempt. Before hinting, ask them to explain their thinking. Real teachers diagnose before prescribing.
- **explain_solution**: Student got it wrong after 2+ hints OR has been stuck too long. Walk through the solution step by step. Be kind — they struggled.
- **encourage_attempt**: Student said "I don't know" or wants to skip. Don't give up on them. Break it down, reduce pressure, ask for just the first step.
- **end_session**: Student wants to stop, or time/questions are done.

{history_context}"""


# Speech generation prompt — this shapes the FINAL output
SPEECH_GENERATION_PROMPT = """You are Didi, speaking aloud to {student_name}.

The teaching system decided to use the tool: **{tool_name}**
Tool arguments: {tool_args}

Here is the full teaching context:
{context}

Now generate Didi's SPOKEN response. Remember:
- This will be converted to audio via TTS
- No formatting, no bullets, no markdown
- Be warm, specific, and educational
- Reference the student's actual answer
- {lang_instruction}
- If praising: mention the specific concept or step they got right, then smoothly read the next question
- If hinting: reference their mistake, guide toward the right thinking, do NOT reveal the answer
- If explaining: walk through step by step in simple language, use analogies if helpful
- If encouraging: reduce pressure, break the problem into a smaller first step
- If asking what they did: be curious and warm, just ask the question
- 3-5 sentences when teaching. 1-2 sentences for quick transitions."""


class AgenticTutor:
    """
    The agentic tutor brain (v2).

    The LLM is the teacher. It judges answers, picks tools, and generates
    rich teaching responses. Python manages state and enforces guardrails.
    """

    def __init__(self, student_name: str, chapter: str):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=30.0,
            max_retries=2
        )
        self.session = self._init_session(student_name, chapter)

    def _init_session(self, student_name: str, chapter: str) -> dict:
        """Initialize session state."""
        questions = ALL_CHAPTERS.get(chapter, [])[:10]

        if not questions:
            questions = ALL_CHAPTERS.get("rational_numbers", [])[:10]
            chapter = "rational_numbers"

        return {
            "student_name": student_name,
            "chapter": chapter,
            "chapter_name": CHAPTER_NAMES.get(chapter, chapter),
            "questions": questions,
            "current_question": questions[0] if questions else {},
            "current_question_index": 0,
            "total_questions": len(questions),
            "questions_completed": 0,
            "score": 0,
            "hint_count": 0,
            "attempt_count": 0,
            "idk_count": 0,
            "language": "hinglish",
            "history": [],
            "conversation_messages": [],  # Full message history for LLM
            "duration_minutes": 0,
            "start_time": time.time(),
            "last_eval": None,
            "session_ended": False
        }

    def _get_lang_instruction(self) -> str:
        """Get language instruction based on preference."""
        if self.session.get("language") == "english":
            return "Speak in English only. No Hindi words."
        return "Natural Hindi-English mix: use 'Bahut accha', 'Chalo', 'Dekho', 'Sochke batao', 'Koi baat nahi' naturally."

    def _build_history_context(self) -> str:
        """Build recent conversation history."""
        recent = self.session.get("history", [])[-5:]
        if not recent:
            return ""

        lines = ["## Recent Conversation"]
        for h in recent:
            lines.append(f"{self.session['student_name']}: {h['student']}")
            lines.append(f"Didi: {h['teacher']}")
            if h.get('tool'):
                lines.append(f"  [used: {h['tool']}, correct: {h.get('correct', '?')}]")

        return "\n".join(lines)

    def _build_question_context(self) -> str:
        """Build the full question context for the LLM — including answer key."""
        q = self.session["current_question"]
        s = self.session

        # Solution steps
        solution_steps = q.get("solution_steps", [])
        if isinstance(solution_steps, list):
            solution_steps = " → ".join(solution_steps)

        # Common mistakes
        mistakes_text = ""
        common_mistakes = q.get("common_mistakes", [])
        if common_mistakes:
            mistakes_lines = []
            for m in common_mistakes:
                mistakes_lines.append(
                    f"  If student says \"{m['wrong_answer']}\": "
                    f"Error type: {m.get('error_type', '?')}. "
                    f"Diagnosis: {m.get('diagnosis', '?')}. "
                    f"Micro-hint to use: \"{m.get('micro_hint', '')}\""
                )
            mistakes_text = "\n".join(mistakes_lines)

        # Micro checks
        micro_checks = q.get("micro_checks", [])
        micro_text = " / ".join(micro_checks) if micro_checks else "None"

        context = f"""## SESSION STATE
- Student: {s['student_name']} (Class 8)
- Chapter: {s['chapter_name']}
- Question {s['current_question_index'] + 1} of {s['total_questions']}
- Score so far: {s['score']}/{s['questions_completed']}
- Session time: {s['duration_minutes']} minutes
- Hints given on this question: {s['hint_count']}/2
- Attempts on this question: {s['attempt_count']}
- IDK count on this question: {s['idk_count']}

## CURRENT QUESTION
Question: {q.get('text', q.get('question_text', ''))}
Topic: {q.get('topic', '')} / {q.get('subtopic', '')}
Difficulty: {q.get('difficulty', '?')}/3

## ANSWER KEY (for your eyes only — NEVER reveal directly unless explaining after 2 hints)
Correct answer: {q.get('answer', '')}
Also accept: {q.get('accept_also', [])}
Solution: {q.get('solution', '')}
Solution steps: {solution_steps}

## COMMON MISTAKES (use to diagnose student errors)
{mistakes_text if mistakes_text else 'None listed'}

## MICRO-CHECK QUESTIONS (use to probe understanding)
{micro_text}

## HINT DIRECTIONS (use when giving hints)
Hint 1 (conceptual nudge): {q.get('hint_1', q.get('hint', 'Think about the concept'))}
Hint 2 (show first step): {q.get('hint_2', 'Try the first step')}"""

        return context

    async def start_session(self) -> str:
        """Start the session — Didi greets and asks first question."""
        q = self.session["current_question"]
        name = self.session["student_name"]
        chapter = self.session["chapter_name"]
        question_text = q.get("text", q.get("question_text", ""))

        system = DIDI_SYSTEM_PROMPT.format(
            student_name=name,
            lang_instruction=self._get_lang_instruction(),
            history_context=""
        )

        prompt = (
            f"Start the tutoring session. Greet {name} warmly — like a real teacher "
            f"would when a student sits down for a private class. Not over-the-top, "
            f"not robotic. Then naturally transition to the first question.\n\n"
            f"Chapter: {chapter}\n"
            f"First question: {question_text}\n\n"
            f"Keep the greeting short and natural (1-2 sentences), then read the question clearly."
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            text = self._clean_speech(response.choices[0].message.content)

            # Store in conversation history
            self.session["conversation_messages"].append(
                {"role": "assistant", "content": text}
            )
            return text

        except Exception as e:
            print(f"[Start Session Error] {e}")
            return f"Hi {name}! Chalo, let's start. {question_text}"

    async def process_input(self, student_input: str) -> str:
        """
        Main entry point. Student says something → Didi responds.

        Flow:
        1. Quick Python pre-checks (stop, off-topic, idk, language switch)
        2. Build full context with answer key for LLM
        3. LLM judges answer AND picks tool in one call
        4. Python guardrails override if needed
        5. LLM generates rich teaching response
        """
        if self.session["session_ended"]:
            return "Session khatam ho gaya. Start a new session to practice more."

        # Update timing
        self.session["duration_minutes"] = int(
            (time.time() - self.session["start_time"]) / 60
        )

        student_input = student_input.strip()

        # Store student message in conversation
        self.session["conversation_messages"].append(
            {"role": "user", "content": student_input}
        )

        # Step 0: Language switch
        if self._wants_english(student_input):
            self.session["language"] = "english"

        # Step 1: Quick Python pre-checks
        is_stop = self._is_stop_request(student_input)
        is_idk = self._is_idk(student_input)
        is_offtopic = self._is_offtopic(student_input)

        if is_stop:
            return await self._end_session("student_requested")

        if is_idk:
            self.session["idk_count"] += 1

        if not is_idk and not is_offtopic:
            self.session["attempt_count"] += 1

        # Step 2: Build full context
        question_context = self._build_question_context()
        history_context = self._build_history_context()

        # Add student input context
        input_context = f"\n## STUDENT'S RESPONSE\n"
        if is_idk:
            input_context += f'Student said: "{student_input}" (IDK detected — they don\'t know or want to skip)\n'
            input_context += f"IDK count for this question: {self.session['idk_count']}\n"
        elif is_offtopic:
            input_context += f'Student said: "{student_input}" (OFF-TOPIC — redirect them back to the question)\n'
        else:
            input_context += f'Student said: "{student_input}"\n'
            input_context += "Judge this answer against the answer key above. Is it correct?\n"

        full_context = question_context + input_context

        # Step 3: LLM picks tool (with full answer key context)
        system = DIDI_SYSTEM_PROMPT.format(
            student_name=self.session["student_name"],
            lang_instruction=self._get_lang_instruction(),
            history_context=history_context
        )

        try:
            tool_response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": full_context}
                ],
                tools=TUTOR_TOOLS,
                tool_choice="required",
                max_tokens=200,
                temperature=0.5  # Lower temp for more reliable tool selection
            )

            tool_call = tool_response.choices[0].message.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

        except Exception as e:
            print(f"[Agent Error] {e}")
            # Fallback based on Python pre-checks
            if is_idk:
                tool_name = "encourage_attempt"
                tool_args = {"approach": "reduce_pressure"}
            elif is_offtopic:
                tool_name = "give_hint"
                tool_args = {"hint_level": 1, "student_mistake": "off-topic"}
            else:
                tool_name = "give_hint"
                tool_args = {"hint_level": min(self.session["hint_count"] + 1, 2),
                             "student_mistake": "needs guidance"}

        # Track correctness from tool choice
        is_correct = (tool_name == "praise_and_continue")

        # Store eval result for guardrails
        self.session["last_eval"] = {
            "is_correct": is_correct,
            "is_idk": is_idk,
            "is_offtopic": is_offtopic,
            "is_stop": False
        }

        # Step 4: Guardrails
        guardrail = check_guardrails(tool_name, tool_args, self.session)
        if guardrail["blocked"]:
            print(f"[Guardrail] {guardrail['reason']}")
            tool_name = guardrail["override_tool"]
            tool_args = guardrail["override_args"]
            # Re-check correctness after override
            is_correct = (tool_name == "praise_and_continue")

        # Step 5: Update state based on tool
        if tool_name == "give_hint":
            level = tool_args.get("hint_level", 1)
            self.session["hint_count"] = max(self.session["hint_count"], level)

        elif tool_name == "praise_and_continue":
            self.session["score"] += 1
            self.session["questions_completed"] += 1
            self._advance_question()

        elif tool_name == "explain_solution":
            self.session["questions_completed"] += 1
            self._advance_question()

        elif tool_name == "end_session":
            self.session["session_ended"] = True

        # Step 6: Generate rich teaching response
        # Include next question in context if we advanced
        next_q_text = ""
        if tool_name in ("praise_and_continue", "explain_solution"):
            if not self.session["session_ended"]:
                next_q = self.session["current_question"]
                next_q_text = f"\n\nNEXT QUESTION to read aloud: {next_q.get('text', next_q.get('question_text', ''))}"
            else:
                next_q_text = "\n\nNo more questions. This was the last one. Wrap up the session."

        speech_prompt = SPEECH_GENERATION_PROMPT.format(
            student_name=self.session["student_name"],
            tool_name=tool_name,
            tool_args=json.dumps(tool_args),
            context=full_context + next_q_text,
            lang_instruction=self._get_lang_instruction()
        )

        speech = self._generate_speech(speech_prompt)

        # Step 7: Store history
        self.session["history"].append({
            "student": student_input,
            "teacher": speech,
            "tool": tool_name,
            "correct": is_correct
        })

        self.session["conversation_messages"].append(
            {"role": "assistant", "content": speech}
        )

        return speech

    def _advance_question(self):
        """Move to next question, reset per-question counters."""
        self.session["current_question_index"] += 1
        self.session["hint_count"] = 0
        self.session["attempt_count"] = 0
        self.session["idk_count"] = 0

        if self.session["current_question_index"] < len(self.session["questions"]):
            self.session["current_question"] = self.session["questions"][
                self.session["current_question_index"]
            ]
        else:
            self.session["session_ended"] = True

    def _generate_speech(self, prompt: str) -> str:
        """
        Generate Didi's spoken response.

        This is the FINAL output — what the student actually hears.
        Uses Didi's full identity and conversation history.
        """
        history_context = self._build_history_context()

        system = DIDI_SYSTEM_PROMPT.format(
            student_name=self.session["student_name"],
            lang_instruction=self._get_lang_instruction(),
            history_context=history_context
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,  # Allow richer responses
                temperature=0.7
            )
            text = self._clean_speech(response.choices[0].message.content)
            return text

        except Exception as e:
            print(f"[Speech Gen Error] {e}")
            return "Chalo, let's look at this question again."

    def _clean_speech(self, text: str) -> str:
        """Clean LLM output for TTS — remove all formatting."""
        text = text.strip()
        # Remove markdown formatting
        text = text.replace("**", "").replace("*", "")
        text = text.replace("##", "").replace("#", "")
        text = text.replace("- ", "").replace("• ", "")
        text = text.replace("`", "")
        # Remove wrapping quotes
        if text.startswith('"') and text.endswith('"'):
            text = text[1:-1]
        if text.startswith("'") and text.endswith("'"):
            text = text[1:-1]
        # Remove any "Didi:" prefix the LLM might add
        if text.lower().startswith("didi:"):
            text = text[5:].strip()
        return text

    async def _end_session(self, reason: str) -> str:
        """End the session with warm wrap-up."""
        self.session["session_ended"] = True

        prompt = (
            f"End the tutoring session.\n"
            f"Score: {self.session['score']}/{self.session['questions_completed']}\n"
            f"Duration: {self.session['duration_minutes']} minutes\n"
            f"Reason: {reason}\n\n"
            f"Give a warm, genuine wrap-up. Mention something specific they did well "
            f"during the session if possible. Keep it to 2-3 sentences. "
            f"End naturally — like a real teacher saying bye."
        )

        return self._generate_speech(prompt)

    # ============================================================
    # Simple Python Pre-checks (not for judging answers)
    # ============================================================

    def _is_stop_request(self, text: str) -> bool:
        stop_phrases = [
            "stop", "bye", "quit", "end", "done", "that's it", "the end",
            "i want to stop", "can we stop", "let's stop", "enough",
            "bas", "band karo"
        ]
        text_lower = text.lower()
        return any(p in text_lower for p in stop_phrases)

    def _is_offtopic(self, text: str) -> bool:
        if any(c.isdigit() for c in text):
            return False
        if "/" in text or "by" in text.lower():
            return False

        offtopic = [
            "who are you", "what is your name", "tell me a joke",
            "play a game", "sing a song", "what can you do",
            "how are you", "what's up"
        ]
        text_lower = text.lower()
        return any(p in text_lower for p in offtopic)

    def _is_idk(self, text: str) -> bool:
        idk_phrases = [
            "i don't know", "i dont know", "idk", "no idea",
            "tell me the answer", "just tell me", "skip",
            "i can't", "i cant", "nahi pata", "pata nahi",
            "what is the answer", "give me the answer",
            "please explain", "explain to me", "please start",
            "mujhe nahi aata", "samajh nahi aa raha"
        ]
        text_lower = text.lower()
        return any(p in text_lower for p in idk_phrases)

    def _wants_english(self, text: str) -> bool:
        english_phrases = [
            "speak in english", "english please", "in english",
            "can you speak english", "talk in english", "use english"
        ]
        text_lower = text.lower()
        return any(p in text_lower for p in english_phrases)

    def get_session_state(self) -> dict:
        """Get current session state for API response."""
        return {
            "student_name": self.session["student_name"],
            "chapter": self.session["chapter"],
            "questions_completed": self.session["questions_completed"],
            "total_questions": self.session["total_questions"],
            "score": self.session["score"],
            "hint_count": self.session["hint_count"],
            "attempt_count": self.session["attempt_count"],
            "duration_minutes": self.session["duration_minutes"],
            "session_ended": self.session["session_ended"]
        }
