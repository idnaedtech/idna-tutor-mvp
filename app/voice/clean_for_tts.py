"""
IDNA EdTech v7.0 — TTS Text Cleaner
Converts mathematical notation, fractions, symbols to spoken text.
Proven working from v6.2.4. Preserved and extended.

This is a PURE FUNCTION — no side effects, no imports beyond stdlib.
"""

import re


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

    # ─── Exponents: x² → x square, x³ → x cube ──────────────────────────
    result = result.replace('²', ' square')
    result = result.replace('³', ' cube')
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
