"""
IDNA EdTech v7.3 — Instruction Builder
Builds the exact LLM prompt for each state+action combination.
Didi's personality, tone, and rules are embedded here.

CRITICAL RULES (enforced in every prompt):
1. Max 2 sentences, 55 words
2. Hinglish with "aap" form
3. Indian examples (roti, cricket, Diwali, monsoon)
4. One idea per turn
5. No false praise
6. Reference student's specific answer when evaluating
"""

from typing import Optional
from app.tutor.state_machine import Action
from app.tutor.answer_checker import Verdict

# v7.4.0: Content bank for verified RAG content
try:
    from content_bank import get_content_bank
    _content_bank = get_content_bank()
except ImportError:
    _content_bank = None

DIDI_BASE = """You are **Didi (दीदी)**, a friendly elder-sister AI tutor for Indian school students. You teach math through voice conversation.

---

## RULE 0: LANGUAGE — ABSOLUTE, NON-NEGOTIABLE

The student's current language preference is: **{medium_of_instruction}**

- If `{medium_of_instruction}` is `english` → Respond ENTIRELY in English. No Hindi words. No Hinglish. No "Hum", no "padhai", no "aaram kijiye". ZERO Hindi.
- If `{medium_of_instruction}` is `hindi` → Respond in Hindi-English code-switch (Hinglish).
- If `{medium_of_instruction}` is `hinglish` → Respond in natural Hindi-English mix.

**LANGUAGE SWITCH DETECTION:**
If the student says ANY of the following (in any phrasing):
- "speak in English" / "talk in English" / "English please" / "I don't understand Hindi" / "please speak properly in English"
- OR if the student sends 2+ consecutive messages in English while you responded in Hindi

Then you MUST:
1. Immediately switch to full English for THIS response and ALL subsequent responses.
2. Acknowledge the switch briefly: "Got it, English from now on."
3. NEVER revert to Hindi unless the student explicitly asks for Hindi again.

**This rule overrides ALL other instructions, including content bank templates. If a content template is in Hindi and the student wants English, you MUST translate it to English before responding. Never paste a Hindi template when the student has requested English.**

---

## RULE 1: CONFUSION ESCALATION PROTOCOL

Track how many times the student signals confusion. Confusion signals include:
- "I don't understand" / "samajh nahi aaya" / "not understanding" / "what?" / "huh?"
- Repeating the same wrong answer
- Off-topic deflection after your explanation
- Frustrated expressions ("I don't get it", "this is hard", "I can't do this")

**Escalation ladder:**

### Confusion count = 1
- Rephrase using a DIFFERENT analogy (not another version of the same analogy).
- Make it shorter — max 2 sentences.

### Confusion count = 2
- Strip to the absolute simplest form. Use only single-digit numbers.
- Example: "2 times 2 is 4. So 4 is a perfect square. That's it. 2 times 2 equals 4."
- Ask a yes/no check: "Does that make sense — 2 times 2 is 4?"

### Confusion count = 3
- STOP teaching the concept abstractly.
- Switch to a direct guided example: "Let's just try one together. What is 3 times 3?"
- Wait for their answer. Guide from their response.

### Confusion count ≥ 4
- Acknowledge their effort warmly: "Hey, it's totally okay. This is a tricky topic and you're doing great by trying."
- Offer an exit: "Want to try a super easy warm-up question, or should we take a break and come back tomorrow?"
- If they choose break → transition to WRAP_UP.
- Do NOT keep cycling through more analogies.

**NEVER repeat the same explanation or analogy twice. If you catch yourself generating a response you've already given, STOP and move down the escalation ladder.**

---

## RULE 2: META-QUESTION ROUTING

Some student messages are NOT about the math concept — they are informational questions about the session itself. Detect and answer them directly.

**Meta-questions (answer from session context, NOT from content bank):**

| Student says | You respond (in {medium_of_instruction}) |
|---|---|
| "What chapter are we learning?" | "We're learning Chapter {chapter_number} — {chapter_name}." |
| "What topic is this?" | "We're on {current_topic}." |
| "What class is this for?" | "This is for Class {class_level}." |
| "What board?" | "This is {board_name} curriculum." |
| "How long have we been studying?" | "We've been at it for about {session_duration_minutes} minutes." |
| "What did we cover?" | Briefly summarize topics covered in this session. |

**Detection rule:** If the student's message is a WH-question (what/which/when/how long) about the session, chapter, subject, or logistics → answer directly from context. Do NOT re-explain the math concept. Do NOT fall back to a teaching response.

---

## RULE 3: EMOTIONAL AWARENESS

Pay attention to the student's emotional state:

- **Frustration** ("I don't want to study", "this is boring", physical displeasure expressions) → Acknowledge warmly. Don't push. Offer a break. "That's completely fine. We can pick this up whenever you're ready."
- **Tiredness** ("not feeling well", "I'm tired", "let's do this tomorrow") → Respect it immediately. Don't try to squeeze in one more question. Wrap up warmly in their preferred language.
- **Playfulness/off-topic** → Gently redirect once, then engage briefly if they persist. They're a child, not an employee.

**If the student expresses frustration or says something indicating physical discomfort or emotional distress, your FIRST response must acknowledge the emotion, not the math.**

---

## RULE 4: RESPONSE FORMAT (VOICE-OPTIMIZED)

- Keep responses SHORT. Max 3 sentences for teaching. Max 2 sentences for feedback.
- No bullet points, no numbered lists — this is spoken aloud via TTS.
- No markdown formatting, no asterisks, no special characters.
- Avoid parenthetical asides — TTS reads them awkwardly.
- Use "times" not "×". Use "equals" not "=". Use "into" for multiplication if in Hinglish.
- Spell out numbers when contextually clearer: "three times three is nine" not "3×3=9".

---

## SESSION CONTEXT (injected per session)

- Student name: {student_name}
- Board: {board_name}
- Class: {class_level}
- Chapter: {chapter_number} — {chapter_name}
- Current topic: {current_topic}
- Language: {medium_of_instruction}
- Session state: {fsm_state}
- Confusion count: {confusion_count}
- Topics covered this session: {topics_covered}
- Session duration: {session_duration_minutes} minutes
"""

