"""
IDNA EdTech v7.0 — Answer Checker
Evaluates student answers against correct answers.

Math: DETERMINISTIC PYTHON. No LLM. Handles:
  - Fractions: -5/9, -1/3, 1/3, etc.
  - Decimals: 0.333, -0.5
  - Hindi spoken: "minus ek tihaayi", "do baata saat"
  - English spoken: "minus one third", "two over seven"
  - Equivalence: 2/6 = 1/3 = 0.333...
  - Sign variants: -1/3 = minus 1/3 = negative one third
  - Expression: x = 7, x=7, 7

Science/Hindi: Will use LLM (separate module, not here).
"""

import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Optional

from app.config import DECIMAL_TOLERANCE


@dataclass
class Verdict:
    """Result of answer checking."""
    correct: bool
    verdict: str  # "CORRECT", "INCORRECT", "PARTIAL"
    student_parsed: Optional[str]  # What we parsed from student's answer
    correct_display: str  # Display form of correct answer
    diagnostic: str  # Specific feedback about the error


# ─── Hindi Number Words ──────────────────────────────────────────────────────

HINDI_NUMBERS = {
    # Basic numbers 1-10
    "ek": 1, "एक": 1,
    "do": 2, "दो": 2,
    "teen": 3, "तीन": 3,
    "char": 4, "chaar": 4, "चार": 4,
    "paanch": 5, "panch": 5, "पांच": 5, "पाँच": 5,
    "chhe": 6, "cheh": 6, "chheh": 6, "छह": 6, "छे": 6,
    "saat": 7, "सात": 7,
    "aath": 8, "आठ": 8,
    "nau": 9, "नौ": 9,
    "das": 10, "दस": 10,
    # 11-20
    "gyarah": 11, "ग्यारह": 11,
    "barah": 12, "baara": 12, "बारह": 12,
    "terah": 13, "तेरह": 13,
    "chaudah": 14, "चौदह": 14,
    "pandrah": 15, "पंद्रह": 15,
    "solah": 16, "सोलह": 16,
    "satrah": 17, "सत्रह": 17,
    "atharah": 18, "athaara": 18, "अठारह": 18,
    "unnis": 19, "unees": 19, "उन्नीस": 19,
    "bees": 20, "बीस": 20,
    # 21-30
    "ekkees": 21, "इक्कीस": 21,
    "baees": 22, "बाईस": 22,
    "tees": 30, "तीस": 30,
    # 40-50
    "chawalees": 44, "chavalees": 44, "चवालीस": 44,
    "pachaas": 50, "पचास": 50,
    # 60-90
    "saath": 60, "साठ": 60,
    "sattar": 70, "सत्तर": 70,
    "assi": 80, "अस्सी": 80,
    "nabbe": 90, "नब्बे": 90,
    # 100, 1000
    "sau": 100, "सौ": 100,
    "hazaar": 1000, "हज़ार": 1000,
    # Zero
    "zero": 0, "sunya": 0, "shunya": 0, "शून्य": 0,
}

ENGLISH_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20,
}

# Fraction words
FRACTION_WORDS = {
    "half": Fraction(1, 2),
    "aadha": Fraction(1, 2), "आधा": Fraction(1, 2),
    "third": Fraction(1, 3),
    "tihaayi": Fraction(1, 3), "तिहाई": Fraction(1, 3),
    "quarter": Fraction(1, 4),
    "chauthai": Fraction(1, 4), "चौथाई": Fraction(1, 4),
    "fifth": Fraction(1, 5),
    "paanchva": Fraction(1, 5),
}

# Negative indicators
NEGATIVE_WORDS = {"minus", "negative", "neg", "-", "माइनस", "मिनस", "मैनस"}

# Hindi phonetic spellings of English words (Whisper garbling)
HINDI_PHONETIC_MAP = {
    # Numbers (Devanagari phonetic of English)
    "वन": "one", "वान": "one",
    "टू": "two", "तू": "two",
    "थ्री": "three", "थ्रे": "three",
    "फोर": "four", "फ़ोर": "four",
    "फाइव": "five", "फ़ाइव": "five",
    "सिक्स": "six",
    "सेवन": "seven", "सेव्हन": "seven",
    "एट": "eight", "ऐट": "eight",
    "नाइन": "nine", "नाईन": "nine",
    "टेन": "ten",
    # Math operators
    "बाई": "by", "बाइ": "by", "बाय": "by",
    "माइनस": "minus", "मिनस": "minus", "मैनस": "minus",
    "प्लस": "plus",
    "ओवर": "over",
    "अपॉन": "upon",
    # Common garbled patterns
    "फ़ाइव बाई नाइन": "five by nine",
    "माइनस फ़ाइव बाई नाइन": "minus five by nine",
}


