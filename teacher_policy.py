"""
IDNA EdTech - Teacher Policy Layer
===================================
Implements teacher-like behavior instead of chatbot responses.

Key Principles (from ChatGPT analysis):
1. Diagnose what the student understands (error taxonomy)
2. Choose a teaching move (not random response)
3. Run a loop: explain → ask → listen → adapt

Architecture:
- Pass 1: Planner decides WHAT teaching move to use (structured JSON)
- Pass 2: Speaker renders it in teacher voice
- Rule: Never TEACH without CHECK within next turn
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import re


# ============================================================
# ERROR TAXONOMY (Math - Class 8 CBSE)
# ============================================================

class TeachingPhase(Enum):
    """
    Soft teaching phase — internal to teacher_policy.
    Tracks where we are in the teaching cycle for a given question.
    """
    PRESENT = "present"        # Present the question
    ATTEMPT = "attempt"        # Student attempts answer
    DIAGNOSE = "diagnose"      # Diagnose the error
    SCAFFOLD = "scaffold"      # Provide scaffolding (hints, examples)
    CHECK = "check"            # Check understanding with micro-question
    ADVANCE = "advance"        # Move to next question


class ErrorType(Enum):
    """
    Math error taxonomy for diagnosis.
    Knowing WHY student got it wrong helps choose the right teaching move.
    """
    # Arithmetic errors
    ARITHMETIC_SLIP = "arithmetic_slip"          # Simple calculation mistake
    SIGN_ERROR = "sign_error"                    # Got +/- wrong

    # Operation errors
    WRONG_OPERATION = "wrong_operation"          # Added when should subtract, etc.
    OPERATION_ORDER = "operation_order"          # BODMAS/order of operations wrong

    # Fraction errors
    FRACTION_ADDITION = "fraction_addition"      # Added numerators AND denominators
    FRACTION_MULTIPLY = "fraction_multiply"      # Wrong multiplication approach
    FRACTION_SIMPLIFY = "fraction_simplify"      # Didn't simplify / simplified wrong
    COMMON_DENOMINATOR = "common_denominator"    # Forgot to find LCD

    # Concept errors
    CONCEPT_MISUNDERSTANDING = "concept_misunderstanding"  # Fundamental concept wrong
    WORD_PROBLEM_TRANSLATION = "word_problem_translation"  # Couldn't parse word problem

    # Partial/incomplete
    INCOMPLETE_ANSWER = "incomplete_answer"      # Stopped mid-calculation
    MISSING_STEP = "missing_step"                # Skipped a required step

    # Unknown
    UNKNOWN = "unknown"                          # Can't determine error type


# Common error patterns for detection
ERROR_PATTERNS = {
    ErrorType.SIGN_ERROR: [
        # Student answer has opposite sign of correct
        lambda correct, student: (
            correct.startswith('-') and not student.startswith('-') or
            not correct.startswith('-') and student.startswith('-')
        ),
    ],
    ErrorType.FRACTION_ADDITION: [
        # Student added both num and denom (e.g., 1/3 + 1/4 = 2/7)
        lambda correct, student: '/' in correct and '/' in student,
    ],
}


def diagnose_error(
    correct_answer: str,
    student_answer: str,
    question_text: str = "",
    question_type: str = "numeric",
) -> Dict[str, Any]:
    """
    Diagnose WHY the student got it wrong.

    Returns:
        dict with:
        - error_type: ErrorType value
        - confidence: 0.0-1.0 how sure we are about diagnosis
        - hint: Suggested mini-hint based on error
        - missing_concept: Tag for student model
    """
    if not student_answer:
        return {
            "error_type": ErrorType.INCOMPLETE_ANSWER.value,
            "confidence": 1.0,
            "hint": "You need to give an answer. Take your best guess!",
            "missing_concept": None,
        }

    # Normalize for comparison
    correct = correct_answer.strip().lower()
    student = student_answer.strip().lower()

    # Check for sign error
    if _is_sign_error(correct, student):
        return {
            "error_type": ErrorType.SIGN_ERROR.value,
            "confidence": 0.9,
            "hint": "Check the sign - is it positive or negative?",
            "missing_concept": "negative_numbers",
        }

    # Check for fraction errors
    if '/' in correct:
        frac_error = _diagnose_fraction_error(correct, student, question_text)
        if frac_error:
            return frac_error

    # Check for arithmetic slip (close but not exact)
    if _is_arithmetic_slip(correct, student):
        return {
            "error_type": ErrorType.ARITHMETIC_SLIP.value,
            "confidence": 0.8,
            "hint": "Double-check your calculation.",
            "missing_concept": None,
        }

    # Check for wrong operation in word problems
    if _looks_like_word_problem(question_text):
        return {
            "error_type": ErrorType.WORD_PROBLEM_TRANSLATION.value,
            "confidence": 0.6,
            "hint": "Read the question again. What operation does it ask for?",
            "missing_concept": "word_problems",
        }

    # Default: unknown error
    return {
        "error_type": ErrorType.UNKNOWN.value,
        "confidence": 0.5,
        "hint": "Let's think about this step by step.",
        "missing_concept": None,
    }


def _is_sign_error(correct: str, student: str) -> bool:
    """Check if the only difference is the sign."""
    try:
        # Extract numbers
        c_num = re.sub(r'[^\d./]', '', correct.replace('-', ''))
        s_num = re.sub(r'[^\d./]', '', student.replace('-', ''))

        if c_num == s_num:
            # Same magnitude, check if signs differ
            c_neg = correct.startswith('-')
            s_neg = student.startswith('-')
            return c_neg != s_neg
    except:
        pass
    return False


def _is_arithmetic_slip(correct: str, student: str) -> bool:
    """Check if student is close (off by 1, transposed digits, etc.)."""
    try:
        # Try to parse as numbers
        if '/' in correct:
            c_parts = correct.split('/')
            c_val = float(c_parts[0]) / float(c_parts[1])
        else:
            c_val = float(correct)

        if '/' in student:
            s_parts = student.split('/')
            s_val = float(s_parts[0]) / float(s_parts[1])
        else:
            s_val = float(student)

        # Check if within 10% or off by 1
        diff = abs(c_val - s_val)
        return diff <= 1 or diff / max(abs(c_val), 0.001) < 0.1
    except:
        return False


def _diagnose_fraction_error(correct: str, student: str, question: str) -> Optional[Dict]:
    """Diagnose specific fraction errors."""
    try:
        # Parse correct answer
        c_parts = correct.split('/')
        c_num, c_den = int(c_parts[0]), int(c_parts[1])

        if '/' not in student:
            # Student didn't give a fraction
            return {
                "error_type": ErrorType.INCOMPLETE_ANSWER.value,
                "confidence": 0.8,
                "hint": "Your answer should be a fraction.",
                "missing_concept": "fractions",
            }

        s_parts = student.split('/')
        s_num, s_den = int(s_parts[0]), int(s_parts[1])

        # Check if student added denominators (common error)
        # e.g., 1/3 + 1/4 = 2/7 (wrong - added both)
        if "+" in question and s_den == c_den + 1:
            return {
                "error_type": ErrorType.FRACTION_ADDITION.value,
                "confidence": 0.85,
                "hint": "When adding fractions, don't add the denominators. Find a common denominator first.",
                "missing_concept": "fraction_addition",
            }

        # Check if numerator is right but denominator wrong
        if abs(s_num) == abs(c_num) and s_den != c_den:
            return {
                "error_type": ErrorType.COMMON_DENOMINATOR.value,
                "confidence": 0.8,
                "hint": "The numerator is right! Check the denominator.",
                "missing_concept": "common_denominator",
            }

        # Check if denominator is right but numerator wrong
        if s_den == c_den and s_num != c_num:
            return {
                "error_type": ErrorType.ARITHMETIC_SLIP.value,
                "confidence": 0.75,
                "hint": "The denominator is correct. Double-check how you combined the numerators.",
                "missing_concept": None,
            }

        # Check for simplification error
        from math import gcd
        s_gcd = gcd(abs(s_num), abs(s_den))
        if s_gcd > 1:
            # Student's answer can be simplified
            simplified_num = s_num // s_gcd
            simplified_den = s_den // s_gcd
            if simplified_num == c_num and simplified_den == c_den:
                return {
                    "error_type": ErrorType.FRACTION_SIMPLIFY.value,
                    "confidence": 0.9,
                    "hint": "That's correct! But can you simplify it?",
                    "missing_concept": None,
                }
    except:
        pass

    return None


def _looks_like_word_problem(question: str) -> bool:
    """Check if question is a word problem."""
    word_problem_indicators = [
        "how many", "how much", "find", "calculate", "total",
        "left", "remaining", "difference", "sum", "product",
        "if", "when", "then", "bought", "sold", "gave", "received"
    ]
    q_lower = question.lower()
    return any(ind in q_lower for ind in word_problem_indicators)


# ============================================================
# TEACHING MOVES
# ============================================================

class TeachingMove(Enum):
    """
    Fixed set of teaching moves (like chess moves).
    Teacher doesn't improvise - chooses from this menu.
    """
    PROBE = "probe"                    # Diagnostic question to locate misunderstanding
    HINT_STEP = "hint_step"            # Give the next smallest step, not the answer
    WORKED_EXAMPLE = "worked_example"  # Solve a similar simpler example
    ERROR_EXPLAIN = "error_explain"    # Name the error type and correct it
    REFRAME = "reframe"                # Explain using different representation
    CHECK_UNDERSTANDING = "check"      # Quick yes/no or short numeric check
    RECAP = "recap"                    # 2-line summary + "now you try again"
    CHALLENGE = "challenge"            # Slightly harder follow-up if correct quickly
    CONFIRM = "confirm"                # Acknowledge correct answer
    REVEAL = "reveal"                  # Show the answer after max attempts


# Teaching move descriptions for LLM
MOVE_DESCRIPTIONS = {
    TeachingMove.PROBE: "Ask ONE diagnostic question to find what they don't understand",
    TeachingMove.HINT_STEP: "Give the smallest possible next step - NOT the answer",
    TeachingMove.WORKED_EXAMPLE: "Show a simpler example: 'If 1/2 + 1/2 = 1, then...'",
    TeachingMove.ERROR_EXPLAIN: "Name their specific mistake and show the fix",
    TeachingMove.REFRAME: "Explain the same idea differently (visual, analogy, etc.)",
    TeachingMove.CHECK_UNDERSTANDING: "Ask ONE quick check question (yes/no or number)",
    TeachingMove.RECAP: "Summarize in 1-2 lines, then ask them to try again",
    TeachingMove.CHALLENGE: "Give a slightly harder follow-up question",
    TeachingMove.CONFIRM: "Briefly confirm they're right and say why",
    TeachingMove.REVEAL: "Show the correct answer with brief explanation",
}


# ============================================================
# TEACHER PLANNER (2-pass approach)
# ============================================================

@dataclass
class TeacherPlan:
    """Structured output from the Teacher Planner."""
    teacher_move: TeachingMove
    goal: str                          # What the next 20-40 seconds achieve
    prompt_to_student: str             # The ONE question to ask
    explanation: str                   # Max 2-3 short lines
    check_question: Optional[str]      # Quick follow-up check
    tone: str                          # warm/firm/neutral
    max_words: int                     # Hard limit on response length
    # New fields per ChatGPT feedback
    expected_response_type: str = "number"  # "number" | "yes_no" | "short_explanation"
    max_response_words: int = 10            # Expected student response length
    # Warmth Policy fields
    warmth_level: int = 1                   # 0=neutral, 1=calm, 2=supportive, 3=soothing
    warmth_primitive: str = ""              # One warmth phrase (max 8 words)


# ============================================================
# WARMTH POLICY (makes tutor feel human, not examiner)
# ============================================================

# Warmth primitives by level (only ONE per turn).
# Level 0=neutral, 1=calm, 2=supportive, 3=soothing.
# Avoids praise-like phrases when wrong - uses acknowledgements instead.
WARMTH_PRIMITIVES = {
    0: (),  # Neutral (fast drills)
    1: ("Yes!", "That's right.", "Good.", "Exactly."),  # Calm (correct)
    2: ("Hmm.", "I see.", "Okay.", "Let me understand.", "Tell me,"),  # Supportive (wrong)
    3: ("That's okay.", "No problem.", "It's okay.", "Let's pause.", "Take your time."),  # Soothing (frustrated)
}

# Diagnostic questions to understand student's thinking (replace "Not quite").
DIAGNOSTIC_STARTERS = (
    "Tell me, what did you do?",
    "How did you get that?",
    "Walk me through your steps.",
    "What did you do first?",
)

# Real-world analogies for math concepts (familiar to Indian students).
# Each entry has: analogy (object), example (story), optional rule (principle).
CONCEPT_ANALOGIES = {
    "fraction_addition_same_denom": {
        "analogy": "roti pieces",
        "example": "1/4 + 1/4 = 2/4. Two pieces out of four.",
        "rule": "Same bottom? Just add tops.",
    },
    "fraction_addition_diff_denom": {
        "analogy": "different sized pieces",
        "example": "1/2 and 1/4 are different sizes. Need same size first.",
    },
    "fraction_meaning": {
        "analogy": "roti or pizza",
        "example": "3/4 = 3 pieces out of 4. Top = taken, bottom = total.",
    },
    "additive_inverse": {
        "analogy": "money",
        "example": "Have 5 rupees, owe 5 rupees = 0. That's 5 + (-5) = 0.",
    },
    "negative_addition": {
        "analogy": "steps",
        "example": "-3 + 2: Go back 3, forward 2. End up 1 back = -1.",
    },
    "rational_number": {
        "analogy": "any fraction",
        "example": "Rational = can be p/q. Like 3 = 3/1, 0.5 = 1/2.",
    },
    "same_denominator_rule": {
        "analogy": "apples",
        "example": "3 apples + 2 apples = 5 apples. Same with sevenths.",
    },
}

# Phrases for offering student choice/agency
AGENCY_PHRASES = [
    "Do you want to try one more, or take a break?",
    "Should we continue, or stop here for today?",
    "Want to try again, or should I explain more?",
    "Ready for the next one, or need more time?",
]

# Phrases for validating student feelings
VALIDATION_PHRASES = [
    "That's okay, this is new for you.",
    "Making mistakes is how we learn.",
    "First time you saw this - it's okay to be confused.",
    "Everyone finds this tricky at first.",
]

# Track recent primitives to avoid repetition (per session)
_recent_primitives: Dict[str, List[str]] = {}  # session_id -> last 3 primitives

# Phrases to remove from GPT output (assistant-y language).
# All map to empty string (removal).
BANNED_PHRASES = frozenset({
    # AI tells
    "as an ai", "i can help you", "i'd be happy to", "i'm here to help",
    # Fake encouragement (sounds insincere when wrong)
    "let's dive in", "great question", "great job", "great effort", "great work",
    "excellent", "wonderful", "fantastic", "amazing", "awesome", "brilliant", "perfect",
    "you're doing great", "really close", "so close", "very close", "you're almost there",
    "nice try", "good job", "well done",
    # Filler confirmations
    "absolutely", "certainly", "of course", "definitely", "sure thing",
})

# For backward compatibility with existing code
BANNED_PHRASE_REPLACEMENTS = {phrase: "" for phrase in BANNED_PHRASES}

# Frustration indicators (include apostrophe variants for STT).
FRUSTRATION_PHRASES = frozenset({
    # Not knowing
    "idk", "i don't know", "i dont know", "dont know", "don't know", "no idea",
    # Giving up
    "i give up", "give up", "skip", "skip it", "leave it",
    "whatever", "nevermind", "never mind", "forget it",
    "just tell me", "tell me the answer", "what's the answer",
    # Can't do it
    "i can't", "i cant", "can't do", "cant do",
    # Difficulty
    "this is hard", "too hard", "its hard", "it's hard",
    "confusing", "confused", "i'm confused", "im confused",
    "don't understand", "dont understand", "didn't understand", "didnt understand",
    "not getting it", "i don't get it", "i dont get it", "makes no sense",
    # Frustration with repeated failure
    "again wrong", "wrong again", "still wrong",
})

# Regex patterns for minimal/gibberish responses indicating frustration.
FRUSTRATION_PATTERNS = (
    r'^\.+$',            # Just dots: ".", ".."
    r'^[.!?,\s]+$',      # Just punctuation
    r'^[a-z]{1,2}$',     # Single/double letters (but "no"/"yes" excluded in code)
    r'^(um+|uh+|ah+|hm+)$',  # Hesitation sounds
)


def calculate_warmth_level(
    attempt_number: int,
    is_correct: bool,
    consecutive_wrong: int = 0,
    response_time_seconds: float = 0,
    student_answer: str = "",
) -> int:
    """
    Calculate warmth level: 0=neutral, 1=calm, 2=supportive, 3=soothing.
    """
    if is_correct:
        return 1  # Calm for correct answers

    # Check for frustration signals
    student_lower = student_answer.lower().strip()

    # Skip frustration check for valid yes/no answers
    if student_lower not in ("no", "yes"):
        has_frustration_phrase = any(p in student_lower for p in FRUSTRATION_PHRASES)
        has_frustration_pattern = any(
            re.match(pattern, student_lower) for pattern in FRUSTRATION_PATTERNS
        )
        is_frustrated = (
            consecutive_wrong >= 2 or
            has_frustration_phrase or
            has_frustration_pattern or
            response_time_seconds > 30
        )
        if is_frustrated:
            return 3  # Soothing for frustrated students

    return 2  # Supportive for wrong answers


def get_warmth_primitive(warmth_level: int, session_id: str = "") -> str:
    """Get a warmth phrase, avoiding recent repeats within session."""
    import random

    primitives = WARMTH_PRIMITIVES.get(warmth_level, ())
    if not primitives:
        return ""

    # Avoid recently used primitives
    recent = _recent_primitives.get(session_id, [])
    available = [p for p in primitives if p not in recent] or list(primitives)
    chosen = random.choice(available)

    # Track usage (keep last 3)
    if session_id:
        recent = (recent + [chosen])[-3:]  # Simpler than append + pop
        _recent_primitives[session_id] = recent

    return chosen


def clear_warmth_history(session_id: str):
    """Clear warmth primitive history for a session."""
    _recent_primitives.pop(session_id, None)


def get_diagnostic_starter() -> str:
    """Get a diagnostic question to understand student's thinking."""
    import random
    return random.choice(DIAGNOSTIC_STARTERS)


