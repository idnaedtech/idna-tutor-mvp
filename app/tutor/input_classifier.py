"""
IDNA EdTech v7.3.0 — Input Classifier (LLM-Based)

ARCHITECTURAL CHANGE: Replaced pattern-based classification with GPT-4o-mini LLM calls.
Fast-path for obvious single/two-word inputs saves latency and cost.

Categories (Student):
    ACK            — understood/agrees (yes, okay, samajh aaya, hmm, got it)
    IDK            — doesn't understand (nahi samjha, I don't know, confused)
    ANSWER         — giving an answer (numbers, math expressions, factual responses)
    CONCEPT_REQUEST — asks to explain something (what is this, explain, why)
    LANGUAGE_SWITCH — wants language change (speak in English, Hindi mein bolo)
    META_QUESTION   — asks about session (which chapter, more examples, real life use)
    COMFORT        — frustrated (I give up, too hard, boring)
    STOP           — wants to end (bye, stop)
    REPEAT         — didn't hear (say again, phir se bolo)
    UNCLEAR        — cannot determine

Categories (Parent):
    PROGRESS   — asking about child's progress
    INSTRUCTION — telling Didi what to focus on
    CHITCHAT   — off-topic, greetings
    GOODBYE    — wants to end
"""

import json
import re
from typing import Literal, Optional
from openai import AsyncOpenAI

# ─── Type Definitions ────────────────────────────────────────────────────────

StudentCategory = Literal[
    "ACK", "IDK", "ANSWER", "CONCEPT_REQUEST", "LANGUAGE_SWITCH",
    "META_QUESTION", "COMFORT", "STOP", "REPEAT", "UNCLEAR", "SILENCE"
]
ParentCategory = Literal["PROGRESS", "INSTRUCTION", "CHITCHAT", "GOODBYE"]

# ─── Fast-Path Sets (for single/two-word obvious inputs) ────────────────────
# These bypass the LLM call for common responses, saving ~150ms latency

FAST_ACK = {
    "haan", "ha", "yes", "ok", "okay", "hmm",
    "हां", "हाँ", "ठीक है", "अच्छा",
    "samajh gaya", "समझ गया",
}

FAST_IDK = {
    "nahi", "no", "नहीं", "pata nahi", "नहीं पता",
    "don't know", "idk", "नहीं समझा", "nahi samjha",
}

FAST_STOP = {
    "bye", "stop", "band karo", "बंद करो", "bas", "बस",
    "khatam", "खतम",
}

# ─── LLM Classifier System Prompt ────────────────────────────────────────────

CLASSIFIER_SYSTEM = """You classify student input for an Indian tutoring system.
Student: Class 8, learning {subject}. Current state: {current_state}. Topic: {current_topic}.

Categories (pick EXACTLY ONE):
- ACK: understood/agrees (yes, okay, samajh aaya, hmm, got it, theek hai, "ab samajh aaya")
- IDK: doesn't understand (nahi samjha, I don't know, confused, "समझ में नहीं आया")
- ANSWER: giving an answer (numbers, math expressions, factual responses, "49", "7 ka square")
- CONCEPT_REQUEST: asks to explain something (what is this, explain, why is it called that, "kaise hota hai")
- LANGUAGE_SWITCH: wants language change (speak in English, Hindi mein bolo, translate, "could you explain in English")
- META_QUESTION: asks about session (which chapter, more examples, real life use, "aur examples do")
- COMFORT: frustrated (I give up, too hard, boring, "bahut mushkil hai")
- STOP: wants to end (bye, stop, band karo)
- REPEAT: didn't hear (say again, phir se bolo, "sunai nahi diya")
- UNCLEAR: cannot determine

For LANGUAGE_SWITCH also return preferred_language: "english"|"hindi"|"hinglish"
For META_QUESTION also return question_type: "examples"|"chapter_info"|"relevance"|"other"
For ANSWER also return raw_answer with just the answer portion extracted

Respond ONLY with JSON: {{"category":"...","confidence":0.0-1.0,"extras":{{...}}}}"""


VALID_CATEGORIES = {
    "ACK", "IDK", "ANSWER", "CONCEPT_REQUEST", "LANGUAGE_SWITCH",
    "META_QUESTION", "COMFORT", "STOP", "REPEAT", "UNCLEAR"
}


# ─── Main Classification Function ────────────────────────────────────────────

