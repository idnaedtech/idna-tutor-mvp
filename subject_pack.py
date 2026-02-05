"""
IDNA EdTech - SubjectPack Interface
====================================
Universal interface for subject-specific tutoring logic.

Architecture:
- One universal conversation engine
- Swap only subject packs
- TutorIntent + Voice layer stays the same across all subjects

Supported Subjects (MVP):
- Math (existing, full support)
- Science (MCQ + keyword short answers)
- English (grammar + reading MCQ + speaking practice)
"""

from abc import ABC, abstractmethod
from typing import List, Literal, Optional, TypedDict
from enum import Enum


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

Subject = Literal["math", "science", "english", "sst", "hindi"]

AnswerType = Literal[
    "numeric",      # Math: exact number/fraction
    "short_text",   # 1-3 words
    "mcq",          # Multiple choice (A/B/C/D)
    "multi_step",   # Requires showing work
    "spoken",       # Fluency/pronunciation check
    "keyword",      # Must contain specific keywords
]


class Canonical(TypedDict):
    """Canonical question representation - same structure for all subjects."""
    question_id: str
    question_text: str
    expected_answer: str            # Can be rubric key / exemplar
    answer_type: AnswerType
    hint_1: str
    hint_2: str
    solution_steps: List[str]       # Explanation ladder
    required_keywords: List[str]    # For keyword-based evaluation
    acceptable_variants: List[str]  # Alternative correct answers
    difficulty: int                 # 1-5 scale
    topic: str
    subtopic: str
    # Enriched fields (Stage 1 — Real Teacher architecture)
    common_mistakes: List[dict]     # [{wrong_answer, error_type, diagnosis, micro_hint}]
    micro_checks: List[str]         # Verified check questions for PROBE move
    target_skill: str               # Skill graph ID (see skill_graph.py)


class EvalResult(TypedDict):
    """Evaluation result - same structure for all subjects."""
    is_correct: bool
    score: float                    # 0.0 to 1.0
    feedback_tag: str               # e.g., "UNIT_MISSING", "GRAMMAR_TENSE"
    normalized_answer: str          # What we understood from student
    partial_credit: bool            # For multi-step problems
    missing_elements: List[str]     # What was missing/wrong


class FeedbackTag(str, Enum):
    """Standard feedback tags across subjects."""
    # General
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    PARTIAL = "PARTIAL"
    
    # Math-specific
    CALCULATION_ERROR = "CALCULATION_ERROR"
    CONCEPT_CONFUSION = "CONCEPT_CONFUSION"
    SIGN_ERROR = "SIGN_ERROR"
    UNIT_MISSING = "UNIT_MISSING"
    FRACTION_NOT_SIMPLIFIED = "FRACTION_NOT_SIMPLIFIED"
    
    # Science-specific
    WRONG_UNIT = "WRONG_UNIT"
    INCOMPLETE_EXPLANATION = "INCOMPLETE_EXPLANATION"
    MISSING_KEYWORD = "MISSING_KEYWORD"
    
    # English-specific
    GRAMMAR_TENSE = "GRAMMAR_TENSE"
    GRAMMAR_AGREEMENT = "GRAMMAR_AGREEMENT"
    SPELLING_ERROR = "SPELLING_ERROR"
    WORD_ORDER = "WORD_ORDER"
    PRONUNCIATION = "PRONUNCIATION"


# =============================================================================
# ABSTRACT BASE CLASS
# =============================================================================

