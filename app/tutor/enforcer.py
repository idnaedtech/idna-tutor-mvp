"""
IDNA EdTech v7.0 — Response Enforcer
Every LLM response passes through here BEFORE reaching TTS.
7 rules. Non-negotiable. No exceptions.

This is a PURE FUNCTION module — no API calls, no side effects.
If enforcement fails after MAX_RETRIES, returns a pre-written safe fallback.
"""

import re
from dataclasses import dataclass
from typing import Optional

from app.config import MAX_RESPONSE_WORDS, MAX_RESPONSE_SENTENCES


@dataclass
class EnforceResult:
    """Result of enforcement check."""
    passed: bool
    text: str  # Cleaned text (may be modified)
    violations: list[str]  # Which rules were violated


# ─── Praise/Encouragement Words ──────────────────────────────────────────────
# These should ONLY appear when verdict is CORRECT

PRAISE_WORDS_HINDI = [
    "शाबाश", "बहुत अच्छा", "बहुत बढ़िया", "एकदम सही",
    "वाह", "बिल्कुल सही",
]

PRAISE_WORDS_HINGLISH = [
    "shabash", "shabaash", "bahut accha", "bahut achha",
    "bahut badhiya", "ekdam sahi", "bilkul sahi",
    "wah", "excellent", "perfect", "great job",
    "very good", "well done", "fantastic", "amazing",
    "brilliant", "correct", "sahi jawab",
]

ALL_PRAISE = PRAISE_WORDS_HINDI + PRAISE_WORDS_HINGLISH


# ─── Safe Fallback Responses ─────────────────────────────────────────────────
# Used when enforcer fails MAX_RETRIES times — never leave student in silence.

SAFE_FALLBACKS = {
    "GREETING": "Namaste! Aaj kya padhna hai?",
    "DISCOVERING_TOPIC": "Aaj school mein kya padha? Batao toh.",
    "CHECKING_UNDERSTANDING": "Chalo dekhte hain kitna samajh aaya. Ek sawaal puchti hoon.",
    "TEACHING": "Chalo isko ek aur tarike se samajhte hain.",
    "WAITING_ANSWER": "Aapka answer sunne mein problem aayi. Ek baar phir boliye?",
    "EVALUATING": "Mujhe check karne mein problem aayi. Ek baar phir try karo.",
    "HINT_1": "Sochiye — answer kya ho sakta hai?",
    "HINT_2": "Ek hint deti hoon — dhyan se sochiye.",
    "FULL_SOLUTION": "Koi baat nahi, chalo saath mein solve karte hain.",
    "NEXT_QUESTION": "Chalo agle question pe chalte hain.",
    "HOMEWORK_HELP": "Homework question phir se padh ke batao?",
    "COMFORT": "Koi baat nahi. Mushkil lag raha hai na? Ruk ke practice karne mein koi bura nahi hai.",
    "SESSION_COMPLETE": "Aaj ki padhai ho gayi! Bahut achha kaam kiya. Kal phir milte hain.",
}


# ─── Enforcement Rules ───────────────────────────────────────────────────────