# v7.3.22 Fix 1: Chapter name mapping for metadata injection
CHAPTER_NAMES = {
    "ch1_rational_numbers": "Chapter 1 - Rational Numbers",
    "ch1_square_and_cube": "Chapter 6 - Squares and Square Roots",
    "ch2_linear_equations": "Chapter 2 - Linear Equations",
    "ch3_understanding_quadrilaterals": "Chapter 3 - Understanding Quadrilaterals",
    "ch4_practical_geometry": "Chapter 4 - Practical Geometry",
    "ch5_data_handling": "Chapter 5 - Data Handling",
    "ch6_squares_square_roots": "Chapter 6 - Squares and Square Roots",
    "ch7_cubes_cube_roots": "Chapter 7 - Cubes and Cube Roots",
}

DIDI_NO_PRAISE = "\nANSWER INCORRECT. No praise. No shabash/bahut accha/well done.\n"
DIDI_PRAISE_OK = "\nANSWER CORRECT. Praise briefly, reference their answer.\n"

LANG_ENGLISH = """
LANGUAGE SETTING: english
YOU MUST respond ENTIRELY in English. Zero Hindi words. No "Acha", "Theek hai", "Dekho", "Samajh aaya", "Kya".
If any content template is in Hindi, TRANSLATE it to English before responding.
"""
LANG_HINDI = """
LANGUAGE SETTING: hindi
Respond in Hindi. Use Devanagari script. Use digits for numbers: "5 × 5 = 25".
"""
LANG_HINGLISH = """
LANGUAGE SETTING: hinglish
Respond in Hinglish (natural mix of Hindi-English). Use digits for math.
"""


def _get_language_instruction(session_context: dict) -> str:
    """Get language instruction based on session preference."""
    pref = session_context.get("language_pref", "hinglish")
    if pref == "english":
        return LANG_ENGLISH
    elif pref == "hindi":
        return LANG_HINDI
    return LANG_HINGLISH


def _get_confusion_instruction(session_context: dict) -> str:
    """Get confusion escalation context based on confusion_count."""
    count = session_context.get("confusion_count", 0)
    return f"\nCONFUSION COUNT: {count}"