def get_agency_phrase() -> str:
    """Get a phrase offering student choice/agency."""
    import random
    return random.choice(AGENCY_PHRASES)


def get_validation_phrase() -> str:
    """Get a phrase validating student's feelings."""
    import random
    return random.choice(VALIDATION_PHRASES)


def get_analogy(skill: str) -> Optional[Dict[str, str]]:
    """Get a real-world analogy for a math concept, or None if not found."""
    # Direct match
    if skill in CONCEPT_ANALOGIES:
        return CONCEPT_ANALOGIES[skill]

    # Fuzzy match - check if any key words appear in skill
    skill_lower = skill.lower()
    for key, analogy in CONCEPT_ANALOGIES.items():
        key_words = key.split('_')
        if key in skill_lower or any(word in skill_lower for word in key_words):
            return analogy

    return None


def remove_banned_phrases(text: str) -> str:
    """
    Remove assistant-y phrases. Preserves warmth primitive (first short sentence).
    """
    # Find first sentence break to preserve warmth primitive
    period_pos = text.find('. ')
    question_pos = text.find('? ')
    first_break = min(
        period_pos if period_pos > 0 else len(text),
        question_pos if question_pos > 0 else len(text),
    )

    # Split if warmth primitive found (short first sentence)
    if 0 < first_break <= 20:
        warmth_part = text[:first_break + 1]
        rest = text[first_break + 1:].strip()
    else:
        warmth_part, rest = "", text

    # Remove banned phrases with word boundaries
    for phrase in BANNED_PHRASES:
        pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
        rest = pattern.sub('', rest)

    # Clean up artifacts
    rest = re.sub(r'\s+', ' ', rest)      # Multiple spaces
    rest = re.sub(r'^[,\s]+|[,\s]+$', '', rest)  # Leading/trailing commas
    rest = re.sub(r'\.{2,}', '.', rest)   # Multiple periods
    rest = rest.strip()

    return f"{warmth_part} {rest}".strip() if warmth_part else rest


