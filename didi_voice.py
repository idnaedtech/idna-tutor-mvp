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

DIDI_PROMPT = """You are Didi, a friendly math tutor in India. You're sitting with {student_name}, Class 8. Everything you say goes through a speaker.

{lang_instruction}

TEACHING STYLE:
- Correct answer → "Sahi hai!" and move on. Don't overpraise.
- Wrong answer → Give a small hint, don't just ask questions.
- Student confused → EXPLAIN the concept simply. Don't keep asking.
- Student asks "why" or "how to use" → Give a short real-world example.

SPEAKING RULES:
1. Short sentences. 2-3 max unless explaining.
2. Say fractions as "minus 3 over 7", not -3/7.
3. Natural Hindi-English: "Dekh", "Chal", "Sahi hai", "Accha". NOT "Kya aap bata sakte hain".
4. NO robotic phrases like "Can you tell me what you were thinking?"

BANNED PHRASES (never use):
- "Can you tell me..."
- "What was your thought process?"
- "How did you approach this?"
- "That's a great question"
- "Let me help you"

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


JUDGE_PROMPT = """You judge math answers. Pick ONE tool.

EXAMPLES:
- Correct: "-1/7", Student: "minus 1 by 7" → MATCH → praise_and_continue
- Correct: "2/3", Student: "two thirds" → MATCH → praise_and_continue
- Correct: "-1/7", Student: "5" → NO MATCH → ask_what_they_did
- Correct: "2/3", Student: "1/3" → NO MATCH → ask_what_they_did

Spoken forms that MATCH written:
- "minus X by Y" = "-X/Y"
- "negative X over Y" = "-X/Y"
- "X by Y" = "X/Y"

YOUR TASK: Compare CORRECT ANSWER to STUDENT SAID. If they mean the same thing, use praise_and_continue. Otherwise use ask_what_they_did."""


def judge_answer(student_input: str, question_context: str,
                 student_name: str, lang: str, history: str) -> dict:
    """
    LLM judges the student's answer using tool calling.
    Returns: {"tool": str, "args": dict}
    """
    try:
        response = _get_client().chat.completions.create(
            model=TOOL_MODEL,
            messages=[
                {"role": "system", "content": JUDGE_PROMPT},
                {"role": "user", "content": question_context}
            ],
            tools=TUTOR_TOOLS,
            tool_choice="required",
            max_tokens=200,
            temperature=0.2
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
    if hint_level == 1:
        guidance = "Give ONE small hint. Example: 'Dekh, denominator same hai toh sirf numerator add kar.'"
    else:
        guidance = "Show the first step clearly. Example: 'Pehle step: minus 3 plus 2 karo. Kitna aaya?'"
    return (
        f"{guidance}\n\n"
        f"{question_ctx}\n\n"
        f"Student said: \"{student_input}\"\n\n"
        f"DO NOT ask 'what did you do' or 'how did you think'. Just give the hint directly."
    )


def build_explain_instruction(question_ctx: str, next_question: str = "") -> str:
    transition = ""
    if next_question:
        transition = f"\n\nAfter explaining, say 'Chal, agla try karte hain' and read: {next_question}"
    return (
        f"Explain simply like talking to your younger sibling.\n"
        f"Example: 'Dekh, yahan dono mein neeche 7 hai na? Toh bas upar wale add kar. Minus 3 plus 2 equals minus 1. Answer minus 1 over 7.'\n"
        f"Short, clear, no fancy words.\n\n"
        f"{question_ctx}"
        f"{transition}"
    )


def build_encourage_instruction(question_ctx: str, student_input: str) -> str:
    return (
        f"Student doesn't know. Give them a starting point, not a question.\n"
        f"Example: 'Dekh, pehle ye samajh - dono fractions mein neeche 7 hai. Toh upar wale numbers ko...'\n"
        f"Lead them, don't interrogate them.\n\n"
        f"{question_ctx}"
    )


def build_praise_instruction(question_ctx: str, what_they_did: str,
                              next_question: str = "") -> str:
    if next_question:
        return (
            f"CORRECT! Say ONLY: 'Sahi hai! Chal agla.' Then read: {next_question}\n"
            f"DO NOT explain anything. Just praise and move on."
        )
    return "CORRECT! Say ONLY: 'Sahi hai!' Nothing else."


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
            f"Smile it off in ONE short sentence — 'Haha, focus yaar' or 'Arre chalo wapas' — "
            f"then briefly re-read: {question_text}. Do NOT explain anything."
        )
    return (
        f'Student said: "{student_input}" — off-topic. '
        f"Redirect gently in ONE sentence, then re-read: {question_text}"
    )


def build_offer_exit_instruction(student_name: str) -> str:
    return (
        f"{student_name} keeps going off-topic. They might be bored. "
        f"Say warmly: 'Lagta hai aaj mood nahi hai. Koi baat nahi, "
        f"hum baad mein continue kar sakte hain. Ya ek aur try karte hain?' "
        f"No guilt, no pressure."
    )


def build_language_switch_instruction(question_text: str) -> str:
    return (
        f"Student asked for English. Switch to English and re-read: {question_text}"
    )


def build_language_reject_instruction(language: str, question_text: str) -> str:
    return (
        f"Student asked to speak in {language}. You can't yet. "
        f"Be warm: 'Sorry yaar, {language} mein abhi nahi bol sakti. "
        f"Jaldi seekh loongi! For now English ya Hindi mein chalate hain.' "
        f"Then re-read: {question_text}"
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
    if lang == "english":
        lang_instruction = "The student asked for English only."
        lang_strict = "STRICT ENGLISH ONLY. Do NOT use ANY Hindi words — no 'Chalo', no 'Dekho', no 'Haan', no 'Accha'. Pure English. Keep your warm tone."
    else:
        lang_instruction = "Natural Hindi-English mix. 'Haan', 'Accha', 'Dekho', 'Chalo', 'Koi baat nahi' come out naturally."
        lang_strict = ""

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
    text = re.sub(r'(\d+)/(\d+)', r'\1 over 2', text)

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
