"""
IDNA Agentic Tutor v3.0 — State Machine Architecture
======================================================
Clean separation:
  input_classifier.py  → classifies student input (pure Python)
  tutor_states.py      → state machine transitions (pure Python)
  didi_voice.py        → LLM speech generation (all LLM calls)
  agentic_tutor.py     → THIS FILE: orchestrator + session state

Public interface (unchanged):
  AgenticTutor(student_name, chapter)
  await tutor.start_session() → str
  await tutor.process_input(text) → str
  tutor.get_session_state() → dict
"""

import time
from questions import ALL_CHAPTERS, CHAPTER_NAMES

import input_classifier as classifier
from tutor_states import State, Action, get_transition
import didi_voice as voice


class AgenticTutor:

    def __init__(self, student_name: str, chapter: str):
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
            "offtopic_streak": 0,
            "language": "hinglish",
            "history": [],
            "duration_minutes": 0,
            "start_time": time.time(),
            "state": State.GREETING,
            "session_ended": False
        }

    # ============================================================
    # PUBLIC INTERFACE
    # ============================================================

    async def start_session(self) -> str:
        q = self.session["current_question"]
        speech = voice.generate_greeting(
            student_name=self.session["student_name"],
            chapter_name=self.session["chapter_name"],
            question_text=q.get("text", q.get("question_text", "")),
            lang=self.session["language"]
        )
        self.session["state"] = State.WAITING_ANSWER
        return speech

    async def process_input(self, student_input: str) -> str:
        if self.session["session_ended"]:
            return "Session khatam ho gaya. New session start karo."

        self.session["duration_minutes"] = int(
            (time.time() - self.session["start_time"]) / 60
        )

        # 1. Classify
        result = classifier.classify(student_input)
        category = result["category"]

        # 2. Language switch side-effect
        if category == "LANGUAGE":
            self.session["language"] = result["detail"]

        # 3. Update counters
        if category == "IDK":
            self.session["idk_count"] += 1
        elif category == "ANSWER":
            self.session["attempt_count"] += 1
        elif category in ("TROLL", "OFFTOPIC"):
            self.session["offtopic_streak"] += 1
        elif category not in ("ACK", "LANGUAGE", "LANG_UNSUPPORTED"):
            self.session["offtopic_streak"] = 0

        # 4. State machine transition
        transition = get_transition(
            state=self.session["state"],
            category=category,
            session=self.session
        )

        action = transition["action"]
        next_state = transition["next_state"]
        meta = transition["meta"]

        # Pass language detail for LANG_UNSUPPORTED
        if category == "LANG_UNSUPPORTED":
            meta["language"] = result["detail"]

        # 5. Execute → speech
        speech = self._execute_action(action, student_input, meta)

        # 6. Update state
        self.session["state"] = next_state
        if next_state == State.ENDED:
            self.session["session_ended"] = True

        # 7. History
        self.session["history"].append({
            "student": student_input,
            "teacher": speech,
            "action": action.value,
            "category": category
        })

        return speech

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

    # ============================================================
    # ACTION EXECUTOR
    # ============================================================

    def _execute_action(self, action: Action, student_input: str, meta: dict) -> str:
        q_ctx = self._build_question_context()
        q_text = self._current_question_text()
        history = self._build_history()
        name = self.session["student_name"]
        lang = self.session["language"]

        if action == Action.JUDGE_AND_RESPOND:
            judge_ctx = q_ctx + f'''

Student answered: "{student_input}"

INSTRUCTION: Compare student answer to correct answer above.
Spoken math: "minus 1 by 7" = -1/7, "2 by 3" = 2/3, "negative one seventh" = -1/7

IF CORRECT → use praise_and_continue
IF WRONG → use ask_what_they_did (first time) or give_hint (after asking)'''
            result = voice.judge_answer(judge_ctx, q_ctx, name, lang, history)
            tool = result["tool"]
            args = result["args"]

            if tool == "praise_and_continue":
                self.session["score"] += 1
                self.session["questions_completed"] += 1
                self._advance_question()
                self.session["state"] = State.TRANSITIONING
                nq = self._current_question_text()
                instr = voice.build_praise_instruction(q_ctx, args.get("what_they_did_well", "got it right"), nq)

            elif tool == "give_hint":
                level = args.get("hint_level", 1)
                self.session["hint_count"] = max(self.session["hint_count"], level)
                self.session["state"] = State.HINTING
                instr = voice.build_hint_instruction(q_ctx, level, student_input)

            elif tool == "explain_solution":
                self.session["questions_completed"] += 1
                self._advance_question()
                self.session["state"] = State.EXPLAINING
                nq = self._current_question_text()
                instr = voice.build_explain_instruction(q_ctx, nq)

            elif tool == "encourage_attempt":
                instr = voice.build_encourage_instruction(q_ctx, student_input)

            elif tool == "ask_what_they_did":
                instr = f'Student answered: "{student_input}". Ask what they did — be curious. Question:\n{q_ctx}'

            elif tool == "end_session":
                return self._end_speech("student_requested")

            else:
                instr = voice.build_hint_instruction(q_ctx, 1, student_input)

            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.GIVE_HINT:
            level = meta.get("hint_level", min(self.session["hint_count"] + 1, 2))
            self.session["hint_count"] = max(self.session["hint_count"], level)
            instr = voice.build_hint_instruction(q_ctx, level, student_input)
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.EXPLAIN_SOLUTION:
            self.session["questions_completed"] += 1
            self._advance_question()
            nq = self._current_question_text()
            instr = voice.build_explain_instruction(q_ctx, nq)
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.ENCOURAGE:
            instr = voice.build_encourage_instruction(q_ctx, student_input)
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.MOVE_TO_NEXT:
            self.session["questions_completed"] += 1
            self._advance_question()
            if self.session["session_ended"]:
                return self._end_speech("completed_all_questions")
            nq = self._current_question_text()
            instr = voice.build_move_next_instruction(nq)
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.RE_ASK:
            instr = voice.build_reask_instruction(q_text, meta.get("after_hint", False))
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.REDIRECT_TROLL:
            instr = voice.build_redirect_instruction(student_input, q_text, is_troll=True)
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.REDIRECT_OFFTOPIC:
            instr = voice.build_redirect_instruction(student_input, q_text, is_troll=False)
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.OFFER_EXIT:
            instr = voice.build_offer_exit_instruction(name)
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.SWITCH_LANGUAGE:
            instr = voice.build_language_switch_instruction(q_text)
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.REJECT_LANGUAGE:
            instr = voice.build_language_reject_instruction(meta.get("language", "that language"), q_text)
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.END_SESSION:
            return self._end_speech(meta.get("reason", "unknown"))

        return voice.generate_speech(f"Re-read: {q_text}", name, lang, history)

    # ============================================================
    # HELPERS
    # ============================================================

    def _advance_question(self):
        self.session["current_question_index"] += 1
        self.session["hint_count"] = 0
        self.session["attempt_count"] = 0
        self.session["idk_count"] = 0
        self.session["offtopic_streak"] = 0
        if self.session["current_question_index"] < len(self.session["questions"]):
            self.session["current_question"] = self.session["questions"][
                self.session["current_question_index"]
            ]
        else:
            self.session["session_ended"] = True

    def _current_question_text(self) -> str:
        q = self.session.get("current_question", {})
        return q.get("text", q.get("question_text", ""))

    def _build_question_context(self) -> str:
        q = self.session["current_question"]
        s = self.session

        steps = q.get("solution_steps", [])
        if isinstance(steps, list):
            steps = " → ".join(steps)

        mistakes = ""
        for m in q.get("common_mistakes", []):
            mistakes += f'  "{m["wrong_answer"]}": {m.get("diagnosis", "?")} (say: "{m.get("micro_hint", "")}")\n'

        return f"""=== CURRENT QUESTION (ONLY this question matters) ===
Q{s['current_question_index'] + 1}/{s['total_questions']} | Score: {s['score']}/{s['questions_completed']} | {s['duration_minutes']}min
Hints: {s['hint_count']}/2 | Attempts: {s['attempt_count']} | IDKs: {s['idk_count']}

QUESTION: {q.get('text', q.get('question_text', ''))}
Topic: {q.get('topic', '')} / {q.get('subtopic', '')}

ANSWER KEY (never reveal unless explaining):
Correct: {q.get('answer', '')}
Also accept: {q.get('accept_also', [])}
Solution: {steps}
Full: {q.get('solution', '')}

COMMON MISTAKES:
{mistakes if mistakes else '(none)'}

HINTS:
L1: {q.get('hint_1', q.get('hint', ''))}
L2: {q.get('hint_2', '')}"""

    def _build_history(self) -> str:
        recent = self.session.get("history", [])[-3:]
        if not recent:
            return ""
        lines = ["Recent (tone reference only — do NOT discuss old questions):"]
        for h in recent:
            short = h['teacher'][:80] + "..." if len(h['teacher']) > 80 else h['teacher']
            lines.append(f"  {self.session['student_name']}: {h['student']}")
            lines.append(f"  Didi: {short}")
        return "\n".join(lines)

    def _end_speech(self, reason: str) -> str:
        self.session["session_ended"] = True
        self.session["state"] = State.ENDED
        return voice.generate_speech(
            voice.build_end_instruction(
                self.session["student_name"],
                self.session["score"],
                self.session["questions_completed"],
                self.session["duration_minutes"],
                reason
            ),
            self.session["student_name"],
            self.session["language"],
            self._build_history()
        )