class TeacherPlanner:
    """
    Decides WHAT teaching move to use based on:
    - Question + expected answer
    - Student's response
    - Error diagnosis
    - Session state (attempts, hints used)
    - Student model (weak skills, pace)
    """

    def __init__(self):
        self.last_moves: List[TeachingMove] = []  # Track to avoid repetition
        self.max_move_history = 5

    def plan(
        self,
        is_correct: bool,
        error_diagnosis: Dict[str, Any],
        attempt_number: int,
        question_text: str,
        correct_answer: str,
        student_answer: str,
        hint_1: str = "",
        hint_2: str = "",
        solution: str = "",
        student_weak_topics: List[str] = None,
        consecutive_wrong: int = 0,
        session_id: str = "",
        # Enriched data (Stage 1)
        micro_check_question: str = "",
        solution_steps: List[str] = None,
    ) -> TeacherPlan:
        """
        Generate a teaching plan based on evaluation.

        This is Pass 1: Structured decision-making.
        The result guides Pass 2 (LLM speaking).
        """
        error_type = error_diagnosis.get("error_type", ErrorType.UNKNOWN.value)
        error_hint = error_diagnosis.get("hint", "")

        # Calculate warmth level based on context
        warmth = calculate_warmth_level(
            attempt_number=attempt_number,
            is_correct=is_correct,
            consecutive_wrong=consecutive_wrong,
            student_answer=student_answer,
        )
        warmth_phrase = get_warmth_primitive(warmth, session_id)

        # CORRECT ANSWER
        if is_correct:
            move = TeachingMove.CONFIRM
            if attempt_number == 1:
                # Quick correct - maybe challenge them
                move = TeachingMove.CHALLENGE if self._should_challenge() else TeachingMove.CONFIRM

            # Per ChatGPT: even confirm should end with quick check
            # "Correct. Now, what's the rule you used in one line?"
            return TeacherPlan(
                teacher_move=move,
                goal="Acknowledge success and reinforce understanding",
                prompt_to_student="What rule did you use?",  # Quick check even on correct
                explanation=f"Correct!",
                check_question=None,
                tone="warm",
                max_words=20,
                warmth_level=warmth,
                warmth_primitive=warmth_phrase,
            )

        # WRONG ANSWER - Choose teaching move based on attempt and error
        move = self._select_move(attempt_number, error_type)

        # Apply repetition breaker
        move = self._break_repetition(move, attempt_number)

        # Track this move
        self._record_move(move)

        # Build the plan based on selected move
        return self._build_plan(
            move=move,
            error_type=error_type,
            error_hint=error_hint,
            attempt_number=attempt_number,
            question_text=question_text,
            correct_answer=correct_answer,
            student_answer=student_answer,
            hint_1=hint_1,
            hint_2=hint_2,
            solution=solution,
            consecutive_wrong=consecutive_wrong,
            session_id=session_id,
            micro_check_question=micro_check_question,
            solution_steps=solution_steps or [],
        )

    def _select_move(self, attempt_number: int, error_type: str) -> TeachingMove:
        """
        Select teaching move based on attempt and error type.

        Escalation ladder (per ChatGPT feedback):
        - Attempt 1: PROBE (diagnose - locate the misunderstanding)
        - Attempt 2: hint_step (small step based on diagnosis)
        - Attempt 3: reframe OR worked_example (change representation)
        - Attempt 4+: reveal (last resort, gated)

        Key insight: "hint_step is not diagnostic. Probe locates misunderstanding."
        """

        # Attempt 1: PROBE (diagnostic question to locate misunderstanding)
        if attempt_number == 1:
            return TeachingMove.PROBE

        # Attempt 2: HINT_STEP (small step based on diagnosis)
        elif attempt_number == 2:
            # Use error_type to choose targeted hint
            if error_type == ErrorType.SIGN_ERROR.value:
                return TeachingMove.REFRAME  # Number line visualization
            elif error_type == ErrorType.WRONG_OPERATION.value:
                return TeachingMove.HINT_STEP  # Probe keyword then hint
            else:
                return TeachingMove.HINT_STEP

        # Attempt 3: REFRAME or WORKED_EXAMPLE (change representation)
        elif attempt_number == 3:
            if error_type in [ErrorType.CONCEPT_MISUNDERSTANDING.value,
                             ErrorType.SIGN_ERROR.value]:
                return TeachingMove.REFRAME
            else:
                return TeachingMove.WORKED_EXAMPLE

        # Attempt 4+: REVEAL (gated - last resort)
        else:
            return TeachingMove.REVEAL

    def _break_repetition(self, move: TeachingMove, attempt: int) -> TeachingMove:
        """
        Repetition breaker: If same move used 2 times and student still wrong,
        force a different approach.
        """
        if len(self.last_moves) >= 2:
            last_two = self.last_moves[-2:]
            if all(m == move for m in last_two):
                # Same move failed twice - try different approach
                if move == TeachingMove.HINT_STEP:
                    return TeachingMove.WORKED_EXAMPLE
                elif move == TeachingMove.PROBE:
                    return TeachingMove.REFRAME
                elif move == TeachingMove.WORKED_EXAMPLE:
                    return TeachingMove.ERROR_EXPLAIN
        return move

    def _record_move(self, move: TeachingMove):
        """Record move for repetition tracking."""
        self.last_moves.append(move)
        if len(self.last_moves) > self.max_move_history:
            self.last_moves.pop(0)

    def _build_plan(
        self,
        move: TeachingMove,
        error_type: str,
        error_hint: str,
        attempt_number: int,
        question_text: str,
        correct_answer: str,
        student_answer: str,
        hint_1: str,
        hint_2: str,
        solution: str,
        consecutive_wrong: int = 0,
        session_id: str = "",
        micro_check_question: str = "",
        solution_steps: List[str] = None,
    ) -> TeacherPlan:
        """Build a complete teaching plan for the selected move."""

        # Calculate warmth level based on context
        warmth = calculate_warmth_level(
            attempt_number=attempt_number,
            is_correct=False,  # _build_plan only called for wrong answers
            consecutive_wrong=consecutive_wrong,
            student_answer=student_answer,
        )
        warmth_phrase = get_warmth_primitive(warmth, session_id)

        # Determine expected response type based on correct answer
        expected_type = "number"
        max_resp_words = 5
        if correct_answer.lower() in ["yes", "no"]:
            expected_type = "yes_no"
            max_resp_words = 3
        elif "/" in correct_answer:
            expected_type = "number"  # fraction
            max_resp_words = 5

        if move == TeachingMove.PROBE:
            # Use verified micro_check question when available (enriched data)
            probe_prompt = micro_check_question or error_hint or "What step did you do first?"
            return TeacherPlan(
                teacher_move=move,
                goal="Find what student doesn't understand",
                prompt_to_student=probe_prompt,
                explanation="",
                check_question=None,
                tone="warm",
                max_words=25,
                expected_response_type="short_explanation",
                max_response_words=15,
                warmth_level=warmth,
                warmth_primitive=warmth_phrase,
            )

        elif move == TeachingMove.HINT_STEP:
            # Use enriched micro_hint from matched_mistake when available
            hint_prompt = hint_1 or error_hint
            return TeacherPlan(
                teacher_move=move,
                goal="Give smallest next step",
                prompt_to_student=f"Try again: {hint_prompt}" if hint_prompt else "Try again.",
                explanation="",
                check_question=None,
                tone="neutral",
                max_words=30,
                expected_response_type=expected_type,
                max_response_words=max_resp_words,
                warmth_level=warmth,
                warmth_primitive=warmth_phrase,
            )

        elif move == TeachingMove.WORKED_EXAMPLE:
            # Use solution_steps when available for richer explanation
            steps = solution_steps or []
            if steps and len(steps) >= 2:
                explanation = ". ".join(steps[:3]) + "."
            else:
                explanation = hint_2 or "Let me show you a simpler case first."
            return TeacherPlan(
                teacher_move=move,
                goal="Show similar simpler example",
                prompt_to_student="Now apply the same idea to your question.",
                explanation=explanation,
                check_question=None,
                tone="warm",
                max_words=45,
                expected_response_type=expected_type,
                max_response_words=max_resp_words,
                warmth_level=warmth,
                warmth_primitive=warmth_phrase,
            )

        elif move == TeachingMove.ERROR_EXPLAIN:
            error_name = self._get_error_name(error_type)
            return TeacherPlan(
                teacher_move=move,
                goal="Name and fix the specific error",
                prompt_to_student=f"You made a {error_name}. {error_hint}",
                explanation="",
                check_question=None,  # Question is in prompt
                tone="firm",
                max_words=35,
                expected_response_type=expected_type,
                max_response_words=max_resp_words,
                warmth_level=warmth,
                warmth_primitive=warmth_phrase,
            )

        elif move == TeachingMove.REFRAME:
            return TeacherPlan(
                teacher_move=move,
                goal="Explain differently",
                prompt_to_student="Think of it this way...",
                explanation=hint_2 or solution[:100] if solution else "",
                check_question=None,  # Removed rhetorical
                tone="warm",
                max_words=45,
                expected_response_type=expected_type,
                max_response_words=max_resp_words,
                warmth_level=warmth,
                warmth_primitive=warmth_phrase,
            )

        elif move == TeachingMove.REVEAL:
            # Reveal: explicit exception - no question required (documented)
            # Warmth level 2 (supportive) for reveal - student struggled
            reveal_warmth = get_warmth_primitive(2, session_id)
            return TeacherPlan(
                teacher_move=move,
                goal="Show correct answer with brief explanation",
                prompt_to_student="",
                explanation=f"The answer is {correct_answer}. {solution[:80] if solution else ''}",
                check_question=None,
                tone="warm",
                max_words=40,
                expected_response_type="none",  # No response expected
                max_response_words=0,
                warmth_level=2,  # Supportive - student needs encouragement
                warmth_primitive=reveal_warmth,
            )

        elif move == TeachingMove.CHALLENGE:
            return TeacherPlan(
                teacher_move=move,
                goal="Challenge with harder follow-up",
                prompt_to_student="Good! Can you tell me why that's correct?",
                explanation="",
                check_question=None,
                tone="warm",
                max_words=20,
                warmth_level=1,  # Calm
                warmth_primitive="",
            )

        else:  # CONFIRM
            return TeacherPlan(
                teacher_move=move,
                goal="Acknowledge correct answer",
                prompt_to_student="",
                explanation=f"Yes, {correct_answer} is right.",
                check_question=None,
                tone="warm",
                max_words=20,
                warmth_level=1,  # Calm
                warmth_primitive="",
            )

    def _get_error_name(self, error_type: str) -> str:
        """Get human-readable error name."""
        names = {
            ErrorType.SIGN_ERROR.value: "sign mistake",
            ErrorType.ARITHMETIC_SLIP.value: "calculation slip",
            ErrorType.FRACTION_ADDITION.value: "common fraction mistake",
            ErrorType.COMMON_DENOMINATOR.value: "denominator issue",
            ErrorType.WRONG_OPERATION.value: "wrong operation",
        }
        return names.get(error_type, "small mistake")

    def _should_challenge(self) -> bool:
        """Decide if we should challenge after correct answer."""
        # Challenge occasionally when student is doing well
        import random
        return random.random() < 0.2  # 20% chance

    def reset(self):
        """Reset move history for new session."""
        self.last_moves = []