class SubjectPack(ABC):
    """
    Abstract interface for subject-specific tutoring logic.
    
    Each subject implements this interface.
    The conversation engine (FSM + TutorIntent) remains the same.
    """
    
    subject: Subject
    display_name: str
    supported_grades: List[int]
    
    @abstractmethod
    def get_chapters(self, grade: int) -> List[dict]:
        """
        Get available chapters for a grade.
        
        Returns:
            List of {"id": str, "name": str, "topic_count": int}
        """
        pass
    
    @abstractmethod
    def get_question(
        self, 
        chapter_id: str, 
        difficulty: int = 3,
        exclude_ids: List[str] = []
    ) -> Canonical:
        """
        Get a question from the specified chapter.
        
        Args:
            chapter_id: Chapter identifier
            difficulty: 1-5 scale
            exclude_ids: Questions already asked in session
            
        Returns:
            Canonical question representation
        """
        pass
    
    @abstractmethod
    def normalize_answer(self, student_utterance: str) -> str:
        """
        Normalize spoken/typed answer to standard form.
        
        Examples:
            Math: "two by three" → "2/3"
            Science: "newton's first law" → "first_law_of_motion"
            English: "I goed" → "i goed" (preserve error for feedback)
            
        Returns:
            Normalized answer string
        """
        pass
    
    @abstractmethod
    def evaluate(
        self, 
        canonical: Canonical, 
        student_answer: str
    ) -> EvalResult:
        """
        Evaluate student's answer against expected answer.
        
        This is DETERMINISTIC - no LLM involved.
        
        Returns:
            EvalResult with is_correct, score, feedback_tag
        """
        pass
    
    @abstractmethod
    def get_hint(
        self, 
        canonical: Canonical, 
        attempt_no: int,
        eval_result: Optional[EvalResult] = None
    ) -> str:
        """
        Get appropriate hint based on attempt number and error type.
        
        Args:
            canonical: The question
            attempt_no: 1, 2, or 3
            eval_result: Previous evaluation (for targeted hints)
            
        Returns:
            Hint text appropriate for the attempt
        """
        pass
    
    @abstractmethod
    def explain_solution(self, canonical: Canonical) -> List[str]:
        """
        Get step-by-step solution explanation.
        
        Returns:
            List of steps (each step is one sentence)
        """
        pass


# =============================================================================
# MATH SUBJECT PACK (Reference Implementation)
# =============================================================================

class MathSubjectPack(SubjectPack):
    """
    Math subject pack - full implementation.
    
    Answer types: numeric, fraction, multi_step
    Evaluation: Deterministic with variant handling
    """
    
    subject: Subject = "math"
    display_name = "Mathematics"
    supported_grades = [6, 7, 8, 9, 10]
    
    # Import existing question bank
    from questions import ALL_CHAPTERS, CHAPTER_NAMES
    
    def get_chapters(self, grade: int) -> List[dict]:
        # Filter chapters by grade (assuming chapter naming convention)
        return [
            {"id": ch_id, "name": name, "topic_count": len(self.ALL_CHAPTERS.get(ch_id, []))}
            for ch_id, name in self.CHAPTER_NAMES.items()
        ]
    
    def get_question(
        self, 
        chapter_id: str, 
        difficulty: int = 3,
        exclude_ids: List[str] = []
    ) -> Canonical:
        import random
        
        questions = self.ALL_CHAPTERS.get(chapter_id, [])
        available = [q for q in questions if q['id'] not in exclude_ids]
        
        if not available:
            raise ValueError(f"No questions available in {chapter_id}")
        
        q = random.choice(available)
        
        return Canonical(
            question_id=q['id'],
            question_text=q['text'],
            expected_answer=q['answer'],
            answer_type=q.get('answer_type', q.get('type', 'numeric')),
            hint_1=q.get('hint_1', q.get('hint', 'Think about the concept.')),
            hint_2=q.get('hint_2', q.get('hint', 'Check your calculation.')),
            solution_steps=q.get('solution_steps', [f"The answer is {q['answer']}"]),
            required_keywords=[],
            acceptable_variants=q.get('accept_also', q.get('variants', [])),
            difficulty=q.get('difficulty', 3),
            topic=q.get('topic', ''),
            subtopic=q.get('subtopic', ''),
            common_mistakes=q.get('common_mistakes', []),
            micro_checks=q.get('micro_checks', []),
            target_skill=q.get('target_skill', ''),
        )
    
    def normalize_answer(self, student_utterance: str) -> str:
        """Use existing evaluator's normalization."""
        from evaluator import normalize_spoken_input
        return normalize_spoken_input(student_utterance)
    
    def evaluate(
        self, 
        canonical: Canonical, 
        student_answer: str
    ) -> EvalResult:
        """Use existing evaluator."""
        from evaluator import check_answer
        
        normalized = self.normalize_answer(student_answer)
        is_correct = check_answer(canonical['expected_answer'], student_answer)
        
        # Determine feedback tag
        if is_correct:
            feedback_tag = FeedbackTag.CORRECT
        else:
            feedback_tag = self._detect_error_type(canonical, normalized)
        
        return EvalResult(
            is_correct=is_correct,
            score=1.0 if is_correct else 0.0,
            feedback_tag=feedback_tag.value,
            normalized_answer=normalized,
            partial_credit=False,
            missing_elements=[]
        )
    
    def _detect_error_type(self, canonical: Canonical, student_answer: str) -> FeedbackTag:
        """Detect what type of error the student made."""
        # Simple heuristics - can be expanded
        expected = canonical['expected_answer']
        
        # Check for sign error
        if student_answer.startswith('-') != expected.startswith('-'):
            if student_answer.replace('-', '') == expected.replace('-', ''):
                return FeedbackTag.SIGN_ERROR
        
        # Check for unsimplified fraction
        if '/' in expected and '/' in student_answer:
            # Could check if student's fraction equals expected but not simplified
            pass
        
        return FeedbackTag.CALCULATION_ERROR
    
    def get_hint(
        self, 
        canonical: Canonical, 
        attempt_no: int,
        eval_result: Optional[EvalResult] = None
    ) -> str:
        if attempt_no == 1:
            return canonical['hint_1']
        elif attempt_no == 2:
            return canonical['hint_2']
        else:
            return canonical['hint_1']  # Fallback
    
    def explain_solution(self, canonical: Canonical) -> List[str]:
        return canonical['solution_steps']