def _get_chapter_context(session_context: dict, question_data: dict = None) -> str:
    """v7.3.22 Fix 1: Build chapter metadata for system prompt.
    v7.3.28: Enhanced with explicit chapter response instruction."""
    chapter_key = session_context.get("chapter", "")
    chapter_name = CHAPTER_NAMES.get(chapter_key, "")

    # Try to get skill info for more specific topic
    skill_name = ""
    if question_data:
        skill_name = question_data.get("target_skill", "")

    if chapter_name:
        # v7.3.28: Make chapter info explicit with instruction
        ctx = f'\nYOU ARE TEACHING: {chapter_name} (NCERT Class 8 Mathematics)'
        ctx += f'\nIf student asks "which chapter" or "what topic", tell them: "{chapter_name}"'
        if skill_name:
            # Make skill name human-readable
            skill_display = skill_name.replace("_", " ").title()
            ctx += f'\nCurrent skill: {skill_display}'
        return ctx
    return ""


def build_prompt(action, session_context, question_data=None, skill_data=None, previous_didi_response=None, conversation_history=None):
    at = action.action_type
    builder = _BUILDERS.get(at, _build_fallback)
    messages = builder(action, session_context, question_data, skill_data, previous_didi_response)

    # v8.1.0: Language, confusion, and chapter context now embedded in DIDI_BASE via _sys()
    # Only inject student's actual words for specificity (unique per turn)
    student_text = getattr(action, 'student_text', None) or session_context.get('student_text', '')
    if student_text and messages and messages[0].get("role") == "system":
        messages[0]["content"] = messages[0]["content"] + f'\n\nSTUDENT SAID: "{student_text}"'

    # v7.3.0: Inject conversation history between system prompt and current instruction
    # This gives GPT context of the ongoing dialogue for more natural responses
    if conversation_history and len(messages) >= 2:
        # Take last 6 entries (cap at 10 for long sessions)
        history_slice = conversation_history[-6:] if len(conversation_history) <= 10 else conversation_history[-10:]
        # Insert history after system prompt, before the current instruction
        system_msg = messages[0]
        current_instruction = messages[1:]
        messages = [system_msg] + history_slice + current_instruction

    return messages


def _format_didi_base(session_context: dict, question_data: dict = None) -> str:
    """Format DIDI_BASE with all session context variables."""
    # Extract chapter info
    chapter_key = session_context.get("chapter", "")
    chapter_name = CHAPTER_NAMES.get(chapter_key, chapter_key)

    # Extract chapter number from chapter_name (e.g., "Chapter 6 - Squares..." -> "6")
    chapter_number = ""
    if chapter_name and "Chapter " in chapter_name:
        parts = chapter_name.split(" - ")
        if parts:
            chapter_number = parts[0].replace("Chapter ", "")

    # Get current topic from question data
    current_topic = ""
    if question_data:
        skill = question_data.get("target_skill", "")
        current_topic = skill.replace("_", " ").title() if skill else ""
    if not current_topic:
        current_topic = session_context.get("current_topic", "Perfect Squares")

    # Get topics covered
    topics_covered = session_context.get("topics_covered", [])
    topics_str = ", ".join(topics_covered) if topics_covered else "None yet"

    # Calculate session duration
    session_duration = session_context.get("session_duration_minutes", 0)

    # Format the prompt
    formatted = DIDI_BASE.format(
        medium_of_instruction=session_context.get("language_pref", "hinglish"),
        confusion_count=session_context.get("confusion_count", 0),
        student_name=session_context.get("student_name", "Student"),
        board_name=session_context.get("board_name", "NCERT"),
        class_level=session_context.get("class_level", 8),
        chapter_number=chapter_number,
        chapter_name=chapter_name,
        current_topic=current_topic,
        fsm_state=session_context.get("state", "TEACHING"),
        topics_covered=topics_str,
        session_duration_minutes=session_duration,
    )
    return formatted


def _sys(extra="", session_context: dict = None, question_data: dict = None):
    """Build system prompt with formatted DIDI_BASE."""
    if session_context:
        base = _format_didi_base(session_context, question_data)
    else:
        # Fallback for backward compat - use unformatted base with placeholders shown
        base = DIDI_BASE.format(
            medium_of_instruction="hinglish",
            confusion_count=0,
            student_name="Student",
            board_name="NCERT",
            class_level=8,
            chapter_number="6",
            chapter_name="Squares and Square Roots",
            current_topic="Perfect Squares",
            fsm_state="TEACHING",
            topics_covered="None yet",
            session_duration_minutes=0,
        )
    return base + extra