def _normalize_hindi_phonetic(text: str) -> str:
    """Convert Hindi phonetic spellings of English words back to English."""
    result = text
    # Sort by length (longest first) to avoid partial replacements
    for hindi, english in sorted(HINDI_PHONETIC_MAP.items(), key=lambda x: -len(x[0])):
        result = result.replace(hindi, english)
    return result


# ─── Parsing Functions ───────────────────────────────────────────────────────

def _parse_number_word(word: str) -> Optional[int]:
    """Parse a single word as a number (Hindi or English)."""
    word = word.lower().strip()
    if word in HINDI_NUMBERS:
        return HINDI_NUMBERS[word]
    if word in ENGLISH_NUMBERS:
        return ENGLISH_NUMBERS[word]
    try:
        return int(word)
    except ValueError:
        return None


def _parse_fraction_from_text(text: str) -> Optional[Fraction]:
    """
    Try to parse a fraction from natural language.
    Handles: "2/7", "2 by 7", "2 baata 7", "2 upon 7", "2 over 7",
             "minus 2 by 7", "negative two thirds", "ek tihaayi"
    """
    text = text.lower().strip()

    # Check for negative
    is_negative = False
    for neg in NEGATIVE_WORDS:
        if text.startswith(neg):
            is_negative = True
            text = text[len(neg):].strip()
            break

    # Direct fraction notation: 2/7, -2/7
    match = re.match(r'^(-?\d+)\s*/\s*(\d+)$', text)
    if match:
        num, den = int(match.group(1)), int(match.group(2))
        if den == 0:
            return None
        frac = Fraction(num, den)
        return -frac if is_negative else frac

    # "X by Y", "X baata Y", "X upon Y", "X over Y"
    for sep in ["by", "baata", "upon", "over", "bata"]:
        parts = text.split(sep)
        if len(parts) == 2:
            num_word = parts[0].strip()
            den_word = parts[1].strip()
            num = _parse_number_word(num_word)
            den = _parse_number_word(den_word)
            if num is not None and den is not None and den != 0:
                frac = Fraction(num, den)
                return -frac if is_negative else frac

    # Named fractions: "one third", "ek tihaayi", "half"
    for word, frac_val in FRACTION_WORDS.items():
        if word in text:
            # Check for multiplier: "two thirds" = 2 * (1/3)
            before = text.split(word)[0].strip()
            multiplier = _parse_number_word(before) if before else 1
            if multiplier is None:
                multiplier = 1
            frac = frac_val * multiplier
            return -frac if is_negative else frac

    # Plain number
    num = _parse_number_word(text)
    if num is not None:
        frac = Fraction(num)
        return -frac if is_negative else frac

    # Try parsing as float
    try:
        val = float(text)
        frac = Fraction(val).limit_denominator(1000)
        return -frac if is_negative else frac
    except ValueError:
        pass

    return None


def _extract_numeric_value(text: str) -> Optional[Fraction]:
    """
    Extract the first numeric/fraction value from text,
    ignoring surrounding words.

    "the answer is 2/7" → Fraction(2, 7)
    "I think its minus 3" → Fraction(-3)
    "x equals 7" → Fraction(7)
    "माइनस फ़ाइव बाई नाइन" → Fraction(-5, 9)
    """
    text = text.lower().strip()
    # Normalize Hindi phonetic spellings to English
    text = _normalize_hindi_phonetic(text)

    # Remove common prefixes
    for prefix in ["the answer is", "answer is", "i think its", "i think",
                   "it is", "its", "it's", "mera answer hai", "mera answer",
                   "jawab hai", "jawab", "x equals", "x =", "answer", "ans"]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()

    # Try full text first
    result = _parse_fraction_from_text(text)
    if result is not None:
        return result

    # Try extracting just the numeric part
    # Look for fraction pattern
    match = re.search(r'(-?\d+)\s*/\s*(\d+)', text)
    if match:
        num, den = int(match.group(1)), int(match.group(2))
        if den != 0:
            return Fraction(num, den)

    # Look for plain number
    match = re.search(r'-?\d+\.?\d*', text)
    if match:
        try:
            val = float(match.group())
            return Fraction(val).limit_denominator(1000)
        except ValueError:
            pass

    return None


# ─── Main Answer Checker ─────────────────────────────────────────────────────

