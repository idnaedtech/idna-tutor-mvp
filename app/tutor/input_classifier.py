"""
IDNA EdTech v7.3.0 — Input Classifier (LLM-Based)

ARCHITECTURAL CHANGE: Replaced pattern-based classification with GPT-5-mini LLM calls.
Fast-path for obvious single/two-word inputs saves latency and cost.

P0 FIX (2026-02-28):
  1. Classifier model: gpt-4o-mini → gpt-5-mini (better Hindi/Devanagari understanding)
  2. FAST_ACK expanded: added "जी", "शुरू करते हैं", "start", "ready", "chalo", etc.
  3. FAST_IDK expanded: added "samajh nahi aaya", "I don't get it", "huh", "what", etc.
  4. Fast-path word limit: 3 → 5 (catches "जी शुरू करते हैं" = 4 words)
  5. Both async classify() and sync classify_student_input() updated consistently.
  6. Added _normalize() to strip punctuation (।,.!?) from STT output before matching.

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

# ─── Punctuation Normalization ───────────────────────────────────────────────
# P0 FIX: STT adds punctuation (Hindi danda ।, commas, periods) that breaks
# fast-path matching. Strip before comparison.
_PUNCT_RE = re.compile(r'[.,!?;:।॰\-\'"()]+')


def _normalize(text: str) -> str:
    """Normalize text for fast-path matching: lowercase, strip punctuation, collapse spaces."""
    t = text.strip().lower()
    t = _PUNCT_RE.sub(' ', t)       # replace punctuation with space
    t = re.sub(r'\s+', ' ', t)      # collapse multiple spaces
    return t.strip()


# ─── Type Definitions ────────────────────────────────────────────────────────

StudentCategory = Literal[
    "ACK", "IDK", "ANSWER", "CONCEPT_REQUEST", "LANGUAGE_SWITCH",
    "META_QUESTION", "COMFORT", "STOP", "REPEAT", "UNCLEAR", "SILENCE"
]
ParentCategory = Literal["PROGRESS", "INSTRUCTION", "CHITCHAT", "GOODBYE"]

# ─── Fast-Path Sets ─────────────────────────────────────────────────────────
# These bypass the LLM call for common responses, saving ~150ms latency
# P0 FIX: Expanded with real student phrases from live test transcripts

FAST_ACK = {
    # English - single words
    "haan", "ha", "yes", "ok", "okay", "hmm", "yep", "yeah", "sure",
    "ready", "start", "alright",
    # English - short phrases
    "let's start", "lets start", "please start", "yes please",
    "yes please start", "i'm ready", "im ready", "lets go", "let's go",
    "go ahead", "yes start", "start please",
    # Hindi - Devanagari
    "हां", "हाँ", "ठीक है", "अच्छा", "जी", "जी हां", "जी हाँ",
    "समझ गया", "समझ गयी", "समझ आ गया", "समझ आ गयी",
    "शुरू करो", "शुरू करें", "शुरू करते हैं", "शुरू कीजिए",
    "चलो", "चलो शुरू करते हैं", "चलिए", "चलो शुरू करो",
    "हां शुरू करो", "हां शुरू करते हैं",
    "जी शुरू करते हैं", "जी शुरू करो", "जी हां शुरू करते हैं",
    "जी शुरू कीजिए",
    # Hindi - Romanized
    "samajh gaya", "samajh gayi", "samajh aa gaya",
    "theek hai", "thik hai", "accha", "acha",
    "shuru karo", "shuru karein", "shuru karte hain", "shuru kijiye",
    "chalo", "chaliye", "chalo shuru karte hain", "chalo shuru karo",
    "ji", "ji haan", "ji ha",
    "haan shuru karo", "haan shuru karte hain",
    "ji shuru karte hain", "ji shuru karo", "ji shuru kijiye",
}

FAST_IDK = {
    # English
    "nahi", "no", "don't know", "idk", "don't get it",
    "i don't understand", "not understanding", "don't understand",
    "what", "huh", "what do you mean",
    # Hindi - Devanagari
    "नहीं", "नहीं पता", "नहीं समझा", "नहीं समझी",
    "समझ नहीं आया", "समझ नहीं आयी", "समझ में नहीं आया",
    "पता नहीं", "क्या",
    # Hindi - Romanized
    "nahi samjha", "nahi samjhi", "samajh nahi aaya", "samajh nahi aya",
    "pata nahi", "nahi aaya", "nahi aya",
    "samajh mein nahi aaya",
}

FAST_STOP = {
    "bye", "stop", "band karo", "बंद करो", "bas", "बस",
    "khatam", "खतम", "goodbye", "bye bye",
}

# P1 Fix: Homework-related phrases → map to CONCEPT_REQUEST (don't add new category)
FAST_HOMEWORK = {
    "homework", "होमवर्क", "home work", "गृहकार्य",
    "assignment", "classwork", "class work",
}

# ─── Fast-path word limit ────────────────────────────────────────────────────
# P0 FIX: Increased from 3 to 5 to catch phrases like "जी शुरू करते हैं" (4 words)
FAST_PATH_MAX_WORDS = 5

# ─── LLM Classifier System Prompt ────────────────────────────────────────────

CLASSIFIER_SYSTEM = """You classify student input for an Indian tutoring system.
Student: Class 8, learning {subject}. Current state: {current_state}. Topic: {current_topic}.

