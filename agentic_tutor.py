"""
IDNA Agentic Tutor - The Teacher Brain (v2.1)
===============================================
LLM is the teacher. LLM judges answers. LLM teaches.
Python manages session state, enforces guardrails, routes tools.

v2.1 changes:
- gpt-4o for speech generation (holds character, natural voice)
- gpt-4o-mini for tool picking (fast, cheap)
- Few-shot examples in system prompt to kill chatbot voice
- Truncation fix: sentences always complete
- Stronger anti-chatbot constraints
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
# MODEL CONFIGURATION
# ============================================================
TOOL_MODEL = "gpt-4o-mini"       # Fast, cheap — picks the right tool
SPEECH_MODEL = "gpt-4o"          # Rich, natural — generates what student hears
TOOL_MAX_TOKENS = 200
SPEECH_MAX_TOKENS = 350


# ============================================================
# DIDI'S CORE IDENTITY + FEW-SHOT EXAMPLES
# ============================================================

DIDI_SYSTEM_PROMPT = """You are Didi — a real Indian math teacher. Not an AI. Not a chatbot. Not an assistant. A teacher.

You're tutoring {student_name}, Class 8, one-on-one. This is a voice session — everything you say will be spoken aloud through a speaker. Write ONLY the words that come out of Didi's mouth.

{lang_instruction}

## HOW DIDI ACTUALLY SOUNDS (follow these exactly)

Here are real examples of how Didi speaks. Match this tone, length, and feel:

WHEN STUDENT GETS IT RIGHT:
- "Haan, -1/7. Sahi hai. You kept the denominator same and added the numerators. Chalo, next one."
- "5/8, correct. You remembered additive inverse means just flip the sign. Good. Agle question pe chalte hain."
- "Yes, 49. You knew 7 times 7. Simple and clean. Okay next question: find the square root of 144."

WHEN STUDENT GETS IT WRONG (first attempt):
- "Hmm, you said 1/7. Accha tell me one thing — when you added -3 and 2, what did you get?"
- "You're saying -1/14. I think I see what happened. Denominators same the na? Toh kya unhe add karte hain?"
- "2/3 nahi hai. But you're on the right track. Go back to the numerators — what's -3 plus 2?"

WHEN GIVING A HINT:
- "Dekho, dono fractions mein denominator same hai — 7. Toh denominator ko chhodho. Sirf numerators pe focus karo. -3 aur 2, add karo."
- "Think about it like money. You owe 3 rupees and someone gives you 2. Kitne owe karte ho ab?"

WHEN STUDENT SAYS IDK:
- "Koi baat nahi. Chhodo poora question. Sirf ye batao — dono fractions mein denominator kya hai? Bas itna."
- "It's okay. Don't try to solve the whole thing. Just tell me the first step — what would you do first?"

WHEN EXPLAINING AFTER STUDENT IS STUCK:
- "Accha sun. -3/7 plus 2/7. Dono mein denominator 7 hai, same hai. Toh hum sirf numerators add karenge: -3 plus 2, that gives -1. Denominator same rehta hai, 7. So answer is -1/7. Samjhe?"

## THINGS DIDI NEVER SAYS (if you write any of these, you've failed)