# ============================================================
# RESPONSE GENERATOR (Pass 2: Speaking) + ENFORCEMENT
# ============================================================

# P0 ENFORCEMENT: Acceptance criteria
MAX_SENTENCES_BEFORE_QUESTION = 2
ONE_QUESTION_RULE = True  # Only one question per turn
MUST_END_WITH_QUESTION = True  # Teaching turns must end with question

# Moves that MUST end with a check question (TEACH → CHECK rule)
TEACHING_MOVES_REQUIRE_CHECK = {
    TeachingMove.PROBE,
    TeachingMove.HINT_STEP,
    TeachingMove.WORKED_EXAMPLE,
    TeachingMove.ERROR_EXPLAIN,
    TeachingMove.REFRAME,
    TeachingMove.RECAP,
}

# Moves that don't need a check question
NO_CHECK_REQUIRED = {
    TeachingMove.CONFIRM,
    TeachingMove.CHALLENGE,  # Challenge IS the question
    TeachingMove.REVEAL,     # Showing answer, moving on
}

# Default check questions when plan doesn't have one
DEFAULT_CHECK_QUESTIONS = [
    "What do you get?",
    "Try again?",
    "What's your answer?",
    "Can you try?",
]


def _count_sentences(text: str) -> int:
    """Count sentences in text."""
    import re
    # Split on sentence endings
    sentences = re.split(r'[.!?]+', text)
    # Filter empty
    return len([s for s in sentences if s.strip()])