def _build_ask_topic(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware topic asking
    lang_pref = ctx.get("language_pref", "hinglish")
    use_english = lang_pref == "english"
    if a.extra.get("retry"):
        retry_ask = "What subject did you study in school today? Math, Science, or Hindi?" if use_english else "Aaj school mein kaunsa subject padha? Math, Science, ya Hindi?"
        msg = f'Student said: "{a.student_text}". Couldn\'t identify subject. Ask specifically: "{retry_ask}"'
    else:
        msg = "Student just logged in. Ask warmly what they studied in school today. Ask about their day first, then the subject."
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": msg}]


def _build_apologize_no_subject(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware apology
    lang_pref = ctx.get("language_pref", "hinglish")
    s = a.detected_subject or "that subject"
    if lang_pref == "english":
        apology = f"Right now I only have Math, but {s} is coming soon! Want to practice math?"
    else:
        apology = f"Abhi mere paas sirf Math hai, lekin jaldi {s} bhi aa jayega! Chalo math practice karte hain?"
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'Student wants {s}, but only Math available. Say warmly: "{apology}"'}]


def _build_probe_understanding(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware probing
    lang_pref = ctx.get("language_pref", "hinglish")
    ch = ctx.get("chapter", "rational numbers")
    example = "If the denominator is the same, how do you add?" if lang_pref == "english" else "Agar denominator same hai, toh add kaise karte hain?"
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'Student studied {ch}. Ask ONE simple concept-check question (not calculation). Example for fractions: "{example}"'}]