Categories (pick EXACTLY ONE):
- ACK: understood/agrees (yes, okay, samajh aaya, hmm, got it, theek hai, "ab samajh aaya", "जी", "शुरू करते हैं", "chalo", "ready", "let's start")
- IDK: doesn't understand (nahi samjha, I don't know, confused, "समझ में नहीं आया", "huh", "what")
- ANSWER: giving an answer (numbers, math expressions, factual responses, "49", "7 ka square")
- CONCEPT_REQUEST: asks to explain something (what is this, explain, why is it called that, "kaise hota hai")
- LANGUAGE_SWITCH: wants language change (speak in English, Hindi mein bolo, translate, "could you explain in English")
- META_QUESTION: asks about session (which chapter, more examples, real life use, "aur examples do", "kya padh rahe hain", "कौन सा चैप्टर")
- COMFORT: frustrated (I give up, too hard, boring, "bahut mushkil hai")
- STOP: wants to end (bye, stop, band karo)
- REPEAT: didn't hear (say again, phir se bolo, "sunai nahi diya")
- UNCLEAR: cannot determine

IMPORTANT: Hindi/Devanagari input is common. "जी शुरू करते हैं" = ACK. "समझ नहीं आया" = IDK. "कौन सा चैप्टर" = META_QUESTION. Classify these correctly.

For LANGUAGE_SWITCH also return preferred_language: "english"|"hindi"|"hinglish"
For META_QUESTION also return question_type: "examples"|"chapter_info"|"relevance"|"other"
For ANSWER also return raw_answer with just the answer portion extracted

Respond ONLY with JSON: {{"category":"...","confidence":0.0-1.0,"extras":{{...}}}}"""


VALID_CATEGORIES = {
    "ACK", "IDK", "ANSWER", "CONCEPT_REQUEST", "LANGUAGE_SWITCH",
    "META_QUESTION", "COMFORT", "STOP", "REPEAT", "UNCLEAR"
}

# ─── Classifier model ────────────────────────────────────────────────────────
# P0 FIX: gpt-4o-mini → gpt-5-mini for better Hindi/Devanagari classification
CLASSIFIER_MODEL = "gpt-5-mini"


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

    normalized = _normalize(text)

    # Check for silence marker
    if normalized == "[silence]" or text.strip().lower() == "[silence]":
        return {"category": "SILENCE", "confidence": 1.0, "extras": {}}

    # ─── Fast Path: obvious matches (up to 5 words) ──────────────────────────
    # P0 FIX: Expanded from 3 to 5 words to catch Hindi phrases
    # Order matters: Check negative categories (IDK, STOP) before positive (ACK)
    words = normalized.split()

    # ─── Fast Path: homework-related → CONCEPT_REQUEST (P1 fix) ───────────────
    # MUST check before ACK because "homework question hai" contains "ha" which matches FAST_ACK
    if any(hw_word in normalized for hw_word in FAST_HOMEWORK):
        return {"category": "CONCEPT_REQUEST", "confidence": 0.90, "extras": {"is_homework": True}}

    if len(words) <= FAST_PATH_MAX_WORDS:
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
            model=CLASSIFIER_MODEL,
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

    normalized = _normalize(text)

    if normalized == "[silence]" or text.strip().lower() == "[silence]":
        return "SILENCE"

    # P0 FIX: Same expanded fast-path as async classify()
    words = normalized.split()
    if len(words) <= FAST_PATH_MAX_WORDS:
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
