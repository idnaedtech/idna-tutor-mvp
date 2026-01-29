"""
IDNA EdTech - Enhanced Evaluator
=================================
Deterministic answer checker with spoken variant normalization.

This evaluator handles voice input variations like:
- "2 by 3" → "2/3"
- "two thirds" → "2/3"
- "minus 5" → "-5"
- "the answer is 5" → "5"
- "x equals 7" → "7"

Architecture (per PRD):
- Evaluator is DETERMINISTIC - never uses LLM for judging
- LLM only phrases responses, never decides correctness
"""

import re
from typing import Tuple, Optional


# Number word to digit mapping
NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20",
    "thirty": "30", "forty": "40", "fifty": "50",
    "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90",
    "hundred": "100",
}

# Fraction word patterns (singular form only, we strip 's' during processing)
FRACTION_DENOMINATORS = {
    "half": 2,
    "third": 3,
    "fourth": 4,
    "quarter": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
}


def normalize_spoken_input(text: str) -> str:
    """
    Normalize spoken math variants to standard format.
    
    Handles:
    - "2 by 3" → "2/3"
    - "two thirds" → "2/3"
    - "minus 5" → "-5"
    - "negative 5" → "-5"
    - "the answer is 5" → "5"
    - "x equals 7" → "7"
    - "it is 5" → "5"
    - "point 5" → ".5"
    - "2 point 5" → "2.5"
    - Duplicate text from STT bug: "2 by 3 2 by 3" → "2/3"
    
    Args:
        text: The spoken input text
        
    Returns:
        Normalized answer string
    """
    if not text:
        return ""
    
    # Convert to lowercase and strip
    normalized = text.lower().strip()
    
    # Remove common filler phrases
    fillers = [
        r"^the answer is\s*",
        r"^it is\s*",
        r"^i think\s*(it'?s?\s*)?",
        r"^that'?s?\s*",
        r"^it'?s?\s*",
        r"^equals?\s*",
        r"^is\s*",
        r"^x\s*equals?\s*",
        r"^y\s*equals?\s*",
        r"^answer\s*:?\s*",
    ]
    for pattern in fillers:
        normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
    
    # Handle STT duplicate bug: "2 by 3 2 by 3" → keep first occurrence
    # Split and check if first half equals second half
    words = normalized.split()
    if len(words) >= 4 and len(words) % 2 == 0:
        mid = len(words) // 2
        if words[:mid] == words[mid:]:
            normalized = " ".join(words[:mid])
    
    # Convert number words to digits
    for word, digit in NUMBER_WORDS.items():
        # Word boundary matching to avoid partial replacements
        normalized = re.sub(rf"\b{word}\b", digit, normalized)
    
    # Handle compound numbers like "twenty one" → "21"
    compound_pattern = r"\b(\d0)\s+(\d)\b"
    normalized = re.sub(compound_pattern, lambda m: str(int(m.group(1)) + int(m.group(2))), normalized)
    
    # Handle "X by Y" → "X/Y" (spoken fractions)
    normalized = re.sub(r"(\d+)\s*by\s*(\d+)", r"\1/\2", normalized)
    
    # Handle "X over Y" → "X/Y"
    normalized = re.sub(r"(\d+)\s*over\s*(\d+)", r"\1/\2", normalized)
    
    # Handle "X divided by Y" → "X/Y"
    normalized = re.sub(r"(\d+)\s*divided\s*by\s*(\d+)", r"\1/\2", normalized)
    
    # Handle fraction words: "two thirds" → "2/3", "eleven twelfths" → "11/12"
    # First, normalize plural forms: "thirds" → "third", "twelfths" → "twelfth"
    for frac_word, denom in FRACTION_DENOMINATORS.items():
        # Handle plurals like "thirds", "fourths", etc.
        plural = frac_word + "s" if not frac_word.endswith("f") else frac_word[:-1] + "ves"
        if frac_word == "half":
            plural = "halves"
        
        # Pattern: "number fraction_word(s)" → "number/denominator"
        for form in [frac_word, plural]:
            pattern = rf"(\d+)\s*{form}\b"
            normalized = re.sub(pattern, rf"\1/{denom}", normalized)
    
    # Handle "a third" → "1/3", "a half" → "1/2"
    normalized = re.sub(r"\ba\s*third\b", "1/3", normalized)
    normalized = re.sub(r"\ba\s*half\b", "1/2", normalized)
    normalized = re.sub(r"\ba\s*quarter\b", "1/4", normalized)
    normalized = re.sub(r"\ban?\s*eighth\b", "1/8", normalized)
    
    # Handle "minus X" or "negative X" → "-X"
    normalized = re.sub(r"\b(minus|negative)\s*(\d+)", r"-\2", normalized)
    
    # Handle decimal points: "point 5" → ".5", "2 point 5" → "2.5"
    normalized = re.sub(r"(\d*)\s*point\s*(\d+)", r"\1.\2", normalized)
    normalized = re.sub(r"^\.(\d+)", r"0.\1", normalized)  # ".5" → "0.5"
    
    # Handle percentage: "50 percent" or "50%" → "50%"
    normalized = re.sub(r"(\d+)\s*percent\b", r"\1%", normalized)
    
    # Remove any remaining extra whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    
    # Remove trailing punctuation
    normalized = re.sub(r"[.,!?]+$", "", normalized)
    
    return normalized