def _count_questions(text: str) -> int:
    """Count questions in text."""
    return text.count('?')


def _ends_with_question(text: str) -> bool:
    """Check if text ends with a question."""
    text = text.strip()
    return text.endswith('?')


def _enforce_max_sentences(text: str, max_sentences: int = 2) -> str:
    """
    P0 ENFORCEMENT: Max 2 sentences before the question.
    Truncates if too long.
    """
    import re

    # Split into sentences (keep delimiters)
    parts = re.split(r'([.!?]+)', text)

    # Reconstruct sentences
    sentences = []
    current = ""
    for part in parts:
        if re.match(r'^[.!?]+$', part):
            current += part
            if current.strip():
                sentences.append(current.strip())
            current = ""
        else:
            current = part

    if current.strip():
        sentences.append(current.strip())

    # If within limit, return as-is
    if len(sentences) <= max_sentences:
        return text

    # Truncate to max sentences
    return " ".join(sentences[:max_sentences])


def _enforce_one_question(text: str) -> str:
    """
    P0 ENFORCEMENT: Only ONE question per turn.
    Keeps only the last question if multiple exist.
    """
    if _count_questions(text) <= 1:
        return text

    import re

    # Split on question marks
    parts = text.split('?')

    if len(parts) <= 2:
        return text

    # Keep statements before last question + last question
    # "What's 2+2? And 3+3?" → "What's 2+2. And 3+3?"
    statements = parts[:-2]
    last_question = parts[-2]

    # Convert earlier questions to statements
    result_parts = []
    for stmt in statements:
        stmt = stmt.strip()
        if stmt:
            result_parts.append(stmt + ".")

    result_parts.append(last_question.strip() + "?")

    return " ".join(result_parts)