# =============================================================================
# SCIENCE SUBJECT PACK (MVP Scope)
# =============================================================================

class ScienceSubjectPack(SubjectPack):
    """
    Science subject pack - MVP scope.
    
    Answer types: mcq, keyword, short_text
    Evaluation: Keyword matching, synonym handling
    
    NOT in MVP: Long descriptive answers, diagram-based, experiments
    """
    
    subject: Subject = "science"
    display_name = "Science"
    supported_grades = [6, 7, 8, 9, 10]
    
    # Synonym mappings for common scientific terms
    SYNONYMS = {
        "photosynthesis": ["food making process", "carbon fixation"],
        "friction": ["resistance", "rubbing force"],
        "newton": ["N", "newtons"],
        "joule": ["J", "joules"],
        "metre": ["meter", "m", "metres", "meters"],
    }
    
    def get_chapters(self, grade: int) -> List[dict]:
        # Would load from science question bank
        return []
    
    def get_question(
        self, 
        chapter_id: str, 
        difficulty: int = 3,
        exclude_ids: List[str] = []
    ) -> Canonical:
        # Would load from science question bank
        raise NotImplementedError("Science questions not yet loaded")
    
    def normalize_answer(self, student_utterance: str) -> str:
        """Normalize scientific terms and units."""
        normalized = student_utterance.lower().strip()
        
        # Normalize units
        unit_mappings = {
            "metres per second": "m/s",
            "meters per second": "m/s",
            "kilometres": "km",
            "kilometers": "km",
            "centimetres": "cm",
            "centimeters": "cm",
            "kilograms": "kg",
            "grams": "g",
        }
        
        for full, abbrev in unit_mappings.items():
            normalized = normalized.replace(full, abbrev)
        
        return normalized
    
    def evaluate(
        self, 
        canonical: Canonical, 
        student_answer: str
    ) -> EvalResult:
        """Evaluate with keyword matching and synonym support."""
        normalized = self.normalize_answer(student_answer)
        expected = canonical['expected_answer'].lower()
        
        # MCQ - exact match
        if canonical['answer_type'] == 'mcq':
            is_correct = normalized in [expected, expected[0]]  # "A" or "a"
            return EvalResult(
                is_correct=is_correct,
                score=1.0 if is_correct else 0.0,
                feedback_tag=FeedbackTag.CORRECT.value if is_correct else FeedbackTag.INCORRECT.value,
                normalized_answer=normalized,
                partial_credit=False,
                missing_elements=[]
            )
        
        # Keyword-based
        if canonical['answer_type'] == 'keyword':
            required = canonical['required_keywords']
            found = []
            missing = []
            
            for keyword in required:
                keyword_lower = keyword.lower()
                # Check direct match or synonyms
                if keyword_lower in normalized:
                    found.append(keyword)
                elif any(syn in normalized for syn in self.SYNONYMS.get(keyword_lower, [])):
                    found.append(keyword)
                else:
                    missing.append(keyword)
            
            score = len(found) / len(required) if required else 0
            is_correct = score >= 0.8  # 80% keywords required
            
            return EvalResult(
                is_correct=is_correct,
                score=score,
                feedback_tag=FeedbackTag.CORRECT.value if is_correct else FeedbackTag.MISSING_KEYWORD.value,
                normalized_answer=normalized,
                partial_credit=0 < score < 1,
                missing_elements=missing
            )
        
        # Short text - direct comparison with variants
        variants = [expected] + canonical.get('acceptable_variants', [])
        is_correct = normalized in [v.lower() for v in variants]
        
        return EvalResult(
            is_correct=is_correct,
            score=1.0 if is_correct else 0.0,
            feedback_tag=FeedbackTag.CORRECT.value if is_correct else FeedbackTag.INCORRECT.value,
            normalized_answer=normalized,
            partial_credit=False,
            missing_elements=[]
        )
    
    def get_hint(
        self, 
        canonical: Canonical, 
        attempt_no: int,
        eval_result: Optional[EvalResult] = None
    ) -> str:
        # Targeted hint based on what's missing
        if eval_result and eval_result.get('missing_elements'):
            missing = eval_result['missing_elements'][0]
            return f"Think about: what is the role of {missing}?"
        
        return canonical['hint_1'] if attempt_no == 1 else canonical['hint_2']
    
    def explain_solution(self, canonical: Canonical) -> List[str]:
        return canonical['solution_steps']


