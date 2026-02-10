"""
IDNA Agentic Tutor - The Teacher Brain
======================================
LLM reasons about teaching moves. Python enforces rules.
"""

import json
import time
import os
from typing import Optional
from openai import OpenAI

from tutor_tools import TUTOR_TOOLS
from tutor_prompts import SYSTEM_PROMPT, SPEECH_PROMPTS
from guardrails import check_guardrails
from context_builder import build_context, build_start_context
from evaluator import evaluate_answer, normalize_spoken_input
from questions import ALL_CHAPTERS, CHAPTER_NAMES


class AgenticTutor:
    """
    The agentic tutor brain.

    Architecture:
    1. Python evaluates answer (deterministic)
    2. Agent reasons about teaching move (LLM with tools)
    3. Guardrails override if needed (Python)
    4. Tool executes and generates speech (LLM)
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
        questions = ALL_CHAPTERS.get(chapter, [])[:10]  # Max 10 per session

        if not questions:
            # Fallback to rational_numbers if chapter not found
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
            "duration_minutes": 0,
            "start_time": time.time(),
            "last_eval": None,
            "session_ended": False
        }

    async def start_session(self) -> str:
        """Start the session with greeting and first question."""
        q = self.session["current_question"]
        name = self.session["student_name"]
        chapter = self.session["chapter_name"]

        # Simple, direct greeting like a real teacher
        greeting = f"Hi {name}! Let's practice {chapter.split(':')[0] if ':' in chapter else chapter}."
        question = q.get("text", q.get("question_text", ""))

        return f"{greeting} Here's your first question: {question}"

    async def process_input(self, student_input: str) -> str:
        """
        Main entry point. Student says something → teacher responds.

        Flow:
        1. Pre-checks (stop, off-topic, idk) - Python
        2. Evaluate answer - Python
        3. Build context with eval result
        4. Agent picks tool - LLM
        5. Guardrails check - Python
        6. Execute tool - generates speech
        """
        if self.session["session_ended"]:
            return "Session has ended. Start a new session to continue practicing."

        # Update timing
        self.session["duration_minutes"] = int(
            (time.time() - self.session["start_time"]) / 60
        )

        student_input = student_input.strip()

        # Step 0: Check language preference
        if self._wants_english(student_input):
            self.session["language"] = "english"
            return "Okay, I'll speak in English. Let me repeat: " + self.session["current_question"].get("text", "")

        # Step 1: Pre-checks (Python, not LLM)
        is_stop = self._is_stop_request(student_input)
        is_idk = self._is_idk(student_input)
        is_offtopic = self._is_offtopic(student_input)

        # Step 2: Evaluate answer (Python, not LLM)
        eval_result = None
        q = self.session["current_question"]

        if is_stop:
            eval_result = {
                "is_correct": False,
                "is_idk": False,
                "is_offtopic": False,
                "is_stop": True,
                "normalized_answer": student_input
            }
        elif is_idk:
            self.session["idk_count"] += 1
            eval_result = {
                "is_correct": False,
                "is_idk": True,
                "is_offtopic": False,
                "is_stop": False,
                "normalized_answer": student_input,
                "idk_count": self.session["idk_count"]
            }
        elif is_offtopic:
            eval_result = {
                "is_correct": False,
                "is_idk": False,
                "is_offtopic": True,
                "is_stop": False,
                "normalized_answer": student_input
            }
        else:
            # Real evaluation using the evaluator
            eval_result = evaluate_answer(
                correct_answer=q.get("answer", ""),
                student_answer=student_input,
                question=q  # Pass full question for common_mistakes matching
            )
            eval_result["is_idk"] = False
            eval_result["is_offtopic"] = False
            eval_result["is_stop"] = False
            self.session["attempt_count"] += 1

        # Store for guardrails
        self.session["last_eval"] = eval_result

        # Step 3: Handle special cases directly (no agent needed)
        if eval_result.get("is_stop"):
            return await self._end_session("student_requested")

        if eval_result.get("is_offtopic"):
            return self._handle_offtopic()

        # Step 4: Build context with evaluation result
        context = build_context(self.session, student_input, eval_result)

        # Step 5: Call agent to pick a tool
        try:
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

            tool_call = response.choices[0].message.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)

        except Exception as e:
            print(f"[Agent Error] {e}")
            # Fallback: use eval result to decide
            if eval_result.get("is_correct"):
                tool_name = "praise_and_continue"
                tool_args = {"what_they_did_well": "good work"}
            elif eval_result.get("is_idk"):
                tool_name = "encourage_attempt"
                tool_args = {"approach": "reduce_pressure"}
            else:
                tool_name = "give_hint"
                tool_args = {
                    "hint_level": self.session["hint_count"] + 1,
                    "student_mistake": "Let's think about this"
                }

        # Step 6: Apply guardrails
        guardrail = check_guardrails(tool_name, tool_args, self.session)
        if guardrail["blocked"]:
            print(f"[Guardrail] {guardrail['reason']}")
            tool_name = guardrail["override_tool"]
            tool_args = guardrail["override_args"]

        # Step 7: Execute tool
        speech = await self._execute_tool(tool_name, tool_args, student_input, eval_result)

        # Step 8: Update history
        self.session["history"].append({
            "student": student_input,
            "teacher": speech,
            "tool": tool_name,
            "correct": eval_result.get("is_correct", False)
        })

        return speech

    async def _execute_tool(
        self,
        tool_name: str,
        args: dict,
        student_input: str,
        eval_result: dict
    ) -> str:
        """Execute the tool and generate speech."""

        q = self.session["current_question"]

        if tool_name == "give_hint":
            return await self._give_hint(args, student_input, eval_result)

        elif tool_name == "praise_and_continue":
            return await self._praise_and_continue(args, student_input)

        elif tool_name == "explain_solution":
            return await self._explain_solution(args)

        elif tool_name == "encourage_attempt":
            return await self._encourage_attempt(args)

        elif tool_name == "ask_what_they_did":
            return await self._ask_what_they_did(args, student_input)

        elif tool_name == "end_session":
            return await self._end_session(args.get("reason", "completed"))

        # Fallback
        return f"Hmm. Let's think about this. {q.get('text', '')}"

    async def _give_hint(self, args: dict, student_input: str, eval_result: dict) -> str:
        """Give a hint, referencing student's specific mistake."""
        level = args.get("hint_level", 1)
        q = self.session["current_question"]

        # Update hint count
        self.session["hint_count"] = max(self.session["hint_count"], level)

        # Get hint direction
        hint_direction = q.get(f"hint_{level}", q.get("hint", "Think about the concept"))

        # Use diagnosis from evaluator if available
        student_mistake = args.get("student_mistake", "")
        if eval_result.get("diagnosis"):
            student_mistake = eval_result["diagnosis"]

        # Generate speech
        prompt = SPEECH_PROMPTS["give_hint"].format(
            student_answer=student_input,
            student_mistake=student_mistake,
            hint_direction=hint_direction,
            hint_level=level
        )

        speech = self._generate_speech(prompt)
        return speech

    async def _praise_and_continue(self, args: dict, student_input: str) -> str:
        """Praise and move to next question."""
        what_they_did_well = args.get("what_they_did_well", "good thinking")

        # Update score
        self.session["score"] += 1
        self.session["questions_completed"] += 1

        # Move to next question
        self.session["current_question_index"] += 1
        self.session["hint_count"] = 0
        self.session["attempt_count"] = 0
        self.session["idk_count"] = 0

        if self.session["current_question_index"] < len(self.session["questions"]):
            next_q = self.session["questions"][self.session["current_question_index"]]
            self.session["current_question"] = next_q

            # Generate praise + next question
            prompt = SPEECH_PROMPTS["praise_and_continue"].format(
                student_answer=student_input,
                what_they_did_well=what_they_did_well,
                next_question=next_q.get("text", next_q.get("question_text", ""))
            )
            return self._generate_speech(prompt)
        else:
            # No more questions
            return await self._end_session("completed")

    async def _explain_solution(self, args: dict) -> str:
        """Full solution walkthrough."""
        q = self.session["current_question"]

        self.session["questions_completed"] += 1

        # Get solution steps
        solution_steps = q.get("solution_steps", [])
        if isinstance(solution_steps, list):
            solution_steps = " ".join(solution_steps)
        elif not solution_steps:
            solution_steps = q.get("solution", "")

        prompt = SPEECH_PROMPTS["explain_solution"].format(
            question=q.get("text", q.get("question_text", "")),
            answer=q.get("answer", ""),
            solution_steps=solution_steps,
            acknowledge_struggle=args.get("acknowledge_struggle", "Let me show you")
        )

        speech = self._generate_speech(prompt)

        # Move to next question
        self.session["current_question_index"] += 1
        self.session["hint_count"] = 0
        self.session["attempt_count"] = 0
        self.session["idk_count"] = 0

        if self.session["current_question_index"] < len(self.session["questions"]):
            next_q = self.session["questions"][self.session["current_question_index"]]
            self.session["current_question"] = next_q
            # Respect language preference
            if self.session.get("language") == "english":
                speech += f" Next question: {next_q.get('text', next_q.get('question_text', ''))}"
            else:
                speech += f" Chalo, next question: {next_q.get('text', next_q.get('question_text', ''))}"
        else:
            speech += " That was our last question."
            return speech + " " + await self._end_session("completed")

        return speech

    async def _encourage_attempt(self, args: dict) -> str:
        """Encourage student who said IDK."""
        approach = args.get("approach", "reduce_pressure")
        q = self.session["current_question"]

        prompt = SPEECH_PROMPTS["encourage_attempt"].format(
            question=q.get("text", q.get("question_text", "")),
            approach=approach
        )

        return self._generate_speech(prompt)

    async def _ask_what_they_did(self, args: dict, student_input: str) -> str:
        """Ask student to explain their thinking before correcting."""
        question_type = args.get("question_type", "what_did_you_do")

        prompt = SPEECH_PROMPTS["ask_what_they_did"].format(
            student_answer=student_input,
            question_type=question_type
        )

        return self._generate_speech(prompt)

    async def _end_session(self, reason: str) -> str:
        """End the session with summary."""
        self.session["session_ended"] = True

        prompt = SPEECH_PROMPTS["end_session"].format(
            score=self.session["score"],
            total=self.session["questions_completed"],
            duration=self.session["duration_minutes"],
            reason=reason
        )

        return self._generate_speech(prompt)

    def _handle_offtopic(self) -> str:
        """Handle off-topic input."""
        q = self.session["current_question"]
        question_text = q.get("text", q.get("question_text", ""))

        return f"Hmm, let's focus on our question. {question_text}"

    def _generate_speech(self, instruction: str) -> str:
        """Generate spoken words via LLM."""
        language = self.session.get("language", "hinglish")
        if language == "english":
            lang_instruction = "Speak in English only. No Hindi words."
        else:
            lang_instruction = "Hindi-English mix is okay."

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"Generate natural spoken teacher speech. {lang_instruction} "
                                   "No formatting. Short sentences. Max 3 sentences total."
                    },
                    {"role": "user", "content": instruction}
                ],
                max_tokens=100,
                temperature=0.7
            )
            text = response.choices[0].message.content.strip()

            # Remove any formatting that slipped through
            text = text.replace("*", "").replace("#", "").replace("- ", "")

            return text

        except Exception as e:
            print(f"[Speech Gen Error] {e}")
            return "Let's continue with our question."

    def _is_stop_request(self, text: str) -> bool:
        """Check if student wants to stop."""
        # Check IDK first - if student is asking for help, don't stop
        if self._is_idk(text):
            return False

        stop_phrases = [
            "let's stop", "i want to stop", "can we stop", "stop now",
            "bye", "goodbye", "quit", "i'm done", "im done", "that's it",
            "the end", "enough", "end session"
        ]
        text_lower = text.lower()
        return any(p in text_lower for p in stop_phrases)

    def _is_offtopic(self, text: str) -> bool:
        """Check if input is off-topic."""
        # Don't mark as off-topic if it contains numbers (likely an answer)
        if any(c.isdigit() for c in text):
            return False

        # Don't mark as off-topic if it contains fraction-like patterns
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
        """Check if student said they don't know."""
        idk_phrases = [
            "i don't know", "i dont know", "i do not know", "idk", "no idea",
            "tell me the answer", "just tell me", "skip",
            "i can't", "i cant", "i can not", "nahi pata", "pata nahi",
            "what is the answer", "give me the answer",
            "please explain", "explain to me", "please start",
            "how is it done", "what is it", "how do i", "how to do",
            "i need help", "help me", "don't understand", "do not understand"
        ]
        text_lower = text.lower()
        return any(p in text_lower for p in idk_phrases)

    def _wants_english(self, text: str) -> bool:
        """Check if student wants English."""
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