def _enforce_ends_with_question(text: str, move: TeachingMove) -> str:
    """
    P0 ENFORCEMENT: Teaching moves MUST end with a question.
    Adds default check question if missing.
    """
    if move not in TEACHING_MOVES_REQUIRE_CHECK:
        return text

    if _ends_with_question(text):
        return text

    # Add a default check question
    import random
    check = random.choice(DEFAULT_CHECK_QUESTIONS)

    text = text.strip()
    if not text.endswith(('.', '!', '?')):
        text += "."

    return f"{text} {check}"


def generate_teacher_response(plan: TeacherPlan) -> Dict[str, Any]:
    """
    Generate the actual spoken response from the teaching plan.

    This is Pass 2: Render the plan in teacher voice.

    P0 ENFORCEMENT (strict rules):
    - Max 2 sentences before asking a question
    - Must end with exactly ONE question (if teaching move)
    - One-question rule (never ask multiple questions)

    WARMTH POLICY:
    - Prepend warmth primitive (max 8 words) if present
    - Only one warmth phrase per turn
    """
    parts = []

    # Add warmth primitive FIRST if present (max 8 words acknowledgement)
    if plan.warmth_primitive:
        parts.append(plan.warmth_primitive.strip())

    # Add explanation if present
    if plan.explanation:
        parts.append(plan.explanation.strip())

    # Add the prompt/question
    if plan.prompt_to_student:
        parts.append(plan.prompt_to_student.strip())

    # Add check question if present (for TEACH → CHECK rule)
    if plan.check_question:
        parts.append(plan.check_question.strip())

    response = " ".join(parts)

    # === WARMTH POLICY: Remove banned phrases ===
    response = remove_banned_phrases(response)

    # === P0 ENFORCEMENT ===

    # 1. Max 2 sentences before question
    response = _enforce_max_sentences(response, MAX_SENTENCES_BEFORE_QUESTION)

    # 2. One question rule
    if ONE_QUESTION_RULE:
        response = _enforce_one_question(response)

    # 3. Must end with question (for teaching moves)
    if MUST_END_WITH_QUESTION:
        response = _enforce_ends_with_question(response, plan.teacher_move)

    # 4. Final word limit check
    words = response.split()
    if len(words) > plan.max_words:
        response = " ".join(words[:plan.max_words])
        if not response.endswith(('.', '?', '!')):
            response += "?"  # Prefer question ending

    # Count for metrics
    sentence_count = _count_sentences(response)
    question_count = _count_questions(response)
    ends_with_q = _ends_with_question(response)

    return {
        "response": response,
        "teacher_move": plan.teacher_move.value,
        "goal": plan.goal,
        "tone": plan.tone,
        "has_check_question": plan.check_question is not None,
        "max_words": plan.max_words,
        # P0 metrics for acceptance criteria
        "sentence_count": sentence_count,
        "question_count": question_count,
        "ends_with_question": ends_with_q,
        # New fields for UI/barge-in (per ChatGPT feedback)
        "expected_response_type": plan.expected_response_type,
        "max_response_words": plan.max_response_words,
        # Warmth policy
        "warmth_level": plan.warmth_level,
        "warmth_primitive": plan.warmth_primitive,
    }


