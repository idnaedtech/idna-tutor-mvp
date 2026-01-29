"""
IDNA EdTech - TutorIntent Layer
================================
This module implements the TutorIntent system for natural, human-like teaching behavior.

Architecture (per PRD):
- Brain = FSM (flow control) + Evaluator (deterministic)
- LLM = Language layer ONLY (phrasing, not judging)
- TutorIntent = Controls teaching micro-behaviors

Key Principles:
1. Voice pacing: max 2 sentences per turn
2. One idea per sentence
3. Avoid robotic transitions ("Now," "Therefore," "Next,")
4. Warm, encouraging tone for Tier 2/3 Indian students
"""

from enum import Enum
from typing import Optional, Dict, Any
import random


class TutorIntent(Enum):
    """
    Teaching intents that map to FSM states.
    Each intent has specific phrasing rules and emotional tone.
    """
    ASK_FRESH = "ask_fresh"           # Present new question
    CONFIRM_CORRECT = "confirm_correct"  # Celebrate right answer
    GUIDE_THINKING = "guide_thinking"    # Hint 1 - Socratic nudge
    NUDGE_CORRECTION = "nudge_correction"  # Hint 2 - Direct guidance
    EXPLAIN_ONCE = "explain_once"        # Show solution after 3 attempts
    MOVE_ON = "move_on"                  # Transition to next question
    ENCOURAGE_RETRY = "encourage_retry"  # Gentle encouragement to try again
    SESSION_START = "session_start"      # Welcome message
    SESSION_END = "session_end"          # Closing message


# Phrasing templates for each intent
# Format: List of templates with {placeholders} for dynamic content
INTENT_PHRASES = {
    TutorIntent.ASK_FRESH: {
        "style": "curious, inviting",
        "max_sentences": 2,
        "templates": [
            "Here's your question. {question}",
            "Let's try this one. {question}",
            "Ready? {question}",
            "Okay, here we go. {question}",
            "Try this one. {question}",
        ]
    },
    
    TutorIntent.CONFIRM_CORRECT: {
        "style": "warm, celebratory",
        "max_sentences": 2,
        "templates": [
            "Yes! That's correct. Well done!",
            "Perfect! You got it right.",
            "Excellent work! That's the answer.",
            "Great job! You nailed it.",
            "Correct! I knew you could do it.",
            "Brilliant! That's exactly right.",
            "Wonderful! You're doing great.",
            "That's it! Nice thinking.",
        ]
    },
    
    TutorIntent.GUIDE_THINKING: {
        "style": "calm, Socratic",
        "max_sentences": 2,
        "templates": [
            "Hmm, not quite. {hint} Think about it again.",
            "Close, but not exactly. {hint}",
            "Let me give you a hint. {hint}",
            "Not quite right. {hint} Give it another try.",
            "Almost there. {hint}",
            "Think about this: {hint}",
        ]
    },
    
    TutorIntent.NUDGE_CORRECTION: {
        "style": "supportive, direct",
        "max_sentences": 2,
        "templates": [
            "Let me help more. {hint} Try once more.",
            "Here's a bigger hint. {hint}",
            "Don't worry, you're close. {hint} One more try!",
            "You can do this. {hint}",
            "Last hint: {hint} Give it your best shot.",
        ]
    },
    
    TutorIntent.EXPLAIN_ONCE: {
        "style": "patient, clear",
        "max_sentences": 3,
        "templates": [
            "No problem, let me show you. {solution}",
            "That's okay. Here's how it works: {solution}",
            "Let me explain. {solution}",
            "Don't worry. The answer is: {solution}",
            "Here's the solution: {solution}",
        ]
    },
    
    TutorIntent.MOVE_ON: {
        "style": "encouraging, forward-looking",
        "max_sentences": 1,
        "templates": [
            "Let's try the next one.",
            "Ready for the next question?",
            "Moving on to a new one.",
            "Let's keep going.",
            "Here comes the next one.",
        ]
    },
    
    TutorIntent.ENCOURAGE_RETRY: {
        "style": "warm, supportive",
        "max_sentences": 1,
        "templates": [
            "Take your time.",
            "No rush. Think it through.",
            "You've got this.",
            "Relax and try again.",
        ]
    },
    
    TutorIntent.SESSION_START: {
        "style": "warm, welcoming",
        "max_sentences": 2,
        "templates": [
            "Hello! Ready to practice math? Let's begin.",
            "Welcome back! Let's do some math together.",
            "Hi there! Time for some practice. Let's start.",
            "Great to see you! Let's learn together today.",
        ]
    },
    
    TutorIntent.SESSION_END: {
        "style": "proud, encouraging",
        "max_sentences": 2,
        "templates": [
            "Great practice today! See you next time.",
            "Well done! You worked hard today.",
            "Nice work! Keep practicing and you'll get even better.",
            "Fantastic effort! See you soon.",
        ]
    },
}


