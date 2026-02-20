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

DIDI_BASE = """You are Didi, a caring Hindi-speaking tutor for Class 8 Math.

PERSONALITY: Warm older sister. Patient. Focused on learning. Use "aap" form always.

FORMAT RULES (STRICT):
- Maximum 2 sentences, 40 words
- ONE idea per turn — never teach AND ask together
- Vary openings — don't always start with "Acha" or "Toh"

SPECIFICITY (CRITICAL):
- ALWAYS reference what the student said: "Aapne X bola..."
- NEVER give generic feedback like "try again" or "sochiye"
- Explain specifically what was right or wrong about their answer

NUMBERS:
- Use digits or English: "5 times 5 = 25", "3 squared = 9"
- NEVER use Hindi number words: teen, chaar, paanch, pachees
"""

DIDI_NO_PRAISE = "\nANSWER INCORRECT. No praise. No shabash/bahut accha/well done.\n"
DIDI_PRAISE_OK = "\nANSWER CORRECT. Praise briefly, reference their answer.\n"

LANG_ENGLISH = """
LANGUAGE: English only. No Hindi words. No "Acha", "Theek hai", "Dekho".
"""
LANG_HINDI = """
LANGUAGE: Hindi (Devanagari). Use digits for numbers: "5 × 5 = 25".
"""
LANG_HINGLISH = """
LANGUAGE: Hinglish. Natural mix of Hindi-English. Use digits for math.
"""


def _get_language_instruction(session_context: dict) -> str:
    """Get language instruction based on session preference."""
    pref = session_context.get("language_pref", "hinglish")
    if pref == "english":
        return LANG_ENGLISH
    elif pref == "hindi":
        return LANG_HINDI
    return LANG_HINGLISH


def build_prompt(action, session_context, question_data=None, skill_data=None, previous_didi_response=None, conversation_history=None):
    at = action.action_type
    builder = _BUILDERS.get(at, _build_fallback)
    messages = builder(action, session_context, question_data, skill_data, previous_didi_response)

    # v7.2.0: Inject language preference into system prompt (BUG 2 fix)
    lang_instruction = _get_language_instruction(session_context)
    if messages and messages[0].get("role") == "system":
        messages[0]["content"] = messages[0]["content"] + lang_instruction

    # Inject student's actual words for specificity
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


def _sys(extra=""):
    return DIDI_BASE + extra


def _build_ask_topic(a, ctx, q, sk, prev):
    if a.extra.get("retry"):
        msg = f'Student said: "{a.student_text}". Couldn\'t identify subject. Ask specifically: "Aaj school mein kaunsa subject padha? Math, Science, ya Hindi?"'
    else:
        msg = "Student just logged in. Ask warmly what they studied in school today. Ask about their day first, then the subject."
    return [{"role": "system", "content": _sys()}, {"role": "user", "content": msg}]


def _build_apologize_no_subject(a, ctx, q, sk, prev):
    s = a.detected_subject or "that subject"
    return [{"role": "system", "content": _sys()}, {"role": "user", "content": f'Student wants {s}, but only Math available. Say warmly: "Abhi mere paas sirf Math hai, lekin jaldi {s} bhi aa jayega! Chalo math practice karte hain?"'}]


def _build_probe_understanding(a, ctx, q, sk, prev):
    ch = ctx.get("chapter", "rational numbers")
    return [{"role": "system", "content": _sys()}, {"role": "user", "content": f'Student studied {ch}. Ask ONE simple concept-check question (not calculation). Example for fractions: "Agar denominator same hai, toh add kaise karte hain?"'}]


def _build_teach_concept(a, ctx, q, sk, prev):
    ch = ctx.get("chapter", "rational numbers")
    extra = ""

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

    # Get actual teaching content from SKILL_TEACHING
    from app.content.seed_questions import SKILL_TEACHING
    skill_key = q.get("target_skill", "") if q else ctx.get("skill", "")
    lesson = SKILL_TEACHING.get(skill_key, {})

    # v7.2.0: Rotate approaches based on teaching_turn (BUG 3 fix)
    # Turn 0: definition/pre_teach, Turn 1: indian_example, Turn 2+: key_insight/visual
    if teaching_turn >= 2:
        teach_content = lesson.get("key_insight") or lesson.get("indian_example") or lesson.get("pre_teach") or ""
    elif teaching_turn == 1:
        teach_content = lesson.get("indian_example") or lesson.get("key_insight") or lesson.get("pre_teach") or ""
    else:
        teach_content = lesson.get("pre_teach") or lesson.get("teaching") or ""

    approach = a.extra.get("approach", "fresh")

    # v7.2.0: Phase-based prompts (BUG 1 fix)
    if a.extra.get("forced_transition"):
        # Turn 3+: Force to question with gentle transition
        msg = 'Say: "Koi baat nahi, chaliye ek sawaal try karte hain." Then read the question.'
    elif approach == "answer_question":
        msg = f'Student asked: "{a.student_text}". Answer their question about {ch}. {teach_content if teach_content else "Use simple example."} 2 sentences.'
    elif approach == "different_example":
        if teaching_turn == 1:
            msg = f'Student didn\'t understand. Use this DIFFERENT example: "{teach_content}". 2 sentences. End: "Ab samajh aaya?"'
        elif teaching_turn >= 2:
            # Simplest version
            msg = f"Student still doesn't understand. Give the SIMPLEST explanation possible: \"{teach_content}\" 2 sentences. End: \"Ab samajh aaya?\""
        else:
            msg = f"Student didn't understand {ch}. Try roti cutting, cricket scoring, or Diwali sweets. 2 sentences. End: \"Ab samajh aaya?\""
    else:
        # Turn 0: Initial teaching
        if teach_content:
            msg = f'Teach this concept naturally in Hinglish: "{teach_content}". 2 sentences. End: "Samajh aaya?"'
        else:
            msg = f"Teach one concept from {ch}. Use Indian example. 2 sentences. End: \"Samajh aaya?\""
    return [{"role": "system", "content": _sys(extra)}, {"role": "user", "content": msg}]


