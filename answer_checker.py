"""
IDNA Tutor - Deterministic Answer Checker (v4.1)
=================================================
Runs BEFORE LLM tool selection.
- True  → definitely correct → force praise_and_continue
- None  → partial answer → force guide_partial_answer
- False → wrong → pass to LLM for hint/scaffold selection

This fixes the core bug: gpt-4o-mini unreliably judging correct answers
when system prompt context is long.
"""

import re
from typing import Optional


def normalize_answer(raw: str) -> str:
    """
    Normalize student input for comparison.
    Handles spoken math: "minus 1 by 7" → "-1/7"
    """
    text = raw.strip().lower()

    # Spoken → symbolic mappings
    text = text.replace("minus ", "-")
    text = text.replace("negative ", "-")
    text = text.replace(" by ", "/")
    text = text.replace(" over ", "/")
    text = text.replace(" upon ", "/")
    text = text.replace(" divided by ", "/")
    text = text.replace(" plus ", "+")
    text = text.replace(" into ", "*")
    text = text.replace(" times ", "*")

    # Compound fractions FIRST (before single words)
    text = re.sub(r'\bone\s+half\b', '1/2', text)
    text = re.sub(r'\btwo\s+thirds?\b', '2/3', text)
    text = re.sub(r'\bthree\s+quarters?\b', '3/4', text)
    text = re.sub(r'\bone\s+third\b', '1/3', text)
    text = re.sub(r'\bone\s+quarter\b', '1/4', text)
    text = re.sub(r'\btwo\s+quarters?\b', '1/2', text)

    # Single fractional words
    text = re.sub(r'\bhalf\b', '1/2', text)
    text = re.sub(r'\bquarter\b', '1/4', text)
    text = re.sub(r'\bthird\b', '1/3', text)

    # Word numbers → digits
    word_nums = {
        "zero": "0", "one": "1", "two": "2", "three": "3",
        "four": "4", "five": "5", "six": "6", "seven": "7",
        "eight": "8", "nine": "9", "ten": "10",
        "eleven": "11", "twelve": "12", "thirteen": "13",
        "fourteen": "14", "fifteen": "15", "sixteen": "16",
        "seventeen": "17", "eighteen": "18", "nineteen": "19",
        "twenty": "20", "thirty": "30", "forty": "40", "fifty": "50",
        "hundred": "100",
    }
    for word, digit in word_nums.items():
        text = re.sub(rf'\b{word}\b', digit, text)

    # Remove "equals", "is", "answer is" prefix
    text = re.sub(r'^(the\s+)?(answer\s+)?(is\s+|equals?\s+)', '', text)

    # Remove "x =" or "x=" prefix (for equation answers)
    text = re.sub(r'^[a-z]\s*=\s*', '', text)

    # Remove spaces around math operators
    text = re.sub(r'\s*([/\-+*])\s*', r'\1', text)

    # Remove trailing period, comma, extra spaces
    text = text.strip().rstrip('.').rstrip(',').strip()

    return text


def _numeric_value(expr: str) -> Optional[float]:
    """Safely evaluate a simple math expression to a number."""
    try:
        # Only allow digits, operators, decimal points, parens
        if re.match(r'^[\d\.\-\+\*/\(\)\s]+$', expr):
            val = eval(expr)
            return float(val)
    except:
        pass
    return None


def normalize_answer_key(key: str) -> list[str]:
    """
    Generate all acceptable normalized forms of the answer key.
    """
    variants = set()
    key = str(key).strip()

    # Original (lowered)
    variants.add(key.lower())

    # Normalized
    norm = normalize_answer(key)
    variants.add(norm)

    # If fraction, add decimal
    if '/' in norm:
        val = _numeric_value(norm)
        if val is not None:
            variants.add(str(round(val, 6)))
            if val == int(val):
                variants.add(str(int(val)))

    return list(variants)


