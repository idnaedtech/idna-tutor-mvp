"""
IDNA Didi Voice — LLM Speech Generation
=========================================
This module handles ALL interaction with the LLM.
Two responsibilities:
1. Judge student answers (tool calling with gpt-4o-mini)
2. Generate Didi's spoken response (gpt-4o)

Nothing else in the system talks to the LLM.
"""

import json
import re
import os
from openai import OpenAI
from tutor_tools import TUTOR_TOOLS


# ============================================================
# CONFIG
# ============================================================
TOOL_MODEL = "gpt-4o-mini"
SPEECH_MODEL = "gpt-4o"

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=30.0,
            max_retries=2
        )
    return _client


# ============================================================
# DIDI'S IDENTITY
# ============================================================

DIDI_PROMPT = """You are Didi — a private math tutor working with {student_name}, a Class 8 student in India. Everything you say is spoken aloud. This is a one-on-one tutoring session.

YOUR CHARACTER:
You are an experienced teacher with 12 years of teaching. You are warm but professional. You speak with the natural authority of a teacher who genuinely cares. You use respectful Hindi — 'aap', 'dekhiye', 'sochiye', 'bataiye' — not casual 'tu/tum'. You are like a respected older sister or a kind school teacher, NOT a street friend. Your students respect you AND feel comfortable with you.

{lang_instruction}

YOUR TEACHING STYLE:
- When they answer correctly: Brief, specific acknowledgment. "Bilkul sahi. Minus 1 over 7." Then move on.
- When they answer partially correct: Acknowledge what's right FIRST. "Haan, minus 1 sahi hai — that's the numerator. Ab denominator kya hoga? Denominator same rehta hai na?"
- When they answer wrong: Don't ask "what were you thinking?" — instead, point out the specific error gently. "Yahan sign pe dhyan do. Minus 3 plus 2 hota hai minus 1, plus 1 nahi."
- When they don't know: Don't ask micro-questions repeatedly. Teach the concept simply with one concrete example, then ask them to try.
- When they repeat the same answer: NEVER re-ask the same question. Either confirm what's right and guide to what's missing, or explain the full solution.

RULES:
1. Complete every sentence. Never stop mid-thought.
2. ONLY discuss the CURRENT question. NEVER reference previous questions.
3. Say fractions as words: "minus 3 over 7", "2 over 3". Never write -3/7.
4. No markdown, no bullets. Spoken words only.
5. Keep responses 2-4 sentences. Up to 5 when teaching a concept.
6. If the student gives the same answer twice, do NOT ask the same question again. Either accept it and guide forward, or explain.
7. Use respectful Hindi. NEVER say "dekh", "batao", "sun", "karo" — use "dekhiye", "bataiye", "suniye", "kariye".

CRITICAL RULE — MATH FORMATTING:
When explaining math, use actual numbers and symbols. Never write math as long Hindi paragraphs.
WRONG: "minus 3 aur 2 ka addition karte hain toh minus 1 aata hai aur denominator same rehta hai 7"
RIGHT: "Dekhiye: minus 3 plus 2 equals minus 1. Denominator same rehta hai: 7. Toh answer: minus 1 over 7."
Always show the working as: number operator number equals result.
Keep each step on its own. Short sentence, then math, then short sentence.
Students need to HEAR the numbers clearly, not long paragraphs about numbers.

CRITICAL — ACKNOWLEDGE CORRECT SUB-STEPS IMMEDIATELY:
When you ask a sub-question like "minus 3 plus 2 kya hoga?" and the student answers correctly (e.g., "minus one"), you MUST:
- Say "Sahi hai!" or "Bilkul sahi!"
- Immediately give the next step
- NEVER re-ask a question the student already answered correctly
When scaffolding multi-step problems, track your progress:
- After each correct sub-step, move to the NEXT step
- If audio is unclear/garbled, say "Ek baar phir bataiye" instead of going back to a previous step
- Never go backwards in the scaffold sequence

HANDLING UNCLEAR AUDIO:
If the student's input seems garbled, nonsensical, or very short (like "mine", "rueldo", single dot "."), respond with:
"{student_name} ji, aapki awaaz clear nahi aayi. Ek baar phir bataiye?"
Do NOT treat garbled audio as a wrong answer. Do NOT re-explain the concept. Just ask them to repeat.

NEVER SAY: "Great job!", "Excellent!", "Let me help you", "That's a great question", "Can you tell me how you would approach this?", "Can you tell me more about how you thought about that?", "Haha focus yaar", "Arre chalo"

{lang_strict}

{history}"""