# SSML templates for warmer, more natural voice synthesis
# Uses pauses (<break>) and Hinglish phrases for warmth
PHRASES_SSML = {
    TutorIntent.ASK_FRESH: [
        "<speak>Achha beta,<break time='300ms'/> {question}<break time='400ms'/> Take your time.</speak>",
        "<speak>Okay,<break time='250ms'/> here's your question.<break time='400ms'/> {question}</speak>",
        "<speak>Let's try this one.<break time='300ms'/> {question}</speak>",
        "<speak>Ready beta?<break time='300ms'/> {question}</speak>",
    ],
    TutorIntent.CONFIRM_CORRECT: [
        "<speak>Bahut accha!<break time='300ms'/> That's exactly right, beta!</speak>",
        "<speak>Perfect!<break time='250ms'/> Well done!<break time='300ms'/> You got it!</speak>",
        "<speak>Excellent!<break time='300ms'/> I knew you could do it!</speak>",
        "<speak>Shabash!<break time='300ms'/> That's correct!</speak>",
    ],
    TutorIntent.GUIDE_THINKING: [
        "<speak>Hmm,<break time='400ms'/> not quite beta.<break time='300ms'/> {hint}<break time='400ms'/> Try again?</speak>",
        "<speak>Close!<break time='300ms'/> Think about this:<break time='400ms'/> {hint}</speak>",
        "<speak>Almost there.<break time='300ms'/> {hint}<break time='400ms'/> What do you think?</speak>",
    ],
    TutorIntent.NUDGE_CORRECTION: [
        "<speak>Let me help more.<break time='400ms'/> {hint}<break time='400ms'/> Try once more, beta.</speak>",
        "<speak>Okay beta,<break time='300ms'/> step by step.<break time='400ms'/> {hint}</speak>",
        "<speak>Don't worry.<break time='300ms'/> {hint}<break time='400ms'/> One more try!</speak>",
    ],
    TutorIntent.EXPLAIN_ONCE: [
        "<speak>Koi baat nahi beta,<break time='400ms'/> let me explain.<break time='500ms'/> {solution}<break time='400ms'/> Samajh aaya?</speak>",
        "<speak>No problem.<break time='400ms'/> Watch this:<break time='500ms'/> {solution}<break time='400ms'/> Got it?</speak>",
        "<speak>That's okay beta.<break time='400ms'/> Here's how:<break time='500ms'/> {solution}</speak>",
    ],
    TutorIntent.MOVE_ON: [
        "<speak>Chalo,<break time='300ms'/> let's try the next one.</speak>",
        "<speak>Okay,<break time='250ms'/> moving on.<break time='300ms'/> Next question!</speak>",
        "<speak>Aage badhte hain.<break time='300ms'/> Next one!</speak>",
    ],
    TutorIntent.ENCOURAGE_RETRY: [
        "<speak>Take your time beta.<break time='300ms'/> No rush.</speak>",
        "<speak>Sochke batao.<break time='300ms'/> You've got this.</speak>",
    ],
    TutorIntent.SESSION_START: [
        "<speak>Namaste beta!<break time='400ms'/> Ready to learn today?<break time='300ms'/> Let's go!</speak>",
        "<speak>Hello!<break time='300ms'/> Great to see you.<break time='400ms'/> Let's practice together.</speak>",
        "<speak>Aao beta!<break time='300ms'/> Time for some math practice.</speak>",
    ],
    TutorIntent.SESSION_END: [
        "<speak>Bahut accha kiya aaj!<break time='400ms'/> Well done beta.<break time='300ms'/> See you next time!</speak>",
        "<speak>Great work today!<break time='400ms'/> Keep practicing.<break time='300ms'/> Bye beta!</speak>",
        "<speak>Shabash!<break time='300ms'/> You did well today.<break time='400ms'/> Phir milenge!</speak>",
    ],
}


def generate_ssml_response(intent: TutorIntent, **kwargs) -> str:
    """
    Generate SSML response for given intent with placeholders filled.

    Args:
        intent: The TutorIntent to generate SSML for
        **kwargs: Placeholder values (question, hint, solution, etc.)

    Returns:
        SSML string ready for Google Cloud TTS
    """
    templates = PHRASES_SSML.get(intent, ["<speak>{text}</speak>"])
    template = random.choice(templates)

    # Fill placeholders safely
    try:
        return template.format(**kwargs) if kwargs else template
    except KeyError:
        # If placeholder not provided, return template as-is
        return template