def _check_length(text: str) -> tuple[bool, str]:
    """Rule 1: Max 55 words, max 2 sentences."""
    words = text.split()
    sentences = re.split(r'[.!?।]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    violations = []
    result = text

    if len(words) > MAX_RESPONSE_WORDS:
        # Truncate at last complete sentence within limit, or hard cut
        truncated = []
        word_count = 0
        for sentence in sentences:
            s_words = sentence.split()
            if word_count + len(s_words) <= MAX_RESPONSE_WORDS:
                truncated.append(sentence)
                word_count += len(s_words)
            else:
                break
        if truncated:
            result = '. '.join(truncated)
            if not result.endswith(('.', '!', '?', '।')):
                result += '.'
        else:
            # No sentence boundary found — hard cut at word limit
            result = ' '.join(words[:MAX_RESPONSE_WORDS])
        violations.append(f"length:{len(words)} words")

    if len(sentences) > MAX_RESPONSE_SENTENCES:
        # Keep only first 2 sentences
        result = '. '.join(sentences[:MAX_RESPONSE_SENTENCES])
        if not result.endswith(('.', '!', '?', '।')):
            result += '.'
        violations.append(f"sentences:{len(sentences)}")

    return (len(violations) == 0, result if violations else text)


def _check_no_false_praise(text: str, verdict: Optional[str]) -> tuple[bool, str]:
    """Rule 2: No praise words unless verdict is CORRECT."""
    if verdict == "CORRECT":
        return True, text  # Praise is allowed when correct

    text_lower = text.lower()
    found_praise = []

    for praise in ALL_PRAISE:
        if praise.lower() in text_lower:
            found_praise.append(praise)

    if found_praise:
        # Remove praise words
        result = text
        for praise in found_praise:
            result = re.sub(re.escape(praise), '', result, flags=re.IGNORECASE)
        result = re.sub(r'\s+', ' ', result).strip()
        # Remove leading punctuation after removal
        result = re.sub(r'^[,.\s!]+', '', result).strip()
        return False, result

    return True, text


def _check_specificity(
    text: str,
    student_answer: Optional[str],
    state: str,
) -> tuple[bool, str]:
    """Rule 3: Response must reference student's answer or specific error.
    Only applies to EVALUATING and HINT states."""
    if state not in ("EVALUATING", "HINT_1", "HINT_2"):
        return True, text

    if not student_answer:
        return True, text  # Can't check if we don't have student's answer

    # Check if response contains student's answer or a reference to it
    student_words = student_answer.lower().split()
    text_lower = text.lower()

    # Check for ANY word from student's answer (numbers, keywords)
    has_reference = False
    for word in student_words:
        if len(word) > 1 and word in text_lower:
            has_reference = True
            break

    # Also check for common reference patterns
    reference_patterns = [
        "aapne", "tumne", "you said", "aapka answer",
        "आपने", "आपका", "bola", "kaha",
    ]
    for pattern in reference_patterns:
        if pattern in text_lower:
            has_reference = True
            break

    return has_reference, text


def _check_no_teach_and_question(text: str) -> tuple[bool, str]:
    """Rule 4: Never teach AND ask a question in the same response."""
    sentences = re.split(r'[.!?।]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) < 2:
        return True, text

    has_teaching = False
    has_question = False

    for s in sentences:
        if '?' in s or '?' in text:  # Check original for question marks
            has_question = True
        # Teaching indicators
        teaching_words = [
            "matlab", "iska matlab", "for example", "jaise ki",
            "yaad rakhiye", "note karo", "formula", "rule",
        ]
        for tw in teaching_words:
            if tw in s.lower():
                has_teaching = True

    if has_teaching and has_question:
        # Keep only the teaching part, remove questions
        result_sentences = []
        for s in sentences:
            if '?' not in s:
                result_sentences.append(s)
        if result_sentences:
            return False, '. '.join(result_sentences) + '.'
        return False, text  # Can't fix, return as-is

    return True, text


def _check_language_match(text: str, language: str) -> tuple[bool, str]:
    """Rule 5: Response language must match session language."""
    # For hi-IN (Hinglish), we allow both Hindi and English
    if language.startswith("hi"):
        return True, text

    # For other languages (Telugu, Tamil, etc.) — check for Devanagari
    # which would indicate Hindi instead of the target language
    if language not in ("hi-IN", "en-IN"):
        devanagari_count = sum(1 for c in text if '\u0900' <= c <= '\u097F')
        total_alpha = sum(1 for c in text if c.isalpha())
        if total_alpha > 0 and devanagari_count / total_alpha > 0.3:
            # More than 30% Devanagari in a non-Hindi session = wrong language
            return False, text

    return True, text


def _check_tts_safety(text: str) -> tuple[bool, str]:
    """Rule 6: No characters that TTS will read literally."""
    violations = []

    # Check for raw fractions (should be converted by clean_for_tts)
    if re.search(r'\d+/\d+', text):
        violations.append("raw_fraction")

    # Check for parentheses
    if '(' in text or ')' in text or '[' in text or ']' in text:
        violations.append("brackets")

    return len(violations) == 0, text


def _check_no_repetition(
    text: str,
    previous_response: Optional[str],
) -> tuple[bool, str]:
    """Rule 7: Don't repeat the previous Didi turn verbatim."""
    if not previous_response:
        return True, text

    # Exact match
    if text.strip().lower() == previous_response.strip().lower():
        return False, text

    # High overlap (>80% of words same)
    words_now = set(text.lower().split())
    words_prev = set(previous_response.lower().split())
    if len(words_now) > 0:
        overlap = len(words_now & words_prev) / len(words_now)
        if overlap > 0.8:
            return False, text

    return True, text


# ─── Main Enforcement Function ───────────────────────────────────────────────

def enforce(
    text: str,
    state: str,
    verdict: Optional[str] = None,
    student_answer: Optional[str] = None,
    language: str = "hi-IN",
    previous_response: Optional[str] = None,
) -> EnforceResult:
    """
    Run all 7 enforcement rules on a LLM response.
    
    Args:
        text: Raw LLM response
        state: Current FSM state
        verdict: CORRECT/INCORRECT/PARTIAL (if evaluating)
        student_answer: What student said (for specificity check)
        language: Session language
        previous_response: Previous Didi response (for repetition check)
    
    Returns:
        EnforceResult with passed flag, cleaned text, and violation list
    """
    violations = []
    current_text = text

    # Rule 1: Length
    passed, current_text = _check_length(current_text)
    if not passed:
        violations.append("LENGTH")

    # Rule 2: No false praise
    passed, current_text = _check_no_false_praise(current_text, verdict)
    if not passed:
        violations.append("FALSE_PRAISE")

    # Rule 3: Specificity
    passed, _ = _check_specificity(current_text, student_answer, state)
    if not passed:
        violations.append("NO_SPECIFICITY")

    # Rule 4: No teach+question
    passed, current_text = _check_no_teach_and_question(current_text)
    if not passed:
        violations.append("TEACH_AND_QUESTION")

    # Rule 5: Language match
    passed, _ = _check_language_match(current_text, language)
    if not passed:
        violations.append("WRONG_LANGUAGE")

    # Rule 6: TTS safety
    passed, _ = _check_tts_safety(current_text)
    if not passed:
        violations.append("TTS_UNSAFE")

    # Rule 7: No repetition
    passed, _ = _check_no_repetition(current_text, previous_response)
    if not passed:
        violations.append("REPETITION")

    return EnforceResult(
        passed=len(violations) == 0,
        text=current_text,
        violations=violations,
    )


def get_safe_fallback(state: str) -> str:
    """Get a pre-written safe response for a given state.
    Used when enforcement fails after MAX_RETRIES."""
    return SAFE_FALLBACKS.get(state, "Ek minute rukiye, main soch rahi hoon.")