# ============================================================
# PUBLIC FUNCTIONS
# ============================================================

def generate_greeting(student_name: str, chapter_name: str,
                      question_text: str, lang: str) -> str:
    """Generate Didi's opening greeting + first question."""
    system = _build_system(student_name, lang, "")
    prompt = (
        f"{student_name} just sat down. You're doing {chapter_name} today. "
        f"Say hi — short, warm, real — then read the first question: {question_text}"
    )
    return _speak(system, prompt)


def judge_answer(student_input: str, question_context: str,
                 student_name: str, lang: str, history: str) -> dict:
    """
    LLM judges the student's answer using tool calling.
    Returns: {"tool": str, "args": dict}
    """
    system = _build_system(student_name, lang, history)

    try:
        response = _get_client().chat.completions.create(
            model=TOOL_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": question_context}
            ],
            tools=TUTOR_TOOLS,
            tool_choice="required",
            max_tokens=200,
            temperature=0.4
        )
        tc = response.choices[0].message.tool_calls[0]
        return {
            "tool": tc.function.name,
            "args": json.loads(tc.function.arguments)
        }
    except Exception as e:
        print(f"[Judge Error] {e}")
        return {"tool": "give_hint", "args": {"hint_level": 1, "student_mistake": "unclear"}}


def generate_speech(instruction: str, student_name: str,
                    lang: str, history: str) -> str:
    """Generate Didi's spoken response for any action."""
    system = _build_system(student_name, lang, history)
    return _speak(system, instruction)


# ============================================================
# SPEECH BUILDERS — one per action type
# ============================================================

def build_hint_instruction(question_ctx: str, hint_level: int,
                           student_input: str) -> str:
    return (
        f"Give a level {hint_level} hint.\n\n"
        f"{question_ctx}\n\n"
        f"Student said: \"{student_input}\"\n\n"
        f"IMPORTANT: If the student's answer is PARTIALLY correct (e.g. they got the numerator right but forgot the denominator), "
        f"acknowledge what's right FIRST, then guide them to what's missing. "
        f"Do NOT re-ask the same question from scratch.\n\n"
        f"{'Give a conceptual nudge — point them in the right direction without revealing the answer.' if hint_level == 1 else 'Show them the first step of the solution. Still dont reveal the final answer.'}"
    )


def build_explain_instruction(question_ctx: str, next_question: str = "") -> str:
    transition = ""
    if next_question:
        transition = f"\n\nAfter explaining, say 'Okay, let's try the next one' and read: {next_question}"
    return (
        f"Explain the full solution step by step. Be kind — they struggled.\n\n"
        f"{question_ctx}"
        f"{transition}"
    )


def build_encourage_instruction(question_ctx: str, student_input: str) -> str:
    return (
        f"Student doesn't know the answer. Encourage them to try.\n"
        f"Break the problem into a smaller piece. Ask for just the first step.\n"
        f"Don't repeat the full question — just ask one small thing.\n\n"
        f"{question_ctx}\n\n"
        f"Student said: \"{student_input}\""
    )


def build_praise_instruction(question_ctx: str, what_they_did: str,
                              next_question: str = "") -> str:
    transition = ""
    if next_question:
        transition = f"\n\nThen move to: {next_question}"
    return (
        f"Student got it right! Quick specific praise — {what_they_did}.\n"
        f"Don't overdo it. One sentence of praise, then transition.\n\n"
        f"{question_ctx}"
        f"{transition}"
    )


def build_reask_instruction(question_text: str, after_hint: bool = False) -> str:
    if after_hint:
        return (
            f"You gave a hint and the student acknowledged it. "
            f"Now ask them to try answering. Be encouraging: "
            f"'Good, now try it — {question_text}'"
        )
    return f"The student acknowledged but hasn't answered. Gently ask: {question_text}"


def build_redirect_instruction(student_input: str, question_text: str,
                                is_troll: bool = False) -> str:
    if is_troll:
        return (
            f'Student said: "{student_input}" — they\'re joking around. '
            f"Gently redirect in ONE short sentence — something like 'Chalo, wapas question pe aate hain' — "
            f"then briefly re-read: {question_text}. Do NOT explain anything."
        )
    return (
        f'Student said: "{student_input}" — off-topic. '
        f"Redirect gently in ONE sentence, then re-read: {question_text}"
    )


def build_offer_exit_instruction(student_name: str) -> str:
    return (
        f"{student_name} keeps going off-topic. They might be bored or tired. "
        f"Say warmly but respectfully: 'Lagta hai aaj aapka mood thoda alag hai. "
        f"Koi baat nahi, hum baad mein continue kar sakte hain. Ya ek aur question try karein?' "
        f"No guilt, no pressure."
    )