# ============================================================
# MAIN INTERFACE
# ============================================================

# Global planner instance (maintains move history per session)
_session_planners: Dict[str, TeacherPlanner] = {}


def get_planner(session_id: str) -> TeacherPlanner:
    """Get or create planner for session."""
    if session_id not in _session_planners:
        _session_planners[session_id] = TeacherPlanner()
    return _session_planners[session_id]


def clear_planner(session_id: str):
    """Clear planner when session ends."""
    if session_id in _session_planners:
        del _session_planners[session_id]


def plan_teacher_response(
    session_id: str,
    is_correct: bool,
    correct_answer: str,
    student_answer: str,
    question_text: str,
    attempt_number: int,
    hint_1: str = "",
    hint_2: str = "",
    solution: str = "",
    question_type: str = "numeric",
    # Enriched data from evaluate_answer (Stage 1)
    eval_result: Optional[Dict] = None,
    common_mistakes: Optional[List[Dict]] = None,
    micro_checks: Optional[List[str]] = None,
    solution_steps: Optional[List[str]] = None,
    target_skill: str = "",
) -> Dict[str, Any]:
    """
    Main entry point: Plan and generate teacher response.

    Combines:
    1. Error diagnosis (uses eval_result.matched_mistake when available)
    2. Teaching move selection
    3. Response generation

    Returns dict with:
    - response: The text to speak
    - teacher_move: Which move was used
    - error_type: What error was diagnosed (if wrong)
    - goal: What this response aims to achieve
    """
    common_mistakes = common_mistakes or []
    micro_checks = micro_checks or []
    solution_steps = solution_steps or []

    # Step 1: Diagnose error (if wrong)
    # Prefer eval_result from enriched evaluator when available
    if is_correct:
        error_diagnosis = {"error_type": None, "confidence": 1.0, "hint": ""}
    elif eval_result and eval_result.get("matched_mistake"):
        # Use deterministic diagnosis from common_mistakes match
        matched = eval_result["matched_mistake"]
        error_diagnosis = {
            "error_type": matched.get("error_type", ErrorType.UNKNOWN.value),
            "confidence": 1.0,  # Deterministic match = high confidence
            "hint": matched.get("micro_hint", ""),
            "missing_concept": None,
            "diagnosis": matched.get("diagnosis", ""),
        }
    else:
        # Fall back to heuristic diagnosis
        error_diagnosis = diagnose_error(
            correct_answer=correct_answer,
            student_answer=student_answer,
            question_text=question_text,
            question_type=question_type,
        )

    # Step 2: Get planner and create plan
    planner = get_planner(session_id)

    # Use micro_check as probe question when available
    probe_question = ""
    if micro_checks and attempt_number <= len(micro_checks):
        probe_question = micro_checks[attempt_number - 1]

    # Use matched_mistake micro_hint for HINT_STEP when available
    enriched_hint = ""
    if eval_result and eval_result.get("micro_hint"):
        enriched_hint = eval_result["micro_hint"]

    plan = planner.plan(
        is_correct=is_correct,
        error_diagnosis=error_diagnosis,
        attempt_number=attempt_number,
        question_text=question_text,
        correct_answer=correct_answer,
        student_answer=student_answer,
        hint_1=enriched_hint or hint_1,
        hint_2=hint_2,
        solution=solution,
        session_id=session_id,
        micro_check_question=probe_question,
        solution_steps=solution_steps,
    )

    # Step 3: Generate response from plan
    result = generate_teacher_response(plan)

    # Add diagnosis info
    result["error_type"] = error_diagnosis.get("error_type")
    result["error_confidence"] = error_diagnosis.get("confidence", 0)
    # Gated reveal: only move to next after attempt 4+ (per ChatGPT feedback)
    result["move_to_next"] = is_correct or attempt_number >= 4
    result["show_answer"] = plan.teacher_move == TeachingMove.REVEAL

    return result