# =============================================================================
# ENGLISH SUBJECT PACK (MVP Scope)
# =============================================================================

class EnglishSubjectPack(SubjectPack):
    """
    English subject pack - MVP scope.
    
    Tracks:
    1. Grammar drills (deterministic)
    2. Reading comprehension MCQ (deterministic)
    3. Speaking practice (fluency check - light scoring)
    
    NOT in MVP: Essay grading, creative writing
    """
    
    subject: Subject = "english"
    display_name = "English"
    supported_grades = [6, 7, 8, 9, 10]
    
    # Grammar rules for common errors
    GRAMMAR_PATTERNS = {
        "tense": {
            "goed": "went",
            "runned": "ran",
            "eated": "ate",
            "drinked": "drank",
        },
        "agreement": {
            "he go": "he goes",
            "she go": "she goes",
            "they goes": "they go",
            "he have": "he has",
            "she have": "she has",
        }
    }
    
    def get_chapters(self, grade: int) -> List[dict]:
        return []
    
    def get_question(
        self, 
        chapter_id: str, 
        difficulty: int = 3,
        exclude_ids: List[str] = []
    ) -> Canonical:
        raise NotImplementedError("English questions not yet loaded")
    
    def normalize_answer(self, student_utterance: str) -> str:
        """Preserve original for grammar checking."""
        return student_utterance.strip().lower()
    
    def evaluate(
        self, 
        canonical: Canonical, 
        student_answer: str
    ) -> EvalResult:
        """Evaluate based on answer type."""
        normalized = self.normalize_answer(student_answer)
        expected = canonical['expected_answer'].lower()
        
        # MCQ (reading comprehension)
        if canonical['answer_type'] == 'mcq':
            is_correct = normalized == expected or normalized == expected[0]
            return EvalResult(
                is_correct=is_correct,
                score=1.0 if is_correct else 0.0,
                feedback_tag=FeedbackTag.CORRECT.value if is_correct else FeedbackTag.INCORRECT.value,
                normalized_answer=normalized,
                partial_credit=False,
                missing_elements=[]
            )
        
        # Grammar (check for specific patterns)
        if canonical['answer_type'] == 'short_text':
            is_correct = normalized == expected
            feedback_tag = FeedbackTag.CORRECT if is_correct else self._detect_grammar_error(normalized)
            
            return EvalResult(
                is_correct=is_correct,
                score=1.0 if is_correct else 0.0,
                feedback_tag=feedback_tag.value,
                normalized_answer=normalized,
                partial_credit=False,
                missing_elements=[]
            )
        
        # Speaking (light scoring - mainly for practice)
        if canonical['answer_type'] == 'spoken':
            # For MVP, just check if they said something reasonable
            has_content = len(normalized.split()) >= 3
            return EvalResult(
                is_correct=has_content,
                score=0.7 if has_content else 0.3,  # Generous scoring
                feedback_tag=FeedbackTag.CORRECT.value if has_content else FeedbackTag.INCOMPLETE_EXPLANATION.value,
                normalized_answer=normalized,
                partial_credit=True,
                missing_elements=[]
            )
        
        return EvalResult(
            is_correct=False,
            score=0.0,
            feedback_tag=FeedbackTag.INCORRECT.value,
            normalized_answer=normalized,
            partial_credit=False,
            missing_elements=[]
        )
    
    def _detect_grammar_error(self, answer: str) -> FeedbackTag:
        """Detect type of grammar error."""
        for error, correction in self.GRAMMAR_PATTERNS["tense"].items():
            if error in answer:
                return FeedbackTag.GRAMMAR_TENSE
        
        for error, correction in self.GRAMMAR_PATTERNS["agreement"].items():
            if error in answer:
                return FeedbackTag.GRAMMAR_AGREEMENT
        
        return FeedbackTag.INCORRECT
    
    def get_hint(
        self, 
        canonical: Canonical, 
        attempt_no: int,
        eval_result: Optional[EvalResult] = None
    ) -> str:
        # Grammar-specific hints
        if eval_result:
            tag = eval_result.get('feedback_tag')
            if tag == FeedbackTag.GRAMMAR_TENSE.value:
                return "Check the tense of your verb. Is it past, present, or future?"
            elif tag == FeedbackTag.GRAMMAR_AGREEMENT.value:
                return "Check if your subject and verb agree. Singular or plural?"
        
        return canonical['hint_1'] if attempt_no == 1 else canonical['hint_2']
    
    def explain_solution(self, canonical: Canonical) -> List[str]:
        return canonical['solution_steps']