def check_math_answer(
    student_answer: str,
    correct_answer: str,
    answer_variants: Optional[list[str]] = None,
) -> Verdict:
    """
    Check a math answer using deterministic Python.
    No LLM calls. Handles all formats.
    
    Args:
        student_answer: Raw text from STT
        correct_answer: Canonical correct answer string
        answer_variants: Additional accepted answer strings
        
    Returns:
        Verdict with correct/incorrect, diagnostic
    """
    if not student_answer or not student_answer.strip():
        return Verdict(
            correct=False,
            verdict="INCORRECT",
            student_parsed=None,
            correct_display=correct_answer,
            diagnostic="Koi answer nahi mila. Ek baar phir try karo."
        )

    student_text = student_answer.strip()

    # Step 1: Exact string match against correct + variants
    all_accepted = [correct_answer] + (answer_variants or [])
    for accepted in all_accepted:
        if student_text.lower().strip() == accepted.lower().strip():
            return Verdict(
                correct=True,
                verdict="CORRECT",
                student_parsed=student_text,
                correct_display=correct_answer,
                diagnostic=""
            )

    # Step 2: Parse both as fractions and compare numerically
    student_val = _extract_numeric_value(student_text)
    correct_val = _parse_fraction_from_text(correct_answer)

    # Also try parsing all variants
    correct_vals = [correct_val]
    for variant in (answer_variants or []):
        v = _parse_fraction_from_text(variant)
        if v is not None:
            correct_vals.append(v)

    if student_val is not None:
        for cv in correct_vals:
            if cv is not None and student_val == cv:
                return Verdict(
                    correct=True,
                    verdict="CORRECT",
                    student_parsed=str(student_val),
                    correct_display=correct_answer,
                    diagnostic=""
                )

        # Step 3: Check if correct but unsimplified
        if correct_val is not None:
            # Student's value equals correct but in different form
            # Already checked above — if we're here, values don't match

            # Diagnose the error
            return _diagnose_math_error(
                student_val, correct_val, student_text, correct_answer
            )

    # Step 4: Could not parse student answer at all
    return Verdict(
        correct=False,
        verdict="INCORRECT",
        student_parsed=student_text,
        correct_display=correct_answer,
        diagnostic=f"Aapne '{student_text}' bola — main samajh nahi paayi. "
                   f"Number ya fraction mein answer dena try karo."
    )


def _diagnose_math_error(
    student_val: Fraction,
    correct_val: Fraction,
    student_text: str,
    correct_answer: str,
) -> Verdict:
    """Generate a specific diagnostic for a wrong math answer."""

    # Sign error: right magnitude, wrong sign
    if abs(student_val) == abs(correct_val):
        if student_val > 0 and correct_val < 0:
            diag = "Answer ka value sahi hai lekin sign galat hai. Minus hona chahiye tha."
        else:
            diag = "Answer ka value sahi hai lekin sign galat hai. Plus hona chahiye tha."
        return Verdict(False, "INCORRECT", str(student_val), correct_answer, diag)

    # Numerator correct, denominator wrong (or vice versa)
    if student_val.denominator == correct_val.denominator:
        diag = (
            f"Denominator sahi hai ({student_val.denominator}), "
            f"lekin numerator galat hai. Aapne {student_val.numerator} bola, "
            f"sochiye phir se."
        )
        return Verdict(False, "INCORRECT", str(student_val), correct_answer, diag)

    if student_val.numerator == correct_val.numerator:
        diag = (
            f"Numerator sahi hai ({student_val.numerator}), "
            f"lekin denominator galat hai."
        )
        return Verdict(False, "INCORRECT", str(student_val), correct_answer, diag)

    # Close but not exact (within 10%)
    if correct_val != 0:
        error_pct = abs(float(student_val - correct_val) / float(correct_val))
        if error_pct < 0.10:
            diag = f"Bahut kareeb hai! Aapne {student_val} bola. Thoda aur dhyan se check karo."
            return Verdict(False, "INCORRECT", str(student_val), correct_answer, diag)

    # Generic wrong
    diag = f"Aapne {student_val} bola. Sahi answer yeh nahi hai. Hint chahiye?"
    return Verdict(False, "INCORRECT", str(student_val), correct_answer, diag)


# ─── Science/Hindi Evaluation Placeholder ────────────────────────────────────

def check_science_answer(
    student_answer: str,
    correct_answer: str,
    key_concepts: list[str],
) -> Verdict:
    """
    Science answers need LLM evaluation.
    This is a placeholder — actual implementation calls LLM from the router.
    Returns a default "needs LLM" response.
    """
    # This will be called from the router, which will handle the LLM call
    raise NotImplementedError(
        "Science evaluation requires LLM. Call via router, not directly."
    )


def check_hindi_answer(
    student_answer: str,
    correct_answer: str,
    key_concepts: list[str],
) -> Verdict:
    """Same as science — needs LLM."""
    raise NotImplementedError(
        "Hindi evaluation requires LLM. Call via router, not directly."
    )