# For testing
if __name__ == "__main__":
    print("=== Teacher Policy Test ===\n")

    # Test error diagnosis
    print("Error Diagnosis Tests:")
    tests = [
        ("5", "-5", "What is 3 - 8?"),  # Sign error
        ("11/12", "2/7", "What is 1/3 + 1/4?"),  # Fraction addition error
        ("7", "8", "What is 3 + 4?"),  # Arithmetic slip
    ]

    for correct, student, question in tests:
        result = diagnose_error(correct, student, question)
        print(f"  Q: {question}")
        print(f"  Correct: {correct}, Student: {student}")
        print(f"  Diagnosis: {result['error_type']} (conf: {result['confidence']})")
        print(f"  Hint: {result['hint']}")
        print()

    # Test full planning
    print("\nTeacher Planning Test:")
    result = plan_teacher_response(
        session_id="test123",
        is_correct=False,
        correct_answer="-1/7",
        student_answer="1/7",
        question_text="What is -3/7 + 2/7?",
        attempt_number=1,
        hint_1="Check the signs of the numerators.",
        hint_2="Add -3 and 2. What do you get?",
        solution="Add numerators: -3 + 2 = -1. Keep denominator: 7. Answer: -1/7",
    )
    print(f"  Move: {result['teacher_move']}")
    print(f"  Response: {result['response']}")
    print(f"  Error: {result['error_type']}")
    print(f"  Goal: {result['goal']}")
