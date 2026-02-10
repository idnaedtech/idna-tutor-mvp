"""
IDNA Agentic Tutor - The Teacher Brain (v2.3)
===============================================
Fixes from real student testing transcript:
1. "Yeah/Okay" after explanation → move to next question (not re-explain)
2. Off-topic/trolling ("subscribe", "thanks for watching") → redirect once, then move on
3. Explain solution → always include next question in same response
4. Telugu/regional language requests → warm acknowledgment
5. last_tool tracking expanded to catch all ack scenarios
6. Stuck-on-question circuit breaker (3+ IDKs → explain and move on)
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

DIDI_SYSTEM_PROMPT = """You are Didi. You teach math to kids in India. Right now you're sitting with {student_name}, a Class 8 student, helping them with math. This is a private tutor session, face to face. Everything you say is spoken out loud — it goes through a speaker.

You grew up in a middle-class Indian family. You've taught for 12 years. You've seen every kind of student — the scared ones, the lazy ones, the bright ones who just need a push. You genuinely like kids. You're not performing warmth, you actually care whether {student_name} understands.

You talk the way you'd talk to your own younger sibling or cousin. {lang_instruction}

When {student_name} gets something right, you react the way a real person would — a quick "haan sahi hai" or "that's it" and you move on. You don't throw a party for every correct answer.

When they get it wrong, you're curious. You want to know what they were thinking. You don't lecture. You ask. And when you do explain, you explain like you're sitting next to them — pointing at an invisible notebook, using examples from everyday life.

When they say "I don't know" — you shrink the problem. You don't repeat the same question louder. You find a smaller piece they CAN answer and start there. If they're genuinely confused about the basics, you stop and teach the basics. You don't robotically push them through micro-questions when they need a real explanation.

When they ask you to explain something — you explain it. Simply. Like a human. You don't deflect with "what do you think?" when they've already told you they don't know.

CRITICAL RULE — NEVER RE-EXPLAIN: If you've already explained a concept and {student_name} says "yeah", "okay", "got it", "makes sense", or any acknowledgment — STOP explaining. Move to the next question immediately. Do NOT repeat the explanation. Do NOT rephrase it. They understood. Move on.

CRITICAL RULE — ALWAYS TRANSITION: When you explain a solution or give an answer, ALWAYS end by reading the next question. Never leave {student_name} hanging after an explanation. The flow is: explain → "Chalo, next question" → read next question.

