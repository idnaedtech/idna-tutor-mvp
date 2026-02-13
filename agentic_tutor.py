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
from answer_checker import check_answer
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

        # v5.0: Never use "Student" as a default name
        clean_name = student_name.strip() if student_name else ""
        if clean_name.lower() == "student":
            clean_name = ""

        return {
            "student_name": clean_name,
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
            "session_ended": False,
            # v4.2: Track repeated scaffolding to prevent sub-question loops
            "last_didi_question": None,
            "didi_repeat_count": 0,
            # v4.12: Track consecutive unclear inputs to break "samajh nahi aaya" loop
            "consecutive_unclear": 0,
            # v6.0.1: Split teach and question into separate turns
            "needs_first_question": True
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

        # v6.0: ALWAYS teach before the first question
        # Get the skill lesson for this question's target skill
        from questions import SKILL_LESSONS
        skill = q.get("target_skill", "")
        skill_lesson = SKILL_LESSONS.get(skill, "")

        # Build a teaching instruction
        if plan.should_pre_teach:
            pre_teach = plan.pre_teach_instruction
        elif skill_lesson:
            pre_teach = (
                f"Before asking the question, teach this concept simply with a real-life example "
                f"that a 13-year-old in India would relate to: {skill_lesson}. "
                f"Use an example with roti, pocket money, or sharing sweets. "
                f"Then say 'Samajh aaya?' and wait."
            )
        else:
            pre_teach = (
                f"Before asking the question, briefly explain what the student needs to know "
                f"to solve it. Use a real-life example. Then say 'Samajh aaya?' and wait."
            )

        # v6.0.1: Only teach in first turn, question comes after student responds
        instruction = (
            f"{name} just sat down for tutoring. You're doing {self.session['chapter_name']} today. "
            f"Say namaste warmly — one sentence only. "
            f"Then teach this concept simply: {pre_teach} "
            f"End with 'Samajh aaya?' and STOP. Do NOT read any question yet. "
            f"Keep your total response under 5 sentences."
        )
        speech = voice.generate_speech(instruction, name, lang, "")

        self.session["state"] = State.WAITING_ANSWER
        return speech

    async def process_input(self, student_input: str) -> str:
        if self.session["session_ended"]:
            return "Session khatam ho gaya. New session start karo."

        self.session["duration_minutes"] = int(
            (time.time() - self.session["start_time"]) / 60
        )

        # v6.0.1: Handle response to "Samajh aaya?" before first question
        if self.session.get("needs_first_question"):
            self.session["needs_first_question"] = False
            category = classifier.classify(student_input)["category"]
            if category in ("ACK", "ANSWER"):
                # Student understood, now read the question
                q_text = self._current_question_text()
                speech = voice.generate_speech(
                    f"Bahut accha! Ab ek question try karte hain: {q_text}",
                    self.session["student_name"],
                    self.session["language"],
                    self._build_history()
                )
                return speech
            elif category in ("IDK", "CONCEPT_REQUEST"):
                # Student needs more teaching
                q = self.session["current_question"]
                skill = q.get("target_skill", "")
                from questions import SKILL_LESSONS
                skill_lesson = SKILL_LESSONS.get(skill, "this concept")
                speech = voice.generate_speech(
                    f"Koi baat nahi. Let me explain differently: {skill_lesson}. "
                    f"Use a different real-life example this time. End with 'Ab samjhe?'",
                    self.session["student_name"],
                    self.session["language"],
                    self._build_history()
                )
                # Keep needs_first_question True so next ACK will show the question
                self.session["needs_first_question"] = True
                return speech
            # For STOP, TROLL etc, fall through to normal flow

        # 0. Filter nonsensical/ambient noise (TV, background chatter)
        # Do NOT penalize student for background noise
        # Use the CURRENT question, not questions extracted from last response
        if classifier.is_nonsensical(student_input):
            self.session["consecutive_unclear"] += 1
            q_text = self._current_question_text()
            print(f"[NOISE] Input: '{student_input}', consecutive: {self.session['consecutive_unclear']}")

            # After 3+ consecutive unclear inputs, force explain and advance
            if self.session["consecutive_unclear"] >= 3:
                print(f"[NOISE] 3+ unclear inputs, forcing explain")
                self.session["consecutive_unclear"] = 0
                self.session["questions_completed"] += 1
                self._advance_question()
                if self.session["session_ended"]:
                    return self._end_speech("completed_all_questions")
                # Build explain instruction
                q_ctx = self._build_question_context()
                nq = self._current_question_text()
                name = self.session["student_name"]
                lang = self.session["language"]
                history = self._build_history()
                instr = (
                    f"{name}, lagta hai awaaz mein problem aa rahi hai. "
                    f"Koi baat nahi, main answer samjha deti hoon.\n\n"
                    f"Explain the solution simply, then move to: {nq}"
                )
                return voice.generate_speech(instr, name, lang, history)

            return f"{self.session['student_name']}, samajh nahi aaya. {q_text}"

        # Valid input received — reset consecutive unclear counter
        self.session["consecutive_unclear"] = 0

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
        elif category not in ("ACK", "LANGUAGE", "LANG_UNSUPPORTED", "CONFIRM"):
            self.session["offtopic_streak"] = 0

        # 3b. Handle CONFIRM — student asking "was my answer correct?"
        if category == "CONFIRM":
            return self._handle_confirm_request()

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
        self._last_tool = None  # Track LLM tool for history
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

        # 8. History — store both state machine action AND LLM tool
        self.session["history"].append({
            "student": student_input,
            "teacher": speech,
            "action": action.value,
            "tool": self._last_tool,  # e.g. "ask_what_they_did", "give_hint"
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
            # CIRCUIT BREAKER: If student has been on this question for 5+ turns, force explain
            turns_on_question = 0
            for h in reversed(self.session.get("history", [])):
                if h.get("tool") in ("praise_and_continue", "explain_solution") or \
                   h.get("action") in ("praise_and_continue", "explain_solution", "move_to_next"):
                    break
                turns_on_question += 1

            if turns_on_question >= 4:
                # Force explain — student has been stuck too long
                self.session["questions_completed"] += 1
                self._advance_question()
                self.session["state"] = State.EXPLAINING
                if not self.session["session_ended"]:
                    self.brain.plan_for_question(self.session["current_question"], self.session)
                nq = self._current_question_text()
                self._last_tool = "explain_solution"
                instr = voice.build_explain_instruction(q_ctx, nq)
                return voice.generate_speech(instr, name, lang, history)

            # ---- DETERMINISTIC CHECK (before LLM) ----
            q = self.session["current_question"]
            answer_key = q.get("answer", "")
            accept_also = q.get("accept_also", [])
            deterministic_result = check_answer(student_input, answer_key, accept_also)

            if deterministic_result is True:
                # CORRECT — bypass LLM, force praise_and_continue
                self._last_tool = "praise_and_continue"
                self.session["score"] += 1
                self.session["questions_completed"] += 1
                self._advance_question()
                self.session["state"] = State.TRANSITIONING
                if not self.session["session_ended"]:
                    self.brain.plan_for_question(self.session["current_question"], self.session)
                nq = self._current_question_text()
                pre_teach = self.brain.get_pre_teach_instruction()
                if pre_teach and nq:
                    instr = voice.build_praise_instruction(q_ctx, "got it right", "") + \
                            f"\n\nBefore the next question, {pre_teach}\nThen ask: {nq}"
                else:
                    instr = voice.build_praise_instruction(q_ctx, "got it right", nq)
                return voice.generate_speech(instr, name, lang, history)

            if deterministic_result is None:
                # PARTIAL — bypass LLM, force guide_partial_answer
                self._last_tool = "guide_partial_answer"
                self.session["state"] = State.HINTING
                # Detect what's partial
                if '/' in answer_key:
                    correct_part = "numerator is correct"
                    missing_part = "include the denominator"
                else:
                    correct_part = "the magnitude is correct"
                    missing_part = "check the sign"
                instr = (
                    f"Student's answer is PARTIALLY correct.\n"
                    f"What they got right: {correct_part}\n"
                    f"What's missing: {missing_part}\n\n"
                    f"Acknowledge the correct part FIRST. "
                    f"Then guide them to the missing piece with ONE specific question.\n\n"
                    f"{q_ctx}"
                )
                return voice.generate_speech(instr, name, lang, history)

            # ---- WRONG or AMBIGUOUS — pass to LLM ----
            # v4.2: Check if student is repeating same answer (stuck)
            student_repeating = self._student_repeating_answer()

            # Build sub-question context from last Didi response
            last_didi_response = ""
            if self.session.get("history"):
                last_didi_response = self.session["history"][-1].get("teacher", "")

            # v4.4: Deterministic sub-question answer detection
            sub_answer_correct = self._check_sub_question_answer(last_didi_response, student_input)
            if sub_answer_correct:
                # Student answered a sub-question correctly — acknowledge and guide forward
                self._last_tool = "guide_partial_answer"
                self.session["state"] = State.HINTING
                instr = (
                    f"Student correctly answered your sub-question!\n"
                    f"You asked something like: '{last_didi_response[-150:]}'\n"
                    f"Student said: '{student_input}' which is CORRECT for that sub-step.\n\n"
                    f"Say 'Haan, sahi hai!' or 'Bilkul!' and then guide them to the NEXT step.\n"
                    f"Do NOT re-ask the same sub-question. Move forward.\n\n"
                    f"{q_ctx}"
                )
                return voice.generate_speech(instr, name, lang, history)

            # Include last Didi response for LLM context
            sub_q_context = ""
            if last_didi_response:
                sub_q_context = (
                    f'\n\nYOUR LAST RESPONSE (check if you asked a sub-question):\n'
                    f'"{last_didi_response[-300:]}"\n'
                )

            judge_input = (
                q_ctx + f'\n\nStudent answered: "{student_input}"\n'
                f'{sub_q_context}'
                f'Check against answer key.\n\n'
                f'SPOKEN MATH RULES (Indian English) — parse the FULL phrase before matching:\n'
                f'- "minus X by Y" = -X/Y (e.g. "minus 1 by 7" = -1/7) ← FULL ANSWER\n'
                f'- "minus X over Y" = -X/Y (e.g. "minus 3 over 7" = -3/7) ← FULL ANSWER\n'
                f'- "X by Y" = X/Y (e.g. "5 by 8" = 5/8)\n'
                f'- "X over Y" = X/Y\n'
                f'- "X upon Y" = X/Y\n'
                f'- "minus X" ALONE (no "by/over/upon" after it) = -X\n'
                f'- Numbers as words: "one" = 1, "seven" = 7, "six" = 6\n\n'
                f'CRITICAL: Parse the ENTIRE student answer as one expression. '
                f'"minus 1 by 7" is -1/7, NOT "minus 1" + extra words. '
                f'If it matches the answer key, use praise_and_continue IMMEDIATELY.\n\n'
                f'SUB-QUESTION HANDLING (CRITICAL - READ YOUR LAST RESPONSE ABOVE):\n'
                f'If YOUR LAST RESPONSE asked the student a specific calculation like:\n'
                f'  - "2 times minus 3 kya hoga?" and student says "minus 6" → CORRECT sub-answer!\n'
                f'  - "minus 3 plus 2 kya hoga?" and student says "minus 1" → CORRECT sub-answer!\n'
                f'For correct sub-answers: use guide_partial_answer with correct_part describing what they got right.\n'
                f'Do NOT re-ask the same sub-question. MOVE FORWARD to the next step.\n\n'
                f'DECISION RULES:\n'
                f'- Answer matches FINAL answer key → praise_and_continue\n'
                f'- Answer is correct for a SUB-QUESTION you asked → guide_partial_answer (acknowledge + next step)\n'
                f'- Answer is CLOSE but incomplete → guide_partial_answer\n'
                f'- Answer is WRONG → give_hint\n'
                f'- Student says IDK or is confused → encourage_attempt\n'
                f'- NEVER ask student to explain their thinking. NEVER repeat the same sub-question.'
            )

            # v4.2: Add warning if student is repeating
            if student_repeating:
                judge_input += (
                    f'\n\nWARNING: Student has given the same answer twice. '
                    f'If their answer is correct for a sub-question you asked, acknowledge it and move forward. '
                    f'If still wrong, give a DIFFERENT hint or explain the solution.'
                )
            result = voice.judge_answer(judge_input, q_ctx, name, lang, history)
            tool = result["tool"]
            args = result["args"]
            self._last_tool = tool  # Track for history counter

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

            elif tool == "guide_partial_answer":
                self.session["state"] = State.HINTING
                correct_part = args.get("correct_part", "")
                missing_part = args.get("missing_part", "")
                instr = (
                    f"Student's answer is PARTIALLY correct.\n"
                    f"What they got right: {correct_part}\n"
                    f"What's missing: {missing_part}\n\n"
                    f"Acknowledge the correct part FIRST — 'Haan, {correct_part}.' "
                    f"Then guide them to the missing piece with ONE specific question. "
                    f"Do NOT re-ask the full question. Do NOT ask how they thought about it.\n\n"
                    f"{q_ctx}"
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

            elif tool == "end_session":
                return self._end_speech("student_requested")

            else:
                instr = voice.build_hint_instruction(q_ctx, 1, student_input)

            # Generate speech
            speech = voice.generate_speech(instr, name, lang, history)

            # v4.2: Check for repeat loop AFTER generating speech
            if self._check_repeat_loop(speech):
                # Didi asked the same sub-question 3+ times — force explain
                self.session["questions_completed"] += 1
                self._advance_question()
                self.session["state"] = State.EXPLAINING
                if not self.session["session_ended"]:
                    self.brain.plan_for_question(self.session["current_question"], self.session)
                nq = self._current_question_text()
                self._last_tool = "explain_solution"
                explain_instr = voice.build_explain_instruction(q_ctx, nq)
                return voice.generate_speech(explain_instr, name, lang, history)

            return speech

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
            instr = voice.build_language_switch_instruction(q_text, self.session["language"])
            return voice.generate_speech(instr, name, lang, history)

        elif action == Action.REJECT_LANGUAGE:
            instr = voice.build_language_reject_instruction(meta.get("language", "that language"), q_text)
            return voice.generate_speech(instr, name, lang, history)

        # ---- TEACH_CONCEPT (v5.0) ----
        elif action == Action.TEACH_CONCEPT:
            # Get concept from classification detail (passed via meta or need to re-classify)
            # Re-classify to get concept detail
            result = classifier.classify(student_input)
            concept = result.get("detail", "this concept")
            q = self.session["current_question"]
            q_text_full = q.get("text", q.get("question_text", ""))

            self._last_tool = "teach_concept"
            instr = (
                f"The student asked about '{concept}'. They don't understand it yet. "
                f"PAUSE the current question. Teach '{concept}' using a simple real-life example "
                f"that a 13-year-old in India would relate to. Use 3-4 short sentences max. "
                f"Show at least one number example. "
                f"Then connect it back to the current question: '{q_text_full}'. "
                f"End with an invitation to try the question again. "
                f"Do NOT just define the term. TEACH it with an example."
            )
            speech = voice.generate_speech(instr, name, lang, history)
            # Reset attempt count since we paused to teach
            self.session["attempt_count"] = max(0, self.session["attempt_count"] - 1)
            return speech

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
        # v4.2: Reset repeat tracking on question advance
        self.session["last_didi_question"] = None
        self.session["didi_repeat_count"] = 0
        if self.session["current_question_index"] < len(self.session["questions"]):
            self.session["current_question"] = self.session["questions"][
                self.session["current_question_index"]
            ]
        else:
            self.session["session_ended"] = True

    def _handle_confirm_request(self) -> str:
        """Handle 'was my answer correct?' type questions."""
        # Find the last student answer from history
        last_answer = None
        for h in reversed(self.session.get("history", [])):
            if h.get("category") == "ANSWER":
                last_answer = h.get("student")
                break

        if not last_answer:
            return f"{self.session['student_name']}, pehle answer toh dijiye!"

        # Check against current question
        q = self.session["current_question"]
        answer_key = q.get("answer", "")
        accept_also = q.get("accept_also", [])
        result = check_answer(last_answer, answer_key, accept_also)

        name = self.session["student_name"]
        q_text = self._current_question_text()

        if result is True:
            # Correct! Praise and move on
            self.session["score"] += 1
            self.session["questions_completed"] += 1
            self._advance_question()
            if self.session["session_ended"]:
                return self._end_speech("completed_all_questions")
            nq = self._current_question_text()
            return f"Haan {name}, aapka answer bilkul sahi tha! Chaliye agla sawal: {nq}"
        elif result is None:
            # Partial
            return f"{name}, aapka answer partial sahi tha. Poora answer dijiye: {q_text}"
        else:
            # Wrong
            return f"{name}, wo answer sahi nahi tha. Phir se try kijiye: {q_text}"

    def _extract_sub_question(self, speech: str) -> str:
        """Extract the last question from Didi's response for repeat detection."""
        import re
        # Find last sentence ending with ?
        questions = re.findall(r'[^.!?]*\?', speech)
        if questions:
            return questions[-1].strip().lower()
        # Fallback: last sentence
        sentences = re.split(r'[.!?]', speech)
        return sentences[-2].strip().lower() if len(sentences) > 1 else speech.strip().lower()

    def _check_repeat_loop(self, speech: str) -> bool:
        """Check if Didi is stuck in a sub-question loop. Returns True if should force explain."""
        current_q = self._extract_sub_question(speech)
        last_q = self.session.get("last_didi_question")

        # Check for similar sub-question (fuzzy match)
        if last_q and self._similar_questions(current_q, last_q):
            self.session["didi_repeat_count"] += 1
        else:
            self.session["didi_repeat_count"] = 1

        self.session["last_didi_question"] = current_q

        # Force explain if same sub-question asked 3+ times
        return self.session["didi_repeat_count"] >= 3

    def _similar_questions(self, q1: str, q2: str) -> bool:
        """Check if two questions are essentially the same."""
        import re
        # Normalize: remove filler words, lowercase
        def normalize(q):
            q = q.lower()
            q = re.sub(r'\b(toh|aur|ab|pehle|bataiye|batao|kya|hai|hoga|karo|kariye)\b', '', q)
            q = re.sub(r'[^a-z0-9\s]', '', q)
            return ' '.join(q.split())

        n1, n2 = normalize(q1), normalize(q2)
        # Check if one contains the other or high overlap
        if n1 in n2 or n2 in n1:
            return True
        # Word overlap
        words1, words2 = set(n1.split()), set(n2.split())
        if not words1 or not words2:
            return False
        overlap = len(words1 & words2) / max(len(words1), len(words2))
        return overlap > 0.6

    def _student_repeating_answer(self) -> bool:
        """Check if student gave essentially the same answer twice in a row."""
        history = self.session.get("history", [])
        if len(history) < 2:
            return False
        last_two = [h.get("student", "").lower().strip() for h in history[-2:]]
        if not all(last_two):
            return False
        # Normalize and compare
        from answer_checker import normalize_answer
        return normalize_answer(last_two[0]) == normalize_answer(last_two[1])

    def _check_sub_question_answer(self, didi_response: str, student_input: str) -> bool:
        """
        Check if student correctly answered a sub-question from Didi's last response.
        Returns True if student's answer matches the expected sub-answer.
        """
        if not didi_response:
            return False

        import re
        from answer_checker import normalize_answer

        didi_lower = didi_response.lower()
        student_norm = normalize_answer(student_input)

        # Pattern 1: "X multiplied by Y" or "X times Y" or "X ko Y se multiply"
        # Expected answer: X * Y
        mult_patterns = [
            r'(\d+)\s*(?:multiplied by|times|ko)\s*(?:minus\s*)?(\d+)',
            r'(\d+)\s*(?:multiply|mul)\s*(?:minus\s*)?(\d+)',
            r'(\d+)\s*(?:ko|aur)\s*(?:minus\s*)?(\d+)\s*(?:se\s*)?(?:multiply|mul)',
        ]
        for pattern in mult_patterns:
            match = re.search(pattern, didi_lower)
            if match:
                a, b = int(match.group(1)), int(match.group(2))
                # Check if "minus" appears before the second number
                if 'minus' in didi_lower[max(0, match.start()-20):match.end()]:
                    b = -b
                expected = a * b
                # Check if student answer matches
                if student_norm == str(expected) or student_norm == f"-{abs(expected)}" or normalize_answer(f"minus {abs(expected)}") == student_norm:
                    return True

        # Pattern 2: "minus X plus Y" or "X plus minus Y" etc.
        # Use capturing groups for signs
        add_pattern = r'(minus\s*)?(\d+)\s*(?:plus|aur|and)\s*(minus\s*)?(\d+)'
        match = re.search(add_pattern, didi_lower)
        if match:
            a_neg = match.group(1) is not None  # "minus" before first number
            a = int(match.group(2))
            b_neg = match.group(3) is not None  # "minus" before second number
            b = int(match.group(4))
            if a_neg:
                a = -a
            if b_neg:
                b = -b
            expected = a + b
            # Check multiple formats
            if student_norm in [str(expected), f"-{abs(expected)}", f"minus{abs(expected)}"]:
                return True
            if expected < 0 and normalize_answer(f"minus {abs(expected)}") == student_norm:
                return True

        # Pattern 3: Direct number check - "kya hoga/aayega" with numbers
        # If Didi asked "2 times minus 3 kya hoga" and student says "-6"
        if re.search(r'kya\s*(?:hoga|aayega|hota)', didi_lower):
            # Look for "2 times minus 3" pattern more specifically
            m = re.search(r'(\d+)\s*(?:times|multiplied by|multiply|mul|ko)\s*minus\s*(\d+)', didi_lower)
            if m:
                a, b = int(m.group(1)), -int(m.group(2))
                expected = a * b
                if student_norm in [str(expected), f"minus{abs(expected)}", f"-{abs(expected)}"]:
                    return True

        return False

    def _count_action_in_history(self, tool_name: str) -> int:
        """Count how many times an LLM tool has been used for the current question.
        Resets when question advances (history tracks all, but we count from last advance)."""
        count = 0
        for h in reversed(self.session.get("history", [])):
            if h.get("tool") == tool_name:
                count += 1
            # Stop counting when we hit a question transition
            if h.get("tool") in ("praise_and_continue", "explain_solution") or \
               h.get("action") in ("praise_and_continue", "explain_solution", "move_to_next"):
                break
        return count

    def _current_question_text(self) -> str:
        q = self.session.get("current_question", {})
        return q.get("text", q.get("question_text", ""))

    def _spoken_variants(self, answer: str) -> str:
        """Generate spoken variants of a math answer for the judge."""
        import re
        variants = []
        answer = answer.strip()

        # Fraction: -1/7 → "minus 1 by 7", "minus 1 over 7", "minus one by seven"
        m = re.match(r'^(-?)(\d+)/(\d+)$', answer)
        if m:
            sign = "minus " if m.group(1) == "-" else ""
            num, den = m.group(2), m.group(3)
            variants.extend([
                f"{sign}{num} by {den}",
                f"{sign}{num} over {den}",
                f"{sign}{num} upon {den}",
                f"{sign}{num}/{den}",
            ])

        # Integer: -5 → "minus 5", "minus five", "negative 5"
        m = re.match(r'^(-?)(\d+)$', answer)
        if m and not '/' in answer:
            sign = "minus " if m.group(1) == "-" else ""
            num = m.group(2)
            variants.extend([
                f"{sign}{num}",
                f"negative {num}" if sign else num,
            ])

        return ", ".join(variants) if variants else answer

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
Spoken variants (auto-generated): {self._spoken_variants(q.get('answer', ''))}
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
