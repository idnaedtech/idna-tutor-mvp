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

DIDI_BASE = """You are Didi, a friendly math practice partner for Indian school students ({board_name} Class {class_level}). The student's name is {student_name}. Always use their actual name — NEVER use "Priya" or "प्रिय" as a name. If you don't know the student's name, say "beta" or skip the name entirely.

You help them learn by DOING problems, not by listening to lectures.

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
11. If the student asks "will you teach me?" or similar direct questions: answer YES warmly first ("Haan bilkul! Main hoon na."), THEN continue with the lesson.
12. NEVER say "aapne poocha" (आपने पूछा) or "you asked" when presenting a question. YOU are asking the question. Say "बताओ" or "Here's the question".

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
    "ch1_rational_numbers": "Chapter 1, Rational Numbers",
    # v10.5.5: Include chapter number — students ask "which chapter number?"
    # v10.6.3: Commas not dashes — TTS reads "-" as "minus"
    "ch1_square_and_cube": "Chapter 6, Squares and Square Roots, and Chapter 7, Cubes and Cube Roots",
    "ch2_linear_equations": "Chapter 2, Linear Equations",
    "ch3_understanding_quadrilaterals": "Chapter 3, Understanding Quadrilaterals",
    "ch4_practical_geometry": "Chapter 4, Practical Geometry",
    "ch5_data_handling": "Chapter 5, Data Handling",
    "ch6_squares_square_roots": "Chapter 6, Squares and Square Roots",
    "ch7_cubes_cube_roots": "Chapter 7, Cubes and Cube Roots",
}

LANG_INSTRUCTIONS = {
    "english": "LANGUAGE: Respond ENTIRELY in English. No Hindi words. No Hinglish. If teaching content below is in Hindi, translate it to English first.",
    "hindi": """LANGUAGE: Respond in STANDARD Hindi (Modern Standard Hindi / Khari Boli) mixed with English for technical terms.
Do NOT use Bhojpuri, Maithili, Awadhi, Marwari, Rajasthani, or any regional dialect.
CRITICAL: Always write Hindi in Devanagari script (देवनागरी). NEVER write Hindi in Roman/Latin script.
Wrong: "Theek hai, squares ka matlab hota hai". Right: "ठीक है, squares का मतलब होता है".
Use 'aap' form respectfully. Use digits for math: "5 times 5 equals 25".
Every Hindi word MUST have complete vowel marks (matras). "ठीक" not "ठक". "है" not "ह".""",
    "hinglish": """LANGUAGE: Respond in Hinglish — natural mix of STANDARD Hindi (Khari Boli) and English.
Do NOT use Bhojpuri, Maithili, Awadhi, Marwari, Rajasthani, or any regional dialect.
CRITICAL: Write Hindi words in Devanagari script, English words in Roman. Example: "बहुत अच्छा! 5 times 5 equals 25 होता है।"
Wrong: "Bahut accha! 5 times 5 equals 25 hota hai." (Roman Hindi sounds garbled in voice)
Use digits for math. Use 'aap' form respectfully.""",
    "telugu": """LANGUAGE: You MUST respond in Telugu script (తెలుగు). Every sentence must be in Telugu.