These are chatbot phrases. Didi is a teacher, not a chatbot:
- "That's a great question!" / "Great job!" / "Excellent!" / "Amazing!" / "Wonderful!"
- "Let's take a moment to think about..." / "Can you tell me how you would approach..."
- "I understand you want..." / "I can help you with..." / "Let me assist..."
- "Sure!" / "Of course!" / "Absolutely!" / "No problem!"
- "That's perfectly fine." / "That's a valid point."
- "Let me explain..." (just explain, don't announce it)
- "How would you approach this?" (too formal — say "kaise karoge?" or "what would you do first?")
- Any sentence starting with "I understand" or "I appreciate"

## RULES

1. Complete your sentences. Never stop mid-thought. If you're reading a question, finish reading it.
2. Every response must reference the student's ACTUAL answer or the ACTUAL question. No generic responses.
3. When transitioning to next question, just read it. Don't say "here's your next question" — just say "Chalo. What is 5/8 minus 3/8?"
4. Keep it 2-4 sentences. Not 1, not 6. When explaining a concept, you can go up to 5.
5. No formatting. No bullets. No bold. No markdown. No asterisks. Just spoken words.
6. Use the student's name sometimes. Not every turn. Maybe every 3rd or 4th response.

{history_context}"""


SPEECH_GENERATION_PROMPT = """The teaching system chose: {tool_name}
Arguments: {tool_args}

Context:
{context}

Generate ONLY Didi's spoken words. Match the examples in your instructions exactly. Complete every sentence. No chatbot phrases. No formatting."""


class AgenticTutor:
    """
    The agentic tutor brain (v2.1).

    Tool picking: gpt-4o-mini (fast, cheap)
    Speech generation: gpt-4o (natural, holds character)
    Answer judging: gpt-4o-mini (has answer key in context)
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
            "duration_minutes": 0,
            "start_time": time.time(),
            "last_eval": None,
            "session_ended": False
        }

    def _get_lang_instruction(self) -> str:
        if self.session.get("language") == "english":
            return "LANGUAGE: English only. No Hindi words at all. But keep the warm, natural teacher tone."
        return "LANGUAGE: Natural Hindi-English mix. Use Hindi naturally: 'Haan', 'Accha', 'Dekho', 'Chalo', 'Sochke batao', 'Koi baat nahi', 'Bahut accha', 'Sahi hai'."

    def _build_history_context(self) -> str:
        recent = self.session.get("history", [])[-4:]
        if not recent:
            return ""

        lines = ["Recent conversation:"]
        for h in recent:
            lines.append(f"  {self.session['student_name']}: {h['student']}")
            lines.append(f"  Didi: {h['teacher']}")

        return "\n".join(lines)

    def _build_question_context(self) -> str:
        """Build full question context with answer key for LLM."""
        q = self.session["current_question"]
        s = self.session

        solution_steps = q.get("solution_steps", [])
        if isinstance(solution_steps, list):
            solution_steps = " → ".join(solution_steps)

        mistakes_text = ""
        for m in q.get("common_mistakes", []):
            mistakes_text += (
                f'  If student says "{m["wrong_answer"]}": '
                f'{m.get("diagnosis", "?")} '
                f'(micro-hint: "{m.get("micro_hint", "")}")\n'
            )

        micro_checks = q.get("micro_checks", [])
        micro_text = " / ".join(micro_checks) if micro_checks else "None"

        return f"""SESSION: {s['student_name']}, Class 8 | {s['chapter_name']}
Question {s['current_question_index'] + 1}/{s['total_questions']} | Score: {s['score']}/{s['questions_completed']} | Time: {s['duration_minutes']}min
Hints used: {s['hint_count']}/2 | Attempts: {s['attempt_count']} | IDK count: {s['idk_count']}

QUESTION: {q.get('text', q.get('question_text', ''))}
Topic: {q.get('topic', '')} / {q.get('subtopic', '')} | Difficulty: {q.get('difficulty', '?')}/3

ANSWER KEY (never reveal directly unless explaining after 2 hints):
Correct: {q.get('answer', '')}
Also accept: {q.get('accept_also', [])}
Solution: {q.get('solution', '')}
Steps: {solution_steps}

COMMON MISTAKES:
{mistakes_text if mistakes_text else 'None listed'}

MICRO-CHECKS: {micro_text}

HINTS:
Level 1: {q.get('hint_1', q.get('hint', 'Think about the concept'))}
Level 2: {q.get('hint_2', 'Try the first step')}"""

    async def start_session(self) -> str:
        """Didi greets and asks first question."""
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
            f"Start the session. Greet {name} — short, warm, real. "
            f"Then read the first question clearly.\n"
            f"Chapter: {chapter}\n"
            f"Question: {question_text}\n\n"
            f"Example of good greeting: \"Hi {name}! Chalo, aaj rational numbers practice karte hain. "
            f"Pehla sawaal: {question_text}\"\n"
            f"Keep it that natural. 2 sentences max for greeting + question."
        )

        try:
            response = self.client.chat.completions.create(
                model=SPEECH_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=SPEECH_MAX_TOKENS,
                temperature=0.7
            )
            return self._clean_speech(response.choices[0].message.content)

        except Exception as e:
            print(f"[Start Error] {e}")
            return f"Hi {name}! Chalo, let's start. {question_text}"

    async def process_input(self, student_input: str) -> str:
        """Student says something → Didi responds."""
        if self.session["session_ended"]:
            return "Session khatam ho gaya. New session start karo practice ke liye."

        self.session["duration_minutes"] = int(
            (time.time() - self.session["start_time"]) / 60
        )

        student_input = student_input.strip()

        # Language switch
        if self._wants_english(student_input):
            self.session["language"] = "english"

        # Pre-checks
        is_stop = self._is_stop_request(student_input)
        is_idk = self._is_idk(student_input)
        is_offtopic = self._is_offtopic(student_input)

        if is_stop:
            return await self._end_session("student_requested")

        if is_idk:
            self.session["idk_count"] += 1

        if not is_idk and not is_offtopic:
            self.session["attempt_count"] += 1

        # Build context
        question_context = self._build_question_context()

        input_line = ""
        if is_idk:
            input_line = f'STUDENT SAID: "{student_input}" → IDK detected. They don\'t know. IDK count: {self.session["idk_count"]}'
        elif is_offtopic:
            input_line = f'STUDENT SAID: "{student_input}" → OFF-TOPIC. Redirect to the question.'
        else:
            input_line = f'STUDENT SAID: "{student_input}" → Judge this against the answer key. Correct or wrong?'

        full_context = question_context + "\n\n" + input_line

        # LLM picks tool (gpt-4o-mini — fast)
        history_context = self._build_history_context()
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
                tool_args = {"approach": "reduce_pressure"}
            else:
                tool_name = "give_hint"
                tool_args = {"hint_level": min(self.session["hint_count"] + 1, 2),
                             "student_mistake": "needs guidance"}

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

        # Update state
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

        # Next question context
        next_q_text = ""
        if tool_name in ("praise_and_continue", "explain_solution"):
            if not self.session["session_ended"]:
                nq = self.session["current_question"]
                next_q_text = f'\n\nNEXT QUESTION (read it aloud at the end): {nq.get("text", nq.get("question_text", ""))}'
            else:
                next_q_text = "\n\nNo more questions. Wrap up the session warmly."

        # Generate speech (gpt-4o — natural voice)
        speech_prompt = SPEECH_GENERATION_PROMPT.format(
            tool_name=tool_name,
            tool_args=json.dumps(tool_args),
            context=full_context + next_q_text
        )

        speech = self._generate_speech(speech_prompt)

        # Store history
        self.session["history"].append({
            "student": student_input,
            "teacher": speech,
            "tool": tool_name,
            "correct": is_correct
        })

        return speech

    def _advance_question(self):
        """Move to next question, reset counters."""
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
        Generate Didi's spoken words using gpt-4o.

        gpt-4o holds character much better than mini.
        The few-shot examples in DIDI_SYSTEM_PROMPT anchor the voice.
        """
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
                temperature=0.7,
                stop=["\n\n"]  # Prevent rambling — stop at paragraph break
            )
            text = self._clean_speech(response.choices[0].message.content)

            # Truncation safety: if text doesn't end with sentence-ender, trim to last complete sentence
            if text and text[-1] not in '.?!।':
                for i in range(len(text) - 1, -1, -1):
                    if text[i] in '.?!।':
                        text = text[:i + 1]
                        break

            return text

        except Exception as e:
            print(f"[Speech Error] {e}")
            return "Chalo, is question ko phir se dekhte hain."

    def _clean_speech(self, text: str) -> str:
        """Clean LLM output for TTS."""
        text = text.strip()
        text = text.replace("**", "").replace("*", "")
        text = text.replace("##", "").replace("#", "")
        text = text.replace("- ", "").replace("• ", "")
        text = text.replace("`", "")
        # Remove wrapping quotes
        if len(text) > 2 and text[0] == '"' and text[-1] == '"':
            text = text[1:-1]
        if len(text) > 2 and text[0] == "'" and text[-1] == "'":
            text = text[1:-1]
        # Remove "Didi:" prefix
        for prefix in ["Didi:", "didi:", "DIDI:", "Didi :", "Teacher:"]:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        return text

    async def _end_session(self, reason: str) -> str:
        """End session with warm wrap-up."""
        self.session["session_ended"] = True

        # Build a specific summary
        history = self.session.get("history", [])
        correct_count = sum(1 for h in history if h.get("correct"))

        prompt = (
            f"End the session. {self.session['student_name']} is done.\n"
            f"Score: {self.session['score']}/{self.session['questions_completed']}\n"
            f"Time: {self.session['duration_minutes']} minutes\n"
            f"Reason: {reason}\n\n"
            f"Say bye like a real teacher. 2-3 sentences. Mention something specific from the session if possible.\n"
            f"Example: \"Accha {self.session['student_name']}, aaj ka session accha raha. "
            f"Rational numbers mein tumhe fractions add karna ab acche se aata hai. Keep practicing, see you next time!\""
        )

        return self._generate_speech(prompt)

    # ============================================================
    # Pre-checks (Python, not LLM)
    # ============================================================

    def _is_stop_request(self, text: str) -> bool:
        stop_phrases = [
            "stop", "bye", "quit", "end", "done", "that's it", "the end",
            "i want to stop", "can we stop", "let's stop", "enough",
            "bas", "band karo", "ruko"
        ]
        return any(p in text.lower() for p in stop_phrases)

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
        return any(p in text.lower() for p in offtopic)

    def _is_idk(self, text: str) -> bool:
        idk_phrases = [
            "i don't know", "i dont know", "idk", "no idea",
            "tell me the answer", "just tell me", "skip",
            "i can't", "i cant", "nahi pata", "pata nahi",
            "what is the answer", "give me the answer",
            "please explain", "explain to me", "please start",
            "mujhe nahi aata", "samajh nahi aa raha"
        ]
        return any(p in text.lower() for p in idk_phrases)

    def _wants_english(self, text: str) -> bool:
        english_phrases = [
            "speak in english", "english please", "in english",
            "can you speak english", "talk in english", "use english"
        ]
        return any(p in text.lower() for p in english_phrases)

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
