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

DIDI_BASE = """You are Didi, a friendly math practice partner for Indian school students ({board_name} Class {class_level}). The student's name is {student_name}. You help them learn by DOING problems, not by listening to lectures.

RULES:
1. Ask questions, don't lecture. Get to a question quickly.
2. If they get it right: brief praise (1 sentence), then next question.
3. If they get it wrong: give ONE hint (1 sentence).
4. If still wrong after hint: show solution briefly (2 sentences max), then move on.
5. NEVER repeat the same explanation twice. If you already said it, try something different.
6. Keep EVERY response under 2 sentences. This is voice — short is better.
7. If they ask you to explain a concept: 2-sentence explanation with one example, then ask a practice question.
8. If they express frustration or tiredness: acknowledge warmly, offer to stop or try easier question. Do NOT keep teaching.
9. If they ask "which chapter" or session info: answer directly.
10. Match the student's language exactly.

You are warm, patient, and encouraging. You believe every student can learn math.

ACKNOWLEDGMENT RULES (MOST IMPORTANT):
11. ALWAYS acknowledge what the student just said BEFORE your response.
    - If they gave an answer: repeat their answer and say if it's right or wrong. "625 — perfect!" or "600 — not quite, let me help."
    - If they asked a question: answer it directly first. "Good question — we're studying Squares and Cubes."
    - If they said they don't understand: validate them. "That's okay, this is tricky. Let me try differently."
    - If they expressed a feeling: name the feeling. "Sounds like you had a rough day."
    - If they made a complaint: address the specific complaint. "You're right, that was too many at once. Let's simplify."
12. NEVER ignore what the student said. NEVER respond as if they said nothing.
13. If the student says "I already answered" or "I just said that" — apologize briefly and acknowledge their answer: "Sorry about that! You said 625, and that's correct. Let's move on."
14. If you're not sure what they meant, ask: "I want to make sure I understood — did you mean 625?"
15. When the student says "too many", "bahut saare", "I can't remember all" — DO NOT offer a break. Instead, reduce scope: "Okay, let's just do the first 5" or "Let's start with an easy one." Adapt the difficulty DOWN, don't give up.

MATH FACTS: ONLY use facts from content provided below. NEVER calculate from memory. Wrong math destroys trust.

LEVEL AWARENESS:
The student is at Level {current_level} of 5.
{level_instruction}
NEVER give examples or questions above their current level.
If they ask about something from a higher level, say: "Great question! We'll get to that soon. First, let's master this."

{language_instruction}

CURRENT SESSION: {chapter_name} — {current_topic}
"""

# v7.3.22 Fix 1: Chapter name mapping for metadata injection
CHAPTER_NAMES = {
    "ch1_rational_numbers": "Chapter 1 - Rational Numbers",
    # v10.2.0 Fix 4: More accurate name covering both squares AND cubes
    "ch1_square_and_cube": "Squares, Cubes and their Roots",
    "ch2_linear_equations": "Chapter 2 - Linear Equations",
    "ch3_understanding_quadrilaterals": "Chapter 3 - Understanding Quadrilaterals",
    "ch4_practical_geometry": "Chapter 4 - Practical Geometry",
    "ch5_data_handling": "Chapter 5 - Data Handling",
    "ch6_squares_square_roots": "Chapter 6 - Squares and Square Roots",
    "ch7_cubes_cube_roots": "Chapter 7 - Cubes and Cube Roots",
}

LANG_INSTRUCTIONS = {
    "english": "LANGUAGE: Respond ENTIRELY in English. No Hindi words. No Hinglish. If teaching content below is in Hindi, translate it to English first.",
    "hindi": """LANGUAGE: Respond in STANDARD Hindi (Modern Standard Hindi / Khari Boli) mixed with English for technical terms.
Do NOT use Bhojpuri, Maithili, Awadhi, Marwari, Rajasthani, or any regional dialect.
Use Devanagari script mixed with English. Use 'aap' form respectfully. Use digits for math: "5 times 5 equals 25".
CRITICAL: Every Hindi word MUST have complete vowel marks (matras). "ठीक" not "ठक". "है" not "ह". "हिंदी" not "हद".
If you cannot write proper Devanagari with all matras, write in Roman Hindi instead.""",
    "hinglish": """LANGUAGE: Respond in Hinglish — natural mix of STANDARD Hindi (Khari Boli) and English.
Do NOT use Bhojpuri, Maithili, Awadhi, Marwari, Rajasthani, or any regional dialect.
Use Roman script with Hindi words. Use digits for math. Use 'aap' form respectfully.""",
    "telugu": """LANGUAGE: Respond in Telugu-English mix (Tenglish).
Use Telugu script for common words, English for math terms (square root, cube, etc.).
Translate any Hindi content to Telugu. Do NOT use Hindi or Hinglish.
Be warm and encouraging like a Telugu elder sister. Use మీరు (meeru) form respectfully.""",
}