def _build_read_question(a, ctx, q, sk, prev):
    if not q:
        return [{"role": "system", "content": _sys()}, {"role": "user", "content": 'No more questions. Say: "Is topic ke saare questions ho gaye! Bahut achhi practice hui."'}]
    if a.extra.get("nudge"):
        return [{"role": "system", "content": _sys()}, {"role": "user", "content": f'Student hasn\'t answered. Question: "{q["question_voice"]}". Gently nudge them to try.'}]
    d = "This is an easier question. " if a.extra.get("difficulty") == "easy" else ""
    return [{"role": "system", "content": _sys()}, {"role": "user", "content": f'{d}Read this question naturally: "{q["question_voice"]}". End: "Batao, kya answer hai?"'}]


def _build_evaluate_answer(a, ctx, q, sk, prev):
    v = a.verdict
    if not v:
        return _build_fallback(a, ctx, q, sk, prev)
    # Note: When correct, route_after_evaluation changes action_type to pick_next_question,
    # so this "correct" branch rarely executes. Kept for edge cases.
    if v.correct:
        return [{"role": "system", "content": _sys(DIDI_PRAISE_OK)}, {"role": "user", "content": f'Answer: "{v.student_parsed or a.student_text}". Correct: "{v.correct_display}". CORRECT. Praise briefly referencing their answer. 1 sentence only.'}]
    return [{"role": "system", "content": _sys(DIDI_NO_PRAISE)}, {"role": "user", "content": f'Answer: "{v.student_parsed or a.student_text}". Correct: "{v.correct_display}". Diagnostic: "{v.diagnostic}". Tell what went wrong. Say "Aapne ... bola". Do NOT reveal answer. 2 sentences.'}]


def _build_give_hint(a, ctx, q, sk, prev):
    if not q:
        return _build_fallback(a, ctx, q, sk, prev)
    hints = q.get("hints") or []

    # Get actual hint or build from question context
    if a.hint_level <= len(hints):
        h = hints[a.hint_level - 1]
    else:
        # No more hints — build contextual hint from question and answer
        answer = q.get("answer", "")
        skill = q.get("target_skill", "")
        if "perfect_square" in skill:
            h = f"Sochiye: kaunsa number khud se multiply karke yeh answer dega?"
        elif "cube" in skill:
            h = f"Sochiye: kaunsa number teen baar multiply karke yeh answer dega?"
        elif "fraction" in skill.lower():
            h = f"Pehle numerators ko dekho, phir denominators ko."
        else:
            # Generic hint based on answer type
            h = f"Is sawaal ka jawab ek number hai. Sochiye step by step."

    return [{"role": "system", "content": _sys(DIDI_NO_PRAISE)}, {"role": "user", "content": f'Give hint #{a.hint_level}: "{h}". Say naturally in Hinglish. Ask to try again. 2 sentences.'}]


def _build_show_solution(a, ctx, q, sk, prev):
    if not q:
        return _build_fallback(a, ctx, q, sk, prev)
    sol = q.get("solution", "Solution not available.")
    return [{"role": "system", "content": _sys()}, {"role": "user", "content": f'3rd wrong. Show solution: "{sol}". Walk through in 2-3 sentences. Be encouraging: "Koi baat nahi, ab samajh aa gaya hoga." No new question.'}]


