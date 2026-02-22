"""
IDNA EdTech v8.1.0 — Preprocessing Layer

Three detectors that run BEFORE the LLM call:
1. Meta-question detector — bypass LLM entirely with template response
2. Language switch detector — update session.language_pref
3. Confusion detector — increment session.confusion_count

Processing order: meta-question → language switch → confusion → LLM
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger("idna.preprocessing")


@dataclass
class PreprocessResult:
    """Result of preprocessing a student message."""
    bypass_llm: bool = False           # If True, use template_response instead of LLM
    template_response: str = ""         # Direct response (only if bypass_llm=True)
    language_switched: bool = False     # If True, language_pref was updated
    new_language: Optional[str] = None  # The new language if switched
    confusion_detected: bool = False    # If True, increment confusion_count
    meta_question_type: Optional[str] = None  # "chapter", "topic", "subject", etc.


# ─── Language Switch Detector ─────────────────────────────────────────────────

LANGUAGE_SWITCH_PATTERNS_ENGLISH = [
    r"speak\s*(in)?\s*english",
    r"talk\s*(in)?\s*english",
    r"english\s*please",
    r"please\s*(speak|talk)\s*(in)?\s*english",
    r"can\s*you\s*(speak|talk)\s*(in)?\s*english",
    r"i\s*don'?t\s*understand\s*hindi",
    r"not\s*understanding\s*hindi",
    r"in\s*english\s*please",
    r"switch\s*to\s*english",
    r"use\s*english",
    r"only\s*english",
    r"respond\s*in\s*english",
]

LANGUAGE_SWITCH_PATTERNS_HINDI = [
    r"hindi\s*(mein|me|mai)\s*(bolo|boliye|baat\s*karo)",
    r"speak\s*(in)?\s*hindi",
    r"talk\s*(in)?\s*hindi",
    r"hindi\s*please",
    r"switch\s*to\s*hindi",
    r"hinglish\s*(mein|me|mai)",
]

_ENGLISH_SWITCH_RE = re.compile(
    "|".join(LANGUAGE_SWITCH_PATTERNS_ENGLISH),
    re.IGNORECASE
)
_HINDI_SWITCH_RE = re.compile(
    "|".join(LANGUAGE_SWITCH_PATTERNS_HINDI),
    re.IGNORECASE
)


def detect_language_switch(text: str) -> Optional[str]:
    """
    Detect if student is requesting a language switch.

    Returns:
        "english", "hindi", or None if no switch requested
    """
    text_lower = text.lower().strip()

    # Check for English switch request
    if _ENGLISH_SWITCH_RE.search(text_lower):
        logger.info(f"Language switch detected: → english (text: '{text[:50]}')")
        return "english"

    # Check for Hindi switch request
    if _HINDI_SWITCH_RE.search(text_lower):
        logger.info(f"Language switch detected: → hindi (text: '{text[:50]}')")
        return "hindi"

    return None


# ─── Confusion Detector ───────────────────────────────────────────────────────

CONFUSION_PATTERNS = [
    # English patterns
    r"(i\s+)?don'?t\s+understand",
    r"(i\s+)?do\s+not\s+understand",
    r"not\s+understand(ing)?",
    r"(i\s+)?don'?t\s+get\s+(it|this)",
    r"(i\s+)?can'?t\s+understand",
    r"what\s+do\s+you\s+mean",
    r"can\s+you\s+explain\s+again",
    r"explain\s+again",
    r"please\s+explain",
    r"say\s+(that\s+)?again",
    r"repeat\s+(that\s+)?please",
    r"huh\??",
    r"what\??$",  # Just "what?" at end
    r"i'?m\s+(so\s+)?confused",
    r"confusing",
    r"(still\s+)?not\s+clear",
    r"doesn'?t\s+make\s+sense",

    # Hindi/Hinglish patterns
    r"(nahi|nai)\s+samajh",
    r"(nahi|nai)\s+samjha",
    r"samajh\s+(nahi|nai|me nahi)",
    r"samjha\s+(nahi|nai)",
    r"(nahi|nai)\s+aaya",
    r"समझ\s+नहीं",
    r"नहीं\s+समझा",
    r"नहीं\s+आया",
    r"kya\s+matlab",
    r"क्या\s+मतलब",
    r"phir\s+se\s+(bolo|batao|samjhao)",
    r"dobara\s+(bolo|batao|samjhao)",
    r"ek\s+baar\s+aur",
]

_CONFUSION_RE = re.compile("|".join(CONFUSION_PATTERNS), re.IGNORECASE)


def detect_confusion(text: str) -> bool:
    """
    Detect if student is expressing confusion or asking for re-explanation.

    Returns:
        True if confusion detected, False otherwise
    """
    text_lower = text.lower().strip()

    if _CONFUSION_RE.search(text_lower):
        logger.info(f"Confusion detected (text: '{text[:50]}')")
        return True

    return False


# ─── Meta-Question Detector ───────────────────────────────────────────────────

META_QUESTION_PATTERNS = {
    "chapter": [
        r"(what|which)\s+chapter",
        r"(what|which)\s+chapter\s+(are\s+we|is\s+this)",
        r"kaunsa\s+chapter",
        r"kaun\s+sa\s+chapter",
        r"कौनसा\s+chapter",
        r"kis\s+chapter",
    ],
    "topic": [
        r"(what|which)\s+topic",
        r"what\s+are\s+we\s+(learning|studying|doing)",
        r"what\s+(is|are)\s+we\s+on",
        r"what'?s\s+the\s+topic",
        r"kya\s+padh\s+rahe",
        r"क्या\s+पढ़\s+रहे",
        r"current\s+topic",
    ],
    "subject": [
        r"(what|which)\s+subject",
        r"kaunsa\s+subject",
        r"kaun\s+sa\s+subject",
    ],
    "progress": [
        r"how\s+long\s+have\s+we\s+been",
        r"what\s+did\s+we\s+cover",
        r"what\s+have\s+we\s+(done|covered|learned)",
        r"kitna\s+ho\s+gaya",
        r"कितना\s+हो\s+गया",
    ],
}

_META_PATTERNS_COMPILED = {
    category: re.compile("|".join(patterns), re.IGNORECASE)
    for category, patterns in META_QUESTION_PATTERNS.items()
}


def detect_meta_question(text: str) -> Optional[str]:
    """
    Detect if student is asking a meta-question about the session.

    Returns:
        Meta-question type ("chapter", "topic", "subject", "progress") or None
    """
    text_lower = text.lower().strip()

    for category, pattern in _META_PATTERNS_COMPILED.items():
        if pattern.search(text_lower):
            logger.info(f"Meta-question detected: {category} (text: '{text[:50]}')")
            return category

    return None


def build_meta_response(
    meta_type: str,
    chapter: str,
    chapter_name: str,
    subject: str,
    current_skill: str,
    language_pref: str,
) -> str:
    """
    Build a direct template response for a meta-question.
    Respects the student's language preference.
    """
    use_english = language_pref == "english"

    if meta_type == "chapter":
        if use_english:
            return f"We are learning {chapter_name}."
        else:
            return f"Hum {chapter_name} padh rahe hain."

    elif meta_type == "topic":
        skill_display = current_skill.replace("_", " ").title() if current_skill else ""
        if use_english:
            if skill_display:
                return f"We are currently on {skill_display} in {chapter_name}."
            return f"We are studying {chapter_name}."
        else:
            if skill_display:
                return f"Abhi hum {skill_display} padh rahe hain, {chapter_name} mein."
            return f"Hum {chapter_name} padh rahe hain."

    elif meta_type == "subject":
        if use_english:
            return f"We are studying {subject.title()}."
        else:
            return f"Hum {subject.title()} padh rahe hain."

    elif meta_type == "progress":
        if use_english:
            return f"We've been working on {chapter_name}. You're doing great!"
        else:
            return f"Hum {chapter_name} pe kaam kar rahe hain. Bahut accha chal raha hai!"

    # Default fallback
    if use_english:
        return f"We are learning {chapter_name}."
    return f"Hum {chapter_name} padh rahe hain."


# ─── Main Preprocessing Function ──────────────────────────────────────────────

def preprocess_student_message(
    text: str,
    chapter: str = "",
    chapter_name: str = "",
    subject: str = "math",
    current_skill: str = "",
    language_pref: str = "hinglish",
) -> PreprocessResult:
    """
    Run all preprocessing checks on student message.

    Processing order: meta-question → language switch → confusion

    Args:
        text: Student's transcribed message
        chapter: Chapter key (e.g., "ch1_square_and_cube")
        chapter_name: Human-readable chapter name
        subject: Current subject
        current_skill: Current skill being taught
        language_pref: Current language preference

    Returns:
        PreprocessResult with detection results
    """
    result = PreprocessResult()

    # 1. Check for meta-question FIRST (bypass LLM if matched)
    meta_type = detect_meta_question(text)
    if meta_type:
        result.bypass_llm = True
        result.meta_question_type = meta_type
        result.template_response = build_meta_response(
            meta_type=meta_type,
            chapter=chapter,
            chapter_name=chapter_name,
            subject=subject,
            current_skill=current_skill,
            language_pref=language_pref,
        )
        logger.info(f"Bypassing LLM for meta-question: {meta_type}")
        return result  # Early return — no need to check other patterns

    # 2. Check for language switch
    new_language = detect_language_switch(text)
    if new_language:
        result.language_switched = True
        result.new_language = new_language

    # 3. Check for confusion
    if detect_confusion(text):
        result.confusion_detected = True

    return result