LEVEL_INSTRUCTIONS = {
    1: "Student is at Level 1 (basic multiplication). Use ONLY simple multiplication: 'What is N times N?' No math terminology. No 'square' or 'cube' words yet.",
    2: "Student is at Level 2 (learning squares). They know multiplication. Introduce 'square' as 'a number times itself'. Keep examples under 15x15.",
    3: "Student is at Level 3 (learning square roots). They know squares. Introduce 'square root' as 'which number was squared?' Connect to squares they already know.",
    4: "Student is at Level 4 (patterns). They know squares and roots. Teach patterns: perfect square recognition, last digit rules, memorization tricks.",
    5: "Student is at Level 5 (prime factorization). They know squares, roots, and patterns. NOW teach prime factorization method for large numbers.",
}


def _get_level_instruction(session_context: dict) -> str:
    """Get level-appropriate teaching instruction."""
    level = session_context.get("current_level", 2)
    return LEVEL_INSTRUCTIONS.get(level, LEVEL_INSTRUCTIONS[2])


def _get_language_instruction(session_context: dict) -> str:
    """Get language instruction based on session preference."""
    pref = session_context.get("language_pref", "hinglish")
    # v10.1: Handle BCP-47 codes like "te-IN"
    if pref == "te-IN":
        pref = "telugu"
    return LANG_INSTRUCTIONS.get(pref, LANG_INSTRUCTIONS["hinglish"])


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
    # P0 FIX: If student is emotionally distressed, override to comfort first
    if session_context and session_context.get("student_emotional"):
        student_text = getattr(action, 'student_text', None) or session_context.get('student_text', '')
        lang_pref = session_context.get("language_pref", "hinglish")
        use_english = lang_pref == "english"
        if use_english:
            emotion_msg = f'Student said: "{student_text}". They sound sad or tired. Your FIRST priority is acknowledging their emotion — NOT teaching math. Say something warm like "I can hear you\'re not having a great day" and then gently ask if they want to continue or take a break. 2 sentences max.'
        else:
            emotion_msg = f'Student ne kaha: "{student_text}". Woh udaas ya thaka hua lag raha hai. PEHLE emotion acknowledge karo — math BAAD mein. Warmly bolo "Lagta hai aaj din thoda tough raha" aur pucho ki continue karna hai ya break lena hai. 2 sentences max.'
        return [
            {"role": "system", "content": _sys(session_context=session_context, question_data=question_data)},
            {"role": "user", "content": emotion_msg}
        ]

    # P0 Bug A: If student is correcting Didi, override action to acknowledge
    if session_context and session_context.get("student_is_correcting"):
        # Force acknowledgment regardless of what FSM decided
        student_text = getattr(action, 'student_text', None) or session_context.get('student_text', '')
        lang_pref = session_context.get("language_pref", "hinglish")
        use_english = lang_pref == "english"
        if use_english:
            correction_msg = f'Student corrected your math: "{student_text}". You MUST acknowledge: "You\'re right, thank you for catching that!" Then give the correct fact. Do NOT ignore the correction. Do NOT continue with a different topic. 2 sentences max.'
        else:
            correction_msg = f'Student ne tumhari math correct ki: "{student_text}". Tum ZAROOR acknowledge karo: "Haan, sahi pakda! Thank you!" Phir correct fact batao. Correction ignore MAT karo. 2 sentences max.'
        return [
            {"role": "system", "content": _sys(session_context=session_context, question_data=question_data)},
            {"role": "user", "content": correction_msg}
        ]

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
    """Format DIDI_BASE with session context variables. v10.1 simplified version."""
    chapter_key = session_context.get("chapter", "")
    chapter_name = CHAPTER_NAMES.get(chapter_key, chapter_key.replace("_", " ").title())

    current_topic = ""
    if question_data:
        skill = question_data.get("target_skill", "")
        current_topic = skill.replace("_", " ").title() if skill else ""
    if not current_topic:
        current_topic = session_context.get("current_topic", "")

    lang_instruction = _get_language_instruction(session_context)
    level_instruction = _get_level_instruction(session_context)
    current_level = session_context.get("current_level", 2)

    formatted = DIDI_BASE.format(
        student_name=session_context.get("student_name", "Student"),
        board_name=session_context.get("board_name", "CBSE"),
        class_level=session_context.get("class_level", 8),
        chapter_name=chapter_name,
        current_topic=current_topic,
        language_instruction=lang_instruction,
        level_instruction=level_instruction,
        current_level=current_level,
    )
    return formatted


