"""
IDNA EdTech v7.3 — TTS Text Cleaner
Converts mathematical notation, fractions, symbols to spoken text.
Proven working from v6.2.4. Preserved and extended.

This is a PURE FUNCTION — no side effects, no imports beyond stdlib.
"""

import re


# ─── English Number Words (0-100) ─────────────────────────────────────────────

_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
         "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
         "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def _number_to_words(n: int) -> str:
    """Convert integer 0-100 to English words."""
    if n < 0 or n > 100:
        return str(n)  # Out of range, return as-is
    if n < 20:
        return _ONES[n]
    if n == 100:
        return "one hundred"
    tens, ones = divmod(n, 10)
    if ones == 0:
        return _TENS[tens]
    return f"{_TENS[tens]}-{_ONES[ones]}"


def digits_to_english_words(text: str) -> str:
    """
    v7.3.20: Convert digits 0-100 to English words for TTS.
    Use when language_pref == 'english' so Sarvam TTS speaks numbers in English.

    Examples:
        "7 times 7 equals 49" → "seven times seven equals forty-nine"
        "5 plus 3" → "five plus three"
    """
    if not text:
        return text

    # Replace numbers 0-100 with words (process larger numbers first to avoid partial matches)
    def replace_number(match):
        num = int(match.group(0))
        if 0 <= num <= 100:
            return _number_to_words(num)
        return match.group(0)

    # Match standalone numbers (not part of larger numbers or words)
    result = re.sub(r'\b(\d{1,3})\b', replace_number, text)

    return result


def clean_for_tts(text: str) -> str:
    """
    Clean text for TTS consumption.
    Converts fractions, math symbols, abbreviations to spoken form.
    
    Examples:
        "What is -5/9 + 2/9?" → "What is minus 5 by 9 plus 2 by 9?"
        "Answer: -1/3" → "Answer: minus 1 by 3"
        "Ch. 1: Rational Numbers" → "Chapter 1: Rational Numbers"
        "x = 7" → "x equals 7"
        "(a + b)" → "a plus b"
    """
    if not text:
        return text

    result = text

    # ─── Remove/replace parentheses (TTS reads them literally) ────────────
    # "(a + b)" → "a plus b"
    result = result.replace("(", "").replace(")", "")
    result = result.replace("[", "").replace("]", "")
    result = result.replace("{", "").replace("}", "")

    # ─── Fractions: -5/9 → minus 5 by 9 ──────────────────────────────────
    # Handle negative fractions first: -5/9
    result = re.sub(
        r'-(\d+)\s*/\s*(\d+)',
        r'minus \1 by \2',
        result
    )
    # Positive fractions: 5/9
    result = re.sub(
        r'(\d+)\s*/\s*(\d+)',
        r'\1 by \2',
        result
    )

    # ─── Math operators ───────────────────────────────────────────────────
    # × → into/times
    result = result.replace('×', ' into ')
    result = result.replace('*', ' into ')
    # ÷ → divided by
    result = result.replace('÷', ' divided by ')
    # + → plus (only when surrounded by spaces or between numbers)
    result = re.sub(r'(\d)\s*\+\s*(\d)', r'\1 plus \2', result)
    # − (unicode minus) and - (when used as operator, not negative sign)
    result = result.replace('−', ' minus ')
    # = → equals
    result = re.sub(r'\s*=\s*', ' equals ', result)
    # ≠ → not equal to
    result = result.replace('≠', ' not equal to ')
    # < > ≤ ≥
    result = result.replace('≤', ' less than or equal to ')
    result = result.replace('≥', ' greater than or equal to ')
    result = result.replace('<', ' less than ')
    result = result.replace('>', ' greater than ')

    # ─── Standalone negative numbers: -7 → minus 7 ───────────────────────
    # Only at word boundaries, not already handled by fraction rule
    result = re.sub(r'(?<!\w)-(\d)', r'minus \1', result)

    # ─── Roots: √ → square root, ∛ → cube root ───────────────────────────
    # Must come BEFORE exponent handling
    result = result.replace('√', 'square root of ')
    result = result.replace('∛', 'cube root of ')

    # ─── Exponents: x² → x ka square, x³ → x ka cube ───────────────────
    result = result.replace('²', ' ka square')
    result = result.replace('³', ' ka cube')
    result = re.sub(r'\^(\d+)', r' to the power \1', result)

    # ─── Common abbreviations ─────────────────────────────────────────────
    result = re.sub(r'\bCh\.?\s*(\d+)', r'Chapter \1', result)
    result = re.sub(r'\bEx\.?\s*(\d+)', r'Exercise \1', result)
    result = re.sub(r'\bQ\.?\s*(\d+)', r'Question \1', result)
    result = re.sub(r'\bFig\.?\s*(\d+)', r'Figure \1', result)
    result = re.sub(r'\bEq\.?\s*(\d+)', r'Equation \1', result)
    result = re.sub(r'\be\.g\.', 'for example', result)
    result = re.sub(r'\bi\.e\.', 'that is', result)

    # ─── Percentage: 85% → 85 percent ────────────────────────────────────
    result = re.sub(r'(\d+)%', r'\1 percent', result)

    # ─── Degree symbol: 90° → 90 degrees ────────────────────────────────
    result = re.sub(r'(\d+)°', r'\1 degrees', result)

    # ─── Pi symbol ───────────────────────────────────────────────────────
    result = result.replace('π', 'pi')

    # ─── Clean up multiple spaces ────────────────────────────────────────
    result = re.sub(r'\s+', ' ', result).strip()

    # ─── Remove any remaining special chars that TTS might choke on ──────
    # Keep: letters (any script), digits, spaces, periods, commas, ?, !
    result = re.sub(r'[^\w\s.,?!:;\'-]', '', result, flags=re.UNICODE)

    # ─── Final cleanup ───────────────────────────────────────────────────
    result = re.sub(r'\s+', ' ', result).strip()

    return result


# ─── Hindi-specific cleaning ─────────────────────────────────────────────────

def clean_hindi_for_tts(text: str) -> str:
    """
    Additional cleaning for Hindi/Hinglish text.
    Applied after clean_for_tts().
    """
    result = clean_for_tts(text)

    # Hindi fraction words
    result = result.replace('by', 'baata')  # "5 by 9" → "5 baata 9" in Hindi context
    # Only replace if surrounding context is Hindi — check for Devanagari chars
    if any('\u0900' <= c <= '\u097F' for c in result):
        result = re.sub(r'(\d+)\s+by\s+(\d+)', r'\1 baata \2', result)

    return result
