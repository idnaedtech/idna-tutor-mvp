"""
IDNA Agentic Tutor - The Teacher Brain (v2.2)
===============================================
The core insight: stop telling the LLM how to be natural.
Instead, give it a character and get out of the way.

v2.2: Conversational rewrite. Didi is a person, not a framework.
"""

import json
import time
import os
import re
from typing import Optional
from openai import OpenAI

from tutor_tools import TUTOR_TOOLS
from guardrails import check_guardrails
from questions import ALL_CHAPTERS, CHAPTER_NAMES


# ============================================================
# MODEL CONFIGURATION
# ============================================================
TOOL_MODEL = "gpt-4o-mini"
SPEECH_MODEL = "gpt-4o"
TOOL_MAX_TOKENS = 200
SPEECH_MAX_TOKENS = 400


# ============================================================
# DIDI'S IDENTITY
# ============================================================
# The key insight: don't give rules. Give a character.
# Don't say "never say X." Just make the character someone
# who would never say X in the first place.

DIDI_SYSTEM_PROMPT = """You are Didi. You teach math to kids in India. Right now you're sitting with {student_name}, a Class 8 student, helping them with math. This is a private tutor session, face to face. Everything you say is spoken out loud — it goes through a speaker.

You grew up in a middle-class Indian family. You've taught for 12 years. You've seen every kind of student — the scared ones, the lazy ones, the bright ones who just need a push. You genuinely like kids. You're not performing warmth, you actually care whether {student_name} understands.

You talk the way you'd talk to your own younger sibling or cousin. {lang_instruction}

When {student_name} gets something right, you react the way a real person would — a quick "haan sahi hai" or "that's it" and you move on. You don't throw a party for every correct answer.

When they get it wrong, you're curious. You want to know what they were thinking. You don't lecture. You ask. And when you do explain, you explain like you're sitting next to them — pointing at an invisible notebook, using examples from everyday life.

When they say "I don't know" — you shrink the problem. You don't repeat the same question louder. You find a smaller piece they CAN answer and start there. If they're genuinely confused about the basics, you stop and teach the basics. You don't robotically push them through micro-questions when they need a real explanation.

When they ask you to explain something — you explain it. Simply. Like a human. You don't deflect with "what do you think?" when they've already told you they don't know.

You keep it short because this is spoken, not written. 2-4 sentences usually. But if a student genuinely needs a concept explained, you take the time. You don't artificially cut yourself off.

When saying fractions out loud, say them naturally: "minus 3 over 7", "2 over 3", "minus 1 over 7". Never write -3/7 or use LaTeX. You are speaking, not writing on a blackboard.

IMPORTANT: You complete every sentence. You never stop mid-thought.

A few things you'd never do because they're not who you are:
- You don't say "Great job!" or "Excellent!" because that's what YouTube teachers say, not real ones.
- You don't say "Let me help you with that" because you're already helping — you don't narrate it.
- You don't say "That's a great question" because no real teacher says that to a 13-year-old.
- You don't start sentences with "I understand" because that's customer service, not teaching.
- You don't say "Can you tell me how you would approach this?" because that sounds like an exam, not a conversation. You'd say "kaise kiya?" or "what did you do?"

{history_context}"""


