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

    # Normalize different minus/dash characters to standard hyphen-minus
    # This handles en-dash (–), em-dash (—), minus sign (−), etc.
    normalized = re.sub(r"[–—−‐]", "-", normalized)

    # Fix speech recognition issues with fractions
    # "- 5 / 8" or "- 5/8" → "-5/8" (remove space after minus)
    normalized = re.sub(r"-\s+(\d)", r"-\1", normalized)
    # "+ 5 / 8" → "5/8" (remove erroneous plus at start)
    normalized = re.sub(r"^\+\s*", "", normalized)
    # "5 / 8" → "5/8" (remove spaces around slash)
    normalized = re.sub(r"(\d+)\s*/\s*(\d+)", r"\1/\2", normalized)

    # Handle badly transcribed fractions like "- 5 - 8 / 5" → try to extract "-5/8"
    # Pattern: minus, number, junk, slash, number at end
    bad_fraction = re.match(r"^-?\s*(\d+).*?/\s*(\d+)$", normalized)
    if bad_fraction and "-" in normalized[:3]:
        # Likely meant negative fraction
        normalized = f"-{bad_fraction.group(1)}/{bad_fraction.group(2)}"
    elif bad_fraction:
        normalized = f"{bad_fraction.group(1)}/{bad_fraction.group(2)}"

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
    
    # Handle negative spoken fractions FIRST (before by/over conversion)
    # "minus 1 by 7" → "-1/7", "negative 2 over 3" → "-2/3"
    normalized = re.sub(r"\b(minus|negative)\s*(\d+)\s*by\s*(\d+)", r"-\2/\3", normalized)
    normalized = re.sub(r"\b(minus|negative)\s*(\d+)\s*over\s*(\d+)", r"-\2/\3", normalized)
    normalized = re.sub(r"\b(minus|negative)\s*(\d+)\s*divided\s*by\s*(\d+)", r"-\2/\3", normalized)

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
    
    # Handle "minus X" or "negative X" → "-X" (including fractions)
    # First handle fractions: "minus 1/7" → "-1/7"
    normalized = re.sub(r"\b(minus|negative)\s*(\d+/\d+)", r"-\2", normalized)
    # Then handle simple numbers: "minus 5" → "-5"
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


def extract_answer_candidate(text: str, expected_type: str = "numeric") -> Optional[str]:
    """
    Extract the answer candidate from a longer sentence.

    This handles cases like:
    - "I think it's 2/3" → extracts "2/3"
    - "The answer is -5" → extracts "-5"
    - "Two by three is my answer" → extracts "2/3" (after normalization)

    Args:
        text: The normalized student response
        expected_type: "numeric", "fraction", "yes_no", "mcq"

    Returns:
        The extracted answer candidate, or None if not found
    """
    # Patterns to extract (ordered by specificity)
    patterns = [
        # Fractions (including negative): -5/8, 2/3
        r'-?\d+\s*/\s*\d+',
        # Decimals: -3.5, 0.5
        r'-?\d+\.\d+',
        # Integers (including negative): -5, 42
        r'-?\d+',
        # Percentages: 50%
        r'\d+%',
    ]

    # For yes/no questions
    if expected_type == "yes_no":
        text_lower = text.lower()
        # Check for yes variants
        if re.search(r'\byes\b|\bhaan\b|\bcorrect\b|\bright\b|\btrue\b', text_lower):
            return "yes"
        # Check for no variants
        if re.search(r'\bno\b|\bnahi\b|\bwrong\b|\bfalse\b|\bnot\b', text_lower):
            return "no"
        return None

    # For MCQ questions
    if expected_type == "mcq":
        match = re.search(r'\b([a-dA-D])\b', text)
        if match:
            return match.group(1).lower()
        return None

    # For numeric/fraction - try each pattern
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Return the last match (usually the actual answer)
            # "I said 5 but now I think 7" → return "7"
            return matches[-1].replace(" ", "")

    return None


def check_answer(correct_answer: str, student_answer: str) -> bool:
    """
    Check if student's answer matches the correct answer.

    This is the main evaluation function called by the API.

    IMPORTANT: This now extracts the answer from within longer sentences.
    "I'm asking, what? Two by three." will correctly match "2/3".

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

    # Normalize the correct answer
    norm_correct = normalize_answer(correct_answer)

    # Determine expected answer type
    expected_type = "numeric"
    if correct_answer.lower() in ["yes", "no"]:
        expected_type = "yes_no"
    elif correct_answer.lower() in ["a", "b", "c", "d"]:
        expected_type = "mcq"
    elif "/" in correct_answer:
        expected_type = "fraction"

    # STEP 1: Try direct comparison with full normalized text
    norm_student = normalize_answer(normalized_student)
    if norm_correct == norm_student:
        return True

    # STEP 2: Extract answer candidate from within the sentence
    candidate = extract_answer_candidate(normalized_student, expected_type)
    if candidate:
        norm_candidate = normalize_answer(candidate)

        # Direct match with candidate
        if norm_correct == norm_candidate:
            return True

        # Fraction equivalence with candidate
        if "/" in norm_correct or "/" in norm_candidate:
            if fractions_equivalent(norm_correct, norm_candidate):
                return True

        # Numeric equivalence with candidate
        try:
            correct_val = eval_safe(norm_correct)
            candidate_val = eval_safe(norm_candidate)
            if correct_val is not None and candidate_val is not None:
                if abs(correct_val - candidate_val) < 0.0001:
                    return True
        except Exception:
            pass

    # STEP 3: Fallback - check fraction equivalence with full text
    if "/" in correct_answer or "/" in normalized_student:
        if fractions_equivalent(norm_correct, norm_student):
            return True

    # STEP 4: Fallback - numeric equivalence with full text
    try:
        correct_val = eval_safe(norm_correct)
        student_val = eval_safe(norm_student)
        if correct_val is not None and student_val is not None:
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
        # NEW: Embedded answer tests (answer within longer sentence)
        ("2/3", "I'm asking you, what are you doing? Two by three.", True),
        ("2/3", "umm let me think... 2 by 3", True),
        ("-5/8", "I think the answer is minus 5 by 8", True),
        ("yes", "Yes, zero is a rational number", True),
        ("yes", "No, zero is not a rational number", False),  # Wrong answer
        ("7", "first I thought 5 but now I say 7", True),  # Takes last number
    ]

    for correct, student, expected in answer_tests:
        result = check_answer(correct, student)
        status = "✅" if result == expected else "❌"
        print(f"  {status} correct='{correct}', student='{student}' → {result}")
