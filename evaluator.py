"""
IDNA EdTech - Answer Evaluator v2
Robust answer checking for math tutoring

Handles:
- Integers, decimals, negatives
- Word numbers (seven, minus three)
- Fractions (7/2, 3/4, one half)
- Units (7 cm, 25 kg)
- Expressions (x = 7, answer is 7)
- Variants (7.0, 07, 7.00)
"""

import re
from fractions import Fraction
from typing import Union, Optional

# Word to number mapping
WORD_TO_NUM = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
    'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
    'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
    'eighteen': 18, 'nineteen': 19, 'twenty': 20,
    'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60,
    'seventy': 70, 'eighty': 80, 'ninety': 90,
    'hundred': 100, 'thousand': 1000,
    # Hindi-English variants (romanized)
    'ek': 1, 'do': 2, 'teen': 3, 'char': 4, 'paanch': 5, 'panch': 5,
    'chhe': 6, 'chhah': 6, 'saat': 7, 'sat': 7, 'aath': 8, 'ath': 8, 
    'nau': 9, 'nou': 9, 'das': 10, 'dus': 10,
    'gyarah': 11, 'barah': 12, 'terah': 13, 'chaudah': 14, 'pandrah': 15,
    'solah': 16, 'satrah': 17, 'atharah': 18, 'unnis': 19, 'bees': 20,
}

# Fraction word mapping
FRACTION_WORDS = {
    'half': 0.5, 'one half': 0.5, 'a half': 0.5,
    'quarter': 0.25, 'one quarter': 0.25, 'a quarter': 0.25,
    'third': 1/3, 'one third': 1/3, 'a third': 1/3,
    'fourth': 0.25, 'one fourth': 0.25, 'a fourth': 0.25,
    'three quarters': 0.75, 'three fourths': 0.75,
    'two thirds': 2/3,
}

# Units to strip
UNITS = [
    'cm', 'centimeter', 'centimeters', 'centimetre', 'centimetres',
    'm', 'meter', 'meters', 'metre', 'metres',
    'km', 'kilometer', 'kilometers', 'kilometre', 'kilometres',
    'mm', 'millimeter', 'millimeters',
    'kg', 'kilogram', 'kilograms', 'kilo', 'kilos',
    'g', 'gram', 'grams',
    'mg', 'milligram', 'milligrams',
    'l', 'liter', 'liters', 'litre', 'litres',
    'ml', 'milliliter', 'milliliters',
    'sq', 'square', 'sq.', 'cm2', 'cm²', 'm2', 'm²',
    'cubic', 'cm3', 'cm³', 'm3', 'm³',
    'degrees', 'degree', '°', 'deg',
    'rupees', 'rupee', 'rs', 'rs.', '₹',
    'percent', 'percentage', '%',
    'seconds', 'second', 'sec', 's',
    'minutes', 'minute', 'min',
    'hours', 'hour', 'hr', 'hrs',
    'days', 'day',
    'years', 'year', 'yr', 'yrs',
]


def normalize_answer(answer: str) -> str:
    """Normalize answer string for comparison."""
    if not answer:
        return ""
    
    # Convert to lowercase and strip whitespace
    answer = str(answer).lower().strip()
    
    # Remove common prefixes
    prefixes = [
        'the answer is', 'answer is', 'answer:', 'ans:', 'ans is',
        'it is', 'it\'s', 'its', 'equals', 'equal to', '=',
        'x =', 'x=', 'y =', 'y=', 'n =', 'n=',
        'result is', 'result:', 'solution is', 'solution:',
    ]
    for prefix in prefixes:
        if answer.startswith(prefix):
            answer = answer[len(prefix):].strip()
    
    # Only strip units if answer has numbers followed by unit
    # Don't strip from pure word answers
    if re.search(r'\d', answer):  # Only if answer contains digits
        for unit in UNITS:
            # Remove unit at end (with optional space)
            pattern = r'\s*' + re.escape(unit) + r'\.?\s*$'
            answer = re.sub(pattern, '', answer, flags=re.IGNORECASE)
    
    return answer.strip()


def word_to_number(word: str) -> Optional[float]:
    """Convert word representation to number."""
    word = word.lower().strip()
    
    # Check fraction words first
    for frac_word, value in FRACTION_WORDS.items():
        if word == frac_word:
            return value
    
    # Handle negative
    is_negative = False
    if word.startswith('minus ') or word.startswith('negative '):
        is_negative = True
        word = word.replace('minus ', '').replace('negative ', '').strip()
    
    # Direct word match
    if word in WORD_TO_NUM:
        value = WORD_TO_NUM[word]
        return -value if is_negative else value
    
    # Try to parse as number after removing negative prefix
    try:
        value = float(word)
        return -value if is_negative else value
    except ValueError:
        pass
    
    # Handle compound numbers like "twenty one", "thirty five"
    parts = word.split()
    if len(parts) == 2:
        if parts[0] in WORD_TO_NUM and parts[1] in WORD_TO_NUM:
            tens = WORD_TO_NUM[parts[0]]
            ones = WORD_TO_NUM[parts[1]]
            if tens >= 20 and ones < 10:
                value = tens + ones
                return -value if is_negative else value
    
    # Handle "X by Y" format (fraction)
    if ' by ' in word:
        parts = word.split(' by ')
        if len(parts) == 2:
            try:
                num = word_to_number(parts[0].strip())
                den = word_to_number(parts[1].strip())
                if num is not None and den is not None and den != 0:
                    value = num / den
                    return -value if is_negative else value
            except:
                pass
    
    return None