class AgenticTutor:

    def __init__(self, student_name: str, chapter: str):
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=30.0,
            max_retries=2
        )
        self.session = self._init_session(student_name, chapter)

    def _init_session(self, student_name: str, chapter: str) -> dict:
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
            "duration_minutes": 0,
            "start_time": time.time(),
            "last_eval": None,
            "last_tool": None,  # Track last tool for acknowledgment detection
            "session_ended": False
        }

    def _get_lang_instruction(self) -> str:
        if self.session.get("language") == "english":
            return "You speak in English only right now because the student asked for it. No Hindi at all. But you're still you — warm, direct, real."
        return "You naturally mix Hindi and English the way educated Indians do. 'Haan', 'Accha', 'Dekho', 'Chalo', 'Koi baat nahi' — these come out naturally, not forced."

    def _build_history_context(self) -> str:
        recent = self.session.get("history", [])[-5:]
        if not recent:
            return ""
        lines = ["\nWhat's happened so far in this session:"]
        for h in recent:
            lines.append(f"  {self.session['student_name']}: {h['student']}")
            lines.append(f"  You said: {h['teacher']}")
        return "\n".join(lines)

    def _build_question_context(self) -> str:
        q = self.session["current_question"]
        s = self.session

        solution_steps = q.get("solution_steps", [])
        if isinstance(solution_steps, list):
            solution_steps = " → ".join(solution_steps)

        mistakes_text = ""
        for m in q.get("common_mistakes", []):
            mistakes_text += (
                f'  "{m["wrong_answer"]}" means: {m.get("diagnosis", "?")} '
                f'(you could say: "{m.get("micro_hint", "")}")\n'
            )

        return f"""You're on question {s['current_question_index'] + 1} of {s['total_questions']}.
{s['student_name']} has scored {s['score']}/{s['questions_completed']} so far. Session: {s['duration_minutes']} min.
Hints given on this question: {s['hint_count']}. Attempts: {s['attempt_count']}. Times they said idk: {s['idk_count']}.

The question: {q.get('text', q.get('question_text', ''))}
Subject: {q.get('topic', '')} / {q.get('subtopic', '')}

--- Your teacher's answer key (don't show this directly) ---
Answer: {q.get('answer', '')}
Also correct: {q.get('accept_also', [])}
How to solve it: {solution_steps}
Full explanation: {q.get('solution', '')}

If they make these common mistakes:
{mistakes_text if mistakes_text else '(none listed)'}

If you need to give a hint:
  Small nudge: {q.get('hint_1', q.get('hint', ''))}
  Bigger help: {q.get('hint_2', '')}"""

    async def start_session(self) -> str:
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
            f"{name} just sat down for today's session. "
            f"You're doing {chapter} today. "
            f"Say hi and ask the first question: {question_text}"
        )

        try:
            response = self.client.chat.completions.create(
                model=SPEECH_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=SPEECH_MAX_TOKENS,
                temperature=0.8
            )
            return self._clean_speech(response.choices[0].message.content)
        except Exception as e:
            print(f"[Start Error] {e}")
            return f"Hi {name}! Chalo, aaj {chapter} karte hain. {question_text}"

    async def process_input(self, student_input: str) -> str:
        if self.session["session_ended"]:
            return "Session khatam ho gaya. New session start karo."

        self.session["duration_minutes"] = int(
            (time.time() - self.session["start_time"]) / 60
        )
        student_input = student_input.strip()

        if self._wants_english(student_input):
            self.session["language"] = "english"

        is_stop = self._is_stop_request(student_input)
        is_idk = self._is_idk(student_input)
        is_offtopic = self._is_offtopic(student_input)
        is_ack = self._is_acknowledgment(student_input)

        if is_stop:
            return await self._end_session("student_requested")

        # If student acknowledges after explanation/hint, move to next question
        last_tool = self.session.get("last_tool")
        if is_ack and last_tool in ("explain_solution", "give_hint"):
            self.session["questions_completed"] += 1
            self._advance_question()
            if self.session["session_ended"]:
                return await self._end_session("completed_all_questions")
            # Move to next question
            nq = self.session["current_question"]
            next_q_text = nq.get("text", nq.get("question_text", ""))
            self.session["last_tool"] = "praise_and_continue"
            return self._generate_speech(
                f"Good, you got the idea. Let's move on. Next question: {next_q_text}"
            )

        if is_idk:
            self.session["idk_count"] += 1
        if not is_idk and not is_offtopic and not is_ack:
            self.session["attempt_count"] += 1

        # Build what the LLM sees
        question_context = self._build_question_context()
        history_context = self._build_history_context()

        # Frame what just happened
        if is_idk:
            situation = (
                f'{self.session["student_name"]} said: "{student_input}"\n'
                f"They don't know the answer or want help. This is the {self.session['idk_count']}th time on this question.\n"
                f"If they've asked for an explanation, give them one. Don't keep pushing micro-questions if they need the concept explained first."
            )
        elif is_offtopic:
            situation = (
                f'{self.session["student_name"]} said: "{student_input}"\n'
                f"This is off-topic. Bring them back gently."
            )
        else:
            situation = (
                f'{self.session["student_name"]} answered: "{student_input}"\n'
                f"Check if this matches the answer key. It might be said differently (spoken math — '2 by 3' means 2/3, 'minus 5' means -5)."
            )

        full_context = question_context + "\n\n" + situation

        # Tool selection (gpt-4o-mini)
        system = DIDI_SYSTEM_PROMPT.format(
            student_name=self.session["student_name"],
            lang_instruction=self._get_lang_instruction(),
            history_context=history_context
        )

        try:
            tool_response = self.client.chat.completions.create(
                model=TOOL_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": full_context}
                ],
                tools=TUTOR_TOOLS,
                tool_choice="required",
                max_tokens=TOOL_MAX_TOKENS,
                temperature=0.4
            )
            tool_call = tool_response.choices[0].message.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
        except Exception as e:
            print(f"[Tool Error] {e}")
            if is_idk:
                tool_name = "encourage_attempt"
                tool_args = {"approach": "break_down"}
            else:
                tool_name = "give_hint"
                tool_args = {"hint_level": min(self.session["hint_count"] + 1, 2),
                             "student_mistake": "unclear"}

        is_correct = (tool_name == "praise_and_continue")

        self.session["last_eval"] = {
            "is_correct": is_correct,
            "is_idk": is_idk,
            "is_offtopic": is_offtopic,
            "is_stop": False
        }

        # Guardrails
        guardrail = check_guardrails(tool_name, tool_args, self.session)
        if guardrail["blocked"]:
            print(f"[Guardrail] {guardrail['reason']}")
            tool_name = guardrail["override_tool"]
            tool_args = guardrail["override_args"]
            is_correct = (tool_name == "praise_and_continue")

        # State updates
        if tool_name == "give_hint":
            self.session["hint_count"] = max(self.session["hint_count"],
                                              tool_args.get("hint_level", 1))
        elif tool_name == "praise_and_continue":
            self.session["score"] += 1
            self.session["questions_completed"] += 1
            self._advance_question()
        elif tool_name == "explain_solution":
            self.session["questions_completed"] += 1
            self._advance_question()
        elif tool_name == "end_session":
            self.session["session_ended"] = True

        # Build speech instruction
        next_q_info = ""
        if tool_name in ("praise_and_continue", "explain_solution"):
            if not self.session["session_ended"]:
                nq = self.session["current_question"]
                next_q_info = f'\n\nAfter you finish, move to the next question: {nq.get("text", nq.get("question_text", ""))}'
            else:
                next_q_info = "\n\nThat was the last question. Wrap up the session."

        speech_instruction = (
            f"The system decided: {tool_name} ({json.dumps(tool_args)})\n\n"
            f"{full_context}"
            f"{next_q_info}\n\n"
            f"Now respond as Didi. Speak naturally. Complete your sentences."
        )

        speech = self._generate_speech(speech_instruction)

        self.session["history"].append({
            "student": student_input,
            "teacher": speech,
            "tool": tool_name,
            "correct": is_correct
        })

        # Track last tool for acknowledgment detection
        self.session["last_tool"] = tool_name

        return speech

    def _advance_question(self):
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
        history_context = self._build_history_context()
        system = DIDI_SYSTEM_PROMPT.format(
            student_name=self.session["student_name"],
            lang_instruction=self._get_lang_instruction(),
            history_context=history_context
        )

        try:
            response = self.client.chat.completions.create(
                model=SPEECH_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=SPEECH_MAX_TOKENS,
                temperature=0.8
            )
            text = self._clean_speech(response.choices[0].message.content)

            # Ensure sentences are complete
            if text and text[-1] not in '.?!।':
                for i in range(len(text) - 1, -1, -1):
                    if text[i] in '.?!।':
                        text = text[:i + 1]
                        break

            return text

        except Exception as e:
            print(f"[Speech Error] {e}")
            return "Ek second. Chalo phir se dekhte hain."

    def _clean_speech(self, text: str) -> str:
        text = text.strip()
        # Remove markdown
        for char in ['**', '*', '##', '#', '`', '•']:
            text = text.replace(char, '')
        text = text.replace('- ', '')

        # Remove LaTeX notation
        text = re.sub(r'\\\(.*?\\\)', '', text)
        text = re.sub(r'\\\[.*?\\\]', '', text)

        # Make fractions TTS-friendly
        # -3/7 → "minus 3 over 7"
        text = re.sub(r'-(\d+)/(\d+)', r'minus \1 over \2', text)
        text = re.sub(r'(\d+)/(\d+)', r'\1 over \2', text)

        # Wrapping quotes
        if len(text) > 2 and text[0] == '"' and text[-1] == '"':
            text = text[1:-1]
        if len(text) > 2 and text[0] == "'" and text[-1] == "'":
            text = text[1:-1]
        # Remove "Didi:" prefix
        for prefix in ["Didi:", "didi:", "DIDI:", "Teacher:", "Didi -", "Didi —"]:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        return text

    async def _end_session(self, reason: str) -> str:
        self.session["session_ended"] = True
        prompt = (
            f"Session's over. {self.session['student_name']} "
            f"got {self.session['score']} out of {self.session['questions_completed']}. "
            f"Took {self.session['duration_minutes']} minutes. "
            f"Reason: {reason}. Say bye naturally."
        )
        return self._generate_speech(prompt)

    def _is_stop_request(self, text: str) -> bool:
        stop = ["stop", "bye", "quit", "end", "done", "that's it", "the end",
                "i want to stop", "can we stop", "let's stop", "enough",
                "bas", "band karo", "ruko"]
        return any(p in text.lower() for p in stop)

    def _is_offtopic(self, text: str) -> bool:
        if any(c.isdigit() for c in text):
            return False
        if "/" in text or "by" in text.lower():
            return False
        offtopic = ["who are you", "what is your name", "tell me a joke",
                    "play a game", "sing a song", "what can you do",
                    "how are you", "what's up"]
        return any(p in text.lower() for p in offtopic)

    def _is_idk(self, text: str) -> bool:
        idk = ["i don't know", "i dont know", "idk", "no idea",
               "tell me the answer", "just tell me", "skip",
               "i can't", "i cant", "nahi pata", "pata nahi",
               "what is the answer", "give me the answer",
               "please explain", "explain to me", "please start",
               "mujhe nahi aata", "samajh nahi aa raha",
               "can you explain", "explain the chapter", "teach me",
               "what is fraction", "what are fractions", "what is a fraction"]
        return any(p in text.lower() for p in idk)

    def _wants_english(self, text: str) -> bool:
        eng = ["speak in english", "english please", "in english",
               "can you speak english", "talk in english", "use english",
               "can you speak in english"]
        return any(p in text.lower() for p in eng)

    def _is_acknowledgment(self, text: str) -> bool:
        """Detect if student is acknowledging they understood (after explanation)."""
        text_lower = text.lower().strip()
        # Short acknowledgments
        acks = ["yeah", "yes", "okay", "ok", "got it", "i got it", "makes sense",
                "i understand", "understood", "right", "alright", "fine", "sure",
                "haan", "theek hai", "theek", "samajh gaya", "samajh gayi",
                "accha", "oh okay", "oh ok", "yep", "yup", "hmm okay", "okay okay",
                "i see", "ah okay", "ah ok", "clear", "that's clear", "kind of"]
        # Must be short (just acknowledgment, not a real answer)
        if len(text_lower.split()) <= 5:
            return any(text_lower == ack or text_lower.startswith(ack + " ") or
                      text_lower.endswith(" " + ack) or ack == text_lower.rstrip(".")
                      for ack in acks)
        return False

    def get_session_state(self) -> dict:
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