# =============================================================================
# SUBJECT PACK REGISTRY
# =============================================================================

class SubjectPackRegistry:
    """Registry of all available subject packs."""
    
    _packs: dict[Subject, SubjectPack] = {}
    
    @classmethod
    def register(cls, pack: SubjectPack):
        """Register a subject pack."""
        cls._packs[pack.subject] = pack
    
    @classmethod
    def get(cls, subject: Subject) -> SubjectPack:
        """Get subject pack by name."""
        if subject not in cls._packs:
            raise ValueError(f"Unknown subject: {subject}")
        return cls._packs[subject]
    
    @classmethod
    def list_subjects(cls) -> List[Subject]:
        """List all registered subjects."""
        return list(cls._packs.keys())
    
    @classmethod
    def initialize_defaults(cls):
        """Register default subject packs."""
        cls.register(MathSubjectPack())
        cls.register(ScienceSubjectPack())
        cls.register(EnglishSubjectPack())


# Initialize on import
SubjectPackRegistry.initialize_defaults()


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    print("=== SubjectPack Interface Test ===\n")
    
    # Get math pack
    math = SubjectPackRegistry.get("math")
    print(f"Subject: {math.display_name}")
    print(f"Grades: {math.supported_grades}")
    
    # Test normalization
    test_utterances = [
        "two by three",
        "minus five",
        "the answer is 7",
    ]
    
    print("\nNormalization tests:")
    for utterance in test_utterances:
        normalized = math.normalize_answer(utterance)
        print(f"  '{utterance}' → '{normalized}'")
    
    print("\nRegistered subjects:", SubjectPackRegistry.list_subjects())