def simplify_fraction(numerator: int, denominator: int) -> Tuple[int, int]:
    """Reduce a fraction to its simplest form."""
    from math import gcd
    if denominator == 0:
        return (numerator, denominator)
    common = gcd(abs(numerator), abs(denominator))
    return (numerator // common, denominator // common)


def parse_fraction(text: str) -> Optional[Tuple[int, int]]:
    """
    Parse a fraction string into (numerator, denominator).
    
    Handles: "2/3", "2 / 3", "-2/3"
    
    Returns None if not a valid fraction.
    """
    match = re.match(r"^(-?\d+)\s*/\s*(\d+)$", text.strip())
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return None


def fractions_equivalent(frac1: str, frac2: str) -> bool:
    """
    Check if two fractions are mathematically equivalent.
    
    Examples:
        "2/4" == "1/2" → True
        "6/9" == "2/3" → True
    """
    parsed1 = parse_fraction(frac1)
    parsed2 = parse_fraction(frac2)
    
    if not parsed1 or not parsed2:
        return False
    
    # Cross multiply to compare: a/b == c/d iff a*d == b*c
    a, b = parsed1
    c, d = parsed2
    
    if b == 0 or d == 0:
        return False
    
    return a * d == b * c


def normalize_answer(answer: str) -> str:
    """
    Normalize an answer for comparison.
    
    - Strips whitespace
    - Lowercases
    - Simplifies fractions
    - Handles decimals
    """
    if not answer:
        return ""
    
    normalized = answer.strip().lower()
    
    # Try to simplify if it's a fraction
    fraction = parse_fraction(normalized)
    if fraction:
        num, denom = simplify_fraction(fraction[0], fraction[1])
        return f"{num}/{denom}"
    
    # Try to normalize decimal representation
    try:
        # Convert to float and back to remove trailing zeros
        float_val = float(normalized)
        if float_val == int(float_val):
            return str(int(float_val))
        return str(float_val)
    except ValueError:
        pass
    
    return normalized


def check_answer(correct_answer: str, student_answer: str) -> bool:
    """
    Check if student's answer matches the correct answer.
    
    This is the main evaluation function called by the API.
    
    Args:
        correct_answer: The expected correct answer
        student_answer: The student's submitted answer (may be spoken)
        
    Returns:
        True if the answer is correct, False otherwise
    """
    if not student_answer:
        return False
    
    # First, normalize spoken input
    normalized_student = normalize_spoken_input(student_answer)
    
    # Normalize both answers
    norm_correct = normalize_answer(correct_answer)
    norm_student = normalize_answer(normalized_student)
    
    # Direct comparison
    if norm_correct == norm_student:
        return True
    
    # Check fraction equivalence
    if "/" in correct_answer or "/" in normalized_student:
        if fractions_equivalent(norm_correct, norm_student):
            return True
    
    # Check numeric equivalence (handles "0.5" vs "1/2")
    try:
        correct_val = eval_safe(norm_correct)
        student_val = eval_safe(norm_student)
        if correct_val is not None and student_val is not None:
            # Allow small floating point tolerance
            if abs(correct_val - student_val) < 0.0001:
                return True
    except Exception:
        pass
    
    return False


def eval_safe(expr: str) -> Optional[float]:
    """
    Safely evaluate a simple math expression.
    Only allows numbers, fractions, and basic operations.
    """
    # Only allow digits, /, -, ., and whitespace
    if not re.match(r"^[\d\s./\-]+$", expr):
        return None
    
    try:
        # Handle fractions
        if "/" in expr:
            parts = expr.split("/")
            if len(parts) == 2:
                denom = float(parts[1])
                if denom == 0:
                    return None
                return float(parts[0]) / denom
        return float(expr)
    except Exception:
        return None


# For testing
if __name__ == "__main__":
    print("=== Evaluator Test ===\n")
    
    # Test spoken variant normalization
    test_cases = [
        ("2 by 3", "2/3"),
        ("two thirds", "2/3"),
        ("minus 5", "-5"),
        ("the answer is 5", "5"),
        ("x equals 7", "7"),
        ("2 point 5", "2.5"),
        ("point 5", "0.5"),
        ("fifty percent", "50%"),
        ("2 by 3 2 by 3", "2/3"),  # Duplicate bug
        ("a half", "1/2"),
        ("negative 10", "-10"),
    ]
    
    print("Spoken Normalization Tests:")
    for spoken, expected in test_cases:
        result = normalize_spoken_input(spoken)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{spoken}' → '{result}' (expected: '{expected}')")
    
    print("\nAnswer Checking Tests:")
    answer_tests = [
        ("2/3", "2 by 3", True),
        ("2/3", "two thirds", True),
        ("1/2", "2/4", True),
        ("-5", "minus 5", True),
        ("0.5", "point 5", True),
        ("11/12", "eleven twelfths", True),
        ("7", "the answer is 7", True),
        ("3", "5", False),
    ]
    
    for correct, student, expected in answer_tests:
        result = check_answer(correct, student)
        status = "✅" if result == expected else "❌"
        print(f"  {status} correct='{correct}', student='{student}' → {result}")
