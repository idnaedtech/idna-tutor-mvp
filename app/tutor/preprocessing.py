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
    emotional_distress: bool = False    # P0 FIX: If True, student is sad/tired/upset


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
    r"samajh\s+(nahi|nai|me nahi|mein nahi)",
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
    # Bug C fix: Additional confusion patterns
    r"समझ\s+में\s+नहीं\s+आया",  # samajh mein nahi aaya (Devanagari)
    r"कुछ\s+समझ\s+में\s+नहीं",  # kuch samajh mein nahi
    r"मुझे.*समझ.*नहीं",  # mujhe samajh nahi
    r"samajh\s+mein\s+nahi",  # romanized
    r"kuch\s+samajh\s+nahi",  # romanized
    r"can'?t\s+understand",
    r"don'?t\s+understand",
    r"didn'?t\s+understand",
    r"not\s+understand",
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


# ─── Emotional Distress Detector ─────────────────────────────────────────────

EMOTIONAL_DISTRESS_PATTERNS = [
    # Hindi - Devanagari
    r"उदास",                    # udaas (sad)
    r"दुखी",                    # dukhi (sorrowful)
    r"रोना\s+आ\s+रहा",         # rona aa raha (feel like crying)
    r"तबीयत\s+ठीक\s+नहीं",     # tabiyat theek nahi (not feeling well)
    r"मन\s+नहीं\s+है",         # man nahi hai (don't feel like it)
    r"बहुत\s+थक",              # bahut thak (very tired)
    r"बोर\s+हो",               # bor ho (bored)
    # Hindi - Romanized
    r"udaas",
    r"dukhi",
    r"tabiyat\s+theek\s+nahi",
    r"man\s+nahi",
    r"bahut\s+thak",
    r"mood\s+kharab",
    # English
    r"(i'?m\s+)?(very\s+)?sad",
    r"not\s+feeling\s+well",
    r"don'?t\s+feel\s+like\s+(studying|learning)",
    r"(i'?m\s+)?(very\s+)?tired",
    r"had\s+a\s+bad\s+day",
    r"upset",
]

_EMOTIONAL_RE = re.compile("|".join(EMOTIONAL_DISTRESS_PATTERNS), re.IGNORECASE)