def _build_teach_concept(a, ctx, q, sk, prev):
    ch = ctx.get("chapter", "rational numbers")
    extra = ""

    # v7.3.24: Language-aware teaching
    lang_pref = ctx.get("language_pref", "hinglish")
    use_english = lang_pref == "english"

    # v7.2.0: Phase-based teaching with teaching_turn (BUG 1/3 fix)
    teaching_turn = getattr(a, 'teaching_turn', 0) or a.reteach_count
    if teaching_turn > 0:
        extra = f"\nRe-teach #{teaching_turn}. Use COMPLETELY DIFFERENT example. Previous: \"{prev or 'unknown'}\". Do NOT repeat."

    # v7.2.0: Anti-repetition context (BUG 3 fix)
    explanations = ctx.get("explanations_given") or []
    if explanations:
        anti_rep = "\n\nYOU ALREADY EXPLAINED THESE (DO NOT REPEAT):\n"
        for exp in explanations[-3:]:  # Last 3 explanations
            anti_rep += f"- Turn {exp.get('turn', '?')}: {exp.get('summary', 'unknown')}\n"
        anti_rep += "Use a COMPLETELY DIFFERENT approach this time.\n"
        extra += anti_rep

    # Get skill key for content lookup
    skill_key = q.get("target_skill", "") if q else ctx.get("skill", "")

    # v7.4.0: Try content bank first for verified RAG content
    # v7.5.3: Enhanced logging and full methodology injection
    cb_definition = None
    cb_hook = None
    cb_analogy = None
    cb_examples = []
    cb_vedic_trick = None
    cb_visualization = None
    if _content_bank:
        cb_definition = _content_bank.get_definition_tts(skill_key)
        cb_hook = _content_bank.get_teaching_hook(skill_key)
        cb_analogy = _content_bank.get_teaching_analogy(skill_key)
        cb_examples = _content_bank.get_examples(skill_key)  # easy, medium, hard
        methodology = _content_bank.get_teaching_methodology(skill_key)
        if methodology:
            cb_vedic_trick = methodology.get("vedic_trick")
            cb_visualization = methodology.get("visualization")  # v7.5.3: tile visualization, etc.
        # v7.5.3: Log content bank usage for debugging
        import logging
        _logger = logging.getLogger("idna.instruction_builder")
        _logger.debug(f"CB skill={skill_key}: def={bool(cb_definition)}, hook={bool(cb_hook)}, analogy={bool(cb_analogy)}, examples={len(cb_examples)}")

    # Fallback to SKILL_TEACHING if content bank doesn't have this concept
    from app.content.seed_questions import SKILL_TEACHING
    lesson = SKILL_TEACHING.get(skill_key, {})

    # v7.4.2: Progressive reteach from content bank
    # Turn 0: definition_tts + hook
    # Turn 1: analogy + examples[0].solution_tts
    # Turn 2: examples[1].solution_tts + vedic_trick
    # Turn 3+: Force transition to question
    if cb_definition and teaching_turn == 0:
        # Turn 0: Use verified content bank definition
        teach_content = cb_definition
        if cb_hook:
            extra += f'\n\nUSE THIS HOOK TO START: "{cb_hook}"'
    elif teaching_turn == 1 and (cb_analogy or cb_examples or cb_visualization):
        # Turn 1: Analogy + visualization + easy example (v7.5.3: added visualization)
        teach_content = cb_analogy or ""
        if cb_visualization:
            teach_content += f" {cb_visualization}"  # e.g., "tile visualization"
        if cb_examples and len(cb_examples) > 0:
            easy_ex = cb_examples[0]
            sol_tts = easy_ex.get("solution_tts", "")
            if sol_tts:
                teach_content += f" Example: {sol_tts}"
    elif teaching_turn == 2 and (cb_examples or cb_vedic_trick):
        # Turn 2: Medium example + vedic trick
        teach_content = ""
        if cb_examples and len(cb_examples) > 1:
            medium_ex = cb_examples[1]
            teach_content = medium_ex.get("solution_tts", "")
        if cb_vedic_trick:
            teach_content += f" Trick: {cb_vedic_trick}"
        # v7.5.3: Also try laddoo analogy or other methodology content
        if not teach_content and cb_analogy:
            teach_content = f"Different approach: {cb_analogy}"
        if not teach_content:
            teach_content = lesson.get("key_insight") or lesson.get("indian_example") or ""
    elif teaching_turn >= 2:
        teach_content = lesson.get("key_insight") or lesson.get("indian_example") or lesson.get("pre_teach") or ""
    elif teaching_turn == 1:
        teach_content = lesson.get("indian_example") or lesson.get("key_insight") or lesson.get("pre_teach") or ""
    else:
        teach_content = lesson.get("pre_teach") or lesson.get("teaching") or ""

    approach = a.extra.get("approach", "fresh")

    # v7.3.24: Language-aware phrases
    transition_phrase = "No problem, let's try a question." if use_english else "Koi baat nahi, chaliye ek sawaal try karte hain."
    understand_check = "Does that make sense?" if use_english else "Ab samajh aaya?"
    understand_short = "Make sense?" if use_english else "Samajh aaya?"
    lang_mode = "English" if use_english else "Hinglish"

    # v7.4.2: Phase-based prompts with progressive reteach
    # Only force transition after Turn 3 (exhausted CB teaching material)
    # v8.1.0: Add translation instruction for Content Bank material when English mode
    translate_instruction = "TRANSLATE TO ENGLISH if the content below is in Hindi/Hinglish. " if use_english else ""

    if a.extra.get("forced_transition") and teaching_turn >= 3:
        # Turn 3+: Force to question with gentle transition
        msg = f'Say: "{transition_phrase}" Then read the question.'
    elif approach == "answer_question":
        msg = f'{translate_instruction}Student asked: "{a.student_text}". Answer their question about {ch}. {teach_content if teach_content else "Use simple example."} 2 sentences.'
    elif approach == "different_example" or teaching_turn > 0:
        # v7.4.2: Reteach with progressive examples - ALWAYS end with samajh aaya?
        # Do NOT transition to question until student gives ACK
        if teaching_turn == 1:
            msg = f'{translate_instruction}Student didn\'t understand. Use this DIFFERENT example: "{teach_content}". 2 sentences. MUST end: "{understand_check}" Wait for their response before continuing.'
        elif teaching_turn == 2:
            msg = f'{translate_instruction}Student still confused. Try this simpler approach: "{teach_content}". 2 sentences. MUST end: "{understand_check}" Do NOT move to question yet.'
        elif teaching_turn >= 3:
            # Exhausted content bank, now can transition
            msg = f'Say: "{transition_phrase}" Then read the question.'
        else:
            msg = f"{translate_instruction}Student didn't understand {ch}. Try roti cutting, cricket scoring, or Diwali sweets. 2 sentences. End: \"{understand_check}\""
    else:
        # Turn 0: Initial teaching
        if teach_content:
            msg = f'Teach this concept naturally in {lang_mode}: "{teach_content}". 2 sentences. End: "{understand_short}"'
        else:
            msg = f"Teach one concept from {ch}. Use Indian example. 2 sentences. End: \"{understand_short}\""
    return [{"role": "system", "content": _sys(extra)}, {"role": "user", "content": msg}]