def strip_ssml(ssml: str) -> str:
    """
    Strip SSML tags to get plain text for fallback TTS.

    Args:
        ssml: SSML string

    Returns:
        Plain text without SSML tags
    """
    import re
    # Remove <speak> tags
    text = re.sub(r'</?speak>', '', ssml)
    # Remove <break> tags
    text = re.sub(r'<break[^>]*/?>', ' ', text)
    # Clean up extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text


class TutorVoice:
    """
    Generates natural tutor responses based on intent and context.
    Ensures voice-friendly pacing and warm tone.
    """
    
    def __init__(self, language: str = "en"):
        """
        Initialize the tutor voice.
        
        Args:
            language: Language code (default: "en" for English)
                      Future: "hi" for Hindi, "te" for Telugu, etc.
        """
        self.language = language
        self.phrases = INTENT_PHRASES
    
    def get_response(
        self,
        intent: TutorIntent,
        question: Optional[str] = None,
        hint: Optional[str] = None,
        solution: Optional[str] = None,
        student_answer: Optional[str] = None,
        correct_answer: Optional[str] = None,
        attempt_number: int = 0,
        score: Optional[Dict[str, int]] = None,
    ) -> str:
        """
        Generate a natural tutor response for the given intent.
        
        Args:
            intent: The TutorIntent to respond with
            question: The math question (for ASK_FRESH)
            hint: The hint text (for GUIDE_THINKING, NUDGE_CORRECTION)
            solution: The solution explanation (for EXPLAIN_ONCE)
            student_answer: What the student answered
            correct_answer: The correct answer
            attempt_number: Which attempt this is (1, 2, or 3)
            score: Dict with 'correct' and 'total' keys
            
        Returns:
            A natural, voice-friendly tutor response string
        """
        phrase_config = self.phrases.get(intent)
        if not phrase_config:
            return "Let's continue."
        
        # Select a random template
        template = random.choice(phrase_config["templates"])
        
        # Fill in placeholders
        response = template
        if question:
            response = response.replace("{question}", question)
        if hint:
            response = response.replace("{hint}", hint)
        if solution:
            response = response.replace("{solution}", solution)
        if correct_answer:
            response = response.replace("{correct_answer}", correct_answer)
        
        return response
    
    def determine_intent(
        self,
        is_correct: bool,
        attempt_number: int,
        is_session_start: bool = False,
        is_session_end: bool = False,
        is_new_question: bool = False,
    ) -> TutorIntent:
        """
        Determine the appropriate TutorIntent based on FSM state.
        
        FSM Transitions → Intent Mapping:
        - Correct answer → CONFIRM_CORRECT
        - Wrong attempt 1 → GUIDE_THINKING
        - Wrong attempt 2 → NUDGE_CORRECTION  
        - Wrong attempt 3 → EXPLAIN_ONCE
        - New question → ASK_FRESH
        - Session start → SESSION_START
        - Session end → SESSION_END
        
        Args:
            is_correct: Whether the answer was correct
            attempt_number: Current attempt number (1, 2, or 3)
            is_session_start: Whether this is the start of a session
            is_session_end: Whether this is the end of a session
            is_new_question: Whether presenting a new question
            
        Returns:
            The appropriate TutorIntent
        """
        if is_session_start:
            return TutorIntent.SESSION_START
        
        if is_session_end:
            return TutorIntent.SESSION_END
        
        if is_new_question:
            return TutorIntent.ASK_FRESH
        
        if is_correct:
            return TutorIntent.CONFIRM_CORRECT
        
        # Wrong answer - escalate hints
        if attempt_number == 1:
            return TutorIntent.GUIDE_THINKING
        elif attempt_number == 2:
            return TutorIntent.NUDGE_CORRECTION
        else:  # attempt_number >= 3
            return TutorIntent.EXPLAIN_ONCE
    
    def build_full_response(
        self,
        is_correct: bool,
        attempt_number: int,
        question: Optional[str] = None,
        hint_1: Optional[str] = None,
        hint_2: Optional[str] = None,
        solution: Optional[str] = None,
        correct_answer: Optional[str] = None,
        move_to_next: bool = False,
    ) -> Dict[str, Any]:
        """
        Build a complete response with intent, text, and metadata.
        
        This is the main method to call from the API endpoint.
        
        Args:
            is_correct: Whether the answer was correct
            attempt_number: Current attempt number
            question: The current question text
            hint_1: First hint (Socratic)
            hint_2: Second hint (direct)
            solution: Full solution explanation
            correct_answer: The correct answer
            move_to_next: Whether to transition to next question
            
        Returns:
            Dict with:
                - intent: TutorIntent name
                - response: The tutor's spoken response
                - move_to_next: Whether to show next question
                - show_answer: Whether to reveal the answer
        """
        intent = self.determine_intent(
            is_correct=is_correct,
            attempt_number=attempt_number,
        )
        
        # Select appropriate hint based on attempt
        hint = None
        if intent == TutorIntent.GUIDE_THINKING:
            hint = hint_1 or "Think about what operation you need."
        elif intent == TutorIntent.NUDGE_CORRECTION:
            hint = hint_2 or hint_1 or "Check your calculation carefully."
        
        # Build the main response (plain text)
        response = self.get_response(
            intent=intent,
            question=question,
            hint=hint,
            solution=solution or f"The answer is {correct_answer}.",
            correct_answer=correct_answer,
            attempt_number=attempt_number,
        )

        # Build SSML response for warmer voice
        ssml_kwargs = {
            "question": question or "",
            "hint": hint or "",
            "solution": solution or f"The answer is {correct_answer}.",
            "correct_answer": correct_answer or "",
        }
        ssml_response = generate_ssml_response(intent, **ssml_kwargs)

        # Add transition if moving to next question
        should_move = is_correct or attempt_number >= 3
        if should_move and move_to_next:
            move_phrase = self.get_response(TutorIntent.MOVE_ON)
            response = f"{response} {move_phrase}"
            # Add SSML transition
            ssml_move = generate_ssml_response(TutorIntent.MOVE_ON)
            # Combine SSML (strip outer <speak> tags and re-wrap)
            ssml_inner = ssml_response.replace("<speak>", "").replace("</speak>", "")
            ssml_move_inner = ssml_move.replace("<speak>", "").replace("</speak>", "")
            ssml_response = f"<speak>{ssml_inner}<break time='400ms'/> {ssml_move_inner}</speak>"

        return {
            "intent": intent.value,
            "response": response,
            "ssml": ssml_response,
            "move_to_next": should_move,
            "show_answer": intent == TutorIntent.EXPLAIN_ONCE,
            "attempt_number": attempt_number,
        }