def build_language_switch_instruction(question_text: str) -> str:
    return (
        f"Student asked for English. Switch to English and re-read: {question_text}"
    )


def build_language_reject_instruction(language: str, question_text: str) -> str:
    return (
        f"Student asked to speak in {language}. You can't yet. "
        f"Be warm and respectful: 'Sorry, abhi {language} mein baat nahi kar sakti. "
        f"Jaldi seekh loongi! Filhaal English ya Hindi mein chalte hain.' "
        f"Then re-read: {question_text}"
    )


def build_tone_adjustment_instruction(question_text: str) -> str:
    return (
        f"Student doesn't like how you're talking — they want you to be more respectful "
        f"and formal. Apologize briefly and warmly: 'Sorry about that! I'll speak more respectfully.' "
        f"Then switch to 'aap' instead of 'tu/tum', use 'dekhiye' instead of 'dekh', "
        f"'kariye' instead of 'karo'. Keep being warm but more polite. "
        f"Re-read the current question respectfully: {question_text}"
    )


def build_end_instruction(student_name: str, score: int,
                           completed: int, duration: int, reason: str) -> str:
    return (
        f"Session over. {student_name} got {score}/{completed}. "
        f"Took {duration} minutes. Reason: {reason}. "
        f"Say bye naturally, 2 sentences max."
    )


def build_move_next_instruction(next_question: str) -> str:
    return (
        f"Student understood. Move on immediately. "
        f"Say something brief like 'Okay, next one' — ONE short sentence — "
        f"then read: {next_question}"
    )


# ============================================================
# PRIVATE HELPERS
# ============================================================

def _build_system(student_name: str, lang: str, history: str) -> str:
    formal = "_formal" in lang
    base_lang = lang.replace("_formal", "")

    if base_lang == "english":
        lang_instruction = "The student asked for English only."
        lang_strict = "STRICT ENGLISH ONLY. Do NOT use ANY Hindi words — no 'Chalo', no 'Dekhiye', no 'Haan', no 'Accha'. Pure English. Keep your warm, respectful tone."
    else:
        lang_instruction = "Respectful Hindi-English mix. Use 'Haan', 'Accha', 'Dekhiye', 'Chaliye', 'Koi baat nahi' naturally. Always use 'aap' form, never 'tu/tum'."
        lang_strict = ""

    if formal:
        lang_strict += (
            "\n\nIMPORTANT — FORMAL/RESPECTFUL TONE: The student asked you to be more respectful. "
            "Use 'aap' instead of 'tu/tum'. Use 'dekhiye' instead of 'dekh'. "
            "Use 'kariye' instead of 'karo'. Use 'bataiye' instead of 'batao'. "
            "Still be warm and friendly, but polite — like talking to an older student, not a little kid."
        )

    return DIDI_PROMPT.format(
        student_name=student_name,
        lang_instruction=lang_instruction,
        lang_strict=lang_strict,
        history=history
    )


def _speak(system: str, prompt: str) -> str:
    """Single LLM call for speech generation."""
    try:
        response = _get_client().chat.completions.create(
            model=SPEECH_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.8
        )
        text = _clean(response.choices[0].message.content)

        # Ensure complete sentences
        if text and text[-1] not in '.?!।':
            for i in range(len(text) - 1, -1, -1):
                if text[i] in '.?!।':
                    text = text[:i + 1]
                    break
        return text

    except Exception as e:
        print(f"[Speech Error] {e}")
        return "Ek second. Chalo phir se dekhte hain."


def _clean(text: str) -> str:
    """Clean LLM output for TTS."""
    text = text.strip()
    for char in ['**', '*', '##', '#', '`', '•']:
        text = text.replace(char, '')
    text = text.replace('- ', '')

    # Remove LaTeX
    text = re.sub(r'\\\(.*?\\\)', '', text)
    text = re.sub(r'\\\[.*?\\\]', '', text)

    # Fractions → TTS-friendly
    text = re.sub(r'-(\d+)/(\d+)', r'minus \1 over \2', text)
    text = re.sub(r'(\d+)/(\d+)', r'\1 over \2', text)

    # Remove wrapping quotes
    if len(text) > 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1]
    if len(text) > 2 and text[0] == "'" and text[-1] == "'":
        text = text[1:-1]

    # Remove Didi: prefix
    for prefix in ["Didi:", "didi:", "DIDI:", "Teacher:", "Didi -", "Didi —"]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    return text