def _build_read_question(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware question reading
    lang_pref = ctx.get("language_pref", "hinglish")
    use_english = lang_pref == "english"
    if not q:
        done_msg = "All questions for this topic are done! Great practice." if use_english else "Is topic ke saare questions ho gaye! Bahut achhi practice hui."
        return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'No more questions. Say: "{done_msg}"'}]
    if a.extra.get("nudge"):
        nudge_lang = "Present in English." if use_english else ""
        return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'Student hasn\'t answered. Question: "{q["question_voice"]}". {nudge_lang} Gently nudge them to try.'}]
    d = "This is an easier question. " if a.extra.get("difficulty") == "easy" else ""
    ask_prompt = 'End: "Tell me, what is the answer?"' if use_english else 'End: "Batao, kya answer hai?"'
    # v7.3.25: Tell LLM to present question in session language
    lang_instruction = "Present this question in English (translate any Hindi)." if use_english else "Read this question naturally."
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'{d}{lang_instruction}: "{q["question_voice"]}". {ask_prompt}'}]


def _build_evaluate_answer(a, ctx, q, sk, prev):
    v = a.verdict
    if not v:
        return _build_fallback(a, ctx, q, sk, prev)
    # v7.3.24: Language-aware evaluation response
    lang_pref = ctx.get("language_pref", "hinglish")
    use_english = lang_pref == "english"
    # Note: When correct, route_after_evaluation changes action_type to pick_next_question,
    # so this "correct" branch rarely executes. Kept for edge cases.
    if v.correct:
        return [{"role": "system", "content": _sys(DIDI_PRAISE_OK)}, {"role": "user", "content": f'Answer: "{v.student_parsed or a.student_text}". Correct: "{v.correct_display}". CORRECT. Praise briefly referencing their answer. 1 sentence only.'}]
    reference = 'Say "You said..."' if use_english else 'Say "Aapne ... bola"'
    return [{"role": "system", "content": _sys(DIDI_NO_PRAISE)}, {"role": "user", "content": f'Answer: "{v.student_parsed or a.student_text}". Correct: "{v.correct_display}". Diagnostic: "{v.diagnostic}". Tell what went wrong. {reference}. Do NOT reveal answer. 2 sentences.'}]


def _build_give_hint(a, ctx, q, sk, prev):
    if not q:
        return _build_fallback(a, ctx, q, sk, prev)
    hints = q.get("hints") or []

    # v7.3.24: Check language preference for hint language
    lang_pref = ctx.get("language_pref", "hinglish")
    use_english = lang_pref == "english"

    # v7.4.0: Try content bank hints first
    question_id = q.get("question_id") or q.get("id")
    cb_hints = []
    if _content_bank and question_id:
        cb_hints = _content_bank.get_hints(question_id)

    # Get actual hint: content bank first, then question hints, then generated
    if cb_hints and a.hint_level <= len(cb_hints):
        h = cb_hints[a.hint_level - 1]
    elif a.hint_level <= len(hints):
        h = hints[a.hint_level - 1]
    else:
        # No more hints — build contextual hint from question and answer
        skill = q.get("target_skill", "")
        if "perfect_square" in skill:
            h = "Think: which number multiplied by itself gives this answer?" if use_english else "Sochiye: kaunsa number khud se multiply karke yeh answer dega?"
        elif "cube" in skill:
            h = "Think: which number multiplied three times gives this answer?" if use_english else "Sochiye: kaunsa number teen baar multiply karke yeh answer dega?"
        elif "fraction" in skill.lower():
            h = "First look at the numerators, then the denominators." if use_english else "Pehle numerators ko dekho, phir denominators ko."
        else:
            # Generic hint based on answer type
            h = "The answer is a number. Think step by step." if use_english else "Is sawaal ka jawab ek number hai. Sochiye step by step."

    # v7.3.24: Use appropriate language instruction
    lang_instruction = "Say naturally in English." if use_english else "Say naturally in Hinglish."
    return [{"role": "system", "content": _sys(DIDI_NO_PRAISE)}, {"role": "user", "content": f'Give hint #{a.hint_level}: "{h}". {lang_instruction} Ask to try again. 2 sentences.'}]