def parse_fraction(text: str) -> Optional[float]:
    """Parse fraction string to float."""
    text = text.strip()
    
    # Handle "a/b" format
    if '/' in text:
        parts = text.split('/')
        if len(parts) == 2:
            try:
                num = float(parts[0].strip())
                den = float(parts[1].strip())
                if den != 0:
                    return num / den
            except ValueError:
                # Try word numbers
                num = word_to_number(parts[0].strip())
                den = word_to_number(parts[1].strip())
                if num is not None and den is not None and den != 0:
                    return num / den
    
    return None


def extract_number(text: str) -> Optional[float]:
    """Extract numeric value from text."""
    text = normalize_answer(text)
    
    if not text:
        return None
    
    # Try direct float conversion first
    try:
        return float(text)
    except ValueError:
        pass
    
    # Try fraction
    fraction_value = parse_fraction(text)
    if fraction_value is not None:
        return fraction_value
    
    # Try word to number
    word_value = word_to_number(text)
    if word_value is not None:
        return word_value
    
    # Try to extract number from text using regex
    # Match integers, decimals, negative numbers
    match = re.search(r'-?\d+\.?\d*', text)
    if match:
        try:
            return float(match.group())
        except ValueError:
            pass
    
    return None


def check_answer(correct: Union[str, int, float], student: str, tolerance: float = 0.001) -> bool:
    """
    Check if student answer matches correct answer.
    
    Args:
        correct: The correct answer (can be string, int, or float)
        student: The student's answer as string
        tolerance: Acceptable difference for float comparison
    
    Returns:
        True if answer is correct, False otherwise
    """
    # Handle empty inputs
    if student is None or str(student).strip() == "":
        return False
    
    # Normalize both answers
    correct_str = normalize_answer(str(correct))
    student_str = normalize_answer(str(student))
    
    # Direct string match (case insensitive)
    if correct_str == student_str:
        return True
    
    # Try numeric comparison
    correct_num = extract_number(str(correct))
    student_num = extract_number(str(student))
    
    if correct_num is not None and student_num is not None:
        # Float comparison with tolerance
        if abs(correct_num - student_num) < tolerance:
            return True
        
        # Check if both are effectively integers
        if correct_num == int(correct_num) and student_num == int(student_num):
            return int(correct_num) == int(student_num)
    
    return False


# ============================================================
# TEST SUITE - 35+ Test Cases
# ============================================================

def run_tests():
    """Run all evaluator tests."""
    
    test_cases = [
        # Basic integers
        ("7", "7", True, "Exact match"),
        ("7", "07", True, "Leading zero"),
        ("7", "7.0", True, "Decimal equivalent"),
        ("7", "7.00", True, "Multiple decimal zeros"),
        ("42", "42", True, "Two digit number"),
        ("100", "100", True, "Three digit number"),
        
        # Negative numbers
        ("-5", "-5", True, "Negative exact"),
        ("-5", "minus 5", True, "Negative word"),
        ("-5", "negative 5", True, "Negative word alt"),
        ("-3", "-3.0", True, "Negative decimal"),
        
        # Decimals
        ("3.14", "3.14", True, "Decimal exact"),
        ("3.14", "3.140", True, "Trailing zero"),
        ("0.5", "0.5", True, "Less than 1"),
        ("0.5", ".5", True, "No leading zero"),
        ("2.5", "2.50", True, "Decimal trailing zero"),
        
        # Word numbers
        ("7", "seven", True, "Word number"),
        ("12", "twelve", True, "Word twelve"),
        ("25", "twenty five", True, "Compound word"),
        ("0", "zero", True, "Word zero"),
        
        # Fractions
        ("0.5", "1/2", True, "Half as fraction"),
        ("0.5", "one half", True, "Half as words"),
        ("0.25", "1/4", True, "Quarter"),
        ("0.25", "one fourth", True, "Fourth as words"),
        ("0.75", "3/4", True, "Three quarters"),
        ("3.5", "7/2", True, "Improper fraction"),
        ("3.5", "seven by two", True, "Fraction as words"),
        
        # With units
        ("7", "7 cm", True, "With cm"),
        ("7", "7cm", True, "No space before unit"),
        ("25", "25 kg", True, "With kg"),
        ("100", "100 meters", True, "With full unit"),
        ("45", "45 degrees", True, "With degrees"),
        ("50", "50%", True, "With percent"),
        ("500", "500 rupees", True, "With rupees"),
        
        # With prefixes
        ("7", "the answer is 7", True, "With prefix"),
        ("7", "x = 7", True, "Variable assignment"),
        ("7", "answer: 7", True, "With colon"),
        ("7", "it is 7", True, "It is prefix"),
        ("7", "equals 7", True, "Equals prefix"),
        
        # Wrong answers
        ("7", "8", False, "Wrong number"),
        ("7", "six", False, "Wrong word"),
        ("7", "", False, "Empty answer"),
        ("7", "   ", False, "Whitespace only"),
        ("3.14", "3.15", False, "Wrong decimal"),
        
        # Edge cases
        ("0", "0", True, "Zero"),
        ("0", "zero", True, "Zero as word"),
        ("-0", "0", True, "Negative zero"),
        ("1000", "1000", True, "Thousand"),
        ("999", "999", True, "Three nines"),
        
        # Hindi number words
        ("7", "saat", True, "Hindi seven"),
        ("10", "das", True, "Hindi ten"),
        ("5", "paanch", True, "Hindi five"),
    ]
    
    print("=" * 60)
    print("IDNA EdTech - Evaluator v2 Test Suite")
    print("=" * 60)
    print()
    
    passed = 0
    failed = 0
    
    for correct, student, expected, description in test_cases:
        result = check_answer(correct, student)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"{status} | {description}")
        print(f"       Correct: '{correct}' | Student: '{student}' | Expected: {expected} | Got: {result}")
        print()
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