def _build_pick_next_question(a, ctx, q, sk, prev):
    if a.extra.get("follow_up"):
        if q:
            return [{"role": "system", "content": _sys()}, {"role": "user", "content": f'After solution, transition to next question. Say briefly "Chalo, ek aur try karte hain." Then read: "{q["question_voice"]}"'}]
        return [{"role": "system", "content": _sys()}, {"role": "user", "content": 'After solution, say briefly: "Chalo, ek aur try karte hain."'}]
    if q:
        # Include praise for correct answer + the next question
        return [{"role": "system", "content": _sys(DIDI_PRAISE_OK)}, {"role": "user", "content": f'Student answered correctly. Brief praise (1 sentence), then read next question: "{q["question_voice"]}"'}]
    return [{"role": "system", "content": _sys()}, {"role": "user", "content": 'No more questions available. Say: "Is topic ke questions ho gaye! Bahut achhi practice hui."'}]


def _build_comfort_student(a, ctx, q, sk, prev):
    return [{"role": "system", "content": _sys("\nCOMFORT MODE: Do NOT teach. Do NOT ask questions. Just acknowledge feelings. Use: \"Koi baat nahi\", \"Mushkil lag raha hai na?\". End: \"Jab ready ho, batana.\"\n")},
            {"role": "user", "content": f'Student said: "{a.student_text}". They are frustrated. Comfort. 2 sentences.'}]


def _build_end_session(a, ctx, q, sk, prev):
    qc = ctx.get("questions_correct", 0)
    qa = ctx.get("questions_attempted", 0)
    return [{"role": "system", "content": _sys()}, {"role": "user", "content": f'Session ending. {qc}/{qa} correct. Summarize warmly. Encourage return tomorrow. "Kal phir milte hain!" 3 sentences max.'}]


def _build_acknowledge_homework(a, ctx, q, sk, prev):
    return [{"role": "system", "content": _sys()}, {"role": "user", "content": '"Achha, homework hai? Photo bhejo ya question padh ke batao." 1 sentence.'}]


def _build_replay_heard(a, ctx, q, sk, prev):
    return [{"role": "system", "content": _sys()}, {"role": "user", "content": f'Student disputes verdict. Didi heard: "{a.student_text}". Say: "Mujhe aisa suna: [heard]. Agar galat suna toh phir try karo." Be apologetic.'}]


def _build_ask_repeat(a, ctx, q, sk, prev):
    return [{"role": "system", "content": _sys()}, {"role": "user", "content": '"Sorry, samajh nahi aaya. Ek baar phir boliye?" 1 sentence.'}]


# v7.2.0: New builders for language switch and meta questions

def _build_acknowledge_language_switch(a, ctx, q, sk, prev):
    """Acknowledge language switch and continue in new language."""
    new_lang = a.extra.get("new_language", "hinglish")
    if new_lang == "english":
        msg = 'Student asked to switch to English. Say: "Sure, I can speak in English. What would you like to know?" 1 sentence.'
    elif new_lang == "hindi":
        msg = 'Student asked for Hindi. Say: "ठीक है, मैं हिंदी में बोलती हूं। आगे बढ़ें?" 1 sentence.'
    else:
        msg = 'Student asked for Hinglish. Say: "Theek hai, hum Hinglish mein baat karte hain. Aage badhein?" 1 sentence.'
    return [{"role": "system", "content": _sys()}, {"role": "user", "content": msg}]


def _build_answer_meta_question(a, ctx, q, sk, prev):
    """Answer meta questions like 'more examples', 'which chapter', etc."""
    meta_type = a.extra.get("meta_type", "more_examples")
    ch = ctx.get("chapter", "rational numbers")

    # Get teaching content for more examples
    from app.content.seed_questions import SKILL_TEACHING
    skill_key = q.get("target_skill", "") if q else ""
    lesson = SKILL_TEACHING.get(skill_key, {})

    if "example" in a.student_text.lower() or meta_type == "more_examples":
        examples = lesson.get("indian_example") or lesson.get("examples", "")
        msg = f'Student wants more examples. Give 2-3 NEW examples for {skill_key}. DO NOT repeat the definition. Do NOT reuse: "{prev or ""}". Use fresh examples: {examples if examples else "laddoo, cricket score, rangoli squares"}. 2 sentences.'
    elif "chapter" in a.student_text.lower() or "topic" in a.student_text.lower():
        title = lesson.get("title_hi") or lesson.get("name") or ch
        msg = f'Student asked which chapter. Say: "Yeh {title} chapter hai, Class 8 Math se." 1 sentence.'
    elif "real life" in a.student_text.lower() or "use" in a.student_text.lower():
        msg = f'Student asked about real-life use. Give 1-2 practical examples: architecture, cooking, shopping. How {ch} is used in daily life. 2 sentences.'
    else:
        msg = f'Student asked: "{a.student_text}". Answer briefly about {ch}. 2 sentences.'

    return [{"role": "system", "content": _sys()}, {"role": "user", "content": msg}]


def _build_fallback(a, ctx, q, sk, prev):
    return [{"role": "system", "content": _sys()}, {"role": "user", "content": 'Something unexpected. Say naturally: "Chalo, aage badhte hain."'}]


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