def _sys(extra="", session_context: dict = None, question_data: dict = None):
    """Build system prompt. v10 version — language instruction is inside DIDI_BASE."""
    if session_context:
        base = _format_didi_base(session_context, question_data)
        # Chapter context for meta-question handling
        chapter_ctx = _get_chapter_context(session_context, question_data)
        if chapter_ctx:
            base += chapter_ctx
    else:
        lang_instruction = LANG_INSTRUCTIONS.get("hinglish")
        base = DIDI_BASE.format(
            student_name="Student",
            board_name="CBSE",
            class_level=8,
            chapter_name="Squares and Square Roots",
            current_topic="Perfect Squares",
            language_instruction=lang_instruction,
            level_instruction=LEVEL_INSTRUCTIONS[2],
            current_level=2,
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

    # v9.0.10: Verified squares/cubes data to prevent hallucination
    # NEVER let LLM compute these from memory - inject verified facts
    _VERIFIED_SQUARES = {
        "perfect_square_identification": "Verified squares: 1²=1, 2²=4, 3²=9, 4²=16, 5²=25, 6²=36, 7²=49, 8²=64, 9²=81, 10²=100",
        "last_digit_pattern": "Verified last digits of squares 1-10: 1,4,9,6,5,6,9,4,1,0. Only 0,1,4,5,6,9 appear. Never 2,3,7,8.",
        "square_estimation": "Verified: 6²=36, 7²=49, 8²=64, 9²=81, 10²=100, 11²=121, 12²=144, 13²=169, 14²=196, 15²=225",
        "cube_identification": "Verified cubes: 1³=1, 2³=8, 3³=27, 4³=64, 5³=125, 6³=216, 7³=343, 8³=512, 9³=729, 10³=1000",
        "cube_estimation": "Verified: 4³=64, 5³=125, 6³=216, 7³=343, 8³=512. For 300, closest is 7³=343 or 6³=216.",
    }
    verified_data = _VERIFIED_SQUARES.get(skill_key, "")
    if verified_data:
        extra += f"\n\n⚠️ USE ONLY THESE VERIFIED VALUES (do NOT compute from memory): {verified_data}\n"

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
            # P0 FIX: Length guard for reteach
            if len(teach_content) > 200:
                msg = f'{translate_instruction}Student didn\'t understand. Take the SIMPLEST part of this: "{teach_content}" and explain ONLY that part in 2 sentences. MUST end: "{understand_check}"'
            else:
                msg = f'{translate_instruction}Student didn\'t understand. Use this DIFFERENT example: "{teach_content}". 2 sentences. MUST end: "{understand_check}" Wait for their response before continuing.'
        elif teaching_turn == 2:
            msg = f'{translate_instruction}Student still confused. Try this simpler approach: "{teach_content}". 2 sentences. MUST end: "{understand_check}" Do NOT move to question yet.'
        elif teaching_turn >= 4:
            # P0 FIX: OFFER BREAK - Student has been struggling too long
            if use_english:
                msg = 'The student has been struggling with this topic for a while now. Do NOT explain again. Say EXACTLY: "This is a tough topic, and you are doing great by trying. Would you like to take a short break, or try a different easier topic?" 2 sentences max.'
            else:
                msg = 'Student bahut der se is topic pe stuck hai. Phir se explain MAT karo. EXACTLY yeh bolo: "Yeh mushkil topic hai, aur aap try kar rahe ho yeh bahut acchi baat hai. Break lena chahoge ya koi aasan topic try karein?" 2 sentences max.'
        elif teaching_turn == 3:
            # P0 FIX: STRATEGY SHIFT - Stop explaining, start asking guided question
            if use_english:
                msg = 'STOP EXPLAINING. The student has heard 3 explanations and still does not understand. Do NOT give another explanation or example. Instead, ask ONE simple guided question: "Let me ask you something simple - what is 2 times 2?" Wait for their answer. 1 sentence only.'
            else:
                msg = 'EXPLAINING BAND KARO. Student ne 3 baar sun liya, samajh nahi aaya. Aur explanation MAT do. Ek simple sawaal pucho: "Chalo ek simple sawaal - 2 into 2 kitna hota hai?" Jawab ka intezaar karo. 1 sentence only.'
        else:
            msg = f"{translate_instruction}Student didn't understand {ch}. Try roti cutting, cricket scoring, or Diwali sweets. 2 sentences. End: \"{understand_check}\""
    else:
        # Turn 0: Initial teaching
        if teach_content:
            # V10: GPT-4.1 rephrases verified content (teacher), doesn't invent (risk)
            # P0 FIX: Enforce voice-friendly length. Content bank has full solutions
            # but TTS should never read more than 3 sentences.
            if len(teach_content) > 200:
                msg = f'The concept is: "{teach_content}". IMPORTANT: Do NOT read this word-for-word. Summarize the KEY IDEA in 2 sentences maximum using a simple example. Then offer: "Would you like me to explain more, or shall we try a question?"'
            else:
                msg = f'Rephrase this concept naturally for the student: "{teach_content}". Then offer: "Would you like an example, or shall we try a question?"'
        else:
            # V10: Log content gap instead of improvising
            import logging
            logging.warning(f"CONTENT GAP: skill={skill_key}, turn={teaching_turn}, chapter={ch}")
            from app.tutor.strings import get_text
            msg = get_text("no_content_available", ctx.get("language_pref", "hinglish"))
    return [{"role": "system", "content": _sys(extra, session_context=ctx, question_data=q)}, {"role": "user", "content": msg}]


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
    """v10: Evaluate with teacher warmth, not examiner coldness."""
    v = a.verdict
    if not v:
        return _build_fallback(a, ctx, q, sk, prev)

    if v.correct:
        return [
            {"role": "system", "content": _sys(session_context=ctx, question_data=q)},
            {"role": "user", "content":
             f'The student answered: "{v.student_parsed or a.student_text}". '
             f'The correct answer is: "{v.correct_display}". '
             f'Their answer is CORRECT. '
             f'Acknowledge their specific answer with brief praise: '
             f'"{v.student_parsed or a.student_text} — that\'s right!" or "Correct, {v.correct_display}!" '
             f'Then say "Let\'s try the next one." '
             f'2 sentences maximum.'}
        ]
    else:
        return [
            {"role": "system", "content": _sys(session_context=ctx, question_data=q)},
            {"role": "user", "content":
             f'The student answered: "{v.student_parsed or a.student_text}". '
             f'The correct answer is: "{v.correct_display}". '
             f'Diagnostic: "{v.diagnostic}". '
             f'First acknowledge their answer: "{v.student_parsed or a.student_text} — not quite." '
             f'Then give ONE specific hint about what went wrong. '
             f'Do NOT reveal the correct answer. '
             f'2 sentences maximum.'}
        ]


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
    # V10: DIDI_NO_PRAISE deleted — persona handles hint tone naturally
    # v10.3.0: Acknowledge student's struggle before giving hint
    ack = '"That\'s okay, let me help." ' if use_english else '"Koi baat nahi, hint deti hoon." '
    return [{"role": "system", "content": _sys("", session_context=ctx, question_data=q)}, {"role": "user", "content": f'Start with {ack} Then give hint #{a.hint_level}: "{h}". {lang_instruction} Ask to try again. 2 sentences.'}]


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
        # v10.3.0: Explicit acknowledgment of correct answer before moving to next question
        return [{"role": "system", "content": _sys("", session_context=ctx, question_data=q)}, {"role": "user", "content": f'Student answered the previous question correctly. Say brief praise like "Well done!" (1 sentence), then read the NEXT question: "{q["question_voice"]}". {q_lang} This is a NEW question — do NOT re-ask the old one.'}]
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'No more questions available. Say: "{done_msg}"'}]