def _build_show_solution(a, ctx, q, sk, prev):
    if not q:
        return _build_fallback(a, ctx, q, sk, prev)

    # v7.4.0: Try content bank full_solution_tts first
    question_id = q.get("question_id") or q.get("id")
    sol = None
    if _content_bank and question_id:
        sol = _content_bank.get_full_solution_tts(question_id)
    if not sol:
        sol = q.get("solution", "Solution not available.")

    # v7.3.24: Language-aware encouragement
    lang_pref = ctx.get("language_pref", "hinglish")
    encouragement = "It's okay, now you understand." if lang_pref == "english" else "Koi baat nahi, ab samajh aa gaya hoga."
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'3rd wrong. Show solution: "{sol}". Walk through in 2-3 sentences. Be encouraging: "{encouragement}" No new question.'}]


def _build_pick_next_question(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware transitions
    lang_pref = ctx.get("language_pref", "hinglish")
    use_english = lang_pref == "english"
    transition = "Let's try another one." if use_english else "Chalo, ek aur try karte hain."
    done_msg = "All questions for this topic are done! Great practice." if use_english else "Is topic ke questions ho gaye! Bahut achhi practice hui."
    # v7.3.25: Tell LLM to present question in session language
    q_lang = "Present question in English (translate any Hindi)." if use_english else ""

    if a.extra.get("follow_up"):
        if q:
            return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'After solution, transition to next question. Say briefly "{transition}" Then read: "{q["question_voice"]}". {q_lang}'}]
        return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'After solution, say briefly: "{transition}"'}]
    if q:
        # Include praise for correct answer + the next question
        return [{"role": "system", "content": _sys(DIDI_PRAISE_OK)}, {"role": "user", "content": f'Student answered correctly. Brief praise (1 sentence), then read next question: "{q["question_voice"]}". {q_lang}'}]
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'No more questions available. Say: "{done_msg}"'}]


def _build_comfort_student(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware comfort messages
    lang_pref = ctx.get("language_pref", "hinglish")
    if lang_pref == "english":
        comfort_mode = '\nCOMFORT MODE: Do NOT teach. Do NOT ask questions. Just acknowledge feelings. Use: "It\'s okay", "This is difficult, isn\'t it?". End: "Let me know when you\'re ready."\n'
    else:
        comfort_mode = '\nCOMFORT MODE: Do NOT teach. Do NOT ask questions. Just acknowledge feelings. Use: "Koi baat nahi", "Mushkil lag raha hai na?". End: "Jab ready ho, batana."\n'
    return [{"role": "system", "content": _sys(comfort_mode)},
            {"role": "user", "content": f'Student said: "{a.student_text}". They are frustrated. Comfort. 2 sentences.'}]


def _build_end_session(a, ctx, q, sk, prev):
    qc = ctx.get("questions_correct", 0)
    qa = ctx.get("questions_attempted", 0)
    # v7.3.24: Language-aware session ending
    lang_pref = ctx.get("language_pref", "hinglish")
    goodbye = "See you tomorrow!" if lang_pref == "english" else "Kal phir milte hain!"
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'Session ending. {qc}/{qa} correct. Summarize warmly. Encourage return tomorrow. "{goodbye}" 3 sentences max.'}]


def _build_acknowledge_homework(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware homework acknowledgment
    lang_pref = ctx.get("language_pref", "hinglish")
    msg = "Oh, you have homework? Send a photo or read me the question." if lang_pref == "english" else "Achha, homework hai? Photo bhejo ya question padh ke batao."
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'"{msg}" 1 sentence.'}]


def _build_replay_heard(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware replay message
    lang_pref = ctx.get("language_pref", "hinglish")
    if lang_pref == "english":
        msg = f'Student disputes verdict. Didi heard: "{a.student_text}". Say: "I heard: [heard]. If I misheard, please try again." Be apologetic.'
    else:
        msg = f'Student disputes verdict. Didi heard: "{a.student_text}". Say: "Mujhe aisa suna: [heard]. Agar galat suna toh phir try karo." Be apologetic.'
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": msg}]


def _build_ask_repeat(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware repeat request
    lang_pref = ctx.get("language_pref", "hinglish")
    msg = "Sorry, I didn't understand. Could you please say that again?" if lang_pref == "english" else "Sorry, samajh nahi aaya. Ek baar phir boliye?"
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'"{msg}" 1 sentence.'}]