# Convenience function for API integration
def generate_tutor_response(
    is_correct: bool,
    attempt_number: int,
    question: str = "",
    hint_1: str = "",
    hint_2: str = "",
    solution: str = "",
    correct_answer: str = "",
) -> Dict[str, Any]:
    """
    Generate a tutor response. Call this from the API endpoint.
    
    Example usage in web_server.py:
    
        from tutor_intent import generate_tutor_response
        
        result = generate_tutor_response(
            is_correct=False,
            attempt_number=1,
            question=question['question'],
            hint_1=question.get('hint_1', ''),
            hint_2=question.get('hint_2', ''),
            solution=question.get('solution', ''),
            correct_answer=question['answer'],
        )
        
        return {
            "correct": result["move_to_next"] and is_correct,
            "message": result["response"],
            "show_answer": result["show_answer"],
            ...
        }
    """
    tutor = TutorVoice()
    return tutor.build_full_response(
        is_correct=is_correct,
        attempt_number=attempt_number,
        question=question,
        hint_1=hint_1,
        hint_2=hint_2,
        solution=solution,
        correct_answer=correct_answer,
        move_to_next=True,
    )


# For testing
if __name__ == "__main__":
    print("=== TutorIntent Layer Test ===\n")

    tutor = TutorVoice()

    # Test scenarios
    scenarios = [
        {"is_correct": True, "attempt": 1, "desc": "Correct on first try"},
        {"is_correct": False, "attempt": 1, "desc": "Wrong - Attempt 1"},
        {"is_correct": False, "attempt": 2, "desc": "Wrong - Attempt 2"},
        {"is_correct": False, "attempt": 3, "desc": "Wrong - Attempt 3"},
    ]

    for s in scenarios:
        result = generate_tutor_response(
            is_correct=s["is_correct"],
            attempt_number=s["attempt"],
            question="What is 2/3 + 1/4?",
            hint_1="Find a common denominator first.",
            hint_2="The common denominator of 3 and 4 is 12.",
            solution="2/3 = 8/12 and 1/4 = 3/12. So 8/12 + 3/12 = 11/12.",
            correct_answer="11/12",
        )
        print(f"📚 {s['desc']}")
        print(f"   Intent: {result['intent']}")
        print(f"   Response: {result['response']}")
        print(f"   SSML: {result['ssml']}")
        print(f"   Move to next: {result['move_to_next']}")
        print()

    # Test SSML generation directly
    print("=== SSML Direct Test ===\n")
    ssml = generate_ssml_response(
        TutorIntent.ASK_FRESH,
        question="What is 5 times 6?"
    )
    print(f"SSML: {ssml}")
    print(f"Plain: {strip_ssml(ssml)}")