def detect_emotional_distress(text: str) -> bool:
    """Detect if student is expressing sadness, tiredness, or emotional distress."""
    text_lower = text.lower().strip()
    if _EMOTIONAL_RE.search(text_lower):
        logger.info(f"Emotional distress detected (text: '{text[:50]}')")
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
        # P0 FIX: Devanagari patterns from Sarvam STT output
        r"कौन\s*सा\s*चैप्टर",        # kaun sa chapter (full Devanagari)
        r"कौनसा\s*चैप्टर",           # kaunsa chapter (full Devanagari)
        r"कोनसा\s*चैप्टर",           # konsa chapter (colloquial Devanagari)
        r"चैप्टर\s*(क्या|कौन)",       # chapter kya/kaun (reversed order)
        # P0 Smoke Test Fix: Additional romanized Hindi patterns
        r"konsa\s+chapter",           # konsa chapter (colloquial romanized)
        r"kaun\s*sa\s+chapter\s+padh",  # kaun sa chapter padh rahe hain
        r"कौन\s*सा\s+chapter",       # mixed Devanagari + English
        r"chapter\s+(kya|kaun|कौन|क्या)",  # chapter kya/kaun hai
    ],
    "topic": [
        r"(what|which)\s+topic",
        r"what\s+are\s+we\s+(learning|studying|doing|reading)",
        r"what\s+(is|are)\s+we\s+on",
        r"what'?s\s+the\s+topic",
        r"kya\s+padh\s+rahe",
        r"क्या\s+पढ़\s+रहे",
        r"current\s+topic",
        # P0 FIX: Additional Devanagari patterns
        r"क्या\s+पढ़\s+रहे\s+हैं",    # kya padh rahe hain (full phrase)
        r"कौन\s*सा\s+topic",          # kaun sa topic (Devanagari + English)
        r"कौनसा\s+topic",             # kaunsa topic
        # P0 Smoke Test Fix: Additional patterns
        r"what\s+(are\s+)?we\s+(reading|studying)",  # what are we reading/studying
        r"kya\s+padh\s+rahe\s+hain",  # kya padh rahe hain (romanized)
        r"konsa\s+topic",              # konsa topic (colloquial)
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

    # DEBUG: Log all pattern matching attempts
    logger.info(f"META-CHECK: input=[{text}], text_lower=[{text_lower}]")

    for category, pattern in _META_PATTERNS_COMPILED.items():
        match = pattern.search(text_lower)
        logger.info(f"META-CHECK: category={category}, pattern_matched={bool(match)}")
        if match:
            logger.info(f"META-CHECK: MATCH FOUND! category={category}, matched_text=[{match.group()}]")
            return category

    logger.info(f"META-CHECK: NO MATCH for input=[{text[:50]}]")
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
    v10.1: Added Telugu support.
    """
    use_english = language_pref == "english"
    use_telugu = language_pref in ("telugu", "te-IN")

    if meta_type == "chapter":
        if use_english:
            return f"We are learning {chapter_name}."
        elif use_telugu:
            return f"Manamu {chapter_name} chaduvutunnamu."
        else:
            return f"Hum {chapter_name} padh rahe hain."

    elif meta_type == "topic":
        skill_display = current_skill.replace("_", " ").title() if current_skill else ""
        if use_english:
            if skill_display:
                return f"We are currently on {skill_display} in {chapter_name}."
            return f"We are studying {chapter_name}."
        elif use_telugu:
            if skill_display:
                return f"Ippudu manamu {skill_display} chaduvutunnamu, {chapter_name} lo."
            return f"Manamu {chapter_name} chaduvutunnamu."
        else:
            if skill_display:
                return f"Abhi hum {skill_display} padh rahe hain, {chapter_name} mein."
            return f"Hum {chapter_name} padh rahe hain."

    elif meta_type == "subject":
        if use_english:
            return f"We are studying {subject.title()}."
        elif use_telugu:
            return f"Manamu {subject.title()} chaduvutunnamu."
        else:
            return f"Hum {subject.title()} padh rahe hain."

    elif meta_type == "progress":
        if use_english:
            return f"We've been working on {chapter_name}. You're doing great!"
        elif use_telugu:
            return f"Manamu {chapter_name} practice chestunnamu. Chala bagundi!"
        else:
            return f"Hum {chapter_name} pe kaam kar rahe hain. Bahut accha chal raha hai!"

    # Default fallback
    if use_english:
        return f"We are learning {chapter_name}."
    elif use_telugu:
        return f"Manamu {chapter_name} chaduvutunnamu."
    return f"Hum {chapter_name} padh rahe hain."


# ─── Language Auto-Detection ─────────────────────────────────────────────────

# Common Hindi words in Roman script (for detecting Hinglish vs pure English)
_HINDI_ROMAN_WORDS = {
    'haan', 'nahi', 'kya', 'kaise', 'kyun', 'samajh', 'padh',
    'bolo', 'batao', 'acha', 'theek', 'chalo', 'karein',
    'seekh', 'shuru', 'aage', 'peeche', 'mujhe', 'humko',
    'aap', 'tum', 'yeh', 'woh', 'hai', 'hain', 'tha',
    'mein', 'ka', 'ki', 'ke', 'ko', 'se', 'par', 'ne',
    'aur', 'lekin', 'toh', 'bhi', 'abhi', 'phir',
    'ji', 'didi', 'namaste',
}


def detect_input_language(text: str) -> str:
    """Detect whether student input is primarily English, Hindi, Telugu, or Hinglish.

    Returns: 'english', 'hindi', 'telugu', or 'hinglish'
    """
    text = text.strip()
    if not text:
        return 'hinglish'

    # v10.1: Telugu detection (Unicode range 0C00-0C7F)
    telugu_chars = len(re.findall(r'[\u0C00-\u0C7F]', text))
    devanagari_chars = len(re.findall(r'[\u0900-\u097F]', text))
    total_alpha = len(re.findall(r'[a-zA-Z\u0900-\u097F\u0C00-\u0C7F]', text))

    if total_alpha == 0:
        return 'hinglish'  # just numbers or punctuation

    # Check Telugu first (higher priority for Telugu pilot)
    telugu_ratio = telugu_chars / total_alpha
    if telugu_ratio > 0.3:
        return 'telugu'

    devanagari_ratio = devanagari_chars / total_alpha

    # Mostly Devanagari → Hindi
    if devanagari_ratio > 0.5:
        return 'hindi'

    # No Devanagari at all → check for common Hindi words in Roman script
    if devanagari_ratio == 0 and telugu_ratio == 0:
        words = set(text.lower().split())
        hindi_word_count = len(words.intersection(_HINDI_ROMAN_WORDS))

        if hindi_word_count == 0:
            return 'english'

        hindi_word_ratio = hindi_word_count / len(words) if words else 0
        if hindi_word_ratio < 0.3:
            return 'english'  # Mostly English with occasional Hindi
        return 'hinglish'

    # Mix of Devanagari and Latin → Hinglish
    return 'hinglish'


def check_language_auto_switch(
    detected_language: str,
    current_session_language: str,
    consecutive_english_count: int,
) -> tuple:
    """Check if we should auto-switch language based on student input.

    Returns: (should_switch, new_language, updated_count)

    Rules:
    - 2+ consecutive English messages while session is hindi/hinglish → auto-switch
    - Hindi/Hinglish message → reset English counter
    - Already matching → no action
    """
    # Student speaking in the same language as session → no action
    if detected_language == current_session_language:
        return False, current_session_language, 0

    # Student speaking English but session is Hindi/Hinglish
    if detected_language == 'english' and current_session_language in ('hindi', 'hinglish'):
        new_count = consecutive_english_count + 1
        if new_count >= 2:
            return True, 'english', new_count
        else:
            return False, current_session_language, new_count

    # Any other case (e.g. Hindi while session is English) → reset counter
    return False, current_session_language, 0


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

    # 4. P0 FIX: Check for emotional distress
    if detect_emotional_distress(text):
        result.emotional_distress = True

    return result