When {student_name} goes off-topic, jokes around, or says random things like "subscribe" or "thanks for watching" — smile it off in ONE short sentence and redirect. Don't re-explain the math. Just say "Arre yaar, focus karo" or "Haha, chalo wapas aate hain" and ask the question again briefly.

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
            "offtopic_streak": 0,      # Track consecutive off-topic inputs
            "language": "hinglish",
            "history": [],
            "duration_minutes": 0,
            "start_time": time.time(),
            "last_eval": None,
            "last_tool": None,
            "explained_current": False,  # Did we already explain this question?
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

    def _get_next_question_text(self) -> str:
        """Get the next question's text for transitions."""
        next_idx = self.session["current_question_index"]
        if next_idx < len(self.session["questions"]):
            nq = self.session["questions"][next_idx]
            return nq.get("text", nq.get("question_text", ""))
        return ""

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

        # Language switch
        if self._wants_english(student_input):
            self.session["language"] = "english"

        # Language request for unsupported language
        lang_request = self._wants_other_language(student_input)
        if lang_request:
            q = self.session["current_question"]
            q_text = q.get("text", q.get("question_text", ""))
            speech = self._generate_speech(
                f'{self.session["student_name"]} asked to speak in {lang_request}. '
                f"You can't speak {lang_request} yet. Be warm about it — say something like "
                f"\"Sorry yaar, {lang_request} mein abhi nahi bol sakti. But jaldi seekh loongi! "
                f"For now let's continue in English or Hindi.\" Then re-read the current question: {q_text}"
            )
            self.session["history"].append({
                "student": student_input, "teacher": speech,
                "tool": "language_redirect", "correct": False
            })
            return speech

        # Detect categories
        is_stop = self._is_stop_request(student_input)
        is_idk = self._is_idk(student_input)
        is_offtopic = self._is_offtopic(student_input)
        is_ack = self._is_acknowledgment(student_input)
        is_troll = self._is_trolling(student_input)

        if is_stop:
            return await self._end_session("student_requested")

        # ============================================================
        # FAST PATH: Acknowledgment after explanation → MOVE ON
        # ============================================================
        last_tool = self.session.get("last_tool")
        if is_ack and last_tool in ("explain_solution", "give_hint", "encourage_attempt", "praise_and_continue"):
            # They understood. Move to next question. No re-explanation.
            if not self.session.get("explained_current"):
                # Ack after a hint — they might be acknowledging the hint, not answering
                # Only auto-advance if we already explained or they've had 2+ hints
                if last_tool == "give_hint" and self.session["hint_count"] < 2:
                    # Don't auto-advance after first hint — ask them to try
                    q_text = self.session["current_question"].get("text", "")
                    speech = self._generate_speech(
                        f"{self.session['student_name']} said \"{student_input}\" after getting a hint. "
                        f"They seem to understand the hint. Now ask them to try answering: {q_text}"
                    )
                    self.session["history"].append({
                        "student": student_input, "teacher": speech,
                        "tool": "re_ask", "correct": False
                    })
                    self.session["last_tool"] = "re_ask"
                    return speech

            # Auto-advance to next question
            self.session["questions_completed"] += 1
            self._advance_question()
            if self.session["session_ended"]:
                return await self._end_session("completed_all_questions")

            nq_text = self._get_next_question_text()
            speech = self._generate_speech(
                f"{self.session['student_name']} understood. Move to next question immediately. "
                f"Say something brief like 'Accha, chalo next one' or 'Good, moving on' — "
                f"ONE short sentence max — then read: {nq_text}"
            )
            self.session["history"].append({
                "student": student_input, "teacher": speech,
                "tool": "praise_and_continue", "correct": False
            })
            self.session["last_tool"] = "praise_and_continue"
            self.session["explained_current"] = False
            return speech

        # ============================================================
        # FAST PATH: Trolling / random nonsense → redirect briefly
        # ============================================================
        if is_troll or (is_offtopic and self.session["offtopic_streak"] >= 1):
            self.session["offtopic_streak"] += 1
            q_text = self.session["current_question"].get("text", "")

            if self.session["offtopic_streak"] >= 3:
                # They're not engaging. Give them a gentle out.
                speech = self._generate_speech(
                    f"{self.session['student_name']} keeps going off-topic (said: \"{student_input}\"). "
                    f"They might be bored or not interested right now. Say something like: "
                    f"'Lagta hai aaj mood nahi hai. Koi baat nahi, hum baad mein continue kar sakte hain. "
                    f"Ya phir ek aur try karte hain?' Keep it warm, no guilt."
                )
            else:
                speech = self._generate_speech(
                    f"{self.session['student_name']} said something random: \"{student_input}\". "
                    f"Smile it off in ONE short sentence — like 'Haha, focus yaar' or 'Arre chalo wapas' — "
                    f"then briefly re-read the question: {q_text}. Do NOT re-explain anything."
                )

            self.session["history"].append({
                "student": student_input, "teacher": speech,
                "tool": "redirect", "correct": False
            })
            self.session["last_tool"] = "redirect"
            return speech

        if is_offtopic:
            self.session["offtopic_streak"] += 1
        else:
            self.session["offtopic_streak"] = 0  # Reset on real input

        if is_idk:
            self.session["idk_count"] += 1
        if not is_idk and not is_offtopic and not is_ack:
            self.session["attempt_count"] += 1

        # ============================================================
        # CIRCUIT BREAKER: Too many IDKs → explain and move on
        # ============================================================
        if self.session["idk_count"] >= 3 and not self.session.get("explained_current"):
            # Student is stuck. Explain the answer and move to next question.
            q = self.session["current_question"]
            solution = q.get("solution", q.get("answer", ""))
            self.session["questions_completed"] += 1
            self.session["explained_current"] = True
            self._advance_question()

            if self.session["session_ended"]:
                speech = self._generate_speech(
                    f"{self.session['student_name']} was stuck. Explain simply: {solution}. "
                    f"Then wrap up the session warmly."
                )
            else:
                nq_text = self._get_next_question_text()
                speech = self._generate_speech(
                    f"{self.session['student_name']} has said 'I don't know' 3 times. "
                    f"They're stuck. Don't push anymore. Explain the answer kindly and simply: {solution}. "
                    f"Then say 'Koi baat nahi, chalo next one try karte hain' and read: {nq_text}"
                )

            self.session["history"].append({
                "student": student_input, "teacher": speech,
                "tool": "explain_solution", "correct": False
            })
            self.session["last_tool"] = "explain_solution"
            self.session["explained_current"] = False
            return speech

        # ============================================================
        # NORMAL PATH: LLM picks tool
        # ============================================================
        question_context = self._build_question_context()
        history_context = self._build_history_context()

        if is_idk:
            situation = (
                f'{self.session["student_name"]} said: "{student_input}"\n'
                f"They don't know the answer or want help. IDK count: {self.session['idk_count']}.\n"
                f"If they've asked for an explanation, give them one. "
                f"Don't keep pushing micro-questions if they need the concept explained."
            )
        elif is_offtopic:
            situation = (
                f'{self.session["student_name"]} said: "{student_input}"\n'
                f"Off-topic. Redirect briefly in ONE sentence, then re-read the question."
            )
        else:
            situation = (
                f'{self.session["student_name"]} answered: "{student_input}"\n'
                f"Check against answer key. Spoken math: '2 by 3' = 2/3, 'minus 5' = -5, "
                f"'seven' = 7, 'negative one over seven' = -1/7."
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
            self.session["explained_current"] = True
            self._advance_question()
        elif tool_name == "end_session":
            self.session["session_ended"] = True

        # Build speech — ALWAYS include next question after explain/praise
        next_q_info = ""
        if tool_name in ("praise_and_continue", "explain_solution"):
            self.session["explained_current"] = False  # Reset for next question
            if not self.session["session_ended"]:
                nq_text = self._get_next_question_text()
                next_q_info = (
                    f'\n\nAFTER your response, transition to the next question. '
                    f'Say "Chalo, next one" or similar, then read: {nq_text}'
                )
            else:
                next_q_info = "\n\nThat was the last question. Wrap up warmly."

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
        self.session["last_tool"] = tool_name

        return speech

    def _advance_question(self):
        self.session["current_question_index"] += 1
        self.session["hint_count"] = 0
        self.session["attempt_count"] = 0
        self.session["idk_count"] = 0
        self.session["offtopic_streak"] = 0
        self.session["explained_current"] = False
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
        for char in ['**', '*', '##', '#', '`', '•']:
            text = text.replace(char, '')
        text = text.replace('- ', '')

        text = re.sub(r'\\\(.*?\\\)', '', text)
        text = re.sub(r'\\\[.*?\\\]', '', text)

        text = re.sub(r'-(\d+)/(\d+)', r'minus \1 over \2', text)
        text = re.sub(r'(\d+)/(\d+)', r'\1 over \2', text)

        if len(text) > 2 and text[0] == '"' and text[-1] == '"':
            text = text[1:-1]
        if len(text) > 2 and text[0] == "'" and text[-1] == "'":
            text = text[1:-1]
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
            f"Reason: {reason}. Say bye naturally. 2 sentences max."
        )
        return self._generate_speech(prompt)

    # ============================================================
    # DETECTION METHODS
    # ============================================================

    def _is_stop_request(self, text: str) -> bool:
        stop = ["stop", "bye", "quit", "end", "done", "that's it", "the end",
                "i want to stop", "can we stop", "let's stop", "enough",
                "bas", "band karo", "ruko", "stop for today",
                "can we stop for today", "that's all for today",
                "let's stop for today"]
        return any(p in text.lower() for p in stop)

    def _is_offtopic(self, text: str) -> bool:
        if any(c.isdigit() for c in text):
            return False
        if "/" in text or "by" in text.lower():
            return False
        offtopic = ["who are you", "what is your name", "tell me a joke",
                    "play a game", "sing a song", "what can you do",
                    "how are you", "what's up", "give me a daily",
                    "day to day", "daily life", "real life example"]
        return any(p in text.lower() for p in offtopic)

    def _is_trolling(self, text: str) -> bool:
        """Detect nonsense / trolling / not-engaged input."""
        troll = ["subscribe", "like and subscribe", "thanks for watching",
                 "thank you for watching", "hit the bell", "smash the like",
                 "comment below", "share this video", "background chatter",
                 "hello youtube", "hey guys", "what's up guys",
                 "lol", "lmao", "hahaha", "hehe",
                 "blah blah", "asdf", "test test", "testing",
                 "aaa", "bbb", "zzz"]
        text_lower = text.lower().strip()
        if any(p in text_lower for p in troll):
            return True
        # Very short random text (1-2 chars) that's not a number
        if len(text_lower) <= 2 and not any(c.isdigit() for c in text_lower):
            return True
        return False

    def _is_idk(self, text: str) -> bool:
        idk = ["i don't know", "i dont know", "idk", "no idea",
               "tell me the answer", "just tell me", "skip",
               "i can't", "i cant", "nahi pata", "pata nahi",
               "what is the answer", "give me the answer",
               "please explain", "explain to me", "please start",
               "mujhe nahi aata", "samajh nahi aa raha",
               "can you explain", "explain the chapter", "teach me",
               "what is fraction", "what are fractions", "what is a fraction",
               "can you teach me", "i'm confused", "i am confused",
               "help me", "no clue", "not sure"]
        return any(p in text.lower() for p in idk)

    def _is_acknowledgment(self, text: str) -> bool:
        """Detect student acknowledging they understood."""
        text_lower = text.lower().strip().rstrip('.!,')
        acks = ["yeah", "yes", "okay", "ok", "got it", "i got it", "makes sense",
                "i understand", "understood", "right", "alright", "fine", "sure",
                "haan", "theek hai", "theek", "samajh gaya", "samajh gayi",
                "accha", "oh okay", "oh ok", "yep", "yup", "hmm okay",
                "okay okay", "i see", "ah okay", "ah ok", "clear",
                "that's clear", "kind of", "sort of", "hmm", "mm",
                "yeah yeah", "yes yes", "ok ok", "ji", "ji haan",
                "samajh aa gaya", "samajh aa gayi", "haan samjha",
                "that makes sense", "oh i see", "ohh", "acha",
                "yeah i got it", "yes i understand", "hmm okay got it"]
        if len(text_lower.split()) <= 6:
            return any(text_lower == ack or text_lower.startswith(ack)
                      for ack in acks)
        return False

    def _wants_english(self, text: str) -> bool:
        eng = ["speak in english", "english please", "in english",
               "can you speak english", "talk in english", "use english",
               "can you speak in english", "explain in english"]
        return any(p in text.lower() for p in eng)

    def _wants_other_language(self, text: str) -> str:
        """Detect request for unsupported language. Returns language name or empty."""
        languages = {
            "telugu": "Telugu", "tamil": "Tamil", "kannada": "Kannada",
            "malayalam": "Malayalam", "bengali": "Bengali", "bangla": "Bengali",
            "marathi": "Marathi", "gujarati": "Gujarati", "punjabi": "Punjabi",
            "odia": "Odia", "assamese": "Assamese", "urdu": "Urdu",
            "spanish": "Spanish", "french": "French", "german": "German",
            "chinese": "Chinese", "japanese": "Japanese", "korean": "Korean",
            "arabic": "Arabic"
        }
        text_lower = text.lower()
        if "speak" in text_lower or "talk" in text_lower or "language" in text_lower or "can you" in text_lower:
            for key, name in languages.items():
                if key in text_lower:
                    return name
        return ""

    def get_session_state(self) -> dict:
        q = self.session.get("current_question", {})
        return {
            "student_name": self.session["student_name"],
            "chapter": self.session["chapter"],
            "chapter_name": self.session.get("chapter_name", ""),
            "questions_completed": self.session["questions_completed"],
            "total_questions": self.session["total_questions"],
            "score": self.session["score"],
            "hint_count": self.session["hint_count"],
            "attempt_count": self.session["attempt_count"],
            "duration_minutes": self.session["duration_minutes"],
            "session_ended": self.session["session_ended"],
            "current_question_text": q.get("text", q.get("question_text", "")),
            "current_question_meta": {
                "topic": q.get("subtopic", q.get("topic", "")),
                "difficulty": q.get("difficulty", 1),
                "image_url": q.get("image_url", None),
            }
        }