def _build_comfort_student(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware comfort messages
    # v10.1: After 2 comfort turns, offer to continue with an easy question
    lang_pref = ctx.get("language_pref", "hinglish")
    # v10.1 FIX: Read comfort_count from action.extra (where state_machine puts it) first
    comfort_count = a.extra.get("comfort_count", ctx.get("comfort_count", 0))
    use_english = lang_pref == "english"

    if comfort_count >= 2:
        # v10.1: Exit comfort loop — offer to continue
        if use_english:
            msg = ('Student has been comforted. Now gently offer to continue: '
                   '"Would you like to try an easy question? No pressure at all." '
                   '1 sentence only.')
        else:
            msg = ('Student ko comfort mil chuka hai. Ab gently offer karo: '
                   '"Ek aasan sawaal try karein? Bilkul koi pressure nahi." '
                   '1 sentence only.')
        return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)},
                {"role": "user", "content": msg}]

    if use_english:
        comfort_mode = '\nCOMFORT MODE: Do NOT teach. Do NOT ask questions. Just acknowledge feelings. Use: "It\'s okay", "This is difficult, isn\'t it?". End: "Let me know when you\'re ready."\n'
    else:
        comfort_mode = '\nCOMFORT MODE: Do NOT teach. Do NOT ask questions. Just acknowledge feelings. Use: "Koi baat nahi", "Mushkil lag raha hai na?". End: "Jab ready ho, batana."\n'
    return [{"role": "system", "content": _sys(comfort_mode, session_context=ctx, question_data=q)},
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
    return_to = a.extra.get("return_to", "")

    # Get teaching content for more examples
    from app.content.seed_questions import SKILL_TEACHING
    skill_key = q.get("target_skill", "") if q else ""
    lesson = SKILL_TEACHING.get(skill_key, {})

    # v10.3.0: After answering, steer back to the question if in answer/hint states
    if return_to in ("WAITING_ANSWER", "HINT_1", "HINT_2"):
        steer_back = ' Then gently steer back: "Now, back to our question..."' if use_english else ' Phir wapas laao: "Ab, apne sawaal pe wapas aate hain..."'
    else:
        steer_back = ""

    # v7.3.28 Fix 1: Check chapter/topic FIRST since meta_type is always "more_examples"
    student_lower = a.student_text.lower()
    if "chapter" in student_lower or "topic" in student_lower or "kaunsa" in student_lower or "कौन" in a.student_text:
        # v7.3.28 Fix 1: Use proper chapter name from CHAPTER_NAMES
        chapter_response = f"We're learning {ch}." if use_english else f"Hum {ch} padh rahe hain."
        msg = f'Student asked which chapter. Say EXACTLY: "{chapter_response}"{steer_back}'
    elif "correct" in student_lower or "right" in student_lower or "sahi" in student_lower or "galat" in student_lower:
        # v10.3.0: Student asking about their answer status
        msg = f'Student asked: "{a.student_text}". Answer their question directly about whether their answer was right or wrong.{steer_back} 2 sentences.'
    elif "example" in student_lower or meta_type == "more_examples":
        examples = lesson.get("indian_example") or lesson.get("examples", "")
        msg = f'Student wants more examples. Give 2-3 NEW examples for {skill_key}. DO NOT repeat the definition. Do NOT reuse: "{prev or ""}". Use fresh examples: {examples if examples else "laddoo, cricket score, rangoli squares"}.{steer_back} 2 sentences.'
    elif "real life" in student_lower or "use" in student_lower:
        msg = f'Student asked about real-life use. Give 1-2 practical examples: architecture, cooking, shopping. How {ch} is used in daily life.{steer_back} 2 sentences.'
    else:
        msg = f'Student asked: "{a.student_text}". Answer their question directly and briefly.{steer_back} 2 sentences.'

    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": msg}]


def _build_fallback(a, ctx, q, sk, prev):
    """v10: Let the model handle unexpected input naturally."""
    return [
        {"role": "system", "content": _sys(session_context=ctx, question_data=q)},
        {"role": "user", "content":
         f'Student said something unexpected: "{a.student_text}". '
         f'Respond naturally as their tutor. If you can address what they said, do so. '
         f'If not, gently guide them back to the current topic.'}
    ]


def _build_re_greet(a, ctx, q, sk, prev):
    """P0 FIX: Handle non-ACK inputs during GREETING state."""
    lang_pref = ctx.get("language_pref", "hinglish")
    use_english = lang_pref == "english"
    ch_key = ctx.get("chapter", "")
    ch = CHAPTER_NAMES.get(ch_key, ch_key.replace("_", " ").title())

    if use_english:
        msg = f'Student is in greeting phase but hasn\'t started. Warmly re-invite: "No worries! Ready to start learning {ch}?" 1 sentence max.'
    else:
        msg = f'Student greeting phase mein hai, start nahi kiya. Warmly re-invite karo: "Koi baat nahi! {ch} shuru karein?" 1 sentence max.'
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)},
            {"role": "user", "content": msg}]


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
    # P0 FIX: re_greet was falling to _build_fallback
    "re_greet": _build_re_greet,
}