def extract_math_from_sentence(text: str) -> list[str]:
    """
    Extract potential math answers from a longer sentence.
    e.g., "7. The answer is minus 1 by 7" → ["minus 1 by 7", "7"]
    """
    candidates = []
    text_lower = text.lower().strip()

    # Pattern 1: After "answer is", "is", "equals"
    after_match = re.search(r'(?:the\s+)?(?:answer\s+)?(?:is|equals?)\s+(.+?)\.?$', text_lower)
    if after_match:
        candidates.append(after_match.group(1).strip())

    # Pattern 2: Fraction patterns (minus X by/over Y)
    frac_match = re.search(r'((?:minus\s+|negative\s+)?-?\d+\s*(?:by|over|upon)\s*\d+)', text_lower)
    if frac_match:
        candidates.append(frac_match.group(1).strip())

    # Pattern 3: Simple "minus X" at end
    minus_match = re.search(r'((?:minus|negative)\s+\d+)\s*\.?$', text_lower)
    if minus_match:
        candidates.append(minus_match.group(1).strip())

    # Pattern 4: Numeric fraction X/Y
    slash_match = re.search(r'(-?\d+\s*/\s*\d+)', text_lower)
    if slash_match:
        candidates.append(slash_match.group(1).strip())

    return candidates


def check_answer(
    student_input: str,
    answer_key: str,
    accept_also: list[str] = None
) -> Optional[bool]:
    """
    Deterministic answer check.

    Returns:
        True  → definitely correct (force praise_and_continue)
        None  → partial / ambiguous (force guide_partial_answer)
        False → definitely wrong (send to LLM for hint selection)
    """
    if not student_input or not student_input.strip():
        return False

    student_norm = normalize_answer(student_input)

    # Also try extracting math from longer sentences
    extracted_candidates = extract_math_from_sentence(student_input)

    # Build all acceptable variants
    key_variants = normalize_answer_key(answer_key)

    # Add accept_also variants from question bank
    if accept_also:
        for av in accept_also:
            key_variants.extend(normalize_answer_key(av))

    # --- Check 1: Exact string match (after normalization) ---
    if student_norm in key_variants:
        return True

    # --- Check 1b: Try extracted math from longer sentences ---
    for candidate in extracted_candidates:
        cand_norm = normalize_answer(candidate)
        if cand_norm in key_variants:
            return True
        # Also check numeric equivalence for extracted candidate
        cand_val = _numeric_value(cand_norm)
        if cand_val is not None:
            for variant in key_variants:
                key_val = _numeric_value(variant)
                if key_val is not None and abs(cand_val - key_val) < 0.0001:
                    return True

    # --- Check 2: Numeric equivalence ---
    student_val = _numeric_value(student_norm)
    if student_val is not None:
        for variant in key_variants:
            key_val = _numeric_value(variant)
            if key_val is not None and abs(student_val - key_val) < 0.0001:
                return True

    # --- Check 3: Partial answer detection ---
    # Student got the numerator right but forgot denominator
    # e.g., "minus 1" or "-1" for answer "-1/7"
    if '/' in answer_key:
        numerator = answer_key.split('/')[0].strip()
        num_norm = normalize_answer(numerator)
        if student_norm == num_norm:
            return None  # Partial — trigger guide_partial_answer
        # Also check magnitude without sign
        if student_norm == num_norm.lstrip('-') and num_norm.startswith('-'):
            return None

    # Student got the number right but forgot the sign
    # e.g., "1/7" for answer "-1/7"
    answer_norm = normalize_answer(answer_key)
    if student_norm == answer_norm.lstrip('-') and answer_norm.startswith('-'):
        return None  # Partial — got magnitude, missed sign

    # Student said "x = <correct>" (equation format)
    if '=' in student_input:
        after_equals = student_input.split('=')[-1].strip()
        return check_answer(after_equals, answer_key, accept_also)

    # --- Definitely wrong ---
    return False


# ============================================================
# SELF-TEST
# ============================================================
if __name__ == "__main__":
    # Exact matches
    assert check_answer("-1/7", "-1/7") is True
    assert check_answer("minus 1 by 7", "-1/7") is True
    assert check_answer("minus one by seven", "-1/7") is True
    assert check_answer("-1 over 7", "-1/7") is True
    assert check_answer("minus 1 over 7", "-1/7") is True

    # Numeric equivalence
    assert check_answer("0.5", "1/2") is True
    assert check_answer("2", "2/1") is True

    # Partial answers (should return None)
    assert check_answer("minus 1", "-1/7") is None  # numerator only
    assert check_answer("-1", "-1/7") is None        # numerator only
    assert check_answer("1/7", "-1/7") is None       # missed the sign

    # Equation format
    assert check_answer("x = 5", "5") is True
    assert check_answer("x = -1/7", "-1/7") is True

    # Wrong answers
    assert check_answer("5", "-1/7") is False
    assert check_answer("2/7", "-1/7") is False
    assert check_answer("hello", "-1/7") is False

    # Edge cases
    assert check_answer("", "-1/7") is False
    assert check_answer("   ", "-1/7") is False

    print("PASS")