async def classify(
    text: str,
    current_state: str = "",
    current_topic: str = "",
    subject: str = "Mathematics",
    client: Optional[AsyncOpenAI] = None,
) -> dict:
    """Classify student input. Fast-path for obvious cases, LLM for everything else.

    Args:
        text: Transcribed student speech
        current_state: Current FSM state (e.g., "TEACHING", "WAITING_ANSWER")
        current_topic: Current topic being taught (e.g., "perfect_square")
        subject: Current subject (default: Mathematics)
        client: AsyncOpenAI client for LLM calls

    Returns:
        dict with keys:
            - category: StudentCategory string
            - confidence: 0.0-1.0 float
            - extras: dict with additional info (e.g., preferred_language for LANGUAGE_SWITCH)
    """
    if not text or not text.strip():
        return {"category": "REPEAT", "confidence": 0.99, "extras": {}}

    normalized = text.strip().lower()

    # Check for silence marker
    if normalized == "[silence]":
        return {"category": "SILENCE", "confidence": 1.0, "extras": {}}

    # ─── Fast Path: single/two-word obvious matches ───────────────────────────
    # Order matters: Check negative categories (IDK, STOP) before positive (ACK)
    words = normalized.split()
    if len(words) <= 3:
        # Check IDK first (e.g., "nahi samjha" contains "samjha" but is IDK)
        if normalized in FAST_IDK or any(phrase in normalized for phrase in FAST_IDK):
            return {"category": "IDK", "confidence": 0.99, "extras": {}}

        if normalized in FAST_STOP or any(phrase in normalized for phrase in FAST_STOP):
            return {"category": "STOP", "confidence": 0.99, "extras": {}}

        if normalized in FAST_ACK or any(phrase in normalized for phrase in FAST_ACK):
            # In WAITING_ANSWER state, "haan"/"yes" could be actual answers
            if current_state == "WAITING_ANSWER":
                return {"category": "ANSWER", "confidence": 0.95, "extras": {"raw_answer": text}}
            return {"category": "ACK", "confidence": 0.99, "extras": {}}

    # ─── Fast Path: obvious numeric answers in WAITING_ANSWER state ───────────
    if current_state == "WAITING_ANSWER":
        # Contains digits → likely an answer
        if re.search(r'\d', text):
            return {"category": "ANSWER", "confidence": 0.95, "extras": {"raw_answer": text}}

    # ─── LLM Classification ───────────────────────────────────────────────────
    if client is None:
        # No client provided, fall back to UNCLEAR
        return {"category": "UNCLEAR", "confidence": 0.0, "extras": {}}

    prompt = CLASSIFIER_SYSTEM.format(
        subject=subject,
        current_state=current_state or "UNKNOWN",
        current_topic=current_topic or "general",
    )

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            temperature=0,
            max_tokens=80,
            response_format={"type": "json_object"},
        )

        result = json.loads(response.choices[0].message.content)
    except (json.JSONDecodeError, IndexError, Exception):
        return {"category": "UNCLEAR", "confidence": 0.0, "extras": {}}

    # Validate category
    category = result.get("category", "UNCLEAR")
    if category not in VALID_CATEGORIES:
        category = "UNCLEAR"

    confidence = float(result.get("confidence", 0.5))
    extras = result.get("extras", {})

    # Special handling for LANGUAGE_SWITCH
    if category == "LANGUAGE_SWITCH" and "preferred_language" not in extras:
        extras["preferred_language"] = _detect_language_preference(text)

    return {"category": category, "confidence": confidence, "extras": extras}


def _detect_language_preference(text: str) -> str:
    """Detect which language the student wants. Returns 'english', 'hindi', or 'hinglish'."""
    text_lower = text.lower().strip()
    english_indicators = ["english", "इंग्लिश", "अंग्रेजी", "angrez"]
    hindi_indicators = ["hindi", "हिंदी", "हिन्दी"]

    for indicator in english_indicators:
        if indicator in text_lower:
            return "english"
    for indicator in hindi_indicators:
        if indicator in text_lower:
            return "hindi"
    return "hinglish"


# ─── Synchronous Wrapper (for backward compatibility) ────────────────────────

def classify_student_input(
    text: str,
    current_state: str = "",
    subject: str = "math",
) -> str:
    """DEPRECATED: Synchronous fast-path only classifier for backward compatibility.

    For full classification including LLM, use the async `classify()` function.
    This function only checks fast-path and returns category string (not dict).
    """
    if not text or not text.strip():
        return "REPEAT"

    normalized = text.strip().lower()

    if normalized == "[silence]":
        return "SILENCE"

    words = normalized.split()
    if len(words) <= 3:
        # Check IDK first (e.g., "nahi samjha" contains "samjha" but is IDK)
        if normalized in FAST_IDK or any(phrase in normalized for phrase in FAST_IDK):
            return "IDK"

        if normalized in FAST_STOP or any(phrase in normalized for phrase in FAST_STOP):
            return "STOP"

        if normalized in FAST_ACK or any(phrase in normalized for phrase in FAST_ACK):
            if current_state == "WAITING_ANSWER":
                return "ANSWER"
            return "ACK"

    # For backward compatibility, check for obvious answers in WAITING_ANSWER
    if current_state == "WAITING_ANSWER":
        if re.search(r'\d', text):
            return "ANSWER"

    # Cannot classify without LLM - return UNCLEAR
    # The caller should use async classify() for full classification
    return "UNCLEAR"


def get_language_switch_preference(text: str) -> str:
    """Get the preferred language from a LANGUAGE_SWITCH input.

    Returns:
        'english', 'hindi', or 'hinglish' (default if unclear)
    """
    return _detect_language_preference(text)


# ─── Parent Classification (unchanged, pattern-based is fine for parents) ────

_PROGRESS_PHRASES = [
    "kaisa chal", "kaise chal", "how is", "progress", "kya padha",
    "aaj kya", "score", "marks", "result", "report",
]

_INSTRUCTION_PHRASES = [
    "dhyan do", "dhyan de", "focus", "zyada practice",
    "concentrate", "weak", "improve",
]

_GOODBYE_PHRASES = [
    "bye", "goodbye", "theek hai", "chalo", "bas",
    "okay thanks", "thank you",
]


def _has_match(text: str, phrases: list) -> bool:
    """Check if any phrase is a substring of the text."""
    text_lower = text.lower().strip()
    for phrase in phrases:
        if phrase in text_lower:
            return True
    return False


def classify_parent_input(text: str) -> ParentCategory:
    """Classify parent input. Pattern-based (parents have simpler needs)."""
    if not text or not text.strip():
        return "CHITCHAT"

    if _has_match(text, _GOODBYE_PHRASES):
        return "GOODBYE"

    if _has_match(text, _INSTRUCTION_PHRASES):
        return "INSTRUCTION"

    if _has_match(text, _PROGRESS_PHRASES):
        return "PROGRESS"

    return "CHITCHAT"
