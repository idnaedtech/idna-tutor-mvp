"""
IDNA EdTech v7.0 — Instruction Builder
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

DIDI_BASE = """You are Didi (दीदी), a warm, patient Hindi-speaking tutor for Class 8 students.

VOICE & TONE:
- Speak in natural Hinglish (Hindi mixed with English as needed)
- Use respectful "aap" form always ("dekhiye", "sochiye", never "tu/tum")
- Sound like a caring older sister, not a robot or chatbot
- Be warm but focused on learning

HARD RULES:
- Maximum 2 sentences. Maximum 55 words. STRICTLY.
- ONE idea per turn. Never teach AND ask a question in the same turn.
- Use Indian examples: roti, cricket, Diwali shopping, monsoon, train journeys
- Do NOT start with "Acha" or "Toh" every time — vary your openings
"""

DIDI_NO_PRAISE = "\nCRITICAL: Do NOT praise. Answer was NOT correct. No shabash/bahut accha/well done.\n"
DIDI_PRAISE_OK = "\nStudent answered correctly. Praise genuinely. Reference their exact answer.\n"


def build_prompt(action, session_context, question_data=None, skill_data=None, previous_didi_response=None):
    at = action.action_type
    builder = _BUILDERS.get(at, _build_fallback)
    return builder(action, session_context, question_data, skill_data, previous_didi_response)


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
    if a.reteach_count > 0:
        extra = f"\nRe-teach #{a.reteach_count}. Use COMPLETELY DIFFERENT example. Previous: \"{prev or 'unknown'}\". Do NOT repeat."

    # Get actual teaching content from SKILL_TEACHING
    from app.content.seed_questions import SKILL_TEACHING
    skill_key = q.get("target_skill", "") if q else ctx.get("skill", "")
    lesson = SKILL_TEACHING.get(skill_key, {})

    # Get content based on reteach count
    if a.reteach_count >= 2:
        teach_content = lesson.get("key_insight") or lesson.get("indian_example") or lesson.get("pre_teach") or ""
    elif a.reteach_count == 1:
        teach_content = lesson.get("indian_example") or lesson.get("key_insight") or lesson.get("pre_teach") or ""
    else:
        teach_content = lesson.get("pre_teach") or lesson.get("teaching") or ""

    approach = a.extra.get("approach", "fresh")
    if approach == "answer_question":
        msg = f'Student asked: "{a.student_text}". Answer their question about {ch}. {teach_content if teach_content else "Use simple example."} 2 sentences.'
    elif approach == "different_example":
        if teach_content:
            msg = f'Student didn\'t understand. Explain differently: "{teach_content}". 2 sentences. End: "Ab samajh aaya?"'
        else:
            msg = f"Student didn't understand {ch}. Try roti cutting, cricket scoring, or Diwali sweets. 2 sentences. End: \"Ab samajh aaya?\""
    else:
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
}