# v7.2.0: New builders for language switch and meta questions

def _build_acknowledge_language_switch(a, ctx, q, sk, prev):
    """Acknowledge language switch and CONTINUE teaching in new language."""
    new_lang = a.extra.get("new_language", "hinglish")
    # v7.3.21 Fix 1: Continue teaching instead of asking "what would you like to know"
    if new_lang == "english":
        msg = 'Student switched to English. Acknowledge briefly ("Sure, English it is.") and CONTINUE teaching the current topic in English. Do NOT ask what they want to learn. 2 sentences max.'
    elif new_lang == "hindi":
        msg = 'Student switched to Hindi. Acknowledge briefly ("ठीक है, हिंदी में") and CONTINUE teaching the current topic in Hindi. Do NOT ask what they want. 2 sentences max.'
    else:
        msg = 'Student switched to Hinglish. Acknowledge briefly ("Theek hai") and CONTINUE teaching the current topic in Hinglish. Do NOT ask what they want. 2 sentences max.'
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": msg}]


def _build_answer_meta_question(a, ctx, q, sk, prev):
    """Answer meta questions like 'more examples', 'which chapter', etc."""
    # v7.3.24: Language-aware meta question handling
    lang_pref = ctx.get("language_pref", "hinglish")
    use_english = lang_pref == "english"
    meta_type = a.extra.get("meta_type", "more_examples")
    ch_key = ctx.get("chapter", "")
    # v7.3.28 Fix 1: Use human-readable chapter name
    ch = CHAPTER_NAMES.get(ch_key, ch_key.replace("_", " ").title())

    # Get teaching content for more examples
    from app.content.seed_questions import SKILL_TEACHING
    skill_key = q.get("target_skill", "") if q else ""
    lesson = SKILL_TEACHING.get(skill_key, {})

    # v7.3.28 Fix 1: Check chapter/topic FIRST since meta_type is always "more_examples"
    if "chapter" in a.student_text.lower() or "topic" in a.student_text.lower():
        # v7.3.28 Fix 1: Use proper chapter name from CHAPTER_NAMES
        chapter_response = f"We're learning {ch}." if use_english else f"Hum {ch} padh rahe hain."
        msg = f'Student asked which chapter. Say EXACTLY: "{chapter_response}" Nothing else.'
    elif "example" in a.student_text.lower() or meta_type == "more_examples":
        examples = lesson.get("indian_example") or lesson.get("examples", "")
        msg = f'Student wants more examples. Give 2-3 NEW examples for {skill_key}. DO NOT repeat the definition. Do NOT reuse: "{prev or ""}". Use fresh examples: {examples if examples else "laddoo, cricket score, rangoli squares"}. 2 sentences.'
    elif "real life" in a.student_text.lower() or "use" in a.student_text.lower():
        msg = f'Student asked about real-life use. Give 1-2 practical examples: architecture, cooking, shopping. How {ch} is used in daily life. 2 sentences.'
    else:
        msg = f'Student asked: "{a.student_text}". Answer briefly about {ch}. 2 sentences.'

    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": msg}]


def _build_fallback(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware fallback
    lang_pref = ctx.get("language_pref", "hinglish")
    fallback_msg = "Let's move on." if lang_pref == "english" else "Chalo, aage badhte hain."
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'Something unexpected. Say naturally: "{fallback_msg}"'}]


_BUILDERS = {
    "ask_topic": _build_ask_topic, "apologize_no_subject": _build_apologize_no_subject,
    "probe_understanding": _build_probe_understanding, "teach_concept": _build_teach_concept,
    "read_question": _build_read_question, "evaluate_answer": _build_evaluate_answer,
    "give_hint": _build_give_hint, "show_solution": _build_show_solution,
    "pick_next_question": _build_pick_next_question, "comfort_student": _build_comfort_student,
    "end_session": _build_end_session, "acknowledge_homework": _build_acknowledge_homework,
    "replay_heard": _build_replay_heard, "ask_repeat": _build_ask_repeat,
    # v7.2.0: New action builders
    "acknowledge_language_switch": _build_acknowledge_language_switch,
    "answer_meta_question": _build_answer_meta_question,
}
