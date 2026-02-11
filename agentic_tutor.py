"""
IDNA Agentic Tutor v3.1 — With Tutor Brain
=============================================
Architecture:
  input_classifier.py  → classifies student input (pure Python)
  tutor_states.py      → state machine transitions (pure Python)
  tutor_brain.py       → pedagogical reasoning (pure Python) ← NEW
  didi_voice.py        → LLM speech generation (all LLM calls)
  agentic_tutor.py     → THIS FILE: orchestrator

The brain sits between state machine and voice:
  classify → transition → BRAIN ENRICHES → voice generates

What the brain does:
  1. Before each question: builds a teaching plan (pre-teach? scaffold? examples?)
  2. Before each response: injects context packet ("student is frustrated, needs examples")
  3. After each interaction: updates student model (confidence, error patterns, learning style)
  4. At session end: generates summary for parent reports

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
from tutor_brain import TutorBrain
import didi_voice as voice


class AgenticTutor:

    def __init__(self, student_name: str, chapter: str):
        self.session = self._init_session(student_name, chapter)
        self.brain = TutorBrain(student_name)

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
        q_text = q.get("text", q.get("question_text", ""))
        name = self.session["student_name"]
        lang = self.session["language"]

        # Brain plans for first question
        plan = self.brain.plan_for_question(q, self.session)

        if plan.should_pre_teach:
            # Brain says: teach the concept before asking
            pre_teach = plan.pre_teach_instruction
            instruction = (
                f"{name} just sat down. You're doing {self.session['chapter_name']} today. "
                f"Say hi warmly. Then: {pre_teach} "
                f"After teaching the concept, read the first question: {q_text}"
            )
            speech = voice.generate_speech(instruction, name, lang, "")
        else:
            speech = voice.generate_greeting(
                student_name=name,
                chapter_name=self.session["chapter_name"],
                question_text=q_text,
                lang=lang
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

        # 2. Language switch
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

        if category == "LANG_UNSUPPORTED":
            meta["language"] = result["detail"]

        # 5. Execute action (brain-enriched)
        speech = self._execute_action(action, student_input, meta, category)

        # 6. Brain observes what happened
        self.brain.observe_interaction(
            student_input=student_input,
            category=category,
            action=action.value,
            question=self.session.get("current_question", {})
        )

        # 7. Update state
        self.session["state"] = next_state
        if next_state == State.ENDED:
            self.session["session_ended"] = True

        # 8. History
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
            },
            # Brain data for frontend/debugging
            "brain": {
                "confidence": self.brain.student.confidence_level,
                "struggling": self.brain.student.concepts_struggling[-3:],
                "error_patterns": self.brain.student.error_patterns[-3:],
                "needs_examples": self.brain.student.needs_concrete_examples,
                "needs_concept_teaching": self.brain.student.needs_concept_teaching,
            }
        }

    def get_session_summary(self) -> dict:
        """For parent reports and debugging."""
        return self.brain.get_session_summary()

    # ============================================================
    # ACTION EXECUTOR — now brain-enriched
    # ============================================================

    def _execute_action(self, action: Action, student_input: str,
                        meta: dict, category: str) -> str:
        q_ctx = self._build_question_context()
        q_text = self._current_question_text()
        history = self._build_history()
        name = self.session["student_name"]
        lang = self.session["language"]
        tone = self.session.get("tone", "casual")  # "casual" or "formal"

        # If formal tone, append instruction to lang
        if tone == "formal":
            lang = lang + "_formal"

        # Brain's context packet — injected into every LLM call
        brain_ctx = self.brain.get_context_packet()
        if brain_ctx:
            q_ctx = brain_ctx + "\n\n" + q_ctx

        # ---- JUDGE_AND_RESPOND ----
        if action == Action.JUDGE_AND_RESPOND:
            judge_input = (
                q_ctx + f'\n\nStudent answered: "{student_input}"\n'
                f'Check against answer key. Spoken math: "2 by 3" = 2/3, "minus 5" = -5, "minus one" = -1.\n\n'
                f'PARTIAL ANSWER RULE: If the student said the numerator correctly but forgot the denominator '
                f'(e.g. answer is "-1/7" and student said "minus 1" or "-1"), use give_hint to acknowledge '
                f'the correct part and guide them to the full answer. Do NOT use ask_what_they_did for partial answers.'
            )
            result = voice.judge_answer(judge_input, q_ctx, name, lang, history)
            tool = result["tool"]
            args = result["args"]

            if tool == "praise_and_continue":
                self.session["score"] += 1
                self.session["questions_completed"] += 1
                self._advance_question()
                self.session["state"] = State.TRANSITIONING
                # Brain plans for next question
                if not self.session["session_ended"]:
                    self.brain.plan_for_question(self.session["current_question"], self.session)
                nq = self._current_question_text()
                pre_teach = self.brain.get_pre_teach_instruction()
                if pre_teach and nq:
                    instr = voice.build_praise_instruction(
                        q_ctx, args.get("what_they_did_well", "got it right"), ""
                    ) + f"\n\nBefore the next question, {pre_teach}\nThen ask: {nq}"
                else:
                    instr = voice.build_praise_instruction(
                        q_ctx, args.get("what_they_did_well", "got it right"), nq
                    )

            elif tool == "give_hint":
                level = args.get("hint_level", 1)
                self.session["hint_count"] = max(self.session["hint_count"], level)
                self.session["state"] = State.HINTING
                # Brain may have a better hint
                enhanced = self.brain.get_enhanced_hint(level)
                if enhanced:
                    instr = voice.build_hint_instruction(q_ctx, level, student_input) + f"\n\nBrain suggests: {enhanced}"
                else:
                    instr = voice.build_hint_instruction(q_ctx, level, student_input)

            elif tool == "explain_solution":
                self.session["questions_completed"] += 1
                self._advance_question()
                self.session["state"] = State.EXPLAINING
                if not self.session["session_ended"]:
                    self.brain.plan_for_question(self.session["current_question"], self.session)
                nq = self._current_question_text()
                instr = voice.build_explain_instruction(q_ctx, nq)

            elif tool == "encourage_attempt":
                # Brain enriches encouragement
                brain_encourage = self.brain.get_encouragement_instruction()
                instr = voice.build_encourage_instruction(q_ctx, student_input) + f"\n\n{brain_encourage}"

            elif tool == "ask_what_they_did":
                # Brain override 1: student needs concept teaching
                if self.brain.student.needs_concept_teaching:
                    instr = (
                        f"Student needs the concept explained. Don't ask what they did — "
                        f"they don't understand the basics. Teach the concept simply with "
                        f"a concrete example, then re-read the question.\n\n{q_ctx}"
                    )
                # Brain override 2: already asked once — don't loop
                elif self._count_action_in_history("ask_what_they_did") >= 1:
                    instr = (
                        f'Student said: "{student_input}". You already asked them to explain '
                        f'their thinking. Do NOT ask again. Instead:\n'
                        f'- If their reasoning sounds correct, confirm and guide to final answer.\n'
                        f'- If wrong, point out the specific mistake gently.\n'
                        f'- If unclear, give a concrete hint.\n\n{q_ctx}'
                    )
                # Brain override 3: student is frustrated
                elif self.brain.student.frustration_signals >= 2:
                    instr = (
                        f"Student is frustrated. Don't ask what they did — just help. "
                        f"Give a clear hint or explain.\n\n{q_ctx}"
                    )
                else:
                    instr = f'Student answered: "{student_input}". Ask what they did — be curious, ONE question only.\n{q_ctx}'

            elif tool == "end_session":
                return self._end_speech("student_requested")

            else:
                instr = voice.build_hint_instruction(q_ctx, 1, student_input)

            return voice.generate_speech(instr, name, lang, history)

        # ---- GIVE_HINT (forced by state machine) ----
        elif action == Action.GIVE_HINT:
            level = meta.get("hint_level", min(self.session["hint_count"] + 1, 2))
            self.session["hint_count"] = max(self.session["hint_count"], level)
            enhanced = self.brain.get_enhanced_hint(level)
            instr = voice.build_hint_instruction(q_ctx, level, student_input)
            if enhanced:
                instr += f"\n\nBrain suggests: {enhanced}"
            return voice.generate_speech(instr, name, lang, history)

        # ---- EXPLAIN_SOLUTION (forced by state machine) ----
        elif action == Action.EXPLAIN_SOLUTION:
            self.session["questions_completed"] += 1
            self._advance_question()
            if not self.session["session_ended"]:
                self.brain.plan_for_question(self.session["current_question"], self.session)
            nq = self._current_question_text()
            instr = voice.build_explain_instruction(q_ctx, nq)
            # If student needs examples, tell the LLM
            if self.brain.student.needs_concrete_examples:
                instr += "\n\nUSE A CONCRETE EXAMPLE in your explanation — everyday objects like money, sharing food, or temperature."
            return voice.generate_speech(instr, name, lang, history)

        # ---- ENCOURAGE ----
        elif action == Action.ENCOURAGE:
            brain_encourage = self.brain.get_encouragement_instruction()
            instr = voice.build_encourage_instruction(q_ctx, student_input)
            instr += f"\n\n{brain_encourage}"
            return voice.generate_speech(instr, name, lang, history)

        # ---- MOVE_TO_NEXT ----
        elif action == Action.MOVE_TO_NEXT:
            self.session["questions_completed"] += 1
            self._advance_question()
            if self.session["session_ended"]:
                return self._end_speech("completed_all_questions")
            # Brain plans for next question
            self.brain.plan_for_question(self.session["current_question"], self.session)
            nq = self._current_question_text()
            pre_teach = self.brain.get_pre_teach_instruction()
            if pre_teach:
                instr = (
                    f"Student understood. Move on. Say something brief like 'Good, next one.' "
                    f"Then: {pre_teach} "
                    f"After teaching the concept briefly, ask: {nq}"
                )
            else:
                instr = voice.build_move_next_instruction(nq)
            return voice.generate_speech(instr, name, lang, history)

        # ---- RE_ASK ----
        elif action == Action.RE_ASK:
            instr = voice.build_reask_instruction(q_text, meta.get("after_hint", False))
            return voice.generate_speech(instr, name, lang, history)

        # ---- REDIRECTS ----
        elif action == Action.REDIRECT_TROLL:
            instr = voice.build_redirect_instruction(student_input, q_text, is_troll=True)
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.REDIRECT_OFFTOPIC:
            instr = voice.build_redirect_instruction(student_input, q_text, is_troll=False)
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.OFFER_EXIT:
            instr = voice.build_offer_exit_instruction(name)
            return voice.generate_speech(instr, name, lang, history)

        # ---- LANGUAGE ----
        elif action == Action.SWITCH_LANGUAGE:
            instr = voice.build_language_switch_instruction(q_text)
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.REJECT_LANGUAGE:
            instr = voice.build_language_reject_instruction(meta.get("language", "that language"), q_text)
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.ADJUST_TONE:
            # Set formal mode in session
            self.session["tone"] = "formal"
            instr = voice.build_tone_adjustment_instruction(q_text)
            return voice.generate_speech(instr, name, lang, history)

        # ---- END ----
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

    def _count_action_in_history(self, action_name: str) -> int:
        """Count how many times an action has been used for the current question.
        Resets when question advances (history tracks all, but we count from last advance)."""
        count = 0
        for h in reversed(self.session.get("history", [])):
            if h.get("action") == action_name:
                count += 1
            # Stop counting when we hit a question transition
            if h.get("action") in ("praise_and_continue", "explain_solution", "move_to_next"):
                break
        return count

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
        # Get brain summary for logging
        summary = self.brain.get_session_summary()
        print(f"[Session Summary] {json.dumps(summary, indent=2)}")
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


# Need json for summary logging
import json