If you cannot express a math term in Telugu, use the English term but keep ALL other words in Telugu.
Do NOT use Hindi, Hinglish, or Devanagari script. Translate any Hindi content to Telugu first.
Be warm and encouraging like a Telugu elder sister (అక్క). Use మీరు (meeru) form respectfully.
Example: "బాగా చెప్పారు! 5 times 5 అంటే 25 అవుతుంది. ఇది square అంటారు."
CRITICAL: If you write even one Hindi word, the student cannot understand. Telugu ONLY.""",
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


def _lang(ctx, english, hinglish, telugu=None):
    """v10.6.1: Pick text by language. Telugu falls back to English if not provided."""
    pref = ctx.get("language_pref", "hinglish") if isinstance(ctx, dict) else "hinglish"
    if pref in ("telugu", "te-IN"):
        return telugu if telugu else english
    if pref == "english":
        return english
    return hinglish


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
        emotion_msg = _lang(session_context,
            f'Student said: "{student_text}". They sound sad or tired. Your FIRST priority is acknowledging their emotion — NOT teaching math. Say something warm like "I can hear you\'re not having a great day" and then gently ask if they want to continue or take a break. 2 sentences max.',
            f'Student ne kaha: "{student_text}". Woh udaas ya thaka hua lag raha hai. PEHLE emotion acknowledge karo — math BAAD mein. Warmly bolo "Lagta hai aaj din thoda tough raha" aur pucho ki continue karna hai ya break lena hai. 2 sentences max.',
            f'Student said: "{student_text}". వాళ్ళు బాధగా లేదా అలసిపోయినట్లు ఉన్నారు. FIRST emotion acknowledge చేయండి — math LATER. Telugu లో warmly respond చేయండి. "మీరు బాగా feel అవ్వట్లేదని తెలుస్తోంది" అని చెప్పి continue చేయాలా break తీసుకోవాలా అని అడగండి. 2 sentences max.'
        )
        return [
            {"role": "system", "content": _sys(session_context=session_context, question_data=question_data)},
            {"role": "user", "content": emotion_msg}
        ]

    # P0 Bug A: If student is correcting Didi, override action to acknowledge
    if session_context and session_context.get("student_is_correcting"):
        # Force acknowledgment regardless of what FSM decided
        student_text = getattr(action, 'student_text', None) or session_context.get('student_text', '')
        lang_pref = session_context.get("language_pref", "hinglish")
        correction_msg = _lang(session_context,
            f'Student corrected your math: "{student_text}". You MUST acknowledge: "You\'re right, thank you for catching that!" Then give the correct fact. Do NOT ignore the correction. Do NOT continue with a different topic. 2 sentences max.',
            f'Student ne tumhari math correct ki: "{student_text}". Tum ZAROOR acknowledge karo: "Haan, sahi pakda! Thank you!" Phir correct fact batao. Correction ignore MAT karo. 2 sentences max.',
            f'Student corrected your math: "{student_text}". మీరు MUST acknowledge చేయాలి: "మీరు correct గా చెప్పారు, thanks!" అని Telugu లో చెప్పండి. Correct fact ఇవ్వండి. Correction ignore చేయకండి. 2 sentences max.'
        )
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
    if a.extra.get("retry"):
        retry_ask = _lang(ctx,
            "What subject did you study in school today? Math, Science, or Hindi?",
            "Aaj school mein kaunsa subject padha? Math, Science, ya Hindi?",
            "ఈ రోజు school లో ఏ subject చదివారు? Math, Science, లేదా Hindi?")
        msg = f'Student said: "{a.student_text}". Couldn\'t identify subject. Ask specifically: "{retry_ask}"'
    else:
        msg = "Student just logged in. Ask warmly what they studied in school today. Ask about their day first, then the subject."
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": msg}]


def _build_apologize_no_subject(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware apology
    lang_pref = ctx.get("language_pref", "hinglish")
    s = a.detected_subject or "that subject"
    apology = _lang(ctx,
        f"Right now I only have Math, but {s} is coming soon! Want to practice math?",
        f"Abhi mere paas sirf Math hai, lekin jaldi {s} bhi aa jayega! Chalo math practice karte hain?",
        f"ప్రస్తుతం నా దగ్గర Math మాత్రమే ఉంది, కానీ {s} త్వరలో వస్తుంది! Math practice చేద్దామా?")
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'Student wants {s}, but only Math available. Say warmly: "{apology}"'}]


def _build_probe_understanding(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware probing
    lang_pref = ctx.get("language_pref", "hinglish")
    ch = ctx.get("chapter", "rational numbers")
    example = _lang(ctx,
        "If the denominator is the same, how do you add?",
        "Agar denominator same hai, toh add kaise karte hain?",
        "Denominator same అయితే, add ఎలా చేస్తారు?")
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'Student studied {ch}. Ask ONE simple concept-check question (not calculation). Example for fractions: "{example}"'}]


def _build_teach_concept(a, ctx, q, sk, prev):
    ch = ctx.get("chapter", "rational numbers")
    extra = ""

    # v7.3.24: Language-aware teaching
    lang_pref = ctx.get("language_pref", "hinglish")
    use_english = lang_pref == "english"
    use_telugu = lang_pref in ("telugu", "te-IN")

    # v10.5.2: Chapter intro — brief explanation before first question
    if a.extra.get("chapter_intro"):
        ch_key = ctx.get("chapter", "")
        ch_name = CHAPTER_NAMES.get(ch_key, ch_key.replace("_", " ").title())
        msg = _lang(ctx,
            f'Student just responded to greeting. Give a brief 2-3 sentence chapter introduction about "{ch_name}". '
            f'Explain what the topic is about in simple terms with one relatable example. '
            f'Then say "Let\'s try a question!" to transition. Do NOT ask a math question yet.',
            f'Student ne greeting ka jawab diya. "{ch_name}" ka brief 2-3 sentence introduction do. '
            f'Simple example ke saath topic samjhao. '
            f'Phir bolo "Chalo ek question try karte hain!" Math question MAT poocho abhi.',
            f'Student greeting కి respond చేశారు. "{ch_name}" గురించి brief 2-3 sentence introduction ఇవ్వండి Telugu లో. '
            f'Simple example తో topic explain చేయండి. '
            f'తర్వాత "ఒక question try చేద్దామా!" అని transition చేయండి. Math question అడగకండి ఇంకా.')
        return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": msg}]

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
    transition_phrase = _lang(ctx, "No problem, let's try a question.", "Koi baat nahi, chaliye ek sawaal try karte hain.", "పరవాలేదు, ఒక question try చేద్దాం.")
    understand_check = _lang(ctx, "Does that make sense?", "Ab samajh aaya?", "అర్థమైందా?")
    understand_short = _lang(ctx, "Make sense?", "Samajh aaya?", "అర్థమైందా?")
    lang_mode = _lang(ctx, "English", "Hinglish", "Telugu")

    # v7.4.2: Phase-based prompts with progressive reteach
    # Only force transition after Turn 3 (exhausted CB teaching material)
    # v8.1.0: Add translation instruction for Content Bank material when English mode
    if use_telugu:
        translate_instruction = "TRANSLATE TO TELUGU (తెలుగు) if the content below is in Hindi/Hinglish/English. "
    elif use_english:
        translate_instruction = "TRANSLATE TO ENGLISH if the content below is in Hindi/Hinglish. "
    else:
        translate_instruction = ""

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
            msg = _lang(ctx,
                'The student has been struggling with this topic for a while now. Do NOT explain again. Say EXACTLY: "This is a tough topic, and you are doing great by trying. Would you like to take a short break, or try a different easier topic?" 2 sentences max.',
                'Student bahut der se is topic pe stuck hai. Phir se explain MAT karo. EXACTLY yeh bolo: "Yeh mushkil topic hai, aur aap try kar rahe ho yeh bahut acchi baat hai. Break lena chahoge ya koi aasan topic try karein?" 2 sentences max.',
                'Student చాలా సేపటి నుండి ఈ topic లో stuck అయ్యారు. మళ్ళీ explain చేయకండి. Telugu లో ఇలా చెప్పండి: "ఇది కష్టమైన topic, మీరు try చేస్తున్నారు అది చాలా బాగుంది. Break తీసుకుందామా, లేదా easy topic try చేద్దామా?" 2 sentences max.')
        elif teaching_turn == 3:
            # P0 FIX: STRATEGY SHIFT - Stop explaining, start asking guided question
            msg = _lang(ctx,
                'STOP EXPLAINING. The student has heard 3 explanations and still does not understand. Do NOT give another explanation or example. Instead, ask ONE simple guided question: "Let me ask you something simple - what is 2 times 2?" Wait for their answer. 1 sentence only.',
                'EXPLAINING BAND KARO. Student ne 3 baar sun liya, samajh nahi aaya. Aur explanation MAT do. Ek simple sawaal pucho: "Chalo ek simple sawaal - 2 into 2 kitna hota hai?" Jawab ka intezaar karo. 1 sentence only.',
                'EXPLAIN చేయడం ఆపండి. Student 3 సార్లు విన్నారు, అర్థం కాలేదు. మరో explanation ఇవ్వకండి. ఒక simple question అడగండి: "ఒక simple question — 2 times 2 ఎంత?" Answer కోసం wait చేయండి. 1 sentence only.')
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
    if not q:
        done_msg = _lang(ctx, "All questions for this topic are done! Great practice.", "Is topic ke saare questions ho gaye! Bahut achhi practice hui.", "ఈ topic questions అయిపోయాయి! చాలా బాగా practice చేశారు.")
        return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'No more questions. Say: "{done_msg}"'}]
    if a.extra.get("nudge"):
        nudge_lang = _lang(ctx, "Present in English.", "", "Present in Telugu (తెలుగు).")
        return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'Student hasn\'t answered. Question: "{q["question_voice"]}". {nudge_lang} Gently nudge them to try.'}]
    # v10.5.3: Post-comfort transition — acknowledge student's willingness before question
    post_comfort_prefix = ""
    if a.extra.get("post_comfort"):
        student_said = a.student_text or ""
        post_comfort_prefix = _lang(ctx,
            f'Student said: "{student_said}" after being comforted. First warmly acknowledge: "Of course! I\'m here to help. Let\'s try together." Then read the question. ',
            f'Student ne comfort ke baad kaha: "{student_said}". Pehle warmly acknowledge karo: "Haan bilkul! Main hoon na, saath mein seekhenge." Phir question padhao. ',
            f'Student comfort తర్వాత చెప్పారు: "{student_said}". Telugu లో warmly acknowledge చేయండి: "అవును! నేను ఉన్నాను, కలిసి నేర్చుకుందాం." తర్వాత question చదవండి. ')
    d = "This is an easier question. " if a.extra.get("difficulty") == "easy" else ""
    ask_prompt = _lang(ctx,
        'End: "Tell me, what is the answer?"',
        'End: "Batao, kya answer hai?"',
        'End: "చెప్పండి, answer ఏమిటి?"')
    lang_instruction = _lang(ctx,
        "Present this question in English (translate any Hindi).",
        "Read this question naturally.",
        "Present this question in Telugu (తెలుగు). Translate any Hindi to Telugu.")
    # v10.6.4 FIX 1: "Here is the question" — never "You asked" or "Aapne poocha"
    present = _lang(ctx, "Here is the question", "यह question है", "ఇది question")
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'{post_comfort_prefix}{d}{present}. {lang_instruction}: "{q["question_voice"]}". {ask_prompt}'}]


def _build_evaluate_answer(a, ctx, q, sk, prev):
    """v10: Evaluate with teacher warmth, not examiner coldness."""
    v = a.verdict
    if not v:
        return _build_fallback(a, ctx, q, sk, prev)

    lang_note = _lang(ctx, "Respond in English.", "", "Respond in Telugu (తెలుగు). Every word in Telugu script.")
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
             f'{lang_note} 2 sentences maximum.'}
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
             f'{lang_note} 2 sentences maximum.'}
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
        # v10.6.4 FIX 2: Yes/no questions need different hint strategy
        answer_lower = (q.get("answer", "") or "").lower().strip()
        is_yes_no = answer_lower in ("haan", "nahi", "yes", "no", "true", "false", "ha", "nah")
        skill = q.get("target_skill", "")

        if is_yes_no and "perfect_square" in skill:
            explanation = q.get("explanation", "")
            h = _lang(ctx,
                f"Think about it — is there a whole number that multiplied by itself gives this number? {explanation}",
                f"सोचिए — क्या कोई whole number खुद से multiply करके यह number दे सकता है? {explanation}",
                f"ఆలోచించండి — ఏదైనా whole number దాని తోనే multiply చేస్తే ఈ number వస్తుందా? {explanation}")
        elif "perfect_square" in skill:
            h = _lang(ctx, "Think: which number multiplied by itself gives this answer?", "सोचिए: कौनसा number खुद से multiply करके यह answer देगा?", "ఆలోచించండి: ఏ number ని దాని తోనే multiply చేస్తే ఈ answer వస్తుంది?")
        elif "cube" in skill:
            h = _lang(ctx, "Think: which number multiplied three times gives this answer?", "सोचिए: कौनसा number तीन बार multiply करके यह answer देगा?", "ఆలోచించండి: ఏ number ని మూడు సార్లు multiply చేస్తే ఈ answer వస్తుంది?")
        elif "fraction" in skill.lower():
            h = _lang(ctx, "First look at the numerators, then the denominators.", "पहले numerators को देखो, फिर denominators को.", "ముందు numerators చూడండి, తర్వాత denominators చూడండి.")
        else:
            # Generic hint based on answer type
            h = _lang(ctx, "The answer is a number. Think step by step.", "जवाब एक number है। Step by step सोचिए।", "Answer ఒక number. Step by step ఆలోచించండి.")

    lang_instruction = _lang(ctx, "Say naturally in English.", "Say naturally in Hinglish.", "Say naturally in Telugu (తెలుగు).")
    # v10.6.4 FIX 4: Devanagari Hindi, not Roman Hindi
    ack = _lang(ctx,
        '"That\'s okay, let me help." ',
        '"कोई बात नहीं, hint देती हूँ।" ',
        '"పరవాలేదు, hint ఇస్తాను." ')
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
        sol = q.get("solution") or q.get("explanation") or ""
        if not sol:
            answer = q.get("answer", "")
            hints = q.get("hints", [])
            sol = f"The answer is {answer}."
            if hints:
                sol += f" {hints[-1]}"

    # v7.3.24: Language-aware encouragement
    lang_pref = ctx.get("language_pref", "hinglish")
    encouragement = _lang(ctx, "It's okay, now you understand.", "Koi baat nahi, ab samajh aa gaya hoga.", "పరవాలేదు, ఇప్పుడు అర్థమైంది.")
    lang_note = _lang(ctx, "Present in English.", "", "Present in Telugu (తెలుగు).")
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'3rd wrong. Show solution: "{sol}". {lang_note} Walk through in 2-3 sentences. Be encouraging: "{encouragement}" No new question.'}]


def _build_pick_next_question(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware transitions
    lang_pref = ctx.get("language_pref", "hinglish")
    transition = _lang(ctx, "Let's try another one.", "Chalo, ek aur try karte hain.", "మరొకటి try చేద్దాం.")
    done_msg = _lang(ctx, "All questions for this topic are done! Great practice.", "Is topic ke questions ho gaye! Bahut achhi practice hui.", "ఈ topic questions అయిపోయాయి! చాలా బాగా practice చేశారు.")
    # v7.3.25: Tell LLM to present question in session language
    q_lang = _lang(ctx, "Present question in English (translate any Hindi).", "", "Present question in Telugu (తెలుగు). Translate any Hindi to Telugu.")

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

    if comfort_count >= 2:
        # v10.1: Exit comfort loop — offer to continue
        msg = _lang(ctx,
            'Student has been comforted. Now gently offer to continue: '
            '"Would you like to try an easy question? No pressure at all." '
            '1 sentence only.',
            'Student ko comfort mil chuka hai. Ab gently offer karo: '
            '"Ek aasan sawaal try karein? Bilkul koi pressure nahi." '
            '1 sentence only.',
            'Student కి comfort అయింది. ఇప్పుడు gently offer చేయండి Telugu లో: '
            '"ఒక easy question try చేద్దామా? ఏ pressure లేదు." '
            '1 sentence only.')
        return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)},
                {"role": "user", "content": msg}]

    comfort_mode = _lang(ctx,
        '\nCOMFORT MODE: Do NOT teach. Do NOT ask questions. Just acknowledge feelings. Use: "It\'s okay", "This is difficult, isn\'t it?". End: "Let me know when you\'re ready."\n',
        '\nCOMFORT MODE: Do NOT teach. Do NOT ask questions. Just acknowledge feelings. Use: "Koi baat nahi", "Mushkil lag raha hai na?". End: "Jab ready ho, batana."\n',
        '\nCOMFORT MODE: Do NOT teach. Do NOT ask questions. Just acknowledge feelings in Telugu. Use: "పరవాలేదు", "కష్టంగా ఉంది కదా?". End: "మీరు ready అయినప్పుడు చెప్పండి."\n')
    return [{"role": "system", "content": _sys(comfort_mode, session_context=ctx, question_data=q)},
            {"role": "user", "content": f'Student said: "{a.student_text}". They are frustrated. Comfort. 2 sentences.'}]


def _build_end_session(a, ctx, q, sk, prev):
    qc = ctx.get("questions_correct", 0)
    qa = ctx.get("questions_attempted", 0)
    # v7.3.24: Language-aware session ending
    lang_pref = ctx.get("language_pref", "hinglish")
    goodbye = _lang(ctx, "See you tomorrow!", "Kal phir milte hain!", "రేపు మళ్ళీ కలుద్దాం!")
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'Session ending. {qc}/{qa} correct. Summarize warmly. Encourage return tomorrow. "{goodbye}" 3 sentences max.'}]


def _build_acknowledge_homework(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware homework acknowledgment
    lang_pref = ctx.get("language_pref", "hinglish")
    msg = _lang(ctx, "Oh, you have homework? Send a photo or read me the question.", "Achha, homework hai? Photo bhejo ya question padh ke batao.", "Homework ఉందా? Photo పంపండి లేదా question చదివి చెప్పండి.")
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'"{msg}" 1 sentence.'}]


def _build_replay_heard(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware replay message
    lang_pref = ctx.get("language_pref", "hinglish")
    msg = _lang(ctx,
        f'Student disputes verdict. Didi heard: "{a.student_text}". Say: "I heard: [heard]. If I misheard, please try again." Be apologetic.',
        f'Student disputes verdict. Didi heard: "{a.student_text}". Say: "Mujhe aisa suna: [heard]. Agar galat suna toh phir try karo." Be apologetic.',
        f'Student disputes verdict. Didi heard: "{a.student_text}". Say in Telugu: "నాకు ఇలా వినిపించింది: [heard]. తప్పు అయితే, మళ్ళీ try చేయండి." Be apologetic.')
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": msg}]


def _build_ask_repeat(a, ctx, q, sk, prev):
    # v7.3.24: Language-aware repeat request
    lang_pref = ctx.get("language_pref", "hinglish")
    msg = _lang(ctx, "Sorry, I didn't understand. Could you please say that again?", "Sorry, samajh nahi aaya. Ek baar phir boliye?", "Sorry, అర్థం కాలేదు. మళ్ళీ చెప్పగలరా?")
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)}, {"role": "user", "content": f'"{msg}" 1 sentence.'}]


# v7.2.0: New builders for language switch and meta questions

def _build_acknowledge_language_switch(a, ctx, q, sk, prev):
    """Acknowledge language switch and CONTINUE teaching in new language."""
    new_lang = a.extra.get("new_language", "hinglish")
    # v7.3.21 Fix 1: Continue teaching instead of asking "what would you like to know"
    if new_lang in ("telugu", "te-IN"):
        msg = 'Student switched to Telugu. Acknowledge briefly ("అలాగే, తెలుగులో చెప్తాను.") and CONTINUE teaching the current topic in Telugu script. Do NOT ask what they want to learn. 2 sentences max.'
    elif new_lang == "english":
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
        steer_back = _lang(ctx,
            ' Then gently steer back: "Now, back to our question..."',
            ' Phir wapas laao: "Ab, apne sawaal pe wapas aate hain..."',
            ' తర్వాత question వైపు తీసుకెళ్ళండి: "ఇప్పుడు, మన question కి వద్దాం..."')
    else:
        steer_back = ""

    # v7.3.28 Fix 1: Check chapter/topic FIRST since meta_type is always "more_examples"
    student_lower = a.student_text.lower()
    if "chapter" in student_lower or "topic" in student_lower or "kaunsa" in student_lower or "कौन" in a.student_text or "number" in student_lower:
        # v10.5.5: Include chapter number in response
        chapter_response = _lang(ctx, f"We are learning {ch}.", f"हम {ch} पढ़ रहे हैं।", f"మనం {ch} నేర్చుకుంటున్నాం.")
        msg = f'Student asked which chapter. Say EXACTLY: "{chapter_response}" Include the chapter NUMBER.{steer_back}'
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
    ch_key = ctx.get("chapter", "")
    ch = CHAPTER_NAMES.get(ch_key, ch_key.replace("_", " ").title())

    msg = _lang(ctx,
        f'Student is in greeting phase but hasn\'t started. Warmly re-invite: "No worries! Ready to start learning {ch}?" 1 sentence max.',
        f'Student greeting phase mein hai, start nahi kiya. Warmly re-invite karo: "Koi baat nahi! {ch} shuru karein?" 1 sentence max.',
        f'Student greeting phase లో ఉన్నారు, start చేయలేదు. Warmly re-invite చేయండి Telugu లో: "పరవాలేదు! {ch} start చేద్దామా?" 1 sentence max.')
    return [{"role": "system", "content": _sys(session_context=ctx, question_data=q)},
            {"role": "user", "content": msg}]


def build_inline_eval_prompt(session_context, question_data, student_text,
                             hint_level, next_question_data, questions_attempted):
    """v10.5.1: Combined eval + response in one LLM call.
    Eliminates separate eval LLM call (~1.3s savings).
    gpt-4.1 evaluates the answer AND responds in a single call.
    Returns (messages, is_session_end) tuple.
    """
    from app.config import MAX_QUESTIONS_PER_SESSION

    if not question_data:
        return None, False

    lang_pref = session_context.get("language_pref", "hinglish")
    use_english = lang_pref == "english"

    q_text = question_data.get("question_voice") or question_data.get("question_text", "")
    expected = question_data.get("answer", "")
    variants = question_data.get("answer_variants", [])

    # Build hint text for incorrect path
    question_id = question_data.get("question_id") or question_data.get("id")
    cb_hints = []
    if _content_bank and question_id:
        cb_hints = _content_bank.get_hints(question_id)
    q_hints = question_data.get("hints") or []

    if hint_level >= 2:
        # Show solution path
        sol = None
        if _content_bank and question_id:
            sol = _content_bank.get_full_solution_tts(question_id)
        if not sol:
            sol = question_data.get("solution") or question_data.get("explanation") or ""
            if not sol:
                answer = question_data.get("answer", "")
                hints = question_data.get("hints", [])
                sol = f"The answer is {answer}."
                if hints:
                    sol += f" {hints[-1]}"
        incorrect_instruction = _lang(session_context,
            f'Show the full solution: "{sol}". Walk through in 2 sentences. '
            f'Be encouraging: "It\'s okay, now you understand."',
            f'Full solution दिखाओ: "{sol}". 2 sentences में समझाओ। '
            f'Encouraging बोलो: "कोई बात नहीं, अब समझ आ गया होगा।"',
            f'Full solution చూపించు: "{sol}". 2 sentences లో explain చేయి. '
            f'Encouraging గా: "పరవాలేదు, ఇప్పుడు అర్థమైంది."'
        )
    else:
        # Hint path
        target_hint_level = hint_level + 1  # hint_level 0 → hint 1, hint_level 1 → hint 2
        if cb_hints and target_hint_level <= len(cb_hints):
            h = cb_hints[target_hint_level - 1]
        elif target_hint_level <= len(q_hints):
            h = q_hints[target_hint_level - 1]
        else:
            # v10.6.4 FIX 2: Yes/no questions need different hint strategy
            answer_lower = (question_data.get("answer", "") or "").lower().strip()
            is_yes_no = answer_lower in ("haan", "nahi", "yes", "no", "true", "false", "ha", "nah")
            skill = question_data.get("target_skill", "")

            if is_yes_no and "perfect_square" in skill:
                explanation = question_data.get("explanation", "")
                h = _lang(session_context,
                    f"Think about it — is there a whole number that multiplied by itself gives this number? {explanation}",
                    f"सोचिए — क्या कोई whole number खुद से multiply करके यह number दे सकता है? {explanation}",
                    f"ఆలోచించండి — ఏదైనా whole number దాని తోనే multiply చేస్తే ఈ number వస్తుందా? {explanation}")
            elif "perfect_square" in skill:
                h = _lang(session_context, "Think: which number multiplied by itself gives this answer?", "सोचिए: कौनसा number खुद से multiply करके यह answer देगा?", "ఆలోచించండి: ఏ number ని దాని తోనే multiply చేస్తే ఈ answer వస్తుంది?")
            elif "cube" in skill:
                h = _lang(session_context, "Think: which number multiplied three times gives this answer?", "सोचिए: कौनसा number तीन बार multiply करके यह answer देगा?", "ఆలోచించండి: ఏ number ని మూడు సార్లు multiply చేస్తే ఈ answer వస్తుంది?")
            else:
                h = _lang(session_context, "The answer is a number. Think step by step.", "जवाब एक number है। Step by step सोचिए।", "Answer ఒక number. Step by step ఆలోచించండి.")

        # v10.6.4 FIX 4: Devanagari Hindi, not Roman Hindi
        ack = _lang(session_context, '"That\'s okay, let me help." ', '"कोई बात नहीं, hint देती हूँ।" ', '"పరవాలేదు, hint ఇస్తాను." ')
        incorrect_instruction = f'Start with {ack} Then give hint: "{h}". Ask to try again.'

    # Build correct path instruction
    is_session_end = (questions_attempted + 1) >= MAX_QUESTIONS_PER_SESSION
    if is_session_end:
        correct_instruction = _lang(session_context,
            'Say brief praise, then end the session warmly. "Great practice today!"',
            'Brief praise do, phir session end karo. "Bahut achhi practice hui aaj!"',
            'Brief praise చెప్పండి, తర్వాత session end చేయండి Telugu లో. "చాలా బాగా practice చేశారు!"')
    elif next_question_data:
        next_q_voice = next_question_data.get("question_voice") or next_question_data.get("question_text", "")
        q_lang = _lang(session_context, "Present question in English (translate any Hindi).", "", "Present question in Telugu (తెలుగు). Translate any Hindi to Telugu.")
        correct_instruction = (
            f'Say brief praise like "Well done!" (1 sentence), '
            f'then read the NEXT question: "{next_q_voice}". {q_lang}'
        )
    else:
        done_msg = _lang(session_context, "All questions for this topic are done! Great practice.", "Is topic ke saare questions ho gaye! Bahut achhi practice hui.", "ఈ topic questions అయిపోయాయి! చాలా బాగా practice చేశారు.")
        correct_instruction = f'Say brief praise, then: "{done_msg}"'
        is_session_end = True

    variants_str = ", ".join(variants) if variants else "none"
    lang_instruction = _lang(session_context, "Respond in English.", "Respond in Hinglish.", "Respond in Telugu (తెలుగు). Every word in Telugu script.")

    user_msg = (
        f'Student was asked: "{q_text}"\n'
        f'Expected answer: {expected}\n'
        f'Acceptable alternate forms: {variants_str}\n'
        f'Student said: "{student_text}"\n\n'
        f'STEP 1: Evaluate if the student\'s answer is correct. '
        f'Numbers in any language count (Hindi words, Devanagari, English). '
        f'If the correct number appears in their response as their answer, it IS correct.\n\n'
        f'STEP 2: Start your response with EXACTLY [CORRECT] or [INCORRECT] on the first line.\n\n'
        f'If [CORRECT]:\n{correct_instruction}\n\n'
        f'If [INCORRECT]:\n{incorrect_instruction}\n\n'
        f'{lang_instruction} 2 sentences maximum after the tag line.'
    )

    messages = [
        {"role": "system", "content": _sys(session_context=session_context, question_data=question_data)},
        {"role": "user", "content": user_msg},
    ]
    return messages, is_session_end


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
